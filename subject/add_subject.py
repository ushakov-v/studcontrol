from flask import render_template, request, redirect, url_for
from flask_login import current_user, login_required
from models import db, Subject, Teacher, User, Request
from get_current_semester import get_current_semester
import re


@login_required
def add_subject_route():
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

    # Проверяем, что текущий пользователь является владельцем или администратором
    if current_user.id != user.id and current_user.role != 'admin':
        return render_template('error.html', message='У вас нет прав на добавление предмета.')

    viewing_other_group = current_user.id != user_id

    message = None
    form_data = request.form.to_dict()
    teachers_data = []

    try:
        _, _, total_semesters = get_current_semester(user, 1)  # получение общего количества семестров
    except ValueError as e:
        return render_template('error.html', message=str(e))

    if request.method == 'POST':
        name = request.form['name']
        abbreviated_name = request.form['abbreviated_name']
        control = request.form['control']
        hours = request.form.get('hours', '').strip()
        if not hours:
            hours = 'Нет часов'
        semester = request.form['semester']

        # Валидация часов (только если заполнено и не "Нет часов")
        if hours != 'Нет часов' and not re.match(r'^\d+$', hours):
            message = 'Количество часов должно содержать только цифры.'
            return render_template('subject/add_subject.html', total_semesters=total_semesters, user_id=user.id,
                                   selected_semester=selected_semester, message=message, form_data=form_data,
                                   teachers_data=teachers_data, viewing_other_group=viewing_other_group)

        # Проверка на дублирующийся предмет для текущего пользователя
        existing_subject = Subject.query.filter_by(
            name=name, abbreviated_name=abbreviated_name, semester=semester, control=control, hours=hours,
            user_id=user.id
        ).first()
        if existing_subject:
            message = "Предмет с таким названием уже существует в этом семестре."
            return render_template('subject/add_subject.html', total_semesters=total_semesters, user_id=user.id,
                                   selected_semester=selected_semester, message=message, form_data=form_data,
                                   teachers_data=teachers_data, viewing_other_group=viewing_other_group)

        # Валидация преподавателей
        i = 1
        while True:
            teacher_name = request.form.get(f'teacher_name_{i}')
            academic_degree = request.form.get(f'academic_degree_{i}')
            academic_title = request.form.get(f'academic_title_{i}')

            if not teacher_name:
                break

            # Валидация имени преподавателя
            if not re.match(r'^[А-Яа-яЁё\s]+$', teacher_name):
                message = f'Имя преподавателя {i} должно содержать только буквы русского алфавита.'
                return render_template('subject/add_subject.html', total_semesters=total_semesters, user_id=user.id,
                                       selected_semester=selected_semester, message=message, form_data=form_data,
                                       teachers_data=teachers_data, viewing_other_group=viewing_other_group)

            teachers_data.append({
                'name': teacher_name,
                'academic_degree': academic_degree,
                'academic_title': academic_title,
            })
            i += 1

        # Создание нового предмета
        subject = Subject(name=name, abbreviated_name=abbreviated_name, semester=semester, control=control, hours=hours,
                          user_id=user.id)
        db.session.add(subject)
        db.session.commit()

        # Добавление преподавателей
        for teacher_data in teachers_data:
            teacher = Teacher(name=teacher_data['name'], academic_degree=teacher_data['academic_degree'],
                              academic_title=teacher_data['academic_title'],
                              subject_id=subject.id)
            db.session.add(teacher)

        db.session.commit()
        return redirect(url_for('subject_list', user_id=user.id, semester=semester))

    return render_template('subject/add_subject.html', total_semesters=total_semesters, user_id=user.id,
                           form_data=form_data, teachers_data=teachers_data, selected_semester=selected_semester,
                           viewing_other_group=viewing_other_group)