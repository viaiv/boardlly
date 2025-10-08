"""
Router para Change Requests (Solicitações de Mudança).

Endpoints para o fluxo completo:
- Editor cria solicitação
- PM lista/visualiza/aprova/rejeita
- Criação automática de Issue no GitHub
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.api import deps
from app.models.change_request import ChangeRequest
from app.models.user import AppUser
from app.schemas.change_request import (
    ChangeRequestCreate,
    ChangeRequestUpdate,
    ChangeRequestApprove,
    ChangeRequestReject,
    ChangeRequestResponse,
    ChangeRequestListResponse,
)
from app.services.change_request import (
    approve_change_request,
    reject_change_request,
)

router = APIRouter(prefix="/requests", tags=["change_requests"])


def _check_permission(user: AppUser, required_roles: list[str]) -> None:
    """Valida se usuário tem permissão (role)"""
    if user.role not in required_roles:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail=f"Permissão insuficiente. Roles permitidas: {', '.join(required_roles)}",
        )


@router.post("", response_model=ChangeRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_change_request(
    data: ChangeRequestCreate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.get_current_user),
) -> ChangeRequestResponse:
    """
    Cria uma nova solicitação de mudança.

    **Permissão:** editor, pm, admin, owner
    """
    _check_permission(current_user, ["editor", "pm", "admin", "owner"])

    if not current_user.account_id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Usuário não está associado a uma conta"
        )

    request = ChangeRequest(
        account_id=current_user.account_id,
        created_by=current_user.id,
        **data.model_dump(),
    )
    db.add(request)
    await db.commit()
    await db.refresh(request, ["creator"])

    # Montar response com creator_name
    response = ChangeRequestResponse.model_validate(request)
    response.creator_name = request.creator.name if request.creator else None

    return response


@router.get("", response_model=list[ChangeRequestListResponse])
async def list_change_requests(
    status_filter: Optional[str] = Query(
        None, description="Filtrar por status: pending, approved, rejected, converted"
    ),
    priority_filter: Optional[str] = Query(
        None, description="Filtrar por prioridade: low, medium, high, urgent"
    ),
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.get_current_user),
) -> list[ChangeRequestListResponse]:
    """
    Lista solicitações da conta do usuário.

    **Filtros opcionais:**
    - `status_filter`: pending, approved, rejected, converted
    - `priority_filter`: low, medium, high, urgent
    """
    if not current_user.account_id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Usuário não está associado a uma conta"
        )

    stmt = (
        select(ChangeRequest)
        .options(joinedload(ChangeRequest.creator))
        .where(ChangeRequest.account_id == current_user.account_id)
    )

    if status_filter:
        stmt = stmt.where(ChangeRequest.status == status_filter)
    if priority_filter:
        stmt = stmt.where(ChangeRequest.priority == priority_filter)

    stmt = stmt.order_by(ChangeRequest.created_at.desc())

    result = await db.execute(stmt)
    requests = result.unique().scalars().all()

    # Montar respostas com creator_name
    responses = []
    for req in requests:
        response = ChangeRequestListResponse.model_validate(req)
        response.creator_name = req.creator.name if req.creator else None
        responses.append(response)

    return responses


@router.get("/{request_id}", response_model=ChangeRequestResponse)
async def get_change_request(
    request_id: UUID,
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.get_current_user),
) -> ChangeRequestResponse:
    """Obtém detalhes de uma solicitação específica"""
    stmt = (
        select(ChangeRequest)
        .options(joinedload(ChangeRequest.creator), joinedload(ChangeRequest.reviewer))
        .where(ChangeRequest.id == request_id)
    )
    result = await db.execute(stmt)
    request = result.unique().scalar_one_or_none()

    if not request or request.account_id != current_user.account_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Solicitação não encontrada")

    # Montar response com names
    response = ChangeRequestResponse.model_validate(request)
    response.creator_name = request.creator.name if request.creator else None
    response.reviewer_name = request.reviewer.name if request.reviewer else None

    return response


@router.patch("/{request_id}", response_model=ChangeRequestResponse)
async def update_change_request(
    request_id: UUID,
    data: ChangeRequestUpdate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.get_current_user),
) -> ChangeRequestResponse:
    """
    Atualiza uma solicitação.

    **Permissão:** Criador da solicitação OU pm/admin/owner
    """
    stmt = select(ChangeRequest).where(ChangeRequest.id == request_id)
    result = await db.execute(stmt)
    request = result.scalar_one_or_none()

    if not request or request.account_id != current_user.account_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Solicitação não encontrada")

    # Verificar permissão: criador ou PM+
    if request.created_by != current_user.id:
        _check_permission(current_user, ["pm", "admin", "owner"])

    # Aplicar atualizações
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(request, key, value)

    await db.commit()
    await db.refresh(request, ["creator"])

    response = ChangeRequestResponse.model_validate(request)
    response.creator_name = request.creator.name if request.creator else None

    return response


@router.post("/{request_id}/approve", response_model=ChangeRequestResponse)
async def approve_request(
    request_id: UUID,
    data: ChangeRequestApprove,
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.get_current_user),
) -> ChangeRequestResponse:
    """
    Aprova uma solicitação e opcionalmente cria Issue no GitHub.

    **Permissão:** pm, admin, owner

    **Ações:**
    1. Marca solicitação como 'approved'
    2. Se `create_issue=true`: cria Issue no GitHub
    3. Se `add_to_project=true`: adiciona Issue ao Project
    4. Marca como 'converted' após criação bem-sucedida
    """
    _check_permission(current_user, ["pm", "admin", "owner"])

    stmt = select(ChangeRequest).where(ChangeRequest.id == request_id)
    result = await db.execute(stmt)
    request = result.scalar_one_or_none()

    if not request or request.account_id != current_user.account_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Solicitação não encontrada")

    if request.status != "pending":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"Solicitação já foi processada (status: {request.status})",
        )

    # Service layer: cria Issue, adiciona ao Project, atualiza request
    updated_request = await approve_change_request(db, request, current_user, data)

    await db.refresh(updated_request, ["creator", "reviewer"])

    response = ChangeRequestResponse.model_validate(updated_request)
    response.creator_name = updated_request.creator.name if updated_request.creator else None
    response.reviewer_name = updated_request.reviewer.name if updated_request.reviewer else None

    return response


@router.post("/{request_id}/reject", response_model=ChangeRequestResponse)
async def reject_request(
    request_id: UUID,
    data: ChangeRequestReject,
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.get_current_user),
) -> ChangeRequestResponse:
    """
    Rejeita uma solicitação.

    **Permissão:** pm, admin, owner
    """
    _check_permission(current_user, ["pm", "admin", "owner"])

    stmt = select(ChangeRequest).where(ChangeRequest.id == request_id)
    result = await db.execute(stmt)
    request = result.scalar_one_or_none()

    if not request or request.account_id != current_user.account_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Solicitação não encontrada")

    if request.status != "pending":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"Solicitação já foi processada (status: {request.status})",
        )

    updated_request = await reject_change_request(db, request, current_user, data)

    await db.refresh(updated_request, ["creator", "reviewer"])

    response = ChangeRequestResponse.model_validate(updated_request)
    response.creator_name = updated_request.creator.name if updated_request.creator else None
    response.reviewer_name = updated_request.reviewer.name if updated_request.reviewer else None

    return response


@router.get("/stats/summary")
async def get_requests_summary(
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.get_current_user),
) -> dict:
    """
    Retorna estatísticas resumidas das solicitações.

    **Response:**
    ```json
    {
      "total": 42,
      "pending": 10,
      "approved": 5,
      "rejected": 2,
      "converted": 25
    }
    ```
    """
    if not current_user.account_id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Usuário não está associado a uma conta"
        )

    stmt = (
        select(ChangeRequest.status, func.count(ChangeRequest.id).label("count"))
        .where(ChangeRequest.account_id == current_user.account_id)
        .group_by(ChangeRequest.status)
    )

    result = await db.execute(stmt)
    stats = {row[0]: row[1] for row in result.all()}

    return {
        "total": sum(stats.values()),
        "pending": stats.get("pending", 0),
        "approved": stats.get("approved", 0),
        "rejected": stats.get("rejected", 0),
        "converted": stats.get("converted", 0),
    }
