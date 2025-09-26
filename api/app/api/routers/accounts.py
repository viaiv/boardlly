from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.user import AppUser
from app.schemas.account import AccountCreateRequest, AccountResponse
from app.services.auth import create_account, set_account_owner

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.post("", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account_endpoint(
    payload: AccountCreateRequest,
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.require_roles("owner")),
) -> AccountResponse:
    if current_user.account_id is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Usuário já pertence a uma conta")

    account = await create_account(db, payload.name)
    current_user.account_id = account.id
    await set_account_owner(db, account, current_user)

    await db.commit()
    await db.refresh(account)
    await db.refresh(current_user)

    return AccountResponse.model_validate(account)
