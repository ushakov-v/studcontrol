from flask import request, redirect, url_for, render_template, session
from flask_login import login_required, current_user
from models import db, Student, StudentSemester, User

@login_required
def transfer_students_to_next_semester_route():
    user_id = request.args.get('user_id', type=int, default=current_user.id)

    user = User.query.get(user_id)
    if not user:
        session['message'] = 'Пользователь не найден.'
        session['message_type'] = 'danger'
        return redirect(url_for('student_list', semester=1))  # Перенаправление на первый семестр по умолчанию

    # Проверка на права доступа: администратор или владелец группы
    if current_user.role != 'admin' and current_user.id != user_id:
        session['message'] = 'У вас нет прав на выполнение этой операции.'
        session['message_type'] = 'danger'
        return redirect(url_for('student_list', semester=1, user_id=user_id))  # Перенаправление на первый семестр

    # Получаем всех студентов для текущего пользователя с их максимальными семестрами и подгруппами
    students_with_semester = db.session.query(
        Student,
        db.func.max(StudentSemester.semester).label('max_semester'),
        StudentSemester.subgroup
    ).join(StudentSemester).filter(
        StudentSemester.user_id == user_id,
        Student.expelled == False  # Исключаем отчисленных студентов
    ).group_by(Student.id, StudentSemester.subgroup).all()

    for student, current_semester, current_subgroup in students_with_semester:
        next_semester = current_semester + 1
        # Создание новой записи о семестре для студента с сохранением подгруппы
        new_student_semester = StudentSemester(
            student_id=student.id,
            semester=next_semester,
            user_id=user_id,
            subgroup=current_subgroup  # Перенос текущей подгруппы
        )
        db.session.add(new_student_semester)

    db.session.commit()
    session['message'] = "Студенты успешно перенесены в следующий семестр."
    session['message_type'] = 'success'
    # Перенаправляем на семестр, который был максимальным + 1
    return redirect(url_for('student_list', semester=next_semester, user_id=user_id))