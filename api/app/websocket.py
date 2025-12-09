from fastapi import WebSocket, WebSocketDisconnect, Depends, Query, status
from sqlalchemy.orm import Session
from typing import Dict, Set
import json
import logging
from datetime import datetime
from .database import SessionLocal
from .security import decode_access_token
from . import models, crud
from .metrics import increment_websocket_connections, decrement_websocket_connections, record_websocket_message

# logging for ws events
logging.basicConfig(
	level=logging.INFO,
	format='%(message)s'
)
logger = logging.getLogger("tears-websocket")


class ConnectionManager:
    
    def __init__(self):
        # {chat_id: {user_id: WebSocket}}
        self.active_connections: Dict[int, Dict[int, WebSocket]] = {}
        self.all_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket, chat_id: int, user_id: int):
        await websocket.accept()
        
        if chat_id not in self.active_connections:
            self.active_connections[chat_id] = {}
        
        self.active_connections[chat_id][user_id] = websocket
        self.all_connections.add(websocket)
        increment_websocket_connections()
        
        log_data = {
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            "event": "websocket_connected",
            "user_id": str(user_id),
            "chat_id": str(chat_id),
            "total_connections": len(self.all_connections),
            "chat_connections": len(self.active_connections.get(chat_id, {}))
        }
        logger.info(json.dumps(log_data))
    
    def disconnect(self, chat_id: int, user_id: int):
        if chat_id in self.active_connections:
            websocket = self.active_connections[chat_id].pop(user_id, None)
            if websocket:
                self.all_connections.discard(websocket)
                decrement_websocket_connections()
                log_data = {
                    "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                    "event": "websocket_disconnected",
                    "user_id": str(user_id),
                    "chat_id": str(chat_id),
                    "total_connections": len(self.all_connections)
                }
                logger.info(json.dumps(log_data))
            
            if not self.active_connections[chat_id]:
                del self.active_connections[chat_id]
    
    async def send_personal_message(self, message: dict, chat_id: int, user_id: int):
        if chat_id in self.active_connections:
            websocket = self.active_connections[chat_id].get(user_id)
            if websocket:
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    log_data = {
                        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                        "event": "websocket_error",
                        "error_type": "send_personal_message",
                        "user_id": str(user_id),
                        "chat_id": str(chat_id),
                        "error": str(e)
                    }
                    logger.error(json.dumps(log_data))
                    self.disconnect(chat_id, user_id)
    
    async def broadcast_to_chat(self, message: dict, chat_id: int, exclude_user: int = None):
        if chat_id not in self.active_connections:
            return
        
        record_websocket_message(chat_id)
        disconnected_users = []
        
        for user_id, websocket in self.active_connections[chat_id].items():
            if exclude_user and user_id == exclude_user:
                continue
            
            try:
                await websocket.send_json(message)
            except Exception as e:
                log_data = {
                    "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                    "event": "websocket_error",
                    "error_type": "broadcast_message",
                    "user_id": str(user_id),
                    "chat_id": str(chat_id),
                    "error": str(e)
                }
                logger.error(json.dumps(log_data))
                disconnected_users.append(user_id)
        
        for user_id in disconnected_users:
            self.disconnect(chat_id, user_id)
    
    def get_chat_users(self, chat_id: int):
        if chat_id in self.active_connections:
            return list(self.active_connections[chat_id].keys())
        return []
    
    def get_total_connections(self) -> int:
        return len(self.all_connections)


manager = ConnectionManager()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_current_user_ws(token: str, db: Session):
    """ usuário via JWT para WebSocket"""
    try:
        payload = decode_access_token(token)
        user_id = int(payload.get("sub"))
        user = crud.get_user(db, user_id)
        if not user:
            raise Exception("User not found")
        return user
    except Exception as e:
        raise Exception(f"Authentication error: {str(e)}")


async def websocket_endpoint(
    websocket: WebSocket,
    chat_id: int,
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint para chat em tempo real
    
    URL: ws://localhost:8000/ws/chats/{chat_id}?token=YOUR_JWT_TOKEN
    """
    
    # Autenticação
    try:
        user = await get_current_user_ws(token, db)
    except Exception as e:
        log_data = {
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            "event": "websocket_auth_failed",
            "chat_id": str(chat_id),
            "error": str(e)
        }
        logger.error(json.dumps(log_data))
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    chat = crud.get_chat(db, chat_id)
    if not chat:
        await websocket.close(code=status.WS_1003_UNSUPPORTED_DATA)
        return
    
    if chat.is_private and not crud.user_is_participant(db, chat_id, user.id):
        log_data = {
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            "event": "websocket_access_denied",
            "user_id": str(user.id),
            "chat_id": str(chat_id),
            "reason": "not_chat_member"
        }
        logger.warning(json.dumps(log_data))
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    await manager.connect(websocket, chat_id, user.id)
    
    await manager.send_personal_message({
        "type": "system",
        "message": f"Connected to chat: {chat.name}",
        "timestamp": datetime.utcnow().isoformat(),
        "chat_id": chat_id
    }, chat_id, user.id)
    
    await manager.broadcast_to_chat({
        "type": "user_joined",
        "user_id": user.id,
        "username": user.username,
        "timestamp": datetime.utcnow().isoformat()
    }, chat_id, exclude_user=user.id)
    
    try:
        while True:
            data = await websocket.receive_text()
            
            try:
                message_data = json.loads(data)
                
                if "content" not in message_data:
                    await manager.send_personal_message({
                        "type": "error",
                        "message": "Invalid message format. 'content' is required."
                    }, chat_id, user.id)
                    continue
                
                new_message = crud.create_message(
                    db, user.id, chat_id, message_data["content"]
                )

                await manager.broadcast_to_chat({
                    "type": "message",
                    "message_id": new_message.id,
                    "content": new_message.content,
                    "user_id": user.id,
                    "username": user.username,
                    "chat_id": chat_id,
                    "timestamp": new_message.created_at.isoformat()
                }, chat_id)
                
                log_data = {
                    "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                    "event": "websocket_message",
                    "user_id": str(user.id),
                    "chat_id": str(chat_id),
                    "message_id": str(new_message.id),
                    "content_length": len(new_message.content)
                }
                logger.info(json.dumps(log_data))
                
            except json.JSONDecodeError:
                await manager.send_personal_message({
                    "type": "error",
                    "message": "Invalid JSON format"
                }, chat_id, user.id)
            except Exception as e:
                log_data = {
                    "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                    "event": "websocket_error",
                    "error_type": "message_processing",
                    "user_id": str(user.id),
                    "chat_id": str(chat_id),
                    "error": str(e)
                }
                logger.error(json.dumps(log_data))
                await manager.send_personal_message({
                    "type": "error",
                    "message": "Error processing message"
                }, chat_id, user.id)
    
    except WebSocketDisconnect:
        manager.disconnect(chat_id, user.id)
        await manager.broadcast_to_chat({
            "type": "user_left",
            "user_id": user.id,
            "username": user.username,
            "timestamp": datetime.utcnow().isoformat()
        }, chat_id)
        log_data = {
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            "event": "websocket_disconnect",
            "user_id": str(user.id),
            "chat_id": str(chat_id),
            "reason": "client_disconnect"
        }
        logger.info(json.dumps(log_data))
    
    except Exception as e:
        log_data = {
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            "event": "websocket_error",
            "error_type": "unexpected",
            "user_id": str(user.id),
            "chat_id": str(chat_id),
            "error": str(e)
        }
        logger.error(json.dumps(log_data))
        manager.disconnect(chat_id, user.id)