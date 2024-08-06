from flask import flash, redirect, url_for, make_response, request
from flask_login import logout_user


def logout_route():
    logout_user()
    return redirect(url_for('index'))