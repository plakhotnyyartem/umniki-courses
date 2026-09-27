"""Начальная настройка при запуске на сервере, где нет доступа к консоли (бесплатный Render).

ADMIN_EMAIL + ADMIN_PASSWORD — создать администратора. Пароль из переменной считается
главным: если его поменять в настройках хостинга, при следующем запуске он обновится
(так можно восстановить доступ, если пароль забыт).
SEED_DEMO_CONTENT=1 — если курсов ещё нет, загрузить демо-курсы. Демо-преподаватели получают
случайный пароль, который никто не знает: их курсы редактирует администратор.
"""

import logging
import os
import secrets

from sqlalchemy import func, select

from .db import SessionLocal
from .models import Course, User
from .security import destroy_user_sessions, hash_password, verify_password

log = logging.getLogger("uvicorn.error")
MIN_ADMIN_PASSWORD = 12


def _ensure_admin(db) -> None:
    email = (os.getenv("ADMIN_EMAIL") or "").strip().lower()
    password = os.getenv("ADMIN_PASSWORD") or ""
    if not email or not password:
        return
    if len(password) < MIN_ADMIN_PASSWORD:
        log.error("ADMIN_PASSWORD короче %s символов — администратор не создан", MIN_ADMIN_PASSWORD)
        return
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        db.add(User(name="Администратор", email=email, password_hash=hash_password(password), role="admin", avatar="🛡️"))
        log.info("Создан администратор %s", email)
    elif user.role != "admin":
        # Не повышаем чужой аккаунт до админа молча — это похоже на ошибку в настройках
        log.error("Пользователь %s уже есть и он не администратор — оставлен без изменений", email)
    elif not verify_password(password, user.password_hash):
        user.password_hash = hash_password(password)
        user.is_active = True
        destroy_user_sessions(db, user.id)
        log.info("Пароль администратора %s обновлён из ADMIN_PASSWORD", email)


def _seed_demo(db) -> None:
    if os.getenv("SEED_DEMO_CONTENT") != "1":
        return
    if db.scalar(select(func.count()).select_from(Course)):
        return
    from .seed import load_demo_courses  # импорт здесь: seed тянет демо-данные, нужные только тут

    load_demo_courses(db, hash_password(secrets.token_urlsafe(24)))
    log.info("Загружены демо-курсы")


def run() -> None:
    db = SessionLocal()
    try:
        _ensure_admin(db)
        _seed_demo(db)
        db.commit()
    finally:
        db.close()
