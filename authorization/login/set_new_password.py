from flask import render_template, request, redirect, url_for, session
from models import User, db
from flask_login import login_user

def set_new_password_route():
    message = None
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        if new_password == confirm_password:
            user_id = session.get('reset_user_id')
            if user_id and session.get('reset_confirmed'):
                user = User.query.get(user_id)
                if user:
                    user.set_password(new_password)
                    user.email_confirmation_code = None
                    db.session.commit()
                    login_user(user)
                    session.pop('reset_user_id', None)
                    session.pop('reset_confirmed', None)
                    return redirect(url_for('index'))
        else:
            message = 'Пароли не совпадают.'
    return render_template('authorization/login/set_new_password.html', message=message)