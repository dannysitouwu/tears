from sqlalchemy.orm import Session
from . import models
from typing import List, Optional
from sqlalchemy import func

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
def list_users(db: Session, page: int = 1, per_page: int = 50):
	q = db.query(models.User).order_by(models.User.id)
	return paginate_query(q, page, per_page)

# chat
def list_chats(db: Session, page: int = 1, per_page: int = 50):
	q = db.query(models.chat).order_by(models.chat.id)
	return paginate_query(q, page, per_page)

# messages
def list_messages(db: Session, page: int = 1, per_page: int = 50, user_id: Optional[int]=None, channel_id: Optional[int]=None, q_text: Optional[str]=None, start_date=None, end_date=None):
	q = db.query(models.message)
	if user_id:
		q = q.filter(models.message.user_id == user_id)
	if channel_id:
		q = q.filter(models.message.channel_id == channel_id)
	if q_text:
		q = q.filter(models.message.content.ilike(f"%{q_text}%"))
	if start_date:
		q = q.filter(models.message.created_at >= start_date)
	if end_date:
		q = q.filter(models.message.created_at <= end_date)
	q = q.order_by(models.message.created_at.desc())
	return paginate_query(q, page, per_page)


def get_message(db: Session, message_id: int):
	return db.query(models.message).filter(models.message.id == message_id).first()


def create_message(db: Session, user_id: int, channel_id: int, content: str):
	msg = models.message(user_id=user_id, channel_id=channel_id, content=content)
	db.add(msg)
	db.commit()
	db.refresh(msg)
	return msg