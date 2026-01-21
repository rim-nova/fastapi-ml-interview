import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.session import create_tables, engine
from app.routers import batch  # Import our new router

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Handle startup and shutdown events."""
    logger.info("Initializing database tables...")
    create_tables()  # Assuming this helper exists in db/session.py
    logger.info("Database ready.")
    yield
    logger.info("Shutting down resources...")
    engine.dispose()


# --- APP INITIALIZATION ---
app = FastAPI(
    title="Batch Processing Engine",
    description="High-performance CSV processing API",
    version="1.0.0",
    lifespan=lifespan
)

# --- MIDDLEWARE ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- REGISTER ROUTERS ---
app.include_router(
    batch.router,
    prefix="/batch",
    tags=["Batch Processing"]
)


@app.get("/health", tags=["System"])
def health_check():
    return {"status": "healthy", "service": "batch-processor"}
