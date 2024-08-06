from datetime import timedelta
import pandas as pd
from io import BytesIO
from flask import send_file, render_template, request
from flask_login import login_required, current_user
from models import Student, Attendance, StudentSemester, User, db, RemoteLearningDate
from get_current_semester import get_current_semester

@login_required
def export_attendance_excel_route():
    selected_semester = request.args.get('semester', type=int, default=1)
    user_id = request.args.get('user_id', type=int, default=current_user.id)

    user = User.query.get(user_id)
    if not user:
        return render_template('error.html', message='Пользователь не найден')

    try:
        start_date, end_date, total_semesters = get_current_semester(user, selected_semester)
    except ValueError as e:
        return render_template('error.html', message=str(e))

    students = db.session.query(Student).join(StudentSemester).filter(
        Student.user_id == user_id,
        StudentSemester.semester == selected_semester
    ).order_by(Student.name).all()

    num_weeks = (end_date - start_date).days // 7 + 1

    data = []
    expelled_students = []
    for student in students:
        student_data = [student.name]
        total_absences = 0
        total_unexcused_absences = 0

        remote_learning_dates = RemoteLearningDate.query.filter_by(student_id=student.id, semester=selected_semester).all()

        for week_offset in range(num_weeks):
            week_start_date = start_date + timedelta(weeks=week_offset)
            week = week_offset + 1  # Неделя начинается с 1 и далее

            absences = Attendance.query.filter(
                Attendance.student_id == student.id,
                Attendance.date.between(week_start_date, week_start_date + timedelta(days=6)),
                Attendance.status == 'Absent'
            ).all()
            excused_absences = Attendance.query.filter(
                Attendance.student_id == student.id,
                Attendance.date.between(week_start_date, week_start_date + timedelta(days=6)),
                Attendance.status == 'Excused'
            ).all()
            num_absences = len(absences) + len(excused_absences)
            num_unexcused_absences = len(absences)

            remote_learning = any(
                rd.start_date <= week_start_date <= rd.end_date for rd in remote_learning_dates
            )

            if remote_learning:
                total_absences_text = 'ДО'
                unexcused_absences_text = 'ДО'
            else:
                total_absences_text = num_absences * 2
                unexcused_absences_text = num_unexcused_absences * 2

            student_data.extend([total_absences_text, unexcused_absences_text])

            total_absences += num_absences
            total_unexcused_absences += num_unexcused_absences

        remote_learning = any(
            rd.start_date <= end_date <= rd.end_date for rd in remote_learning_dates
        )

        if remote_learning:
            total_absences_text = 'ДО'
            unexcused_absences_text = 'ДО'
        else:
            total_absences_text = total_absences * 2
            unexcused_absences_text = total_unexcused_absences * 2

        student_data.extend([total_absences_text, unexcused_absences_text])
        data.append(student_data)

        if student.expelled:
            expelled_students.append(student.name)

    columns = ['ФИО студента']
    for week in range(1, num_weeks + 1):
        columns.extend([f'Неделя {week} (Кол-во пропущенных занятий)', f'Неделя {week} (По неув. причине)'])
    columns.extend(['Всего (Кол-во пропущенных занятий)', 'Всего (По неув. причине)'])

    df = pd.DataFrame(data, columns=columns)

    max_name_length = max(df['ФИО студента'].apply(lambda x: len(x)))
    name_column_width = max_name_length * 1.2

    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Attendance', startrow=1)

    workbook = writer.book
    worksheet = writer.sheets['Attendance']

    header_format = workbook.add_format(
        {'bold': True, 'text_wrap': True, 'valign': 'vcenter', 'align': 'center', 'border': 1, 'rotation': 90})
    merge_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})
    data_format_center = workbook.add_format({'valign': 'vcenter', 'align': 'center', 'border': 1})
    data_format_left = workbook.add_format({'valign': 'vcenter', 'align': 'left', 'border': 1})
    expelled_format = workbook.add_format({'valign': 'vcenter', 'align': 'left', 'border': 1, 'bg_color': '#FF0000'})
    expelled_format_center = workbook.add_format(
        {'valign': 'vcenter', 'align': 'center', 'border': 1, 'bg_color': '#FF0000'})

    worksheet.set_column('A:A', name_column_width)
    worksheet.merge_range('A1:A2', 'ФИО студента', merge_format)

    col = 1
    for week in range(1, num_weeks + 1):
        worksheet.merge_range(0, col, 0, col + 1, f'Неделя {week}', merge_format)
        worksheet.write(1, col, 'Кол-во\nпропущенных\nзанятий', header_format)
        worksheet.write(1, col + 1, 'По неув.\nпричине', header_format)
        col += 2

    worksheet.merge_range(0, col, 0, col + 1, 'Всего', merge_format)
    worksheet.write(1, col, 'Кол-во\nпропущенных\nзанятий', header_format)
    worksheet.write(1, col + 1, 'По неув.\nпричине', header_format)
    worksheet.set_row(1, 78)

    for row_num in range(2, len(df) + 2):
        student_name = df.iloc[row_num - 2, 0]
        if student_name in expelled_students:
            row_format = expelled_format
            row_format_center = expelled_format_center
        else:
            row_format = data_format_left
            row_format_center = data_format_center

        worksheet.write(row_num, 0, student_name, row_format)
        for col_num in range(1, len(columns)):
            worksheet.write(row_num, col_num, df.iloc[row_num - 2, col_num], row_format_center)

    writer.close()
    output.seek(0)

    return send_file(output, download_name=f"attendance_semester_{selected_semester}.xlsx", as_attachment=True)
