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
    allow_anonymous: bool = False 

class ChatOut(BaseModel):
    id: int
    name: str
    is_private: bool
    created_at: datetime
    member_count: int = 0
    message_count: int = 0
    role: Optional[str] = None 
    class Config:
        from_attributes = True

class MemberCreate(BaseModel):
    user_id: Optional[int] = None
    username: Optional[str] = None

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
    username: Optional[str]
    display_name: Optional[str]
    content: str
    created_at: datetime
    class Config:
        from_attributes = True