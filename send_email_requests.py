from flask_mail import Mail, Message
from flask import current_app, url_for

mail = Mail()

def send_email_requests(subject, recipient, body, endpoint=None, endpoint_params=None):
    msg = Message(
        subject,
        sender=current_app.config['MAIL_USERNAME'],
        recipients=[recipient]
    )
    if endpoint:
        with current_app.app_context():
            link = url_for(endpoint, **endpoint_params, _external=True)
            body += f"\n\nДля перехода в приложение, пожалуйста, нажмите на ссылку ниже:\n{link}"
    msg.body = body
    mail.send(msg)
