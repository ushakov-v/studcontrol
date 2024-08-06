from datetime import datetime, timedelta

def get_current_semester(user, selected_semester):
    now = datetime.now().date()

    start_year = user.start_date.year
    end_year = user.end_date.year

    total_semesters = (end_year - start_year) * 2

    # Проверяем, не выходит ли запрошенный семестр за пределы периода обучения
    if selected_semester < 1 or selected_semester > total_semesters:
        raise ValueError(f"Запрашиваемый семестр {selected_semester} выходит за пределы периода обучения.")

    # Вычисляем год текущего семестра на основе текущей даты и семестра
    year = start_year + (selected_semester - 1) // 2

    if year > end_year:
        raise ValueError("Запрашиваемый семестр выходит за пределы периода обучения.")

    if selected_semester % 2 == 1:
        # Осенний семестр (с 1 сентября по 31 декабря)
        start_date = datetime(year, 9, 1).date()
        if start_date.weekday() == 6:
            # Если 1 сентября воскресенье, начнем с 2 сентября
            start_date += timedelta(days=1)
        elif start_date.weekday() > 0:
            # Если 1 сентября не понедельник и не воскресенье, начнем с предыдущего понедельника
            start_date -= timedelta(days=start_date.weekday())
        end_date = datetime(year, 12, 31).date()
        if end_date.weekday() != 6:
            # Если 31 декабря не воскресенье, добавляем дни, чтобы охватить полную неделю
            end_date += timedelta(days=(6 - end_date.weekday()))
    else:
        # Весенний семестр (с 2 недели февраля по 2 неделю июня)
        year += 1  # Для весеннего семестра следующий календарный год
        start_date = datetime(year, 2, 1).date()
        # Переходим ко второй неделе февраля
        start_date += timedelta(days=(7 - start_date.weekday()) % 7)
        end_date = datetime(year, 6, 1).date()
        # Переходим ко второй неделе июня
        end_date += timedelta(days=(7 - end_date.weekday()) % 7)

    return start_date, end_date, total_semesters
