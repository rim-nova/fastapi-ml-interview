from sqlalchemy import Column, Integer, String, Text, Float, DateTime
from sqlalchemy.dialects.postgresql import JSON
from datetime import datetime
from app.db.session import Base


class BatchJob(Base):
    """Batch processing job"""
    __tablename__ = "batch_jobs"

    id = Column(Integer, primary_key=True, index=True)
    batch_uuid = Column(String, unique=True, index=True)
    status = Column(String, default="pending")
    total_count = Column(Integer, default=0)
    processed_count = Column(Integer, default=0)
    summary = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


class BatchResult(Base):
    """Individual result within a batch"""
    __tablename__ = "batch_results"

    id = Column(Integer, primary_key=True, index=True)
    batch_uuid = Column(String, index=True)
    row_id = Column(String)
    original_text = Column(Text)
    sentiment = Column(String)
    score = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
