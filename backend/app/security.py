import hashlib
import hmac
import os
import secrets
from datetime import timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .models import AuthSession, User, utcnow

SESSION_COOKIE = "sid"
SESSION_TTL = timedelta(days=14)
# В продакшене за HTTPS выставьте COOKIE_SECURE=1
COOKIE_SECURE = os.getenv("COOKIE_SECURE") == "1"

_SCRYPT = {"n": 2**14, "r": 8, "p": 1, "dklen": 64}


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, **_SCRYPT)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, salt_hex, hash_hex = stored.split("$")
    except ValueError:
        return False
    if algo != "scrypt":
        return False
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), **_SCRYPT)
    # Сравнение за постоянное время — защита от timing-атак
    return hmac.compare_digest(digest.hex(), hash_hex)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(db: Session, user: User) -> str:
    token = secrets.token_urlsafe(32)
    db.add(AuthSession(token_hash=_token_hash(token), user_id=user.id, expires_at=utcnow() + SESSION_TTL))
    # Заодно чистим протухшие сессии
    db.execute(delete(AuthSession).where(AuthSession.expires_at < utcnow()))
    db.commit()
    return token


def user_by_token(db: Session, token: str | None) -> User | None:
    if not token:
        return None
    sess = db.scalar(select(AuthSession).where(AuthSession.token_hash == _token_hash(token)))
    if not sess or sess.expires_at < utcnow() or not sess.user.is_active:
        return None
    return sess.user


def destroy_session(db: Session, token: str | None) -> None:
    if token:
        db.execute(delete(AuthSession).where(AuthSession.token_hash == _token_hash(token)))
        db.commit()


def destroy_user_sessions(db: Session, user_id: int) -> None:
    db.execute(delete(AuthSession).where(AuthSession.user_id == user_id))
