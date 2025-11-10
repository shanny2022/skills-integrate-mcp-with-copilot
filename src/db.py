import os
from sqlmodel import SQLModel, create_engine, Session

# Simple DB configuration for local development. Uses file-based SQLite by default.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data.db")

# Create SQLModel engine
engine = create_engine(DATABASE_URL, echo=False)


def init_db() -> None:
    """Create database tables."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Session:
    """Return a new Session. Use as a context manager: `with get_session() as session:`"""
    return Session(engine)
