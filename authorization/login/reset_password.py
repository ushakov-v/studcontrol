from flask import render_template, request, redirect, url_for, session
from models import User, db

def reset_password_route():
    message = None
    if request.method == 'POST':
        confirmation_code = request.form.get('confirmation_code')
        user_id = session.get('reset_user_id')
        if user_id:
            user = User.query.get(user_id)
            if user and user.email_confirmation_code == confirmation_code:
                session['reset_confirmed'] = True
                return redirect(url_for('set_new_password'))
        message = 'Неправильный код подтверждения.'
    return render_template('authorization/login/reset_password.html', message=message)
