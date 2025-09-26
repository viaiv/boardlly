import base64
import os
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.project_item import ProjectItem
from app.services.github import ProjectItemPayload, ProjectMetadata, ProjectSummary

os.environ.setdefault("TACTYO_SESSION_SECRET", "test-secret-value-123456")
os.environ.setdefault(
    "TACTYO_ENCRYPTION_KEY",
    base64.b64encode(b"0123456789abcdef0123456789abcdef").decode(),
)


@pytest.mark.anyio
async def test_configure_github_project(client: AsyncClient, monkeypatch):
    await client.post(
        "/api/auth/register",
        json={"email": "owner@example.com", "password": "supersecret", "name": "Owner"},
    )

    await client.post("/api/accounts", json={"name": "Equipe Tactyo"})

    await client.post(
        "/api/settings/github-token",
        json={"token": "ghp_exampletoken123456789"},
    )

    status_response = await client.get("/api/settings/github-token")
    assert status_response.status_code == 200
    assert status_response.json()["configured"] is True

    async def fake_fetch_metadata(client, owner, number):
        return ProjectMetadata(
            node_id="PROJECT_NODE_ID",
            title="Tactyo",
            owner=owner,
            number=number,
            field_mappings={"Status": {"id": "status-id", "name": "Status"}},
        )

    async def fake_list_projects(client, owner):
        return [
            ProjectSummary(node_id="A", number=1, title="Project A", updated_at=None),
            ProjectSummary(node_id="B", number=2, title="Project B", updated_at=None),
        ]

    monkeypatch.setattr("app.services.github.fetch_project_metadata", fake_fetch_metadata)
    monkeypatch.setattr("app.services.github.list_projects", fake_list_projects)

    list_response = await client.get("/api/settings/github-projects", params={"owner": "viaiv"})
    assert list_response.status_code == 200
    assert len(list_response.json()) == 2

    response = await client.post(
        "/api/settings/github-project",
        json={"owner": "viaiv", "project_number": 1},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["owner_login"] == "viaiv"
    assert data["project_node_id"] == "PROJECT_NODE_ID"


@pytest.mark.anyio
async def test_sync_github_project(client: AsyncClient, session_factory, monkeypatch):
    await client.post(
        "/api/auth/register",
        json={"email": "owner@example.com", "password": "supersecret", "name": "Owner"},
    )

    await client.post("/api/accounts", json={"name": "Equipe Tactyo"})
    await client.post(
        "/api/settings/github-token",
        json={"token": "ghp_exampletoken123456789"},
    )

    status_response = await client.get("/api/settings/github-token")
    assert status_response.status_code == 200

    async def fake_fetch_metadata(client, owner, number):
        return ProjectMetadata(
            node_id="PROJECT_NODE_ID",
            title="Tactyo",
            owner=owner,
            number=number,
            field_mappings={"Status": {"id": "status-id", "name": "Status"}},
        )

    async def fake_fetch_items(client, project_node_id):
        return [
            ProjectItemPayload(
                node_id="ITEM_NODE",
                content_node_id="ISSUE_NODE",
                content_type="Issue",
                title="Implement feature",
                url="https://github.com/org/repo/issues/1",
                status="In Progress",
                iteration="Sprint 1",
                estimate=5.0,
                assignees=["alice"],
                updated_at=datetime.now(timezone.utc),
                field_values={"Status": "In Progress"},
            )
        ]

    async def fake_list_projects(client, owner):
        return [ProjectSummary(node_id="PROJECT_NODE_ID", number=1, title="Tactyo", updated_at=None)]

    monkeypatch.setattr("app.services.github.fetch_project_metadata", fake_fetch_metadata)
    monkeypatch.setattr("app.services.github.fetch_project_items", fake_fetch_items)
    monkeypatch.setattr("app.services.github.list_projects", fake_list_projects)

    project_response = await client.post(
        "/api/settings/github-project",
        json={"owner": "viaiv", "project_number": 1},
    )
    project_id = project_response.json()["id"]

    sync_response = await client.post(f"/api/github/sync/{project_id}")
    assert sync_response.status_code == 200
    assert sync_response.json()["synced_items"] == 1

    async with session_factory() as session:  # type: AsyncSession
        result = await session.execute(select(ProjectItem).where(ProjectItem.item_node_id == "ITEM_NODE"))
        item = result.scalar_one()
        assert item.title == "Implement feature"
        assert item.status == "In Progress"
        assert item.assignees == ["alice"]
