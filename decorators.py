from functools import wraps
from flask import abort, flash, redirect, url_for, render_template
from flask_login import current_user

def role_required(role):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Вам нужно войти в систему для доступа к этой странице.', 'warning')
                return redirect(url_for('login'))
            if current_user.role != role:
                return render_template('error.html', message='У вас нет прав на выполнение этого действия.')
            return func(*args, **kwargs)
        return wrapper
    return decorator

def roles_required(*roles):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Вам нужно войти в систему для доступа к этой странице.', 'warning')
                return redirect(url_for('login'))
            if current_user.role not in roles:
                return render_template('error.html', message='У вас нет прав на выполнение этого действия.')
            return func(*args, **kwargs)
        return wrapper
    return decorator
