from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

ANALYTICS_DB_URL = os.getenv('ANALYTICS_DATABASE_URL', os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5433/analytics_tears'))
engine = create_engine(ANALYTICS_DB_URL, pool_size=5, max_overflow=10, pool_pre_ping=True, pool_recycle=3600)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()