from flask import render_template
from flask_login import current_user
from models import User, db


def profile_route():
    group_leader = None
    if current_user.role == 'student':
        group_leader = db.session.query(User).filter(
            User.role == 'captain',
            User.group == current_user.group
        ).first()
    return render_template('authorization/profile/profile.html', user=current_user, group_leader=group_leader)
