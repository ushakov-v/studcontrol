from flask import render_template, request, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime
import re
from models import db, User, Request

@login_required
def edit_user_route(user_id):
    user = User.query.get(user_id)
    message = None
    message_type = None

    # Create data structure for captains by institute
    captains = User.query.filter_by(role='captain').all()
    institutes_captains = {}
    for captain in captains:
        if captain.institute not in institutes_captains:
            institutes_captains[captain.institute] = []
        institutes_captains[captain.institute].append({
            "id": captain.id,
            "full_name": captain.full_name,
            "group": captain.group,
            "start_date": captain.start_date.strftime('%Y-%m-%d'),
            "end_date": captain.end_date.strftime('%Y-%m-%d')
        })

    # Get the current captain for the student
    current_captain_id = None
    if user.role == 'student':
        current_captain_request = Request.query.filter_by(student_id=user_id, status='approved').first()
        if current_captain_request:
            current_captain_id = current_captain_request.captain_id

    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        role = request.form.get('role')
        institute = request.form.get('institute')
        captain_id = request.form.get('captain_id')

        if role != 'student' and role != 'admin':
            group = request.form.get('group')
            start_date_str = request.form.get('start_date')
            end_date_str = request.form.get('end_date')

        # Validate full name
        if not re.match(r'^[А-Яа-яЁё\s-]+$', full_name):
            message = 'ФИО должно содержать только буквы русского алфавита.'
            message_type = 'danger'
            return render_template('authorization/edit_user.html', user=user, institutes_captains=institutes_captains, current_captain_id=current_captain_id, message=message, message_type=message_type)

        # Validate email
        email_regex = r'^[^@]+@[^@]+\.[^@]+$'
        if not re.match(email_regex, email):
            message = 'Введите корректный email адрес.'
            message_type = 'danger'
            return render_template('authorization/edit_user.html', user=user, institutes_captains=institutes_captains, current_captain_id=current_captain_id, message=message, message_type=message_type)

        if role == 'captain':
            # Validate dates
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                message = 'Неправильный формат даты.'
                message_type = 'danger'
                return render_template('authorization/edit_user.html', user=user, institutes_captains=institutes_captains, current_captain_id=current_captain_id, message=message, message_type=message_type)

            if start_date >= end_date:
                message = 'Дата начала обучения должна быть раньше даты окончания.'
                message_type = 'danger'
                return render_template('authorization/edit_user.html', user=user, institutes_captains=institutes_captains, current_captain_id=current_captain_id, message=message, message_type=message_type)

        user.full_name = full_name
        user.email = email
        user.role = role

        if role == 'admin':
            user.group = 'admin'
            user.institute = 'admin'
            user.start_date = datetime.strptime('2024-01-01', '%Y-%m-%d').date()
            user.end_date = datetime.strptime('2025-12-31', '%Y-%m-%d').date()
        else:
            user.institute = institute

        if role == 'chief':
            user.group = 'Без группы'
        elif role != 'student' and role != 'admin':
            user.group = group
            user.start_date = start_date
            user.end_date = end_date
        elif captain_id and role == 'student':
            captain = User.query.get(captain_id)
            if captain:
                user.group = captain.group
                user.start_date = captain.start_date
                user.end_date = captain.end_date

                # Add request for student to view the captain's group
                request_entry = Request(
                    student_id=user.id,
                    captain_id=captain.id,
                    status='approved',
                    timestamp=datetime.utcnow()
                )
                db.session.add(request_entry)

        db.session.commit()
        return redirect(url_for('user_list'))

    return render_template('authorization/edit_user.html', user=user, institutes_captains=institutes_captains, current_captain_id=current_captain_id, message=message, message_type=message_type)
