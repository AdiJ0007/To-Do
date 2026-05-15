"""Test separate admin and member roles with email format."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db_session
from app.core.database import Base
from app.main import app
from app.models import association, project, todo, user  # noqa: F401
from app.services.user_service import detect_role_from_email


@pytest.fixture()
def client() -> TestClient:
    """Create a test client with an in-memory database."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db() -> Session:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db_session] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_detect_role_from_email():
    """Test that email format correctly determines role."""
    assert detect_role_from_email("john.admin@test.com") == "admin"
    assert detect_role_from_email("JOHN.ADMIN@TEST.COM") == "admin"  # Case insensitive
    assert detect_role_from_email("jane.member@test.com") == "member"
    assert detect_role_from_email("JANE.MEMBER@TEST.COM") == "member"  # Case insensitive
    assert detect_role_from_email("bob@test.com") == "member"  # Default to member


def test_register_admin_user(client: TestClient):
    """Test registering an admin user."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "John Admin",
            "email": "john.admin@test.com",
            "password": "SecurePassword123",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["user"]["role"] == "admin"
    assert data["user"]["email"] == "john.admin@test.com"


def test_register_member_user(client: TestClient):
    """Test registering a member user."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Jane Member",
            "email": "jane.member@test.com",
            "password": "SecurePassword123",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["user"]["role"] == "member"
    assert data["user"]["email"] == "jane.member@test.com"


def test_login_admin_user(client: TestClient):
    """Test logging in as admin."""
    # First register
    client.post(
        "/api/v1/auth/register",
        json={
            "name": "John Admin",
            "email": "john.admin@test.com",
            "password": "SecurePassword123",
        },
    )

    # Then login
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "john.admin@test.com", "password": "SecurePassword123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["role"] == "admin"


def test_admin_sees_all_project_todos(client: TestClient):
    """Test that admin can see all todos in their projects."""
    # Create admin and member users
    admin_user = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Admin User",
            "email": "admin.admin@test.com",
            "password": "SecurePassword123",
        },
    ).json()
    admin_token = admin_user["access_token"]

    member_user = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Member User",
            "email": "member.member@test.com",
            "password": "SecurePassword123",
        },
    ).json()

    # Create a project as admin
    project_response = client.post(
        "/api/v1/projects",
        json={"name": "Test Project", "description": "Test", "member_ids": [member_user["user"]["id"]]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert project_response.status_code == 201
    project = project_response.json()

    # Create a todo in the project assigned to member (by admin)
    todo_response = client.post(
        "/api/v1/todos",
        json={
            "title": "Member Task",
            "description": "Task for member",
            "priority": "medium",
            "project_id": project["id"],
            "assignee_ids": [member_user["user"]["id"]],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert todo_response.status_code == 201
    todo = todo_response.json()

    # Admin should see the todo
    todos_response = client.get(
        "/api/v1/todos?skip=0&limit=10",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert todos_response.status_code == 200
    todos = todos_response.json()
    assert len(todos["items"]) == 1
    assert todos["items"][0]["id"] == todo["id"]


def test_member_only_sees_assigned_todos(client: TestClient):
    """Test that member can only see todos assigned to them."""
    # Create admin and two members
    admin_user = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Admin User",
            "email": "admin.admin@test.com",
            "password": "SecurePassword123",
        },
    ).json()
    admin_token = admin_user["access_token"]

    member1_user = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Member 1",
            "email": "member1.member@test.com",
            "password": "SecurePassword123",
        },
    ).json()
    member1_token = member1_user["access_token"]

    member2_user = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Member 2",
            "email": "member2.member@test.com",
            "password": "SecurePassword123",
        },
    ).json()

    # Create a project
    project_response = client.post(
        "/api/v1/projects",
        json={
            "name": "Test Project",
            "description": "Test",
            "member_ids": [member1_user["user"]["id"], member2_user["user"]["id"]],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    project = project_response.json()

    # Create two todos - one for member1, one for member2
    todo1_response = client.post(
        "/api/v1/todos",
        json={
            "title": "Task for Member 1",
            "priority": "medium",
            "project_id": project["id"],
            "assignee_ids": [member1_user["user"]["id"]],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    todo1 = todo1_response.json()

    todo2_response = client.post(
        "/api/v1/todos",
        json={
            "title": "Task for Member 2",
            "priority": "medium",
            "project_id": project["id"],
            "assignee_ids": [member2_user["user"]["id"]],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Member1 should only see todo1
    todos_response = client.get(
        "/api/v1/todos?skip=0&limit=10",
        headers={"Authorization": f"Bearer {member1_token}"},
    )
    todos = todos_response.json()
    assert len(todos["items"]) == 1
    assert todos["items"][0]["id"] == todo1["id"]
