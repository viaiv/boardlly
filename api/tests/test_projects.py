from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.account import Account

from app.models.github_project import GithubProject
from app.models.project_item import ProjectItem
from app.models.github_project_field import GithubProjectField
from app.models.user import AppUser


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
    assert "epic_name" in items[0]


@pytest.mark.anyio
async def test_update_project_item_status_syncs_to_github(client: AsyncClient, session_factory, monkeypatch):
    await client.post(
        "/api/auth/register",
        json={"email": "owner@example.com", "password": "supersecret", "name": "Owner"},
    )

    await client.post(
        "/api/accounts",
        json={"name": "Equipe Tactyo"},
    )

    async with session_factory() as session:  # type: AsyncSession
        user = (await session.execute(select(AppUser))).scalar_one()
        account_id = await _get_account_id(session)
        user.role = "owner"
        user.account_id = account_id
        project = GithubProject(
            account_id=account_id,
            owner_login="viaiv",
            project_number=1,
            project_node_id="PVT_TEST",
            name="Test",
            field_mappings={
                "Status": {
                    "id": "status-field",
                    "options": [
                        {"id": "opt-backlog", "name": "Backlog"},
                        {"id": "opt-done", "name": "Done"},
                    ],
                }
            },
            status_columns=["Backlog", "Done"],
        )
        session.add(project)
        await session.flush()

        session.add(
            GithubProjectField(
                project_id=project.id,
                field_id="status-field",
                field_name="Status",
                field_type="SINGLE_SELECT",
                options=[
                    {"id": "opt-backlog", "name": "Backlog"},
                    {"id": "opt-done", "name": "Done"},
                ],
            )
        )

        item = ProjectItem(
            account_id=account_id,
            project_id=project.id,
            item_node_id="ITEM_NODE",
            content_type="Issue",
            title="Sample Item",
            status="Backlog",
        )
        session.add(item)
        await session.commit()
        item_id = item.id

    async def fake_get_token(db: AsyncSession, account: Account) -> str:  # type: ignore[override]
        return "ghs_fake"

    client_calls: list[object] = []

    class FakeClient:
        def __init__(self, token: str):
            self.token = token
            self.calls: list[dict[str, object]] = []
            client_calls.append(self)

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def execute(self, query: str, variables: dict[str, object]):
            self.calls.append({"query": query.strip(), "variables": variables})
            if "updateProjectV2ItemFieldValue" in query:
                return {"updateProjectV2ItemFieldValue": {"projectV2Item": {"id": variables["input"]["itemId"]}}}
            if "clearProjectV2ItemFieldValue" in query:
                return {"clearProjectV2ItemFieldValue": {"projectV2Item": {"id": variables["input"]["itemId"]}}}
            return {}

    monkeypatch.setattr("app.services.github.get_github_token", fake_get_token)
    monkeypatch.setattr("app.services.github.GithubGraphQLClient", FakeClient)

    response = await client.patch(
        f"/api/projects/current/items/{item_id}",
        json={"status": "Done"},
    )
    assert response.status_code == 200
    assert client_calls
    update_client = client_calls[0]
    update_call = update_client.calls[-1]
    assert update_call["variables"]["input"]["value"]["singleSelectOptionId"] == "opt-done"

    async with session_factory() as session:
        refreshed_item = await session.get(ProjectItem, item_id)
        assert refreshed_item is not None
        assert refreshed_item.status == "Done"

    response_clear = await client.patch(
        f"/api/projects/current/items/{item_id}",
        json={"status": None},
    )
    assert response_clear.status_code == 200
    clear_call = client_calls[-1].calls[-1]
    assert "clearProjectV2ItemFieldValue" in clear_call["query"]

    async with session_factory() as session:
        refreshed_item = await session.get(ProjectItem, item_id)
        assert refreshed_item is not None
        assert refreshed_item.status is None


