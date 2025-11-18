"""Integration tests for task endpoints."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def authenticated_client(client: TestClient, test_user_data):
    """Create an authenticated client."""
    # Register and login
    client.post("/api/auth/register", json=test_user_data)
    response = client.post("/api/auth/login", json=test_user_data)
    token = response.json()["access_token"]

    # Add token to headers
    client.headers["Authorization"] = f"Bearer {token}"
    return client


def test_create_task(authenticated_client: TestClient, test_task_data):
    """Test creating a task."""
    response = authenticated_client.post("/api/tasks", json=test_task_data)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == test_task_data["title"]
    assert data["description"] == test_task_data["description"]
    assert data["urgency"] == test_task_data["urgency"]
    assert data["status"] == test_task_data["status"]
    assert "id" in data


def test_list_tasks(authenticated_client: TestClient, test_task_data):
    """Test listing tasks."""
    # Create a task first
    authenticated_client.post("/api/tasks", json=test_task_data)

    # List tasks
    response = authenticated_client.get("/api/tasks")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "data" in data
    assert isinstance(data["data"], list)
    assert len(data["data"]) >= 1
    assert data["data"][0]["title"] == test_task_data["title"]


def test_get_task(authenticated_client: TestClient, test_task_data):
    """Test getting a specific task."""
    # Create a task
    create_response = authenticated_client.post("/api/tasks", json=test_task_data)
    task_id = create_response.json()["id"]

    # Get the task
    response = authenticated_client.get(f"/api/tasks/{task_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == task_id
    assert data["title"] == test_task_data["title"]


def test_update_task(authenticated_client: TestClient, test_task_data):
    """Test updating a task."""
    # Create a task
    create_response = authenticated_client.post("/api/tasks", json=test_task_data)
    task_id = create_response.json()["id"]

    # Update the task
    update_data = {"title": "Updated Task Title", "urgency": "high"}
    response = authenticated_client.patch(f"/api/tasks/{task_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Task Title"
    assert data["urgency"] == "high"


def test_complete_task(authenticated_client: TestClient, test_task_data):
    """Test completing a task."""
    # Create a task
    create_response = authenticated_client.post("/api/tasks", json=test_task_data)
    task_id = create_response.json()["id"]

    # Complete the task
    response = authenticated_client.post(f"/api/tasks/{task_id}/complete")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "done"


def test_delete_task(authenticated_client: TestClient, test_task_data):
    """Test deleting a task."""
    # Create a task
    create_response = authenticated_client.post("/api/tasks", json=test_task_data)
    task_id = create_response.json()["id"]

    # Delete the task
    response = authenticated_client.delete(f"/api/tasks/{task_id}")
    assert response.status_code == 204

    # Verify it's deleted
    response = authenticated_client.get(f"/api/tasks/{task_id}")
    assert response.status_code == 404


def test_unauthorized_access(client: TestClient, test_task_data):
    """Test that unauthenticated requests are rejected."""
    response = client.get("/api/tasks")
    assert response.status_code == 401

    response = client.post("/api/tasks", json=test_task_data)
    assert response.status_code == 401
