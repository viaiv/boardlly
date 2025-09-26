from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

import httpx
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt_secret, encrypt_secret
from app.models.account import Account
from app.models.account_github_credentials import AccountGithubCredentials
from app.models.github_project import GithubProject
from app.models.project_item import ProjectItem
from app.models.github_project_field import GithubProjectField

GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"


@dataclass
class ProjectMetadata:
    node_id: str
    title: Optional[str]
    owner: str
    number: int
    field_mappings: Dict[str, Any]


@dataclass
class ProjectItemPayload:
    node_id: str
    content_node_id: Optional[str]
    content_type: Optional[str]
    title: Optional[str]
    url: Optional[str]
    status: Optional[str]
    iteration: Optional[str]
    iteration_id: Optional[str]
    iteration_start: Optional[datetime]
    iteration_end: Optional[datetime]
    estimate: Optional[float]
    assignees: List[str]
    updated_at: Optional[datetime]
    remote_updated_at: Optional[datetime]
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    due_date: Optional[datetime]
    field_values: Dict[str, Any]


@dataclass
class ProjectSummary:
    node_id: str
    number: int
    title: Optional[str]
    updated_at: Optional[datetime]


@dataclass
class ParsedFieldDetails:
    iteration_title: Optional[str] = None
    iteration_id: Optional[str] = None
    iteration_start: Optional[datetime] = None
    iteration_end: Optional[datetime] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    due_date: Optional[datetime] = None


START_DATE_ALIASES = {"start date", "start", "kickoff", "início", "inicio"}
END_DATE_ALIASES = {"end date", "finish", "fim", "conclusão", "conclusao"}
DUE_DATE_ALIASES = {"due date", "target date", "deadline", "entrega"}


async def store_github_token(db: AsyncSession, account: Account, token: str) -> None:
    nonce, ciphertext = encrypt_secret(token)
    credentials = await db.get(AccountGithubCredentials, account.id)
    if credentials:
        credentials.pat_ciphertext = ciphertext
        credentials.pat_nonce = nonce
    else:
        credentials = AccountGithubCredentials(
            account_id=account.id,
            pat_ciphertext=ciphertext,
            pat_nonce=nonce,
        )
        db.add(credentials)
    await db.flush()


async def get_github_token(db: AsyncSession, account: Account) -> str:
    credentials = await db.get(AccountGithubCredentials, account.id)
    if not credentials:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Token do GitHub não configurado")
    return decrypt_secret(credentials.pat_nonce, credentials.pat_ciphertext)


class GithubGraphQLClient:
    def __init__(self, token: str):
        self._client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {token}",
                "User-Agent": "Tactyo/0.1",
                "X-GitHub-Api-Version": "2022-11-28",
                "GraphQL-Features": "projects_next_graphql",
            },
            timeout=httpx.Timeout(15.0, connect=10.0),
        )

    async def execute(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        try:
            response = await self._client.post(GITHUB_GRAPHQL_URL, json={"query": query, "variables": variables})
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=f"GitHub API retornou status {exc.response.status_code}: {detail}",
            ) from exc
        except httpx.RequestError as exc:
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Não foi possível se comunicar com o GitHub",
            ) from exc

        data = response.json()
        print(f"DEBUG: GitHub GraphQL response: {data}")

        # Check for fatal errors (not partial data errors)
        if errors := data.get("errors"):
            fatal_errors = []
            for error in errors:
                # Skip NOT_FOUND errors for specific paths (user/organization queries)
                if error.get("type") == "NOT_FOUND" and error.get("path") in [["user"], ["organization"]]:
                    continue
                fatal_errors.append(error)

            if fatal_errors:
                message = ", ".join(error.get("message", "Erro desconhecido") for error in fatal_errors)
                print(f"DEBUG: Fatal GraphQL errors: {fatal_errors}")
                raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=message)

        return data["data"]

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "GithubGraphQLClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()


