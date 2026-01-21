from pydantic import BaseModel, Field
from typing import Optional


class JobCreate(BaseModel):
    """Schema for creating a new prediction job"""
    text: str = Field(..., min_length=1, example="This product is amazing!")


class JobResponse(BaseModel):
    """Schema for job status response"""
    job_uuid: str
    status: str
    result_label: Optional[str] = None
    result_score: Optional[float] = None

    class Config:
        orm_mode = True
