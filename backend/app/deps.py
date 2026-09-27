from typing import Annotated

from fastapi import Cookie, Depends, HTTPException
from sqlalchemy.orm import Session

from .db import get_db
from .models import Course, User
from .security import SESSION_COOKIE, user_by_token

DB = Annotated[Session, Depends(get_db)]


def current_user_optional(db: DB, sid: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None) -> User | None:
    return user_by_token(db, sid)


def current_user(user: Annotated[User | None, Depends(current_user_optional)]) -> User:
    if user is None:
        raise HTTPException(401, "Нужно войти в аккаунт")
    return user


def require_roles(*roles: str):
    def checker(user: Annotated[User, Depends(current_user)]) -> User:
        if user.role not in roles:
            raise HTTPException(403, "Недостаточно прав")
        return user

    return checker


OptionalUser = Annotated[User | None, Depends(current_user_optional)]
CurrentUser = Annotated[User, Depends(current_user)]
Student = Annotated[User, Depends(require_roles("student"))]
Staff = Annotated[User, Depends(require_roles("teacher", "admin"))]
Admin = Annotated[User, Depends(require_roles("admin"))]


def get_course_or_404(db: Session, course_id: int) -> Course:
    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(404, "Курс не найден")
    return course


def ensure_can_edit(course: Course, user: User) -> None:
    """Редактировать курс может его автор или администратор."""
    if user.role != "admin" and course.teacher_id != user.id:
        raise HTTPException(403, "Это не ваш курс")
