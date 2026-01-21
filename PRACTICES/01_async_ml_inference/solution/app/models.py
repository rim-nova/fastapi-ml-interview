from sqlalchemy import Column, Integer, String, Text, Float, DateTime
from datetime import datetime
from app.db.session import Base


class MLJob(Base):
    __tablename__ = "ml_jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_uuid = Column(String, unique=True, index=True)
    input_text = Column(Text)
    status = Column(String, default="pending")  # pending, processing, completed, failed
    result_score = Column(Float, nullable=True)
    result_label = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
