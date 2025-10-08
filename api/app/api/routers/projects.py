from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any, Iterable

from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.account import Account
from app.models.github_project import GithubProject
from app.models.github_project_field import GithubProjectField
from app.models.project_item import ProjectItem
from app.models.user import AppUser
from app.schemas.github import (
    GithubProjectResponse,
    EpicDashboardResponse,
    EpicDetailResponse,
    EpicOptionResponse,
    EpicOptionCreateRequest,
    EpicOptionUpdateRequest,
    EpicCreateRequest,
    EpicCreateResponse,
    EpicSummaryResponse,
    IterationDashboardResponse,
    IterationOptionResponse,
    IterationSummaryResponse,
    ProjectItemAuthorResponse,
    ProjectItemCommentResponse,
    ProjectItemDetailResponse,
    ProjectItemLabelResponse,
    ProjectItemResponse,
    ProjectItemUpdateRequest,
    StatusBreakdownEntry,
)
from app.services.github import (
    GithubGraphQLClient,
    apply_local_project_item_updates,
    create_epic_issue,
    fetch_project_item_comments,
    fetch_project_item_details,
    get_github_token,
    list_epic_options,
    create_epic_option,
    update_epic_option,
    delete_epic_option,
    list_iteration_options,
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
    status: str | None = None,
    iteration: str | None = None,
    epic: str | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.get_current_user),
) -> list[ProjectItemResponse]:
    """
    Lista itens do projeto atual com filtros opcionais.

    **Filtros:**
    - `status`: Filtrar por status (ex: "Backlog", "Todo", "In Progress", "Done")
    - `iteration`: Filtrar por sprint/iteration
    - `epic`: Filtrar por epic
    - `search`: Buscar no título
    """
    account = await _get_account_or_404(db, current_user)
    project = await _get_project_or_404(db, account)

    stmt = select(ProjectItem).where(ProjectItem.project_id == project.id)

    # Aplicar filtros
    if status:
        stmt = stmt.where(ProjectItem.status == status)
    if iteration:
        stmt = stmt.where(ProjectItem.iteration == iteration)
    if epic:
        stmt = stmt.where(ProjectItem.epic == epic)
    if search:
        stmt = stmt.where(ProjectItem.title.ilike(f"%{search}%"))

    # Ordenação
    stmt = stmt.order_by(
        ProjectItem.start_date.asc().nulls_last(),
        ProjectItem.end_date.asc().nulls_last(),
        ProjectItem.updated_at.desc().nullslast(),
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
        in {
            "start_date",
            "end_date",
            "due_date",
            "iteration_id",
            "iteration_title",
            "status",
            "epic_option_id",
            "epic_name",
        }
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


def _normalize_status(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip()
    return normalized if normalized else None


def _status_is_done(status: str | None, done_keywords: Iterable[str]) -> bool:
    if not status:
        return False
    normalized = status.strip().lower()
    if not normalized:
        return False
    return any(keyword in normalized for keyword in done_keywords)


def _safe_float(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


@router.get("/current/iterations/dashboard", response_model=IterationDashboardResponse)
async def get_iteration_dashboard(
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.get_current_user),
) -> IterationDashboardResponse:
    account = await _get_account_or_404(db, current_user)
    project = await _get_project_or_404(db, account)

    stmt = select(ProjectItem).where(ProjectItem.project_id == project.id)
    result = await db.execute(stmt)
    items = list(result.scalars().all())

    options = await list_iteration_options(db, project)
    done_keywords = {
        "done",
        "concluído",
        "concluido",
        "finalizado",
        "finished",
        "completo",
        "completed",
    }

    summaries = _build_iteration_summaries(items, done_keywords)

    option_responses = [
        IterationOptionResponse(
            id=option.id,
            name=option.title,
            start_date=option.start_date,
            end_date=option.end_date,
        )
        for option in options
    ]

    return IterationDashboardResponse(summaries=summaries, options=option_responses)


def _build_iteration_summaries(
    items: list[ProjectItem],
    done_keywords: Iterable[str],
) -> list[IterationSummaryResponse]:
    buckets: dict[str, dict[str, Any]] = {}

    for item in items:
        key = item.iteration_id or "__without_iteration__"
        bucket = buckets.get(key)
        if not bucket:
            bucket = {
                "iteration_id": item.iteration_id,
                "name": _normalize_status(item.iteration) or None,
                "start_date": item.iteration_start,
                "end_date": item.iteration_end,
                "item_count": 0,
                "completed_count": 0,
                "total_estimate": 0.0,
                "completed_estimate": 0.0,
                "status_breakdown": defaultdict(lambda: {"count": 0, "estimate": 0.0}),
            }
            buckets[key] = bucket

        estimate_value = _safe_float(item.estimate)
        bucket["item_count"] += 1
        bucket["total_estimate"] += estimate_value

        status_label = _normalize_status(item.status)
        status_key = status_label if status_label is not None else None
        status_bucket = bucket["status_breakdown"][status_key]
        status_bucket["count"] += 1
        status_bucket["estimate"] += estimate_value

        if _status_is_done(status_label, done_keywords):
            bucket["completed_count"] += 1
            bucket["completed_estimate"] += estimate_value

        if item.iteration_start and (
            bucket["start_date"] is None or item.iteration_start < bucket["start_date"]
        ):
            bucket["start_date"] = item.iteration_start
        if item.iteration_end and (
            bucket["end_date"] is None or item.iteration_end > bucket["end_date"]
        ):
            bucket["end_date"] = item.iteration_end
        if item.iteration and not bucket["name"]:
            bucket["name"] = _normalize_status(item.iteration)

    summaries: list[IterationSummaryResponse] = []
    for key, bucket in buckets.items():
        status_breakdown = [
            StatusBreakdownEntry(
                status=status,
                count=entry["count"],
                total_estimate=round(entry["estimate"], 2) if entry["estimate"] else 0.0,
            )
            for status, entry in sorted(
                bucket["status_breakdown"].items(), key=lambda pair: pair[0] or "zzzz"
            )
        ]

        name = bucket["name"]
        if not name:
            name = "Sem sprint"

        summaries.append(
            IterationSummaryResponse(
                iteration_id=None if key == "__without_iteration__" else bucket["iteration_id"],
                name=name,
                start_date=bucket["start_date"],
                end_date=bucket["end_date"],
                item_count=bucket["item_count"],
                completed_count=bucket["completed_count"],
                total_estimate=round(bucket["total_estimate"], 2) if bucket["total_estimate"] else 0.0,
                completed_estimate=round(bucket["completed_estimate"], 2)
                if bucket["completed_estimate"]
                else 0.0,
                status_breakdown=status_breakdown,
            )
        )

    summaries.sort(
        key=lambda summary: (
            summary.start_date.isoformat() if summary.start_date else "zzzz",
            summary.name,
        )
    )

    return summaries


@router.get("/current/epics/dashboard", response_model=EpicDashboardResponse)
async def get_epic_dashboard(
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.get_current_user),
) -> EpicDashboardResponse:
    account = await _get_account_or_404(db, current_user)
    project = await _get_project_or_404(db, account)

    stmt = select(ProjectItem).where(ProjectItem.project_id == project.id)
    result = await db.execute(stmt)
    items = list(result.scalars().all())

    options = await list_epic_options(db, project)
    done_keywords = {
        "done",
        "concluído",
        "concluido",
        "finalizado",
        "finished",
        "completo",
        "completed",
    }

    summaries = _build_epic_summaries(items, done_keywords)

    option_responses = [
        EpicOptionResponse(
            id=option.id,
            name=option.name,
            color=option.color,
        )
        for option in options
    ]

    return EpicDashboardResponse(summaries=summaries, options=option_responses)


def _build_epic_summaries(items: list[ProjectItem], done_keywords: Iterable[str]) -> list[EpicSummaryResponse]:
    buckets: dict[str, dict[str, Any]] = {}

    for item in items:
        key = item.epic_option_id or "__without_epic__"
        bucket = buckets.get(key)
        if not bucket:
            bucket = {
                "epic_option_id": item.epic_option_id,
                "name": _normalize_status(item.epic_name) or None,
                "item_count": 0,
                "completed_count": 0,
                "total_estimate": 0.0,
                "completed_estimate": 0.0,
                "status_breakdown": defaultdict(lambda: {"count": 0, "estimate": 0.0}),
            }
            buckets[key] = bucket

        estimate_value = _safe_float(item.estimate)
        bucket["item_count"] += 1
        bucket["total_estimate"] += estimate_value

        status_label = _normalize_status(item.status)
        status_bucket = bucket["status_breakdown"][status_label if status_label is not None else None]
        status_bucket["count"] += 1
        status_bucket["estimate"] += estimate_value

        if _status_is_done(status_label, done_keywords):
            bucket["completed_count"] += 1
            bucket["completed_estimate"] += estimate_value

        if item.epic_name and not bucket["name"]:
            bucket["name"] = _normalize_status(item.epic_name)

    summaries: list[EpicSummaryResponse] = []
    for key, bucket in buckets.items():
        status_breakdown = [
            StatusBreakdownEntry(
                status=status,
                count=entry["count"],
                total_estimate=round(entry["estimate"], 2) if entry["estimate"] else 0.0,
            )
            for status, entry in sorted(
                bucket["status_breakdown"].items(), key=lambda pair: pair[0] or "zzzz"
            )
        ]

        name = bucket["name"] or "Sem épico"

        summaries.append(
            EpicSummaryResponse(
                epic_option_id=None if key == "__without_epic__" else bucket["epic_option_id"],
                name=name,
                item_count=bucket["item_count"],
                completed_count=bucket["completed_count"],
                total_estimate=round(bucket["total_estimate"], 2) if bucket["total_estimate"] else 0.0,
                completed_estimate=round(bucket["completed_estimate"], 2)
                if bucket["completed_estimate"]
                else 0.0,
                status_breakdown=status_breakdown,
            )
        )

    summaries.sort(key=lambda summary: summary.name)
    return summaries


@router.get("/current/epics", response_model=list[EpicDetailResponse])
async def list_epics(
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.get_current_user),
) -> list[EpicDetailResponse]:
    """Lista épicos completos (issues que são épicos) com descrição e progresso"""
    account = await _get_account_or_404(db, current_user)
    project = await _get_project_or_404(db, account)

    # Buscar todos os itens do projeto
    stmt = select(ProjectItem).where(ProjectItem.project_id == project.id)
    result = await db.execute(stmt)
    all_items = list(result.scalars().all())

    # Identificar quais são épicos (título contém "EPIC:" ou "epic:")
    epic_items = [item for item in all_items if item.title and "epic:" in item.title.lower()]

    # Buscar detalhes de cada épico e calcular progresso
    epics: list[EpicDetailResponse] = []
    token = await get_github_token(db, account)

    for epic_item in epic_items:
        # Buscar detalhes da issue épica
        epic_details = None
        if epic_item.content_node_id:
            async with GithubGraphQLClient(token) as client:
                details_raw = await fetch_project_item_details(client, epic_item.content_node_id)
                if details_raw:
                    epic_details = details_raw

        # Encontrar opção Epic que corresponde a este épico
        epic_option_id = epic_item.epic_option_id
        epic_option_name = epic_item.epic_name

        # Se não tem epic_option vinculado, buscar pela nomenclatura do título
        if not epic_option_id:
            # Extrair nome do épico do título (remove "EPIC:" e emoji)
            title_clean = epic_item.title.replace("EPIC:", "").replace("epic:", "").strip()
            # Buscar opção que tenha nome similar
            options = await list_epic_options(db, project)
            for option in options:
                if option.name and option.name.lower() in title_clean.lower():
                    epic_option_id = option.id
                    epic_option_name = option.name
                    break

        # Calcular progresso: contar issues vinculadas a este épico
        linked_issues = [
            item for item in all_items
            if item.epic_option_id == epic_option_id and item.id != epic_item.id
        ] if epic_option_id else []

        done_keywords = {"done", "concluído", "concluido", "finalizado", "finished", "completo", "completed"}
        completed_issues = [
            item for item in linked_issues
            if item.status and any(kw in item.status.lower() for kw in done_keywords)
        ]

        total_estimate = sum(_safe_float(item.estimate) for item in linked_issues)
        completed_estimate = sum(_safe_float(item.estimate) for item in completed_issues)

        progress_percentage = (
            (len(completed_issues) / len(linked_issues) * 100)
            if linked_issues else 0.0
        )

        epics.append(
            EpicDetailResponse(
                id=epic_item.id,
                item_node_id=epic_item.item_node_id,
                content_node_id=epic_item.content_node_id,
                epic_option_id=epic_option_id,
                epic_option_name=epic_option_name,
                title=epic_item.title or "Sem título",
                description=epic_details.get("body_text") if epic_details else None,
                url=epic_item.url,
                state=epic_details.get("state") if epic_details else None,
                author=epic_details.get("author_login") if epic_details else None,
                created_at=parse_datetime(epic_details.get("created_at")) if epic_details else None,
                updated_at=parse_datetime(epic_details.get("updated_at")) if epic_details else epic_item.updated_at,
                labels=epic_details.get("labels", []) if epic_details else [],
                total_issues=len(linked_issues),
                completed_issues=len(completed_issues),
                progress_percentage=round(progress_percentage, 1),
                total_estimate=round(total_estimate, 2) if total_estimate else None,
                completed_estimate=round(completed_estimate, 2) if completed_estimate else None,
                linked_issues=[item.id for item in linked_issues],
            )
        )

    # Ordenar por título
    epics.sort(key=lambda e: e.title)
    return epics


