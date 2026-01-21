"""
MongoDB Base Models.

Provides base classes and utilities for MongoDB documents:
- PyObjectId for MongoDB ObjectId handling
- BaseDocument with common fields
- Serialization helpers
"""
from datetime import datetime
from typing import Any, Optional

from bson import ObjectId
from pydantic import BaseModel, Field, ConfigDict


class PyObjectId(str):
    """
    Custom type for MongoDB ObjectId.
    
    Allows Pydantic to validate and serialize ObjectId fields.
    
    Usage:
        class User(BaseDocument):
            id: Optional[PyObjectId] = Field(default=None, alias="_id")
    """
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, v, info=None):
        if v is None:
            return None
        if isinstance(v, ObjectId):
            return str(v)
        if isinstance(v, str):
            if ObjectId.is_valid(v):
                return v
            raise ValueError(f"Invalid ObjectId: {v}")
        raise TypeError(f"ObjectId or str required, got {type(v)}")
    
    @classmethod
    def __get_pydantic_json_schema__(cls, schema, handler):
        return {"type": "string"}


class BaseDocument(BaseModel):
    """
    Base class for MongoDB documents.
    
    Provides:
    - id field mapped to MongoDB _id
    - Timestamp fields (created_at, updated_at)
    - Soft delete support (is_deleted, deleted_at)
    - Serialization methods
    
    Usage:
        class User(BaseDocument):
            email: str
            name: str
    """
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
        from_attributes=True,
    )
    
    # MongoDB _id field
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Soft delete
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None
    
    def to_mongo(self) -> dict[str, Any]:
        """
        Convert document to MongoDB-compatible dict.
        
        - Converts id to _id
        - Excludes None values
        - Updates updated_at timestamp
        """
        data = self.model_dump(by_alias=True, exclude_none=True)
        
        # Remove id if None (let MongoDB generate)
        if "_id" in data and data["_id"] is None:
            del data["_id"]
        elif "_id" in data:
            data["_id"] = ObjectId(data["_id"])
        
        # Update timestamp
        data["updated_at"] = datetime.utcnow()
        
        return data
    
    def to_insert(self) -> dict[str, Any]:
        """
        Convert document for insertion (excludes _id).
        """
        data = self.to_mongo()
        data.pop("_id", None)
        data["created_at"] = datetime.utcnow()
        data["updated_at"] = datetime.utcnow()
        return data
    
    @classmethod
    def from_mongo(cls, data: dict[str, Any]) -> "BaseDocument":
        """
        Create document instance from MongoDB dict.
        
        Converts _id ObjectId to string.
        """
        if data is None:
            return None
        
        # Convert _id to string
        if "_id" in data:
            data["_id"] = str(data["_id"])
        
        return cls(**data)
    
    def soft_delete(self) -> dict[str, Any]:
        """
        Return update dict for soft delete.
        
        Usage:
            await db.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": user.soft_delete()}
            )
        """
        return {
            "is_deleted": True,
            "deleted_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
    
    def restore(self) -> dict[str, Any]:
        """
        Return update dict for restoring soft-deleted document.
        """
        return {
            "is_deleted": False,
            "deleted_at": None,
            "updated_at": datetime.utcnow(),
        }


class TimestampMixin(BaseModel):
    """Mixin for timestamp fields only."""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SoftDeleteMixin(BaseModel):
    """Mixin for soft delete fields only."""
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None
