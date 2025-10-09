from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any, Iterable

from fastapi import APIRouter, Depends, HTTPException, status, Response, Header
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.account import Account
from app.models.github_project import GithubProject
from app.models.github_project_field import GithubProjectField
from app.models.project_item import ProjectItem
from app.models.project_member import ProjectMember
from app.models.project_invite import ProjectInvite
from app.models.project_repository import ProjectRepository
from app.models.user import AppUser
from app.services.email import send_project_invite_email
from app.core.security import generate_verification_token
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
    StoryCreateRequest,
    StoryCreateResponse,
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
from app.schemas.project_member import (
    ProjectMemberResponse,
    ProjectMemberCreateRequest,
    ProjectMemberUpdateRequest,
)
from app.schemas.project_invite import (
    ProjectInviteResponse,
    ProjectInviteCreateRequest,
    ProjectInviteListResponse,
)
from app.schemas.repository import (
    ProjectRepositoryResponse,
    ProjectRepositoryCreateRequest,
    ProjectRepositoryUpdateRequest,
)
from app.schemas.hierarchy import (
    HierarchyResponse,
    HierarchyEpicResponse,
    HierarchyItemResponse,
)
from app.services.github import (
    GithubGraphQLClient,
    apply_local_project_item_updates,
    create_epic_issue,
    create_story_issue,
    fetch_project_item_comments,
    fetch_project_item_details,
    get_github_token,
    list_epic_options,
    list_iteration_options,
    parse_datetime,
    setup_project_fields,
    update_item_iteration,
    # New label-based epic functions
    create_epic_label,
    update_epic_label,
    delete_epic_label,
    list_epic_labels,
)

router = APIRouter(prefix="/projects", tags=["projects"])


async def _get_account_or_404(db: AsyncSession, current_user: AppUser) -> Account:
    if current_user.account_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Usuário não possui conta configurada")
    account = await db.get(Account, current_user.account_id)
    if not account:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Conta não encontrada")
    return account


async def _get_project_or_404(
    db: AsyncSession,
    account: Account,
    project_id: int | None = None
) -> GithubProject:
    """
    Busca projeto por ID (se fornecido) ou retorna o primeiro projeto da conta.

    Args:
        db: Sessão do banco
        account: Conta do usuário
        project_id: ID do projeto (opcional, vem do header X-Project-Id)

    Returns:
        GithubProject configurado

    Raises:
        HTTPException: Se projeto não encontrado ou não pertence à conta
    """
    if project_id:
        # Buscar projeto específico e verificar se pertence à conta
        project = await db.get(GithubProject, project_id)
        if not project or project.account_id != account.id:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                detail="Projeto não encontrado ou não pertence a esta conta"
            )
        return project

    # Buscar primeiro projeto da conta (comportamento legado)
    stmt = select(GithubProject).where(GithubProject.account_id == account.id).limit(1)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Projeto GitHub não configurado")
    return project


async def _user_can_manage_project(
    db: AsyncSession,
    user: AppUser,
    project: GithubProject
) -> bool:
    """
    Verifica se o usuário tem permissão para gerenciar o projeto.

    Retorna True se:
    - Usuário é owner ou admin da conta
    - Usuário é admin do projeto específico
    """
    # Verificar se é owner/admin da conta
    if user.role in ["owner", "admin"]:
        return True

    # Verificar se é admin do projeto
    stmt = select(ProjectMember).where(
        ProjectMember.user_id == user.id,
        ProjectMember.project_id == project.id,
        ProjectMember.role == "admin"
    )
    result = await db.execute(stmt)
    member = result.scalar_one_or_none()
    return member is not None


@router.get("", response_model=list[GithubProjectResponse])
async def list_projects(
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.get_current_user),
    x_project_id: int | None = Header(None, alias="X-Project-Id"),
) -> list[GithubProjectResponse]:
    """Lista todos os projetos GitHub da conta do usuário."""
    account = await _get_account_or_404(db, current_user)
    print(f"🔍 [API] list_projects - User: {current_user.email}, Account ID: {account.id}")

    stmt = select(GithubProject).where(GithubProject.account_id == account.id).order_by(GithubProject.created_at.desc())
    result = await db.execute(stmt)
    projects = result.scalars().all()

    print(f"📊 [API] list_projects - Encontrados {len(projects)} projetos para account_id={account.id}")
    for proj in projects:
        print(f"   - ID: {proj.id}, Nome: {proj.name}, Owner: {proj.owner_login}")

    return [GithubProjectResponse.model_validate(p) for p in projects]


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.require_roles("owner", "admin")),
) -> Response:
    """
    Remove um projeto GitHub da conta.

    ATENÇÃO: Esta operação também remove todos os itens do projeto (issues, PRs, etc).
    """
    account = await _get_account_or_404(db, current_user)

    # Verificar se o projeto existe e pertence à conta
    project = await db.get(GithubProject, project_id)
    if not project or project.account_id != account.id:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail="Projeto não encontrado ou não pertence a esta conta"
        )

    # Deletar projeto (cascade deleta itens relacionados)
    await db.delete(project)
    await db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/current", response_model=GithubProjectResponse)
