from datetime import timedelta
from flask import render_template, request
from flask_login import login_required, current_user
from models import Student, Attendance, Subject, RemoteLearningDate, User, db, Request
from datetime import datetime
from babel.dates import format_date
from get_current_semester import get_current_semester

@login_required
def student_week_attendance_route(student_id):
    user_id = request.args.get('user_id', type=int, default=current_user.id)

    # Checking user permissions and roles
    if current_user.role == 'student':
        request_entry = Request.query.filter_by(student_id=current_user.id, status='approved').order_by(
            Request.timestamp.desc()).first()
        if not request_entry:
            return render_template('error.html', message='Ваш запрос на просмотр группы не был одобрен.')
        user_id = request_entry.captain_id

    if current_user.role == 'chief':
        request_entry = Request.query.filter_by(student_id=current_user.id, status='approved').first()
        if not request_entry:
            return render_template('error.html',
                                   message='Ваш запрос на просмотр журналов не был одобрен администратором.')

    if current_user.role == 'captain':
        request_entry = Request.query.filter_by(student_id=current_user.id, status='approved').first()
        if not request_entry:
            return render_template('error.html',
                                   message='Ваш запрос на редактирование журнала посещаемости не был одобрен.')

        if user_id != current_user.id:
            return render_template('error.html', message='У вас нет доступа к этой группе.')

    if current_user.id != user_id and current_user.role != 'admin':
        return render_template('error.html', message='У вас нет прав на выполнение этого действия.')

    # Query the student by id and user_id
    student = Student.query.filter_by(id=student_id, user_id=user_id).first()
    user = User.query.get_or_404(user_id)

    if not student:
        return render_template('error.html', message='Студент не найден')

    selected_semester = request.args.get('semester', type=int, default=1)

    # Get the current semester dates
    try:
        start_date, end_date, total_semesters = get_current_semester(user, selected_semester)
    except ValueError as e:
        return render_template('error.html', message=str(e))

    num_weeks = (end_date - start_date).days // 7 + 1

    weeks = [(start_date + timedelta(weeks=i)).isocalendar()[1] for i in range(num_weeks)]
    week_ranges = [(week, (start_date + timedelta(weeks=i)).strftime('%d.%m.%Y') + ' - ' +
                    (start_date + timedelta(weeks=i, days=6)).strftime('%d.%m.%Y')) for i, week in enumerate(weeks)]

    week_dates = {}
    for i in range(num_weeks):
        week_start_date = start_date + timedelta(weeks=i)
        week_dates[weeks[i]] = [(week_start_date + timedelta(days=day)).strftime('%d.%m') for day in range(7)]

    selected_week = request.args.get('week', type=int, default=None)
    if selected_week not in weeks:
        selected_week = weeks[0] if weeks else None

    # Query all subjects for the user and sort by name
    subjects = Subject.query.filter_by(user_id=user_id).order_by(Subject.name).all()
    attendance_data = {}

    week_start_date = start_date + timedelta(weeks=weeks.index(selected_week))
    week_end_date = week_start_date + timedelta(days=6)

    total_absences_all_dates = 0
    total_unexcused_absences_all_dates = 0

    # Get remote learning dates for the student in the selected semester
    remote_learning_dates = RemoteLearningDate.query.filter_by(student_id=student.id, semester=selected_semester).all()

    # Iterate through each date in the week
    for single_date in (week_start_date + timedelta(n) for n in range(7)):
        single_date_str = single_date.strftime('%Y-%m-%d')
        student_attendance = {}
        total_absences = 0
        total_unexcused_absences = 0

        # Check if the date falls within any remote learning period
        remote_learning_present = any(
            remote_learning.start_date <= single_date <= remote_learning.end_date for remote_learning in remote_learning_dates
        )

        # Iterate through each subject
        for subject in subjects:
            # Query absences using subject_id
            absences = Attendance.query.filter_by(student_id=student.id, subject_id=subject.id, date=single_date).all()

            if absences:
                if remote_learning_present:
                    student_attendance[subject.name] = {
                        'total_absences': 'ДО',
                        'unexcused_absences': 'ДО'
                    }
                else:
                    num_absences = len([a for a in absences if a.status == 'Absent' or a.status == 'Excused'])
                    num_unexcused_absences = len([a for a in absences if a.status == 'Absent'])

                    student_attendance[subject.name] = {
                        'total_absences': num_absences,
                        'unexcused_absences': num_unexcused_absences
                    }

                    total_absences += num_absences
                    total_unexcused_absences += num_unexcused_absences

        if student_attendance:
            student_attendance['total'] = {
                'total_absences': 'ДО' if remote_learning_present else total_absences,
                'unexcused_absences': 'ДО' if remote_learning_present else total_unexcused_absences
            }

            attendance_data[single_date] = {
                'attendance': student_attendance
            }

            total_absences_all_dates += total_absences
            total_unexcused_absences_all_dates += total_unexcused_absences

    attendance_data['total'] = {
        'total_absences': 'ДО' if any(
            remote_learning.start_date <= week_start_date <= remote_learning.end_date for remote_learning in remote_learning_dates
        ) else total_absences_all_dates,
        'unexcused_absences': 'ДО' if any(
            remote_learning.start_date <= week_start_date <= remote_learning.end_date for remote_learning in remote_learning_dates
        ) else total_unexcused_absences_all_dates
    }

    viewing_other_group = current_user.id != user_id

    return render_template('attendance/student_week_attendance.html', student=student, num_weeks=num_weeks,
                           subjects=subjects, attendance_data=attendance_data, selected_week=selected_week,
                           weeks=weeks, start_date=start_date, timedelta=timedelta,
                           current_week=datetime.now().isocalendar()[1], format_date=format_date,
                           week_ranges=week_ranges, total_semesters=total_semesters, selected_semester=selected_semester, user_id=user_id, viewing_attendance_user=user, viewing_other_group=viewing_other_group)
