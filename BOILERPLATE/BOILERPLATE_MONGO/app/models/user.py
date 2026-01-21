"""
User Document Model for MongoDB.

Represents user accounts in the users collection.
"""
from typing import Optional

from pydantic import EmailStr, Field

from app.models.base import BaseDocument


class UserDocument(BaseDocument):
    """
    User document for MongoDB.
    
    Collection: users
    
    Indexes:
        - email (unique)
        - is_deleted
        - created_at
    """
    
    # Collection name (for reference)
    __collection__ = "users"
    
    # User fields
    email: EmailStr
    hashed_password: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    
    # Status flags
    is_active: bool = True
    is_verified: bool = False
    is_superuser: bool = False
    
    @classmethod
    def collection_name(cls) -> str:
        """Get the collection name."""
        return cls.__collection__


class UserInDB(UserDocument):
    """User document with all database fields."""
    pass


class UserPublic(BaseDocument):
    """User document for public responses (no password)."""
    email: EmailStr
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    is_active: bool = True
    is_verified: bool = False
