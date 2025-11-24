from typing import Optional
from pydantic import BaseModel, EmailStr
from datetime import datetime

# --- user ---
class UserCreate(BaseModel):
    username: str
    display_name: Optional[str]
    email: EmailStr
    password: str
    class Config:
        from_attributes = True

class UserOut(BaseModel):
    id: int
    username: str
    display_name: Optional[str]
    email: EmailStr
    is_active: bool
    created_at: datetime
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

# --- chat ---
class ChatCreate(BaseModel):
    name: str
    is_private: bool = False

class ChatOut(BaseModel):
    id: int
    name: str
    is_private: bool
    created_at: datetime
    class Config:
        from_attributes = True

class MemberCreate(BaseModel):
    user_id: int

# for messages created from /chats/{id}/messages
class ChatMessageCreate(BaseModel):
    content: str

# --- message ---
class MessageCreate(BaseModel):
    chat_id: int
    # user_id: int
    content: str

class MessageOut(BaseModel):
    id: int
    chat_id: int
    user_id: int
    content: str
    created_at: datetime
    class Config:
        from_attributes = True