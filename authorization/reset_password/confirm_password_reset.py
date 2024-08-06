from flask import request, render_template, redirect, url_for, session
from models import db, User

def confirm_password_reset_route():
    message = None
    message_type = None
    if request.method == 'POST':
        confirmation_code = request.form.get('confirmation_code')
        user_id = session.get('change_password_user_id')
        if user_id:
            user = User.query.get(user_id)
            if user and user.email_confirmation_code == confirmation_code:
                session['change_password_user_id_confirmed'] = user.id
                return redirect(url_for('change_password'))
        message = 'Неправильный код подтверждения. Пожалуйста, попробуйте снова.'
        message_type = 'danger'
    return render_template('authorization/reset_password/confirm_password_reset.html', message=message, message_type=message_type)
