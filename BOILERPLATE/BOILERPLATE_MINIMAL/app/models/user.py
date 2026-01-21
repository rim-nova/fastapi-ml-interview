"""
User Model.

Defines the User database model with:
- Authentication fields (email, password hash)
- Profile fields (name, avatar)
- Status fields (is_active, is_superuser)
- Timestamps
"""
from typing import Optional

from sqlalchemy import String, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, SoftDeleteMixin


class User(Base, TimestampMixin, SoftDeleteMixin):
    """
    User model for authentication and profile data.
    
    Table: users
    
    Attributes:
        email: Unique email address (used for login)
        hashed_password: Bcrypt hashed password
        full_name: User's display name
        is_active: Whether the user can login
        is_superuser: Admin privileges
        is_verified: Email verification status
    """
    
    # Authentication fields
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    
    # Profile fields
    full_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    avatar_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True
    )
    bio: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    
    # Status fields
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )
    is_superuser: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    
    # Relationships (uncomment when Item model has user_id)
    # items: Mapped[list["Item"]] = relationship("Item", back_populates="owner")
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email})>"
    
    @property
    def display_name(self) -> str:
        """Return display name or email prefix."""
        return self.full_name or self.email.split("@")[0]
