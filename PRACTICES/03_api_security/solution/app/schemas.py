from pydantic import BaseModel, Field, validator
from typing import Optional


class JobCreate(BaseModel):
    # Strict validation defined here
    text: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        example="This is a sample text that meets length requirements."
    )

    @validator('text')
    def validate_content(cls, v):
        if not v.strip():
            raise ValueError("Text cannot be empty or whitespace only")
        if len(v.strip()) < 10:
            raise ValueError("Text must contain at least 10 non-whitespace characters")
        return v


class JobResponse(BaseModel):
    job_uuid: str
    status: str
    result_label: Optional[str] = None
    result_score: Optional[float] = None

    class Config:
        orm_mode = True
