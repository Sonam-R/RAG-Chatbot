from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# SQLite database file in the backend directory
engine = create_engine("sqlite:///./app.db", connect_args={"check_same_thread": False})

# Session factory
SessionLocal = sessionmaker(bind=engine, autoflush=False)

# Base class for declarative models
class Base(DeclarativeBase):
    pass
