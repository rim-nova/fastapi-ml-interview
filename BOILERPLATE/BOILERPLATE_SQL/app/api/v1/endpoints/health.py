"""
Health check endpoints for monitoring and load balancer probes.
"""
from datetime import datetime
from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.session import get_db

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }


class DetailedHealthResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str
    database: str
    uptime_seconds: float | None = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2024-01-15T10:30:00Z",
                "version": "1.0.0",
                "database": "connected",
                "uptime_seconds": 3600.5
            }
        }


# Track application start time
_start_time = datetime.utcnow()


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Basic health check",
    description="Simple health check for load balancers and basic monitoring."
)
async def health_check():
    """
    Basic health check endpoint.
    Returns 200 OK if the application is running.
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow()
    )


@router.get(
    "/health/ready",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Readiness check",
    description="Check if the application is ready to accept traffic."
)
async def readiness_check(db: Session = Depends(get_db)):
    """
    Readiness check - verifies database connectivity.
    Use this for Kubernetes readiness probes.
    """
    try:
        # Test database connection
        db.execute(text("SELECT 1"))
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
    description="Comprehensive health check with component status."
)
async def detailed_health_check(db: Session = Depends(get_db)):
    """
    Detailed health check with database status and uptime.
    Useful for monitoring dashboards.
    """
    # Check database
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
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
