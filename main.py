import atexit
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, render_template
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, current_user
from flask_migrate import Migrate
from models import db, User, create_admin_user, TempUser, Message
from authorization.registration.register_chief import register_chief_route
from authorization.registration.register_captain import register_captain_route
from authorization.registration.register_student import register_student_route
from authorization.login.login import login_route
from authorization.profile.logout import logout_route
from authorization.profile.profile import profile_route
from authorization.user_list import user_list_route
from authorization.profile.edit_profile import edit_profile_route
from authorization.profile.delete_profile import delete_profile_route
from authorization.edit_user import edit_user_route
from authorization.delete_user import delete_user_route
from student.student_list import student_list_route
from student.add_student import add_student_route
from student.view_student import view_student_route
from student.edit_student import edit_student_route
from student.delete_student import delete_student_route
from subject.subject_list import subject_list_route
from subject.add_subject import add_subject_route
from subject.edit_subject import edit_subject_route
from subject.delete_subject import delete_subject_route
from attendance.attendance import manage_attendance_route
from attendance.view_subject_attendance import view_subject_attendance_route
from attendance.edit_subject_attendance import edit_subject_attendance_route
from attendance.delete_subject_attendance import delete_subject_attendance_route
from attendance.week_attendance_table import week_attendance_table_route
from attendance.student_week_attendance import student_week_attendance_route
from attendance.subject_week_attendance import subject_week_attendance_route
from attendance.export_attendance_excel import export_attendance_excel_route
from toggle_remote_learning import toggle_remote_learning_route
from transfer_students_to_next_semester import transfer_students_to_next_semester_route
from toggle_expel_student import toggle_expel_student_route
from send_email import send_confirmation_email, mail
from authorization.registration.confirm_email_register_student import confirm_email_register_student_route
from authorization.registration.confirm_email_register_chief import confirm_email_register_chief_route
from authorization.registration.confirm_email_register_captain import confirm_email_register_captain_route
from authorization.login.forgot_password import forgot_password_route
from authorization.login.reset_password import reset_password_route
from authorization.login.set_new_password import set_new_password_route
from authorization.reset_password.change_password import change_password_route
from authorization.reset_password.confirm_password_reset import confirm_password_reset_route
from authorization.reset_password.change_password_request import change_password_request_route
from authorization.group_overview import group_overview_route
from authorization.messages.inbox import inbox_route
from authorization.messages.view_message import view_message_route
from authorization.messages.manage_requests import manage_requests_route
from authorization.messages.approve_request import approve_request_route
from authorization.messages.reject_request import reject_request_route
from authorization.transfer_captain_rights import transfer_captain_rights_route
from flask_wtf.csrf import CSRFProtect

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres.uhlsmwbpyueirzgvnfzo:Ushakov_v123@aws-0-eu-central-1.pooler.supabase.com:6543/postgres'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = '*\xba\x85\x9b\x9e\xf9\xe1\x88\x06\xb7\x1d\xc1\x06K\xab1\xfb\xc6\xa4\xd1@n\xed\x8f'
app.config['MAIL_SERVER'] = 'smtp.yandex.ru'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USERNAME'] = 'studcontrolapp@yandex.ru'
app.config['MAIL_PASSWORD'] = 'xnjuzpcuavbbfpal'

db.init_app(app)
mail.init_app(app)
migrate = Migrate(app, db)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# # CSRF защита
# csrf = CSRFProtect(app)

# Создание всех таблиц, если они не существуют
with app.app_context():
    db.create_all()
    create_admin_user()  # Создаем администратора, если его нет в базе

# Функция загрузки пользователя
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.context_processor
def inject_user():
    if current_user.is_authenticated:
        has_new_messages = Message.query.filter_by(recipient_id=current_user.id, is_read=False).count() > 0
    else:
        has_new_messages = False
    return dict(has_new_messages=has_new_messages)

# Главная страница index.html
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/privacy_policy')
def privacy_policy():
    return render_template('privacy_policy.html')

def delete_old_temp_users():
    with app.app_context():
        threshold_date = datetime.now() - timedelta(days=1)
        TempUser.query.filter(TempUser.created_at < threshold_date).delete()
        db.session.commit()

scheduler = BackgroundScheduler()
scheduler.add_job(func=delete_old_temp_users, trigger="interval", hours=24)
scheduler.start()

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())

# Добавление HTTP заголовков для безопасности
@app.after_request
def apply_security_headers(response):
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = (
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' "
        "https://code.jquery.com https://maxcdn.bootstrapcdn.com "
        "https://cdnjs.cloudflare.com https://stackpath.bootstrapcdn.com; "
        "img-src 'self' data:; "
        "font-src 'self' data:; "
        "connect-src 'self';"
    )
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response