async def get_current_project(
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.get_current_user),
    x_project_id: int | None = Header(None, alias="X-Project-Id"),
) -> GithubProjectResponse:
    """
    Retorna o projeto ativo.

    Se X-Project-Id header estiver presente, retorna aquele projeto.
    Caso contrário, retorna o primeiro projeto da conta.
    """
    account = await _get_account_or_404(db, current_user)
    project = await _get_project_or_404(db, account, x_project_id)
    return GithubProjectResponse.model_validate(project)


@router.get("/current/items", response_model=list[ProjectItemResponse])
async def list_current_project_items(
    status: str | None = None,
    iteration: str | None = None,
    epic: str | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.get_current_user),
    x_project_id: int | None = Header(None, alias="X-Project-Id"),
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
    project = await _get_project_or_404(db, account, x_project_id)

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
    x_project_id: int | None = Header(None, alias="X-Project-Id"),
) -> ProjectItemResponse:
    account = await _get_account_or_404(db, current_user)
    project = await _get_project_or_404(db, account, x_project_id)

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
    x_project_id: int | None = Header(None, alias="X-Project-Id"),
) -> list[ProjectItemCommentResponse]:
    account = await _get_account_or_404(db, current_user)
    project = await _get_project_or_404(db, account, x_project_id)

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
    x_project_id: int | None = Header(None, alias="X-Project-Id"),
) -> ProjectItemDetailResponse:
    account = await _get_account_or_404(db, current_user)
    project = await _get_project_or_404(db, account, x_project_id)

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
    x_project_id: int | None = Header(None, alias="X-Project-Id"),
) -> list[str]:
    account = await _get_account_or_404(db, current_user)
    project = await _get_project_or_404(db, account, x_project_id)

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


@router.get("/current/setup/status")
async def get_setup_status(
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.get_current_user),
    x_project_id: int | None = Header(None, alias="X-Project-Id"),
) -> dict[str, Any]:
    """
    Verifica quais campos necessários estão configurados no projeto.

    **Response:**
    ```json
    {
      "iteration": {"exists": true, "required": true},
      "epic": {"exists": false, "required": false},
      "estimate": {"exists": true, "required": false},
      "status": {"exists": true, "required": true}
    }
    ```
    """
    from app.services.github import (
        _load_project_fields,
        _resolve_iteration_field_from_collection,
        _resolve_epic_field_from_collection,
    )

    account = await _get_account_or_404(db, current_user)
    project = await _get_project_or_404(db, account, x_project_id)

    # Carregar campos atuais
    fields = await _load_project_fields(db, project.id)

    status = {
        "iteration": {"exists": False, "required": True, "description": "Campo para gerenciar sprints"},
        "epic": {"exists": False, "required": False, "description": "Campo para agrupar issues por épico"},
        "estimate": {"exists": False, "required": False, "description": "Campo para story points"},
        "status": {"exists": False, "required": True, "description": "Campo de status do item"},
    }

    # Verificar campos existentes
    iteration_field = _resolve_iteration_field_from_collection(fields)
    epic_field = _resolve_epic_field_from_collection(list(fields))

    status["iteration"]["exists"] = iteration_field is not None
    status["epic"]["exists"] = epic_field is not None

    # Verificar Status e Estimate
    for field in fields:
        field_name_lower = (field.field_name or "").lower()
        field_type_lower = (field.field_type or "").lower()

        if field_name_lower == "status" or "status" in field_type_lower:
            status["status"]["exists"] = True

        if field_name_lower in ["estimate", "story points", "points"]:
            status["estimate"]["exists"] = True

    return status


@router.post("/current/setup")
async def run_project_setup(
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.require_roles("admin", "owner")),
) -> dict[str, Any]:
    """
    Executa setup automático do projeto, criando campos necessários.

    **Permissão:** admin, owner

    **Campos criados (se não existirem):**
    - Iteration: Campo para gerenciar sprints
    - Epic: Campo Single Select com opções padrão (Feature, Bug Fix, Tech Debt)
    - Estimate: Campo numérico para story points

    **Response:**
    ```json
    {
      "iteration": {"exists": false, "created": true},
      "epic": {"exists": false, "created": true},
      "estimate": {"exists": false, "created": true},
      "status": {"exists": true, "created": false}
    }
    ```
    """
    account = await _get_account_or_404(db, current_user)
    project = await _get_project_or_404(db, account, x_project_id)

    report = await setup_project_fields(db, account, project)

    await db.commit()

    return report


@router.get("/current/fields")
async def list_project_fields(
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.get_current_user),
    x_project_id: int | None = Header(None, alias="X-Project-Id"),
) -> dict[str, Any]:
    """
    Lista todos os campos do projeto para debug.
    Útil para verificar se o campo Iteration está configurado.
    """
    account = await _get_account_or_404(db, current_user)
    project = await _get_project_or_404(db, account, x_project_id)

    stmt = select(GithubProjectField).where(GithubProjectField.project_id == project.id)
    result = await db.execute(stmt)
    fields = result.scalars().all()

    return {
        "project_id": project.id,
        "project_node_id": project.project_node_id,
        "total_fields": len(fields),
        "fields": [
            {
                "id": field.id,
                "field_id": field.field_id,
                "field_name": field.field_name,
                "field_type": field.field_type,
                "data_type": field.data_type,
                "options": field.options if hasattr(field, "options") else None,
            }
            for field in fields
        ],
    }


