from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.pool import StaticPool, QueuePool
from app.config import settings


# 1. Engine Configuration
def get_engine_args():
    database_url = settings.get_database_url()
    if database_url.startswith("sqlite"):
        return {
            "connect_args": {"check_same_thread": False},
            "poolclass": StaticPool,
            "echo": settings.DB_ECHO
        }
    return {
        "poolclass": QueuePool,
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
        "echo": settings.DB_ECHO
    }


engine = create_engine(settings.get_database_url(), **get_engine_args())

# 2. Session Factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 3. Model Base (THIS WAS MISSING)
Base = declarative_base()


# 4. Dependency
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 5. Table Creation Helper
def create_tables():
    # Import models here to ensure they are registered with Base before creation
    from app import models
    Base.metadata.create_all(bind=engine)
