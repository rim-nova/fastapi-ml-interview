import time
import random
import hashlib
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import sql
from app.schemas import api_models as schemas
from app.ml.engine import SentimentModel

router = APIRouter(prefix="/predict", tags=["Inference"])


def get_traffic_bucket(user_id: str) -> int:
    """
    Determines which traffic 'bucket' (0-99) a user falls into.
    """
    if not user_id:
        return random.randint(0, 99)

    hash_obj = hashlib.sha256(user_id.encode("utf-8"))
    hash_int = int(hash_obj.hexdigest(), 16)
    return hash_int % 100


def select_model(db: Session, req: schemas.PredictRequest) -> sql.MLModel:
    # 1. Developer Override
    if req.model_version:
        model = db.query(sql.MLModel).filter(
            sql.MLModel.version == req.model_version
        ).first()
        if not model:
            raise HTTPException(status_code=404, detail="Requested version not found")
        return model

    # 2. Fetch Active Models
    active_models = db.query(sql.MLModel).filter(
        sql.MLModel.status == "active",
        sql.MLModel.traffic_percent > 0
    ).order_by(sql.MLModel.id).all()

    if not active_models:
        raise HTTPException(status_code=503, detail="No active models configured")

    # 3. Deterministic Selection
    bucket = get_traffic_bucket(req.user_id)

    cumulative_weight = 0
    for model in active_models:
        cumulative_weight += model.traffic_percent
        if bucket < cumulative_weight:
            return model

    return active_models[0]


@router.post("", response_model=schemas.PredictResponse)
def predict(req: schemas.PredictRequest, db: Session = Depends(get_db)):
    model_config = select_model(db, req)

    start_time = time.time()
    prediction, confidence = SentimentModel.predict(req.text, model_config.version)
    latency = int((time.time() - start_time) * 1000)

    log_entry = sql.PredictionLog(
        model_uuid=model_config.model_uuid,
        model_version=model_config.version,
        input_text=req.text,
        prediction=prediction,
        confidence=confidence,
        latency_ms=latency
    )
    db.add(log_entry)
    db.commit()

    return {
        "prediction": prediction,
        "confidence": confidence,
        "model_version": model_config.version,
        "model_uuid": model_config.model_uuid,
        "latency_ms": latency
    }
