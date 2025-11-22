from typing import Optional
from pydantic import BaseModel
from datetime import datetime

# --- user ---
class UserOut(BaseModel):
    id: int
    username: str
    display_name: Optional[str]
    email: Optional[str]
    created_at: datetime
    class Config:
        from_attributes = True

# --- chat ---
class ChatOut(BaseModel):
    id: int
    name: str
    is_private: bool
    created_at: datetime
    class Config:
        from_attributes = True

# --- message ---
class MessageOut(BaseModel):
    id: int
    channel_id: int
    user_id: int
    content: str
    created_at: datetime
    class Config:
        from_attributes = True

class MessageCreate(BaseModel):
    channel_id: int
    user_id: int
    content: str
    sticker_id: Optional[int] = None