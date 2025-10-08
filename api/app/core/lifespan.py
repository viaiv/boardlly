import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.session import engine
from app.services.scheduler import start_scheduler, stop_scheduler

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # Startup
    try:
        async with engine.begin():
            logger.info("Database connection established")
    except Exception as exc:  # pragma: no cover - startup diagnostics
        logger.exception("Failed to connect to the database", exc_info=exc)
        raise

    # Iniciar scheduler de jobs periódicos
    try:
        start_scheduler()
        logger.info("Scheduler started successfully")
    except Exception as exc:
        logger.exception("Failed to start scheduler", exc_info=exc)
        # Não bloquear startup se scheduler falhar

    try:
        yield
    finally:
        # Shutdown
        # Parar scheduler
        try:
            stop_scheduler()
            logger.info("Scheduler stopped")
        except Exception as exc:
            logger.exception("Failed to stop scheduler", exc_info=exc)

        # Fechar conexão com banco
        await engine.dispose()
        logger.info("Database connection closed")
