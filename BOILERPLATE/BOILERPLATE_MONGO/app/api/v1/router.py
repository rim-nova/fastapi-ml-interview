"""
API v1 router - aggregates all endpoint routers.
"""
from fastapi import APIRouter

from app.api.v1.endpoints import health, auth, items

# Create main API router
api_router = APIRouter()

# Include endpoint routers
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(items.router)
