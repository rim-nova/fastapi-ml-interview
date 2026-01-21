"""
Application Configuration.

Uses Pydantic Settings for environment variable management.
MongoDB-specific settings included.
"""
from functools import lru_cache
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # =========================================================================
    # Application
    # =========================================================================
    APP_NAME: str = "FastAPI MongoDB App"
    APP_DESCRIPTION: str = "Production-ready FastAPI with MongoDB"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = True
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # =========================================================================
    # MongoDB Configuration
    # =========================================================================
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "fastapi_db"
    
    # Connection Pool Settings
    MONGODB_MIN_POOL_SIZE: int = 1
    MONGODB_MAX_POOL_SIZE: int = 10
    MONGODB_MAX_IDLE_TIME_MS: int = 30000
    
    # =========================================================================
    # Security
    # =========================================================================
    SECRET_KEY: str = "your-super-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Password
    PASSWORD_MIN_LENGTH: int = 8
    BCRYPT_ROUNDS: int = 12
    
    # API Keys
    API_KEY_HEADER: str = "X-API-Key"
    API_KEYS: str = ""
    
    @property
    def api_keys_list(self) -> List[str]:
        """Parse API keys from comma-separated string."""
        if not self.API_KEYS:
            return []
        return [k.strip() for k in self.API_KEYS.split(",") if k.strip()]
    
    # =========================================================================
    # CORS
    # =========================================================================
    CORS_ORIGINS: str = '["http://localhost:3000","http://localhost:8080"]'
    CORS_ALLOW_METHODS: str = '["*"]'
    CORS_ALLOW_HEADERS: str = "*"
    CORS_ALLOW_CREDENTIALS: bool = True
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from JSON string."""
        import json
        try:
            return json.loads(self.CORS_ORIGINS)
        except json.JSONDecodeError:
            return ["*"]
    
    @property
    def cors_methods_list(self) -> List[str]:
        """Parse CORS methods from JSON string."""
        import json
        try:
            return json.loads(self.CORS_ALLOW_METHODS)
        except json.JSONDecodeError:
            return ["*"]
    
    # =========================================================================
    # Rate Limiting
    # =========================================================================
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    
    # =========================================================================
    # API Documentation
    # =========================================================================
    DOCS_URL: str = "/docs"
    REDOC_URL: str = "/redoc"
    OPENAPI_URL: str = "/openapi.json"
    API_V1_PREFIX: str = "/api/v1"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
