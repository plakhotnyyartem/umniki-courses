import re
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StrictInt, field_validator, model_validator

MIN_AGE, MAX_AGE = 5, 14
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

Subject = Literal["english", "math"]
Role = Literal["admin", "teacher", "student"]
Age = Field(ge=MIN_AGE, le=MAX_AGE)


def _email(v: str) -> str:
    v = v.strip().lower()
    if not EMAIL_RE.match(v):
        raise ValueError("Некорректный email")
    return v


class LoginIn(BaseModel):
    email: str
    password: str

    _norm = field_validator("email")(_email)


class RegisterIn(BaseModel):
    """Самостоятельная регистрация доступна только ученикам."""

    name: str = Field(min_length=2, max_length=80)
    email: str
    password: str = Field(min_length=8, max_length=128)
    age: int = Age
    avatar: str = Field(default="🙂", max_length=8)

    _norm = field_validator("email")(_email)

    @field_validator("name")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()


class ProfileIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    avatar: str = Field(max_length=8)


class UserCreateIn(BaseModel):
    """Создание пользователя администратором (в т.ч. преподавателей)."""

    name: str = Field(min_length=2, max_length=80)
    email: str
    password: str = Field(min_length=8, max_length=128)
    role: Role
    age: int | None = Field(default=None, ge=MIN_AGE, le=MAX_AGE)

    _norm = field_validator("email")(_email)

    @model_validator(mode="after")
    def _student_needs_age(self):
        if self.role == "student" and self.age is None:
            raise ValueError("Для ученика нужно указать возраст")
        if self.role != "student":
            self.age = None
        return self


class UserUpdateIn(BaseModel):
    role: Role | None = None
    is_active: bool | None = None


class CourseIn(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    description: str = Field(default="", max_length=3000)
    subject: Subject
    min_age: int = Age
    max_age: int = Age
    cover: str = Field(default="📘", max_length=8)
    is_published: bool = False

    @model_validator(mode="after")
    def _age_range(self):
        if self.min_age > self.max_age:
            raise ValueError("Минимальный возраст больше максимального")
        return self


class LessonIn(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    content: str = Field(default="", max_length=20000)
    video_url: str | None = Field(default=None, max_length=300)
    position: int | None = None


class QuestionIn(BaseModel):
    kind: Literal["choice", "text"] = "choice"
    text: str = Field(min_length=1, max_length=500)
    # для kind='choice'
    options: list[str] = Field(default_factory=list, max_length=6)
    correct_index: int | None = Field(default=None, ge=0)
    # для kind='text'
    accepted: list[str] = Field(default_factory=list, max_length=10)
    match_numeric: bool = True

    @field_validator("options", "accepted")
    @classmethod
    def _clean(cls, v: list[str]) -> list[str]:
        return [o.strip()[:200] for o in v]

    @model_validator(mode="after")
    def _by_kind(self):
        if self.kind == "choice":
            if len(self.options) < 2:
                raise ValueError("Нужно минимум 2 варианта ответа")
            if any(not o for o in self.options):
                raise ValueError("Варианты ответа не должны быть пустыми")
            if self.correct_index is None or self.correct_index >= len(self.options):
                raise ValueError("Неверный номер правильного ответа")
            self.accepted = []
        else:
            self.accepted = [a for a in self.accepted if a]
            if not self.accepted:
                raise ValueError("Укажите хотя бы один правильный ответ")
            self.options, self.correct_index = [], None
        return self


class SubmitIn(BaseModel):
    # Для вопроса с выбором — номер варианта, для вопроса с вводом — строка.
    # StrictInt: без него Pydantic превратит true в 1, и это засчитается как вариант №1.
    answers: list[StrictInt | Annotated[str, Field(max_length=200)] | None] = Field(max_length=100)


class FeedbackIn(BaseModel):
    student_id: int
    text: str = Field(min_length=1, max_length=2000)


class OrderIn(BaseModel):
    """Полный список id в новом порядке."""

    ids: list[int] = Field(max_length=500)


class PublishIn(BaseModel):
    is_published: bool
