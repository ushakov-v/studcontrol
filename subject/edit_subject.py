from flask import render_template, request, redirect, url_for
from flask_login import current_user, login_required
from models import db, Subject, Teacher, User, Request
from get_current_semester import get_current_semester
import re

@login_required
def edit_subject_route(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    user = User.query.get(subject.user_id)
    user_id = request.args.get('user_id', type=int, default=current_user.id)

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
    if subject.user_id != current_user.id and current_user.role != 'admin':
        return render_template('error.html', message='У вас нет прав на редактирование этого предмета.', viewing_attendance_user=user)

    viewing_other_group = current_user.id != user.id

    form_data = request.form.to_dict()
    teachers_data = []
    for i, teacher in enumerate(subject.teachers, start=1):
        teachers_data.append({
            'id': teacher.id,
            'name': teacher.name,
            'academic_degree': teacher.academic_degree,
            'academic_title': teacher.academic_title,
            'index': i
        })

    # Получение текущего семестра
    try:
        _, _, total_semesters = get_current_semester(user, 1)
    except ValueError as e:
        return render_template('error.html', message=str(e), viewing_attendance_user=user)

    if request.method == 'POST':
        new_name = request.form['name']
        new_abbreviated_name = request.form['abbreviated_name']
        new_semester = request.form['semester']
        new_control = request.form['control']
        new_hours = request.form['hours']

        # Валидация часов
        if not re.match(r'^\d+$', new_hours):
            error_message = 'Количество часов должно содержать только цифры.'
            return render_template('subject/edit_subject.html', subject=subject, error_message=error_message, total_semesters=total_semesters, viewing_attendance_user=user, teachers_data=teachers_data, form_data=form_data, user_id=user.id, viewing_other_group=viewing_other_group, selected_semester=subject.semester)

        # Проверка на дублирующийся предмет
        existing_subject = Subject.query.filter(
            Subject.id != subject_id,
            Subject.name == new_name,
            Subject.abbreviated_name == new_abbreviated_name,
            Subject.semester == new_semester,
            Subject.control == new_control,
            Subject.hours == new_hours,
            Subject.user_id == subject.user_id
        ).first()

        if existing_subject:
            error_message = "Предмет с таким названием уже существует в этом семестре."
            return render_template('subject/edit_subject.html', subject=subject, error_message=error_message, total_semesters=total_semesters, viewing_attendance_user=user, teachers_data=teachers_data, form_data=form_data, user_id=user.id, viewing_other_group=viewing_other_group, selected_semester=subject.semester)

        # Обновление данных предмета
        subject.name = new_name
        subject.abbreviated_name = new_abbreviated_name
        subject.semester = new_semester
        subject.control = new_control
        subject.hours = new_hours

        # Удаление преподавателей, если они были удалены на форме
        teachers_to_delete = request.form.getlist('delete_teacher')
        if teachers_to_delete:
            # Фильтрация пустых значений
            teachers_to_delete = [teacher_id for teacher_id in teachers_to_delete if teacher_id]
            if teachers_to_delete:
                Teacher.query.filter(Teacher.id.in_(teachers_to_delete)).delete(synchronize_session=False)

        # Обновление преподавателей
        i = 1
        while True:
            teacher_name = request.form.get(f'teacher_name_{i}')
            academic_degree = request.form.get(f'academic_degree_{i}')
            academic_title = request.form.get(f'academic_title_{i}')

            if not teacher_name:
                break

            teacher_id = request.form.get(f'teacher_id_{i}')
            if teacher_id:
                teacher = Teacher.query.get(teacher_id)
                teacher.name = teacher_name
                teacher.academic_degree = academic_degree
                teacher.academic_title = academic_title
            else:
                teacher = Teacher(name=teacher_name, academic_degree=academic_degree, academic_title=academic_title,
                                  subject_id=subject.id)
                db.session.add(teacher)

            teachers_data.append({
                'id': teacher.id if teacher_id else '',
                'name': teacher_name,
                'academic_degree': academic_degree,
                'academic_title': academic_title,
                'index': i
            })
            i += 1

        db.session.commit()
        return redirect(url_for('subject_list', user_id=subject.user_id, semester=new_semester))

    return render_template('subject/edit_subject.html', subject=subject, total_semesters=total_semesters, viewing_attendance_user=user, teachers_data=teachers_data, form_data=form_data, user_id=user.id, viewing_other_group=viewing_other_group, selected_semester=subject.semester)
