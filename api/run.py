"""Bootstraps the Tactyo backend when using a local virtualenv.

The script performs three steps:
1. Checks whether core dependencies are importable (helpful to catch missing installs early).
2. Executes Alembic migrations so the database schema is aligned with the codebase.
3. Starts the FastAPI application through uvicorn with auto-reload enabled.
"""

from __future__ import annotations

import importlib
import logging
import pathlib
import sys
from typing import Iterable

from alembic import command
from alembic.config import Config

BASE_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent

REQUIRED_PACKAGES: Iterable[str] = (
    "fastapi",
    "uvicorn",
    "sqlalchemy",
    "asyncpg",
    "alembic",
    "pydantic",
    "pydantic_settings",
)

logger = logging.getLogger("tactyo.run")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def verify_dependencies() -> None:
    """Ensure all required packages are importable within the current environment."""

    missing: list[str] = []
    for package in REQUIRED_PACKAGES:
        module_name = package.replace("-", "_").split("[", 1)[0]
        try:
            importlib.import_module(module_name)
        except ModuleNotFoundError:
            missing.append(package)

    if missing:
        requirement_hint = "pip install -r api/requirements-dev.txt"
        raise RuntimeError(
            "Dependências ausentes: "
            + ", ".join(missing)
            + f". Execute `{requirement_hint}` no seu venv antes de continuar."
        )

    logger.info("Todas as dependências requeridas foram encontradas.")


def run_migrations() -> None:
    """Apply Alembic migrations up to head."""

    alembic_ini = REPO_ROOT / "api" / "alembic.ini"
    if not alembic_ini.exists():
        raise FileNotFoundError(f"Arquivo Alembic não encontrado: {alembic_ini}")

    config = Config(str(alembic_ini))
    config.set_main_option("script_location", str(REPO_ROOT / "api" / "alembic"))
    config.set_main_option("sqlalchemy.url", str(_database_url()))

    logger.info("Aplicando migrações Alembic...")
    command.upgrade(config, "head")
    logger.info("Migrações aplicadas com sucesso.")


def _load_settings():
    try:
        from app.core.config import settings  # noqa: WPS433 (lazy import to delay validation)
    except Exception as exc:  # pragma: no cover - configuration issues handled at runtime
        raise RuntimeError(
            "Falha ao carregar configurações. Verifique variáveis de ambiente obrigatórias, "
            "como TACTYO_SESSION_SECRET (mínimo 16 caracteres) e TACTYO_DATABASE_URL."
        ) from exc
    return settings


def _database_url() -> str:
    settings = _load_settings()
    return str(settings.database_url)


def start_server() -> None:
    """Run uvicorn pointing at main:app with reload enabled."""

    import uvicorn

    logger.info("Inicializando servidor uvicorn em http://0.0.0.0:8000")
    uvicorn.run(
        "main:app",
        app_dir=str(BASE_DIR),
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_delay=0.25,
        reload_dirs=[str(BASE_DIR)],
    )


def main() -> None:
    verify_dependencies()
    run_migrations()
    start_server()


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as exc:
        logger.error(str(exc))
        sys.exit(1)
