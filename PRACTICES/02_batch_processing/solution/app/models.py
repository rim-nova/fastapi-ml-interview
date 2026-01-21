from sqlalchemy import Column, Integer, String, Text, Float, DateTime
from sqlalchemy.dialects.postgresql import JSON
from datetime import datetime
from app.db.base import Base  # Assuming you have a base class like in Practice 1


class BatchJob(Base):
    __tablename__ = "batch_jobs"

    id = Column(Integer, primary_key=True, index=True)
    batch_uuid = Column(String, unique=True, index=True)
    status = Column(String, default="pending")  # pending, processing, completed, failed
    total_count = Column(Integer, default=0)
    processed_count = Column(Integer, default=0)
    summary = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


class BatchResult(Base):
    __tablename__ = "batch_results"

    id = Column(Integer, primary_key=True, index=True)
    batch_uuid = Column(String, index=True)
    row_id = Column(String)
    original_text = Column(Text)
    sentiment = Column(String)
    score = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
