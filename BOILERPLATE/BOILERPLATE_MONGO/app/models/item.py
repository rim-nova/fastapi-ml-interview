"""
Item Document Model for MongoDB.

A generic item model that can be adapted for various use cases.
"""
from enum import Enum
from typing import Any, Optional

from pydantic import Field

from app.models.base import BaseDocument, PyObjectId


class ItemStatus(str, Enum):
    """Item status enumeration."""
    DRAFT = "draft"
    PENDING = "pending"
    ACTIVE = "active"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    FAILED = "failed"


class ItemPriority(str, Enum):
    """Item priority enumeration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class ItemDocument(BaseDocument):
    """
    Item document for MongoDB.
    
    Collection: items
    
    Indexes:
        - title (text index for search)
        - status
        - owner_id
        - is_deleted
        - created_at
        - (owner_id, status) compound
    """
    
    __collection__ = "items"
    
    # Basic fields
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    
    # Status and priority
    status: ItemStatus = ItemStatus.DRAFT
    priority: ItemPriority = ItemPriority.MEDIUM
    
    # Numeric fields
    price: Optional[float] = Field(default=None, ge=0)
    quantity: int = Field(default=1, ge=0)
    
    # Flexible metadata (MongoDB's strength!)
    metadata: Optional[dict[str, Any]] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    
    # Owner reference (stored as string, not ObjectId reference)
    owner_id: Optional[str] = None
    
    @classmethod
    def collection_name(cls) -> str:
        """Get the collection name."""
        return cls.__collection__
    
    @property
    def is_active(self) -> bool:
        """Check if item is in an active state."""
        return self.status in [ItemStatus.ACTIVE, ItemStatus.PROCESSING]
    
    @property
    def is_completed(self) -> bool:
        """Check if item is completed."""
        return self.status == ItemStatus.COMPLETED
