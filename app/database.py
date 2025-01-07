from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pathlib import Path
import os

# Default database path
DEFAULT_DB_PATH = os.getenv("DB_PATH")


def get_engine(db_path: Path = DEFAULT_DB_PATH):
    """Get SQLAlchemy engine for the given database path."""
    database_url = f"sqlite:///{db_path}"
    return create_engine(database_url, connect_args={"check_same_thread": False})


# These will be initialized when init_db is called
engine = None
SessionLocal = None


def get_db():
    """Dependency to get a database session."""
    if SessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_db first.")

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(db_path: Path = DEFAULT_DB_PATH):
    """Initialize database with a specific path.

    Creates the database file and parent directories if they don't exist.

    :param db_path: Path to the SQLite database file
    """
    global engine, SessionLocal

    # Create parent directories if they don't exist
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Create engine and session maker
    engine = get_engine(db_path)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Import and create tables
    from .models import Base

    Base.metadata.create_all(bind=engine)

    print(f"Database initialized at: {db_path.absolute()}")
