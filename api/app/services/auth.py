from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password, generate_verification_token
from app.models.account import Account
from app.models.user import AppUser


async def count_users(db: AsyncSession) -> int:
    stmt = select(func.count(AppUser.id))
    result = await db.execute(stmt)
    return int(result.scalar_one())


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[AppUser]:
    stmt = select(AppUser).where(AppUser.email == email)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_account(db: AsyncSession, name: str) -> Account:
    account = Account(name=name)
    db.add(account)
    await db.flush()
    return account


async def create_user(
    db: AsyncSession,
    *,
    account: Account | None,
    email: str,
    password: str,
    role: str,
    name: Optional[str] = None,
) -> AppUser:
    hashed = hash_password(password)
    verification_token = generate_verification_token()
    token_expires = datetime.now(timezone.utc) + timedelta(hours=24)

    user = AppUser(
        account_id=account.id if account else None,
        email=email.lower(),
        password_hash=hashed,
        name=name,
        role=role,
        email_verified=False,
        email_verification_token=verification_token,
        email_verification_token_expires=token_expires,
    )
    db.add(user)
    try:
        await db.flush()
    except IntegrityError as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="E-mail já cadastrado.",
        ) from exc
    return user


async def set_account_owner(db: AsyncSession, account: Account, user: AppUser) -> None:
    account.owner_user_id = user.id
    await db.flush()


async def authenticate_user(db: AsyncSession, email: str, password: str) -> AppUser:
    user = await get_user_by_email(db, email.lower())
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")

    # Verificar se o email foi confirmado
    if not user.email_verified:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Email não verificado. Por favor, verifique seu email antes de fazer login."
        )

    return user