@router.get("/current/iterations/dashboard", response_model=IterationDashboardResponse)
async def get_iteration_dashboard(
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.get_current_user),
    x_project_id: int | None = Header(None, alias="X-Project-Id"),
) -> IterationDashboardResponse:
    account = await _get_account_or_404(db, current_user)
    project = await _get_project_or_404(db, account, x_project_id)

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


@router.patch("/current/items/{item_id}", response_model=ProjectItemResponse)
async def update_project_item(
    item_id: int,
    request_data: ProjectItemUpdateRequest,
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.require_roles("pm", "admin", "owner")),
) -> ProjectItemResponse:
    """
    Atualiza um item do projeto (issue/PR/draft).

    **Permissão:** pm, admin, owner

    **Campos atualizáveis:**
    - `iteration_id`: ID da sprint/iteration (ou null para remover)
    - `status`: Status do item
    - `epic_option_id`: ID do epic
    - `start_date`, `end_date`, `due_date`: Datas customizadas

    **Exemplo de Request:**
    ```json
    {
      "iteration_id": "PVTIF_lADOBz...",
      "status": "In Progress"
    }
    ```
    """
    account = await _get_account_or_404(db, current_user)
    project = await _get_project_or_404(db, account, x_project_id)

    item = await db.get(ProjectItem, item_id)
    if not item or item.project_id != project.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Item não encontrado")

    # Atualizar iteration se fornecida
    if hasattr(request_data, "iteration_id") and request_data.iteration_id is not None:
        item = await update_item_iteration(
            db,
            account,
            project,
            item,
            request_data.iteration_id if request_data.iteration_id else None,
        )

    # Aplicar outras atualizações (status, datas, etc)
    updates = {}
    if request_data.status is not None:
        updates["status"] = request_data.status
    if request_data.start_date is not None:
        updates["start_date"] = request_data.start_date
    if request_data.end_date is not None:
        updates["end_date"] = request_data.end_date
    if request_data.due_date is not None:
        updates["due_date"] = request_data.due_date
    if request_data.epic_option_id is not None:
        updates["epic_option_id"] = request_data.epic_option_id
    if request_data.epic_name is not None:
        updates["epic_name"] = request_data.epic_name

    if updates:
        item = await apply_local_project_item_updates(
            db,
            account,
            project,
            item,
            updates,
            current_user.id,
        )

    await db.commit()
    await db.refresh(item)

    return ProjectItemResponse.model_validate(item)


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
    x_project_id: int | None = Header(None, alias="X-Project-Id"),
) -> EpicDashboardResponse:
    account = await _get_account_or_404(db, current_user)
    project = await _get_project_or_404(db, account, x_project_id)

    stmt = select(ProjectItem).where(ProjectItem.project_id == project.id)
    result = await db.execute(stmt)
    items = list(result.scalars().all())

    # Use list_epic_labels (from database) instead of list_epic_options (from GitHub)
    options = await list_epic_labels(db, project)
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
            name=option.option_name,  # Use option_name instead of name
            color=option.color,
            description=option.description,
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
    x_project_id: int | None = Header(None, alias="X-Project-Id"),
) -> list[EpicDetailResponse]:
    """Lista épicos completos (issues que são épicos) com descrição e progresso"""
    account = await _get_account_or_404(db, current_user)
    project = await _get_project_or_404(db, account, x_project_id)

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
    x_project_id: int | None = Header(None, alias="X-Project-Id"),
) -> EpicCreateResponse:
    """Cria um novo épico (issue) no GitHub, adiciona ao projeto e opcionalmente vincula ao campo Epic"""
    account = await _get_account_or_404(db, current_user)
    project = await _get_project_or_404(db, account, x_project_id)
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


@router.post("/current/stories", response_model=StoryCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_story(
    story_data: StoryCreateRequest,
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.get_current_user),
    x_project_id: int | None = Header(None, alias="X-Project-Id"),
) -> StoryCreateResponse:
    """Cria uma nova história (issue) no GitHub, adiciona ao projeto e vincula ao épico especificado"""
    account = await _get_account_or_404(db, current_user)
    project = await _get_project_or_404(db, account, x_project_id)
    token = await get_github_token(db, account)

    # Get epic field ID
    epic_field_id = None
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
        result = await create_story_issue(
            client=client,
            owner=project.owner_login,
            repository=story_data.repository,
            title=story_data.title,
            description=story_data.description,
            labels=story_data.labels,
            project_node_id=project.project_node_id,
            epic_field_id=epic_field_id,
            epic_option_id=story_data.epic_option_id,
        )

    return StoryCreateResponse(
        issue_number=result["issue_number"],
        issue_url=result["issue_url"],
        issue_node_id=result["issue_node_id"],
    )


@router.get("/current/epics/options", response_model=list[EpicOptionResponse])
async def list_epic_options_endpoint(
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.get_current_user),
    x_project_id: int | None = Header(None, alias="X-Project-Id"),
) -> list[EpicOptionResponse]:
    """
    Lista todos os épicos (labels) do projeto.
    Épicos são gerenciados como labels do GitHub com prefixo 'epic:'.
    """
    account = await _get_account_or_404(db, current_user)
    project = await _get_project_or_404(db, account, x_project_id)
    epics = await list_epic_labels(db, project)
    return [EpicOptionResponse.model_validate(epic) for epic in epics]


