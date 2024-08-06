from flask import redirect, url_for, request, render_template
from flask_login import current_user, login_required
from models import db, Student, StudentSemester, Attendance, User

@login_required
def delete_student_route(student_id):
    selected_semester = request.args.get('semester', type=int, default=1)

    # Получаем студента и его владельца
    student = Student.query.get_or_404(student_id)
    owner = User.query.get(student.user_id)

    # Проверяем, что текущий пользователь является владельцем или администратором
    if current_user.id != owner.id and current_user.role != 'admin':
        return render_template('error.html', message='У вас нет прав на удаление этого студента.')

    if student:
        # Удаление записей посещаемости студента
        Attendance.query.filter_by(student_id=student.id).delete()

        # Удаление записей студента в таблице StudentSemester
        StudentSemester.query.filter_by(student_id=student.id, user_id=owner.id).delete()

        # Удаление самого студента
        db.session.delete(student)
        db.session.commit()

    return redirect(url_for('student_list', semester=selected_semester, user_id=owner.id))
