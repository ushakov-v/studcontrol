from flask_wtf import FlaskForm
from wtforms import StringField, EmailField, TelField, RadioField, SelectField, SubmitField, PasswordField, DateField
from wtforms.validators import DataRequired, Email, Regexp, Optional

class LoginForm(FlaskForm):
    email = StringField('E-mail', validators=[DataRequired(), Email()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Войти')

class SemesterForm(FlaskForm):
    semester = SelectField('Семестр', validators=[DataRequired()])

class AddStudentForm(FlaskForm):
    name = StringField('ФИО студента', validators=[DataRequired(), Regexp(r'^[А-Яа-яЁё\s-]+$', message="Имя должно содержать только буквы русского алфавита.")])
    email = EmailField('Email', validators=[Optional(), Email()])
    phone = TelField('Телефон', validators=[Optional(), Regexp(r'^\+?\d{10,15}$', message="Введите корректный номер телефона.")])
    subgroup = RadioField('Подгруппа', choices=[('subgroup1', 'Подгруппа 1'), ('subgroup2', 'Подгруппа 2')], default='subgroup1')
    semester = SelectField('Семестр', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Добавить студента')

class EditStudentForm(AddStudentForm):
    submit = SubmitField('Сохранить изменения')

class ViewStudentForm(FlaskForm):
    pass

class DeleteStudentForm(FlaskForm):
    pass

class AttendanceForm(FlaskForm):
    semester = SelectField('Учебный семестр', validators=[DataRequired()])
    subject = SelectField('Название предмета', validators=[DataRequired()])
    subgroup = SelectField('Подгруппа', validators=[DataRequired()])
    activity = SelectField('Тип занятия', choices=[
        ('lecture', 'Лекция'),
        ('practice', 'Практическое занятие'),
        ('laboratory', 'Лабораторное занятие')
    ], validators=[DataRequired()])
    date = DateField('Дата', format='%Y-%m-%d', validators=[DataRequired()])
    study_time = SelectField('Время проведения занятия', choices=[
        ('1', '08:30 - 10:00'),
        ('2', '10:10 - 11:40'),
        ('3', '11:50 - 13:20'),
        ('4', '14:00 - 15:30'),
        ('5', '15:40 - 17:10'),
        ('6', '17:20 - 18:50'),
        ('7', '19:00 - 20:30'),
        ('8', '20:40 - 22:10')
    ], validators=[DataRequired()])
    topic = StringField('Тема занятия', validators=[DataRequired()])
    submit = SubmitField('Сохранить посещаемость')

