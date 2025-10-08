"""
Serviço de agendamento de tarefas usando APScheduler.

Gerencia jobs periódicos como:
- Sincronização automática de Projects do GitHub
"""

import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import SessionLocal
from app.models.account import Account
from app.models.github_project import GithubProject
from app.services.github import get_github_token, sync_github_project

logger = logging.getLogger("tactyo.scheduler")

# Scheduler global
scheduler: AsyncIOScheduler | None = None


async def sync_all_projects():
    """
    Job agendado que sincroniza todos os projetos ativos.

    Percorre todas as contas com projetos configurados e executa sync.
    """
    logger.info("Iniciando sincronização automática de todos os projetos")

    async with SessionLocal() as db:
        # Buscar todos os projetos ativos
        stmt = select(GithubProject).join(Account)
        result = await db.execute(stmt)
        projects = result.scalars().all()

        synced_count = 0
        error_count = 0

        for project in projects:
            try:
                logger.info(f"Sincronizando projeto {project.id} ({project.name})")

                # Buscar account
                account = await db.get(Account, project.account_id)
                if not account:
                    logger.warning(f"Account {project.account_id} não encontrada para projeto {project.id}")
                    error_count += 1
                    continue

                # Obter token e sincronizar
                token = await get_github_token(db, account)
                count = await sync_github_project(db, account, project, token)

                logger.info(f"Projeto {project.id} sincronizado: {count} itens")
                synced_count += 1

            except Exception as e:
                logger.error(f"Erro ao sincronizar projeto {project.id}: {e}", exc_info=True)
                error_count += 1

        logger.info(
            f"Sincronização automática concluída: {synced_count} projetos sincronizados, "
            f"{error_count} erros"
        )


def start_scheduler():
    """
    Inicia o scheduler de jobs periódicos.

    Configuração padrão:
    - Sync de projetos: a cada 15 minutos
    """
    global scheduler

    if scheduler is not None:
        logger.warning("Scheduler já está rodando")
        return

    logger.info("Iniciando scheduler de jobs periódicos")

    scheduler = AsyncIOScheduler()

    # Job: Sincronização de projetos (a cada 15 minutos)
    scheduler.add_job(
        sync_all_projects,
        trigger=CronTrigger(minute="*/15"),  # A cada 15 minutos
        id="sync_all_projects",
        name="Sincronização automática de projetos GitHub",
        replace_existing=True,
        misfire_grace_time=300,  # 5 minutos de tolerância
    )

    scheduler.start()
    logger.info("Scheduler iniciado com sucesso")
    logger.info(f"Jobs agendados: {[job.id for job in scheduler.get_jobs()]}")


def stop_scheduler():
    """Para o scheduler de jobs."""
    global scheduler

    if scheduler is None:
        logger.warning("Scheduler não está rodando")
        return

    logger.info("Parando scheduler")
    scheduler.shutdown(wait=True)
    scheduler = None
    logger.info("Scheduler parado com sucesso")


def get_scheduler_status() -> dict:
    """
    Retorna status do scheduler e jobs agendados.

    Returns:
        dict: {
            "running": bool,
            "jobs": [{
                "id": str,
                "name": str,
                "next_run_time": str | None,
                "trigger": str
            }]
        }
    """
    if scheduler is None:
        return {"running": False, "jobs": []}

    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger),
        })

    return {
        "running": scheduler.running,
        "jobs": jobs,
    }