@router.post(
    "/current/epics/options",
    response_model=EpicOptionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_epic_option_endpoint(
    payload: EpicOptionCreateRequest,
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.require_roles("owner", "admin")),
    x_project_id: int | None = Header(None, alias="X-Project-Id"),
) -> EpicOptionResponse:
    """
    Cria um novo épico como label do GitHub.
    A label é criada em todos os repositórios vinculados ao projeto.
    """
    account = await _get_account_or_404(db, current_user)
    project = await _get_project_or_404(db, account, x_project_id)
    epic = await create_epic_label(db, account, project, payload.name, payload.color, payload.description)
    return EpicOptionResponse.model_validate(epic)


@router.patch("/current/epics/options/{epic_id}", response_model=EpicOptionResponse)
async def update_epic_option_endpoint(
    epic_id: int,
    payload: EpicOptionUpdateRequest,
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.require_roles("owner", "admin")),
    x_project_id: int | None = Header(None, alias="X-Project-Id"),
) -> EpicOptionResponse:
    """
    Atualiza um épico (label) em todos os repositórios do projeto.
    """
    account = await _get_account_or_404(db, current_user)
    project = await _get_project_or_404(db, account, x_project_id)
    epic = await update_epic_label(db, account, project, epic_id, payload.name, payload.color, payload.description)
    return EpicOptionResponse.model_validate(epic)


@router.delete("/current/epics/options/{epic_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_epic_option_endpoint(
    epic_id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.require_roles("owner", "admin")),
    x_project_id: int | None = Header(None, alias="X-Project-Id"),
) -> Response:
    """
    Deleta um épico (label) de todos os repositórios do projeto.
    """
    account = await _get_account_or_404(db, current_user)
    project = await _get_project_or_404(db, account, x_project_id)
    await delete_epic_label(db, account, project, epic_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ============================================================================
# Project Repositories Management
# ============================================================================


@router.get("/current/repositories", response_model=list[ProjectRepositoryResponse])
async def list_project_repositories(
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.get_current_user),
    x_project_id: int | None = Header(None, alias="X-Project-Id"),
) -> list[ProjectRepositoryResponse]:
    """Lista todos os repositórios vinculados ao projeto."""
    account = await _get_account_or_404(db, current_user)
    project = await _get_project_or_404(db, account, x_project_id)

    stmt = select(ProjectRepository).where(ProjectRepository.project_id == project.id)
    result = await db.execute(stmt)
    repositories = result.scalars().all()

    return [ProjectRepositoryResponse.model_validate(repo) for repo in repositories]


@router.post("/current/repositories", response_model=ProjectRepositoryResponse, status_code=status.HTTP_201_CREATED)
async def add_project_repository(
    payload: ProjectRepositoryCreateRequest,
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.require_roles("owner", "admin")),
    x_project_id: int | None = Header(None, alias="X-Project-Id"),
) -> ProjectRepositoryResponse:
    """Vincula um repositório ao projeto."""
    account = await _get_account_or_404(db, current_user)
    project = await _get_project_or_404(db, account, x_project_id)

    # Verificar se já existe
    stmt = select(ProjectRepository).where(
        ProjectRepository.project_id == project.id,
        ProjectRepository.owner == payload.owner,
        ProjectRepository.repo_name == payload.repo_name,
    )
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"Repositório {payload.owner}/{payload.repo_name} já está vinculado ao projeto"
        )

    # Se está marcando como primary, desmarcar outros
    if payload.is_primary:
        stmt = select(ProjectRepository).where(
            ProjectRepository.project_id == project.id,
            ProjectRepository.is_primary == True
        )
        result = await db.execute(stmt)
        for repo in result.scalars().all():
            repo.is_primary = False

    # Criar repositório
    repository = ProjectRepository(
        project_id=project.id,
        owner=payload.owner,
        repo_name=payload.repo_name,
        is_primary=payload.is_primary,
    )
    db.add(repository)
    await db.commit()
    await db.refresh(repository)

    return ProjectRepositoryResponse.model_validate(repository)


@router.patch("/current/repositories/{repository_id}", response_model=ProjectRepositoryResponse)
async def update_project_repository(
    repository_id: int,
    payload: ProjectRepositoryUpdateRequest,
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.require_roles("owner", "admin")),
    x_project_id: int | None = Header(None, alias="X-Project-Id"),
) -> ProjectRepositoryResponse:
    """Atualiza um repositório do projeto."""
    account = await _get_account_or_404(db, current_user)
    project = await _get_project_or_404(db, account, x_project_id)

    repository = await db.get(ProjectRepository, repository_id)
    if not repository or repository.project_id != project.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Repositório não encontrado")

    # Se está marcando como primary, desmarcar outros
    if payload.is_primary:
        stmt = select(ProjectRepository).where(
            ProjectRepository.project_id == project.id,
            ProjectRepository.is_primary == True,
            ProjectRepository.id != repository_id
        )
        result = await db.execute(stmt)
        for repo in result.scalars().all():
            repo.is_primary = False

    if payload.is_primary is not None:
        repository.is_primary = payload.is_primary

    await db.commit()
    await db.refresh(repository)

    return ProjectRepositoryResponse.model_validate(repository)


