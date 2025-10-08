#!/usr/bin/env python3
"""
Script para gerar secrets seguros para o Tactyo.
Use antes de fazer deploy em produção.
"""

import secrets
from cryptography.fernet import Fernet


def generate_session_secret() -> str:
    """Gera um secret seguro para sessões."""
    return secrets.token_urlsafe(32)


def generate_encryption_key() -> str:
    """Gera uma chave de encriptação base64 (32 bytes)."""
    return Fernet.generate_key().decode()


def main():
    print("=" * 60)
    print("TACTYO - Gerador de Secrets")
    print("=" * 60)
    print()

    session_secret = generate_session_secret()
    encryption_key = generate_encryption_key()

    print("📝 Copie estas variáveis para seu .env ou EasyPanel:\n")

    print("# Session Secret (para cookies e sessões)")
    print(f"TACTYO_SESSION_SECRET={session_secret}")
    print()

    print("# Encryption Key (para dados sensíveis no banco)")
    print(f"TACTYO_ENCRYPTION_KEY={encryption_key}")
    print()

    print("=" * 60)
    print("⚠️  IMPORTANTE:")
    print("- Guarde estas secrets em local seguro")
    print("- NÃO commite no Git")
    print("- Use secrets diferentes para dev/staging/prod")
    print("=" * 60)


if __name__ == "__main__":
    main()
