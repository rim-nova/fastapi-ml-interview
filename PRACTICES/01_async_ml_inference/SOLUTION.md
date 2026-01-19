# Solution: Async ML Inference

## Approach

This solution implements asynchronous ML inference using FastAPI's `BackgroundTasks`. The key insight is that users shouldn't wait for slow ML operations - instead, they get a job ID immediately and can poll for results.

---

## Architecture

```
Client Request → Create Job (DB) → Return job_id → Background Task starts
                                                          ↓
Client polls GET /jobs/{id} ← Update DB ← ML Inference completes
```

---

## Key Implementation Details

### 1. Job Creation Flow

```python
@app.post("/predict", response_model=JobResponse)
def create_prediction(
    request: JobCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    # 1. Generate unique ID
    job_id = str(uuid.uuid4())
    
    # 2. Save to database with "pending" status
    new_job = MLJob(
        job_uuid=job_id,
        input_text=request.text,
        status="pending"
    )
    db.add(new_job)
    db.commit()
    
    # 3. Schedule background task
    background_tasks.add_task(process_ml_job, job_id, request.text)
    
    # 4. Return immediately
    return JobResponse(job_uuid=job_id, status="processing")
```

### 2. Background Task (Critical Pattern)

```python
def process_ml_job(job_id: str, text: str):
    """
    IMPORTANT: Create a NEW database session inside background tasks!
    The original session is closed after the HTTP response is sent.
    """
    from .database import SessionLocal
    
    db = SessionLocal()
    try:
        # Update status to processing
        job = db.query(MLJob).filter(MLJob.job_uuid == job_id).first()
        job.status = "processing"
        db.commit()
        
        # Simulate ML model (5 seconds)
        time.sleep(5)
        
        # Mock ML result
        sentiment = "positive" if "good" in text.lower() or "amazing" in text.lower() else "negative"
        confidence = 0.95
        
        # Update with results
        job.status = "completed"
        job.result_label = sentiment
        job.result_score = confidence
        db.commit()
        
        print(f"✅ Job {job_id} completed: {sentiment} ({confidence})")
        
    except Exception as e:
        print(f"❌ Job {job_id} failed: {e}")
        job = db.query(MLJob).filter(MLJob.job_uuid == job_id).first()
        if job:
            job.status = "failed"
            db.commit()
    finally:
        db.close()  # ALWAYS close the session
```

### 3. Status Polling Endpoint

```python
@app.get("/jobs/{job_id}", response_model=JobResponse)
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    job = db.query(MLJob).filter(MLJob.job_uuid == job_id).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobResponse(
        job_uuid=job.job_uuid,
        status=job.status,
        result_label=job.result_label,
        result_score=job.result_score
    )
```

---

## Complete Code Implementation

### File: `app/main.py`

