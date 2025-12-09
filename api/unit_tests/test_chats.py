"""  
Unit tests for chat endpoints
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app, get_db
from app.database import Base


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
@pytest.fixture
def auth_token(client):
    """Create a user and return auth token"""
    client.post(
        "/auth/register",
        json={
            "username": "testuser",
            "display_name": "Test User",
            "email": "test@example.com",
            "password": "testpass123"
        }
    )
    
    response = client.post(
        "/auth/token",
        data={
            "username": "testuser",
            "password": "testpass123"
        }
    )
    return response.json()["access_token"]


def test_create_chat(client, auth_token):
    """Test creating a new chat"""
    response = client.post(
        "/chats",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "name": "Test Chat",
            "is_private": False,
            "allow_anonymous": False
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Chat"
    assert data["is_private"] == False
    assert "id" in data


def test_list_chats(client, auth_token):
    """Test listing chats"""
    # Create a chat first
    client.post(
        "/chats",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "name": "Test Chat",
            "is_private": False,
            "allow_anonymous": False
        }
    )
    
    # List chats
    response = client.get(
        "/chats",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) >= 1


def test_get_chat_details(client, auth_token):
    """Test getting chat details"""
    # Create a chat
    create_response = client.post(
        "/chats",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "name": "Test Chat",
            "is_private": False,
            "allow_anonymous": False
        }
    )
    chat_id = create_response.json()["id"]
    
    # Get chat details
    response = client.get(
        f"/chats/{chat_id}",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Chat"
    assert data["id"] == chat_id


def test_send_message(client, auth_token):
    """Test sending a message to chat"""
    # Create a chat
    create_response = client.post(
        "/chats",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "name": "Test Chat",
            "is_private": False,
            "allow_anonymous": False
        }
    )
    chat_id = create_response.json()["id"]
    
    # Send message
    response = client.post(
        f"/chats/{chat_id}/messages",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"content": "Hello, this is a test message!"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["content"] == "Hello, this is a test message!"
    assert data["chat_id"] == chat_id


def test_get_chat_messages(client, auth_token):
    """Test getting chat messages"""
    # Create chat and send message
    create_response = client.post(
        "/chats",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "name": "Test Chat",
            "is_private": False,
            "allow_anonymous": False
        }
    )
    chat_id = create_response.json()["id"]
    
    client.post(
        f"/chats/{chat_id}/messages",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"content": "Test message"}
    )
    
    # Get messages
    response = client.get(
        f"/chats/{chat_id}/messages",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) >= 1


def test_search_chats(client, auth_token):
    """Test searching chats"""
    # Create a chat
    client.post(
        "/chats",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "name": "Unique Chat Name",
            "is_private": False,
            "allow_anonymous": False
        }
    )
    
    # Search
    response = client.get(
        "/chats?search=Unique",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) >= 1
    assert "Unique" in data["items"][0]["name"]
