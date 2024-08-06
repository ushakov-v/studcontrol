from flask import flash, redirect, url_for
from flask_login import login_required
from decorators import roles_required
from models import User, db, Student, StudentSemester, Request, Attendance, RemoteLearningDate, Message, Subject, Teacher
from datetime import datetime

@login_required
@roles_required('admin', 'chief')
def transfer_captain_rights_route(student_id):
    student = User.query.get(student_id)
    if not student or student.role != 'student':
        flash('Неверный студент', 'danger')
        return redirect(url_for('user_list'))

    captain = User.query.filter_by(group=student.group, role='captain').first()
    if not captain:
        flash('В группе нет старосты', 'danger')
        return redirect(url_for('user_list'))

    # Перенос данных журнала от старосты к студенту
    Student.query.filter_by(user_id=captain.id).update({'user_id': student.id})
    StudentSemester.query.filter_by(user_id=captain.id).update({'user_id': student.id})
    Attendance.query.filter_by(user_id=captain.id).update({'user_id': student.id})
    RemoteLearningDate.query.filter_by(student_id=captain.id).update({'student_id': student.id})
    Subject.query.filter_by(user_id=captain.id).update({'user_id': student.id})

    # Удаление данных журнала старосты
    Student.query.filter_by(user_id=captain.id).delete()
    StudentSemester.query.filter_by(user_id=captain.id).delete()
    Attendance.query.filter_by(user_id=captain.id).delete()
    RemoteLearningDate.query.filter_by(student_id=captain.id).delete()
    Subject.query.filter_by(user_id=captain.id).delete()

    # Смена ролей
    student.role = 'captain'
    captain.role = 'student'
    db.session.commit()

    # Добавляем запрос на просмотр группы для бывшего старосты
    request_entry = Request(
        student_id=captain.id,
        captain_id=student.id,
        status='approved',
        timestamp=datetime.utcnow()
    )
    db.session.add(request_entry)
    db.session.commit()

    return redirect(url_for('user_list'))
