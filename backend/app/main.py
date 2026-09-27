from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import bootstrap
from .db import ROOT_DIR, Base, engine
from .migrations import run_migrations
from .routers import admin, auth, courses, teacher

Base.metadata.create_all(engine)
run_migrations(engine)
bootstrap.run()

app = FastAPI(title="Умники — курсы английского и математики")

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


@app.middleware("http")
async def csrf_and_headers(request: Request, call_next):
    # Защита от CSRF: изменяющие запросы к API должны приходить из нашего JS (fetch с этим заголовком).
    # Обычная HTML-форма с чужого сайта не может выставить свой заголовок, а cross-origin fetch
    # с ним упрётся в CORS preflight, который мы не разрешаем.
    if (
        request.method in UNSAFE_METHODS
        and request.url.path.startswith("/api/")
        and request.headers.get("x-requested-with") != "fetch"
    ):
        return JSONResponse({"detail": "CSRF-проверка не пройдена"}, status_code=403)

    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    # Без Cache-Control браузер сам решает, сколько хранить файл, и может долго показывать
    # старую (или оборванную) копию CSS/JS. no-cache = перед использованием спросить сервер;
    # если файл не менялся, сервер ответит коротким 304 по ETag.
    response.headers.setdefault("Cache-Control", "no-store" if request.url.path.startswith("/api/") else "no-cache")
    return response


FIELD_NAMES = {
    "name": "Имя",
    "email": "Email",
    "password": "Пароль",
    "age": "Возраст",
    "title": "Название",
    "description": "Описание",
    "min_age": "Возраст от",
    "max_age": "Возраст до",
    "options": "Варианты ответа",
    "text": "Текст",
}


def _humanize(err: dict) -> str:
    field = next((str(p) for p in reversed(err.get("loc", ())) if isinstance(p, str) and p != "body"), "")
    ctx = err.get("ctx") or {}
    msg = {
        "string_too_short": f"минимум {ctx.get('min_length')} символов",
        "string_too_long": f"максимум {ctx.get('max_length')} символов",
        "greater_than_equal": f"не меньше {ctx.get('ge')}",
        "less_than_equal": f"не больше {ctx.get('le')}",
        "missing": "обязательное поле",
        "int_parsing": "должно быть числом",
        "too_short": f"минимум {ctx.get('min_length')} элемента",
    }.get(err.get("type"))
    if msg is None:
        # Наши собственные ValueError из валидаторов уже на русском
        msg = str(ctx.get("error") or err.get("msg", "некорректное значение")).removeprefix("Value error, ")
    label = FIELD_NAMES.get(field)
    return f"{label}: {msg}" if label else msg


@app.exception_handler(RequestValidationError)
async def validation_handler(_: Request, exc: RequestValidationError):
    return JSONResponse({"detail": _humanize(exc.errors()[0])}, status_code=422)


app.include_router(auth.router)
app.include_router(courses.router)
app.include_router(teacher.router)
app.include_router(admin.router)

# Фронтенд: обычные HTML-страницы (/ → index.html, /login.html и т.д.)
app.mount("/", StaticFiles(directory=ROOT_DIR / "frontend", html=True), name="frontend")