# Маршруты
app.add_url_rule('/register_chief', 'register_chief', register_chief_route, methods=['GET', 'POST'])
app.add_url_rule('/register_captain', 'register_captain', register_captain_route, methods=['GET', 'POST'])
app.add_url_rule('/register_student', 'register_student', register_student_route, methods=['GET', 'POST'])
app.add_url_rule('/login', 'login', login_route, methods=['GET', 'POST'])
app.add_url_rule('/logout', 'logout', logout_route)
app.add_url_rule('/profile', 'profile', profile_route)
app.add_url_rule('/user_list', 'user_list', user_list_route)
app.add_url_rule('/edit_profile', 'edit_profile', edit_profile_route, methods=['GET', 'POST'])
app.add_url_rule('/delete_profile', 'delete_profile', delete_profile_route, methods=['POST'])
app.add_url_rule('/edit_user/<int:user_id>', 'edit_user', edit_user_route, methods=['GET', 'POST'])
app.add_url_rule('/delete_user/<int:user_id>', 'delete_user', delete_user_route, methods=['POST'])
app.add_url_rule('/student_list', 'student_list', student_list_route, methods=['GET', 'POST'])
app.add_url_rule('/add_student', 'add_student', add_student_route, methods=['GET', 'POST'])
app.add_url_rule('/view_student/<int:student_id>', 'view_student', view_student_route)
app.add_url_rule('/edit_student/<int:student_id>', 'edit_student', edit_student_route, methods=['GET', 'POST'])
app.add_url_rule('/delete_student/<int:student_id>', 'delete_student', delete_student_route)
app.add_url_rule('/attendance', 'attendance', manage_attendance_route, methods=['GET', 'POST'])
app.add_url_rule('/subject_list', 'subject_list', subject_list_route, methods=['GET', 'POST'])
app.add_url_rule('/add_subject', 'add_subject', add_subject_route, methods=['GET', 'POST'])
app.add_url_rule('/edit_subject/<int:subject_id>', 'edit_subject', edit_subject_route, methods=['GET', 'POST'])
app.add_url_rule('/delete_subject/<int:subject_id>', 'delete_subject', delete_subject_route)
app.add_url_rule('/view_subject_attendance/<int:subject_id>', 'view_subject_attendance', view_subject_attendance_route)
app.add_url_rule('/edit_subject_attendance/<int:subject_id>/<string:date>', 'edit_subject_attendance', edit_subject_attendance_route, methods=['GET', 'POST'])
app.add_url_rule('/delete_subject_attendance/<int:subject_id>/<string:date>', 'delete_subject_attendance', delete_subject_attendance_route)
app.add_url_rule('/week_attendance_table', 'week_attendance_table', week_attendance_table_route, methods=['GET', 'POST'])
app.add_url_rule('/student_week_attendance/<int:student_id>', 'student_week_attendance', student_week_attendance_route, methods=['GET', 'POST'])
app.add_url_rule('/subject_week_attendance', 'subject_week_attendance', subject_week_attendance_route, methods=['GET', 'POST'])
app.add_url_rule('/export_attendance_excel', 'export_attendance_excel', export_attendance_excel_route)
app.add_url_rule('/toggle_remote_learning/<int:student_id>', 'toggle_remote_learning', toggle_remote_learning_route, methods=['GET', 'POST'])
app.add_url_rule('/transfer_students_to_next_semester', 'transfer_students_to_next_semester', transfer_students_to_next_semester_route)
app.add_url_rule('/toggle_expel_student/<int:student_id>', 'toggle_expel_student', toggle_expel_student_route, methods=['GET', 'POST'])
app.add_url_rule('/send_email', 'send_email', send_confirmation_email, methods=['GET', 'POST'])
app.add_url_rule('/confirm_email_register_student', 'confirm_email_register_student', confirm_email_register_student_route, methods=['GET', 'POST'])
app.add_url_rule('/confirm_email_register_chief', 'confirm_email_register_chief', confirm_email_register_chief_route, methods=['GET', 'POST'])
app.add_url_rule('/confirm_email_register_captain', 'confirm_email_register_captain', confirm_email_register_captain_route, methods=['GET', 'POST'])
app.add_url_rule('/forgot_password', 'forgot_password', forgot_password_route, methods=['GET', 'POST'])
app.add_url_rule('/reset_password', 'reset_password', reset_password_route, methods=['GET', 'POST'])
app.add_url_rule('/set_new_password', 'set_new_password', set_new_password_route, methods=['GET', 'POST'])
app.add_url_rule('/change_password', 'change_password', change_password_route, methods=['GET', 'POST'])
app.add_url_rule('/confirm_password_reset', 'confirm_password_reset', confirm_password_reset_route, methods=['GET', 'POST'])
app.add_url_rule('/change_password_request', 'change_password_request', change_password_request_route, methods=['GET', 'POST'])
app.add_url_rule('/group_overview/<int:user_id>', 'group_overview', group_overview_route, methods=['GET', 'POST'])
app.add_url_rule('/inbox', 'inbox', inbox_route, methods=['GET', 'POST'])
app.add_url_rule('/view_message/<int:message_id>', 'view_message', view_message_route, methods=['GET', 'POST'])
app.add_url_rule('/manage_requests', 'manage_requests', manage_requests_route, methods=['GET', 'POST'])
app.add_url_rule('/approve_request/<int:request_id>', 'approve_request', approve_request_route, methods=['GET', 'POST'])
app.add_url_rule('/reject_request/<int:request_id>', 'reject_request', reject_request_route, methods=['GET', 'POST'])
app.add_url_rule('/transfer_captain_rights/<int:student_id>', 'transfer_captain_rights', transfer_captain_rights_route, methods=['GET', 'POST'])

if __name__ == '__main__':
    app.run(debug=True)
