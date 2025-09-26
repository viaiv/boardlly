from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.account import Account
from app.models.github_project import GithubProject
from app.models.user import AppUser
from app.schemas.github import GithubProjectResponse
from app.services.github import get_github_token, sync_github_project

router = APIRouter(prefix="/github", tags=["github"])


@router.post("/sync/{project_id}")
async def sync_project(
    project_id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.require_roles("owner", "admin")),
) -> dict[str, int]:
    account = await db.get(Account, current_user.account_id) if current_user.account_id else None
    if not account:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Usuário não possui conta")

    project = await db.get(GithubProject, project_id)
    if not project or project.account_id != account.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Projeto não encontrado")

    token = await get_github_token(db, account)
    count = await sync_github_project(db, account, project, token)
    return {"synced_items": count}
