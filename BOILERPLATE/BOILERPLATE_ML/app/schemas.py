from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class JobCreate(BaseModel):
    """Schema for creating a new job"""
    text: str = Field(..., example="This is sample text for processing")

class JobResponse(BaseModel):
    """Schema for job response"""
    job_uuid: str
    status: str
    result_label: Optional[str] = None
    result_score: Optional[float] = None
    
    class Config:
        orm_mode = True  # Allows conversion from SQLAlchemy models
