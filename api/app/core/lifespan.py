import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.session import engine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    try:
        async with engine.begin():
            logger.info("Database connection established")
    except Exception as exc:  # pragma: no cover - startup diagnostics
        logger.exception("Failed to connect to the database", exc_info=exc)
        raise

    try:
        yield
    finally:
        await engine.dispose()
        logger.info("Database connection closed")
