from flask import request, render_template, redirect, url_for, session
from flask_login import login_user
from models import db, User

def change_password_route():
    message = None
    message_type = None
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        user_id = session.get('change_password_user_id_confirmed')
        if user_id:
            user = User.query.get(user_id)
            if user and password == confirm_password:
                user.set_password(password)
                db.session.commit()
                login_user(user)
                session.pop('change_password_user_id', None)
                session.pop('change_password_user_id_confirmed', None)
                message = 'Пароль успешно изменен.'
                message_type = 'success'
                return render_template('authorization/reset_password/change_password.html', message=message, message_type=message_type)
            else:
                message = 'Пароли не совпадают. Пожалуйста, попробуйте снова.'
                message_type = 'danger'
    return render_template('authorization/reset_password/change_password.html', message=message, message_type=message_type)
