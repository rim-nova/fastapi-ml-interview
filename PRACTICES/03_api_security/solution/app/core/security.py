from fastapi import Header, HTTPException
from app.core.config import settings


async def verify_api_key(x_api_key: str = Header(...)):
    """
    Security Dependency: Validates x-api-key header.
    Returns 401 if invalid.
    """
    if x_api_key not in settings.API_KEYS:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API Key"
        )
    return x_api_key
