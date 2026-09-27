"""Публичный каталог + всё, что делает ученик: запись на курс, уроки, тесты, прогресс."""

from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from ..deps import DB, CurrentUser, OptionalUser, Student, get_course_or_404
from ..grading import is_text_answer_correct
from ..models import Course, Enrollment, Feedback, Lesson, LessonProgress, Question, User
from ..schemas import SubmitIn
from ..serializers import course_out, lesson_out, stars

router = APIRouter(prefix="/api", tags=["courses"])


def _progress_map(db, user_id: int, lesson_ids: list[int]) -> dict[int, LessonProgress]:
    if not lesson_ids:
        return {}
    rows = db.scalars(
        select(LessonProgress).where(LessonProgress.user_id == user_id, LessonProgress.lesson_id.in_(lesson_ids))
    )
    return {p.lesson_id: p for p in rows}


def _is_enrolled(db, user_id: int, course_id: int) -> bool:
    return db.get(Enrollment, (user_id, course_id)) is not None


def _can_view_course(course: Course, user: User | None) -> bool:
    if course.is_published:
        return True
    return user is not None and (user.role == "admin" or course.teacher_id == user.id)


@router.get("/courses")
def list_courses(db: DB, subject: str | None = None, age: int | None = None, q: str | None = None):
    stmt = (
        select(Course)
        .where(Course.is_published.is_(True))
        .options(selectinload(Course.teacher), selectinload(Course.lessons))
        .order_by(Course.created_at.desc())
    )
    if subject in ("english", "math"):
        stmt = stmt.where(Course.subject == subject)
    if age is not None:
        stmt = stmt.where(Course.min_age <= age, Course.max_age >= age)
    if q:
        stmt = stmt.where(Course.title.ilike(f"%{q.strip()[:50]}%"))
    return [course_out(c) for c in db.scalars(stmt)]


@router.get("/courses/{course_id}")
def get_course(course_id: int, db: DB, user: OptionalUser):
    course = get_course_or_404(db, course_id)
    if not _can_view_course(course, user):
        raise HTTPException(404, "Курс не найден")

    enrolled = bool(user and user.role == "student" and _is_enrolled(db, user.id, course.id))
    progress = _progress_map(db, user.id, [l.id for l in course.lessons]) if enrolled else {}
    students = db.scalar(select(func.count()).select_from(Enrollment).where(Enrollment.course_id == course.id))

    return course_out(
        course,
        enrolled=enrolled,
        students_count=students,
        can_edit=bool(user and (user.role == "admin" or course.teacher_id == user.id)),
        lessons=[
            {
                "id": l.id,
                "title": l.title,
                "questions_count": len(l.questions),
                "done": l.id in progress,
                "stars": stars(progress[l.id].score, progress[l.id].total) if l.id in progress else None,
            }
            for l in course.lessons
        ],
    )


@router.post("/courses/{course_id}/enroll", status_code=201)
def enroll(course_id: int, db: DB, user: Student):
    course = get_course_or_404(db, course_id)
    if not course.is_published:
        raise HTTPException(404, "Курс не найден")
    if user.age is not None and not (course.min_age <= user.age <= course.max_age):
        raise HTTPException(400, f"Этот курс для возраста {course.min_age}–{course.max_age} лет")
    if not _is_enrolled(db, user.id, course.id):
        db.add(Enrollment(user_id=user.id, course_id=course.id))
        db.commit()
    return {"ok": True}


@router.delete("/courses/{course_id}/enroll", status_code=204)
def unenroll(course_id: int, db: DB, user: Student):
    enrollment = db.get(Enrollment, (user.id, course_id))
    if enrollment:
        db.delete(enrollment)
        db.commit()


def _lesson_for_user(db, lesson_id: int, user: User) -> Lesson:
    lesson = db.get(Lesson, lesson_id)
    if lesson is None:
        raise HTTPException(404, "Урок не найден")
    course = lesson.course
    if user.role == "student":
        if not course.is_published or not _is_enrolled(db, user.id, course.id):
            raise HTTPException(403, "Сначала запишитесь на курс")
    elif user.role == "teacher" and course.teacher_id != user.id:
        raise HTTPException(403, "Это не ваш курс")
    return lesson


