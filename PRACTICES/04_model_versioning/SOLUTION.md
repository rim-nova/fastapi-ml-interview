# Solution: Model Versioning & A/B Testing

## Approach

This solution implements a model registry with A/B testing capabilities:
1. **Model Registry** - Store and manage ML model metadata
2. **Traffic Routing** - Weighted random selection for A/B tests
3. **Performance Tracking** - Log every prediction with latency
4. **Aggregation Queries** - Calculate statistics per model

---

## Architecture

```
                    ┌─────────────────────────────┐
                    │      Model Registry         │
                    │  ┌───────┐    ┌───────┐    │
                    │  │ v1.0  │    │ v2.0  │    │
                    │  │ 70%   │    │ 30%   │    │
                    │  └───────┘    └───────┘    │
                    └─────────────────────────────┘
                                 ↑
                    ┌────────────┴────────────┐
                    │    Traffic Router       │
                    │  (Weighted Selection)   │
                    └────────────┬────────────┘
                                 ↑
    Request → /predict → Select Model → Run Inference → Log Result → Response
                                                              ↓
                                                   ┌──────────────────┐
                                                   │  Prediction Logs │
                                                   │  (for analytics) │
                                                   └──────────────────┘
```

---

## Complete Code Implementation

### File: `app/models.py`

```python
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Boolean
from datetime import datetime
from .database import Base

class MLModel(Base):
    """ML Model Registry"""
    __tablename__ = "ml_models"
    
    id = Column(Integer, primary_key=True, index=True)
    model_uuid = Column(String, unique=True, index=True)
    name = Column(String, index=True)
    version = Column(String)
    description = Column(Text, nullable=True)
    accuracy = Column(Float)
    status = Column(String, default="inactive")  # inactive, active, testing, deprecated
    traffic_percent = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    activated_at = Column(DateTime, nullable=True)


class PredictionLog(Base):
    """Log every prediction for analysis"""
    __tablename__ = "prediction_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    model_uuid = Column(String, index=True)
    model_version = Column(String)
    input_text = Column(Text)
    prediction = Column(String)
    confidence = Column(Float)
    latency_ms = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
```

### File: `app/schemas.py`

```python
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# Model Registry Schemas
class ModelCreate(BaseModel):
    name: str = Field(..., example="sentiment-model")
    version: str = Field(..., example="1.0.0")
    accuracy: float = Field(..., ge=0, le=1, example=0.92)
    description: Optional[str] = Field(None, example="Improved accuracy model")

class ModelResponse(BaseModel):
    model_id: str
    name: str
    version: str
    description: Optional[str]
    accuracy: float
    status: str
    traffic_percent: int
    created_at: datetime
    activated_at: Optional[datetime]
    
    class Config:
        orm_mode = True

class ModelActivate(BaseModel):
    traffic_percent: int = Field(..., ge=0, le=100, example=50)

# Prediction Schemas
class PredictRequest(BaseModel):
    text: str = Field(..., min_length=1, example="This product is amazing!")
    model_version: Optional[str] = Field(None, example="1.0.0")

class PredictResponse(BaseModel):
    prediction: str
    confidence: float
    model_id: str
    model_version: str
    latency_ms: int

# Performance Schemas
class ModelPerformance(BaseModel):
    model_id: str
    version: str
    request_count: int
    avg_latency_ms: float
    avg_confidence: float

class PerformanceReport(BaseModel):
    models: List[ModelPerformance]
    total_requests: int
    recommendation: Optional[str]
```

### File: `app/main.py`

