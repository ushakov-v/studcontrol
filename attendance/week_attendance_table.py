from datetime import timedelta
from flask import render_template, request
from flask_login import login_required, current_user
from models import Student, Attendance, StudentSemester, db, User, Request
from get_current_semester import get_current_semester
from collections import defaultdict

@login_required
def week_attendance_table_route():
    selected_semester = request.args.get('semester', type=int, default=1)
    user_id = request.args.get('user_id', type=int, default=current_user.id)

    # Проверка на права доступа
    viewing_other_group = current_user.id != user_id

    # Проверка ролей пользователей (капитан, студент и т.д.)
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

    try:
        start_date, end_date, total_semesters = get_current_semester(user, selected_semester)
    except ValueError as e:
        return render_template('error.html', message=str(e))

    # Получаем всех студентов одним запросом
    students = db.session.query(Student).join(StudentSemester).filter(
        Student.user_id == user_id,
        StudentSemester.semester == selected_semester
    ).order_by(Student.name).all()

    if not students:
        # Если нет студентов, сразу рендерим пустую таблицу
        return render_template('attendance/week_attendance_table.html',
                               students=[],
                               num_weeks=0,
                               start_date=start_date,
                               attendance_data={},
                               selected_semester=selected_semester,
                               total_semesters=total_semesters,
                               user_id=user_id,
                               viewing_attendance_user=user,
                               viewing_other_group=viewing_other_group)

    # Получаем ID студентов для фильтра
    student_ids = [student.id for student in students]

    # Вычисляем количество недель
    num_weeks = (end_date - start_date).days // 7 + 1

    # Один большой запрос: все релевантные Attendance за семестр для всех студентов
    all_absences = Attendance.query.filter(
        Attendance.student_id.in_(student_ids),
        Attendance.date.between(start_date, end_date),
        Attendance.status.in_(['Absent', 'Excused', 'Remote'])
    ).all()

    # Группируем данные в памяти: defaultdict для student_id -> week -> list of absences
    attendance_by_student_week = defaultdict(lambda: defaultdict(list))
    for absence in all_absences:
        # Вычисляем неделю для даты
        week_offset = (absence.date - start_date).days // 7
        week = week_offset + 1
        attendance_by_student_week[absence.student_id][week].append(absence)

    # Теперь обрабатываем данные для каждого студента
    attendance_data = {}
    for student in students:
        student_attendance = {}
        total_absences = 0
        total_unexcused_absences = 0
        contains_do = False  # Флаг для хотя бы одного ДО
        all_zeros = True  # Флаг для только нулей в не-ДО неделях

        for week_offset in range(num_weeks):
            week = week_offset + 1
            absences = attendance_by_student_week[student.id][week]  # Список absences для этой недели

            num_absences = len([a for a in absences if a.status in ['Absent', 'Excused']])
            num_unexcused_absences = len([a for a in absences if a.status == 'Absent'])
            remote_learning_present = any(a.status == 'Remote' for a in absences)

            if remote_learning_present:
                total_absences_text = 'ДО'
                unexcused_absences_text = 'ДО'
                hours_absences_text = 'ДО'
                hours_unexcused_absences_text = 'ДО'
                contains_do = True
            else:
                total_absences_text = num_absences
                unexcused_absences_text = num_unexcused_absences
                hours_absences_text = num_absences * 2
                hours_unexcused_absences_text = num_unexcused_absences * 2
                if num_absences > 0:
                    all_zeros = False

            student_attendance[week] = {
                'total_absences': total_absences_text,
                'unexcused_absences': unexcused_absences_text,
                'hours_absences': hours_absences_text,
                'hours_unexcused_absences': hours_unexcused_absences_text
            }

            # Увеличиваем totals только если не ДО
            if not remote_learning_present:
                total_absences += num_absences
                total_unexcused_absences += num_unexcused_absences

        # Если есть ДО и все остальное 0, то totals = ДО
        if contains_do and all_zeros:
            total_absences = 'ДО'
            total_unexcused_absences = 'ДО'

        # Вычисляем hours totals заранее (для шаблона)
        total_hours_absences = total_absences * 2 if total_absences != 'ДО' else 'ДО'
        total_hours_unexcused = total_unexcused_absences * 2 if total_unexcused_absences != 'ДО' else 'ДО'

        attendance_data[student] = {
            'attendance': student_attendance,
            'total_absences': total_absences,
            'total_unexcused_absences': total_unexcused_absences,
            'total_hours_absences': total_hours_absences,
            'total_hours_unexcused': total_hours_unexcused
        }

    return render_template('attendance/week_attendance_table.html',
                           students=students,
                           num_weeks=num_weeks,
                           start_date=start_date,
                           attendance_data=attendance_data,
                           selected_semester=selected_semester,
                           total_semesters=total_semesters,
                           user_id=user_id,
                           viewing_attendance_user=user,
                           viewing_other_group=viewing_other_group)