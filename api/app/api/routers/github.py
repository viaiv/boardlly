from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.config import settings
from app.models.account import Account
from app.models.github_project import GithubProject
from app.models.user import AppUser
from app.schemas.github import GithubProjectResponse
from app.services.github import get_github_token, sync_github_project
from app.services.scheduler import get_scheduler_status
from app.services.webhook import WEBHOOK_HANDLERS, verify_webhook_signature

router = APIRouter(prefix="/github", tags=["github"])
logger = logging.getLogger("tactyo.api.github")


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


@router.get("/scheduler/status")
async def get_scheduler_info(
    current_user: AppUser = Depends(deps.require_roles("owner", "admin")),
) -> dict:
    """
    Retorna status do scheduler e jobs agendados.

    **Permissão:** admin, owner

    **Response:**
    ```json
    {
      "running": true,
      "jobs": [{
        "id": "sync_all_projects",
        "name": "Sincronização automática de projetos GitHub",
        "next_run_time": "2025-10-07T23:30:00",
        "trigger": "cron[minute='*/15']"
      }]
    }
    ```
    """
    return get_scheduler_status()


@router.post("/webhooks")
async def receive_github_webhook(
    request: Request,
    db: AsyncSession = Depends(deps.get_db),
    x_hub_signature_256: str | None = Header(None, alias="X-Hub-Signature-256"),
    x_github_event: str | None = Header(None, alias="X-GitHub-Event"),
    x_github_delivery: str | None = Header(None, alias="X-GitHub-Delivery"),
) -> dict[str, str]:
    """
    Recebe e processa webhooks do GitHub.

    **Eventos suportados:**
    - `project_v2_item`: Itens adicionados/editados/removidos do projeto
    - `issues`: Issues criadas/editadas/fechadas
    - `pull_request`: PRs criados/editados/merged

    **Configuração no GitHub:**
    1. Vá em Settings → Webhooks → Add webhook
    2. Payload URL: `https://seu-dominio.com/api/github/webhooks`
    3. Content type: `application/json`
    4. Secret: Configure `TACTYO_WEBHOOK_SECRET`
    5. Events: Selecione `Project cards`, `Issues`, `Pull requests`

    **Headers esperados:**
    - X-Hub-Signature-256: Assinatura HMAC-SHA256 do payload
    - X-GitHub-Event: Tipo de evento
    - X-GitHub-Delivery: ID único da entrega

    **Response:**
    - 200: Webhook processado com sucesso
    - 401: Assinatura inválida
    - 400: Evento não suportado ou payload inválido
    """
    # Validar headers
    if not x_github_event:
        logger.warning("Webhook received without X-GitHub-Event header")
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Missing X-GitHub-Event header",
        )

    if not x_hub_signature_256:
        logger.warning("Webhook received without signature")
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Hub-Signature-256 header",
        )

    # Ler payload
    payload_bytes = await request.body()

    # Validar assinatura HMAC
    if not settings.webhook_secret:
        logger.error("TACTYO_WEBHOOK_SECRET not configured")
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook secret not configured",
        )

    verify_webhook_signature(payload_bytes, x_hub_signature_256, settings.webhook_secret)

    # Parsear payload
    try:
        payload: dict[str, Any] = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse webhook payload: {e}")
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        )

    # Log do webhook
    logger.info(
        f"Received GitHub webhook: event={x_github_event}, "
        f"delivery={x_github_delivery}, "
        f"action={payload.get('action', 'N/A')}"
    )

    # Buscar handler para o evento
    handler = WEBHOOK_HANDLERS.get(x_github_event)

    if not handler:
        logger.info(f"No handler for event type: {x_github_event}")
        return {"status": "ignored", "reason": f"Event type '{x_github_event}' not supported"}

    # Processar evento
    try:
        event_action = payload.get("action", "unknown")
        await handler(db, event_action, payload)

        logger.info(f"Successfully processed {x_github_event} webhook")
        return {"status": "processed", "event": x_github_event, "action": event_action}

    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        # Retornar 200 para evitar redelivery do GitHub
        return {"status": "error", "message": str(e)}