@router.delete("/current/repositories/{repository_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project_repository(
    repository_id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.require_roles("owner", "admin")),
    x_project_id: int | None = Header(None, alias="X-Project-Id"),
) -> Response:
    """Remove um repositório do projeto."""
    account = await _get_account_or_404(db, current_user)
    project = await _get_project_or_404(db, account, x_project_id)

    repository = await db.get(ProjectRepository, repository_id)
    if not repository or repository.project_id != project.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Repositório não encontrado")

    await db.delete(repository)
    await db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ============================================================================
# Project Members Management
# ============================================================================


@router.get("/{project_id}/available-users", response_model=list[dict])
async def list_available_users_for_project(
    project_id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.require_roles("owner", "admin")),
) -> list[dict]:
    """
    Lista usuários disponíveis para convidar ao projeto.

    Retorna apenas usuários da mesma conta do projeto que:
    - Não são membros ativos do projeto
    - Não têm convites pendentes

    **Permissão:** owner, admin (do projeto)
    """
    account = await _get_account_or_404(db, current_user)
    project = await _get_project_or_404(db, account, project_id)

    # Verificar permissão no projeto
    has_permission = await _user_can_manage_project(db, current_user, project)
    if not has_permission:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para gerenciar membros deste projeto"
        )

    # Buscar todos os usuários da conta do projeto
    stmt = select(AppUser).where(AppUser.account_id == project.account_id)
    result = await db.execute(stmt)
    all_users = result.scalars().all()

    # Buscar IDs de usuários que já são membros
    stmt_members = select(ProjectMember.user_id).where(ProjectMember.project_id == project.id)
    result_members = await db.execute(stmt_members)
    member_ids = {row[0] for row in result_members.all()}

    # Buscar IDs de usuários com convites pendentes
    stmt_invites = select(ProjectInvite.invited_user_id).where(
        ProjectInvite.project_id == project.id,
        ProjectInvite.status == "pending"
    )
    result_invites = await db.execute(stmt_invites)
    invited_ids = {row[0] for row in result_invites.all()}

    # Filtrar usuários disponíveis
    available_users = [
        {
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "role": user.role,
        }
        for user in all_users
        if user.id not in member_ids and user.id not in invited_ids
    ]

    return available_users


@router.get("/{project_id}/members", response_model=list[ProjectMemberResponse])
async def list_project_members(
    project_id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.get_current_user),
) -> list[ProjectMemberResponse]:
    """
    Lista todos os membros de um projeto.

    Retorna informações de cada membro incluindo role e dados do usuário.
    """
    account = await _get_account_or_404(db, current_user)
    project = await _get_project_or_404(db, account, project_id)

    # Query project members with user information joined
    stmt = (
        select(ProjectMember, AppUser)
        .join(AppUser, ProjectMember.user_id == AppUser.id)
        .where(ProjectMember.project_id == project.id)
        .order_by(ProjectMember.created_at.asc())
    )
    result = await db.execute(stmt)
    rows = result.all()

    members = []
    for member, user in rows:
        members.append(
            ProjectMemberResponse(
                id=member.id,
                user_id=member.user_id,
                project_id=member.project_id,
                role=member.role,
                created_at=member.created_at,
                updated_at=member.updated_at,
                user_email=user.email,
                user_name=user.name,
            )
        )

    return members


@router.post("/{project_id}/members", response_model=ProjectMemberResponse, status_code=status.HTTP_201_CREATED)
async def add_project_member(
    project_id: int,
    payload: ProjectMemberCreateRequest,
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.require_roles("owner", "admin")),
) -> ProjectMemberResponse:
    """
    Adiciona um membro ao projeto com um role específico.

    **Permissão:** owner, admin

    **Roles disponíveis:**
    - viewer: Apenas visualização
    - editor: Pode editar itens
    - pm: Project Manager, pode gerenciar sprints e épicos
    - admin: Administrador do projeto
    """
    account = await _get_account_or_404(db, current_user)
    project = await _get_project_or_404(db, account, project_id)

    # Validate role
    valid_roles = ["viewer", "editor", "pm", "admin"]
    if payload.role not in valid_roles:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Role inválido. Use um dos seguintes: {', '.join(valid_roles)}"
        )

    # Check if user exists and belongs to same account
    user = await db.get(AppUser, payload.user_id)
    if not user or user.account_id != account.id:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado ou não pertence à mesma conta"
        )

    # Check if user is already a member
    stmt = select(ProjectMember).where(
        ProjectMember.user_id == payload.user_id,
        ProjectMember.project_id == project.id
    )
    result = await db.execute(stmt)
    existing_member = result.scalar_one_or_none()

    if existing_member:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Usuário já é membro deste projeto"
        )

    # Create new project member
    new_member = ProjectMember(
        user_id=payload.user_id,
        project_id=project.id,
        role=payload.role
    )
    db.add(new_member)
    await db.commit()
    await db.refresh(new_member)

    return ProjectMemberResponse(
        id=new_member.id,
        user_id=new_member.user_id,
        project_id=new_member.project_id,
        role=new_member.role,
        created_at=new_member.created_at,
        updated_at=new_member.updated_at,
        user_email=user.email,
        user_name=user.name,
    )


