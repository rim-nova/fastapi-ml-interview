"""
Item Model.

A generic item model that can be adapted for various use cases:
- Products in e-commerce
- Tasks in task management
- Posts in social media
- Jobs in ML pipelines

Modify this model based on your specific requirements.
"""
from typing import Optional
from enum import Enum as PyEnum

from sqlalchemy import String, Text, Float, Integer, Enum, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, SoftDeleteMixin


class ItemStatus(str, PyEnum):
    """Item status enumeration."""
    DRAFT = "draft"
    PENDING = "pending"
    ACTIVE = "active"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    FAILED = "failed"


class ItemPriority(str, PyEnum):
    """Item priority enumeration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Item(Base, TimestampMixin, SoftDeleteMixin):
    """
    Generic Item model.
    
    Table: items
    
    This model includes common fields found in many applications.
    Adapt it to your specific needs by:
    - Renaming fields
    - Adding/removing fields
    - Changing data types
    
    Attributes:
        title: Item title/name
        description: Detailed description
        status: Current status (draft, pending, active, etc.)
        priority: Priority level
        price: Numeric value (for products, scores, etc.)
        quantity: Integer count
        metadata: JSON field for flexible data
        owner_id: Foreign key to User
    """
    
    # Basic fields
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    
    # Status and priority
    status: Mapped[ItemStatus] = mapped_column(
        Enum(ItemStatus),
        default=ItemStatus.DRAFT,
        nullable=False,
        index=True
    )
    priority: Mapped[ItemPriority] = mapped_column(
        Enum(ItemPriority),
        default=ItemPriority.MEDIUM,
        nullable=False
    )
    
    # Numeric fields (adapt naming for your use case)
    price: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True
    )
    quantity: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False
    )
    
    # Flexible JSON field for additional data
    # Use for: tags, settings, results, metadata, etc.
    metadata: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        default=dict
    )
    
    # Owner relationship (optional)
    owner_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Uncomment to enable relationship
    # owner: Mapped[Optional["User"]] = relationship("User", back_populates="items")
    
    def __repr__(self) -> str:
        return f"<Item(id={self.id}, title={self.title}, status={self.status})>"
    
    @property
    def is_active(self) -> bool:
        """Check if item is in an active state."""
        return self.status in [ItemStatus.ACTIVE, ItemStatus.PROCESSING]
    
    @property
    def is_completed(self) -> bool:
        """Check if item is completed."""
        return self.status == ItemStatus.COMPLETED
