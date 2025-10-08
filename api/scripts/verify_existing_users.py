#!/usr/bin/env python3
"""
Script para marcar todos os usuários existentes como verificados.

Útil após aplicar a migration de email_verification quando já existem
usuários no sistema que foram criados antes da verificação de email.

Uso:
    python scripts/verify_existing_users.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, update
from app.db.session import SessionLocal
from app.models.user import AppUser


async def main():
    print("=" * 60)
    print("TACTYO - Verificar Usuários Existentes")
    print("=" * 60)
    print()

    async with SessionLocal() as db:
        # Buscar usuários não verificados
        stmt = select(AppUser).where(AppUser.email_verified == False)
        result = await db.execute(stmt)
        unverified_users = result.scalars().all()

        if not unverified_users:
            print("✅ Todos os usuários já estão verificados!")
            return

        print(f"📊 Encontrados {len(unverified_users)} usuários não verificados:")
        print()

        for user in unverified_users:
            print(f"  • {user.email:40} | Role: {user.role}")

        print()
        print(f"⚠️  Esta ação irá marcar todos esses {len(unverified_users)} usuários como verificados.")
        confirm = input("Confirmar? (s/N): ").strip().lower()

        if confirm != "s":
            print("❌ Operação cancelada")
            return

        # Marcar todos como verificados
        stmt = (
            update(AppUser)
            .where(AppUser.email_verified == False)
            .values(
                email_verified=True,
                email_verification_token=None,
                email_verification_token_expires=None,
            )
        )
        result = await db.execute(stmt)
        await db.commit()

        print()
        print(f"✅ {result.rowcount} usuários marcados como verificados!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n❌ Operação cancelada pelo usuário")
        sys.exit(1)
