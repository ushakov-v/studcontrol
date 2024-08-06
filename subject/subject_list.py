from flask import render_template, request, session
from flask_login import current_user, login_required
from models import Subject, User, Request


@login_required
def subject_list_route():
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

    viewing_other_group = current_user.id != user_id

    # Определяем количество семестров на основе периода обучения пользователя
    start_year = user.start_date.year
    end_year = user.end_date.year
    total_semesters = (end_year - start_year) * 2

    # Проверяем, что выбранный семестр входит в диапазон
    if selected_semester < 1 or selected_semester > total_semesters:
        return render_template('error.html', message=f"Запрашиваемый семестр {selected_semester} выходит за пределы периода обучения.")

    subjects = Subject.query.filter_by(user_id=user_id, semester=selected_semester).order_by(Subject.name).all()

    semesters = list(range(1, total_semesters + 1))
    return render_template('subject/subject_list.html', subjects=subjects, semesters=semesters,
                           selected_semester=selected_semester, user_id=user_id, viewing_attendance_user=user,
                           viewing_other_group=viewing_other_group)
