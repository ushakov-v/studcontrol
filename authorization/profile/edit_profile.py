from flask import render_template, request, redirect, url_for, session
from flask_login import login_required, current_user, login_user
from datetime import datetime
import re
from models import db, User, Request, Message

@login_required
def edit_profile_route():
    user = User.query.get(current_user.id)
    message = None
    message_type = None

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

    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        institute = request.form.get('institute')
        captain_id = request.form.get('captain_id')

        if user.role != 'student':
            group = request.form.get('group')
            start_date_str = request.form.get('start_date')
            end_date_str = request.form.get('end_date')

        # Валидация ФИО
        if not re.match(r'^[А-Яа-яЁё\s-]+$', full_name):
            message = 'ФИО должно содержать только буквы русского алфавита.'
            message_type = 'danger'
            return render_template('authorization/profile/edit_profile.html', user=user, institutes_captains=institutes_captains,
                                   message=message, message_type=message_type)

        # Валидация email
        email_regex = r'^[^@]+@[^@]+\.[^@]+$'
        if not re.match(email_regex, email):
            message = 'Введите корректный email адрес.'
            message_type = 'danger'
            return render_template('authorization/profile/edit_profile.html', user=user, institutes_captains=institutes_captains,
                                   message=message, message_type=message_type)

        if user.role != 'student':
            try:
                if start_date_str:
                    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                else:
                    start_date = user.start_date

                if end_date_str:
                    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                else:
                    end_date = user.end_date
            except ValueError:
                message = 'Неправильный формат даты.'
                message_type = 'danger'
                return render_template('authorization/profile/edit_profile.html', user=user, institutes_captains=institutes_captains,
                                       message=message, message_type=message_type)

            if start_date >= end_date:
                message = 'Дата начала обучения должна быть раньше даты окончания.'
                message_type = 'danger'
                return render_template('authorization/profile/edit_profile.html', user=user, institutes_captains=institutes_captains,
                                       message=message, message_type=message_type)

        if full_name:
            user.full_name = full_name
        if email:
            user.email = email
        if institute and institute != user.institute:
            # Создание запроса на изменение института, если редактирует не староста
            if user.role == 'student':
                request_entry = Request(
                    student_id=user.id,
                    captain_id=captain_id,
                    institute=institute,
                    status='pending'
                )
                db.session.add(request_entry)
                db.session.commit()  # Сохраняем запрос, чтобы получить его id

                message = Message(
                    sender_id=user.id,
                    recipient_id=captain_id,
                    subject='Запрос на просмотр группы',
                    body=f'Студент {user.full_name} запрашивает доступ на просмотр Вашего журнала посещаемости.',
                    timestamp=datetime.utcnow(),
                    request_id=request_entry.id  # Устанавливаем request_id
                )
                db.session.add(message)
            else:
                user.institute = institute  # Обновляем институт без создания запроса, если редактирует староста

        if user.role != 'student' and group:
            user.group = group
        if user.role != 'student' and start_date_str:
            user.start_date = start_date
        if user.role != 'student' and end_date_str:
            user.end_date = end_date

        db.session.commit()

        if user.role == 'student':
            captain = User.query.get(captain_id)
            message = f'Запрос на просмотр группы {captain.group} успешно отправлен его старосте.'
            message_type = 'success'
        else:
            message = 'Профиль успешно обновлен.'
            message_type = 'success'

        return render_template('authorization/profile/edit_profile.html', user=user, institutes_captains=institutes_captains, message=message,
                               message_type=message_type)

    return render_template('authorization/profile/edit_profile.html', user=user, institutes_captains=institutes_captains)
