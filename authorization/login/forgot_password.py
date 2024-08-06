from flask import render_template, request, redirect, url_for, session
from models import User, db
from send_password_reset_email import send_password_reset_email
from generate_confirmation_code import generate_confirmation_code
import re


def forgot_password_route():
    message = None
    if request.method == 'POST':
        email = request.form.get('email').strip().lower()

        # Серверная валидация email
        email_regex = r'^[^@]+@[^@]+\.[^@]+$'
        if not re.match(email_regex, email):
            message = 'Некорректный формат электронной почты.'
            return render_template('authorization/login/forgot_password.html', message=message)

        user = User.query.filter(User.email.ilike(email)).first()
        if user:
            confirmation_code = generate_confirmation_code()
            user.email_confirmation_code = confirmation_code
            db.session.commit()
            send_password_reset_email(user)
            session['reset_user_id'] = user.id
            return redirect(url_for('reset_password'))
        else:
            message = 'Пользователь с такой электронной почтой не найден.'
    return render_template('authorization/login/forgot_password.html', message=message)
