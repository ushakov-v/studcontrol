from flask import redirect, url_for, request, flash, render_template
from flask_login import login_required, current_user
from models import Student, User, db
from datetime import datetime

@login_required
def toggle_expel_student_route(student_id):
    student = Student.query.get(student_id)
    user = User.query.get(student.user_id)

    if not student or (student.user_id != current_user.id and current_user.role != 'admin'):
        return render_template('error.html', message='У вас нет прав на выполнение этого действия.', viewing_attendance_user=user)

    if request.method == 'POST':
        if 'remove_expel_student' in request.form:
            student.expelled = False
            student.expel_date = None
        else:
            expel_date = request.form.get('expel_date')
            student.expel_date = datetime.strptime(expel_date, '%Y-%m-%d').date()
            student.expelled = True
        db.session.commit()
        return redirect(url_for('view_student', student_id=student.id, user_id=student.user_id))

    return render_template('toggle_expel_student.html', student=student, user_id=student.user_id, viewing_attendance_user=user)
