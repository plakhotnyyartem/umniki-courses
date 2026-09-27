"""Ставит демо-аккаунтам случайные пароли — обязательно перед тем, как открывать сайт в интернет.

Запуск (из папки backend): python -m app.reset_demo_passwords
Пароли записываются в data/demo-accounts.txt (файл доступен только владельцу и не попадает в git).
"""

import os
import secrets

from sqlalchemy import select

from .db import DATA_DIR, SessionLocal
from .models import User
from .security import destroy_user_sessions, hash_password
from .seed import USERS

OUT_FILE = DATA_DIR / "demo-accounts.txt"


def run() -> None:
    db = SessionLocal()
    lines = []
    for info in USERS:
        user = db.scalar(select(User).where(User.email == info["email"]))
        if user is None:
            continue
        password = secrets.token_urlsafe(12)
        user.password_hash = hash_password(password)
        destroy_user_sessions(db, user.id)  # старые входы с demo12345 больше не действуют
        lines.append(f"{user.role:8} {user.email:22} {password}")
    db.commit()
    db.close()

    fd = os.open(OUT_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write("Демо-аккаунты с новыми паролями (не публикуйте этот файл):\n\n" + "\n".join(lines) + "\n")
    print(f"Пароли {len(lines)} демо-аккаунтов заменены. Новые пароли: {OUT_FILE}")


if __name__ == "__main__":
    run()
