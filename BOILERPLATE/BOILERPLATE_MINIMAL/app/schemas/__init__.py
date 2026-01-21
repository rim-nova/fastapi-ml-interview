"""
Pydantic Schemas.

Export all schemas for easy imports:
    from app.schemas import UserCreate, UserResponse, ItemCreate
"""
from app.schemas.base import (
    BaseSchema,
    TimestampSchema,
    PaginationParams,
    PaginatedResponse,
    SuccessResponse,
    ErrorResponse,
    ErrorDetail,
    MessageResponse,
    IDResponse,
    DeleteResponse,
    HealthCheck,
    DetailedHealthCheck,
)
from app.schemas.user import (
    UserBase,
    UserCreate,
    UserUpdate,
    UserUpdatePassword,
    UserResponse,
    UserInDB,
    LoginRequest,
    Token,
    TokenPayload,
    RefreshTokenRequest,
    PasswordResetRequest,
    PasswordReset,
)
from app.schemas.item import (
    ItemBase,
    ItemCreate,
    ItemUpdate,
    ItemPatch,
    ItemResponse,
    ItemDetail,
    ItemList,
    PaginatedItemResponse,
    ItemQueryParams,
    ItemSortParams,
    ItemBulkCreate,
    ItemBulkUpdate,
    ItemBulkDelete,
    BulkOperationResponse,
)

__all__ = [
    # Base
    "BaseSchema",
    "TimestampSchema",
    "PaginationParams",
    "PaginatedResponse",
    "SuccessResponse",
    "ErrorResponse",
    "ErrorDetail",
    "MessageResponse",
    "IDResponse",
    "DeleteResponse",
    "HealthCheck",
    "DetailedHealthCheck",
    # User
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserUpdatePassword",
    "UserResponse",
    "UserInDB",
    "LoginRequest",
    "Token",
    "TokenPayload",
    "RefreshTokenRequest",
    "PasswordResetRequest",
    "PasswordReset",
    # Item
    "ItemBase",
    "ItemCreate",
    "ItemUpdate",
    "ItemPatch",
    "ItemResponse",
    "ItemDetail",
    "ItemList",
    "PaginatedItemResponse",
    "ItemQueryParams",
    "ItemSortParams",
    "ItemBulkCreate",
    "ItemBulkUpdate",
    "ItemBulkDelete",
    "BulkOperationResponse",
]
