from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional


class JobCreate(BaseModel):
    text: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        example="This is a sample text for ML processing that meets the length requirements."
    )

    # UPDATED: Use @field_validator instead of @validator for Pydantic V2
    @field_validator('text')
    def validate_text_content(cls, v):
        stripped = v.strip()
        if len(stripped) < 10:
            raise ValueError("Text must contain at least 10 non-whitespace characters")
        return v


class JobResponse(BaseModel):
    job_uuid: str
    status: str
    result_label: Optional[str] = None
    result_score: Optional[float] = None

    # UPDATED: The Modern Pydantic V2 configuration
    model_config = ConfigDict(from_attributes=True)
