from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import Message, db
import pytz

@login_required
def inbox_route():
    if request.method == 'POST':
        selected_messages = request.form.getlist('selected_messages')
        if selected_messages:
            Message.query.filter(Message.id.in_(selected_messages), Message.recipient_id == current_user.id).delete(synchronize_session='fetch')
            db.session.commit()
            flash('Выбранные сообщения удалены.', 'success')
        return redirect(url_for('inbox'))

    messages = Message.query.filter_by(recipient_id=current_user.id).order_by(Message.timestamp.desc()).all()

    user_timezone = pytz.timezone('Europe/Moscow')

    for message in messages:
        message.local_timestamp = message.timestamp.replace(tzinfo=pytz.utc).astimezone(user_timezone)

    return render_template('authorization/messages/inbox.html', messages=messages)
