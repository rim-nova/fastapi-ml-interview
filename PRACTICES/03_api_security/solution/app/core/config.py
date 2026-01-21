import os
from pydantic import AnyHttpUrl, validator, PostgresDsn
from pydantic_settings import BaseSettings
from typing import List, Union, Set


class Settings(BaseSettings):
    PROJECT_NAME: str = "Secure ML API"

    # Database
    # Uses PostgresDsn for validation
    DATABASE_URL: PostgresDsn = os.getenv(
        "DATABASE_URL",
        "postgresql://user:password@db:5432/ml_db"
    )

    # Security
    # Parses JSON string '["key1", "key2"]' or set literal from .env
    API_KEYS: Set[str] = {
        "user-key-1",
        "user-key-2",
        "test-secret-key"
    }

    RATE_LIMIT_PER_MINUTE: int = 5

    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    class Config:
        case_sensitive = True
        env_file = ".env"


settings = Settings()
