"""
Shared pytest configuration and fixtures
This file ensures models are imported before any tests run
"""
# Import models to register them with Base.metadata
# This MUST happen before any test tries to create tables
from app.models import User, Chat, ChatMember, Message  # noqa: F401
