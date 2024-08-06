import re
from flask import request, render_template, redirect, url_for
from flask_login import login_user
from models import User

def login_route():
    message = None  # Инициализируем переменную для сообщения
    if request.method == 'POST':
        email = request.form.get('email').strip().lower()

        # Серверная валидация email
        email_regex = r'^[^@]+@[^@]+\.[^@]+$'
        if not re.match(email_regex, email):
            message = 'Некорректный формат электронной почты.'
            return render_template('authorization/login/login.html', message=message)

        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            message = 'Вход выполнен успешно!'
            return redirect(url_for('index', message=message))
        else:
            message = 'Неправильный email или пароль.'

    return render_template('authorization/login/login.html', message=message)
