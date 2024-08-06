from datetime import datetime
from flask import redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Request, User, Message
from send_email_requests import send_email_requests  # Импортируйте функцию send_email из email_utils

@login_required
def approve_request_route(request_id):
    request_entry = Request.query.get_or_404(request_id)

    if request_entry.status == 'approved':
        flash('Запрос уже был одобрен.', 'warning')
        return redirect(url_for('manage_requests'))

    if current_user.role not in ['admin', 'chief', 'captain']:
        flash('У вас нет прав на выполнение этого действия.', 'danger')
        return redirect(url_for('manage_requests'))

    # Проверка прав для капитанов
    if current_user.role == 'captain' and request_entry.captain_id != current_user.id:
        flash('У вас нет прав на выполнение этого действия.', 'danger')
        return redirect(url_for('manage_requests'))

    if current_user.role == 'chief' and current_user.institute != request_entry.institute:
        flash('У вас нет прав на выполнение этого действия.', 'danger')
        return redirect(url_for('manage_requests'))

    try:
        # Обновляем статус запроса
        request_entry.status = 'approved'
        db.session.commit()

        student = User.query.get(request_entry.student_id)

        email_subject = 'Запрос одобрен'
        email_body = ''

        if current_user.role == 'captain':
            if request_entry.captain_id == current_user.id:
                # Одобрение просмотра группы старосты студентом
                student.institute = request_entry.institute
                student.group = current_user.group
                student.start_date = current_user.start_date
                student.end_date = current_user.end_date

                # Отправка сообщения студенту об одобрении
                message = Message(
                    sender_id=current_user.id,
                    recipient_id=student.id,
                    subject=email_subject,
                    body='Ваш запрос на просмотр группы был одобрен старостой.',
                    timestamp=datetime.utcnow()
                )
                db.session.add(message)

                email_body = 'Ваш запрос на просмотр группы был одобрен старостой.'

        if current_user.role in ['admin', 'chief'] and student.role == 'captain':
            # Одобрение доступа к журналу старосте
            student.role = 'captain'  # Обновляем роль студента на старосту

            message = Message(
                sender_id=current_user.id,
                recipient_id=student.id,
                subject=email_subject,
                body='Ваш запрос на доступ к журналу старосты был одобрен.',
                timestamp=datetime.utcnow()
            )
            db.session.add(message)

            email_body = 'Ваш запрос на доступ к журналу старосты был одобрен.'

        if current_user.role == 'admin' and student.role == 'chief':
            student.role = 'chief'

            message = Message(
                sender_id=current_user.id,
                recipient_id=student.id,
                subject=email_subject,
                body='Ваш запрос на доступ ко всем журналам старост был одобрен администратором.',
                timestamp=datetime.utcnow()
            )
            db.session.add(message)

            email_body = 'Ваш запрос на доступ ко всем журналам старост был одобрен администратором.'

        # Удаляем запрос для других пользователей
        if current_user.role in ['admin', 'chief']:
            other_requests = Request.query.filter(
                Request.id != request_id,
                Request.student_id == request_entry.student_id,
                Request.status == 'pending'
            ).all()
            for req in other_requests:
                req.status = 'removed'
                db.session.commit()

        db.session.commit()

        # Отправляем email
        send_email_requests(
            email_subject,
            student.email,
            email_body,
            endpoint='index',  # Указываем эндпоинт для ссылки
            endpoint_params={}  # Параметры для эндпоинта
        )

        flash('Запрос одобрен.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Произошла ошибка при одобрении запроса: {str(e)}', 'danger')

    return redirect(url_for('manage_requests'))