async def fetch_project_metadata(client: GithubGraphQLClient, owner: str, number: int) -> ProjectMetadata:
    query = """
    query($owner: String!, $number: Int!) {
      organization(login: $owner) {
        projectV2(number: $number) {
          id
          title
          fields(first: 50) {
            nodes {
              __typename
              ... on ProjectV2FieldCommon { id name dataType }
              ... on ProjectV2IterationField { id name configuration { iterations { id title startDate duration } } }
              ... on ProjectV2SingleSelectField { id name options { id name } }
            }
          }
        }
      }
      user(login: $owner) {
        projectV2(number: $number) {
          id
          title
          fields(first: 50) {
            nodes {
              __typename
              ... on ProjectV2FieldCommon { id name dataType }
              ... on ProjectV2IterationField { id name configuration { iterations { id title startDate duration } } }
              ... on ProjectV2SingleSelectField { id name options { id name } }
            }
          }
        }
      }
    }
    """
    data = await client.execute(query, {"owner": owner, "number": number})
    project = data.get("organization", {}).get("projectV2") or data.get("user", {}).get("projectV2")
    if not project:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Projeto não encontrado no GitHub")

    fields = project.get("fields", {}).get("nodes", [])
    field_mappings = {}
    for field in fields:
        name = field.get("name")
        if not name:
            continue
        field_mappings[name] = field
    return ProjectMetadata(
        node_id=project["id"],
        title=project.get("title"),
        owner=owner,
        number=number,
        field_mappings=field_mappings,
    )


async def list_projects(client: GithubGraphQLClient, owner: str) -> List[ProjectSummary]:
    query = """
    query($owner: String!) {
      organization(login: $owner) {
        projectsV2(first: 50) {
          nodes {
            id
            number
            title
            updatedAt
          }
        }
      }
      user(login: $owner) {
        projectsV2(first: 50) {
          nodes {
            id
            number
            title
            updatedAt
          }
        }
      }
    }
    """
    data = await client.execute(query, {"owner": owner})
    org = data.get("organization")
    usr = data.get("user")
    if org is None and usr is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Owner não encontrado no GitHub")

    nodes: List[dict[str, Any]] = []
    if org and org.get("projectsV2"):
        nodes.extend(org["projectsV2"].get("nodes", []))
    if usr and usr.get("projectsV2"):
        nodes.extend(usr["projectsV2"].get("nodes", []))

    summaries: List[ProjectSummary] = []
    for node in nodes:
        try:
            number = int(node.get("number"))
        except (TypeError, ValueError):
            continue
        summaries.append(
            ProjectSummary(
                node_id=node.get("id"),
                number=number,
                title=node.get("title"),
                updated_at=parse_datetime(node.get("updatedAt")),
            )
        )
    return summaries


