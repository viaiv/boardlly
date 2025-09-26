import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.account import Account

from app.models.github_project import GithubProject
from app.models.project_item import ProjectItem


@pytest.mark.anyio
async def test_get_current_project_without_configuration_returns_404(client: AsyncClient):
    await client.post(
        "/api/auth/register",
        json={"email": "owner@example.com", "password": "supersecret", "name": "Owner"},
    )

    response = await client.get("/api/projects/current")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_get_current_project_and_items(client: AsyncClient, session_factory):
    await client.post(
        "/api/auth/register",
        json={"email": "owner@example.com", "password": "supersecret", "name": "Owner"},
    )

    await client.post(
        "/api/accounts",
        json={"name": "Equipe Tactyo"},
    )

    async with session_factory() as session:  # type: AsyncSession
        account_id = await _get_account_id(session)
        project = GithubProject(
            account_id=account_id,
            owner_login="viaiv",
            project_number=1,
            project_node_id="PVT_TEST",
            name="Test Project",
        )
        session.add(project)
        await session.flush()
        item = ProjectItem(
            account_id=account_id,
            project_id=project.id,
            item_node_id="ITEM_TEST",
            content_type="Issue",
            title="Sample Item",
            status="Backlog",
            assignees=["alice"],
        )
        session.add(item)
        await session.commit()

    project_response = await client.get("/api/projects/current")
    assert project_response.status_code == 200
    assert project_response.json()["name"] == "Test Project"

    items_response = await client.get("/api/projects/current/items")
    assert items_response.status_code == 200
    items = items_response.json()
    assert len(items) == 1
    assert items[0]["title"] == "Sample Item"
    assert items[0]["assignees"] == ["alice"]


async def _get_account_id(session: AsyncSession):
    result = await session.execute(select(Account.id).limit(1))
    row = result.fetchone()
    assert row is not None
    return row[0]
