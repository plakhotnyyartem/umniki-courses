"""Преобразование ORM-объектов в JSON для фронтенда."""

from urllib.parse import parse_qs, urlparse

from .models import Course, Lesson, Question, User


def youtube_embed(url: str | None) -> str | None:
    """Ссылку YouTube превращаем в адрес для <iframe>; другие ссылки не встраиваем."""
    if not url:
        return None
    try:
        u = urlparse(url)
    except ValueError:
        return None
    host = (u.hostname or "").lower()
    vid = None
    if host == "youtu.be":
        vid = u.path.lstrip("/")
    elif host == "youtube.com" or host.endswith(".youtube.com"):
        vid = parse_qs(u.query).get("v", [None])[0]
        parts = u.path.strip("/").split("/")
        if not vid and len(parts) == 2 and parts[0] in ("embed", "shorts"):
            vid = parts[1]
    if vid and 6 <= len(vid) <= 20 and all(c.isalnum() or c in "-_" for c in vid):
        return f"https://www.youtube-nocookie.com/embed/{vid}"
    return None


def stars(score: int, total: int) -> int:
    """3 звезды — всё верно, 2 — от 70%, 1 — от 40%."""
    if total == 0:
        return 3
    p = score / total
    return 3 if p == 1 else 2 if p >= 0.7 else 1 if p >= 0.4 else 0


def user_out(u: User) -> dict:
    return {
        "id": u.id,
        "name": u.name,
        "email": u.email,
        "role": u.role,
        "age": u.age,
        "avatar": u.avatar,
        "is_active": u.is_active,
        "created_at": u.created_at.isoformat(),
    }


def course_out(c: Course, **extra) -> dict:
    return {
        "id": c.id,
        "title": c.title,
        "description": c.description,
        "subject": c.subject,
        "min_age": c.min_age,
        "max_age": c.max_age,
        "cover": c.cover,
        "is_published": c.is_published,
        "teacher": {"id": c.teacher.id, "name": c.teacher.name, "avatar": c.teacher.avatar},
        "lessons_count": len(c.lessons),
        **extra,
    }


def question_out(q: Question, with_answer: bool) -> dict:
    data = {"id": q.id, "kind": q.kind, "text": q.text, "options": q.options}
    if with_answer:
        data.update(correct_index=q.correct_index, accepted=q.accepted, match_numeric=q.match_numeric)
    return data


def lesson_out(lesson: Lesson, with_answers: bool = False) -> dict:
    return {
        "id": lesson.id,
        "course_id": lesson.course_id,
        "title": lesson.title,
        "content": lesson.content,
        "video_url": lesson.video_url,
        "video_embed": youtube_embed(lesson.video_url),
        "position": lesson.position,
        "questions": [question_out(q, with_answers) for q in lesson.questions],
    }
