"""
Serviço para processar webhooks do GitHub.

Valida assinaturas HMAC e processa eventos:
- project_v2_item: sincroniza itens do projeto
- issues: sincroniza issues
- pull_request: sincroniza PRs
"""

import hashlib
import hmac
import logging
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.github_project import GithubProject
from app.models.project_item import ProjectItem
from app.core.config import settings

logger = logging.getLogger("tactyo.webhook")


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    Verifica a assinatura HMAC-SHA256 do webhook do GitHub.

    Args:
        payload: Body da requisição (bytes)
        signature: Header X-Hub-Signature-256 (formato: sha256=...)
        secret: Webhook secret configurado

    Returns:
        bool: True se assinatura válida

    Raises:
        HTTPException: Se assinatura inválida ou formato incorreto
    """
    if not signature or not signature.startswith("sha256="):
        logger.warning("Webhook signature missing or invalid format")
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature format",
        )

    # Extrair hash da assinatura
    provided_hash = signature.split("=", 1)[1]

    # Calcular hash esperado
    expected_hash = hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()

    # Comparação segura contra timing attacks
    if not hmac.compare_digest(provided_hash, expected_hash):
        logger.warning("Webhook signature mismatch")
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature",
        )

    return True


async def handle_project_v2_item_event(
    db: AsyncSession,
    event_action: str,
    payload: dict[str, Any],
) -> None:
    """
    Processa eventos de project_v2_item.

    Ações suportadas:
    - created: novo item adicionado ao projeto
    - edited: item atualizado (fields, posição)
    - deleted: item removido do projeto
    - converted: draft convertido em issue
    - archived/reordered: atualizações de estado

    Args:
        db: Sessão do banco
        event_action: Ação do evento (created, edited, etc)
        payload: Payload do webhook
    """
    logger.info(f"Processing project_v2_item event: {event_action}")

    try:
        # Extrair dados do payload
        project_item_data = payload.get("projects_v2_item", {})
        project_data = payload.get("project_v2", {})

        item_node_id = project_item_data.get("node_id")
        project_node_id = project_data.get("node_id")

        if not item_node_id or not project_node_id:
            logger.warning("Missing node IDs in project_v2_item webhook")
            return

        # Buscar projeto no banco
        stmt = select(GithubProject).where(
            GithubProject.project_node_id == project_node_id
        )
        result = await db.execute(stmt)
        project = result.scalar_one_or_none()

        if not project:
            logger.info(f"Project {project_node_id} not found in database, ignoring webhook")
            return

        if event_action == "deleted":
            # Remover item do banco
            stmt = select(ProjectItem).where(ProjectItem.item_node_id == item_node_id)
            result = await db.execute(stmt)
            item = result.scalar_one_or_none()

            if item:
                await db.delete(item)
                await db.commit()
                logger.info(f"Deleted project item {item_node_id}")

        else:
            # Para created/edited: fazer sync completo do projeto
            # (mais simples que tentar atualizar apenas este item)
            from app.services.github import get_github_token, sync_github_project

            account = await db.get(Account, project.account_id)
            if account:
                token = await get_github_token(db, account)
                count = await sync_github_project(db, account, project, token)
                logger.info(f"Synced project {project.id} via webhook: {count} items")

    except Exception as e:
        logger.error(f"Error processing project_v2_item webhook: {e}", exc_info=True)
        # Não lançar exceção - webhook deve retornar 200 mesmo com erro


async def handle_issues_event(
    db: AsyncSession,
    event_action: str,
    payload: dict[str, Any],
) -> None:
    """
    Processa eventos de issues.

    Ações suportadas:
    - opened: nova issue criada
    - edited: issue atualizada (título, descrição, labels)
    - closed: issue fechada
    - reopened: issue reaberta
    - assigned/unassigned: assignees alterados

    Args:
        db: Sessão do banco
        event_action: Ação do evento
        payload: Payload do webhook
    """
    logger.info(f"Processing issues event: {event_action}")

    try:
        issue = payload.get("issue", {})
        issue_node_id = issue.get("node_id")

        if not issue_node_id:
            logger.warning("Missing issue node_id in webhook")
            return

        # Buscar item do projeto associado à issue
        stmt = select(ProjectItem).where(ProjectItem.content_node_id == issue_node_id)
        result = await db.execute(stmt)
        items = result.scalars().all()

        if not items:
            logger.info(f"Issue {issue_node_id} not found in any project, ignoring")
            return

        # Atualizar cada projeto que contém esta issue
        for item in items:
            project = await db.get(GithubProject, item.project_id)
            if project:
                from app.services.github import get_github_token, sync_github_project

                account = await db.get(Account, project.account_id)
                if account:
                    token = await get_github_token(db, account)
                    await sync_github_project(db, account, project, token)
                    logger.info(f"Synced project {project.id} due to issue update")

    except Exception as e:
        logger.error(f"Error processing issues webhook: {e}", exc_info=True)


async def handle_pull_request_event(
    db: AsyncSession,
    event_action: str,
    payload: dict[str, Any],
) -> None:
    """
    Processa eventos de pull_request.

    Ações suportadas:
    - opened: novo PR criado
    - closed: PR fechado/merged
    - reopened: PR reaberto
    - edited: PR atualizado

    Args:
        db: Sessão do banco
        event_action: Ação do evento
        payload: Payload do webhook
    """
    logger.info(f"Processing pull_request event: {event_action}")

    try:
        pr = payload.get("pull_request", {})
        pr_node_id = pr.get("node_id")

        if not pr_node_id:
            logger.warning("Missing PR node_id in webhook")
            return

        # Buscar item do projeto associado ao PR
        stmt = select(ProjectItem).where(ProjectItem.content_node_id == pr_node_id)
        result = await db.execute(stmt)
        items = result.scalars().all()

        if not items:
            logger.info(f"PR {pr_node_id} not found in any project, ignoring")
            return

        # Atualizar cada projeto que contém este PR
        for item in items:
            project = await db.get(GithubProject, item.project_id)
            if project:
                from app.services.github import get_github_token, sync_github_project

                account = await db.get(Account, project.account_id)
                if account:
                    token = await get_github_token(db, account)
                    await sync_github_project(db, account, project, token)
                    logger.info(f"Synced project {project.id} due to PR update")

    except Exception as e:
        logger.error(f"Error processing pull_request webhook: {e}", exc_info=True)


# Mapeamento de eventos para handlers
WEBHOOK_HANDLERS = {
    "project_v2_item": handle_project_v2_item_event,
    "issues": handle_issues_event,
    "pull_request": handle_pull_request_event,
}
