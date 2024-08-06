from datetime import datetime
from flask import redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Request, User, Message
from send_email_requests import send_email_requests

@login_required
def reject_request_route(request_id):
    request_entry = Request.query.get_or_404(request_id)

    if request_entry.status == 'rejected':
        flash('Запрос уже был отклонен.', 'warning')
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
        request_entry.status = 'rejected'
        db.session.commit()

        student = User.query.get(request_entry.student_id)

        email_subject = 'Запрос отклонён'
        email_body = ''

        if current_user.role == 'captain' and request_entry.captain_id == current_user.id:
            # Отклонение запроса на просмотр группы старосты студентом
            message = Message(
                sender_id=current_user.id,
                recipient_id=student.id,
                subject=email_subject,
                body='Ваш запрос на просмотр группы был отклонён старостой.',
                timestamp=datetime.utcnow()
            )
            db.session.add(message)

            email_body = 'Ваш запрос на просмотр группы был отклонён старостой.'

        if current_user.role in ['admin', 'chief'] and student.role == 'captain':
            # Отклонение доступа к журналу старосте
            message = Message(
                sender_id=current_user.id,
                recipient_id=student.id,
                subject=email_subject,
                body='Ваш запрос на доступ к журналу старосты был отклонён.',
                timestamp=datetime.utcnow()
            )
            db.session.add(message)

            email_body = 'Ваш запрос на доступ к журналу старосты был отклонён.'

        if current_user.role == 'admin' and student.role == 'chief':
            message = Message(
                sender_id=current_user.id,
                recipient_id=student.id,
                subject=email_subject,
                body='Ваш запрос на доступ ко всем журналам старост был отклонён администратором.',
                timestamp=datetime.utcnow()
            )
            db.session.add(message)

            email_body = 'Ваш запрос на доступ ко всем журналам старост был отклонён администратором.'

        db.session.commit()

        # Отправляем email
        send_email_requests(
            email_subject,
            student.email,
            email_body,
            endpoint='index',  # Указываем эндпоинт для ссылки
            endpoint_params={}  # Параметры для эндпоинта
        )

        flash('Запрос отклонён.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Произошла ошибка при отклонении запроса: {str(e)}', 'danger')

    return redirect(url_for('manage_requests'))
