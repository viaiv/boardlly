"""Ferramenta para preparar e iniciar a API localmente.

O script executa três etapas principais:
1. Verifica se as dependências núcleo estão disponíveis no ambiente virtual.
2. Aplica as migrações Alembic necessárias para alinhar o banco de dados.
3. Inicia o servidor FastAPI via uvicorn com recarregamento automático.

Use as flags da CLI para pular etapas ou executá-las isoladamente.
"""

from __future__ import annotations

import argparse
import importlib
import logging
import pathlib
import sys
from typing import Iterable, Sequence

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


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Executa checagens, migrações e sobe o servidor da API.",
    )
    parser.add_argument(
        "--skip-checks",
        action="store_true",
        help="Não valida as dependências antes de continuar.",
    )
    parser.add_argument(
        "--skip-migrations",
        action="store_true",
        help="Não executa as migrações Alembic.",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Executa apenas as verificações de dependências e encerra.",
    )
    parser.add_argument(
        "--migrate-only",
        action="store_true",
        help="Executa verificações e migrações sem subir o servidor.",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host exposto pelo uvicorn (padrão: 0.0.0.0).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Porta exposta pelo uvicorn (padrão: 8000).",
    )
    parser.add_argument(
        "--no-reload",
        action="store_true",
        help="Desativa o recarregamento automático de código.",
    )

    args = parser.parse_args(argv)

    if args.check_only and args.migrate_only:
        parser.error("Use apenas uma das flags --check-only ou --migrate-only.")

    return args


def verify_dependencies(packages: Iterable[str] = REQUIRED_PACKAGES) -> None:
    """Garantir que os pacotes principais podem ser importados."""

    missing: list[str] = []
    for package in packages:
        module_name = package.replace("-", "_").split("[", 1)[0]
        try:
            importlib.import_module(module_name)
        except ModuleNotFoundError:
            missing.append(package)

    if missing:
        requirement_hint = "pip install -r api/requirements-dev.txt"
        raise RuntimeError(
            "Dependências ausentes: "
            + ", ".join(sorted(missing))
            + f". Execute `{requirement_hint}` no seu venv antes de continuar."
        )

    logger.info("Todas as dependências requeridas foram encontradas.")


def run_migrations() -> None:
    """Aplicar migrações alembic até a head."""

    alembic_ini = REPO_ROOT / "api" / "alembic.ini"
    if not alembic_ini.exists():
        raise FileNotFoundError(f"Arquivo Alembic não encontrado: {alembic_ini}")

    config = Config(str(alembic_ini))
    config.set_main_option("script_location", str(BASE_DIR / "alembic"))
    config.set_main_option("sqlalchemy.url", _database_url())

    logger.info("Aplicando migrações Alembic...")
    command.upgrade(config, "head")
    logger.info("Migrações aplicadas com sucesso.")


def _load_settings():
    try:
        from app.core.config import settings  # noqa: WPS433 (import tardio para validar no runtime)
    except Exception as exc:  # pragma: no cover - problemas de config tratados em tempo real
        raise RuntimeError(
            "Falha ao carregar configurações. Verifique variáveis de ambiente obrigatórias, "
            "como TACTYO_SESSION_SECRET (mínimo 16 caracteres) e TACTYO_DATABASE_URL."
        ) from exc
    return settings


def _database_url() -> str:
    settings = _load_settings()
    return str(settings.database_url)


def start_server(*, host: str, port: int, reload: bool) -> None:
    """Iniciar o uvicorn apontando para main:app."""

    import uvicorn

    logger.info("Inicializando servidor uvicorn em http://%s:%s", host, port)

    uvicorn_kwargs: dict[str, object] = {"reload": reload}
    if reload:
        uvicorn_kwargs.update(
            reload_delay=0.25,
            reload_dirs=[str(BASE_DIR / "app")],
        )

    uvicorn.run(
        "main:app",
        app_dir=str(BASE_DIR),
        host=host,
        port=port,
        **uvicorn_kwargs,
    )


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)

    if args.skip_checks:
        logger.info("Pulando verificação de dependências a pedido.")
    else:
        verify_dependencies()

    if args.check_only:
        logger.info("Verificações concluídas. Nada mais a fazer.")
        return

    if args.skip_migrations:
        logger.info("Pulando migrações Alembic a pedido.")
    else:
        run_migrations()

    if args.migrate_only:
        logger.info("Migrações concluídas. Encerrando conforme solicitado.")
        return

    start_server(host=args.host, port=args.port, reload=not args.no_reload)


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as exc:
        logger.error(str(exc))
        sys.exit(1)
    except KeyboardInterrupt:  # pragma: no cover - interação manual
        logger.info("Execução interrompida pelo usuário.")
        sys.exit(130)