@router.post("/current/epics", response_model=EpicCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_epic(
    epic_data: EpicCreateRequest,
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.get_current_user),
) -> EpicCreateResponse:
    """Cria um novo épico (issue) no GitHub, adiciona ao projeto e opcionalmente vincula ao campo Epic"""
    account = await _get_account_or_404(db, current_user)
    project = await _get_project_or_404(db, account)
    token = await get_github_token(db, account)

    # Get epic field ID if epic_option_id is provided
    epic_field_id = None
    if epic_data.epic_option_id:
        # Find epic field from project fields
        stmt = select(GithubProjectField).where(
            GithubProjectField.project_id == project.id,
            GithubProjectField.field_type.in_(["single_select", "projectv2singleselectfield"])
        )
        result = await db.execute(stmt)
        fields = list(result.scalars().all())

        # Find the Epic field
        for field in fields:
            field_name_lower = (field.field_name or "").lower()
            if any(alias in field_name_lower for alias in ["epic", "épico"]):
                epic_field_id = field.field_id
                break

    async with GithubGraphQLClient(token) as client:
        result = await create_epic_issue(
            client=client,
            owner=project.owner_login,
            repository=epic_data.repository,
            title=epic_data.title,
            description=epic_data.description,
            labels=epic_data.labels,
            project_node_id=project.project_node_id,
            epic_field_id=epic_field_id,
            epic_option_id=epic_data.epic_option_id,
        )

    return EpicCreateResponse(
        issue_number=result["issue_number"],
        issue_url=result["issue_url"],
        issue_node_id=result["issue_node_id"],
    )