@router.get("/lessons/{lesson_id}")
def get_lesson(lesson_id: int, db: DB, user: CurrentUser):
    lesson = _lesson_for_user(db, lesson_id, user)
    lessons = lesson.course.lessons
    idx = next(i for i, l in enumerate(lessons) if l.id == lesson.id)
    progress = db.get(LessonProgress, (user.id, lesson.id))
    # Ученику правильные ответы не отдаём — проверка только на сервере
    data = lesson_out(lesson, with_answers=user.role != "student")
    data.update(
        course={"id": lesson.course.id, "title": lesson.course.title, "subject": lesson.course.subject},
        index=idx + 1,
        total_lessons=len(lessons),
        prev_id=lessons[idx - 1].id if idx > 0 else None,
        next_id=lessons[idx + 1].id if idx + 1 < len(lessons) else None,
        progress=(
            {"score": progress.score, "total": progress.total, "stars": stars(progress.score, progress.total)}
            if progress
            else None
        ),
    )
    return data


def _check_answer(q: Question, answer: int | str | None) -> dict:
    """Результат по одному вопросу. Правильный ответ показываем уже после сдачи — чтобы ребёнок учился на ошибке."""
    if q.kind == "text":
        given = answer if isinstance(answer, str) else None
        return {
            "question_id": q.id,
            "correct": is_text_answer_correct(given, q.accepted, q.match_numeric),
            "expected": q.accepted[0],
        }
    chosen = answer if isinstance(answer, int) else None
    return {"question_id": q.id, "correct": chosen == q.correct_index, "correct_index": q.correct_index}


@router.post("/lessons/{lesson_id}/submit")
def submit_lesson(lesson_id: int, data: SubmitIn, db: DB, user: Student):
    lesson = _lesson_for_user(db, lesson_id, user)
    questions = lesson.questions
    answers = data.answers + [None] * (len(questions) - len(data.answers))
    results = [_check_answer(q, a) for q, a in zip(questions, answers)]
    score = sum(r["correct"] for r in results)
    total = len(questions)

    progress = db.get(LessonProgress, (user.id, lesson.id))
    if progress is None:
        db.add(LessonProgress(user_id=user.id, lesson_id=lesson.id, score=score, total=total))
        best = score
    else:
        progress.attempts += 1
        # Храним лучший результат, чтобы повторная попытка не «отнимала» звёзды
        if score >= progress.score or progress.total != total:
            progress.score, progress.total = score, total
        best = progress.score
    db.commit()
    return {"score": score, "total": total, "stars": stars(score, total), "best": best, "results": results}


@router.get("/me/dashboard")
def student_dashboard(db: DB, user: Student):
    enrollments = db.scalars(
        select(Enrollment)
        .where(Enrollment.user_id == user.id)
        .options(selectinload(Enrollment.course).selectinload(Course.lessons))
        .order_by(Enrollment.enrolled_at.desc())
    ).all()

    all_lesson_ids = [l.id for e in enrollments for l in e.course.lessons]
    progress = _progress_map(db, user.id, all_lesson_ids)

    courses = []
    for e in enrollments:
        c = e.course
        done = [l for l in c.lessons if l.id in progress]
        next_lesson = next((l for l in c.lessons if l.id not in progress), None)
        courses.append(
            course_out(
                c,
                done=len(done),
                stars=sum(stars(progress[l.id].score, progress[l.id].total) for l in done),
                next_lesson_id=next_lesson.id if next_lesson else None,
            )
        )

    feedback = db.scalars(
        select(Feedback).where(Feedback.student_id == user.id).order_by(Feedback.created_at.desc()).limit(20)
    )
    return {
        "courses": courses,
        "total_stars": sum(c["stars"] for c in courses),
        "lessons_done": len(progress),
        "feedback": [
            {
                "id": f.id,
                "text": f.text,
                "created_at": f.created_at.isoformat(),
                "course": {"id": f.course.id, "title": f.course.title},
                "teacher": {"name": f.teacher.name, "avatar": f.teacher.avatar},
            }
            for f in feedback
        ],
    }
