#!/usr/bin/env python3
"""
Script de teste E2E para Change Requests.

Fluxo testado:
1. Login como usuário PM/Admin
2. Criar uma Change Request
3. Aprovar a Change Request (criando Issue no GitHub)
4. Verificar Issue no GitHub
"""

import requests
import json
import sys
from datetime import datetime

BASE_URL = "http://localhost:8000"
session = requests.Session()

def login(email: str, password: str) -> bool:
    """Faz login e mantém sessão"""
    print(f"🔐 Login como {email}...")
    resp = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": email,
        "password": password
    })

    if resp.status_code == 200:
        user = resp.json()
        print(f"✅ Login bem-sucedido: {user['name']} (role: {user['role']})")
        return True
    else:
        print(f"❌ Erro no login: {resp.status_code} - {resp.text}")
        return False

def create_request() -> str | None:
    """Cria uma Change Request de teste"""
    print("\n📝 Criando Change Request...")

    timestamp = datetime.now().strftime("%H:%M:%S")
    payload = {
        "title": f"[TESTE E2E] Request criada via script - {timestamp}",
        "description": "Esta é uma solicitação de teste criada automaticamente.\n\nObjetivo: validar fluxo completo de aprovação e criação de Issue.",
        "impact": "Validar integração entre frontend, backend e GitHub API.",
        "priority": "high",
        "request_type": "feature"
    }

    resp = session.post(f"{BASE_URL}/api/requests", json=payload)

    if resp.status_code == 201:
        request_data = resp.json()
        request_id = request_data["id"]
        print(f"✅ Request criada: {request_id}")
        print(f"   Título: {request_data['title']}")
        print(f"   Status: {request_data['status']}")
        return request_id
    else:
        print(f"❌ Erro ao criar request: {resp.status_code} - {resp.text}")
        return None

def approve_request(request_id: str) -> dict | None:
    """Aprova a Change Request e cria Issue no GitHub"""
    print(f"\n✅ Aprovando Request {request_id}...")

    payload = {
        "create_issue": True,
        "add_to_project": True
    }

    resp = session.post(f"{BASE_URL}/api/requests/{request_id}/approve", json=payload)

    if resp.status_code == 200:
        request_data = resp.json()
        print(f"✅ Request aprovada!")
        print(f"   Status: {request_data['status']}")

        if request_data.get("github_issue_number"):
            print(f"   Issue GitHub: #{request_data['github_issue_number']}")
            print(f"   URL: {request_data['github_issue_url']}")

        return request_data
    else:
        print(f"❌ Erro ao aprovar: {resp.status_code}")
        print(f"   Response: {resp.text}")
        return None

def verify_request(request_id: str):
    """Verifica detalhes da Request"""
    print(f"\n🔍 Verificando Request {request_id}...")

    resp = session.get(f"{BASE_URL}/api/requests/{request_id}")

    if resp.status_code == 200:
        data = resp.json()
        print(f"✅ Request encontrada:")
        print(f"   Título: {data['title']}")
        print(f"   Status: {data['status']}")
        print(f"   Prioridade: {data['priority']}")
        print(f"   Criada por: {data['creator_name']}")
        print(f"   Revisada por: {data.get('reviewer_name', 'N/A')}")

        if data.get('github_issue_url'):
            print(f"   ✅ Issue GitHub: {data['github_issue_url']}")
        else:
            print(f"   ⚠️  Nenhuma Issue criada")

        return data
    else:
        print(f"❌ Erro ao verificar: {resp.status_code}")
        return None

def main():
    print("=" * 60)
    print("TESTE E2E: Change Request Workflow")
    print("=" * 60)

    # Credenciais (ajustar conforme necessário)
    # Você pode passar como argumentos ou criar variável de ambiente
    email = input("Email do usuário PM/Admin: ").strip() or "admin@example.com"
    password = input("Senha: ").strip() or "password123"

    # 1. Login
    if not login(email, password):
        sys.exit(1)

    # 2. Criar Request
    request_id = create_request()
    if not request_id:
        sys.exit(1)

    # 3. Aprovar Request
    approved_data = approve_request(request_id)
    if not approved_data:
        sys.exit(1)

    # 4. Verificar Request
    verify_request(request_id)

    print("\n" + "=" * 60)
    print("✅ TESTE E2E CONCLUÍDO COM SUCESSO!")
    print("=" * 60)

    if approved_data.get("github_issue_url"):
        print(f"\n🔗 Abra no navegador: {approved_data['github_issue_url']}")

    print(f"\n🔗 Veja detalhes no frontend: http://localhost:5173/requests/{request_id}")

if __name__ == "__main__":
    main()
