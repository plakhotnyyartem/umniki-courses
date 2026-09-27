from datetime import datetime, timezone

from sqlalchemy import JSON, CheckConstraint, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('admin', 'teacher', 'student')", name="ck_user_role"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(10))
    age: Mapped[int | None]
    avatar: Mapped[str] = mapped_column(String(8), default="🙂")
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    courses: Mapped[list["Course"]] = relationship(back_populates="teacher", cascade="all, delete-orphan")


class Course(Base):
    __tablename__ = "courses"
    __table_args__ = (
        CheckConstraint("subject IN ('english', 'math')", name="ck_course_subject"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    subject: Mapped[str] = mapped_column(String(10), index=True)
    min_age: Mapped[int] = mapped_column(default=6)
    max_age: Mapped[int] = mapped_column(default=14)
    cover: Mapped[str] = mapped_column(String(8), default="📘")
    is_published: Mapped[bool] = mapped_column(default=False)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    teacher: Mapped[User] = relationship(back_populates="courses")
    lessons: Mapped[list["Lesson"]] = relationship(
        back_populates="course", cascade="all, delete-orphan", order_by="(Lesson.position, Lesson.id)"
    )
    enrollments: Mapped[list["Enrollment"]] = relationship(cascade="all, delete-orphan")


class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(120))
    content: Mapped[str] = mapped_column(Text, default="")
    video_url: Mapped[str | None] = mapped_column(String(300))
    position: Mapped[int] = mapped_column(default=0)

    course: Mapped[Course] = relationship(back_populates="lessons")
    questions: Mapped[list["Question"]] = relationship(
        back_populates="lesson", cascade="all, delete-orphan", order_by="(Question.position, Question.id)"
    )


class Question(Base):
    """Вопрос мини-теста в конце урока.

    kind='choice' — выбор одного варианта из options, правильный — correct_index.
    kind='text'   — ребёнок вводит ответ сам; засчитывается любой из accepted.
    """

    __tablename__ = "questions"
    __table_args__ = (CheckConstraint("kind IN ('choice', 'text')", name="ck_question_kind"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(10), default="choice", server_default="choice")
    text: Mapped[str] = mapped_column(String(500))
    options: Mapped[list[str]] = mapped_column(JSON, default=list)
    correct_index: Mapped[int | None]
    accepted: Mapped[list[str]] = mapped_column(JSON, default=list, server_default="[]")
    # Сравнивать числа по значению: 0,5 = 0.5 = 1/2
    match_numeric: Mapped[bool] = mapped_column(default=True, server_default="1")
    position: Mapped[int] = mapped_column(default=0, server_default="0")

    lesson: Mapped[Lesson] = relationship(back_populates="questions")


class Enrollment(Base):
    __tablename__ = "enrollments"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), primary_key=True)
    enrolled_at: Mapped[datetime] = mapped_column(default=utcnow)

    user: Mapped[User] = relationship()
    course: Mapped[Course] = relationship(back_populates="enrollments")


class LessonProgress(Base):
    """Лучший результат ученика по уроку (урок считается пройденным, если запись есть)."""

    __tablename__ = "lesson_progress"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"), primary_key=True)
    score: Mapped[int] = mapped_column(default=0)
    total: Mapped[int] = mapped_column(default=0)
    attempts: Mapped[int] = mapped_column(default=1)
    completed_at: Mapped[datetime] = mapped_column(default=utcnow)


class Feedback(Base):
    """Комментарий преподавателя ученику по курсу."""

    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    course: Mapped[Course] = relationship()
    teacher: Mapped[User] = relationship(foreign_keys=[teacher_id])


class AuthSession(Base):
    """Серверная сессия. В БД храним только SHA-256 от токена из cookie."""

    __tablename__ = "auth_sessions"
    __table_args__ = (UniqueConstraint("token_hash"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[datetime]

    user: Mapped[User] = relationship()
