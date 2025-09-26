from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import SessionLocal
from app.models.user import AppUser


async def get_db() -> AsyncSession:
    async with SessionLocal() as session:
        yield session


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> AppUser:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Sessão inválida")

    stmt = select(AppUser).where(AppUser.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado")
    return user


async def get_optional_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Optional[AppUser]:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    stmt = select(AppUser).where(AppUser.id == user_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


def require_roles(*roles: str):
    async def dependency(user: AppUser = Depends(get_current_user)) -> AppUser:
        if roles and user.role not in roles:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail="Permissão insuficiente",
            )
        return user

    return dependency