```python
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
import uuid
import time
import random
from datetime import datetime
from typing import List, Optional

from . import models, schemas
from .database import engine, get_db

# Create tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Model Versioning API",
    description="ML Model Registry with A/B Testing",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# MOCK ML INFERENCE
# ============================================

def mock_inference(model: models.MLModel, text: str) -> dict:
    """
    Simulate ML model inference.
    In production, this would call the actual model.
    """
    # Simulate different accuracy based on model
    base_confidence = model.accuracy
    
    # Add some variance
    variance = random.uniform(-0.05, 0.05)
    confidence = min(max(base_confidence + variance, 0.5), 0.99)
    
    # Simple sentiment logic
    text_lower = text.lower()
    if any(word in text_lower for word in ["great", "amazing", "love", "excellent", "best"]):
        sentiment = "positive"
    elif any(word in text_lower for word in ["terrible", "awful", "hate", "worst", "bad"]):
        sentiment = "negative"
    else:
        sentiment = "neutral"
    
    # Simulate processing time (different per model version)
    version_latency = int(model.version.split('.')[0]) * 10 + random.randint(20, 50)
    time.sleep(version_latency / 1000)  # Convert to seconds
    
    return {
        "label": sentiment,
        "confidence": round(confidence, 4)
    }

# ============================================
# MODEL SELECTION (A/B ROUTING)
# ============================================

def select_model(db: Session, requested_version: Optional[str] = None) -> models.MLModel:
    """
    Select model based on traffic weights or explicit version.
    Implements weighted random selection for A/B testing.
    """
    # If specific version requested, use it
    if requested_version:
        model = db.query(models.MLModel).filter(
            models.MLModel.version == requested_version,
            models.MLModel.status.in_(["active", "testing"])
        ).first()
        
        if not model:
            raise HTTPException(
                status_code=404, 
                detail=f"Model version {requested_version} not found or not active"
            )
        return model
    
    # Get active models with traffic > 0
    active_models = db.query(models.MLModel).filter(
        models.MLModel.status == "active",
        models.MLModel.traffic_percent > 0
    ).all()
    
    if not active_models:
        raise HTTPException(
            status_code=503, 
            detail="No active models available. Please activate a model first."
        )
    
    # Weighted random selection
    total_weight = sum(m.traffic_percent for m in active_models)
    
    if total_weight == 0:
        raise HTTPException(
            status_code=503,
            detail="Active models have 0% traffic allocation"
        )
    
    # Normalize if total != 100
    rand = random.randint(1, total_weight)
    
    cumulative = 0
    for model in active_models:
        cumulative += model.traffic_percent
        if rand <= cumulative:
            return model
    
    # Fallback (shouldn't reach here)
    return active_models[0]

# ============================================
# ENDPOINTS
# ============================================

@app.get("/")
def read_root():
    return {"message": "Model Versioning API is running"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}


# --- Model Management ---

@app.post("/models", response_model=schemas.ModelResponse)
def register_model(
    request: schemas.ModelCreate,
    db: Session = Depends(get_db)
):
    """Register a new ML model version"""
    
    # Check if version already exists for this model name
    existing = db.query(models.MLModel).filter(
        models.MLModel.name == request.name,
        models.MLModel.version == request.version
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Model {request.name} v{request.version} already exists"
        )
    
    model_uuid = f"model-{uuid.uuid4().hex[:12]}"
    
    new_model = models.MLModel(
        model_uuid=model_uuid,
        name=request.name,
        version=request.version,
        description=request.description,
        accuracy=request.accuracy,
        status="inactive",
        traffic_percent=0
    )
    
    db.add(new_model)
    db.commit()
    db.refresh(new_model)
    
    return schemas.ModelResponse(
        model_id=new_model.model_uuid,
        name=new_model.name,
        version=new_model.version,
        description=new_model.description,
        accuracy=new_model.accuracy,
        status=new_model.status,
        traffic_percent=new_model.traffic_percent,
        created_at=new_model.created_at,
        activated_at=new_model.activated_at
    )


@app.get("/models", response_model=List[schemas.ModelResponse])
def list_models(
    status: Optional[str] = None,
    name: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all registered models with optional filters"""
    
    query = db.query(models.MLModel)
    
    if status:
        query = query.filter(models.MLModel.status == status)
    if name:
        query = query.filter(models.MLModel.name == name)
    
    model_list = query.order_by(models.MLModel.created_at.desc()).all()
    
    return [
        schemas.ModelResponse(
            model_id=m.model_uuid,
            name=m.name,
            version=m.version,
            description=m.description,
            accuracy=m.accuracy,
            status=m.status,
            traffic_percent=m.traffic_percent,
            created_at=m.created_at,
            activated_at=m.activated_at
        )
        for m in model_list
    ]


@app.get("/models/{model_id}", response_model=schemas.ModelResponse)
def get_model(model_id: str, db: Session = Depends(get_db)):
    """Get details for a specific model"""
    
    model = db.query(models.MLModel).filter(
        models.MLModel.model_uuid == model_id
    ).first()
    
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    return schemas.ModelResponse(
        model_id=model.model_uuid,
        name=model.name,
        version=model.version,
        description=model.description,
        accuracy=model.accuracy,
        status=model.status,
        traffic_percent=model.traffic_percent,
        created_at=model.created_at,
        activated_at=model.activated_at
    )


@app.post("/models/{model_id}/activate", response_model=schemas.ModelResponse)
def activate_model(
    model_id: str,
    request: schemas.ModelActivate,
    db: Session = Depends(get_db)
):
    """Activate a model with specified traffic percentage"""
    
    model = db.query(models.MLModel).filter(
        models.MLModel.model_uuid == model_id
    ).first()
    
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    # Update model
    model.status = "active"
    model.traffic_percent = request.traffic_percent
    model.activated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(model)
    
    # Calculate total traffic
    total_traffic = db.query(func.sum(models.MLModel.traffic_percent)).filter(
        models.MLModel.status == "active"
    ).scalar() or 0
    
    warning = None
    if total_traffic > 100:
        warning = f"Warning: Total traffic allocation is {total_traffic}%, exceeds 100%"
    elif total_traffic < 100:
        warning = f"Note: Total traffic allocation is {total_traffic}%, {100-total_traffic}% unallocated"
    
    response = schemas.ModelResponse(
        model_id=model.model_uuid,
        name=model.name,
        version=model.version,
        description=model.description,
        accuracy=model.accuracy,
        status=model.status,
        traffic_percent=model.traffic_percent,
        created_at=model.created_at,
        activated_at=model.activated_at
    )
    
    return response


@app.post("/models/{model_id}/deactivate", response_model=schemas.ModelResponse)
def deactivate_model(model_id: str, db: Session = Depends(get_db)):
    """Deactivate a model (set traffic to 0)"""
    
    model = db.query(models.MLModel).filter(
        models.MLModel.model_uuid == model_id
    ).first()
    
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    model.status = "inactive"
    model.traffic_percent = 0
    
    db.commit()
    db.refresh(model)
    
    return schemas.ModelResponse(
        model_id=model.model_uuid,
        name=model.name,
        version=model.version,
        description=model.description,
        accuracy=model.accuracy,
        status=model.status,
        traffic_percent=model.traffic_percent,
        created_at=model.created_at,
        activated_at=model.activated_at
    )


# --- Predictions ---

@app.post("/predict", response_model=schemas.PredictResponse)
def predict(
    request: schemas.PredictRequest,
    db: Session = Depends(get_db)
):
    """Make a prediction using A/B routing or specific version"""
    
    # Select model
    model = select_model(db, request.model_version)
    
    # Time the inference
    start_time = time.time()
    result = mock_inference(model, request.text)
    latency_ms = int((time.time() - start_time) * 1000)
    
    # Log prediction
    log = models.PredictionLog(
        model_uuid=model.model_uuid,
        model_version=model.version,
        input_text=request.text,
        prediction=result["label"],
        confidence=result["confidence"],
        latency_ms=latency_ms
    )
    db.add(log)
    db.commit()
    
    return schemas.PredictResponse(
        prediction=result["label"],
        confidence=result["confidence"],
        model_id=model.model_uuid,
        model_version=model.version,
        latency_ms=latency_ms
    )


# --- Performance Analytics ---

@app.get("/models/performance", response_model=schemas.PerformanceReport)
def get_performance(db: Session = Depends(get_db)):
    """Compare performance across all models"""
    
    # Aggregate statistics per model
    stats = db.query(
        models.PredictionLog.model_uuid,
        models.PredictionLog.model_version,
        func.count(models.PredictionLog.id).label("request_count"),
        func.avg(models.PredictionLog.latency_ms).label("avg_latency"),
        func.avg(models.PredictionLog.confidence).label("avg_confidence")
    ).group_by(
        models.PredictionLog.model_uuid,
        models.PredictionLog.model_version
    ).all()
    
    performance_list = [
        schemas.ModelPerformance(
            model_id=s.model_uuid,
            version=s.model_version,
            request_count=s.request_count,
            avg_latency_ms=round(s.avg_latency or 0, 2),
            avg_confidence=round(s.avg_confidence or 0, 4)
        )
        for s in stats
    ]
    
    total_requests = sum(p.request_count for p in performance_list)
    
    # Generate recommendation
    recommendation = None
    if len(performance_list) >= 2:
        # Sort by confidence
        sorted_by_confidence = sorted(
            performance_list, 
            key=lambda x: x.avg_confidence, 
            reverse=True
        )
        best = sorted_by_confidence[0]
        second = sorted_by_confidence[1]
        
        diff = round((best.avg_confidence - second.avg_confidence) * 100, 1)
        if diff > 1:
            recommendation = f"{best.version} shows {diff}% higher confidence than {second.version}"
    
    return schemas.PerformanceReport(
        models=performance_list,
        total_requests=total_requests,
        recommendation=recommendation
    )


@app.delete("/models/{model_id}")
def delete_model(model_id: str, db: Session = Depends(get_db)):
    """Delete a model (only if inactive)"""
    
    model = db.query(models.MLModel).filter(
        models.MLModel.model_uuid == model_id
    ).first()
    
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    if model.status == "active":
        raise HTTPException(
            status_code=400, 
            detail="Cannot delete active model. Deactivate first."
        )
    
    # Delete prediction logs for this model
    db.query(models.PredictionLog).filter(
        models.PredictionLog.model_uuid == model_id
    ).delete()
    
    # Delete model
    db.delete(model)
    db.commit()
    
    return {"message": f"Model {model_id} deleted"}
```

