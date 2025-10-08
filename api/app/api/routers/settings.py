from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.account import Account
from app.models.account_github_credentials import AccountGithubCredentials
from app.models.project_member import ProjectMember
from app.models.user import AppUser
from app.schemas.github import (
    GithubProjectRequest,
    GithubProjectSummary,
    GithubTokenRequest,
    GithubProjectResponse,
)
from app.services.github import (
    fetch_project_metadata,
    get_github_token,
    store_github_token,
    upsert_github_project,
    GithubGraphQLClient,
    list_projects,
)

router = APIRouter(prefix="/settings", tags=["settings"])


@router.post("/github-token", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def configure_github_token(
    payload: GithubTokenRequest,
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.require_roles("owner", "admin")),
) -> Response:
    account = await db.get(Account, current_user.account_id) if current_user.account_id else None
    if not account:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Usuário não possui conta para configurar")
    if not payload.token or len(payload.token.strip()) < 10:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Token inválido")

    await store_github_token(db, account, payload.token.strip())
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/github-token")
async def github_token_status(
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.require_roles("owner", "admin")),
) -> dict[str, bool]:
    account = await db.get(Account, current_user.account_id) if current_user.account_id else None
    if not account:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Usuário não possui conta para configurar")

    credentials = await db.get(AccountGithubCredentials, account.id)
    return {"configured": credentials is not None}


@router.post("/github-project", response_model=GithubProjectResponse)
async def configure_github_project(
    payload: GithubProjectRequest,
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.require_roles("owner", "admin")),
) -> GithubProjectResponse:
    account = await db.get(Account, current_user.account_id) if current_user.account_id else None
    if not account:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Usuário não possui conta para configurar")

    token = await get_github_token(db, account)

    async with GithubGraphQLClient(token) as client:
        metadata = await fetch_project_metadata(client, payload.owner, payload.project_number)

    project = await upsert_github_project(db, account, metadata)

    # Adicionar owner como admin do projeto automaticamente (se ainda não for membro)
    stmt = select(ProjectMember).where(
        ProjectMember.user_id == current_user.id,
        ProjectMember.project_id == project.id
    )
    result = await db.execute(stmt)
    existing_member = result.scalar_one_or_none()

    if not existing_member:
        owner_member = ProjectMember(
            user_id=current_user.id,
            project_id=project.id,
            role="admin"
        )
        db.add(owner_member)

    await db.commit()
    await db.refresh(project)

    return GithubProjectResponse.model_validate(project)


@router.get("/github-projects", response_model=list[GithubProjectSummary])
async def list_github_projects(
    owner: str,
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.require_roles("owner", "admin")),
) -> list[GithubProjectSummary]:
    account = await db.get(Account, current_user.account_id) if current_user.account_id else None
    if not account:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Usuário não possui conta para configurar")

    token = await get_github_token(db, account)

    async with GithubGraphQLClient(token) as client:
        summaries = await list_projects(client, owner.strip())

    return [GithubProjectSummary.model_validate(asdict(summary)) for summary in summaries]
