"""Минимальные миграции для SQLite через PRAGMA user_version.

create_all() создаёт только отсутствующие таблицы и не меняет существующие,
поэтому изменения схемы в уже созданной базе делаем здесь. Каждая миграция выполняется один раз.
Когда проект переедет на PostgreSQL, этот файл стоит заменить на Alembic.
"""

from sqlalchemy import Engine, text


def _columns(conn, table: str) -> set[str]:
    return {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))}


def _v1_question_kinds(conn) -> None:
    # Нужно сделать correct_index необязательным, а SQLite не умеет менять NOT NULL через ALTER —
    # поэтому пересобираем таблицу: создаём новую, копируем данные, подменяем.
    if "kind" in _columns(conn, "questions"):
        return
    conn.execute(text("""
        CREATE TABLE questions_new (
            id INTEGER PRIMARY KEY,
            lesson_id INTEGER NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
            kind VARCHAR(10) NOT NULL DEFAULT 'choice',
            text VARCHAR(500) NOT NULL,
            options JSON NOT NULL,
            correct_index INTEGER,
            accepted JSON NOT NULL DEFAULT '[]',
            match_numeric BOOLEAN NOT NULL DEFAULT 1,
            CONSTRAINT ck_question_kind CHECK (kind IN ('choice', 'text'))
        )"""))
    conn.execute(text("""
        INSERT INTO questions_new (id, lesson_id, kind, text, options, correct_index)
        SELECT id, lesson_id, 'choice', text, options, correct_index FROM questions"""))
    conn.execute(text("DROP TABLE questions"))
    conn.execute(text("ALTER TABLE questions_new RENAME TO questions"))
    conn.execute(text("CREATE INDEX ix_questions_lesson_id ON questions (lesson_id)"))


def _v2_question_position(conn) -> None:
    # Добавить столбец в SQLite можно простым ALTER; начальный порядок — как раньше, по id
    if "position" in _columns(conn, "questions"):
        return
    conn.execute(text("ALTER TABLE questions ADD COLUMN position INTEGER NOT NULL DEFAULT 0"))
    conn.execute(text("""
        UPDATE questions SET position = (
            SELECT COUNT(*) FROM questions q2 WHERE q2.lesson_id = questions.lesson_id AND q2.id <= questions.id
        )"""))


def _v3_drop_parent_email(conn) -> None:
    # Родителей на сайте нет — удаляем столбец вместе с уже сохранёнными адресами.
    # DROP COLUMN поддерживается в SQLite с версии 3.35.
    if "parent_email" in _columns(conn, "users"):
        conn.execute(text("ALTER TABLE users DROP COLUMN parent_email"))


MIGRATIONS = [_v1_question_kinds, _v2_question_position, _v3_drop_parent_email]


def run_migrations(engine: Engine) -> None:
    if engine.dialect.name != "sqlite":
        return
    with engine.begin() as conn:
        version = conn.execute(text("PRAGMA user_version")).scalar()
        for i, migration in enumerate(MIGRATIONS[version:], start=version + 1):
            migration(conn)
            conn.execute(text(f"PRAGMA user_version = {i}"))
