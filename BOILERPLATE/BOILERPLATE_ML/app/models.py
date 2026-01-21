from sqlalchemy import Column, Integer, String, Text, Float, DateTime
from datetime import datetime
from .database import Base

class MLJob(Base):
    """
    Database model for ML jobs
    
    This is a template - modify based on your specific needs
    """
    __tablename__ = "ml_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    job_uuid = Column(String, unique=True, index=True)
    input_text = Column(Text)
    status = Column(String, default="pending")  # pending, processing, completed, failed
    result_score = Column(Float, nullable=True)
    result_label = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
