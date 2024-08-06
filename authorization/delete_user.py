from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from models import db, User  # Убедитесь, что у вас есть импорт модели User и базы данных


@login_required
def delete_user_route(user_id):
    user = User.query.get(user_id)
    db.session.delete(user)
    db.session.commit()
    return redirect(url_for('user_list'))

