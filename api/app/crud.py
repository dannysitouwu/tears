from sqlalchemy.orm import Session
from . import models
from typing import List, Optional
from sqlalchemy import func
from .security import hash_password
from .schemas import UserCreate

MAX_PER_PAGE = 250

def paginate_query(query, page: int = 1, per_page: int = 50):
	per_page = min(per_page, MAX_PER_PAGE)
	page = max(page, 1)
	total_items = query.order_by(None).count()
	total_pages = (total_items + per_page - 1) // per_page if total_items else 0
	items = query.offset((page - 1) * per_page).limit(per_page).all()
	return {
		'items': items,
		'page': page,
		'per_page': per_page,
		'total_items': total_items,
		'total_pages': total_pages,
	}

# users
def get_user_by_email(db: Session, email: str):
	return db.query(models.User).filter(models.User.email == email).first()

def get_user_by_username(db: Session, username: str):
	return db.query(models.User).filter(models.User.username == username).first()

def get_user(db: Session, user_id: int):
	return db.query(models.User).filter(models.User.id == user_id).first()

def create_user(db: Session, user: UserCreate):
	hashed = hash_password(user.password)
	db_user = models.User(email=user.email, password_hash=hashed, username=getattr(user, 'username', None), display_name=getattr(user, 'display_name', None))
	db.add(db_user)
	db.commit()
	db.refresh(db_user)
	return db_user

def list_users(db: Session, page: int = 1, per_page: int = 50):
	q = db.query(models.User).order_by(models.User.id)
	return paginate_query(q, page, per_page)

# chat

def create_chat(db, chat_create, creator_user=None):
	#If creator is None, the chat is anonymous/temporary chat
	chat = models.Chat(name=chat_create.name, is_private=chat_create.is_private)
	db.add(chat)
	db.commit()
	db.refresh(chat)
	if creator_user:
		participant = models.ChatMember(chat_id=chat.id, user_id=creator_user.id, role="owner")
		db.add(participant)
		db.commit()
	return chat

def add_chat_member(db, chat_id: int, user_id: int, role: str = "member"):
    # avoid duplicates
    exists = db.query(models.ChatMember).filter_by(chat_id=chat_id, user_id=user_id).first()
    if exists:
        return exists
    member = models.ChatMember(chat_id=chat_id, user_id=user_id, role=role)
    db.add(member); db.commit(); db.refresh(member)
    return member

def user_is_participant(db, chat_id: int, user_id: int) -> bool:
    return db.query(models.ChatMember).filter_by(chat_id=chat_id, user_id=user_id).first() is not None

def get_chat(db, chat_id: int):
    return db.query(models.Chat).filter(models.Chat.id == chat_id).first()

def list_chats(db: Session, page: int = 1, per_page: int = 50):
	q = db.query(models.Chat).order_by(models.Chat.id)
	return paginate_query(q, page, per_page)

# messages
def list_messages(db: Session, page: int = 1, per_page: int = 50, user_id: Optional[int]=None, chat_id: Optional[int]=None, q_text: Optional[str]=None, start_date=None, end_date=None):
	q = db.query(models.Message)
	if user_id:
		q = q.filter(models.Message.user_id == user_id)
	if chat_id:
		q = q.filter(models.Message.chat_id == chat_id)
	if q_text:
		q = q.filter(models.Message.content.ilike(f"%{q_text}%"))
	if start_date:
		q = q.filter(models.Message.created_at >= start_date)
	if end_date:
		q = q.filter(models.Message.created_at <= end_date)
	q = q.order_by(models.Message.created_at.desc())
	return paginate_query(q, page, per_page)


def get_message(db: Session, message_id: int):
	return db.query(models.Message).filter(models.Message.id == message_id).first()


def create_message(db: Session, user_id: int, chat_id: int, content: str):
	msg = models.Message(user_id=user_id, chat_id=chat_id, content=content)
	db.add(msg)
	db.commit()
	db.refresh(msg)
	return msg