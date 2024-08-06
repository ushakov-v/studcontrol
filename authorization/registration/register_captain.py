from flask import request, render_template, redirect, url_for, session
from datetime import datetime
import re
from models import TempUser, db, User
from send_email import send_confirmation_email
from generate_confirmation_code import generate_confirmation_code

def register_captain_route():
    message = None  # Инициализируем переменную для сообщения
    message_type = 'success'  # Устанавливаем тип сообщения по умолчанию
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email').strip().lower()  # Приводим к нижнему регистру для нечувствительности к регистру
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        institute = request.form.get('institute')
        role = request.form.get('role', 'captain')
        group = request.form.get('group').strip()
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')

        # Валидация ФИО
        if not re.match(r'^[А-Яа-яЁё\s-]+$', full_name):
            message = 'ФИО должно содержать только буквы русского алфавита.'
            message_type = 'danger'
            return render_template('authorization/registration/register_captain.html', message=message, message_type=message_type, full_name=full_name, email=email, institute=institute, role=role, group=group, start_date=start_date_str, end_date=end_date_str)

        # Валидация email
        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            message = 'Введите корректный email адрес.'
            message_type = 'danger'
            return render_template('authorization/registration/register_captain.html', message=message, message_type=message_type, full_name=full_name, email=email, institute=institute, role=role, group=group, start_date=start_date_str, end_date=end_date_str)

        # Валидация группы
        if not group.endswith('о') and not group.endswith('з') and not group.endswith('оз'):
            message = 'Название группы должно заканчиваться на "о", "з" или "оз".'
            message_type = 'danger'
            return render_template('authorization/registration/register_captain.html', message=message, message_type=message_type, full_name=full_name, email=email, institute=institute, role=role, group=group, start_date=start_date_str, end_date=end_date_str)

        # Проверка совпадения паролей
        if password != confirm_password:
            message = 'Пароли не совпадают.'
            message_type = 'danger'
            return render_template('authorization/registration/register_captain.html', message=message, message_type=message_type, full_name=full_name, email=email, institute=institute, role=role, group=group, start_date=start_date_str, end_date=end_date_str)

        # Преобразование строковых дат в объекты date
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            message = 'Неправильный формат даты.'
            message_type = 'danger'
            return render_template('authorization/registration/register_captain.html', message=message, message_type=message_type, full_name=full_name, email=email, institute=institute, role=role, group=group, start_date=start_date_str, end_date=end_date_str)

        # Проверка на существование группы в базе данных
        existing_group = User.query.filter(User.group == group).first()
        if existing_group:
            message = 'Пользователь с этой группой уже существует.'
            message_type = 'danger'
            return render_template('authorization/registration/register_captain.html', message=message, message_type=message_type, full_name=full_name, email=email, institute=institute, role=role, group=group, start_date=start_date_str, end_date=end_date_str)

        # Создание нового временного пользователя без проверки на уникальность email
        temp_user = TempUser(
            full_name=full_name,
            email=email,
            institute=institute,
            role=role,
            group=group,
            start_date=start_date,
            end_date=end_date,
            email_confirmation_code=generate_confirmation_code(),
            created_at=datetime.utcnow()
        )
        temp_user.set_password(password)
        db.session.add(temp_user)
        db.session.commit()
        send_confirmation_email(temp_user)  # Отправим подтверждающее письмо

        # Очистка cookies
        for key in list(session.keys()):
            session.pop(key)

        session['temp_user_id'] = temp_user.id  # Сохраняем temp_user_id в сессии
        return redirect(url_for('confirm_email_register_captain'))

    return render_template('authorization/registration/register_captain.html', message=message, message_type=message_type)
