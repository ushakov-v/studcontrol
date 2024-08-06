from flask_mail import Mail, Message
from flask import current_app

mail = Mail()

def send_confirmation_email(temp_user):
    confirmation_code = temp_user.email_confirmation_code
    msg = Message(
        'Код подтверждения регистрации',
        sender=current_app.config['MAIL_USERNAME'],
        recipients=[temp_user.email]
    )
    msg.body = f'Ваш код подтверждения: {confirmation_code}. Пожалуйста, введите этот код для завершения регистрации.'
    mail.send(msg)
