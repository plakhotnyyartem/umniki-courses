"""Кабинет преподавателя: свои курсы, уроки, вопросы, ученики и отзывы.
Администратор имеет те же права на любой курс."""

from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from ..deps import DB, Staff, ensure_can_edit, get_course_or_404
from ..models import Course, Enrollment, Feedback, Lesson, LessonProgress, Question, User
from ..schemas import CourseIn, FeedbackIn, LessonIn, OrderIn, QuestionIn
from ..serializers import course_out, lesson_out, question_out, stars

router = APIRouter(prefix="/api/teacher", tags=["teacher"])


def _editable_course(db, course_id: int, user) -> Course:
    course = get_course_or_404(db, course_id)
    ensure_can_edit(course, user)
    return course


def _editable_lesson(db, lesson_id: int, user) -> Lesson:
    lesson = db.get(Lesson, lesson_id)
    if lesson is None:
        raise HTTPException(404, "Урок не найден")
    ensure_can_edit(lesson.course, user)
    return lesson


@router.get("/courses")
def my_courses(db: DB, user: Staff):
    stmt = (
        select(Course, func.count(Enrollment.user_id))
        .outerjoin(Enrollment, Enrollment.course_id == Course.id)
        .where(Course.teacher_id == user.id)
        .group_by(Course.id)
        .order_by(Course.created_at.desc())
        .options(selectinload(Course.teacher), selectinload(Course.lessons))
    )
    return [course_out(c, students_count=n) for c, n in db.execute(stmt)]


@router.post("/courses", status_code=201)
def create_course(data: CourseIn, db: DB, user: Staff):
    course = Course(**data.model_dump(), teacher_id=user.id)
    db.add(course)
    db.commit()
    return course_out(course)


@router.get("/courses/{course_id}")
def course_details(course_id: int, db: DB, user: Staff):
    course = _editable_course(db, course_id, user)
    return course_out(course, lessons=[lesson_out(l, with_answers=True) for l in course.lessons])


@router.put("/courses/{course_id}")
def update_course(course_id: int, data: CourseIn, db: DB, user: Staff):
    course = _editable_course(db, course_id, user)
    for key, value in data.model_dump().items():
        setattr(course, key, value)
    db.commit()
    return course_out(course)


@router.delete("/courses/{course_id}", status_code=204)
def delete_course(course_id: int, db: DB, user: Staff):
    db.delete(_editable_course(db, course_id, user))
    db.commit()


# --- Уроки ---


@router.post("/courses/{course_id}/lessons", status_code=201)
def create_lesson(course_id: int, data: LessonIn, db: DB, user: Staff):
    course = _editable_course(db, course_id, user)
    position = data.position if data.position is not None else max((l.position for l in course.lessons), default=0) + 1
    lesson = Lesson(
        course_id=course.id,
        title=data.title,
        content=data.content,
        video_url=data.video_url or None,
        position=position,
    )
    db.add(lesson)
    db.commit()
    return lesson_out(lesson, with_answers=True)


def _apply_order(items: list, ids: list[int]) -> None:
    """Проставляет position по присланному порядку. Список должен содержать ровно те же элементы —
    иначе (например, в другой вкладке урок уже удалили) просим обновить страницу."""
    if len(ids) != len(set(ids)) or set(ids) != {item.id for item in items}:
        raise HTTPException(409, "Список изменился — обновите страницу")
    by_id = {item.id: item for item in items}
    for pos, item_id in enumerate(ids, start=1):
        by_id[item_id].position = pos


@router.put("/courses/{course_id}/lessons/order", status_code=204)
def reorder_lessons(course_id: int, data: OrderIn, db: DB, user: Staff):
    course = _editable_course(db, course_id, user)
    _apply_order(course.lessons, data.ids)
    db.commit()


