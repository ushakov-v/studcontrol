from flask import render_template, request, session
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from models import Student, Attendance, Subject, StudentSemester, User, db, Request
from get_current_semester import get_current_semester

@login_required
def subject_week_attendance_route():
    selected_semester = request.args.get('semester', type=int, default=1)
    user_id = request.args.get('user_id', type=int, default=current_user.id)
    date_str = request.args.get('date')
    date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else datetime.today().date()

    # Проверка роли текущего пользователя
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

    user = User.query.get(user_id)
    if not user:
        return render_template('error.html', message='Пользователь не найден')

    # Получение текущего семестра
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
    selected_day = request.args.get('day', type=int, default=None)

    if selected_week not in weeks:
        selected_week = weeks[0] if weeks else None

    # Получение списка студентов
    students = db.session.query(Student).join(StudentSemester).filter(
        Student.user_id == user_id,
        StudentSemester.semester == selected_semester
    ).order_by(Student.name).all()

    # Получение списка предметов
    subjects = Subject.query.filter_by(user_id=user_id, semester=selected_semester).order_by(Subject.name).all() if selected_semester else []

    attendance_data = []

    if selected_week and selected_day:
        week_start_date = start_date + timedelta(weeks=(weeks.index(selected_week)))
        selected_date = week_start_date + timedelta(days=(selected_day - 1))

        for student in students:
            if not student.expel_date or student.expel_date > selected_date:
                records = Attendance.query.filter_by(student_id=student.id, date=selected_date).all()
                student_attendance = {
                    'student_name': student.name,
                    'attendance_records': []
                }

                for record in records:
                    # Извлечение названия предмета с использованием subject_id
                    subject = Subject.query.get(record.subject_id)
                    subject_name = subject.abbreviated_name if subject and subject.abbreviated_name else 'Неизвестный предмет'
                    status = record.status
                    student_attendance['attendance_records'].append({
                        'subject': subject_name,
                        'activity': record.activity,
                        'study_time': record.study_time,
                        'subgroup': record.subgroup,
                        'status': status
                    })

                attendance_data.append(student_attendance)

    displayed_subjects = set()
    subject_max_columns = {}
    subject_details = {}

    # Уникальные комбинации предмета, активности, времени занятия и подгруппы
    for student_attendance in attendance_data:
        for record in student_attendance['attendance_records']:
            subject = record['subject']
            key = (subject, record['activity'], record['study_time'])

            if subject not in subject_details:
                subject_details[subject] = {}

            if key not in subject_details[subject]:
                subject_details[subject][key] = set()

            subject_details[subject][key].add(record['subgroup'])
            displayed_subjects.add(subject)

    # Определение количества колонок для каждого предмета
    for subject, details in subject_details.items():
        subject_max_columns[subject] = len(details)

    displayed_subjects = sorted(displayed_subjects)

    viewing_other_group = current_user.id != user_id

    return render_template('attendance/subject_week_attendance.html', students=students, subjects=subjects,
                           attendance_data=attendance_data, selected_week=selected_week, selected_day=selected_day,
                           week_ranges=week_ranges, displayed_subjects=displayed_subjects,
                           week_dates=week_dates, selected_semester=selected_semester, total_semesters=total_semesters,
                           subject_max_columns=subject_max_columns, subject_details=subject_details,
                           user_id=user_id, viewing_attendance_user=user,
                           viewing_other_group=viewing_other_group)
