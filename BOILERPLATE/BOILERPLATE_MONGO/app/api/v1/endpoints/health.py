"""
Health check endpoints for MongoDB.
"""
from datetime import datetime
from fastapi import APIRouter, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from app.db.mongodb import get_database

router = APIRouter(tags=["Health"])

# Track application start time
_start_time = datetime.utcnow()


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime


class DetailedHealthResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str
    database: str
    uptime_seconds: float


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Basic health check",
)
async def health_check():
    """Basic health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow()
    )


@router.get(
    "/health/ready",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Readiness check",
)
async def readiness_check(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Readiness check - verifies MongoDB connectivity."""
    try:
        # Ping MongoDB
        await db.command("ping")
        return HealthResponse(
            status="ready",
            timestamp=datetime.utcnow()
        )
    except Exception:
        return HealthResponse(
            status="not_ready",
            timestamp=datetime.utcnow()
        )


@router.get(
    "/health/detailed",
    response_model=DetailedHealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Detailed health check",
)
async def detailed_health_check(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Detailed health check with database status and uptime."""
    # Check database
    db_status = "connected"
    try:
        await db.command("ping")
    except Exception:
        db_status = "disconnected"
    
    # Calculate uptime
    uptime = (datetime.utcnow() - _start_time).total_seconds()
    
    overall_status = "healthy" if db_status == "connected" else "degraded"
    
    return DetailedHealthResponse(
        status=overall_status,
        timestamp=datetime.utcnow(),
        version="1.0.0",
        database=db_status,
        uptime_seconds=uptime
    )
