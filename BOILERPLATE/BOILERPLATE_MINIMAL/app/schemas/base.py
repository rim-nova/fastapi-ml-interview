"""
Base Schemas.

Provides common schema patterns:
- Base schema with ORM mode
- Pagination parameters
- Standard response wrappers
- Error responses
"""
from datetime import datetime
from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field


# =============================================================================
# Base Schema Configuration
# =============================================================================
class BaseSchema(BaseModel):
    """
    Base schema with common configuration.
    
    All schemas should inherit from this.
    """
    model_config = ConfigDict(
        from_attributes=True,  # Allow ORM model conversion
        populate_by_name=True,  # Allow field aliases
        str_strip_whitespace=True,  # Strip whitespace from strings
    )


class TimestampSchema(BaseSchema):
    """Schema mixin for timestamp fields."""
    created_at: datetime
    updated_at: datetime


# =============================================================================
# Pagination
# =============================================================================
class PaginationParams(BaseModel):
    """
    Pagination query parameters.
    
    Usage in endpoint:
        @app.get("/items")
        def list_items(pagination: PaginationParams = Depends()):
            skip = pagination.skip
            limit = pagination.limit
    """
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")
    
    @property
    def skip(self) -> int:
        """Calculate offset for database query."""
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        """Alias for page_size."""
        return self.page_size


# Generic type for paginated items
T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Paginated response wrapper.
    
    Usage:
        return PaginatedResponse(
            items=items,
            total=total_count,
            page=page,
            page_size=page_size
        )
    """
    items: List[T]
    total: int
    page: int
    page_size: int
    pages: int = 0
    
    def __init__(self, **data):
        super().__init__(**data)
        # Calculate total pages
        if self.page_size > 0:
            self.pages = (self.total + self.page_size - 1) // self.page_size
    
    @property
    def has_next(self) -> bool:
        """Check if there's a next page."""
        return self.page < self.pages
    
    @property
    def has_prev(self) -> bool:
        """Check if there's a previous page."""
        return self.page > 1


# =============================================================================
# Standard Responses
# =============================================================================
class SuccessResponse(BaseModel):
    """Standard success response."""
    success: bool = True
    message: str = "Operation successful"
    data: Optional[Any] = None


class ErrorDetail(BaseModel):
    """Error detail structure."""
    code: str
    message: str
    details: Optional[Any] = None


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: ErrorDetail


class MessageResponse(BaseModel):
    """Simple message response."""
    message: str


class IDResponse(BaseModel):
    """Response with just an ID."""
    id: int


class DeleteResponse(BaseModel):
    """Response for delete operations."""
    deleted: bool = True
    id: int


# =============================================================================
# Health Check
# =============================================================================
class HealthCheck(BaseModel):
    """Health check response."""
    status: str = "healthy"
    version: Optional[str] = None
    database: Optional[str] = None


class DetailedHealthCheck(BaseModel):
    """Detailed health check with component status."""
    status: str
    components: dict[str, dict[str, Any]]
    uptime_seconds: float
