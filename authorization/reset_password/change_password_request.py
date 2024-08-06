from flask import request, render_template, redirect, url_for, session, flash
from flask_login import login_required, current_user
from models import db, User
from password_change_email import password_change_email
from generate_confirmation_code import generate_confirmation_code

@login_required
def change_password_request_route():
    user = current_user
    user.email_confirmation_code = generate_confirmation_code()
    db.session.commit()
    password_change_email(user)
    session['change_password_user_id'] = user.id
    return redirect(url_for('confirm_password_reset'))
