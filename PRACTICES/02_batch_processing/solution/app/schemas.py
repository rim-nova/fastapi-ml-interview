from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class BatchCreateResponse(BaseModel):
    batch_id: str
    status: str
    total_count: int
    processed_count: int


class BatchStatusResponse(BaseModel):
    batch_id: str
    status: str
    total_count: int
    processed_count: int
    progress_percent: float
    summary: Optional[Dict[str, int]] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class ResultItem(BaseModel):
    row_id: str
    text: str
    sentiment: str
    score: float


class BatchResultsResponse(BaseModel):
    batch_id: str
    page: int
    per_page: int
    total_results: int
    total_pages: int
    results: List[ResultItem]
