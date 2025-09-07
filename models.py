from datetime import datetime
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import JSON

db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    expelled = db.Column(db.Boolean, default=False)
    expel_date = db.Column(db.Date, nullable=True)

    remote_learning_dates = db.relationship('RemoteLearningDate', backref='student', lazy=True, cascade="all, delete-orphan")
    semesters = db.relationship('StudentSemester', backref='student', lazy=True, cascade="all, delete-orphan")
    attendances = db.relationship('Attendance', backref='student', lazy=True, cascade="all, delete-orphan")

class RemoteLearningDate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id', ondelete='CASCADE'), nullable=False, name='fk_remote_learning_student_id')
    semester = db.Column(db.Integer, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)

class StudentSemester(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id', ondelete='CASCADE'), nullable=False, name='fk_student_semester_student_id')
    subgroup = db.Column(db.String(20), nullable=False)
    semester = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, name='fk_student_semester_user_id')

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id', ondelete='CASCADE'), nullable=False, name='fk_attendance_student_id')
    date = db.Column(db.Date, nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id', ondelete='CASCADE'), nullable=False, name='fk_attendance_subject_id')
    study_time = db.Column(db.String(20))
    topic = db.Column(db.String(300))
    status = db.Column(db.String(10), nullable=False)
    activity = db.Column(db.String(20), nullable=False)
    subgroup = db.Column(db.String(20), nullable=False)
    week = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, name='fk_attendance_user_id')

class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    academic_degree = db.Column(db.String(50))
    academic_title = db.Column(db.String(50))
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id', ondelete='CASCADE'), nullable=False, name='fk_teacher_subject_id')

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(300), nullable=False)
    abbreviated_name = db.Column(db.String(100))
    semester = db.Column(db.Integer, nullable=False)
    control = db.Column(db.String(30), nullable=False)
    hours = db.Column(db.String(20), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, name='fk_subject_user_id')

    teachers = db.relationship('Teacher', backref='subject', lazy=True, cascade="all, delete-orphan")

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    email_confirmed = db.Column(db.Boolean, default=False)
    email_confirmation_code = db.Column(db.String(100), nullable=True)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    institute = db.Column(db.String(150))
    group = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)

    students = db.relationship('Student', backref='user', lazy=True, cascade="all, delete-orphan")
    subjects = db.relationship('Subject', backref='user', lazy=True, cascade="all, delete-orphan")
    attendances = db.relationship('Attendance', backref='user', lazy=True, cascade="all, delete-orphan")
    sent_messages = db.relationship('Message', foreign_keys='Message.sender_id', backref='sender', lazy=True, cascade="all, delete-orphan")
    received_messages = db.relationship('Message', foreign_keys='Message.recipient_id', backref='recipient', lazy=True, cascade="all, delete-orphan")
    student_requests = db.relationship('Request', foreign_keys='Request.student_id', back_populates='student_user', lazy=True, cascade="all, delete-orphan")
    captain_requests = db.relationship('Request', foreign_keys='Request.captain_id', back_populates='captain_user', lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password, password)

class TempUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    institute = db.Column(db.String(150))
    group = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    email_confirmation_code = db.Column(db.String(6), nullable=False)
    created_at = db.Column(db.DateTime)

    def set_password(self, password):
        self.password = bcrypt.generate_password_hash(password).decode('utf-8')

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, name='fk_message_sender_id')
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, name='fk_message_recipient_id')
    subject = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    request_id = db.Column(db.Integer, db.ForeignKey('request.id', ondelete='SET NULL'), nullable=True, name='fk_message_request_id')

    request = db.relationship('Request', backref='messages')

class Request(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, name='fk_request_student_id')
    captain_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, name='fk_request_captain_id')
    institute = db.Column(db.String(150), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='pending')
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    student_user = db.relationship('User', foreign_keys=[student_id], back_populates='student_requests')
    captain_user = db.relationship('User', foreign_keys=[captain_id], back_populates='captain_requests')

def get_student_captain(student_id):
    request_entry = Request.query.filter_by(student_id=student_id, status='approved').first()
    if request_entry:
        return User.query.get(request_entry.captain_id)
    return None

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def create_admin_user():
    admin = User.query.filter_by(email='f0rmoodle@yandex.ru').first()
    if not admin:
        admin = User(
            full_name='Admin',
            email='f0rmoodle@yandex.ru',
            role='admin',
            group='admin',
            start_date=datetime.strptime('2024-01-01', '%Y-%m-%d').date(),
            end_date=datetime.strptime('2025-12-31', '%Y-%m-%d').date()
        )
        admin.set_password('admin')
        db.session.add(admin)
        db.session.commit()