@pytest.mark.anyio
async def test_list_project_item_comments(client: AsyncClient, session_factory, monkeypatch):
    await client.post(
        "/api/auth/register",
        json={"email": "owner@example.com", "password": "supersecret", "name": "Owner"},
    )

    await client.post(
        "/api/accounts",
        json={"name": "Equipe Tactyo"},
    )

    async with session_factory() as session:
        user = (await session.execute(select(AppUser))).scalar_one()
        account_id = await _get_account_id(session)
        user.role = "owner"
        user.account_id = account_id

        project = GithubProject(
            account_id=account_id,
            owner_login="viaiv",
            project_number=1,
            project_node_id="PVT_TEST",
            name="Test",
        )
        session.add(project)
        await session.flush()

        item = ProjectItem(
            account_id=account_id,
            project_id=project.id,
            item_node_id="ITEM_NODE",
            content_node_id="CONTENT_NODE",
            content_type="Issue",
            title="Sample Item",
        )
        session.add(item)
        await session.commit()
        item_id = item.id

    async def fake_get_token(db: AsyncSession, account: Account) -> str:  # type: ignore[override]
        return "gh_fake"

    async def fake_fetch_comments(client_obj, content_node_id: str, limit: int = 30):
        assert content_node_id == "CONTENT_NODE"
        return [
            {
                "id": "COMMENT-1",
                "body": "Primeiro comentário",
                "author_login": "alice",
                "author_url": "https://github.com/alice",
                "author_avatar_url": "https://avatars.githubusercontent.com/u/1?v=4",
                "created_at": datetime(2025, 1, 10, 12, 0, tzinfo=timezone.utc).isoformat(),
                "updated_at": None,
                "url": "https://github.com/org/repo/issues/1#issuecomment-1",
            }
        ]

    class DummyClient:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            return False

    monkeypatch.setattr("app.services.github.get_github_token", fake_get_token)
    monkeypatch.setattr("app.services.github.fetch_project_item_comments", fake_fetch_comments)
    monkeypatch.setattr("app.services.github.GithubGraphQLClient", DummyClient)

    response = await client.get(f"/api/projects/current/items/{item_id}/comments")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["author"] == "alice"
    assert payload[0]["body"] == "Primeiro comentário"
    assert payload[0]["url"].endswith("issuecomment-1")


@pytest.mark.anyio
async def test_get_project_item_details(client: AsyncClient, session_factory, monkeypatch):
    await client.post(
        "/api/auth/register",
        json={"email": "owner@example.com", "password": "supersecret", "name": "Owner"},
    )

    await client.post(
        "/api/accounts",
        json={"name": "Equipe Tactyo"},
    )

    async with session_factory() as session:
        user = (await session.execute(select(AppUser))).scalar_one()
        account_id = await _get_account_id(session)
        user.role = "owner"
        user.account_id = account_id

        project = GithubProject(
            account_id=account_id,
            owner_login="viaiv",
            project_number=1,
            project_node_id="PVT_TEST",
            name="Test",
        )
        session.add(project)
        await session.flush()

        item = ProjectItem(
            account_id=account_id,
            project_id=project.id,
            item_node_id="ITEM_NODE",
            content_node_id="CONTENT_NODE",
            content_type="Issue",
            title="Sample Item",
        )
        session.add(item)
        await session.commit()
        item_id = item.id

    async def fake_get_token(db: AsyncSession, account: Account) -> str:  # type: ignore[override]
        return "gh_fake"

    async def fake_fetch_details(client_obj, content_node_id: str):
        assert content_node_id == "CONTENT_NODE"
        return {
            "id": "ISSUE_NODE",
            "content_type": "Issue",
            "number": 42,
            "title": "Detalhes",
            "body": "Descrição *markdown*",
            "body_text": "Descrição markdown",
            "state": "OPEN",
            "merged": None,
            "url": "https://github.com/org/repo/issues/42",
            "created_at": datetime(2025, 1, 1, tzinfo=timezone.utc).isoformat(),
            "updated_at": datetime(2025, 1, 2, tzinfo=timezone.utc).isoformat(),
            "author_login": "alice",
            "author_url": "https://github.com/alice",
            "author_avatar_url": "https://avatars.githubusercontent.com/u/1?v=4",
            "labels": [
                {"name": "bug", "color": "ff0000"},
                {"name": "backend", "color": "123456"},
            ],
        }

    class DummyClient:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            return False

    monkeypatch.setattr("app.services.github.get_github_token", fake_get_token)
    monkeypatch.setattr("app.services.github.fetch_project_item_details", fake_fetch_details)
    monkeypatch.setattr("app.services.github.GithubGraphQLClient", DummyClient)

    response = await client.get(f"/api/projects/current/items/{item_id}/details")
    assert response.status_code == 200
    payload = response.json()
    assert payload["number"] == 42
    assert payload["author"]["login"] == "alice"
    assert payload["labels"][0]["name"] == "bug"
    assert payload["labels"][0]["color"] == "ff0000"

async def _get_account_id(session: AsyncSession):
    result = await session.execute(select(Account.id).limit(1))
    row = result.fetchone()
    assert row is not None
    return row[0]
