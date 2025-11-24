from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func, Boolean
from sqlalchemy.orm import relationship
from .database import Base

# user

class User(Base):
	__tablename__ = 'users'
	id = Column(Integer, primary_key=True, index=True)
	username = Column(String(64), unique=True, index=True, nullable=False)
	display_name = Column(String(128))
	email = Column(String(256), unique=True, index=True, nullable=False)
	password_hash = Column(String, nullable=False)
	is_active = Column(Boolean, default=True)
	created_at = Column(DateTime(timezone=True), server_default=func.now())

# chat

class Chat(Base):
	__tablename__ = 'chats'
	id = Column(Integer, primary_key=True, index=True)
	name = Column(String(128), index=True, nullable=False)
	is_private = Column(Boolean, default=False)
	created_at = Column(DateTime(timezone=True), server_default=func.now())

class ChatMember(Base):
	__tablename__ = 'chat_members'
	id = Column(Integer, primary_key=True, index=True)
	chat_id = Column(Integer, ForeignKey('chats.id'), index=True, nullable=False)
	user_id = Column(Integer, ForeignKey('users.id'), index=True, nullable=False)
	role = Column(String(20), default="member", nullable=False)
	joined_at = Column(DateTime(timezone=True), server_default=func.now())

	user = relationship('User')
	chat = relationship('Chat')	

# message

class Message(Base):
	__tablename__ = 'messages'
	id = Column(Integer, primary_key=True, index=True)
	chat_id = Column(Integer, ForeignKey('chats.id'), index=True, nullable=False)
	user_id = Column(Integer, ForeignKey('users.id'), index=True, nullable=False)
	content = Column(Text, nullable=False)
	created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

	user = relationship('User')
	chat = relationship('Chat')