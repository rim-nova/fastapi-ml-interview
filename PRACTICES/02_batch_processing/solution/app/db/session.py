from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.pool import QueuePool
from app.config import settings


# 1. Engine Configuration
def get_engine_args():
    return {
        "poolclass": QueuePool,
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
        "echo": settings.DB_ECHO
    }


engine = create_engine(settings.DATABASE_URL, **get_engine_args())

# 2. Session Factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 3. Model Base
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
    # Import models here to avoid circular imports at the top level
    from app import models
    Base.metadata.create_all(bind=engine)
