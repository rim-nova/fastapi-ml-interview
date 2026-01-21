"""
Database Session Management.

Supports multiple database backends:
- SQLite (default, for development/testing)
- PostgreSQL (recommended for production)
- MySQL (alternative for production)

Usage:
    from app.db.session import get_db, SessionLocal
    
    # In FastAPI endpoints
    @app.get("/items")
    def get_items(db: Session = Depends(get_db)):
        return db.query(Item).all()
"""
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool, QueuePool

from app.config import settings


# =============================================================================
# Engine Configuration
# =============================================================================
def get_engine_args():
    """
    Get database engine arguments based on database type.
    
    SQLite requires special handling for:
    - Same thread checking
    - Connection pooling
    
    PostgreSQL/MySQL use connection pooling for performance.
    """
    database_url = settings.get_database_url()
    
    # SQLite configuration
    if database_url.startswith("sqlite"):
        return {
            "connect_args": {"check_same_thread": False},
            "poolclass": StaticPool,
            "echo": settings.DB_ECHO
        }
    
    # PostgreSQL/MySQL configuration
    return {
        "poolclass": QueuePool,
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
        "pool_timeout": settings.DB_POOL_TIMEOUT,
        "pool_recycle": settings.DB_POOL_RECYCLE,
        "pool_pre_ping": True,  # Verify connection before using
        "echo": settings.DB_ECHO
    }


# Create engine
engine = create_engine(
    settings.get_database_url(),
    **get_engine_args()
)


# =============================================================================
# Session Factory
# =============================================================================
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


# =============================================================================
# Database Dependency
# =============================================================================
def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency for FastAPI.
    
    Usage:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    
    The session is automatically closed after the request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =============================================================================
# Table Creation
# =============================================================================
def create_tables():
    """
    Create all database tables.
    
    Called during application startup.
    In production, use Alembic migrations instead.
    """
    from app.models.base import Base
    # Import all models to register them with Base
    from app.models import user, item  # noqa: F401
    
    Base.metadata.create_all(bind=engine)


def drop_tables():
    """
    Drop all database tables.
    
    USE WITH CAUTION - Only for testing/development.
    """
    from app.models.base import Base
    Base.metadata.drop_all(bind=engine)


# =============================================================================
# Optional: Slow Query Logging
# =============================================================================
if settings.DEBUG:
    import time
    import logging
    
    logger = logging.getLogger("sqlalchemy.slow_queries")
    SLOW_QUERY_THRESHOLD = 1.0  # seconds
    
    @event.listens_for(engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        conn.info.setdefault("query_start_time", []).append(time.time())
    
    @event.listens_for(engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        total_time = time.time() - conn.info["query_start_time"].pop(-1)
        if total_time > SLOW_QUERY_THRESHOLD:
            logger.warning(f"Slow query ({total_time:.2f}s): {statement[:200]}...")
