from flask import render_template, request, redirect, url_for, session, flash
from flask_login import login_user
from models import db, User, TempUser, Request, Message
from datetime import datetime
from send_email_requests import send_email_requests  # Импортируйте функцию send_email_requests

def confirm_email_register_student_route():
    if request.method == 'POST':
        confirmation_code = request.form.get('confirmation_code')
        temp_user_id = session.get('temp_user_id')
        captain_id = session.get('captain_id')  # Получаем ID старосты из сессии

        if temp_user_id:
            temp_user = TempUser.query.get(temp_user_id)
            if temp_user and temp_user.email_confirmation_code == confirmation_code:
                # Получаем все дублирующие записи по email, отсортированные по created_at в порядке убывания
                temp_users = TempUser.query.filter_by(email=temp_user.email).order_by(TempUser.created_at.desc()).all()
                if temp_users:
                    latest_temp_user = temp_users[0]
                    # Создаем постоянного пользователя на основе последнего временного пользователя
                    user = User(
                        full_name=latest_temp_user.full_name,
                        email=latest_temp_user.email,
                        institute=latest_temp_user.institute,
                        role=latest_temp_user.role,
                        group=latest_temp_user.group,
                        start_date=latest_temp_user.start_date,
                        end_date=latest_temp_user.end_date,
                        password=latest_temp_user.password  # Передаём хэшированный пароль напрямую
                    )
                    db.session.add(user)
                    db.session.commit()

                    # Создание запроса на одобрение старостой
                    request_entry = Request(
                        student_id=user.id,  # Используем постоянного пользователя
                        captain_id=captain_id,
                        institute=user.institute
                    )
                    db.session.add(request_entry)
                    db.session.commit()

                    message = Message(
                        sender_id=user.id,
                        recipient_id=captain_id,
                        subject='Запрос на просмотр группы',
                        body=f'Студент {user.full_name} зарегистрировался в системе и запрашивает доступ на просмотр Вашего журнала посещаемости.',
                        timestamp=datetime.utcnow(),
                        request_id=request_entry.id  # Устанавливаем request_id
                    )
                    db.session.add(message)

                    # Отправляем email старосте
                    captain = User.query.get(captain_id)
                    send_email_requests(
                        'Запрос на просмотр группы',
                        captain.email,
                        f'Студент {user.full_name} зарегистрировался в системе и запрашивает доступ на просмотр Вашего журнала посещаемости.',
                        endpoint='inbox',  # Указываем эндпоинт для ссылки
                        endpoint_params={}  # Параметры для эндпоинта
                    )

                    # Удаляем все временные записи
                    for temp_user in temp_users:
                        db.session.delete(temp_user)
                    db.session.commit()

                    # Входим в систему
                    login_user(user)

                    # Удаляем temp_user_id и captain_id из сессии
                    session.pop('temp_user_id', None)
                    session.pop('captain_id', None)

                    return redirect(url_for('index'))
        message = 'Неправильный код подтверждения. Пожалуйста, попробуйте снова.'
        return render_template('authorization/registration/confirm_email_register_student.html', message=message)

    return render_template('authorization/registration/confirm_email_register_student.html')
