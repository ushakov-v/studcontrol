from flask import request, render_template
from flask_login import login_required, current_user
from get_current_semester import get_current_semester
from models import Student, db, StudentSemester, User, Request
from datetime import datetime

@login_required
def student_list_route():
    selected_semester = request.args.get('semester', type=int, default=1)
    user_id = request.args.get('user_id', type=int, default=current_user.id)

    if current_user.role == 'student':
        request_entry = Request.query.filter_by(student_id=current_user.id, status='approved').order_by(
            Request.timestamp.desc()).first()
        if not request_entry:
            return render_template('error.html', message='Ваш запрос на просмотр группы не был одобрен.')
        user_id = request_entry.captain_id

    if current_user.role == 'chief':
        request_entry = Request.query.filter_by(student_id=current_user.id, status='approved').first()
        if not request_entry:
            return render_template('error.html', message='Ваш запрос на просмотр журналов не был одобрен администратором.')

    if current_user.role == 'captain':
        request_entry = Request.query.filter_by(student_id=current_user.id, status='approved').first()
        if not request_entry:
            return render_template('error.html', message='Ваш запрос на редактирование журнала посещаемости не был одобрен.')

        if user_id != current_user.id:
            return render_template('error.html', message='У вас нет доступа к этой группе.')

    user = User.query.get(user_id)
    if not user:
        return render_template('error.html', message='Пользователь не найден')

    is_owner_or_admin = user_id == current_user.id or current_user.role == 'admin'

    try:
        _, end_date, total_semesters = get_current_semester(user, selected_semester)
    except ValueError as e:
        return render_template('error.html', message=str(e))

    students = db.session.query(Student).join(StudentSemester).filter(
        StudentSemester.semester == selected_semester,
        StudentSemester.user_id == user_id
    ).order_by(Student.name).all()

    can_transfer = datetime.now().date() >= end_date

    viewing_other_group = current_user.id != user_id

    return render_template('student/student_list.html', students=students, selected_semester=selected_semester, total_semesters=total_semesters, can_transfer=can_transfer, user_id=user_id, is_owner_or_admin=is_owner_or_admin, viewing_attendance_user=user, viewing_other_group=viewing_other_group)
