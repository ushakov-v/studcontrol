from flask import render_template, url_for
from flask_login import login_required, current_user
from models import Message, db

@login_required
def view_message_route(message_id):
    message = Message.query.get_or_404(message_id)

    if message.recipient_id != current_user.id:
        return render_template('error.html', message='У вас нет доступа к этому сообщению.')

    if not message.is_read:
        message.is_read = True
        db.session.commit()

    return render_template('authorization/messages/view_message.html', message=message)
