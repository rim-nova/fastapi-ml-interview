"""
Base Model and Mixins.

Provides common functionality for all database models:
- Automatic table naming
- Timestamp fields (created_at, updated_at)
- Soft delete support
- Serialization helpers
"""
from datetime import datetime
from typing import Any, Dict

from sqlalchemy import Column, Integer, DateTime, Boolean, event
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy models.
    
    Features:
    - Automatic table name generation from class name
    - id primary key column
    - to_dict() method for serialization
    """
    
    # Auto-generate table name from class name (CamelCase to snake_case)
    @declared_attr.directive
    def __tablename__(cls) -> str:
        """Generate table name from class name."""
        name = cls.__name__
        # Convert CamelCase to snake_case
        result = [name[0].lower()]
        for char in name[1:]:
            if char.isupper():
                result.extend(['_', char.lower()])
            else:
                result.append(char)
        return ''.join(result) + 's'  # Pluralize
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model instance to dictionary."""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
    
    def __repr__(self) -> str:
        """String representation of model."""
        return f"<{self.__class__.__name__}(id={self.id})>"


class TimestampMixin:
    """
    Mixin for automatic timestamp management.
    
    Adds:
    - created_at: Set on creation
    - updated_at: Updated on each modification
    """
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )


class SoftDeleteMixin:
    """
    Mixin for soft delete functionality.
    
    Instead of actually deleting records, marks them as deleted.
    
    Adds:
    - is_deleted: Boolean flag
    - deleted_at: Timestamp of deletion
    
    Usage:
        # Soft delete
        item.soft_delete()
        db.commit()
        
        # Restore
        item.restore()
        db.commit()
        
        # Query non-deleted only
        db.query(Item).filter(Item.is_deleted == False).all()
    """
    
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True
    )
    
    deleted_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=True
    )
    
    def soft_delete(self) -> None:
        """Mark record as deleted."""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
    
    def restore(self) -> None:
        """Restore soft-deleted record."""
        self.is_deleted = False
        self.deleted_at = None


class ActiveMixin:
    """
    Mixin for active/inactive status.
    
    Adds:
    - is_active: Boolean flag for active status
    """
    
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True
    )
