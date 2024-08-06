import pytz
from flask import redirect, url_for, render_template
from flask_login import login_required, current_user
from models import db, Request, User, Message


@login_required
def manage_requests_route():
    requests = Request.query.filter_by(captain_id=current_user.id, status='pending').order_by(Request.timestamp.desc()).all()

    # Предположим, что временная зона пользователя хранится в атрибуте user.timezone
    user_timezone = pytz.timezone('Europe/Moscow')  # Замените на нужную временную зону

    # Преобразование времени сообщений в локальное время
    for request in requests:
        request.local_timestamp = request.timestamp.replace(tzinfo=pytz.utc).astimezone(user_timezone)

    return render_template('authorization/messages/manage_requests.html', requests=requests)



