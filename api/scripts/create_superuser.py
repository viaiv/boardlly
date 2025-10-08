#!/usr/bin/env python3
"""
Script para criar ou promover superusuário (owner) no Tactyo.

Uso:
    python scripts/create_superuser.py

    ou (dentro do venv):

    ./scripts/create_superuser.py
"""

import asyncio
import sys
from pathlib import Path

# Adiciona o diretório raiz ao path para importar módulos da app
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.user import AppUser
from app.models.account import Account
from app.core.security import hash_password
from app.core.config import settings


async def main():
    print("=" * 60)
    print("TACTYO - Criar/Promover Superusuário (Owner)")
    print("=" * 60)
    print()

    async with SessionLocal() as db:
        # Contar usuários existentes
        stmt = select(AppUser)
        result = await db.execute(stmt)
        users = result.scalars().all()

        print(f"📊 Total de usuários no sistema: {len(users)}")
        print()

        if users:
            print("Escolha uma opção:")
            print("  [1] Criar novo superusuário")
            print("  [2] Promover usuário existente a owner")
            print()
            choice = input("Opção: ").strip()

            if choice == "2":
                await promote_existing_user(db, users)
            elif choice == "1":
                await create_new_superuser(db)
            else:
                print("❌ Opção inválida")
                return
        else:
            print("ℹ️  Nenhum usuário no sistema. Criando primeiro superusuário...")
            print()
            await create_new_superuser(db)


async def create_new_superuser(db):
    """Cria um novo superusuário."""
    print("--- Criar Novo Superusuário ---")
    print()

    email = input("Email: ").strip().lower()
    if not email:
        print("❌ Email é obrigatório")
        return

    # Verificar se email já existe
    stmt = select(AppUser).where(AppUser.email == email)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        print(f"❌ Já existe um usuário com o email {email}")
        return

    password = input("Senha (mín. 8 caracteres): ").strip()
    if len(password) < 8:
        print("❌ Senha deve ter no mínimo 8 caracteres")
        return

    name = input("Nome (opcional): ").strip() or None

    # Criar conta para o owner
    account_name = input("Nome da conta/empresa (opcional): ").strip() or f"Conta de {email}"

    account = Account(name=account_name)
    db.add(account)
    await db.flush()

    # Criar usuário owner
    user = AppUser(
        account_id=account.id,
        email=email,
        password_hash=hash_password(password),
        name=name,
        role="owner",
        email_verified=True,  # Superusuário é verificado automaticamente
        email_verification_token=None,
        email_verification_token_expires=None,
    )
    db.add(user)
    await db.flush()

    # Definir owner da conta
    account.owner_user_id = user.id

    await db.commit()

    print()
    print("✅ Superusuário criado com sucesso!")
    print(f"   Email: {email}")
    print(f"   Role: owner")
    print(f"   Conta: {account_name}")
    print(f"   Email Verificado: Sim")


async def promote_existing_user(db, users):
    """Promove um usuário existente a owner."""
    print("--- Promover Usuário Existente ---")
    print()
    print("Usuários disponíveis:")
    print()

    for i, user in enumerate(users, 1):
        verified = "✓" if user.email_verified else "✗"
        print(f"  [{i}] {user.email:40} | Role: {user.role:10} | Verificado: {verified}")

    print()
    choice = input("Número do usuário para promover a owner: ").strip()

    try:
        index = int(choice) - 1
        if index < 0 or index >= len(users):
            print("❌ Número inválido")
            return
    except ValueError:
        print("❌ Entrada inválida")
        return

    user = users[index]

    if user.role == "owner":
        print(f"⚠️  {user.email} já é owner")
        return

    print()
    print(f"Você está prestes a promover {user.email} para owner (superusuário).")
    confirm = input("Confirmar? (s/N): ").strip().lower()

    if confirm != "s":
        print("❌ Operação cancelada")
        return

    # Promover a owner
    user.role = "owner"

    # Verificar email automaticamente se ainda não verificado
    if not user.email_verified:
        user.email_verified = True
        user.email_verification_token = None
        user.email_verification_token_expires = None
        print("   ℹ️  Email verificado automaticamente")

    # Se o usuário não tem conta, criar uma
    if not user.account_id:
        account_name = input("Nome da conta/empresa para este owner: ").strip() or f"Conta de {user.email}"
        account = Account(name=account_name, owner_user_id=user.id)
        db.add(account)
        await db.flush()
        user.account_id = account.id
        print(f"   ℹ️  Conta '{account_name}' criada")

    await db.commit()

    print()
    print(f"✅ {user.email} promovido a owner com sucesso!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n❌ Operação cancelada pelo usuário")
        sys.exit(1)
