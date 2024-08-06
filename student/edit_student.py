from flask import request, render_template, url_for, redirect
from flask_login import current_user, login_required
from get_current_semester import get_current_semester
from models import db, Student, StudentSemester, User, Request
import re

@login_required
def edit_student_route(student_id):
    selected_semester = request.args.get('semester', type=int, default=1)
    user_id = request.args.get('user_id', type=int, default=current_user.id)

    # Получаем студента и его владельца
    student = Student.query.get_or_404(student_id)
    owner = User.query.get(student.user_id)
    user = User.query.get_or_404(student.user_id)

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

    # Проверяем, что текущий пользователь является владельцем или администратором
    if current_user.id != owner.id and current_user.role != 'admin':
        return render_template('error.html', message='У вас нет прав на редактирование этого студента.')

    viewing_other_group = current_user.id != owner.id

    # Получаем текущее количество семестров
    try:
        _, _, total_semesters = get_current_semester(owner, selected_semester)
    except ValueError as e:
        return render_template('errors/error.html', message=str(e))

    message = None
    message_type = None
    form_data = request.form.to_dict()

    if request.method == 'POST':
        new_name = request.form['name']
        new_email = request.form.get('email', '').strip().lower()
        new_phone = request.form.get('phone', '').strip()
        new_subgroup = request.form['subgroup']
        new_semester = request.form['semester']

        # Валидация email
        if new_email and not re.match(r'^[^@]+@[^@]+\.[^@]+$', new_email):
            message = 'Введите корректный email адрес.'
            message_type = 'danger'
            return render_template('student/edit_student.html', student=student, selected_semester=selected_semester,
                                   total_semesters=total_semesters, message=message, message_type=message_type, form_data=form_data, viewing_other_group=viewing_other_group)

        # Валидация имени
        if not re.match(r'^[А-Яа-яЁё\s-]+$', new_name):
            message = 'Имя должно содержать только буквы русского алфавита.'
            message_type = 'danger'
            return render_template('student/edit_student.html', student=student, selected_semester=selected_semester,
                                   total_semesters=total_semesters, message=message, message_type=message_type, form_data=form_data, viewing_other_group=viewing_other_group)

        # Валидация телефона
        if new_phone and not re.match(r'^\+?\d{10,15}$', new_phone):
            message = 'Введите корректный номер телефона.'
            message_type = 'danger'
            return render_template('student/edit_student.html', student=student, selected_semester=selected_semester,
                                   total_semesters=total_semesters, message=message, message_type=message_type, form_data=form_data, viewing_other_group=viewing_other_group)

        # Проверка на дублирующегося студента, исключая текущего редактируемого студента
        existing_student = db.session.query(Student).join(StudentSemester).filter(
            Student.id != student_id,
            Student.name == new_name,
            Student.user_id == owner.id,
            StudentSemester.semester == new_semester
        ).first()

        if existing_student:
            message = "Студент с таким именем уже существует в вашем списке в текущем семестре."
            message_type = 'danger'
            return render_template('student/edit_student.html', student=student, selected_semester=selected_semester,
                                   total_semesters=total_semesters, message=message, message_type=message_type, form_data=form_data, viewing_other_group=viewing_other_group)

        # Обновление студента
        student.name = new_name
        student.email = new_email
        student.phone = new_phone
        student.subgroup = new_subgroup

        # Обновление семестра студента
        student_semester = StudentSemester.query.filter_by(student_id=student_id, semester=new_semester).first()
        if not student_semester:
            student_semester = StudentSemester(student_id=student_id, semester=new_semester, user_id=owner.id)
            db.session.add(student_semester)

        db.session.commit()
        return redirect(url_for('student_list', semester=selected_semester, user_id=owner.id))


    return render_template('student/edit_student.html', student=student, selected_semester=selected_semester,
                           total_semesters=total_semesters, user_id=owner.id, viewing_attendance_user=user,
                           message=message, message_type=message_type, form_data=form_data, viewing_other_group=viewing_other_group)
