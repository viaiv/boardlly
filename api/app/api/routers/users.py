from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.user import AppUser
from app.schemas.auth import UserResponse
from app.api.routers.auth import build_user_response

router = APIRouter(tags=["users"])


@router.get("/me", response_model=UserResponse)
async def read_current_user(current_user: AppUser = Depends(deps.get_current_user)) -> UserResponse:
    return build_user_response(current_user)


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.require_roles("admin", "owner")),
) -> list[UserResponse]:
    if current_user.account_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Usuário ainda não possui conta")

    stmt = select(AppUser).where(AppUser.account_id == current_user.account_id)
    result = await db.execute(stmt)
    members = result.scalars().all()
    return [build_user_response(member) for member in members]
