from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Header, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.account import Account
from app.models.epic_option import EpicOption
from app.models.github_project import GithubProject
from app.models.user import AppUser
from app.schemas.epic import EpicOptionCreate, EpicOptionResponse, EpicOptionUpdate
from app.schemas.github import EpicOptionResponse as GithubEpicOptionResponse
from app.services.github import GithubGraphQLClient, get_github_token

router = APIRouter(tags=["epics"])


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
    Get project by ID or return the first project from account.

    Args:
        db: Database session
        account: User's account
        project_id: Project ID (optional, comes from X-Project-Id header)
    """
    if project_id:
        project = await db.get(GithubProject, project_id)
        if not project:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Projeto não encontrado")
        if project.account_id != account.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Acesso negado ao projeto")
        return project

    # Get first project if no ID specified
    stmt = select(GithubProject).where(GithubProject.account_id == account.id).limit(1)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Nenhum projeto conectado")

    return project


# ============================================================================
# ROUTES: /projects/current/epics (uses X-Project-Id header)
# ============================================================================

@router.get("/projects/current/epics", response_model=list[GithubEpicOptionResponse])
async def list_epics_current(
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.get_current_user),
    x_project_id: int | None = Header(None, alias="X-Project-Id"),
) -> list[GithubEpicOptionResponse]:
    """
    Lista todos os épicos disponíveis no projeto atual.

    Épicos são buscados do campo customizado 'Epic' do GitHub Projects V2.
    """
    from app.services.github import list_epic_options

    account = await _get_account_or_404(db, current_user)
    project = await _get_project_or_404(db, account, x_project_id)

    # Buscar opções do campo Epic do GitHub Projects
    epic_options = await list_epic_options(db, project)

    return [
        GithubEpicOptionResponse(
            id=option.id,
            name=option.name,
            color=option.color,
            description=option.description,
        )
        for option in epic_options
    ]


@router.post("/projects/current/epics", response_model=EpicOptionResponse, status_code=status.HTTP_201_CREATED)
async def create_epic_current(
    payload: EpicOptionCreate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.get_current_user),
    x_project_id: int | None = Header(None, alias="X-Project-Id"),
) -> EpicOptionResponse:
    """Cria um novo épico no projeto atual."""
    account = await _get_account_or_404(db, current_user)
    project = await _get_project_or_404(db, account, x_project_id)

    token = await get_github_token(db, project.account_id)

    import secrets
    option_id = f"PVTSSFO_{secrets.token_hex(16)}"

    epic = EpicOption(
        project_id=project.id,
        option_id=option_id,
        option_name=payload.option_name,
        color=payload.color,
        description=payload.description,
    )

    db.add(epic)
    await db.commit()
    await db.refresh(epic)

    return EpicOptionResponse.model_validate(epic)


@router.get("/projects/current/epics/{epic_id}", response_model=EpicOptionResponse)
async def get_epic_current(
    epic_id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.get_current_user),
    x_project_id: int | None = Header(None, alias="X-Project-Id"),
) -> EpicOptionResponse:
    """Retorna detalhes de um épico específico do projeto atual."""
    account = await _get_account_or_404(db, current_user)
    project = await _get_project_or_404(db, account, x_project_id)

    epic = await db.get(EpicOption, epic_id)
    if not epic or epic.project_id != project.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Épico não encontrado")

    return EpicOptionResponse.model_validate(epic)


@router.patch("/projects/current/epics/{epic_id}", response_model=EpicOptionResponse)
async def update_epic_current(
    epic_id: int,
    payload: EpicOptionUpdate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.get_current_user),
    x_project_id: int | None = Header(None, alias="X-Project-Id"),
) -> EpicOptionResponse:
    """Atualiza um épico do projeto atual."""
    account = await _get_account_or_404(db, current_user)
    project = await _get_project_or_404(db, account, x_project_id)

    epic = await db.get(EpicOption, epic_id)
    if not epic or epic.project_id != project.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Épico não encontrado")

    if payload.option_name is not None:
        epic.option_name = payload.option_name
    if payload.color is not None:
        epic.color = payload.color
    if payload.description is not None:
        epic.description = payload.description

    await db.commit()
    await db.refresh(epic)

    return EpicOptionResponse.model_validate(epic)


@router.delete("/projects/current/epics/{epic_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_epic_current(
    epic_id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.get_current_user),
    x_project_id: int | None = Header(None, alias="X-Project-Id"),
) -> Response:
    """Deleta um épico do projeto atual."""
    account = await _get_account_or_404(db, current_user)
    project = await _get_project_or_404(db, account, x_project_id)

    epic = await db.get(EpicOption, epic_id)
    if not epic or epic.project_id != project.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Épico não encontrado")

    await db.delete(epic)
    await db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ============================================================================
# ROUTES: /projects/{project_id}/epics (explicit project ID)
# ============================================================================

@router.get("/projects/{project_id}/epics", response_model=list[EpicOptionResponse])
async def list_epics(
    project_id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.get_current_user),
) -> list[EpicOptionResponse]:
    """
    Lista todos os épicos do projeto.
    """
    account = await _get_account_or_404(db, current_user)
    project = await _get_project_or_404(db, account, project_id)

    stmt = select(EpicOption).where(EpicOption.project_id == project.id)
    result = await db.execute(stmt)
    epics = result.scalars().all()

    return [EpicOptionResponse.model_validate(epic) for epic in epics]


@router.post("/projects/{project_id}/epics", response_model=EpicOptionResponse, status_code=status.HTTP_201_CREATED)
async def create_epic(
    project_id: int,
    payload: EpicOptionCreate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.get_current_user),
) -> EpicOptionResponse:
    """
    Cria um novo épico no projeto.

    O épico é criado tanto localmente quanto no GitHub Projects V2
    como uma nova opção do campo SingleSelect "Epic".
    """
    account = await _get_account_or_404(db, current_user)
    project = await _get_project_or_404(db, account, project_id)

    # Get GitHub token
    token = await get_github_token(db, project.account_id)

    # Create epic option on GitHub via GraphQL
    client = GithubGraphQLClient(token)

    # First, get the Epic field ID (we need to implement this)
    # For now, let's create a placeholder option_id (will be replaced with real GraphQL call)
    import secrets
    option_id = f"PVTSSFO_{secrets.token_hex(16)}"  # Placeholder GitHub node ID

    # TODO: Call GraphQL mutation to create epic option on GitHub
    # mutation_result = await client.create_epic_option(
    #     project_node_id=project.project_node_id,
    #     epic_field_id=epic_field_id,
    #     name=payload.option_name,
    #     color=payload.color,
    #     description=payload.description
    # )
    # option_id = mutation_result["id"]

    # Create epic option in database
    epic = EpicOption(
        project_id=project.id,
        option_id=option_id,
        option_name=payload.option_name,
        color=payload.color,
        description=payload.description,
    )

    db.add(epic)
    await db.commit()
    await db.refresh(epic)

    return EpicOptionResponse.model_validate(epic)


@router.get("/projects/{project_id}/epics/{epic_id}", response_model=EpicOptionResponse)
async def get_epic(
    project_id: int,
    epic_id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.get_current_user),
) -> EpicOptionResponse:
    """
    Retorna detalhes de um épico específico.
    """
    account = await _get_account_or_404(db, current_user)
    project = await _get_project_or_404(db, account, project_id)

    epic = await db.get(EpicOption, epic_id)
    if not epic or epic.project_id != project.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Épico não encontrado")

    return EpicOptionResponse.model_validate(epic)


@router.patch("/projects/{project_id}/epics/{epic_id}", response_model=EpicOptionResponse)
async def update_epic(
    project_id: int,
    epic_id: int,
    payload: EpicOptionUpdate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.get_current_user),
) -> EpicOptionResponse:
    """
    Atualiza um épico existente.

    Atualiza tanto localmente quanto no GitHub Projects V2.
    """
    account = await _get_account_or_404(db, current_user)
    project = await _get_project_or_404(db, account, project_id)

    epic = await db.get(EpicOption, epic_id)
    if not epic or epic.project_id != project.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Épico não encontrado")

    # Get GitHub token
    token = await get_github_token(db, project.account_id)
    client = GithubGraphQLClient(token)

    # TODO: Call GraphQL mutation to update epic option on GitHub
    # await client.update_epic_option(
    #     option_node_id=epic.option_id,
    #     name=payload.option_name,
    #     color=payload.color,
    #     description=payload.description
    # )

    # Update local database
    if payload.option_name is not None:
        epic.option_name = payload.option_name
    if payload.color is not None:
        epic.color = payload.color
    if payload.description is not None:
        epic.description = payload.description

    await db.commit()
    await db.refresh(epic)

    return EpicOptionResponse.model_validate(epic)


@router.delete("/projects/{project_id}/epics/{epic_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_epic(
    project_id: int,
    epic_id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: AppUser = Depends(deps.get_current_user),
) -> Response:
    """
    Deleta um épico.

    Remove tanto localmente quanto do GitHub Projects V2.
    """
    account = await _get_account_or_404(db, current_user)
    project = await _get_project_or_404(db, account, project_id)

    epic = await db.get(EpicOption, epic_id)
    if not epic or epic.project_id != project.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Épico não encontrado")

    # Get GitHub token
    token = await get_github_token(db, project.account_id)
    client = GithubGraphQLClient(token)

    # TODO: Call GraphQL mutation to delete epic option on GitHub
    # await client.delete_epic_option(option_node_id=epic.option_id)

    # Delete from local database
    await db.delete(epic)
    await db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
