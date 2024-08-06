from flask import redirect, url_for, render_template, request
from flask_login import current_user, login_required
from models import db, Subject, Attendance, Teacher

@login_required
def delete_subject_route(subject_id):
    selected_semester = request.args.get('semester', type=int, default=1)

    subject = Subject.query.get_or_404(subject_id)

    # Проверяем, что текущий пользователь является владельцем или администратором
    if subject.user_id != current_user.id and current_user.role != 'admin':
        return render_template('error.html', message='У вас нет прав на удаление этого предмета.')

    # Удаление записей о посещаемости для данного предмета
    attendances = Attendance.query.filter_by(subject=subject.name).all()
    for attendance in attendances:
        db.session.delete(attendance)

    # Удаление записей преподавателей для данного предмета
    teachers = Teacher.query.filter_by(subject_id=subject.id).all()
    for teacher in teachers:
        db.session.delete(teacher)

    # Удаление самого предмета
    db.session.delete(subject)
    db.session.commit()

    return redirect(url_for('subject_list', user_id=subject.user_id, semester=selected_semester))
