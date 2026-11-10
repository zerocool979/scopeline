from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from .config import settings

_ph = PasswordHasher()


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _ph.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


DUMMY_HASH = hash_password("dummy-password-for-timing")


def create_token(user) -> str:
    exp = datetime.now(UTC) + timedelta(minutes=settings.token_minutes)
    return jwt.encode({"sub": str(user.id), "tv": user.token_version, "exp": exp},
                      settings.secret_key, algorithm="HS256")


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.secret_key, algorithms=["HS256"])
