from flask import request, render_template, redirect, url_for, session
from datetime import datetime
import re
from models import TempUser, db, User
from send_email import send_confirmation_email
from generate_confirmation_code import generate_confirmation_code

def register_student_route():
    message = None
    message_type = 'success'
    captains = User.query.filter_by(role='captain').all()

    # Создаем структуру данных для старост по институтам
    institutes_captains = {}
    for captain in captains:
        if captain.institute not in institutes_captains:
            institutes_captains[captain.institute] = []
        institutes_captains[captain.institute].append({
            "id": captain.id,
            "full_name": captain.full_name,
            "group": captain.group,
            "start_date": captain.start_date.strftime('%Y-%m-%d'),
            "end_date": captain.end_date.strftime('%Y-%m-%d')
        })

    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email').strip().lower()
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        institute = request.form.get('institute')
        role = request.form.get('role', 'student')
        captain_id = request.form.get('captain_id')

        # Получаем данные старосты
        captain = User.query.get(captain_id)
        if not captain:
            message = 'Выбранный староста не найден.'
            message_type = 'danger'
            return render_template('authorization/registration/register_student.html', message=message, message_type=message_type, full_name=full_name, email=email, institute=institute, institutes_captains=institutes_captains)

        group = captain.group
        start_date = captain.start_date
        end_date = captain.end_date

        # Валидация ФИО
        if not re.match(r'^[А-Яа-яЁё\s-]+$', full_name):
            message = 'ФИО должно содержать только буквы русского алфавита.'
            message_type = 'danger'
            return render_template('authorization/registration/register_student.html', message=message, message_type=message_type, full_name=full_name, email=email, institute=institute, institutes_captains=institutes_captains)

        # Валидация email
        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            message = 'Введите корректный email адрес.'
            message_type = 'danger'
            return render_template('authorization/registration/register_student.html', message=message, message_type=message_type, full_name=full_name, email=email, institute=institute, institutes_captains=institutes_captains)

        # Проверка совпадения паролей
        if password != confirm_password:
            message = 'Пароли не совпадают.'
            message_type = 'danger'
            return render_template('authorization/registration/register_student.html', message=message, message_type=message_type, full_name=full_name, email=email, institute=institute, institutes_captains=institutes_captains)

        # Создание нового временного пользователя
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
        send_confirmation_email(temp_user)

        # Очистка cookies
        for key in list(session.keys()):
            session.pop(key)

        session['temp_user_id'] = temp_user.id
        session['captain_id'] = captain_id  # Сохраняем ID старосты в сессии
        return redirect(url_for('confirm_email_register_student'))

    return render_template('authorization/registration/register_student.html', message=message, message_type=message_type, institutes_captains=institutes_captains)