@router.get("/current/epics/options", response_model=list[EpicOptionResponse])
async def list_epic_options_endpoint(
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.get_current_user),
) -> list[EpicOptionResponse]:
    print("DEBUG: ===== ENDPOINT /current/epics/options CHAMADO =====")
    account = await _get_account_or_404(db, current_user)
    print(f"DEBUG: Account ID: {account.id}")
    project = await _get_project_or_404(db, account)
    print(f"DEBUG: Project ID: {project.id}, name: {project.name}")
    options = await list_epic_options(db, project)
    print(f"DEBUG: list_epic_options retornou {len(options)} opções")
    result = [EpicOptionResponse.model_validate(option.__dict__) for option in options]
    print(f"DEBUG: Retornando {len(result)} épicos ao frontend")
    return result


@router.post(
    "/current/epics/options",
    response_model=EpicOptionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_epic_option_endpoint(
    payload: EpicOptionCreateRequest,
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.require_roles("owner", "admin")),
) -> EpicOptionResponse:
    account = await _get_account_or_404(db, current_user)
    project = await _get_project_or_404(db, account)
    option = await create_epic_option(db, account, project, payload.name, payload.color)
    return EpicOptionResponse.model_validate(option.__dict__)


@router.patch("/current/epics/options/{option_id}", response_model=EpicOptionResponse)
async def update_epic_option_endpoint(
    option_id: str,
    payload: EpicOptionUpdateRequest,
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.require_roles("owner", "admin")),
) -> EpicOptionResponse:
    account = await _get_account_or_404(db, current_user)
    project = await _get_project_or_404(db, account)
    option = await update_epic_option(db, account, project, option_id, payload.name, payload.color)
    return EpicOptionResponse.model_validate(option.__dict__)


@router.delete("/current/epics/options/{option_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_epic_option_endpoint(
    option_id: str,
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.require_roles("owner", "admin")),
) -> Response:
    account = await _get_account_or_404(db, current_user)
    project = await _get_project_or_404(db, account)
    await delete_epic_option(db, account, project, option_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
