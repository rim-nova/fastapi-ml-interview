from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class MLModel(Base):
    __tablename__ = "ml_models"

    id = Column(Integer, primary_key=True, index=True)
    model_uuid = Column(String, unique=True, index=True)
    name = Column(String, index=True)
    version = Column(String)
    status = Column(String, default="inactive")  # active, inactive
    traffic_percent = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PredictionLog(Base):
    __tablename__ = "prediction_logs"

    id = Column(Integer, primary_key=True, index=True)
    model_uuid = Column(String)
    model_version = Column(String)
    input_text = Column(Text)
    prediction = Column(String)
    confidence = Column(Float)
    latency_ms = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
