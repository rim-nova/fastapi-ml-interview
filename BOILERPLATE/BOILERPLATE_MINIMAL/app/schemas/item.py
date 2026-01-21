"""
Item Schemas.

Pydantic schemas for Item-related operations:
- Create
- Update
- Query filters
- Responses
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import Field, field_validator

from app.schemas.base import BaseSchema, TimestampSchema, PaginatedResponse
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


class ItemPatch(BaseSchema):
    """Schema for partial item update."""
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[ItemStatus] = None
    priority: Optional[ItemPriority] = None


# =============================================================================
# Item Response Schemas
# =============================================================================
class ItemResponse(ItemBase, TimestampSchema):
    """Schema for item response."""
    id: int
    owner_id: Optional[int] = None
    is_deleted: bool = False


class ItemDetail(ItemResponse):
    """Detailed item response with additional data."""
    # Add related data here if needed
    # owner: Optional[UserResponse] = None
    pass


class ItemList(BaseSchema):
    """Schema for item list response."""
    items: List[ItemResponse]
    total: int


# Paginated item response
class PaginatedItemResponse(PaginatedResponse[ItemResponse]):
    """Paginated list of items."""
    pass


# =============================================================================
# Item Query Schemas
# =============================================================================
class ItemQueryParams(BaseSchema):
    """Query parameters for filtering items."""
    status: Optional[ItemStatus] = None
    priority: Optional[ItemPriority] = None
    min_price: Optional[float] = Field(None, ge=0)
    max_price: Optional[float] = Field(None, ge=0)
    search: Optional[str] = Field(None, max_length=100)
    owner_id: Optional[int] = None
    
    @field_validator("search")
    @classmethod
    def sanitize_search(cls, v: Optional[str]) -> Optional[str]:
        """Sanitize search query."""
        if v:
            return v.strip()
        return v


class ItemSortParams(BaseSchema):
    """Sort parameters for items."""
    sort_by: str = Field(default="created_at", pattern="^(id|title|created_at|updated_at|price|priority)$")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")


# =============================================================================
# Bulk Operations
# =============================================================================
class ItemBulkCreate(BaseSchema):
    """Schema for bulk item creation."""
    items: List[ItemCreate] = Field(..., min_length=1, max_length=100)


class ItemBulkUpdate(BaseSchema):
    """Schema for bulk item update."""
    ids: List[int] = Field(..., min_length=1, max_length=100)
    update: ItemUpdate


class ItemBulkDelete(BaseSchema):
    """Schema for bulk item deletion."""
    ids: List[int] = Field(..., min_length=1, max_length=100)


class BulkOperationResponse(BaseSchema):
    """Response for bulk operations."""
    success: bool = True
    affected_count: int
    message: str


# =============================================================================
# Aliases for endpoint compatibility
# =============================================================================
class ItemListResponse(BaseSchema):
    """Response for paginated item list."""
    items: List[ItemResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


# Aliases
BulkItemCreate = ItemBulkCreate


class BulkDeleteRequest(BaseSchema):
    """Request schema for bulk delete."""
    ids: List[int] = Field(..., min_length=1, max_length=100)


class BulkDeleteResponse(BaseSchema):
    """Response schema for bulk delete."""
    deleted_count: int
    deleted_ids: List[int]
    failed_ids: List[int] = []
