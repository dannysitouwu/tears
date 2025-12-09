import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app, get_db
from app.database import Base
from app.models import User, Chat, ChatMember, Message
import json

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

@pytest.fixture(scope="function")
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    yield
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
def client(setup_test_db):
    return TestClient(app)
@pytest.fixture
def setup_chat(client):
    client.post(
        "/auth/register",
        json={
            "username": "wsuser",
            "display_name": "WebSocket User",
            "email": "ws@example.com",
            "password": "testpass123"
        }
    )
    
    login_response = client.post(
        "/auth/token",
        data={
            "username": "wsuser",
            "password": "testpass123"
        }
    )
    token = login_response.json()["access_token"]
    
    chat_response = client.post(
        "/chats",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "WebSocket Test Chat",
            "is_private": False,
            "allow_anonymous": False
        }
    )
    chat_id = chat_response.json()["id"]
    
    return {"token": token, "chat_id": chat_id}

def test_websocket_connection(client, setup_chat):
    token = setup_chat["token"]
    chat_id = setup_chat["chat_id"]
    
    with client.websocket_connect(f"/ws/chats/{chat_id}?token={token}") as websocket:
        data = websocket.receive_json()
        assert data["type"] == "system"
        assert "Connected to chat" in data["message"]


def test_websocket_send_message(client, setup_chat):
    token = setup_chat["token"]
    chat_id = setup_chat["chat_id"]
    
    with client.websocket_connect(f"/ws/chats/{chat_id}?token={token}") as websocket:
        websocket.receive_json()
        
        websocket.send_text(json.dumps({"content": "Hello via WebSocket!"}))
        
        data = websocket.receive_json()
        assert data["type"] == "message"
        assert data["content"] == "Hello via WebSocket!"


def test_websocket_unauthorized(client, setup_chat):
    chat_id = setup_chat["chat_id"]
    
    with pytest.raises(Exception):
        with client.websocket_connect(f"/ws/chats/{chat_id}?token=invalid_token"):
            pass

def test_websocket_invalid_message_format(client, setup_chat):
    token = setup_chat["token"]
    chat_id = setup_chat["chat_id"]
    
    with client.websocket_connect(f"/ws/chats/{chat_id}?token={token}") as websocket:
        websocket.receive_json()
        
        websocket.send_text("not a json")

        data = websocket.receive_json()
        assert data["type"] == "error"
