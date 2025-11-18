"""Integration tests for group endpoints."""

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


def test_create_group(authenticated_client: TestClient):
    """Test creating a group."""
    group_data = {
        "name": "Test Group",
        "description": "A test group",
    }
    response = authenticated_client.post("/api/groups", json=group_data)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == group_data["name"]
    assert data["description"] == group_data["description"]
    assert "id" in data


def test_list_groups(authenticated_client: TestClient):
    """Test listing groups."""
    # Create a group first
    group_data = {"name": "Test Group", "description": "A test group"}
    authenticated_client.post("/api/groups", json=group_data)

    # List groups
    response = authenticated_client.get("/api/groups")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "data" in data
    assert isinstance(data["data"], list)
    assert len(data["data"]) >= 1


def test_get_group(authenticated_client: TestClient):
    """Test getting a specific group."""
    # Create a group
    group_data = {"name": "Test Group", "description": "A test group"}
    create_response = authenticated_client.post("/api/groups", json=group_data)
    group_id = create_response.json()["id"]

    # Get the group
    response = authenticated_client.get(f"/api/groups/{group_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == group_id
    assert data["name"] == group_data["name"]


def test_update_group(authenticated_client: TestClient):
    """Test updating a group."""
    # Create a group
    group_data = {"name": "Test Group", "description": "A test group"}
    create_response = authenticated_client.post("/api/groups", json=group_data)
    group_id = create_response.json()["id"]

    # Update the group
    update_data = {"name": "Updated Group Name"}
    response = authenticated_client.patch(f"/api/groups/{group_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Group Name"


def test_delete_group(authenticated_client: TestClient):
    """Test deleting a group."""
    # Create a group
    group_data = {"name": "Test Group", "description": "A test group"}
    create_response = authenticated_client.post("/api/groups", json=group_data)
    group_id = create_response.json()["id"]

    # Delete the group
    response = authenticated_client.delete(f"/api/groups/{group_id}")
    assert response.status_code == 204

    # Verify it's deleted
    response = authenticated_client.get(f"/api/groups/{group_id}")
    assert response.status_code == 404
