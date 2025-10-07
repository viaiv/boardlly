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
from app.services.github import EpicOptionData


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


@pytest.mark.anyio
async def test_dashboard_endpoints_return_summaries(client: AsyncClient, session_factory):
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
            project_number=9,
            project_node_id="PVT_DASH",
            name="Roadmap",
            status_columns=["Backlog", "In Review", "Done"],
        )
        session.add(project)
        await session.flush()

        session.add(
            GithubProjectField(
                project_id=project.id,
                field_id="iteration-field",
                field_name="Iteration",
                field_type="ITERATION",
                options={
                    "iterations": [
                        {
                            "id": "it-1",
                            "title": "Sprint Janeiro",
                            "startDate": datetime(2025, 1, 1, tzinfo=timezone.utc).isoformat(),
                            "duration": 14,
                        }
                    ]
                },
            )
        )

        session.add(
            GithubProjectField(
                project_id=project.id,
                field_id="epic-field",
                field_name="Epic",
                field_type="SINGLE_SELECT",
                options=[
                    {"id": "epic-1", "name": "Plataforma"},
                    {"id": "epic-2", "name": "Onboarding"},
                ],
            )
        )

        session.add_all(
            [
                ProjectItem(
                    account_id=account_id,
                    project_id=project.id,
                    item_node_id="ITEM-1",
                    content_type="Issue",
                    title="Planejar API",
                    status="Backlog",
                    iteration="Sprint Janeiro",
                    iteration_id="it-1",
                    iteration_start=datetime(2025, 1, 1, tzinfo=timezone.utc),
                    iteration_end=datetime(2025, 1, 14, tzinfo=timezone.utc),
                    estimate=3,
                    epic_option_id="epic-1",
                    epic_name="Plataforma",
                ),
                ProjectItem(
                    account_id=account_id,
                    project_id=project.id,
                    item_node_id="ITEM-2",
                    content_type="Issue",
                    title="Implementar fluxo",
                    status="Done",
                    iteration="Sprint Janeiro",
                    iteration_id="it-1",
                    iteration_start=datetime(2025, 1, 1, tzinfo=timezone.utc),
                    iteration_end=datetime(2025, 1, 14, tzinfo=timezone.utc),
                    estimate=5,
                    epic_option_id="epic-1",
                    epic_name="Plataforma",
                ),
                ProjectItem(
                    account_id=account_id,
                    project_id=project.id,
                    item_node_id="ITEM-3",
                    content_type="Issue",
                    title="Revisar onboarding",
                    status="In Review",
                    estimate=2,
                ),
            ]
        )

        await session.commit()

    iteration_response = await client.get("/api/projects/current/iterations/dashboard")
    assert iteration_response.status_code == 200
    iteration_data = iteration_response.json()

    option_ids = {option["id"] for option in iteration_data["options"]}
    assert "it-1" in option_ids

    iteration_summaries = {summary["iteration_id"]: summary for summary in iteration_data["summaries"]}
    assert iteration_summaries["it-1"]["item_count"] == 2
    assert iteration_summaries["it-1"]["completed_count"] == 1
    assert iteration_summaries["it-1"]["total_estimate"] == 8.0
    done_entry = next(
        entry for entry in iteration_summaries["it-1"]["status_breakdown"] if entry["status"] == "Done"
    )
    assert done_entry["count"] == 1

    unassigned_iteration = iteration_summaries[None]
    assert unassigned_iteration["item_count"] == 1

    epic_response = await client.get("/api/projects/current/epics/dashboard")
    assert epic_response.status_code == 200
    epic_data = epic_response.json()

    epic_option_ids = {option["id"] for option in epic_data["options"]}
    assert {"epic-1", "epic-2"}.issubset(epic_option_ids)

    epic_summaries = {summary["epic_option_id"]: summary for summary in epic_data["summaries"]}
    plataforma_summary = epic_summaries["epic-1"]
    assert plataforma_summary["item_count"] == 2
    assert plataforma_summary["completed_count"] == 1

    unassigned_epic = epic_summaries[None]
    assert unassigned_epic["item_count"] == 1
    assert any(entry["status"] == "In Review" for entry in unassigned_epic["status_breakdown"])


@pytest.mark.anyio
async def test_manage_epic_options_endpoints(client: AsyncClient, session_factory, monkeypatch):
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
            project_number=12,
            project_node_id="PVT_EPIC",
            name="Epics",
        )
        session.add(project)
        await session.flush()
        session.add(
            GithubProjectField(
                project_id=project.id,
                field_id="epic-field",
                field_name="Epic",
                field_type="SINGLE_SELECT",
                options=[
                    {"id": "epic-1", "name": "Origem"},
                ],
            )
        )
        await session.commit()

    created_calls: dict[str, tuple[str, str | None]] = {}

    async def fake_create(db, account, project, name, color):
        created_calls["args"] = (name, color)
        return EpicOptionData(id="epic-new", name=name, color=(color or "BLUE"))

    async def fake_update(db, account, project, option_id, name, color):
        return EpicOptionData(id=option_id, name=name or "Atualizado", color=(color or "GREEN"))

    async def fake_delete(db, account, project, option_id):
        created_calls["deleted"] = option_id

    async def fake_list(db, project):
        return [
            EpicOptionData(id="epic-1", name="Origem", color="BLUE"),
            EpicOptionData(id="epic-new", name="Discovery", color="BLUE"),
        ]

    monkeypatch.setattr("app.services.github.create_epic_option", fake_create)
    monkeypatch.setattr("app.services.github.update_epic_option", fake_update)
    monkeypatch.setattr("app.services.github.delete_epic_option", fake_delete)
    monkeypatch.setattr("app.services.github.list_epic_options", fake_list)

    create_response = await client.post(
        "/api/projects/current/epics/options",
        json={"name": "Discovery", "color": "blue"},
    )
    assert create_response.status_code == 201
    assert created_calls["args"] == ("Discovery", "blue")
    payload = create_response.json()
    assert payload["name"] == "Discovery"
    assert payload["color"] == "BLUE"

    update_response = await client.patch(
        "/api/projects/current/epics/options/epic-new",
        json={"name": "Delivery", "color": "green"},
    )
    assert update_response.status_code == 200
    update_payload = update_response.json()
    assert update_payload["id"] == "epic-new"
    assert update_payload["name"] == "Delivery"
    assert update_payload["color"] == "GREEN"

    list_response = await client.get("/api/projects/current/epics/options")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 2

    delete_response = await client.delete("/api/projects/current/epics/options/epic-new")
    assert delete_response.status_code == 204
    assert created_calls["deleted"] == "epic-new"


async def _get_account_id(session: AsyncSession):
    result = await session.execute(select(Account.id).limit(1))
    row = result.fetchone()
    assert row is not None
    return row[0]
