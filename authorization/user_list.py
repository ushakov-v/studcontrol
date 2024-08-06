from flask import render_template, request
from flask_login import login_required, current_user
from decorators import roles_required
from models import User, Request

@login_required
@roles_required('admin', 'chief')
def user_list_route():
    institute_filter = request.args.get('institute')
    role_filter = request.args.get('role')
    name_filter = request.args.get('name')  # Получаем параметр поиска по имени
    sort_by = request.args.get('sort_by', 'full_name')  # Получаем параметр сортировки из запроса

    if current_user.role == 'chief':
        request_entry = Request.query.filter_by(student_id=current_user.id, status='approved').first()
        if not request_entry:
            return render_template('error.html',
                                   message='Ваш запрос на просмотр журналов не был одобрен администратором.')

    query = User.query

    if institute_filter:
        query = query.filter_by(institute=institute_filter)

    if role_filter:
        query = query.filter_by(role=role_filter)

    if name_filter:
        query = query.filter(User.full_name.ilike(f'%{name_filter}%'))  # Добавляем фильтр по имени

    # Сортируем в зависимости от параметра сортировки
    if sort_by == 'group':
        query = query.order_by(User.group)
    else:
        query = query.order_by(User.full_name)

    users = query.all()

    # Получение старост для всех студентов
    student_captains = {}
    for user in users:
        if user.role == 'student':
            captain = User.query.filter_by(group=user.group, role='captain').first()
            if captain:
                student_captains[user.id] = captain.id

    return render_template('authorization/user_list.html', users=users, institute_filter=institute_filter, role_filter=role_filter, name_filter=name_filter, sort_by=sort_by, student_captains=student_captains)
