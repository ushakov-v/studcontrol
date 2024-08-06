from flask import request, redirect, url_for, render_template, session
from flask_login import login_required, current_user
from models import db, Student, StudentSemester, User

@login_required
def transfer_students_to_next_semester_route():
    current_semester = int(request.args.get('current_semester'))
    next_semester = current_semester + 1
    user_id = request.args.get('user_id', type=int, default=current_user.id)

    user = User.query.get(user_id)
    if not user:
        session['message'] = 'Пользователь не найден.'
        session['message_type'] = 'danger'
        return redirect(url_for('student_list', semester=current_semester))

    # Проверка на права доступа: администратор или владелец группы
    if current_user.role != 'admin' and current_user.id != user_id:
        session['message'] = 'У вас нет прав на выполнение этой операции.'
        session['message_type'] = 'danger'
        return redirect(url_for('student_list', semester=current_semester, user_id=user_id))

    students = db.session.query(Student).join(StudentSemester).filter(
        StudentSemester.semester == current_semester,
        StudentSemester.user_id == user_id,
        Student.expelled == False  # Исключаем отчисленных студентов
    ).all()

    for student in students:
        # Создание новой записи о семестре для студента
        new_student_semester = StudentSemester(
            student_id=student.id,
            semester=next_semester,
            user_id=user_id
        )
        db.session.add(new_student_semester)

    db.session.commit()
    session['message'] = "Студенты успешно перенесены в следующий семестр."
    session['message_type'] = 'success'
    return redirect(url_for('student_list', semester=next_semester, user_id=user_id))