async def fetch_project_items(client: GithubGraphQLClient, project_node_id: str) -> List[ProjectItemPayload]:
    query = """
    query($projectId: ID!, $first: Int!, $after: String) {
      node(id: $projectId) {
        ... on ProjectV2 {
          items(first: $first, after: $after) {
            pageInfo { hasNextPage endCursor }
            nodes {
              id
              updatedAt
              content {
                __typename
                ... on Issue { id title url updatedAt assignees(first: 20) { nodes { login } } }
                ... on PullRequest { id title url updatedAt assignees(first: 20) { nodes { login } } }
                ... on DraftIssue { id title }
              }
              fieldValues(first: 50) {
                nodes {
                  __typename
                  ... on ProjectV2ItemFieldTextValue { field { ... on ProjectV2FieldCommon { name } } text }
                  ... on ProjectV2ItemFieldNumberValue { field { ... on ProjectV2FieldCommon { name } } number }
                  ... on ProjectV2ItemFieldSingleSelectValue { field { ... on ProjectV2FieldCommon { name } } name }
                  ... on ProjectV2ItemFieldDateValue { field { ... on ProjectV2FieldCommon { name dataType } } date }
                  ... on ProjectV2ItemFieldIterationValue {
                    field { ... on ProjectV2FieldCommon { name } }
                    title
                    iterationId
                    startDate
                    duration
                  }
                }
              }
            }
          }
        }
      }
    }
    """
    items: List[ProjectItemPayload] = []
    after: Optional[str] = None
    while True:
        data = await client.execute(query, {"projectId": project_node_id, "first": 50, "after": after})
        node = data.get("node")
        if not node:
            break
        items_data = node.get("items", {})
        for element in items_data.get("nodes", []):
            content = element.get("content") or {}
            typename = content.get("__typename")
            field_nodes = element.get("fieldValues", {}).get("nodes", [])
            field_values, field_details = parse_field_details(field_nodes)
            assignees = extract_assignees(content)
            project_item_updated = parse_datetime(element.get("updatedAt"))
            content_updated = parse_datetime(content.get("updatedAt"))
            items.append(
                ProjectItemPayload(
                    node_id=element.get("id"),
                    content_node_id=content.get("id"),
                    content_type=typename,
                    title=content.get("title") or element.get("title"),
                    url=content.get("url"),
                    status=field_values.get("Status"),
                    iteration=field_details.iteration_title or field_values.get("Iteration"),
                    iteration_id=field_details.iteration_id,
                    iteration_start=field_details.iteration_start,
                    iteration_end=field_details.iteration_end,
                    estimate=safe_number(field_values.get("Estimate")),
                    assignees=assignees,
                    updated_at=content_updated or project_item_updated,
                    remote_updated_at=project_item_updated,
                    start_date=field_details.start_date,
                    end_date=field_details.end_date,
                    due_date=field_details.due_date,
                    field_values=field_values,
                )
            )
        page_info = items_data.get("pageInfo", {})
        if not page_info.get("hasNextPage"):
            break
        after = page_info.get("endCursor")
    return items


def parse_field_details(nodes: List[dict[str, Any]]) -> tuple[Dict[str, Any], ParsedFieldDetails]:
    values: Dict[str, Any] = {}
    details = ParsedFieldDetails()

    for node in nodes:
        field = node.get("field") or {}
        name = field.get("name")
        if not name:
            continue

        typename = node.get("__typename")
        lower_name = name.lower()

        if typename == "ProjectV2ItemFieldNumberValue":
            values[name] = node.get("number")
        elif typename == "ProjectV2ItemFieldSingleSelectValue":
            values[name] = node.get("name")
        elif typename == "ProjectV2ItemFieldIterationValue":
            values[name] = node.get("title")
            details.iteration_title = node.get("title")
            details.iteration_id = node.get("iterationId")
            details.iteration_start = parse_date_value(node.get("startDate"))
            details.iteration_end = compute_iteration_end(details.iteration_start, node.get("duration"))
        elif typename == "ProjectV2ItemFieldDateValue":
            values[name] = node.get("date")
            date_value = parse_date_value(node.get("date"))
            if not date_value:
                continue
            if lower_name in START_DATE_ALIASES and not details.start_date:
                details.start_date = date_value
            elif lower_name in END_DATE_ALIASES and not details.end_date:
                details.end_date = date_value
            elif lower_name in DUE_DATE_ALIASES and not details.due_date:
                details.due_date = date_value
        elif typename == "ProjectV2ItemFieldTextValue":
            values[name] = node.get("text")
        else:
            values[name] = node.get("text")

    if not details.start_date and details.iteration_start:
        details.start_date = details.iteration_start

    if not details.end_date:
        if details.iteration_end:
            details.end_date = details.iteration_end
        elif details.due_date:
            details.end_date = details.due_date

    if not details.start_date and details.due_date:
        details.start_date = details.due_date - timedelta(days=1)

    return values, details


