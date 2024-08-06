from flask import redirect, url_for, request, render_template, session
from flask_login import current_user, logout_user
from models import db, User

def delete_profile_route():
    if request.method == 'POST':
        # Получаем текущего пользователя
        user = current_user

        # Удаляем пользователя из базы данных, что автоматически удалит все связанные записи благодаря каскадному удалению
        db.session.delete(user)
        db.session.commit()

        # Выход пользователя из системы
        logout_user()

        # Сохраняем сообщение о успешном удалении в сессии
        session['message'] = 'Профиль успешно удалён.'

        # Редирект на главную страницу или другую нужную страницу
        return redirect(url_for('index'))

    # Возвращаем рендеринг шаблона, если запрос не POST
    return render_template('authorization/profile/profile.html', user=current_user)
