"""
Unit tests for authentication endpoints
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app, get_db
from app.database import Base
from app.models import User
import os


# Test database - use SQLite in memory for isolation
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def setup_test_db():
    """Create tables before each test and drop after"""
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    yield
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def client(setup_test_db):
    """TestClient with database setup"""
    return TestClient(app)


def test_register_user(client):
    """Test user registration"""
    response = client.post(
        "/auth/register",
        json={
            "username": "testuser",
            "display_name": "Test User",
            "email": "test@example.com",
            "password": "testpass123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    assert "id" in data


def test_register_duplicate_username(client):
    """Test registering with duplicate username"""
    # First registration
    client.post(
        "/auth/register",
        json={
            "username": "testuser",
            "display_name": "Test User 1",
            "email": "test1@example.com",
            "password": "testpass123"
        }
    )
    
    # Duplicate username
    response = client.post(
        "/auth/register",
        json={
            "username": "testuser",
            "display_name": "Test User 2",
            "email": "test2@example.com",
            "password": "testpass123"
        }
    )
    assert response.status_code == 400


def test_login_success(client):
    """Test successful login"""
    # Register user
    client.post(
        "/auth/register",
        json={
            "username": "testuser",
            "display_name": "Test User",
            "email": "test@example.com",
            "password": "testpass123"
        }
    )
    
    # Login
    response = client.post(
        "/auth/token",
        data={
            "username": "testuser",
            "password": "testpass123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client):
    """Test login with wrong password"""
    # Register user
    client.post(
        "/auth/register",
        json={
            "username": "testuser",
            "display_name": "Test User",
            "email": "test@example.com",
            "password": "testpass123"
        }
    )
    
    # Login with wrong password
    response = client.post(
        "/auth/token",
        data={
            "username": "testuser",
            "password": "wrongpassword"
        }
    )
    assert response.status_code == 401


def test_get_current_user(client):
    """Test getting current user info"""
    # Register and login
    client.post(
        "/auth/register",
        json={
            "username": "testuser",
            "display_name": "Test User",
            "email": "test@example.com",
            "password": "testpass123"
        }
    )
    
    login_response = client.post(
        "/auth/token",
        data={
            "username": "testuser",
            "password": "testpass123"
        }
    )
    token = login_response.json()["access_token"]
    
    # Get user info
    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"


def test_get_current_user_unauthorized(client):
    """Test getting current user without token"""
    response = client.get("/auth/me")
    assert response.status_code == 401
