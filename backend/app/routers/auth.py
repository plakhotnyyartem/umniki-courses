import time
from collections import defaultdict, deque

from fastapi import APIRouter, Cookie, HTTPException, Request, Response
from sqlalchemy import select

from ..deps import DB, CurrentUser, OptionalUser
from ..models import User
from ..schemas import LoginIn, ProfileIn, RegisterIn
from ..security import (
    COOKIE_SECURE,
    SESSION_COOKIE,
    SESSION_TTL,
    create_session,
    destroy_session,
    hash_password,
    verify_password,
)
from ..serializers import user_out

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Простейшее ограничение перебора паролей: не больше 10 неудачных попыток за 15 минут
# для пары «IP + email». Email в ключе нужен за прокси хостинга, где IP у всех может
# оказаться одинаковым: иначе один человек с неверным паролем заблокировал бы вход всем.
# Для нескольких процессов/серверов это нужно вынести в Redis.
_FAILS: dict[str, deque] = defaultdict(deque)
_WINDOW, _MAX_FAILS = 15 * 60, 10


def _too_many_fails(key: str) -> bool:
    q = _FAILS[key]
    while q and q[0] < time.monotonic() - _WINDOW:
        q.popleft()
    return len(q) >= _MAX_FAILS


def _set_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=int(SESSION_TTL.total_seconds()),
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,
    )


@router.post("/register", status_code=201)
def register(data: RegisterIn, response: Response, db: DB):
    if db.scalar(select(User).where(User.email == data.email)):
        raise HTTPException(409, "Этот email уже зарегистрирован")
    user = User(
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        role="student",
        age=data.age,
        avatar=data.avatar,
    )
    db.add(user)
    db.commit()
    _set_cookie(response, create_session(db, user))
    return user_out(user)


def _client_ip(request: Request) -> str:
    ip = request.client.host if request.client else "?"
    # За туннелем Cloudflare все запросы приходят с localhost, а настоящий адрес — в заголовке.
    # Доверяем ему только для локальных подключений, иначе его легко подделать.
    if ip in ("127.0.0.1", "::1"):
        return request.headers.get("cf-connecting-ip", ip)
    return ip


@router.post("/login")
def login(data: LoginIn, request: Request, response: Response, db: DB):
    key = f"{_client_ip(request)}|{data.email}"
    if _too_many_fails(key):
        raise HTTPException(429, "Слишком много попыток. Попробуйте через 15 минут.")
    user = db.scalar(select(User).where(User.email == data.email))
    if not user or not verify_password(data.password, user.password_hash):
        _FAILS[key].append(time.monotonic())
        raise HTTPException(401, "Неверный email или пароль")
    if not user.is_active:
        raise HTTPException(403, "Аккаунт заблокирован. Обратитесь к администратору.")
    _FAILS.pop(key, None)
    _set_cookie(response, create_session(db, user))
    return user_out(user)


@router.post("/logout", status_code=204)
def logout(response: Response, db: DB, sid: str | None = Cookie(default=None, alias=SESSION_COOKIE)):
    destroy_session(db, sid)
    response.delete_cookie(SESSION_COOKIE)


@router.get("/me")
def me(user: OptionalUser):
    return {"user": user_out(user) if user else None}


@router.put("/me")
def update_profile(data: ProfileIn, user: CurrentUser, db: DB):
    user.name = data.name.strip()
    user.avatar = data.avatar
    db.commit()
    return user_out(user)
