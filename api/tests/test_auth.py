import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_register_first_user_establishes_session(client: AsyncClient):
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "owner@example.com",
            "password": "supersecret",
            "name": "Owner",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["role"] == "owner"
    assert data["needs_account_setup"] is True

    me_response = await client.get("/api/me")
    assert me_response.status_code == 200
    me_data = me_response.json()
    assert me_data["email"] == "owner@example.com"
    assert me_data["needs_account_setup"] is True


@pytest.mark.anyio
async def test_login_sets_session_and_me(client: AsyncClient):
    await client.post(
        "/api/auth/register",
        json={
            "email": "owner@example.com",
            "password": "supersecret",
            "name": "Owner",
        },
    )

    await client.post(
        "/api/accounts",
        json={"name": "Equipe Tactyo"},
    )

    await client.post("/api/auth/logout")

    login_response = await client.post(
        "/api/auth/login",
        json={"email": "owner@example.com", "password": "supersecret"},
    )
    assert login_response.status_code == 200

    me_response = await client.get("/api/me")
    assert me_response.status_code == 200


@pytest.mark.anyio
async def test_register_second_user_requires_admin(client: AsyncClient):
    await client.post(
        "/api/auth/register",
        json={
            "email": "owner@example.com",
            "password": "supersecret",
            "name": "Owner",
        },
    )

    await client.post(
        "/api/accounts",
        json={"name": "Equipe Tactyo"},
    )

    second_response = await client.post(
        "/api/auth/register",
        json={
            "email": "viewer@example.com",
            "password": "anothersecret",
            "name": "Viewer",
            "role": "viewer",
        },
    )
    assert second_response.status_code == 201
    data = second_response.json()
    assert data["role"] == "viewer"


@pytest.mark.anyio
async def test_register_requires_admin_when_not_first(client: AsyncClient):
    await client.post(
        "/api/auth/register",
        json={
            "email": "owner@example.com",
            "password": "supersecret",
            "name": "Owner",
        },
    )
    await client.post("/api/auth/logout")

    response = await client.post(
        "/api/auth/register",
        json={
            "email": "user2@example.com",
            "password": "anothersecret",
            "name": "User Two",
            "role": "viewer",
        },
    )
    assert response.status_code == 401


@pytest.mark.anyio
async def test_account_creation_only_once(client: AsyncClient):
    await client.post(
        "/api/auth/register",
        json={
            "email": "owner@example.com",
            "password": "supersecret",
            "name": "Owner",
        },
    )

    create_response = await client.post(
        "/api/accounts",
        json={"name": "Equipe Tactyo"},
    )
    assert create_response.status_code == 201

    duplicate_response = await client.post(
        "/api/accounts",
        json={"name": "Outra Conta"},
    )
    assert duplicate_response.status_code == 400