@router.put("/lessons/{lesson_id}")
def update_lesson(lesson_id: int, data: LessonIn, db: DB, user: Staff):
    lesson = _editable_lesson(db, lesson_id, user)
    lesson.title = data.title
    lesson.content = data.content
    lesson.video_url = data.video_url or None
    if data.position is not None:
        lesson.position = data.position
    db.commit()
    return lesson_out(lesson, with_answers=True)


@router.delete("/lessons/{lesson_id}", status_code=204)
def delete_lesson(lesson_id: int, db: DB, user: Staff):
    db.delete(_editable_lesson(db, lesson_id, user))
    db.commit()


# --- Вопросы теста ---


@router.post("/lessons/{lesson_id}/questions", status_code=201)
def create_question(lesson_id: int, data: QuestionIn, db: DB, user: Staff):
    lesson = _editable_lesson(db, lesson_id, user)
    last = max((x.position for x in lesson.questions), default=0)
    q = Question(lesson_id=lesson.id, position=last + 1, **data.model_dump())
    db.add(q)
    db.commit()
    return question_out(q, with_answer=True)


@router.put("/lessons/{lesson_id}/questions/order", status_code=204)
def reorder_questions(lesson_id: int, data: OrderIn, db: DB, user: Staff):
    lesson = _editable_lesson(db, lesson_id, user)
    _apply_order(lesson.questions, data.ids)
    db.commit()


def _editable_question(db, question_id: int, user) -> Question:
    q = db.get(Question, question_id)
    if q is None:
        raise HTTPException(404, "Вопрос не найден")
    ensure_can_edit(q.lesson.course, user)
    return q


@router.put("/questions/{question_id}")
def update_question(question_id: int, data: QuestionIn, db: DB, user: Staff):
    # Уже сохранённые результаты учеников не пересчитываем: звёзды, полученные
    # по старой версии вопроса, остаются. Новая проверка действует со следующей попытки.
    q = _editable_question(db, question_id, user)
    for key, value in data.model_dump().items():
        setattr(q, key, value)
    db.commit()
    return question_out(q, with_answer=True)


@router.delete("/questions/{question_id}", status_code=204)
def delete_question(question_id: int, db: DB, user: Staff):
    db.delete(_editable_question(db, question_id, user))
    db.commit()


# --- Ученики и отзывы ---


@router.get("/courses/{course_id}/students")
def course_students(course_id: int, db: DB, user: Staff):
    course = _editable_course(db, course_id, user)
    lesson_ids = [l.id for l in course.lessons]
    students = db.scalars(
        select(User)
        .join(Enrollment, Enrollment.user_id == User.id)
        .where(Enrollment.course_id == course.id)
        .order_by(User.name)
    ).all()

    progress: dict[int, dict[int, LessonProgress]] = {}
    if lesson_ids and students:
        rows = db.scalars(
            select(LessonProgress).where(
                LessonProgress.lesson_id.in_(lesson_ids),
                LessonProgress.user_id.in_([s.id for s in students]),
            )
        )
        for p in rows:
            progress.setdefault(p.user_id, {})[p.lesson_id] = p

    return {
        "lessons": [{"id": l.id, "title": l.title} for l in course.lessons],
        "students": [
            {
                "id": s.id,
                "name": s.name,
                "avatar": s.avatar,
                "age": s.age,
                "done": len(progress.get(s.id, {})),
                "results": {
                    lid: {"score": p.score, "total": p.total, "stars": stars(p.score, p.total), "attempts": p.attempts}
                    for lid, p in progress.get(s.id, {}).items()
                },
            }
            for s in students
        ],
    }


@router.post("/courses/{course_id}/feedback", status_code=201)
def leave_feedback(course_id: int, data: FeedbackIn, db: DB, user: Staff):
    course = _editable_course(db, course_id, user)
    if db.get(Enrollment, (data.student_id, course.id)) is None:
        raise HTTPException(400, "Этот ученик не записан на курс")
    db.add(Feedback(course_id=course.id, student_id=data.student_id, teacher_id=user.id, text=data.text.strip()))
    db.commit()
    return {"ok": True}
