from flask_mail import Mail, Message
from flask import current_app

mail = Mail()

def password_change_email(user):
    confirmation_code = user.email_confirmation_code
    msg = Message(
        'Смена пароля',
        sender=current_app.config['MAIL_USERNAME'],
        recipients=[user.email]
    )
    msg.body = f'Ваш код для смены пароля: {confirmation_code}. Пожалуйста, введите этот код, чтобы сменить пароль.'
    mail.send(msg)
