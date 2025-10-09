#!/usr/bin/env python3
"""
Script de debug para investigar o problema de projetos.

Uso:
    cd api
    python scripts/debug_projects.py [email@usuario.com]

Se não fornecer email, lista todos os usuários e seus projetos.
"""

import asyncio
import sys
from pathlib import Path

# Ajustar PYTHONPATH para incluir o diretório api
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.github_project import GithubProject
from app.models.user import AppUser
from app.models.account import Account


async def debug_user_projects(email: str | None = None):
    """Debug projetos de um usuário específico ou de todos."""
    async with SessionLocal() as db:
        if email:
            # Buscar usuário específico
            stmt = select(AppUser).where(AppUser.email == email)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                print(f"❌ Usuário com email '{email}' não encontrado")
                return

            users = [user]
        else:
            # Listar todos os usuários
            stmt = select(AppUser)
            result = await db.execute(stmt)
            users = list(result.scalars().all())
            print(f"📋 Total de usuários no banco: {len(users)}\n")

        for user in users:
            print(f"👤 Usuário: {user.email}")
            print(f"   Nome: {user.name}")
            print(f"   ID: {user.id}")
            print(f"   Role: {user.role}")
            print(f"   Account ID: {user.account_id}")

            if not user.account_id:
                print("   ⚠️  Usuário sem conta configurada\n")
                continue

            # Buscar conta
            account = await db.get(Account, user.account_id)
            if account:
                print(f"   🏢 Conta: {account.name} (ID: {account.id})")
            else:
                print(f"   ❌ Conta {user.account_id} não encontrada!\n")
                continue

            # Buscar projetos da conta
            stmt = select(GithubProject).where(GithubProject.account_id == user.account_id)
            result = await db.execute(stmt)
            projects = list(result.scalars().all())
            print(f"   📁 Projetos: {len(projects)}")

            if projects:
                for i, proj in enumerate(projects, 1):
                    print(f"      {i}. ID: {proj.id}")
                    print(f"         Nome: {proj.name or '(sem nome)'}")
                    print(f"         Owner: {proj.owner_login}")
                    print(f"         Number: {proj.project_number}")
                    print(f"         Node ID: {proj.project_node_id}")
                    print(f"         Status Columns: {proj.status_columns}")
                    print(f"         Last Sync: {proj.last_synced_at}")
            else:
                print("      ⚠️  Nenhum projeto encontrado para esta conta")

            print()


async def check_orphan_localstorage():
    """Mostra sugestões de IDs que podem estar órfãos no localStorage."""
    async with SessionLocal() as db:
        stmt = select(GithubProject)
        result = await db.execute(stmt)
        projects = list(result.scalars().all())

        all_project_ids = [p.id for p in projects]
        print("🔍 IDs de projetos válidos no banco:")
        if all_project_ids:
            for pid in all_project_ids:
                print(f"   - {pid}")
        else:
            print("   (nenhum)")

        print("\n💡 Se seu localStorage tem um ID diferente destes, ele está órfão!")


async def main():
    email_arg = sys.argv[1] if len(sys.argv) > 1 else None

    print("=" * 60)
    print("🔍 DEBUG: Projetos por Usuário")
    print("=" * 60)
    print()

    await debug_user_projects(email_arg)

    print("=" * 60)
    await check_orphan_localstorage()
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
