from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db_session
from app.core.database import Base
from app.main import app
from app.models import association, project, todo, user  # noqa: F401


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db_session] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def register_user(client: TestClient, *, name: str, email: str, password: str):
    response = client.post(
        "/api/v1/auth/register",
        json={"name": name, "email": email, "password": password},
    )
    assert response.status_code == 201
    return response.json()


def login_user(client: TestClient, *, email: str, password: str):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    return response.json()


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_register_login_and_me(client: TestClient) -> None:
    register_payload = register_user(
        client,
        name="Alice",
        email="alice@example.com",
        password="password123",
    )
    assert register_payload["user"]["email"] == "alice@example.com"

    login_payload = login_user(client, email="alice@example.com", password="password123")
    me_response = client.get("/api/v1/auth/me", headers=auth_headers(login_payload["access_token"]))
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "alice@example.com"


def test_project_members_and_task_assignees(client: TestClient) -> None:
    alice = register_user(client, name="Alice", email="alice@example.com", password="password123")
    bob = register_user(client, name="Bob", email="bob@example.com", password="password123")

    alice_login = login_user(client, email="alice@example.com", password="password123")
    bob_login = login_user(client, email="bob@example.com", password="password123")

    project_response = client.post(
        "/api/v1/projects",
        headers=auth_headers(alice_login["access_token"]),
        json={
            "name": "Website Launch",
            "description": "Shared delivery",
            "member_ids": [bob["user"]["id"]],
        },
    )
    assert project_response.status_code == 201
    project_payload = project_response.json()
    assert len(project_payload["members"]) == 2

    todo_response = client.post(
        "/api/v1/todos",
        headers=auth_headers(alice_login["access_token"]),
        json={
            "title": "Ship landing page",
            "description": "Assign to both people",
            "project_id": project_payload["id"],
            "assignee_ids": [alice["user"]["id"], bob["user"]["id"]],
        },
    )
    assert todo_response.status_code == 201
    todo_payload = todo_response.json()
    assert todo_payload["project_id"] == project_payload["id"]
    assert len(todo_payload["assignees"]) == 2

    bob_list = client.get(
        "/api/v1/todos",
        headers=auth_headers(bob_login["access_token"]),
    )
    assert bob_list.status_code == 200
    assert bob_list.json()["total"] == 1

    project_get = client.get(
        f"/api/v1/projects/{project_payload['id']}",
        headers=auth_headers(bob_login["access_token"]),
    )
    assert project_get.status_code == 200

    users_response = client.get("/api/v1/users", headers=auth_headers(alice_login["access_token"]))
    assert users_response.status_code == 200
    assert users_response.json()["total"] == 2


