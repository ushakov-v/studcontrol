from flask import Flask, render_template, request, redirect, url_for
from flask_login import login_required, current_user
from decorators import roles_required
from models import db, User, Request


@login_required
@roles_required('admin', 'chief')
def group_overview_route(user_id):
    user = User.query.get(user_id)
    if not user:
        return render_template('error.html', message='Пользователь не найден')

    if current_user.role == 'chief':
        request_entry = Request.query.filter_by(student_id=current_user.id, status='approved').first()
        if not request_entry:
            return render_template('error.html',
                                   message='Ваш запрос на просмотр журналов не был одобрен администратором.')

    return render_template('authorization/group_overview.html', group_name=user.group, user=user)
