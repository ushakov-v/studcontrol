from flask import redirect, url_for, request, render_template
from flask_login import login_required, current_user
from models import Attendance, db, Subject, User, Request
from datetime import datetime


@login_required
def delete_subject_attendance_route(subject_id, date):
    # Get the user_id from the request or default to the current user's id
    user_id = request.args.get('user_id', type=int, default=current_user.id)
    user = User.query.get(user_id)

    if not user:
        return render_template('error.html', message='Пользователь не найден')

    # Check permissions for the current user
    if current_user.id != user_id and current_user.role != 'admin':
        return render_template('error.html', message='У вас нет прав на выполнение этого действия.')

    if current_user.role == 'chief':
        request_entry = Request.query.filter_by(student_id=current_user.id, status='approved').first()
        if not request_entry:
            return render_template('error.html',
                                   message='Ваш запрос на просмотр журналов не был одобрен администратором.')

    if current_user.role == 'captain':
        request_entry = Request.query.filter_by(student_id=current_user.id, status='approved').first()
        if not request_entry:
            return render_template('error.html',
                                   message='Ваш запрос на редактирование журнала посещаемости не был одобрен.')

        if user_id != current_user.id:
            return render_template('error.html', message='У вас нет доступа к этой группе.')

    # Split the date string into date, study time, and activity
    selected_date_str, study_time, activity = date.split(' - ')

    # Parse the date from string format
    selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()

    # Fetch the subject by its ID
    subject = Subject.query.get(subject_id)

    # Ensure subject exists
    if not subject:
        return render_template('error.html', message='Предмет не найден')

    # Delete attendance records that match the criteria using subject_id
    Attendance.query.filter_by(subject_id=subject.id, date=selected_date, study_time=study_time, activity=activity,
                               user_id=user_id).delete()
    db.session.commit()

    # Redirect to the view subject attendance page
    return redirect(url_for('view_subject_attendance', subject_id=subject_id, user_id=user_id))
