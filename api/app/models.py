from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func, Boolean
from sqlalchemy.orm import relationship
from .database import Base

class user(Base):
	__tablename__ = 'users'
	id = Column(Integer, primary_key=True, index=True)
	username = Column(String(64), unique=True, index=True, nullable=False)
	display_name = Column(String(128))
	email = Column(String(256), unique=True, index=True)
	created_at = Column(DateTime(timezone=True), server_default=func.now())

class chat(Base):
	__tablename__ = 'channels'
	id = Column(Integer, primary_key=True, index=True)
	name = Column(String(128), index=True, nullable=False)
	is_private = Column(Boolean, default=False)
	created_at = Column(DateTime(timezone=True), server_default=func.now())

class message(Base):
	__tablename__ = 'messages'
	id = Column(Integer, primary_key=True, index=True)
	channel_id = Column(Integer, ForeignKey('channels.id'), index=True, nullable=False)
	user_id = Column(Integer, ForeignKey('users.id'), index=True, nullable=False)
	content = Column(Text, nullable=False)
	created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

	user = relationship('User')
	channel = relationship('Channel')