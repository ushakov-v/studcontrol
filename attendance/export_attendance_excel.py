from datetime import timedelta
import pandas as pd
from io import BytesIO
from flask import send_file, render_template, request
from flask_login import login_required, current_user
from models import Student, Attendance, StudentSemester, User, db, RemoteLearningDate
from get_current_semester import get_current_semester
from sqlalchemy import func, case

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

    # Fetch students once
    students = db.session.query(Student).join(StudentSemester).filter(
        Student.user_id == user_id,
        StudentSemester.semester == selected_semester
    ).order_by(Student.name).all()

    student_ids = [s.id for s in students]
    num_weeks = (end_date - start_date).days // 7 + 1

    # Single query for all attendances: group by student, week, and status type
    attendances_query = db.session.query(
        Attendance.student_id,
        func.date_trunc('week', Attendance.date).label('week_start'),
        func.sum(case((Attendance.status == 'Absent', 1), else_=0)).label('unexcused'),
        func.sum(case((Attendance.status == 'Excused', 1), else_=0)).label('excused')
    ).filter(
        Attendance.student_id.in_(student_ids),
        Attendance.date.between(start_date, end_date)
    ).group_by(Attendance.student_id, 'week_start').all()

    # Build a dict for quick lookup: {student_id: {week_offset: (absences, unexcused)}}
    attendance_dict = {sid: {} for sid in student_ids}
    for att in attendances_query:
        week_offset = ((att.week_start.date() - start_date).days // 7) + 1
        total_abs = att.unexcused + att.excused
        attendance_dict[att.student_id][week_offset] = (total_abs, att.unexcused)

    # Fetch all remote learning dates in one query
    remote_dates = db.session.query(RemoteLearningDate).filter(
        RemoteLearningDate.student_id.in_(student_ids),
        RemoteLearningDate.semester == selected_semester
    ).all()
    remote_dict = {s.id: remote_dates for s in students if any(rd.student_id == s.id for rd in remote_dates)}

    data = []
    expelled_students = [s.name for s in students if s.expelled]

    for student in students:
        student_data = [student.name]
        total_absences = 0
        total_unexcused = 0
        remotes = remote_dict.get(student.id, [])

        for week in range(1, num_weeks + 1):
            week_start = start_date + timedelta(weeks=week-1)
            remote = any(rd.start_date <= week_start <= rd.end_date for rd in remotes)

            if remote:
                abs_text = 'ДО'
                unexc_text = 'ДО'
            else:
                abs_count, unexc_count = attendance_dict[student.id].get(week, (0, 0))
                abs_text = abs_count * 2
                unexc_text = unexc_count * 2
                total_absences += abs_count
                total_unexcused += unexc_count

            student_data.extend([abs_text, unexc_text])

        # Total with remote check
        remote_total = any(rd.start_date <= end_date <= rd.end_date for rd in remotes)
        total_abs_text = 'ДО' if remote_total else total_absences * 2
        total_unexc_text = 'ДО' if remote_total else total_unexcused * 2
        student_data.extend([total_abs_text, total_unexc_text])
        data.append(student_data)

    # Rest of the code (Pandas/Excel generation) remains the same for now, as it's efficient
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