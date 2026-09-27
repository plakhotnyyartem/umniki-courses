import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)


def _normalize_url(url: str) -> str:
    # Хостинги (Neon, Render, Heroku) выдают postgres:// или postgresql://, а SQLAlchemy
    # по такому адресу ищет драйвер psycopg2. Мы используем psycopg 3 — указываем его явно.
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


DATABASE_URL = _normalize_url(os.getenv("DATABASE_URL") or f"sqlite:///{DATA_DIR / 'app.db'}")
IS_SQLITE = DATABASE_URL.startswith("sqlite")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if IS_SQLITE else {},
    # Бесплатный Neon усыпляет базу и рвёт простаивающие соединения — проверяем перед использованием
    pool_pre_ping=not IS_SQLITE,
)


@event.listens_for(engine, "connect")
def _sqlite_pragmas(dbapi_conn, _record):
    # В SQLite внешние ключи (и ON DELETE CASCADE) по умолчанию выключены
    if IS_SQLITE:
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys = ON")
        cur.execute("PRAGMA journal_mode = WAL")
        cur.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
