import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl, PostgresDsn, field_validator
from typing import List, Union, Set


class Settings(BaseSettings):
    PROJECT_NAME: str = "Secure ML API"

    # 1. Add these fields to match your .env file
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str

    # Database URL
    DATABASE_URL: PostgresDsn = os.getenv(
        "DATABASE_URL",
        "postgresql://user:password@db:5432/ml_db"
    )

    # Security
    API_KEYS: Set[str] = {
        "user-key-1",
        "user-key-2",
        "test-secret-key"
    }

    RATE_LIMIT_PER_MINUTE: int = 5

    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # 2. Configuration to handle extra env vars safely
    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        extra="ignore"
    )


settings = Settings()
