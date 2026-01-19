# Practice 04: Model Versioning & A/B Testing

**Difficulty:** ⭐⭐⭐ (Medium-Hard)  
**Time Estimate:** 60-75 minutes  
**Job Requirement:** "Model metadata, evaluation outputs"

---

## 📝 Problem Statement

Your ML team frequently deploys new model versions. You need a system to:
- Track multiple model versions
- Route traffic between versions (A/B testing)
- Compare model performance
- Safely roll out new versions

### Requirements

1. **POST /models** - Register a new model version
   - Store model metadata (name, version, accuracy, etc.)
   - Track deployment status

2. **GET /models** - List all registered models
   - Filter by status (active, inactive, testing)
   - Show performance metrics

3. **POST /predict** - Make predictions with traffic splitting
   - Specify model version OR use A/B routing
   - Track which model served each prediction

4. **POST /models/{model_id}/activate** - Activate a model version
   - Set traffic percentage (0-100%)
   - Deactivate previous version if needed

5. **GET /models/performance** - Compare model performance
   - Show accuracy, latency, usage count per model
   - Identify best performing model

### Example Usage

```bash
# Register model v1
curl -X POST http://localhost:8000/models \
  -H "Content-Type: application/json" \
  -d '{
    "name": "sentiment-model",
    "version": "1.0.0",
    "accuracy": 0.85,
    "description": "Initial production model"
  }'

# Response:
{
  "model_id": "model-abc123",
  "name": "sentiment-model",
  "version": "1.0.0",
  "status": "inactive",
  "traffic_percent": 0
}

# Register model v2
curl -X POST http://localhost:8000/models \
  -H "Content-Type: application/json" \
  -d '{
    "name": "sentiment-model",
    "version": "2.0.0",
    "accuracy": 0.91,
    "description": "Improved with more training data"
  }'

# Set up A/B test: 80% to v1, 20% to v2
curl -X POST http://localhost:8000/models/model-abc123/activate \
  -H "Content-Type: application/json" \
  -d '{"traffic_percent": 80}'

curl -X POST http://localhost:8000/models/model-def456/activate \
  -H "Content-Type: application/json" \
  -d '{"traffic_percent": 20}'

# Make predictions (routed automatically)
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "Great product!"}'

# Response includes which model was used:
{
  "prediction": "positive",
  "confidence": 0.92,
  "model_version": "2.0.0",
  "model_id": "model-def456"
}

# Force specific model version
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "Great product!", "model_version": "1.0.0"}'

# Compare performance
curl http://localhost:8000/models/performance

# Response:
{
  "models": [
    {
      "model_id": "model-abc123",
      "version": "1.0.0",
      "request_count": 800,
      "avg_latency_ms": 45,
      "avg_confidence": 0.87
    },
    {
      "model_id": "model-def456",
      "version": "2.0.0",
      "request_count": 200,
      "avg_latency_ms": 52,
      "avg_confidence": 0.93
    }
  ],
  "recommendation": "model-def456 shows 7% higher confidence"
}
```

---

## 🎯 Learning Objectives

1. **Model Registry Pattern** - Track ML model metadata
2. **A/B Testing** - Traffic splitting with weighted routing
3. **Performance Tracking** - Latency and accuracy metrics
4. **Feature Flags** - Gradual rollout strategies
5. **Database Aggregations** - Computing averages and counts

---

## 🚀 Getting Started

1. Copy the boilerplate:
   ```bash
   cp -r ../../BOILERPLATE ./practice
   cd practice
   ```

2. Design your database schema first
3. Implement model registration
4. Add traffic routing logic
5. Implement performance tracking

---

## 💡 Hints

<details>
<summary>Hint 1: Database schema for model registry</summary>

```python
class MLModel(Base):
    __tablename__ = "ml_models"
    
    id = Column(Integer, primary_key=True)
    model_uuid = Column(String, unique=True, index=True)
    name = Column(String, index=True)
    version = Column(String)
    description = Column(Text)
    accuracy = Column(Float)
    status = Column(String, default="inactive")  # inactive, active, testing
    traffic_percent = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class PredictionLog(Base):
    __tablename__ = "prediction_logs"
    
    id = Column(Integer, primary_key=True)
    model_uuid = Column(String, index=True)
    input_text = Column(Text)
    prediction = Column(String)
    confidence = Column(Float)
    latency_ms = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
```
</details>

<details>
<summary>Hint 2: Traffic splitting logic</summary>

