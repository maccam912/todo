"""Integration tests for API endpoints."""

from fastapi.testclient import TestClient


def test_root_endpoint(client: TestClient):
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "SmartTodo API"
    assert "version" in data


def test_health_endpoint(client: TestClient):
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_register_user(client: TestClient, test_user_data):
    """Test user registration."""
    response = client.post("/api/auth/register", json=test_user_data)
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == test_user_data["username"]
    assert "id" in data
    assert "password" not in data


def test_register_duplicate_user(client: TestClient, test_user_data):
    """Test registering a duplicate user."""
    # Register first time
    response = client.post("/api/auth/register", json=test_user_data)
    assert response.status_code == 201

    # Try to register again with same username
    response = client.post("/api/auth/register", json=test_user_data)
    assert response.status_code == 400


def test_login_user(client: TestClient, test_user_data):
    """Test user login."""
    # Register user
    client.post("/api/auth/register", json=test_user_data)

    # Login
    response = client.post("/api/auth/login", json=test_user_data)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_credentials(client: TestClient, test_user_data):
    """Test login with invalid credentials."""
    # Register user
    client.post("/api/auth/register", json=test_user_data)

    # Try to login with wrong password
    invalid_data = test_user_data.copy()
    invalid_data["password"] = "WrongPassword123!"
    response = client.post("/api/auth/login", json=invalid_data)
    assert response.status_code == 401