@router.patch("/{project_id}/members/{user_id}", response_model=ProjectMemberResponse)
async def update_project_member(
    project_id: int,
    user_id: str,
    payload: ProjectMemberUpdateRequest,
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.require_roles("owner", "admin")),
) -> ProjectMemberResponse:
    """
    Atualiza o role de um membro do projeto.

    **Permissão:** owner, admin
    """
    from uuid import UUID

    account = await _get_account_or_404(db, current_user)
    project = await _get_project_or_404(db, account, project_id)

    # Validate role
    valid_roles = ["viewer", "editor", "pm", "admin"]
    if payload.role not in valid_roles:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Role inválido. Use um dos seguintes: {', '.join(valid_roles)}"
        )

    # Convert user_id string to UUID
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="ID de usuário inválido")

    # Find project member
    stmt = select(ProjectMember, AppUser).join(
        AppUser, ProjectMember.user_id == AppUser.id
    ).where(
        ProjectMember.user_id == user_uuid,
        ProjectMember.project_id == project.id
    )
    result = await db.execute(stmt)
    row = result.first()

    if not row:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail="Membro não encontrado neste projeto"
        )

    member, user = row

    # Update role
    member.role = payload.role
    await db.commit()
    await db.refresh(member)

    return ProjectMemberResponse(
        id=member.id,
        user_id=member.user_id,
        project_id=member.project_id,
        role=member.role,
        created_at=member.created_at,
        updated_at=member.updated_at,
        user_email=user.email,
        user_name=user.name,
    )


@router.delete("/{project_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_project_member(
    project_id: int,
    user_id: str,
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.require_roles("owner", "admin")),
) -> Response:
    """
    Remove um membro do projeto.

    **Permissão:** owner, admin
    """
    from uuid import UUID

    account = await _get_account_or_404(db, current_user)
    project = await _get_project_or_404(db, account, project_id)

    # Convert user_id string to UUID
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="ID de usuário inválido")

    # Find and delete project member
    stmt = select(ProjectMember).where(
        ProjectMember.user_id == user_uuid,
        ProjectMember.project_id == project.id
    )
    result = await db.execute(stmt)
    member = result.scalar_one_or_none()

    if not member:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail="Membro não encontrado neste projeto"
        )

    await db.delete(member)
    await db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ============================================================================
# Project Invites Management
# ============================================================================


@router.post("/{project_id}/invites", response_model=ProjectInviteResponse, status_code=status.HTTP_201_CREATED)
async def create_project_invite(
    project_id: int,
    payload: ProjectInviteCreateRequest,
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.require_roles("owner", "admin")),
) -> ProjectInviteResponse:
    """
    Cria um convite para adicionar um membro ao projeto via email.

    **Permissão:** owner, admin

    **Validações:**
    - Não pode haver convite pendente para o mesmo email
    - Usuário com esse email não pode já ser membro do projeto

    **Nota:** O email pode ser de alguém que ainda não tem conta. O convite
    ficará pendente até a pessoa se cadastrar com esse email e aceitar.
    """
    account = await _get_account_or_404(db, current_user)
    project = await _get_project_or_404(db, account, project_id)

    # Validate role
    valid_roles = ["viewer", "editor", "pm", "admin"]
    if payload.role not in valid_roles:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Role inválido. Use um dos seguintes: {', '.join(valid_roles)}"
        )

    # Normalize email
    invited_email = payload.email.lower().strip()

    # Check if user with this email is already a member
    stmt = (
        select(ProjectMember)
        .join(AppUser, ProjectMember.user_id == AppUser.id)
        .where(
            AppUser.email == invited_email,
            ProjectMember.project_id == project.id
        )
    )
    result = await db.execute(stmt)
    existing_member = result.scalar_one_or_none()

    if existing_member:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Usuário com este email já é membro deste projeto"
        )

    # Check if there's already an invite for this email (any status)
    stmt = select(ProjectInvite).where(
        ProjectInvite.invited_email == invited_email,
        ProjectInvite.project_id == project.id
    )
    result = await db.execute(stmt)
    existing_invite = result.scalar_one_or_none()

    if existing_invite:
        if existing_invite.status == "pending":
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="Já existe um convite pendente para este email"
            )
        elif existing_invite.status == "accepted":
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="Este usuário já aceitou um convite anteriormente"
            )
        elif existing_invite.status in ("rejected", "cancelled"):
            # Reativar convite rejeitado ou cancelado
            existing_invite.status = "pending"
            existing_invite.role = payload.role
            existing_invite.invited_by_user_id = current_user.id
            existing_invite.invite_token = generate_verification_token()
            await db.commit()
            await db.refresh(existing_invite)
            new_invite = existing_invite
        else:
            # Status desconhecido - não deveria acontecer, mas reativa por segurança
            existing_invite.status = "pending"
            existing_invite.role = payload.role
            existing_invite.invited_by_user_id = current_user.id
            existing_invite.invite_token = generate_verification_token()
            await db.commit()
            await db.refresh(existing_invite)
            new_invite = existing_invite
    else:
        # Create new invite
        new_invite = ProjectInvite(
            project_id=project.id,
            invited_email=invited_email,
            invited_by_user_id=current_user.id,
            role=payload.role,
            status="pending",
            invite_token=generate_verification_token()
        )
        db.add(new_invite)
        await db.commit()
        await db.refresh(new_invite)

    # Send invitation email
    try:
        await send_project_invite_email(
            to_email=invited_email,
            inviter_name=current_user.name or current_user.email,
            project_name=project.name or f"{project.owner_login}/{project.project_number}",
            role=payload.role,
            invite_token=new_invite.invite_token,
        )
    except Exception as e:
        # Log error but don't fail the request
        # The invite was created successfully, email is just a notification
        print(f"⚠️  Falha ao enviar email de convite: {e}")

    return ProjectInviteResponse(
        id=new_invite.id,
        project_id=new_invite.project_id,
        invited_email=new_invite.invited_email,
        invited_by_user_id=new_invite.invited_by_user_id,
        role=new_invite.role,
        status=new_invite.status,
        created_at=new_invite.created_at,
        updated_at=new_invite.updated_at,
        project_name=project.name,
        project_owner=project.owner_login,
        project_number=project.project_number,
        invited_by_email=current_user.email,
        invited_by_name=current_user.name,
    )


