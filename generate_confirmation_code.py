from flask_mail import Mail
import random

mail = Mail()

def generate_confirmation_code():
    return str(random.randint(100000, 999999))