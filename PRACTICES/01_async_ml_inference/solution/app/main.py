import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.session import create_tables, engine
from app.routers import inference  # Import the new router

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Handle startup and shutdown events.
    """
    # Startup: Create tables
    logger.info("Initializing database tables...")
    create_tables()
    logger.info("Database ready.")
    yield
    # Shutdown: Clean up resources
    logger.info("Shutting down...")
    engine.dispose()


# --- APP INITIALIZATION ---
app = FastAPI(
    title="Sentiment Analysis Engine",
    description="Asynchronous ML Inference API with background processing.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
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
    inference.router,
    prefix="/api/v1",
    tags=["Inference"]
)


# --- HEALTH CHECK ---
@app.get("/health", tags=["System"])
def health_check():
    return {"status": "healthy", "service": "async-ml-inference"}