@router.get("/{project_id}/invites", response_model=list[ProjectInviteListResponse])
async def list_project_invites(
    project_id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.require_roles("owner", "admin")),
) -> list[ProjectInviteListResponse]:
    """
    Lista convites pendentes do projeto.

    **Permissão:** owner, admin
    """
    account = await _get_account_or_404(db, current_user)
    project = await _get_project_or_404(db, account, project_id)

    # Query invites
    stmt = (
        select(ProjectInvite)
        .where(
            ProjectInvite.project_id == project.id,
            ProjectInvite.status == "pending"
        )
        .order_by(ProjectInvite.created_at.desc())
    )
    result = await db.execute(stmt)
    invites_list = result.scalars().all()

    invites = []
    for invite in invites_list:
        # Load inviter user
        invited_by = await db.get(AppUser, invite.invited_by_user_id)
        invites.append(
            ProjectInviteListResponse(
                id=invite.id,
                project_id=invite.project_id,
                project_name=project.name,
                project_owner=project.owner_login,
                project_number=project.project_number,
                invited_email=invite.invited_email,
                invited_by_user_id=invite.invited_by_user_id,
                invited_by_email=invited_by.email if invited_by else "",
                invited_by_name=invited_by.name if invited_by else None,
                role=invite.role,
                status=invite.status,
                created_at=invite.created_at,
            )
        )

    return invites


@router.get("/invites/received", response_model=list[ProjectInviteListResponse])
async def list_received_invites(
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.get_current_user),
) -> list[ProjectInviteListResponse]:
    """
    Lista convites recebidos pelo usuário atual (pendentes).

    Qualquer usuário pode ver convites enviados para seu email.
    """
    account = await _get_account_or_404(db, current_user)

    # Query invites received by current user's email
    stmt = (
        select(ProjectInvite)
        .where(
            ProjectInvite.invited_email == current_user.email,
            ProjectInvite.status == "pending"
        )
        .order_by(ProjectInvite.created_at.desc())
    )
    result = await db.execute(stmt)
    invites_list = result.scalars().all()

    invites = []
    for invite in invites_list:
        # Load related project and inviter
        project = await db.get(GithubProject, invite.project_id)
        invited_by = await db.get(AppUser, invite.invited_by_user_id)

        if not project:
            continue
        invites.append(
            ProjectInviteListResponse(
                id=invite.id,
                project_id=invite.project_id,
                project_name=project.name,
                project_owner=project.owner_login,
                project_number=project.project_number,
                invited_email=invite.invited_email,
                invited_by_user_id=invite.invited_by_user_id,
                invited_by_email=invited_by.email if invited_by else "",
                invited_by_name=invited_by.name if invited_by else None,
                role=invite.role,
                status=invite.status,
                created_at=invite.created_at,
            )
        )

    return invites


@router.post("/invites/{invite_id}/accept", response_model=ProjectMemberResponse)
async def accept_project_invite(
    invite_id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.get_current_user),
) -> ProjectMemberResponse:
    """
    Aceita um convite para se tornar membro do projeto.

    O convite deve estar pendente e o email deve corresponder ao do usuário atual.
    Ao aceitar, o convite é marcado como "accepted" e um ProjectMember é criado.
    """
    account = await _get_account_or_404(db, current_user)

    # Find invite
    invite = await db.get(ProjectInvite, invite_id)
    if not invite:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail="Convite não encontrado"
        )

    # Verify invite email matches current user's email
    if invite.invited_email.lower() != current_user.email.lower():
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Este convite não é para você"
        )

    # Verify invite is pending
    if invite.status != "pending":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"Convite já foi {invite.status}"
        )

    # Get project
    project = await db.get(GithubProject, invite.project_id)
    if not project or project.account_id != account.id:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail="Projeto não encontrado"
        )

    # Check if user is already a member (race condition protection)
    stmt = select(ProjectMember).where(
        ProjectMember.user_id == current_user.id,
        ProjectMember.project_id == invite.project_id
    )
    result = await db.execute(stmt)
    existing_member = result.scalar_one_or_none()

    if existing_member:
        # Update invite status anyway
        invite.status = "accepted"
        await db.commit()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Você já é membro deste projeto"
        )

    # Create project member
    new_member = ProjectMember(
        user_id=current_user.id,
        project_id=invite.project_id,
        role=invite.role
    )
    db.add(new_member)

    # Update invite status
    invite.status = "accepted"

    await db.commit()
    await db.refresh(new_member)

    return ProjectMemberResponse(
        id=new_member.id,
        user_id=new_member.user_id,
        project_id=new_member.project_id,
        role=new_member.role,
        created_at=new_member.created_at,
        updated_at=new_member.updated_at,
        user_email=current_user.email,
        user_name=current_user.name,
    )


