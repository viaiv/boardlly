#!/usr/bin/env python3
"""
Script para testar a implementação de hierarquia épico > história > tarefa.

Uso:
    python test_hierarchy.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.project_item import ProjectItem
from app.models.github_project import GithubProject
from app.models.epic_option import EpicOption
from app.utils.hierarchy import derive_item_type_from_labels, is_story, is_task


async def test_derive_item_type():
    """Testa a função de derivação de tipo a partir de labels."""
    print("=" * 60)
    print("TESTE 1: Derivação de item_type a partir de labels")
    print("=" * 60)
    print()

    test_cases = [
        (["type:story", "priority:high"], None, "story"),
        (["type:task"], None, "task"),
        (["type:feature"], None, "feature"),
        (["type:bug"], None, "bug"),
        (["priority:high"], "HISTORY: User login", "story"),
        (["priority:low"], "Regular task", None),
        (None, None, None),
    ]

    for labels, title, expected in test_cases:
        result = derive_item_type_from_labels(labels, title)
        status = "✅" if result == expected else "❌"
        print(f"{status} Labels: {labels}, Title: {title!r}")
        print(f"   Esperado: {expected}, Resultado: {result}")
        print()


async def test_database_structure():
    """Testa a estrutura do banco de dados."""
    print("=" * 60)
    print("TESTE 2: Estrutura do Banco de Dados")
    print("=" * 60)
    print()

    async with SessionLocal() as db:
        # Verificar se as tabelas existem
        try:
            # Testar ProjectItem com novos campos
            stmt = select(ProjectItem).limit(1)
            result = await db.execute(stmt)
            item = result.scalar_one_or_none()

            if item:
                print("✅ Tabela ProjectItem existe e tem dados")
                print(f"   Campos hierárquicos:")
                print(f"   - item_type: {item.item_type}")
                print(f"   - parent_item_id: {item.parent_item_id}")
                print(f"   - labels: {item.labels}")
            else:
                print("⚠️  Tabela ProjectItem existe mas está vazia")

            print()

            # Testar EpicOption
            stmt = select(EpicOption).limit(1)
            result = await db.execute(stmt)
            epic = result.scalar_one_or_none()

            if epic:
                print("✅ Tabela EpicOption existe e tem dados")
                print(f"   - option_name: {epic.option_name}")
                print(f"   - color: {epic.color}")
            else:
                print("⚠️  Tabela EpicOption existe mas está vazia")

            print()

        except Exception as e:
            print(f"❌ Erro ao acessar banco de dados: {e}")
            return


async def test_project_items_with_labels():
    """Lista items do projeto com labels e tipo derivado."""
    print("=" * 60)
    print("TESTE 3: Items com Labels e Tipo Derivado")
    print("=" * 60)
    print()

    async with SessionLocal() as db:
        stmt = select(ProjectItem).limit(10)
        result = await db.execute(stmt)
        items = result.scalars().all()

        if not items:
            print("⚠️  Nenhum item encontrado no banco")
            return

        print(f"📊 Encontrados {len(items)} items:")
        print()

        for item in items:
            print(f"• {item.title}")
            print(f"  Labels: {item.labels}")
            print(f"  Type: {item.item_type}")
            print(f"  Parent: {item.parent_item_id}")

            # Verificar se o tipo foi derivado corretamente
            expected_type = derive_item_type_from_labels(item.labels, item.title)
            if item.item_type != expected_type:
                print(f"  ⚠️  Tipo esperado: {expected_type}")

            print()


async def test_hierarchy_structure():
    """Testa a estrutura hierárquica dos items."""
    print("=" * 60)
    print("TESTE 4: Estrutura Hierárquica")
    print("=" * 60)
    print()

    async with SessionLocal() as db:
        # Contar items por tipo
        stmt = select(ProjectItem)
        result = await db.execute(stmt)
        all_items = result.scalars().all()

        if not all_items:
            print("⚠️  Nenhum item encontrado")
            return

        # Estatísticas
        by_type = {}
        root_items = []
        child_items = []

        for item in all_items:
            # Contar por tipo
            item_type = item.item_type or "undefined"
            by_type[item_type] = by_type.get(item_type, 0) + 1

            # Separar root vs child
            if item.parent_item_id is None:
                root_items.append(item)
            else:
                child_items.append(item)

        print("📊 Estatísticas:")
        print(f"   Total de items: {len(all_items)}")
        print(f"   Items raiz (sem pai): {len(root_items)}")
        print(f"   Items com pai: {len(child_items)}")
        print()

        print("📊 Items por tipo:")
        for item_type, count in sorted(by_type.items()):
            print(f"   {item_type}: {count}")
        print()

        # Mostrar algumas relações pai-filho
        if child_items:
            print("📊 Exemplos de relações pai-filho:")
            for child in child_items[:5]:
                parent = next((i for i in all_items if i.id == child.parent_item_id), None)
                if parent:
                    print(f"   • {parent.title} ({parent.item_type})")
                    print(f"     └─ {child.title} ({child.item_type})")
            print()


async def test_epics():
    """Lista épicos cadastrados."""
    print("=" * 60)
    print("TESTE 5: Épicos Cadastrados")
    print("=" * 60)
    print()

    async with SessionLocal() as db:
        stmt = select(EpicOption)
        result = await db.execute(stmt)
        epics = result.scalars().all()

        if not epics:
            print("⚠️  Nenhum épico cadastrado")
            print("💡 Use o endpoint POST /api/projects/{project_id}/epics para criar")
            return

        print(f"📊 Encontrados {len(epics)} épicos:")
        print()

        for epic in epics:
            print(f"• {epic.option_name}")
            print(f"  ID: {epic.id}")
            print(f"  Option ID (GitHub): {epic.option_id}")
            print(f"  Cor: {epic.color}")
            print(f"  Descrição: {epic.description}")
            print()


async def main():
    print("=" * 60)
    print("TACTYO - Testes de Hierarquia Épico > História > Tarefa")
    print("=" * 60)
    print()

    try:
        await test_derive_item_type()
        await test_database_structure()
        await test_project_items_with_labels()
        await test_hierarchy_structure()
        await test_epics()

        print("=" * 60)
        print("✅ Testes concluídos!")
        print("=" * 60)
        print()
        print("💡 Próximos passos:")
        print("   1. Acesse http://localhost:8000/docs para testar os endpoints")
        print("   2. Use POST /api/projects/{id}/epics para criar épicos")
        print("   3. Use GET /api/projects/{id}/hierarchy para ver a estrutura")

    except Exception as e:
        print(f"❌ Erro durante testes: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
