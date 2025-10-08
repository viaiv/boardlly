"""
Service layer para gerenciamento de Change Requests.

Lógica de negócio para aprovação e rejeição de solicitações,
incluindo criação automática de Issues no GitHub.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.change_request import ChangeRequest
from app.models.github_project import GithubProject
from app.models.user import AppUser
from app.services.github import GithubGraphQLClient, get_github_token

if TYPE_CHECKING:
    from app.schemas.change_request import ChangeRequestApprove, ChangeRequestReject


async def get_github_project(db: AsyncSession, account_id: str) -> GithubProject:
    """Busca projeto GitHub configurado para a conta"""
    stmt = select(GithubProject).where(GithubProject.account_id == account_id)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail="Projeto GitHub não configurado. Configure em /settings",
        )
    return project


async def create_issue_from_request(
    client: GithubGraphQLClient,
    request: ChangeRequest,
    project: GithubProject,
    creator_name: str,
) -> tuple[str, int, str]:
    """
    Cria uma Issue no GitHub a partir de uma ChangeRequest.

    Returns:
        Tupla (issue_node_id, issue_number, issue_url)
    """
    # Buscar repositório associado ao projeto
    # Projects v2 podem estar em org ou repo, vamos buscar o primeiro repo da org
    repo_query = """
    query($login: String!) {
      organization(login: $login) {
        repositories(first: 1, orderBy: {field: CREATED_AT, direction: DESC}) {
          nodes {
            id
            name
          }
        }
      }
    }
    """
    repo_data = await client.execute(repo_query, {"login": project.owner_login})
    repositories = repo_data.get("organization", {}).get("repositories", {}).get("nodes", [])

    if not repositories:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail=f"Nenhum repositório encontrado para {project.owner_login}. Configure um repositório padrão.",
        )

    repo_node_id = repositories[0]["id"]
    repo_name = repositories[0]["name"]

    # Montar corpo da Issue
    issue_body = _build_issue_body(request, creator_name)

    # Buscar labels existentes para mapear prioridade
    labels_to_apply = _get_labels_for_request(request)

    # Criar Issue
    create_mutation = """
    mutation($repositoryId: ID!, $title: String!, $body: String) {
      createIssue(input: {repositoryId: $repositoryId, title: $title, body: $body}) {
        issue {
          id
          number
          url
        }
      }
    }
    """

    create_variables = {
        "repositoryId": repo_node_id,
        "title": request.title,
        "body": issue_body,
    }

    create_data = await client.execute(create_mutation, create_variables)
    issue = create_data.get("createIssue", {}).get("issue", {})
    if not issue or not issue.get("id"):
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, detail="Falha ao criar Issue no GitHub"
        )

    return issue["id"], issue["number"], issue["url"]


async def add_issue_to_project(
    client: GithubGraphQLClient, project_node_id: str, issue_node_id: str
) -> str:
    """
    Adiciona uma Issue ao Project.

    Returns:
        project_item_node_id
    """
    add_mutation = """
    mutation($projectId: ID!, $contentId: ID!) {
      addProjectV2ItemById(input: {projectId: $projectId, contentId: $contentId}) {
        item {
          id
        }
      }
    }
    """

    add_variables = {"projectId": project_node_id, "contentId": issue_node_id}

    add_data = await client.execute(add_mutation, add_variables)
    project_item = add_data.get("addProjectV2ItemById", {}).get("item", {})
    project_item_node_id = project_item.get("id")

    if not project_item_node_id:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao adicionar Issue ao Project",
        )

    return project_item_node_id


def _build_issue_body(request: ChangeRequest, creator_name: str) -> str:
    """Constrói o corpo da Issue com informações da solicitação"""
    lines = []

    if request.description:
        lines.append(request.description)
        lines.append("")

    lines.append("---")
    lines.append("")

    # Metadados
    if request.impact:
        lines.append(f"**Impacto:** {request.impact}")
    lines.append(f"**Prioridade:** {request.priority}")
    if request.request_type:
        lines.append(f"**Tipo:** {request.request_type}")
    lines.append(f"**Solicitado por:** {creator_name}")
    lines.append("")

    # Link para o Tactyo (futuro)
    lines.append(f"_Criado a partir da Change Request `{request.id}`_")

    return "\n".join(lines)


def _get_labels_for_request(request: ChangeRequest) -> list[str]:
    """Mapeia prioridade/tipo da request para labels do GitHub"""
    labels = []

    # Mapear prioridade
    priority_labels = {
        "low": "priority: low",
        "medium": "priority: medium",
        "high": "priority: high",
        "urgent": "priority: urgent",
    }
    if request.priority in priority_labels:
        labels.append(priority_labels[request.priority])

    # Mapear tipo
    type_labels = {
        "feature": "type: feature",
        "bug": "type: bug",
        "tech_debt": "type: tech debt",
        "docs": "type: documentation",
    }
    if request.request_type and request.request_type in type_labels:
        labels.append(type_labels[request.request_type])

    return labels


async def approve_change_request(
    db: AsyncSession,
    request: ChangeRequest,
    reviewer: AppUser,
    data: ChangeRequestApprove,
) -> ChangeRequest:
    """
    Aprova uma solicitação e opcionalmente cria Issue no GitHub.

    Flow:
    1. Atualiza status para 'approved'
    2. Se create_issue=True:
       - Cria Issue no GitHub
       - Adiciona ao Project (se add_to_project=True)
       - Atualiza status para 'converted'
    """
    # 1. Atualizar status da request
    request.status = "approved"
    request.reviewed_by = reviewer.id
    request.reviewed_at = datetime.utcnow()
    request.review_notes = data.review_notes

    # 2. Criar Issue (se solicitado)
    if data.create_issue:
        project = await get_github_project(db, request.account_id)

        # Obter token GitHub
        token = await get_github_token(db, request.account_id)
        client = GithubGraphQLClient(token)

        # Buscar nome do criador
        creator = await db.get(AppUser, request.created_by)
        creator_name = creator.name or creator.email if creator else "Unknown"

        # Criar Issue
        issue_node_id, issue_number, issue_url = await create_issue_from_request(
            client, request, project, creator_name
        )

        request.github_issue_node_id = issue_node_id
        request.github_issue_number = issue_number
        request.github_issue_url = issue_url

        # 3. Adicionar ao Project (se solicitado)
        if data.add_to_project:
            await add_issue_to_project(client, project.project_node_id, issue_node_id)

            # TODO: Aplicar fields sugeridos (epic, iteration, estimate)
            # Isso requer buscar os field IDs do projeto e executar mutations
            # para updateProjectV2ItemFieldValue

        request.status = "converted"
        request.converted_at = datetime.utcnow()

    await db.commit()
    await db.refresh(request)
    return request


async def reject_change_request(
    db: AsyncSession,
    request: ChangeRequest,
    reviewer: AppUser,
    data: ChangeRequestReject,
) -> ChangeRequest:
    """Rejeita uma solicitação"""
    request.status = "rejected"
    request.reviewed_by = reviewer.id
    request.reviewed_at = datetime.utcnow()
    request.review_notes = data.review_notes

    await db.commit()
    await db.refresh(request)
    return request
