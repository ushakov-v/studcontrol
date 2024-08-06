from flask import request, render_template, url_for, redirect
from flask_login import current_user, login_required
from get_current_semester import get_current_semester
from models import db, Student, StudentSemester, User, Request
import re


@login_required
def add_student_route():
    selected_semester = request.args.get('semester', type=int, default=1)
    user_id = request.args.get('user_id', type=int, default=current_user.id)

    user = User.query.get(user_id)
    if not user:
        return render_template('error.html', message='Пользователь не найден')

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

    # Проверка, что только владелец или администратор может добавлять студентов
    if current_user.id != user_id and current_user.role != 'admin':
        return render_template('error.html', message='У вас нет прав на добавление студентов в эту группу.')

    viewing_other_group = current_user.id != user_id

    # Получаем текущее количество семестров
    try:
        _, _, total_semesters = get_current_semester(user, selected_semester)
    except ValueError as e:
        return render_template('errors/error.html', message=str(e))

    message = None
    message_type = None
    form_data = request.form.to_dict()

    if request.method == 'POST':
        name = request.form['name']
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        subgroup = request.form['subgroup']
        semester = request.form['semester']  # Получаем выбранный семестр из формы

        # Валидация email
        if email and not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            message = 'Введите корректный email адрес.'
            message_type = 'danger'
            return render_template('student/add_student.html', selected_semester=selected_semester,
                                   total_semesters=total_semesters, user_id=user_id, viewing_attendance_user=user,
                                   message=message, message_type=message_type, form_data=form_data,
                                   viewing_other_group=viewing_other_group)

        # Валидация имени
        if not re.match(r'^[А-Яа-яЁё\s-]+$', name):
            message = 'Имя должно содержать только буквы русского алфавита.'
            message_type = 'danger'
            return render_template('student/add_student.html', selected_semester=selected_semester,
                                   total_semesters=total_semesters, user_id=user_id, viewing_attendance_user=user,
                                   message=message, message_type=message_type, form_data=form_data,
                                   viewing_other_group=viewing_other_group)

        # Валидация телефона
        if phone and not re.match(r'^\+?\d{10,15}$', phone):
            message = 'Введите корректный номер телефона.'
            message_type = 'danger'
            return render_template('student/add_student.html', selected_semester=selected_semester,
                                   total_semesters=total_semesters, user_id=user_id, viewing_attendance_user=user,
                                   message=message, message_type=message_type, form_data=form_data,
                                   viewing_other_group=viewing_other_group)

        # Проверка на дублирующегося студента для текущего пользователя и выбранного семестра
        existing_student = db.session.query(Student).join(StudentSemester).filter(
            Student.name == name,
            Student.user_id == user_id,
            StudentSemester.semester == semester
        ).first()
        if existing_student:
            message = "Студент с таким именем уже существует в списке в выбранном семестре."
            message_type = 'danger'
            return render_template('student/add_student.html', selected_semester=selected_semester,
                                   total_semesters=total_semesters, user_id=user_id, viewing_attendance_user=user,
                                   message=message, message_type=message_type, form_data=form_data,
                                   viewing_other_group=viewing_other_group)

        # Создание нового студента
        new_student = Student(
            name=name,
            email=email,
            phone=phone,
            subgroup=subgroup,
            user_id=user_id  # Позволяет одному пользователю иметь несколько студентов
        )
        db.session.add(new_student)
        db.session.commit()

        # Создание записи о семестре для студента
        student_semester = StudentSemester(
            student_id=new_student.id,
            semester=semester,  # Используем выбранный семестр
            user_id=user_id
        )
        db.session.add(student_semester)
        db.session.commit()

        return redirect(url_for('student_list', semester=semester, user_id=user_id))

    return render_template('student/add_student.html', selected_semester=selected_semester,
                           total_semesters=total_semesters, user_id=user_id, viewing_attendance_user=user,
                           message=message, message_type=message_type, form_data=form_data,
                           viewing_other_group=viewing_other_group)
