from datetime import datetime
from flask import render_template, request, redirect, url_for
from flask_login import login_required, current_user
from models import db, Attendance, Student, Subject, User, RemoteLearningDate, StudentSemester, Request
from get_current_semester import get_current_semester

@login_required
def manage_attendance_route():
    selected_semester = request.args.get('semester', type=int, default=1)
    selected_subgroup = request.args.get('subgroup', type=str, default='all')
    selected_subject = request.args.get('subject', type=int, default=None)
    user_id = request.args.get('user_id', type=int, default=current_user.id)

    user = User.query.get(user_id)
    if not user:
        return render_template('error.html', message='Пользователь не найден')

    viewing_other_group = current_user.id != user_id

    if current_user.id != user_id and current_user.role != 'admin':
        return render_template('error.html', message='У вас нет прав на выполнение этого действия.')

    # Проверка прав доступа пользователя
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

    date_str = request.args.get('date')
    date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else datetime.today().date()

    success_message = None

    if request.method == 'POST':
        date_str = request.form['date']
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        subject_id = request.form['subject']
        activity = request.form['activity']
        study_time = request.form['study_time']
        topic = request.form['topic']
        subject = Subject.query.get(subject_id)

        # Удаляем предыдущие записи о посещаемости для этой даты, предмета и времени
        Attendance.query.filter_by(date=date, subject_id=subject_id, study_time=study_time, user_id=user_id).delete()

        for student in Student.query.filter_by(user_id=user_id).all():
            if student.expel_date and date >= student.expel_date:
                continue
            status = request.form.get(f'status_{student.id}', None)
            if status:
                # Получаем подгруппу для выбранного семестра
                student_semester = StudentSemester.query.filter_by(student_id=student.id, semester=selected_semester).first()
                current_subgroup = student_semester.subgroup if student_semester else 'whole_group'
                attendance = Attendance(
                    student_id=student.id,
                    date=date,
                    subject_id=subject_id,
                    study_time=study_time,
                    topic=topic,
                    status=status,
                    activity=activity,
                    subgroup=current_subgroup,
                    week=date.isocalendar()[1],
                    user_id=user_id
                )
                db.session.add(attendance)
        db.session.commit()
        success_message = 'Посещаемость успешно добавлена!'

    # Получение списка студентов с учетом семестра и подгруппы
    query = db.session.query(Student).join(StudentSemester).filter(
        Student.user_id == user_id,
        StudentSemester.semester == selected_semester,
        (Student.expel_date == None) | (Student.expel_date > date)
    )

    if selected_subgroup != 'all':
        query = query.filter(StudentSemester.subgroup == selected_subgroup)

    students = query.order_by(Student.name).all()

    # Добавляем информацию о подгруппах к каждому студенту
    for student in students:
        student_semester = StudentSemester.query.filter_by(student_id=student.id, semester=selected_semester).first()
        student.current_subgroup = student_semester.subgroup if student_semester else 'whole_group'

    try:
        start_date, end_date, total_semesters = get_current_semester(user, selected_semester)
    except ValueError as e:
        return render_template('error.html', message=str(e))

    # Получение списка предметов
    subjects = Subject.query.filter_by(user_id=user_id, semester=selected_semester).order_by(Subject.name).all() if selected_semester else []

    # Получение дат дистанционного обучения для всех студентов
    remote_learning_dates = {}
    for student in students:
        remote_dates = RemoteLearningDate.query.filter_by(student_id=student.id).all()
        remote_learning_dates[student.id] = [
            {'semester': rd.semester, 'start_date': rd.start_date, 'end_date': rd.end_date}
            for rd in remote_dates
        ]

    return render_template('attendance/attendance.html', success_message=success_message, students=students, subjects=subjects, selected_semester=selected_semester, selected_subgroup=selected_subgroup, selected_subject=selected_subject, total_semesters=total_semesters, date=date, start_date=start_date, end_date=end_date, user_id=user_id, remote_learning_dates=remote_learning_dates, viewing_attendance_user=user, viewing_other_group=viewing_other_group)