from flask import render_template, request, session, redirect, url_for
from flask_login import login_required, current_user
from models import Attendance, Student, Subject, Teacher, User, db, RemoteLearningDate, Request
from datetime import datetime, timedelta
from get_current_semester import get_current_semester

@login_required
def view_subject_attendance_route(subject_id):
    user_id = request.args.get('user_id', type=int, default=current_user.id)

    # Проверка роли и прав доступа
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

    # Получение предмета
    subject = Subject.query.filter_by(id=subject_id, user_id=user_id).first()
    user = User.query.get_or_404(user_id)

    if not subject:
        return render_template('error.html', message='Предмет не найден')

    # Получение списка преподавателей для предмета
    teachers = Teacher.query.filter_by(subject_id=subject_id).all()

    selected_week = request.args.get('week')
    selected_date = request.args.get('date')

    # Получаем текущий семестр
    try:
        start_date, end_date, _ = get_current_semester(user, subject.semester)
    except ValueError as e:
        return render_template('attendance/view_subject_attendance.html', message=str(e))

    num_weeks = (end_date - start_date).days // 7 + 1
    weeks = [(start_date + timedelta(weeks=i)).isocalendar()[1] for i in range(num_weeks)]
    week_ranges = [(week, (start_date + timedelta(weeks=i)).strftime('%d.%m.%Y') + ' - ' +
                    (start_date + timedelta(weeks=i, days=6)).strftime('%d.%m.%Y')) for i, week in enumerate(weeks)]

    # Установление значения по умолчанию для selected_week
    if not selected_week:
        selected_week = weeks[0]
    else:
        selected_week = int(selected_week)

    week_start_date = start_date + timedelta(weeks=weeks.index(selected_week))
    week_dates = [(week_start_date + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]

    # Сопоставление датам дней недели
    days_of_week = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
    week_dates_with_days = [(week_dates[i], days_of_week[i]) for i in range(7)]

    # Получение данных посещаемости
    attendances = db.session.query(
        Attendance.date,
        Attendance.activity,
        Attendance.study_time,
        Attendance.topic
    ).filter_by(
        subject_id=subject_id,  # Используем subject_id вместо имени
        user_id=user_id
    ).distinct().all()

    dates = sorted([(attendance.date, attendance.activity, attendance.study_time, attendance.topic) for attendance in attendances], key=lambda x: (x[0], x[2], x[1]))

    # Фильтрация дат на основе выбранной недели
    filtered_dates = [date for date in dates if date[0].strftime('%Y-%m-%d') in week_dates]

    # Установление значения по умолчанию для selected_date
    if not selected_date and filtered_dates:
        first_filtered_date = filtered_dates[0]
        selected_date = f"{first_filtered_date[0].strftime('%Y-%m-%d')} - {first_filtered_date[2]} - {first_filtered_date[1]}"
    elif not filtered_dates:
        selected_date = None

    if selected_date:
        selected_date_parts = selected_date.split(' - ')
        selected_date_obj = datetime.strptime(selected_date_parts[0], '%Y-%m-%d').date()
        selected_study_time = selected_date_parts[1] if len(selected_date_parts) > 1 else None
        selected_activity = selected_date_parts[2] if len(selected_date_parts) > 2 else None

        # Фильтрация по subject_id вместо subject.name
        attendances = Attendance.query.filter_by(
            subject_id=subject_id,
            date=selected_date_obj,
            activity=selected_activity,
            study_time=selected_study_time,
            user_id=user_id
        ).all()

        student_ids = [attendance.student_id for attendance in attendances]
        students = Student.query.filter(Student.id.in_(student_ids)).order_by(Student.name).all()

        selected_topic = attendances[0].topic if attendances else None
    else:
        attendances = []
        students = []
        selected_topic = None

    attendance_data = {}
    for attendance in attendances:
        if attendance.student_id not in attendance_data:
            attendance_data[attendance.student_id] = []
        attendance_data[attendance.student_id].append(attendance)

    students_with_attendance = [
        student for student in students if student.id in attendance_data and any(att.status for att in attendance_data[student.id])
    ]

    # Получение дат дистанционного обучения для всех студентов
    remote_learning_dates = {}
    for student in students:
        remote_dates = RemoteLearningDate.query.filter_by(student_id=student.id).all()
        remote_learning_dates[student.id] = [
            {'start_date': rd.start_date.strftime('%Y-%m-%d'), 'end_date': rd.end_date.strftime('%Y-%m-%d')}
            for rd in remote_dates
        ]

    viewing_other_group = current_user.id != user_id

    return render_template(
        'attendance/view_subject_attendance.html',
        subject=subject,
        students=students_with_attendance,
        attendances=attendances,
        selected_date=selected_date,
        selected_topic=selected_topic,
        dates=filtered_dates,
        weeks=week_ranges,
        week_dates=week_dates_with_days,
        selected_week=selected_week,
        attendance_data=attendance_data,
        teachers=teachers,
        all_students=students_with_attendance,
        user_id=user_id,
        date=datetime.today().date(),
        viewing_attendance_user=user,
        remote_learning_dates=remote_learning_dates,
        viewing_other_group=viewing_other_group,
        selected_semester=subject.semester
    )
