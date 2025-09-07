from datetime import timedelta
import pandas as pd
from io import BytesIO
from flask import send_file, render_template, request
from flask_login import login_required, current_user
from models import Student, Attendance, StudentSemester, User, db, RemoteLearningDate, Subject, Request, Teacher
from get_current_semester import get_current_semester

def split_topic_by_words(topic, max_length=50):
    """Split a topic into lines by words, respecting max_length."""
    words = topic.split()
    lines = []
    current_line = []
    current_length = 0

    for word in words:
        # Add 1 for the space if current_line is not empty
        word_length = len(word) + (1 if current_line else 0)
        if current_length + word_length <= max_length:
            current_line.append(word)
            current_length += word_length
        else:
            if current_line:
                lines.append(' '.join(current_line))
                current_line = [word]
                current_length = len(word)
            else:
                # If a single word is too long, split it
                lines.append(word[:max_length])
                current_line = [word[max_length:]] if word[max_length:] else []
                current_length = len(current_line[0]) if current_line else 0

    if current_line:
        lines.append(' '.join(current_line))

    return lines if lines else [topic]

@login_required
def export_subject_attendance_route():
    subject_id = request.args.get('subject_id', type=int)
    selected_semester = request.args.get('semester', type=int, default=1)
    user_id = request.args.get('user_id', type=int, default=current_user.id)

    # Проверка прав доступа
    if current_user.role == 'student':
        return render_template('error.html', message='У вас нет прав для экспорта посещаемости.')
    if current_user.role == 'captain' and user_id != current_user.id:
        return render_template('error.html', message='У вас нет доступа к этой группе.')
    if current_user.role == 'chief':
        request_entry = Request.query.filter_by(student_id=current_user.id, status='approved').first()
        if not request_entry:
            return render_template('error.html', message='Ваш запрос на просмотр журналов не был одобрен.')

    # Проверка существования пользователя
    user = User.query.get(user_id)
    if not user:
        return render_template('error.html', message='Пользователь не найден')

    # Проверка существования предмета
    subject = Subject.query.get(subject_id)
    if not subject or subject.user_id != user_id or subject.semester != selected_semester:
        return render_template('error.html', message='Предмет не найден или не соответствует семестру/группе.')

    # Получение дат семестра
    try:
        start_date, end_date, total_semesters = get_current_semester(user, selected_semester)
    except ValueError as e:
        return render_template('error.html', message=str(e))

    # Проверка корректности семестра
    if selected_semester < 1 or selected_semester > total_semesters:
        return render_template('error.html', message=f"Запрашиваемый семестр {selected_semester} выходит за пределы периода обучения.")

    # Получение студентов с подгруппами для текущего семестра
    students = db.session.query(Student).join(StudentSemester).filter(
        Student.user_id == user_id,
        StudentSemester.semester == selected_semester
    ).order_by(Student.name).all()

    # Добавление атрибута current_subgroup для каждого студента
    for student in students:
        student_semester = StudentSemester.query.filter_by(student_id=student.id, semester=selected_semester).first()
        student.current_subgroup = student_semester.subgroup if student_semester else 'whole_group'

    # Получаем все уникальные сессии (дата + время) для конкретного предмета
    sessions_query = db.session.query(
        Attendance.date,
        Attendance.study_time,
        Attendance.activity,
        Attendance.topic,
        Attendance.subgroup
    ).filter(
        Attendance.subject_id == subject_id,
        Attendance.date.between(start_date, end_date)
    ).distinct().order_by(Attendance.date, Attendance.study_time).all()

    # Дедупликация сессий для лекций
    unique_sessions = {}
    for date, study_time, activity, topic, subgroup in sessions_query:
        key = (date, study_time)
        if activity == 'lecture':
            # Для лекций используем subgroup=None и сохраняем только одну запись
            if key not in unique_sessions or unique_sessions[key][2] != 'lecture':
                unique_sessions[key] = (date, study_time, activity, topic, None)
        else:
            # Для других видов занятий включаем subgroup в ключ
            subgroup_key = (date, study_time, subgroup)
            unique_sessions[subgroup_key] = (date, study_time, activity, topic, subgroup)

    # Сортировка уникальных сессий по дате и времени
    attendance_sessions = sorted(unique_sessions.values(), key=lambda x: (x[0], x[1]))

    # Загружаем все данные посещаемости и дистанционного обучения
    student_ids = [s.id for s in students]
    attendances = db.session.query(Attendance).filter(
        Attendance.student_id.in_(student_ids),
        Attendance.subject_id == subject_id,
        Attendance.date.between(start_date, end_date)
    ).all()
    remote_learning_dates = db.session.query(RemoteLearningDate).filter(
        RemoteLearningDate.student_id.in_(student_ids),
        RemoteLearningDate.semester == selected_semester
    ).all()

    # Получаем информацию о преподавателях
    teachers = subject.teachers
    teachers_info = []
    degree_map = {
        'doctor': 'Доктор наук',
        'candidate': 'Кандидат наук'
    }
    title_map = {
        'assistant': 'Ассистент',
        'associate': 'Доцент',
        'teacher': 'Преподаватель',
        'professor': 'Профессор',
        'senior_teacher': 'Старший преподаватель'
    }
    for teacher in teachers:
        degree = degree_map.get(teacher.academic_degree, '')
        title = title_map.get(teacher.academic_title, '')
        if degree and title:
            full_title = degree + ', ' + title
        elif degree:
            full_title = degree
        elif title:
            full_title = title
        else:
            full_title = ''
        teacher_info = teacher.name + (f" ({full_title})" if full_title else '')
        teachers_info.append(teacher_info)
    teacher_str = ', '.join(teachers_info) if teachers_info else user.full_name

    # Перевод формы контроля
    control_map = {
        'none_control': '',  # Пустая строка для случая "Нет вида контроля"
        'credit': 'Зачёт',
        'exam': 'Экзамен',
        'differentiated_credit': 'Дифференцированный зачёт',
        'coursework': 'Курсовая работа (проект)',
        'diploma': 'Защита ВКР'
    }
    control_translation = control_map.get(subject.control, 'Неизвестная форма контроля')

    # Перевод видов занятий
    activity_map = {
        'lecture': 'Л',
        'laboratory': 'ЛЗ',
        'practice': 'ПЗ'
    }

    # Карта для подгрупп
    subgroup_map = {
        'subgroup1': '1 п.',
        'subgroup2': '2 п.'
    }

    # Формируем данные для всех студентов и сессий
    data = []
    student_remote_dates_dict = {s.id: [rd for rd in remote_learning_dates if rd.student_id == s.id] for s in students}

    max_name_length = 0
    for idx, student in enumerate(students):
        parts = student.name.split()
        if len(parts) >= 3:
            student_display_name = f"{parts[0]} {parts[1][0]}.{parts[2][0]}."
        elif len(parts) == 2:
            student_display_name = f"{parts[0]} {parts[1][0]}."
        else:
            student_display_name = student.name
        max_name_length = max(max_name_length, len(student_display_name))

        student_data = [idx + 1, student_display_name]
        for session in attendance_sessions:
            date, study_time, activity, topic, session_subgroup = session
            # Проверяем, относится ли студент к подгруппе для текущей сессии
            is_relevant_subgroup = (
                session_subgroup is None or  # Лекции или вся группа
                student.current_subgroup == session_subgroup or  # Совпадение подгруппы
                activity == 'lecture'  # Для лекций подгруппа не учитывается
            )

            # Проверяем дистанционное обучение
            remote_learning = any(
                rd.start_date <= date <= rd.end_date
                for rd in student_remote_dates_dict[student.id]
            ) and is_relevant_subgroup

            if remote_learning:
                student_data.append('ДО')
            else:
                attendance_record = next(
                    (a for a in attendances if a.student_id == student.id and a.date == date and a.study_time == study_time),
                    None
                )
                if attendance_record and is_relevant_subgroup:
                    if attendance_record.status == 'Absent':
                        student_data.append('н')
                    elif attendance_record.status == 'Excused':
                        student_data.append('уп')
                    else:
                        student_data.append('')
                else:
                    student_data.append('')
        data.append(student_data)

    # Генерация Excel-файла
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    workbook = writer.book

    # Форматирование
    header_format = workbook.add_format({'bold': True, 'text_wrap': True, 'valign': 'vcenter', 'align': 'center', 'border': 1})
    header_rotated_format = workbook.add_format({'bold': True, 'text_wrap': True, 'valign': 'vcenter', 'align': 'center', 'border': 1, 'rotation': 90})
    data_format_center = workbook.add_format({'valign': 'vcenter', 'align': 'center', 'border': 1})
    data_format_left = workbook.add_format({'valign': 'vcenter', 'align': 'left', 'border': 1})
    expelled_format = workbook.add_format({'valign': 'vcenter', 'align': 'left', 'border': 1, 'bg_color': '#FF0000'})
    expelled_format_center = workbook.add_format({'valign': 'vcenter', 'align': 'center', 'border': 1, 'bg_color': '#FF0000'})
    title_format = workbook.add_format({'bold': True, 'font_size': 12, 'align': 'left', 'text_wrap': True})

    # Специальные форматы для столбца "Тема занятия" при многострочных темах
    topic_top_format = workbook.add_format({
        'valign': 'vcenter',
        'align': 'left',
        'top': 1,
        'bottom': 0,
        'left': 1,
        'right': 1
    })
    topic_middle_format = workbook.add_format({
        'valign': 'vcenter',
        'align': 'left',
        'top': 0,
        'bottom': 0,
        'left': 1,
        'right': 1
    })
    topic_bottom_format = workbook.add_format({
        'valign': 'vcenter',
        'align': 'left',
        'top': 0,
        'bottom': 1,
        'left': 1,
        'right': 1
    })

    # Формирование строки дисциплины с учетом отсутствия запятой при 'none'
    if subject.control == 'none_control':
        discipline_str = f"{subject.name} ({subject.hours} ч.)"
    else:
        discipline_str = f"{subject.name} ({subject.hours} ч., {control_translation})"
    discipline_height = max(15, (len(discipline_str) // 50 + 1) * 15)
    teacher_height = max(15, (len(teacher_str) // 50 + 1) * 15)

    topics_headers = ['Дата', 'Вид занятия', 'Тема занятия', 'Подпись преподавателя']

    # Разделение сессий на чанки по 13
    chunk_size = 13
    num_chunks = (len(attendance_sessions) + chunk_size - 1) // chunk_size

    for chunk_idx in range(num_chunks):
        start = chunk_idx * chunk_size
        end = min(start + chunk_size, len(attendance_sessions))
        sessions_chunk = attendance_sessions[start:end]

        # Колонки для чанка
        columns_chunk = ['№', 'Фамилия и инициалы студента'] + [session[0].strftime('%d.%m') for session in sessions_chunk]

        # Данные для чанка
        data_chunk = []
        for student_data in data:
            student_chunk = student_data[0:2] + student_data[2 + start:2 + end]
            data_chunk.append(student_chunk)

        df_chunk = pd.DataFrame(data_chunk, columns=columns_chunk)

        # Создание листа
        sheet_name = f'Attendance_{chunk_idx + 1}'
        attendance_start_row = 2
        df_chunk.to_excel(writer, index=False, sheet_name=sheet_name, startrow=attendance_start_row)

        worksheet = writer.sheets[sheet_name]

        # Запись информации о дисциплине
        last_attendance_col = len(columns_chunk) - 1
        worksheet.merge_range(0, 0, 0, last_attendance_col, f'ДИСЦИПЛИНА: {discipline_str}', title_format)
        worksheet.set_row(0, discipline_height)

        # Перезапись заголовков
        worksheet.write(attendance_start_row, 0, '№', header_format)
        worksheet.write(attendance_start_row, 1, 'Фамилия и инициалы студента', header_format)
        for col_num in range(2, len(columns_chunk)):
            worksheet.write(attendance_start_row, col_num, columns_chunk[col_num], header_rotated_format)
        worksheet.set_row(attendance_start_row, 65)

        # Запись данных посещаемости
        for row_num, student in enumerate(students):
            is_expelled = student.expelled
            row_format = expelled_format if is_expelled else data_format_left
            row_format_center = expelled_format_center if is_expelled else data_format_center
            worksheet.write(attendance_start_row + 1 + row_num, 0, df_chunk.iloc[row_num, 0], row_format_center)
            worksheet.write(attendance_start_row + 1 + row_num, 1, df_chunk.iloc[row_num, 1], row_format)
            for col_num in range(2, len(columns_chunk)):
                worksheet.write(attendance_start_row + 1 + row_num, col_num, df_chunk.iloc[row_num, col_num], row_format_center)

        # Установка ширины столбцов для посещаемости
        worksheet.set_column(0, 0, 4)  # №
        worksheet.set_column(1, 1, max_name_length * 1.2)  # Фамилия
        for col in range(2, len(columns_chunk)):
            worksheet.set_column(col, col, 5)  # Даты

        # Пропуск 3 столбцов и добавление информации о преподавателе и тем занятий
        attendance_col_count = len(columns_chunk)
        skip_columns = 3
        topics_start_col = attendance_col_count + skip_columns

        # Информация о преподавателе
        worksheet.merge_range(0, topics_start_col, 0, topics_start_col + 3, f'ПРЕПОДАВАТЕЛЬ: {teacher_str}', title_format)
        worksheet.set_row(0, max(discipline_height, teacher_height))  # Установка максимальной высоты для строки 0

        # Таблица тем занятий
        topics_start_row = 2  # Ниже информации о преподавателе с пустой строкой
        for col, header in enumerate(topics_headers):
            worksheet.write(topics_start_row, topics_start_col + col, header, header_format)

        current_row = topics_start_row + 1
        for session in sessions_chunk:
            date, study_time, activity, topic, session_subgroup = session
            translated_activity = activity_map.get(activity, activity)
            # Для лекций подгруппа не указывается
            if session_subgroup and activity != 'lecture':
                sg_str = subgroup_map.get(session_subgroup, session_subgroup)
                translated_activity = f"{translated_activity} ({sg_str})"
            lines = split_topic_by_words(topic, max_length=50)  # Разбиение темы по словам

            # Объединение ячеек для даты, вида занятия и подписи
            if len(lines) > 1:
                worksheet.merge_range(current_row, topics_start_col, current_row + len(lines) - 1, topics_start_col, date.strftime('%d.%m'), data_format_center)
                worksheet.merge_range(current_row, topics_start_col + 1, current_row + len(lines) - 1, topics_start_col + 1, translated_activity, data_format_center)
                worksheet.merge_range(current_row, topics_start_col + 3, current_row + len(lines) - 1, topics_start_col + 3, '', data_format_center)
                for j, line in enumerate(lines):
                    if j == 0:
                        cell_format = topic_top_format
                    elif j == len(lines) - 1:
                        cell_format = topic_bottom_format
                    else:
                        cell_format = topic_middle_format
                    worksheet.write(current_row + j, topics_start_col + 2, line, cell_format)
            else:
                worksheet.write(current_row, topics_start_col, date.strftime('%d.%m'), data_format_center)
                worksheet.write(current_row, topics_start_col + 1, translated_activity, data_format_center)
                worksheet.write(current_row, topics_start_col + 2, lines[0], data_format_left)
                worksheet.write(current_row, topics_start_col + 3, '', data_format_center)

            current_row += len(lines)

        # Установка ширины столбцов для тем занятий
        worksheet.set_column(topics_start_col, topics_start_col, 10)  # Дата
        worksheet.set_column(topics_start_col + 1, topics_start_col + 1, 10)  # Вид занятия
        worksheet.set_column(topics_start_col + 2, topics_start_col + 2, 50)  # Тема занятия
        worksheet.set_column(topics_start_col + 3, topics_start_col + 3, 10)  # Подпись

    writer.close()
    output.seek(0)

    # Возврат файла с названием, включающим имя предмета
    return send_file(
        output,
        download_name=f"attendance_{subject.name}_semester_{selected_semester}.xlsx",
        as_attachment=True
    )