@router.post("/invites/{invite_id}/reject", status_code=status.HTTP_204_NO_CONTENT)
async def reject_project_invite(
    invite_id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.get_current_user),
) -> Response:
    """
    Rejeita um convite para se tornar membro do projeto.

    O convite deve estar pendente e o email deve corresponder ao do usuário atual.
    """
    # Find invite
    invite = await db.get(ProjectInvite, invite_id)
    if not invite:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail="Convite não encontrado"
        )

    # Verify invite email matches current user's email
    if invite.invited_email.lower() != current_user.email.lower():
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Este convite não é para você"
        )

    # Verify invite is pending
    if invite.status != "pending":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"Convite já foi {invite.status}"
        )

    # Update invite status
    invite.status = "rejected"
    await db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{project_id}/invites/{invite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_project_invite(
    project_id: int,
    invite_id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.require_roles("owner", "admin")),
) -> Response:
    """
    Cancela um convite pendente.

    **Permissão:** owner, admin

    O convite deve estar pendente e pertencer ao projeto especificado.
    """
    account = await _get_account_or_404(db, current_user)
    project = await _get_project_or_404(db, account, project_id)

    # Find invite
    invite = await db.get(ProjectInvite, invite_id)
    if not invite or invite.project_id != project.id:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail="Convite não encontrado neste projeto"
        )

    # Verify invite is pending
    if invite.status != "pending":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"Convite já foi {invite.status}"
        )

    # Update invite status
    invite.status = "cancelled"
    await db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{project_id}/hierarchy", response_model=HierarchyResponse)
async def get_project_hierarchy(
    project_id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.get_current_user),
) -> HierarchyResponse:
    """
    Retorna a hierarquia completa do projeto (épicos > histórias > tarefas).

    Organiza os itens em uma estrutura hierárquica baseada em:
    - Épicos (campo Epic do projeto)
    - Relacionamentos pai-filho (campo parent_item_id)
    - Tipo de item (item_type derivado de labels)

    Retorna items agrupados por épico, com estrutura aninhada de histórias e tarefas.
    """
    account = await _get_account_or_404(db, current_user)
    project = await _get_project_or_404(db, account, project_id)

    # Load all project items
    stmt = (
        select(ProjectItem)
        .where(ProjectItem.project_id == project.id)
        .order_by(ProjectItem.title)
    )
    result = await db.execute(stmt)
    all_items = result.scalars().all()

    # Build item lookup map
    items_by_id = {item.id: item for item in all_items}

    # Helper function to build item tree recursively
    def build_item_response(item: ProjectItem, visited: set[int]) -> HierarchyItemResponse:
        """Build hierarchical item response with children."""
        if item.id in visited:
            # Prevent circular references
            return HierarchyItemResponse(
                id=item.id,
                item_node_id=item.item_node_id,
                title=item.title,
                item_type=item.item_type,
                status=item.status,
                epic_name=item.epic_name,
                parent_item_id=item.parent_item_id,
                labels=item.labels,
                children=[]
            )

        visited.add(item.id)

        # Find children
        children = [
            build_item_response(child, visited)
            for child in all_items
            if child.parent_item_id == item.id
        ]

        return HierarchyItemResponse(
            id=item.id,
            item_node_id=item.item_node_id,
            title=item.title,
            item_type=item.item_type,
            status=item.status,
            epic_name=item.epic_name,
            parent_item_id=item.parent_item_id,
            labels=item.labels,
            children=children
        )

    # Group items by epic
    epics_map: dict[str | None, list[ProjectItem]] = defaultdict(list)
    root_items = []  # Items with no parent

    for item in all_items:
        if item.parent_item_id is None:
            root_items.append(item)

    # Group root items by epic
    for item in root_items:
        epic_key = item.epic_option_id or item.epic_name
        epics_map[epic_key].append(item)

    # Build response
    epics = []
    orphans = []

    for epic_key, items in epics_map.items():
        visited: set[int] = set()
        items_tree = [build_item_response(item, visited) for item in items]

        if epic_key is None:
            # Items without epic
            orphans.extend(items_tree)
        else:
            # Items with epic
            epic_name = items[0].epic_name if items else None
            epics.append(
                HierarchyEpicResponse(
                    epic_option_id=epic_key,
                    epic_name=epic_name,
                    items=items_tree
                )
            )

    return HierarchyResponse(epics=epics, orphans=orphans)
