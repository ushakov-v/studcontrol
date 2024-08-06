from flask_mail import Mail, Message
from flask import current_app

mail = Mail()

def send_password_reset_email(user):
    confirmation_code = user.email_confirmation_code
    msg = Message(
        'Сброс пароля',
        sender=current_app.config['MAIL_USERNAME'],
        recipients=[user.email]
    )
    msg.body = f'Ваш код для сброса пароля: {confirmation_code}. Пожалуйста, введите этот код, чтобы сбросить пароль.'
    mail.send(msg)
