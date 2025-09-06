from datetime import datetime
from flask import render_template, request, redirect, url_for
from flask_login import login_required, current_user
from models import Attendance, Student, Subject, RemoteLearningDate, db, User, Request, StudentSemester

@login_required
def edit_subject_attendance_route(subject_id, date):
    user_id = request.args.get('user_id', type=int, default=current_user.id)
    user = User.query.get(user_id)
    if not user:
        return render_template('error.html', message='Пользователь не найден')

    # Проверка доступа пользователя
    if current_user.role == 'chief':
        request_entry = Request.query.filter_by(student_id=current_user.id, status='approved').first()
        if not request_entry:
            return render_template('error.html', message='Ваш запрос на просмотр журналов не был одобрен администратором.')

    if current_user.role == 'captain':
        request_entry = Request.query.filter_by(student_id=current_user.id, status='approved').first()
        if not request_entry:
            return render_template('error.html', message='Ваш запрос на редактирование журнала посещаемости не был одобрен.')

        if user_id != current_user.id:
            return render_template('error.html', message='У вас нет доступа к этой группе.')

    if current_user.id != user_id and current_user.role != 'admin':
        return render_template('error.html', message='У вас нет прав на выполнение этого действия.')

    # Получение информации о предмете
    subject = Subject.query.get(subject_id)
    if not subject:
        return render_template('error.html', message='Предмет не найден')

    selected_semester = subject.semester  # Используем семестр, привязанный к предмету

    # Получение списка студентов
    students = Student.query.filter_by(user_id=user_id).order_by(Student.name).all()

    # Обработка параметров даты и времени
    date_obj = datetime.strptime(date, '%Y-%m-%d').date()
    study_time = request.args.get('study_time')
    activity = request.args.get('activity')
    selected_week = request.args.get('week')

    # Получение записей о посещаемости
    attendances = Attendance.query.filter_by(subject_id=subject_id, date=date_obj, study_time=study_time, activity=activity).all()
    attendance_data = {attendance.student_id: attendance for attendance in attendances}

    if request.method == 'POST':
        new_date = request.form.get('new_date')
        new_study_time = request.form.get('new_study_time')
        new_activity = request.form.get('new_activity')
        new_topic = request.form.get('new_topic')

        new_date_obj = datetime.strptime(new_date, '%Y-%m-%d').date()

        # Удаление старых записей
        Attendance.query.filter_by(subject_id=subject_id, date=date_obj, study_time=study_time, activity=activity).delete()

        # Добавление или обновление записей о посещаемости
        for student in students:
            status = request.form.get(f'status_{student.id}')
            if status:
                # Получаем подгруппу для семестра предмета
                student_semester = StudentSemester.query.filter_by(student_id=student.id, semester=selected_semester).first()
                current_subgroup = student_semester.subgroup if student_semester else 'whole_group'
                if student.id in attendance_data:
                    old_attendance = attendance_data[student.id]
                    new_attendance = Attendance(
                        student_id=student.id,
                        date=new_date_obj,
                        subject_id=subject_id,
                        study_time=new_study_time,
                        activity=new_activity,
                        status=status,
                        topic=new_topic,
                        subgroup=current_subgroup,
                        week=old_attendance.week,
                        user_id=old_attendance.user_id
                    )
                else:
                    new_attendance = Attendance(
                        student_id=student.id,
                        date=new_date_obj,
                        subject_id=subject_id,
                        study_time=new_study_time,
                        activity=new_activity,
                        status=status,
                        topic=new_topic,
                        subgroup=current_subgroup,
                        week=selected_week or 1,
                        user_id=user_id
                    )
                db.session.add(new_attendance)

            # Обновление статуса дистанционного обучения студента
            remote_learning_start_date = request.form.get(f'remote_learning_start_date_{student.id}')
            remote_learning_end_date = request.form.get(f'remote_learning_end_date_{student.id}')
            if remote_learning_start_date and remote_learning_end_date:
                try:
                    start_date_obj = datetime.strptime(remote_learning_start_date, '%Y-%m-%d').date()
                    end_date_obj = datetime.strptime(remote_learning_end_date, '%Y-%m-%d').date()
                    existing_record = RemoteLearningDate.query.filter_by(student_id=student.id, semester=selected_week).first()
                    if existing_record:
                        existing_record.start_date = start_date_obj
                        existing_record.end_date = end_date_obj
                    else:
                        remote_learning_date = RemoteLearningDate(
                            student_id=student.id,
                            semester=selected_week,
                            start_date=start_date_obj,
                            end_date=end_date_obj
                        )
                        db.session.add(remote_learning_date)
                except ValueError:
                    pass

        db.session.commit()
        return redirect(url_for('view_subject_attendance', subject_id=subject.id, week=selected_week, date=f"{new_date} - {new_study_time} - {new_activity}", user_id=user_id))

    # Проверка статуса дистанционного обучения для студентов
    students_with_remote_learning = {
        rl.student_id for rl in RemoteLearningDate.query.filter(
            RemoteLearningDate.student_id.in_([s.id for s in students]),
            RemoteLearningDate.start_date <= date_obj,
            RemoteLearningDate.end_date >= date_obj
        ).all()
    }

    # Фильтруем студентов для отображения только тех, кто имеет отметку о посещаемости на текущую дату
    students_with_attendance = [
        student for student in students
        if student.id in attendance_data or student.id in students_with_remote_learning
    ]

    # Добавляем информацию о подгруппах к каждому студенту
    for student in students_with_attendance:
        student_semester = StudentSemester.query.filter_by(student_id=student.id, semester=selected_semester).first()
        student.current_subgroup = student_semester.subgroup if student_semester else 'whole_group'

    viewing_other_group = current_user.id != user_id

    return render_template(
        'attendance/edit_subject_attendance.html',
        subject=subject,
        students=students_with_attendance,
        date=date_obj,
        study_time=study_time,
        activity=activity,
        topic=attendances[0].topic if attendances else '',
        attendance_data=attendance_data,
        user_id=user_id,
        students_with_remote_learning=students_with_remote_learning,
        viewing_other_group=viewing_other_group,
        selected_semester=selected_semester
    )