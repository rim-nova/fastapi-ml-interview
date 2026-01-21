from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime


# --- Management Schemas ---

class ModelCreate(BaseModel):
    name: str = Field(..., min_length=1, example="sentiment-v1")
    version: str = Field(..., min_length=1, example="1.0.0")


class TrafficUpdate(BaseModel):
    percent: int = Field(..., ge=0, le=100, description="Traffic percentage (0-100)")


class ModelResponse(BaseModel):
    model_uuid: str
    name: str
    version: str
    status: str
    traffic_percent: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Inference Schemas ---

class PredictRequest(BaseModel):
    text: str = Field(..., min_length=1, example="I love using this product!")
    model_version: Optional[str] = Field(None, description="Force a specific version (for testing)")
    user_id: Optional[str] = Field(None, description="Unique User ID for Sticky Routing (A/B consistency)")


class PredictResponse(BaseModel):
    prediction: str
    confidence: float
    model_version: str
    model_uuid: str
    latency_ms: int


# --- Analytics Schemas ---

class PerformanceStat(BaseModel):
    model_version: str
    request_count: int
    avg_latency: float
    avg_confidence: float