```python
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import uuid
import time

from . import models, schemas
from .database import engine, get_db, SessionLocal

# Create tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Async ML Inference API",
    description="ML API with background processing",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def process_ml_job(job_id: str, text: str):
    """Background task for ML inference"""
    db = SessionLocal()
    try:
        # Get and update job
        job = db.query(models.MLJob).filter(models.MLJob.job_uuid == job_id).first()
        if not job:
            print(f"Job {job_id} not found")
            return
        
        job.status = "processing"
        db.commit()
        
        # Simulate ML model delay
        print(f"🔄 Processing job {job_id}...")
        time.sleep(5)
        
        # Mock sentiment analysis
        text_lower = text.lower()
        if any(word in text_lower for word in ["good", "great", "amazing", "love", "excellent"]):
            sentiment = "positive"
            confidence = 0.95
        elif any(word in text_lower for word in ["bad", "terrible", "hate", "awful", "horrible"]):
            sentiment = "negative"
            confidence = 0.92
        else:
            sentiment = "neutral"
            confidence = 0.78
        
        # Update with results
        job.status = "completed"
        job.result_label = sentiment
        job.result_score = confidence
        db.commit()
        
        print(f"✅ Job {job_id} completed: {sentiment} ({confidence})")
        
    except Exception as e:
        print(f"❌ Job {job_id} failed: {e}")
        try:
            job = db.query(models.MLJob).filter(models.MLJob.job_uuid == job_id).first()
            if job:
                job.status = "failed"
                db.commit()
        except:
            pass
    finally:
        db.close()


@app.get("/")
def read_root():
    return {"message": "Async ML Inference API is running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/predict", response_model=schemas.JobResponse)
def create_prediction(
    request: schemas.JobCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Submit text for sentiment analysis.
    Returns immediately with job ID.
    """
    # Generate unique job ID
    job_id = str(uuid.uuid4())
    
    # Create job in database
    new_job = models.MLJob(
        job_uuid=job_id,
        input_text=request.text,
        status="pending"
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    
    # Schedule background processing
    background_tasks.add_task(process_ml_job, job_id, request.text)
    
    return schemas.JobResponse(
        job_uuid=job_id,
        status="processing",
        result_label=None,
        result_score=None
    )


@app.get("/jobs/{job_id}", response_model=schemas.JobResponse)
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """
    Check status of a prediction job.
    """
    job = db.query(models.MLJob).filter(models.MLJob.job_uuid == job_id).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return schemas.JobResponse(
        job_uuid=job.job_uuid,
        status=job.status,
        result_label=job.result_label,
        result_score=job.result_score
    )


@app.get("/jobs", response_model=list[schemas.JobResponse])
def list_jobs(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    """
    List all jobs (bonus endpoint).
    """
    jobs = db.query(models.MLJob).order_by(
        models.MLJob.created_at.desc()
    ).offset(skip).limit(limit).all()
    
    return [
        schemas.JobResponse(
            job_uuid=job.job_uuid,
            status=job.status,
            result_label=job.result_label,
            result_score=job.result_score
        )
        for job in jobs
    ]
```

### File: `app/schemas.py`

```python
from pydantic import BaseModel, Field
from typing import Optional

class JobCreate(BaseModel):
    """Schema for creating a new prediction job"""
    text: str = Field(
        ..., 
        min_length=1,
        max_length=10000,
        example="This product is amazing! I love it."
    )

class JobResponse(BaseModel):
    """Schema for job response"""
    job_uuid: str
    status: str  # pending, processing, completed, failed
    result_label: Optional[str] = None
    result_score: Optional[float] = None
    
    class Config:
        orm_mode = True
```

### File: `app/models.py`

```python
from sqlalchemy import Column, Integer, String, Text, Float, DateTime
from datetime import datetime
from .database import Base

class MLJob(Base):
    """Database model for ML inference jobs"""
    __tablename__ = "ml_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    job_uuid = Column(String, unique=True, index=True)
    input_text = Column(Text)
    status = Column(String, default="pending")  # pending, processing, completed, failed
    result_score = Column(Float, nullable=True)
    result_label = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

---

## Testing

```bash
# 1. Start services
docker-compose up --build

# 2. Submit a job
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "This product is amazing! I love it!"}'

# Response (immediate):
# {"job_uuid":"abc123...","status":"processing","result_label":null,"result_score":null}

# 3. Check status immediately
curl http://localhost:8000/jobs/abc123...
# Response: {"status":"processing"...}

# 4. Wait 5+ seconds, check again
curl http://localhost:8000/jobs/abc123...
# Response: {"status":"completed","result_label":"positive","result_score":0.95}

# 5. Test with negative sentiment
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "This is terrible and I hate it!"}'
```

---

## Key Interview Points

### Why BackgroundTasks?

- **Built-in to FastAPI** - No external dependencies
- **Good for short tasks** (< 30 seconds)
- **Not persistent** - Tasks lost on server restart

### When NOT to use BackgroundTasks?

- Tasks longer than 30 seconds → Use Celery
- Need task persistence → Use message queue (RabbitMQ, Redis)
- Need task retries → Use Celery with retry logic

### Common Mistake to Avoid

```python
# ❌ WRONG - Session closed after HTTP response
@app.post("/predict")
def predict(db: Session = Depends(get_db)):
    background_tasks.add_task(process, db)  # db will be closed!

# ✅ CORRECT - Create new session in background task
def process(job_id: str):
    db = SessionLocal()  # New session
    try:
        # ... work
    finally:
        db.close()
```

---

## Time to Implement: 45-60 minutes

**Breakdown:**
- 10 min: Setup boilerplate
- 15 min: Implement POST /predict
- 10 min: Implement background task
- 10 min: Implement GET /jobs/{id}
- 10 min: Testing and debugging
