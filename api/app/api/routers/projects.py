from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.account import Account
from app.models.github_project import GithubProject
from app.models.project_item import ProjectItem
from app.models.user import AppUser
from app.schemas.github import (
    GithubProjectResponse,
    ProjectItemAuthorResponse,
    ProjectItemCommentResponse,
    ProjectItemDetailResponse,
    ProjectItemLabelResponse,
    ProjectItemResponse,
    ProjectItemUpdateRequest,
)
from app.services.github import (
    GithubGraphQLClient,
    apply_local_project_item_updates,
    fetch_project_item_comments,
    fetch_project_item_details,
    get_github_token,
    parse_datetime,
)

router = APIRouter(prefix="/projects", tags=["projects"])


async def _get_account_or_404(db: AsyncSession, current_user: AppUser) -> Account:
    if current_user.account_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Usuário não possui conta configurada")
    account = await db.get(Account, current_user.account_id)
    if not account:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Conta não encontrada")
    return account


async def _get_project_or_404(db: AsyncSession, account: Account) -> GithubProject:
    stmt = select(GithubProject).where(GithubProject.account_id == account.id)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Projeto GitHub não configurado")
    return project


@router.get("/current", response_model=GithubProjectResponse)
async def get_current_project(
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.get_current_user),
) -> GithubProjectResponse:
    account = await _get_account_or_404(db, current_user)
    project = await _get_project_or_404(db, account)
    return GithubProjectResponse.model_validate(project)


@router.get("/current/items", response_model=list[ProjectItemResponse])
async def list_current_project_items(
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.get_current_user),
) -> list[ProjectItemResponse]:
    account = await _get_account_or_404(db, current_user)
    project = await _get_project_or_404(db, account)
    stmt = (
        select(ProjectItem)
        .where(ProjectItem.project_id == project.id)
        .order_by(
            ProjectItem.start_date.asc().nulls_last(),
            ProjectItem.end_date.asc().nulls_last(),
            ProjectItem.updated_at.desc().nullslast(),
        )
    )
    result = await db.execute(stmt)
    items = result.scalars().all()
    return [ProjectItemResponse.model_validate(item) for item in items]


@router.patch("/current/items/{item_id}", response_model=ProjectItemResponse)
async def update_project_item(
    item_id: int,
    payload: ProjectItemUpdateRequest,
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.require_roles("owner", "admin")),
) -> ProjectItemResponse:
    account = await _get_account_or_404(db, current_user)
    project = await _get_project_or_404(db, account)

    item = await db.get(ProjectItem, item_id)
    if not item or item.project_id != project.id or item.account_id != account.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Item não encontrado")

    data = payload.model_dump(exclude_unset=True)

    remote_timestamp = data.get("remote_updated_at")
    if remote_timestamp and item.remote_updated_at and remote_timestamp < item.remote_updated_at:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="O item foi atualizado no GitHub recentemente. Recarregue e tente novamente.",
        )

    updates = {
        key: value
        for key, value in data.items()
        if key
        in {"start_date", "end_date", "due_date", "iteration_id", "iteration_title", "status"}
    }

    if not updates:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Nenhuma alteração informada")

    await apply_local_project_item_updates(db, account, project, item, updates, current_user.id)
    await db.commit()
    await db.refresh(item)
    return ProjectItemResponse.model_validate(item)


@router.get("/current/items/{item_id}/comments", response_model=list[ProjectItemCommentResponse])
async def list_project_item_comments(
    item_id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.get_current_user),
) -> list[ProjectItemCommentResponse]:
    account = await _get_account_or_404(db, current_user)
    project = await _get_project_or_404(db, account)

    item = await db.get(ProjectItem, item_id)
    if not item or item.project_id != project.id or item.account_id != account.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Item não encontrado")

    if not item.content_node_id:
        return []

    token = await get_github_token(db, account)

    async with GithubGraphQLClient(token) as client:
        raw_comments = await fetch_project_item_comments(client, item.content_node_id)

    comments: list[ProjectItemCommentResponse] = []
    for comment in raw_comments:
        if not comment.get("id"):
            continue
        comments.append(
            ProjectItemCommentResponse(
                id=str(comment.get("id")),
                body=str(comment.get("body") or ""),
                author=comment.get("author_login"),
                author_url=comment.get("author_url"),
                author_avatar_url=comment.get("author_avatar_url"),
                url=comment.get("url"),
                created_at=parse_datetime(comment.get("created_at")),
                updated_at=parse_datetime(comment.get("updated_at")),
            )
        )

    return sorted(
        comments,
        key=lambda value: value.created_at.timestamp() if value.created_at else float("inf"),
    )


@router.get("/current/items/{item_id}/details", response_model=ProjectItemDetailResponse)
async def get_project_item_details(
    item_id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.get_current_user),
) -> ProjectItemDetailResponse:
    account = await _get_account_or_404(db, current_user)
    project = await _get_project_or_404(db, account)

    item = await db.get(ProjectItem, item_id)
    if not item or item.project_id != project.id or item.account_id != account.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Item não encontrado")

    if not item.content_node_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Item não possui conteúdo no GitHub")

    token = await get_github_token(db, account)

    async with GithubGraphQLClient(token) as client:
        details_raw = await fetch_project_item_details(client, item.content_node_id)

    if not details_raw:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Detalhes não encontrados no GitHub")

    labels = [
        ProjectItemLabelResponse(name=str(label.get("name")), color=label.get("color"))
        for label in details_raw.get("labels", [])
        if isinstance(label, dict) and label.get("name")
    ]

    author = None
    if any(details_raw.get(key) for key in ("author_login", "author_url", "author_avatar_url")):
        author = ProjectItemAuthorResponse(
            login=details_raw.get("author_login"),
            url=details_raw.get("author_url"),
            avatar_url=details_raw.get("author_avatar_url"),
        )

    return ProjectItemDetailResponse(
        id=str(details_raw.get("id")),
        content_type=details_raw.get("content_type"),
        number=details_raw.get("number"),
        title=details_raw.get("title") or item.title,
        body=details_raw.get("body"),
        body_text=details_raw.get("body_text"),
        state=details_raw.get("state"),
        merged=details_raw.get("merged"),
        url=details_raw.get("url") or item.url,
        created_at=parse_datetime(details_raw.get("created_at")),
        updated_at=parse_datetime(details_raw.get("updated_at")),
        author=author,
        labels=labels,
    )


@router.post("/current/statuses", response_model=list[str])
async def update_status_columns(
    payload: dict,
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.require_roles("owner", "admin")),
) -> list[str]:
    account = await _get_account_or_404(db, current_user)
    project = await _get_project_or_404(db, account)

    columns = payload.get("columns")
    if not isinstance(columns, list):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Columns deve ser uma lista")

    cleaned: list[str] = []
    for item in columns:
        if not isinstance(item, str):
            continue
        name = item.strip()
        if not name or name.lower() == "done":
            continue
        if name not in cleaned:
            cleaned.append(name)

    cleaned.append("Done")
    project.status_columns = cleaned
    await db.commit()
    await db.refresh(project)
    return cleaned
