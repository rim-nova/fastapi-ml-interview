import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.session import get_db
from app.models import sql
from app.schemas import api_models as schemas

router = APIRouter(prefix="/models", tags=["Registry"])


@router.post("", response_model=schemas.ModelResponse, status_code=201)
def register_model(model_in: schemas.ModelCreate, db: Session = Depends(get_db)):
    existing = db.query(sql.MLModel).filter(sql.MLModel.version == model_in.version).first()
    if existing:
        raise HTTPException(400, "Model version already exists")

    new_model = sql.MLModel(
        model_uuid=f"mod-{uuid.uuid4().hex[:8]}",
        name=model_in.name,
        version=model_in.version,
        status="inactive",
        traffic_percent=0
    )
    db.add(new_model)
    db.commit()
    db.refresh(new_model)
    return new_model


@router.post("/{model_uuid}/activate", response_model=schemas.ModelResponse)
def update_traffic(
        model_uuid: str,
        traffic: schemas.TrafficUpdate,
        db: Session = Depends(get_db)
):
    model = db.query(sql.MLModel).filter(sql.MLModel.model_uuid == model_uuid).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    model.status = "active" if traffic.percent > 0 else "inactive"
    model.traffic_percent = traffic.percent

    db.commit()
    db.refresh(model)
    return model


@router.get("/stats", response_model=list[schemas.PerformanceStat])
def get_performance_stats(db: Session = Depends(get_db)):
    stats = db.query(
        sql.PredictionLog.model_version,
        func.count(sql.PredictionLog.id).label("count"),
        func.avg(sql.PredictionLog.latency_ms).label("latency"),
        func.avg(sql.PredictionLog.confidence).label("confidence")
    ).group_by(sql.PredictionLog.model_version).all()

    return [
        {
            "model_version": s.model_version,
            "request_count": s.count,
            "avg_latency": round(s.latency, 2),
            "avg_confidence": round(s.confidence, 4)
        }
        for s in stats
    ]