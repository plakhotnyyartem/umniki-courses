"""Панель администратора: пользователи, модерация курсов, статистика."""

from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from ..deps import DB, Admin, get_course_or_404
from ..models import Course, Enrollment, LessonProgress, User
from ..schemas import PublishIn, UserCreateIn, UserUpdateIn
from ..security import destroy_user_sessions, hash_password
from ..serializers import course_out, user_out

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/stats")
def stats(db: DB, _: Admin):
    by_role = dict(db.execute(select(User.role, func.count()).group_by(User.role)).all())
    by_subject = dict(db.execute(select(Course.subject, func.count()).group_by(Course.subject)).all())
    count = lambda model: db.scalar(select(func.count()).select_from(model))  # noqa: E731
    return {
        "users": by_role,
        "courses": by_subject,
        "published": db.scalar(select(func.count()).where(Course.is_published.is_(True))),
        "enrollments": count(Enrollment),
        "lessons_completed": count(LessonProgress),
    }


@router.get("/users")
def list_users(db: DB, _: Admin, role: str | None = None, q: str | None = None):
    stmt = select(User).order_by(User.created_at.desc())
    if role in ("admin", "teacher", "student"):
        stmt = stmt.where(User.role == role)
    if q:
        pattern = f"%{q.strip()[:50]}%"
        stmt = stmt.where(User.name.ilike(pattern) | User.email.ilike(pattern))
    return [user_out(u) for u in db.scalars(stmt)]


@router.post("/users", status_code=201)
def create_user(data: UserCreateIn, db: DB, _: Admin):
    if db.scalar(select(User).where(User.email == data.email)):
        raise HTTPException(409, "Этот email уже зарегистрирован")
    user = User(
        name=data.name.strip(),
        email=data.email,
        password_hash=hash_password(data.password),
        role=data.role,
        age=data.age,
    )
    db.add(user)
    db.commit()
    return user_out(user)


@router.patch("/users/{user_id}")
def update_user(user_id: int, data: UserUpdateIn, db: DB, admin: Admin):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "Пользователь не найден")
    if user.id == admin.id:
        raise HTTPException(400, "Нельзя менять роль или блокировать самого себя")

    if data.role is not None and data.role != user.role:
        if data.role == "student" and user.age is None:
            raise HTTPException(400, "У пользователя не указан возраст — сделать учеником нельзя")
        if user.role == "teacher" and user.courses:
            raise HTTPException(400, "У преподавателя есть курсы. Сначала удалите или передайте их.")
        user.role = data.role
    if data.is_active is not None:
        user.is_active = data.is_active
        if not data.is_active:
            destroy_user_sessions(db, user.id)  # блокировка действует сразу
    db.commit()
    return user_out(user)


@router.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: int, db: DB, admin: Admin):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "Пользователь не найден")
    if user.id == admin.id:
        raise HTTPException(400, "Нельзя удалить самого себя")
    db.delete(user)
    db.commit()


@router.get("/courses")
def all_courses(db: DB, _: Admin):
    stmt = (
        select(Course, func.count(Enrollment.user_id))
        .outerjoin(Enrollment, Enrollment.course_id == Course.id)
        .group_by(Course.id)
        .order_by(Course.created_at.desc())
        .options(selectinload(Course.teacher), selectinload(Course.lessons))
    )
    return [course_out(c, students_count=n) for c, n in db.execute(stmt)]


@router.patch("/courses/{course_id}")
def set_published(course_id: int, data: PublishIn, db: DB, _: Admin):
    course = get_course_or_404(db, course_id)
    course.is_published = data.is_published
    db.commit()
    return course_out(course)