```python
import random

def select_model(db: Session, requested_version: str = None):
    """Select model based on traffic weights or explicit version"""
    
    # If specific version requested, use it
    if requested_version:
        model = db.query(MLModel).filter(
            MLModel.version == requested_version
        ).first()
        if model:
            return model
        raise HTTPException(404, f"Model version {requested_version} not found")
    
    # Get active models with traffic > 0
    active_models = db.query(MLModel).filter(
        MLModel.status == "active",
        MLModel.traffic_percent > 0
    ).all()
    
    if not active_models:
        raise HTTPException(503, "No active models available")
    
    # Weighted random selection
    total_weight = sum(m.traffic_percent for m in active_models)
    rand = random.randint(1, total_weight)
    
    cumulative = 0
    for model in active_models:
        cumulative += model.traffic_percent
        if rand <= cumulative:
            return model
    
    return active_models[0]  # Fallback
```
</details>

<details>
<summary>Hint 3: Performance aggregation query</summary>

```python
from sqlalchemy import func

def get_model_performance(db: Session):
    """Calculate performance metrics per model"""
    
    stats = db.query(
        PredictionLog.model_uuid,
        func.count(PredictionLog.id).label("request_count"),
        func.avg(PredictionLog.latency_ms).label("avg_latency"),
        func.avg(PredictionLog.confidence).label("avg_confidence")
    ).group_by(
        PredictionLog.model_uuid
    ).all()
    
    return stats
```
</details>

<details>
<summary>Hint 4: Logging predictions with latency</summary>

```python
import time

@app.post("/predict")
def predict(request: PredictRequest, db: Session = Depends(get_db)):
    # Select model
    model = select_model(db, request.model_version)
    
    # Time the prediction
    start_time = time.time()
    result = run_inference(model, request.text)
    latency_ms = int((time.time() - start_time) * 1000)
    
    # Log prediction
    log = PredictionLog(
        model_uuid=model.model_uuid,
        input_text=request.text,
        prediction=result["label"],
        confidence=result["score"],
        latency_ms=latency_ms
    )
    db.add(log)
    db.commit()
    
    return {
        "prediction": result["label"],
        "confidence": result["score"],
        "model_version": model.version,
        "model_id": model.model_uuid
    }
```
</details>

---

## ✅ Success Criteria

- [ ] Can register multiple model versions
- [ ] Traffic splitting routes correctly (test with 100 requests)
- [ ] Specific model version can be requested
- [ ] Performance metrics calculated correctly
- [ ] Activation/deactivation works properly
- [ ] Error handling for missing models

---

## 🔍 What Interviewers Look For

**Good:**
- ✅ Working model registration
- ✅ Basic traffic routing
- ✅ Request logging

**Great:**
- ✅ All of above, plus:
- ✅ Weighted random selection
- ✅ Performance aggregation queries
- ✅ Proper validation

**Excellent:**
- ✅ All of above, plus:
- ✅ Gradual rollout support
- ✅ Statistical analysis (confidence intervals)
- ✅ Explains production considerations

---

## 📚 Key Concepts

- **Model Registry**: Centralized metadata store for ML models
- **A/B Testing**: Statistical comparison of model variants
- **Canary Deployment**: Gradually increase traffic to new version
- **Feature Flags**: Toggle features without code deployment
- **Observability**: Track request volume, latency, accuracy

---

## ⏱️ Time Management

- **10 min**: Database models (MLModel, PredictionLog)
- **15 min**: Model registration endpoints
- **15 min**: Traffic routing logic
- **10 min**: Prediction endpoint with logging
- **10 min**: Performance aggregation endpoint
- **10 min**: Testing A/B split
- **5 min**: Error handling

**Total: 75 minutes**

---

## 🧪 Testing Commands

```bash
# Register two models
curl -X POST http://localhost:8000/models \
  -H "Content-Type: application/json" \
  -d '{"name": "sentiment", "version": "1.0.0", "accuracy": 0.85}'

curl -X POST http://localhost:8000/models \
  -H "Content-Type: application/json" \
  -d '{"name": "sentiment", "version": "2.0.0", "accuracy": 0.92}'

# Activate with A/B split
curl -X POST http://localhost:8000/models/{model1_id}/activate \
  -d '{"traffic_percent": 70}'

curl -X POST http://localhost:8000/models/{model2_id}/activate \
  -d '{"traffic_percent": 30}'

# Send 100 predictions, check distribution
for i in {1..100}; do
  curl -s -X POST http://localhost:8000/predict \
    -H "Content-Type: application/json" \
    -d '{"text": "Great product!"}' | jq -r '.model_version'
done | sort | uniq -c

# Expected output (approximately):
#   70 1.0.0
#   30 2.0.0

# Check performance
curl http://localhost:8000/models/performance
```

---

## 🎓 Production Considerations

1. **Statistical Significance**: Need enough samples before declaring winner
2. **Segment Analysis**: Performance may vary by user segment
3. **Rollback Plan**: Quick way to revert if new model fails
4. **Shadow Mode**: Test new model without serving results
5. **Metric Selection**: Choose right metrics (accuracy vs latency vs cost)

---

**This is a CRITICAL interview topic - ML engineering teams use these patterns daily!**