def parse_date_value(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        if value.endswith("Z"):
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        else:
            dt = datetime.fromisoformat(value)
    except ValueError:
        return None

    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def compute_iteration_end(start: Optional[datetime], duration_value: Any) -> Optional[datetime]:
    if not start or duration_value in (None, ""):
        return None
    try:
        duration_int = int(duration_value)
    except (TypeError, ValueError):
        return None
    return start + timedelta(days=duration_int)


def extract_assignees(content: dict[str, Any]) -> List[str]:
    assignees = content.get("assignees", {}).get("nodes") if content else None
    if not assignees:
        return []
    return [node.get("login") for node in assignees if node.get("login")]


def parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def safe_number(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


async def upsert_github_project(
    db: AsyncSession,
    account: Account,
    metadata: ProjectMetadata,
) -> GithubProject:
    stmt = select(GithubProject).where(GithubProject.account_id == account.id)
    existing = await db.execute(stmt)
    project = existing.scalar_one_or_none()
    if project:
        project.owner_login = metadata.owner
        project.project_number = metadata.number
        project.project_node_id = metadata.node_id
        project.name = metadata.title
        project.field_mappings = metadata.field_mappings
        if metadata.field_mappings and not project.status_columns:
            project.status_columns = extract_status_columns(metadata.field_mappings)
    else:
        project = GithubProject(
            account_id=account.id,
            owner_login=metadata.owner,
            project_number=metadata.number,
            project_node_id=metadata.node_id,
            name=metadata.title,
            field_mappings=metadata.field_mappings,
            status_columns=extract_status_columns(metadata.field_mappings) if metadata.field_mappings else None,
        )
        db.add(project)
    await db.flush()
    if metadata.field_mappings:
        await sync_project_fields(db, project, metadata.field_mappings)
        await db.flush()
    return project


async def upsert_project_items(
    db: AsyncSession,
    account: Account,
    project: GithubProject,
    items: List[ProjectItemPayload],
) -> int:
    count = 0
    for payload in items:
        stmt = select(ProjectItem).where(ProjectItem.item_node_id == payload.node_id)
        result = await db.execute(stmt)
        item = result.scalar_one_or_none()
        if item:
            item.content_node_id = payload.content_node_id
            item.content_type = payload.content_type
            item.title = payload.title
            item.url = payload.url
            item.status = payload.status
            item.iteration = payload.iteration
            item.iteration_id = payload.iteration_id
            item.iteration_start = payload.iteration_start
            item.iteration_end = payload.iteration_end
            item.estimate = payload.estimate
            item.assignees = payload.assignees
            item.start_date = payload.start_date
            item.end_date = payload.end_date
            item.due_date = payload.due_date
            item.field_values = payload.field_values
            item.updated_at = payload.updated_at
            item.last_synced_at = datetime.now(timezone.utc)
            item.remote_updated_at = payload.remote_updated_at
        else:
            item = ProjectItem(
                account_id=account.id,
                project_id=project.id,
                item_node_id=payload.node_id,
                content_node_id=payload.content_node_id,
                content_type=payload.content_type,
                title=payload.title,
                url=payload.url,
                status=payload.status,
                iteration=payload.iteration,
                iteration_id=payload.iteration_id,
                iteration_start=payload.iteration_start,
                iteration_end=payload.iteration_end,
                estimate=payload.estimate,
                assignees=payload.assignees,
                start_date=payload.start_date,
                end_date=payload.end_date,
                due_date=payload.due_date,
                field_values=payload.field_values,
                updated_at=payload.updated_at,
                remote_updated_at=payload.remote_updated_at,
                last_synced_at=datetime.now(timezone.utc),
            )
            db.add(item)
        count += 1
    project.last_synced_at = datetime.now(timezone.utc)
    await db.flush()
    return count


async def sync_github_project(
    db: AsyncSession,
    account: Account,
    project: GithubProject,
    token: str,
) -> int:
    async with GithubGraphQLClient(token) as client:
        items = await fetch_project_items(client, project.project_node_id)
    count = await upsert_project_items(db, account, project, items)
    await db.commit()
    return count


async def sync_project_fields(
    db: AsyncSession,
    project: GithubProject,
    field_mappings: dict[str, Any],
) -> None:
    existing = {field.field_id: field for field in project.fields}
    seen: set[str] = set()

    for name, data in field_mappings.items():
        if not isinstance(data, dict):
            continue
        field_id = data.get("id")
        if not field_id:
            continue
        field_type = data.get("dataType") or data.get("__typename") or "UNKNOWN"

        options: Any = None
        if isinstance(data.get("options"), list):
            options = data.get("options")
        elif isinstance(data.get("configuration"), dict):
            options = data.get("configuration")

        existing_field = existing.get(field_id)
        if existing_field:
            existing_field.field_name = name
            existing_field.field_type = field_type
            existing_field.options = options
        else:
            db.add(
                GithubProjectField(
                    project_id=project.id,
                    field_id=field_id,
                    field_name=name,
                    field_type=field_type,
                    options=options,
                )
            )
        seen.add(field_id)

    for field_id, field in existing.items():
        if field_id not in seen:
            await db.delete(field)


def ensure_timezone(value: Optional[datetime]) -> Optional[datetime]:
    if not value:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def resolve_iteration_field(project: GithubProject) -> Optional[GithubProjectField]:
    for field in project.fields:
        field_type = (field.field_type or "").lower()
        field_name = (field.field_name or "").lower()
        if field_type in {"iteration", "projectv2iterationfield"} or field_name == "iteration":
            return field
    return None


def resolve_iteration_option(
    iteration_field: Optional[GithubProjectField],
    iteration_id: Optional[str],
) -> tuple[Optional[str], Optional[datetime], Optional[datetime]]:
    if not iteration_field or not iteration_id:
        return None, None, None
    options = iteration_field.options or {}
    iterations = []
    if isinstance(options, dict):
        iterations = options.get("iterations") or []
    elif isinstance(options, list):
        iterations = options
    for option in iterations or []:
        if option.get("id") == iteration_id:
            title = option.get("title")
            start = parse_date_value(option.get("startDate"))
            end = compute_iteration_end(start, option.get("duration"))
            return title, start, end
    return None, None, None


async def apply_local_project_item_updates(
    db: AsyncSession,
    project: GithubProject,
    item: ProjectItem,
    updates: dict[str, Any],
    editor_id: Optional[uuid.UUID],
) -> ProjectItem:
    if not updates:
        return item

    start_date = ensure_timezone(updates.get("start_date")) if "start_date" in updates else None
    end_date = ensure_timezone(updates.get("end_date")) if "end_date" in updates else None
    due_date = ensure_timezone(updates.get("due_date")) if "due_date" in updates else None

    if start_date and end_date and end_date < start_date:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="end_date deve ser maior ou igual a start_date")

    has_changes = False

    if "start_date" in updates:
        item.start_date = start_date
        has_changes = True

    if "end_date" in updates:
        item.end_date = end_date
        has_changes = True

    if "due_date" in updates:
        item.due_date = due_date
        has_changes = True

    if "iteration_id" in updates:
        iteration_field = resolve_iteration_field(project)
        iteration_id = updates.get("iteration_id")
        if iteration_id:
            title_from_options, iteration_start, iteration_end = resolve_iteration_option(iteration_field, iteration_id)
            item.iteration_id = iteration_id
            item.iteration = updates.get("iteration_title") or title_from_options or item.iteration
            item.iteration_start = iteration_start
            item.iteration_end = iteration_end
        else:
            item.iteration_id = None
            item.iteration = None
            item.iteration_start = None
            item.iteration_end = None
        has_changes = True

    if has_changes:
        item.last_local_edit_at = datetime.now(timezone.utc)
        item.last_local_edit_by = editor_id
        await db.flush()

    return item


def extract_status_columns(field_mappings: dict[str, Any]) -> list[str] | None:
    status_field = field_mappings.get("Status")
    if not status_field:
        return None
    options = status_field.get("options")
    if not options or not isinstance(options, list):
        return None
    names = [option.get("name") for option in options if option.get("name")]
    unique = []
    for name in names:
        if name not in unique:
            unique.append(name)
    if "Done" not in unique:
        unique.append("Done")
    return unique
