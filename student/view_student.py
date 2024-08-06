from flask import render_template, request, session
from flask_login import login_required, current_user
from models import Student, Attendance, User, RemoteLearningDate, db, Request


@login_required
def view_student_route(student_id):
    user_id = request.args.get('user_id', type=int, default=current_user.id)
    selected_semester = request.args.get('semester', type=int, default=1)

    if current_user.role == 'student':
        request_entry = Request.query.filter_by(student_id=current_user.id, status='approved').order_by(
            Request.timestamp.desc()).first()
        if not request_entry:
            return render_template('error.html', message='Ваш запрос на просмотр группы не был одобрен.')
        user_id = request_entry.captain_id

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

    user = User.query.get(user_id)
    if not user:
        return render_template('error.html', message='Пользователь не найден')

    student = Student.query.filter_by(id=student_id, user_id=user_id).first()
    remote_learning_dates = RemoteLearningDate.query.filter_by(student_id=student_id).all()

    # Форматируем даты ДО
    formatted_remote_learning_dates = [
        f"с {period.start_date.strftime('%d.%m.%Y')} по {period.end_date.strftime('%d.%m.%Y')}"
        for period in remote_learning_dates
    ]

    viewing_other_group = current_user.id != user_id

    if student:
        total_absences = Attendance.query.filter_by(student_id=student_id, status='Absent').count()
        unexcused_absences = Attendance.query.filter_by(student_id=student_id, status='Absent').filter(
            Attendance.status != 'Excused').count()
        return render_template('student/view_student.html', student=student, total_absences=total_absences,
                               unexcused_absences=unexcused_absences, user_id=user_id, viewing_attendance_user=user,
                               remote_learning_dates=formatted_remote_learning_dates, viewing_other_group=viewing_other_group, selected_semester=selected_semester)
    else:
        return render_template('error.html', message='Студент не найден')
