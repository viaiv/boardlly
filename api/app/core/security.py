from __future__ import annotations

from typing import Optional

from argon2 import PasswordHasher, exceptions as argon2_exceptions
from fastapi import HTTPException, Request, status

password_hasher = PasswordHasher()


def hash_password(plain_password: str) -> str:
    return password_hasher.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        password_hasher.verify(hashed_password, plain_password)
        return True
    except argon2_exceptions.VerifyMismatchError:
        return False
    except argon2_exceptions.VerificationError:
        return False


SESSION_USER_KEY = "user_id"


def establish_session(request: Request, user_id: str) -> None:
    request.session[SESSION_USER_KEY] = user_id


def clear_session(request: Request) -> None:
    request.session.pop(SESSION_USER_KEY, None)


def current_session_user_id(request: Request) -> Optional[str]:
    return request.session.get(SESSION_USER_KEY)


def ensure_password_strength(password: str) -> None:
    if len(password) < 8:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Senha deve possuir ao menos 8 caracteres.",
        )
