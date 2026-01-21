"""
Custom Exceptions.

Provides custom exception classes for consistent error handling:
- APIException: Base exception with error code and details
- Specific exceptions for common scenarios (NotFound, Unauthorized, etc.)
"""
from typing import Any, Optional


class APIException(Exception):
    """
    Base API exception.
    
    All custom exceptions should inherit from this class.
    
    Attributes:
        status_code: HTTP status code
        error_code: Machine-readable error code
        message: Human-readable error message
        details: Additional error details
    
    Usage:
        raise APIException(
            status_code=400,
            error_code="VALIDATION_ERROR",
            message="Invalid input data",
            details={"field": "email", "error": "Invalid format"}
        )
    """
    
    def __init__(
        self,
        status_code: int,
        error_code: str,
        message: str,
        details: Optional[Any] = None
    ):
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        self.details = details
        super().__init__(message)


# =============================================================================
# 400 Bad Request Exceptions
# =============================================================================
class BadRequestException(APIException):
    """400 Bad Request - Invalid client request."""
    
    def __init__(
        self,
        message: str = "Bad request",
        error_code: str = "BAD_REQUEST",
        details: Optional[Any] = None
    ):
        super().__init__(
            status_code=400,
            error_code=error_code,
            message=message,
            details=details
        )


class ValidationException(APIException):
    """400 Bad Request - Validation error."""
    
    def __init__(
        self,
        message: str = "Validation error",
        details: Optional[Any] = None
    ):
        super().__init__(
            status_code=400,
            error_code="VALIDATION_ERROR",
            message=message,
            details=details
        )


# =============================================================================
# 401 Unauthorized Exceptions
# =============================================================================
class UnauthorizedException(APIException):
    """401 Unauthorized - Authentication required."""
    
    def __init__(
        self,
        message: str = "Authentication required",
        error_code: str = "UNAUTHORIZED",
        details: Optional[Any] = None
    ):
        super().__init__(
            status_code=401,
            error_code=error_code,
            message=message,
            details=details
        )


class InvalidCredentialsException(APIException):
    """401 Unauthorized - Invalid login credentials."""
    
    def __init__(self, message: str = "Invalid email or password"):
        super().__init__(
            status_code=401,
            error_code="INVALID_CREDENTIALS",
            message=message,
            details=None
        )


class TokenExpiredException(APIException):
    """401 Unauthorized - Token has expired."""
    
    def __init__(self, message: str = "Token has expired"):
        super().__init__(
            status_code=401,
            error_code="TOKEN_EXPIRED",
            message=message,
            details=None
        )


# =============================================================================
# 403 Forbidden Exceptions
# =============================================================================
class ForbiddenException(APIException):
    """403 Forbidden - Access denied."""
    
    def __init__(
        self,
        message: str = "Access denied",
        error_code: str = "FORBIDDEN",
        details: Optional[Any] = None
    ):
        super().__init__(
            status_code=403,
            error_code=error_code,
            message=message,
            details=details
        )


class InsufficientPermissionsException(APIException):
    """403 Forbidden - Insufficient permissions."""
    
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(
            status_code=403,
            error_code="INSUFFICIENT_PERMISSIONS",
            message=message,
            details=None
        )


# =============================================================================
# 404 Not Found Exceptions
# =============================================================================
class NotFoundException(APIException):
    """404 Not Found - Resource not found."""
    
    def __init__(
        self,
        message: str = "Resource not found",
        error_code: str = "NOT_FOUND",
        details: Optional[Any] = None
    ):
        super().__init__(
            status_code=404,
            error_code=error_code,
            message=message,
            details=details
        )


class UserNotFoundException(APIException):
    """404 Not Found - User not found."""
    
    def __init__(self, message: str = "User not found"):
        super().__init__(
            status_code=404,
            error_code="USER_NOT_FOUND",
            message=message,
            details=None
        )


class ItemNotFoundException(APIException):
    """404 Not Found - Item not found."""
    
    def __init__(self, message: str = "Item not found"):
        super().__init__(
            status_code=404,
            error_code="ITEM_NOT_FOUND",
            message=message,
            details=None
        )


# =============================================================================
# 409 Conflict Exceptions
# =============================================================================
class ConflictException(APIException):
    """409 Conflict - Resource conflict."""
    
    def __init__(
        self,
        message: str = "Resource conflict",
        error_code: str = "CONFLICT",
        details: Optional[Any] = None
    ):
        super().__init__(
            status_code=409,
            error_code=error_code,
            message=message,
            details=details
        )


class DuplicateException(APIException):
    """409 Conflict - Duplicate resource."""
    
    def __init__(self, message: str = "Resource already exists"):
        super().__init__(
            status_code=409,
            error_code="DUPLICATE",
            message=message,
            details=None
        )


class EmailAlreadyExistsException(APIException):
    """409 Conflict - Email already registered."""
    
    def __init__(self, message: str = "Email already registered"):
        super().__init__(
            status_code=409,
            error_code="EMAIL_EXISTS",
            message=message,
            details=None
        )


# =============================================================================
# 429 Too Many Requests Exceptions
# =============================================================================
class RateLimitExceededException(APIException):
    """429 Too Many Requests - Rate limit exceeded."""
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None
    ):
        details = {"retry_after": retry_after} if retry_after else None
        super().__init__(
            status_code=429,
            error_code="RATE_LIMIT_EXCEEDED",
            message=message,
            details=details
        )


# =============================================================================
# 500 Internal Server Error Exceptions
# =============================================================================
class InternalServerException(APIException):
    """500 Internal Server Error - Unexpected error."""
    
    def __init__(
        self,
        message: str = "Internal server error",
        error_code: str = "INTERNAL_ERROR",
        details: Optional[Any] = None
    ):
        super().__init__(
            status_code=500,
            error_code=error_code,
            message=message,
            details=details
        )


class DatabaseException(APIException):
    """500 Internal Server Error - Database error."""
    
    def __init__(self, message: str = "Database error"):
        super().__init__(
            status_code=500,
            error_code="DATABASE_ERROR",
            message=message,
            details=None
        )


# =============================================================================
# 503 Service Unavailable Exceptions
# =============================================================================
class ServiceUnavailableException(APIException):
    """503 Service Unavailable - Service temporarily unavailable."""
    
    def __init__(
        self,
        message: str = "Service temporarily unavailable",
        error_code: str = "SERVICE_UNAVAILABLE",
        details: Optional[Any] = None
    ):
        super().__init__(
            status_code=503,
            error_code=error_code,
            message=message,
            details=details
        )