def test_project_crud_operations(client: TestClient) -> None:
    # Register and login user
    alice = register_user(client, name="Alice", email="alice@example.com", password="password123")
    alice_login = login_user(client, email="alice@example.com", password="password123")
    alice_headers = auth_headers(alice_login["access_token"])

    # CREATE: Create a project
    create_response = client.post(
        "/api/v1/projects",
        headers=alice_headers,
        json={"name": "My Project", "description": "Test project"},
    )
    assert create_response.status_code == 201
    project = create_response.json()
    assert project["name"] == "My Project"

    # READ: Get project
    get_response = client.get(f"/api/v1/projects/{project['id']}", headers=alice_headers)
    assert get_response.status_code == 200
    assert get_response.json()["name"] == "My Project"

    # UPDATE: Update project
    update_response = client.patch(
        f"/api/v1/projects/{project['id']}",
        headers=alice_headers,
        json={"name": "Updated Project", "description": "Updated description"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Updated Project"

    # DELETE: Delete project
    delete_response = client.delete(f"/api/v1/projects/{project['id']}", headers=alice_headers)
    assert delete_response.status_code == 204

    # Verify deletion
    get_deleted = client.get(f"/api/v1/projects/{project['id']}", headers=alice_headers)
    assert get_deleted.status_code == 404


def test_project_permissions(client: TestClient) -> None:
    # Register two users
    alice = register_user(client, name="Alice", email="alice@example.com", password="password123")
    bob = register_user(client, name="Bob", email="bob@example.com", password="password123")

    alice_login = login_user(client, email="alice@example.com", password="password123")
    bob_login = login_user(client, email="bob@example.com", password="password123")

    alice_headers = auth_headers(alice_login["access_token"])
    bob_headers = auth_headers(bob_login["access_token"])

    # Alice creates a project without Bob
    project_response = client.post(
        "/api/v1/projects",
        headers=alice_headers,
        json={"name": "Alice's Project", "description": "Private project"},
    )
    project = project_response.json()

    # Bob should not see Alice's project
    bob_list = client.get("/api/v1/projects", headers=bob_headers)
    bob_projects = bob_list.json()["items"]
    assert all(p["id"] != project["id"] for p in bob_projects)

    # Bob cannot edit Alice's project
    bob_edit = client.patch(
        f"/api/v1/projects/{project['id']}",
        headers=bob_headers,
        json={"name": "Hacked Project"},
    )
    assert bob_edit.status_code == 403

    # Bob cannot delete Alice's project
    bob_delete = client.delete(f"/api/v1/projects/{project['id']}", headers=bob_headers)
    assert bob_delete.status_code == 403


def test_project_members_operations(client: TestClient) -> None:
    alice = register_user(client, name="Alice", email="alice@example.com", password="password123")
    bob = register_user(client, name="Bob", email="bob@example.com", password="password123")
    charlie = register_user(client, name="Charlie", email="charlie@example.com", password="password123")

    alice_login = login_user(client, email="alice@example.com", password="password123")
    alice_headers = auth_headers(alice_login["access_token"])

    # Create project with Bob
    project_response = client.post(
        "/api/v1/projects",
        headers=alice_headers,
        json={"name": "Team Project", "description": "Collab", "member_ids": [bob["user"]["id"]]},
    )
    project = project_response.json()
    assert len(project["members"]) == 2  # Alice + Bob

    # Add Charlie to project
    add_member_response = client.post(
        f"/api/v1/projects/{project['id']}/members",
        headers=alice_headers,
        json={"member_ids": [charlie["user"]["id"]]},
    )
    assert add_member_response.status_code == 200
    updated_project = add_member_response.json()
    assert len(updated_project["members"]) == 3  # Alice + Bob + Charlie

    # Remove Bob from project
    remove_member_response = client.delete(
        f"/api/v1/projects/{project['id']}/members/{bob['user']['id']}",
        headers=alice_headers,
    )
    assert remove_member_response.status_code == 200
    final_project = remove_member_response.json()
    assert len(final_project["members"]) == 2  # Alice + Charlie


def test_task_crud_operations(client: TestClient) -> None:
    alice = register_user(client, name="Alice", email="alice@example.com", password="password123")
    alice_login = login_user(client, email="alice@example.com", password="password123")
    alice_headers = auth_headers(alice_login["access_token"])

    # Create project
    project_response = client.post(
        "/api/v1/projects",
        headers=alice_headers,
        json={"name": "My Project", "description": "Test"},
    )
    project = project_response.json()

    # CREATE: Create a task
    task_response = client.post(
        "/api/v1/todos",
        headers=alice_headers,
        json={
            "title": "Test Task",
            "description": "Task description",
            "project_id": project["id"],
            "priority": "medium",
            "assignee_ids": [alice["user"]["id"]],
        },
    )
    assert task_response.status_code == 201
    task = task_response.json()
    assert task["title"] == "Test Task"
    assert task["priority"] == "medium"
    assert not task["completed"]

    # READ: Get task list
    list_response = client.get("/api/v1/todos", headers=alice_headers)
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1

    # UPDATE: Mark task as complete
    update_response = client.patch(
        f"/api/v1/todos/{task['id']}",
        headers=alice_headers,
        json={"completed": True},
    )
    assert update_response.status_code == 200
    assert update_response.json()["completed"]

    # DELETE: Delete task
    delete_response = client.delete(f"/api/v1/todos/{task['id']}", headers=alice_headers)
    assert delete_response.status_code == 204


def test_authentication_errors(client: TestClient) -> None:
    # Register a user
    register_user(client, name="Alice", email="alice@example.com", password="password123")

    # Test invalid password
    invalid_login = client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "wrongpassword"},
    )
    assert invalid_login.status_code == 401

    # Test non-existent email
    no_user_login = client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@example.com", "password": "password123"},
    )
    assert no_user_login.status_code == 401

    # Test duplicate email registration
    duplicate_email = client.post(
        "/api/v1/auth/register",
        json={"name": "Bob", "email": "alice@example.com", "password": "password123"},
    )
    assert duplicate_email.status_code == 400

    # Test missing authorization header
    unauthorized = client.get("/api/v1/auth/me")
    assert unauthorized.status_code == 401
