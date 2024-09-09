from flask import redirect, url_for, request, render_template
from flask_login import login_required, current_user
from models import Student, Attendance, User, RemoteLearningDate, db
from datetime import datetime
import json

@login_required
def toggle_remote_learning_route(student_id):
    student = Student.query.get(student_id)
    user = User.query.get(student.user_id)

    if not student or (student.user_id != current_user.id and current_user.role != 'admin'):
        return render_template('error.html', message='У вас нет прав на выполнение этого действия.',
                               viewing_attendance_user=user)

    remote_learning_dates = RemoteLearningDate.query.filter_by(student_id=student_id).all()

    if request.method == 'POST':
        semester = int(request.form.get('semester'))
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')

        if 'remove_remote_learning' in request.form:
            remote_learning_date = RemoteLearningDate.query.filter_by(student_id=student_id, semester=semester).first()
            if remote_learning_date:
                db.session.delete(remote_learning_date)
                db.session.commit()  # Подтверждение удаления дистанционного обучения
            return redirect(url_for('view_student', student_id=student.id, user_id=student.user_id))

        else:
            remote_learning_date = RemoteLearningDate.query.filter_by(student_id=student_id, semester=semester).first()
            if not remote_learning_date:
                remote_learning_date = RemoteLearningDate(student_id=student_id, semester=semester)
                db.session.add(remote_learning_date)

            remote_learning_date.start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            remote_learning_date.end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

        db.session.commit()
        return redirect(url_for('view_student', student_id=student.id, user_id=student.user_id))

    total_semesters = (user.end_date.year - user.start_date.year) * 2
    remote_learning_dates_json = json.dumps([{
        'semester': rld.semester,
        'start_date': rld.start_date.strftime('%Y-%m-%d'),
        'end_date': rld.end_date.strftime('%Y-%m-%d')
    } for rld in remote_learning_dates])

    return render_template('toggle_remote_learning.html', student=student, user_id=student.user_id,
                           viewing_attendance_user=user, total_semesters=total_semesters,
                           remote_learning_dates_json=remote_learning_dates_json)