---

## Key Design Decisions

### 1. Weighted Random Selection

```python
# Algorithm:
# 1. Sum all weights
# 2. Generate random number 1 to total
# 3. Walk through models, accumulating weights
# 4. Return model when cumulative >= random

total_weight = sum(m.traffic_percent for m in active_models)
rand = random.randint(1, total_weight)

cumulative = 0
for model in active_models:
    cumulative += model.traffic_percent
    if rand <= cumulative:
        return model
```

**Why this works:**
- Model with 70% traffic has 70% chance of selection
- Fair distribution over many requests
- Simple and efficient (O(n) where n = number of active models)

### 2. Prediction Logging

Log every prediction for:
- Performance comparison
- Debugging
- Compliance/audit
- Model retraining data

### 3. Aggregation Queries

SQLAlchemy aggregation for statistics:
```python
stats = db.query(
    func.count(PredictionLog.id).label("request_count"),
    func.avg(PredictionLog.latency_ms).label("avg_latency"),
    func.avg(PredictionLog.confidence).label("avg_confidence")
).group_by(PredictionLog.model_uuid).all()
```

---

## Testing

```bash
# 1. Register models
curl -X POST http://localhost:8000/models \
  -H "Content-Type: application/json" \
  -d '{"name": "sentiment", "version": "1.0.0", "accuracy": 0.85}'

curl -X POST http://localhost:8000/models \
  -H "Content-Type: application/json" \
  -d '{"name": "sentiment", "version": "2.0.0", "accuracy": 0.92}'

# 2. Activate with A/B split (70/30)
curl -X POST http://localhost:8000/models/MODEL1_ID/activate \
  -H "Content-Type: application/json" \
  -d '{"traffic_percent": 70}'

curl -X POST http://localhost:8000/models/MODEL2_ID/activate \
  -H "Content-Type: application/json" \
  -d '{"traffic_percent": 30}'

# 3. Send 100 predictions, check distribution
for i in {1..100}; do
  curl -s -X POST http://localhost:8000/predict \
    -H "Content-Type: application/json" \
    -d '{"text": "Great product!"}' | jq -r '.model_version'
done | sort | uniq -c

# Expected: ~70 for v1.0.0, ~30 for v2.0.0

# 4. Check performance
curl http://localhost:8000/models/performance | jq
```

---

## Interview Discussion Points

**Q: "How would you ensure statistical significance in A/B tests?"**

A: Calculate sample size using power analysis. For detecting 5% difference with 95% confidence, need ~1500 samples per variant. Track p-values and confidence intervals.

**Q: "How do you handle gradual rollout?"**

A: Start at 1% traffic, monitor error rate and latency, gradually increase: 1% → 5% → 25% → 50% → 100%. Automated rollback if metrics degrade.

**Q: "What about multi-arm bandits vs A/B testing?"**

A: A/B is fixed allocation; bandits dynamically adjust based on performance. Use Thompson Sampling or UCB for faster convergence to optimal model.

---

## Time to Implement: 60-75 minutes
