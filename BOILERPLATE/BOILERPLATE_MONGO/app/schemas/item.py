"""
Item Schemas for MongoDB.

Pydantic schemas for Item-related operations.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import Field, field_validator

from app.schemas.base import BaseSchema, TimestampSchema
from app.models.item import ItemStatus, ItemPriority


# =============================================================================
# Item Base Schemas
# =============================================================================
class ItemBase(BaseSchema):
    """Base item schema with common fields."""
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=5000)
    status: ItemStatus = ItemStatus.DRAFT
    priority: ItemPriority = ItemPriority.MEDIUM
    price: Optional[float] = Field(None, ge=0)
    quantity: int = Field(default=1, ge=0)
    metadata: Optional[Dict[str, Any]] = None
    tags: List[str] = Field(default_factory=list)


class ItemCreate(ItemBase):
    """Schema for creating a new item."""
    pass


class ItemUpdate(BaseSchema):
    """Schema for updating an item (all fields optional)."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=5000)
    status: Optional[ItemStatus] = None
    priority: Optional[ItemPriority] = None
    price: Optional[float] = Field(None, ge=0)
    quantity: Optional[int] = Field(None, ge=0)
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None


# =============================================================================
# Item Response Schemas
# =============================================================================
class ItemResponse(ItemBase, TimestampSchema):
    """Schema for item response."""
    id: str = Field(..., alias="_id")
    owner_id: Optional[str] = None
    is_deleted: bool = False
    
    @field_validator("id", mode="before")
    @classmethod
    def convert_objectid(cls, v):
        return str(v) if v else None


class ItemListResponse(BaseSchema):
    """Response for paginated item list."""
    items: List[ItemResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


# =============================================================================
# Bulk Operations
# =============================================================================
class BulkItemCreate(BaseSchema):
    """Schema for bulk item creation."""
    items: List[ItemCreate] = Field(..., min_length=1, max_length=100)


class BulkDeleteRequest(BaseSchema):
    """Request schema for bulk delete."""
    ids: List[str] = Field(..., min_length=1, max_length=100)


class BulkDeleteResponse(BaseSchema):
    """Response schema for bulk delete."""
    deleted_count: int
    deleted_ids: List[str]
    failed_ids: List[str] = []
