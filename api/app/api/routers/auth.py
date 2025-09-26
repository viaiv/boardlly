from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.security import clear_session, ensure_password_strength, establish_session
from app.models.account import Account
from app.models.user import AppUser
from app.schemas.auth import LoginRequest, RegisterRequest, UserResponse
from app.services.auth import (
    authenticate_user,
    count_users,
    create_user,
    get_user_by_email,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def build_user_response(user: AppUser) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        account_id=user.account_id,
        needs_account_setup=user.account_id is None,
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    payload: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser | None = Depends(deps.get_optional_current_user),
) -> UserResponse:
    total_users = await count_users(db)
    email_exists = await get_user_by_email(db, payload.email)
    if email_exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="E-mail já cadastrado")

    ensure_password_strength(payload.password)

    account: Account | None = None
    role: str

    if total_users == 0:
        role = "owner"
    else:
        if current_user is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Autenticação necessária")
        if current_user.role not in {"admin", "owner"}:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Permissão insuficiente")
        account = await db.get(Account, current_user.account_id)
        if not account:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Conta não encontrada")
        role = payload.role

    user = await create_user(
        db,
        account=account,
        email=payload.email,
        password=payload.password,
        role=role,
        name=payload.name,
    )

    if total_users == 0:
        establish_session(request, str(user.id))

    await db.commit()
    await db.refresh(user)

    return build_user_response(user)


@router.post("/login", response_model=UserResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(deps.get_db),
) -> UserResponse:
    user = await authenticate_user(db, payload.email, payload.password)
    establish_session(request, str(user.id))
    await db.commit()
    await db.refresh(user)
    return build_user_response(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def logout(request: Request) -> Response:
    clear_session(request)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
