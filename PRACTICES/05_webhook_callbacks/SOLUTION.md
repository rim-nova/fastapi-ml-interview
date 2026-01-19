# Solution: Webhook Callbacks

## Approach

This solution implements a webhook delivery system with:
1. **Async Delivery** - Non-blocking webhook calls
2. **Retry with Backoff** - Exponential retry delays
3. **HMAC Signing** - Payload verification
4. **Delivery Tracking** - Log all attempts

---

## Complete Code Implementation

### File: `app/models.py`

```python
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Boolean
from datetime import datetime
from .database import Base

class MLJob(Base):
    __tablename__ = "ml_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    job_uuid = Column(String, unique=True, index=True)
    input_text = Column(Text)
    status = Column(String, default="pending")
    result_score = Column(Float, nullable=True)
    result_label = Column(String, nullable=True)
    webhook_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"
    
    id = Column(Integer, primary_key=True, index=True)
    job_uuid = Column(String, index=True)
    webhook_url = Column(String)
    attempt_number = Column(Integer)
    status_code = Column(Integer, nullable=True)
    success = Column(Boolean, default=False)
    error_message = Column(Text, nullable=True)
    response_body = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

### File: `app/schemas.py`

```python
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List
from datetime import datetime

class JobCreate(BaseModel):
    text: str = Field(..., min_length=1)
    webhook_url: Optional[str] = Field(None, example="https://your-server.com/callback")

class JobResponse(BaseModel):
    job_id: str
    status: str
    webhook_registered: bool

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    result_label: Optional[str]
    result_score: Optional[float]

class WebhookAttempt(BaseModel):
    attempt: int
    timestamp: datetime
    status_code: Optional[int]
    success: bool
    error_message: Optional[str]

class WebhookStatusResponse(BaseModel):
    job_id: str
    webhook_url: str
    delivery_status: str  # pending, delivered, failed
    total_attempts: int
    attempts: List[WebhookAttempt]
```

### File: `app/main.py`

```python
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import uuid
import time
import hmac
import hashlib
import json
import requests
from datetime import datetime
from typing import Optional

from . import models, schemas
from .database import engine, get_db, SessionLocal

# Create tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Webhook Callbacks API",
    description="ML API with webhook notifications",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
WEBHOOK_SECRET = "your-secret-key-change-in-production"
MAX_WEBHOOK_RETRIES = 3
WEBHOOK_TIMEOUT = 10

# ============================================
# WEBHOOK UTILITIES
# ============================================

def generate_signature(payload: dict) -> str:
    """Generate HMAC-SHA256 signature for webhook payload"""
    payload_bytes = json.dumps(payload, sort_keys=True, default=str).encode()
    signature = hmac.new(
        WEBHOOK_SECRET.encode(),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()
    return f"sha256={signature}"


def deliver_webhook(job_uuid: str, webhook_url: str, payload: dict):
    """
    Deliver webhook with retry logic and exponential backoff.
    This function runs in a background task.
    """
    db = SessionLocal()
    
    try:
        signature = generate_signature(payload)
        headers = {
            "Content-Type": "application/json",
            "X-Signature": signature,
            "X-Job-ID": job_uuid
        }
        
        for attempt in range(1, MAX_WEBHOOK_RETRIES + 1):
            print(f"Webhook attempt {attempt} for job {job_uuid}")
            
            delivery_record = models.WebhookDelivery(
                job_uuid=job_uuid,
                webhook_url=webhook_url,
                attempt_number=attempt
            )
            
            try:
                response = requests.post(
                    webhook_url,
                    json=payload,
                    headers=headers,
                    timeout=WEBHOOK_TIMEOUT
                )
                
                delivery_record.status_code = response.status_code
                delivery_record.response_body = response.text[:500]  # Limit stored response
                
                if response.status_code < 400:
                    delivery_record.success = True
                    db.add(delivery_record)
                    db.commit()
                    print(f"✅ Webhook delivered for job {job_uuid}")
                    return
                else:
                    delivery_record.success = False
                    delivery_record.error_message = f"HTTP {response.status_code}"
                    
            except requests.Timeout:
                delivery_record.success = False
                delivery_record.error_message = "Request timeout"
                
            except requests.RequestException as e:
                delivery_record.success = False
                delivery_record.error_message = str(e)[:500]
            
            db.add(delivery_record)
            db.commit()
            
            # Exponential backoff before retry
            if attempt < MAX_WEBHOOK_RETRIES:
                backoff = 2 ** (attempt - 1)  # 1s, 2s, 4s
                print(f"Retrying in {backoff}s...")
                time.sleep(backoff)
        
        print(f"❌ Webhook delivery failed after {MAX_WEBHOOK_RETRIES} attempts for job {job_uuid}")
        
    except Exception as e:
        print(f"Webhook delivery error: {e}")
    finally:
        db.close()


def process_ml_job(job_uuid: str, text: str, webhook_url: Optional[str]):
    """Background task for ML processing"""
    db = SessionLocal()
    
    try:
        job = db.query(models.MLJob).filter(models.MLJob.job_uuid == job_uuid).first()
        if not job:
            return
        
        job.status = "processing"
        db.commit()
        
        # Simulate ML processing
        print(f"🔄 Processing job {job_uuid}...")
        time.sleep(3)
        
        # Mock result
        text_lower = text.lower()
        if any(w in text_lower for w in ["great", "amazing", "love"]):
            sentiment, confidence = "positive", 0.95
        elif any(w in text_lower for w in ["bad", "terrible", "hate"]):
            sentiment, confidence = "negative", 0.91
        else:
            sentiment, confidence = "neutral", 0.75
        
        # Update job
        job.status = "completed"
        job.result_label = sentiment
        job.result_score = confidence
        job.completed_at = datetime.utcnow()
        db.commit()
        
        print(f"✅ Job {job_uuid} completed: {sentiment}")
        
        # Send webhook if configured
        if webhook_url:
            payload = {
                "job_id": job_uuid,
                "status": "completed",
                "result": {
                    "sentiment": sentiment,
                    "confidence": confidence
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            deliver_webhook(job_uuid, webhook_url, payload)
            
    except Exception as e:
        print(f"Job processing error: {e}")
        job = db.query(models.MLJob).filter(models.MLJob.job_uuid == job_uuid).first()
        if job:
            job.status = "failed"
            db.commit()
            
            # Send failure webhook
            if webhook_url:
                payload = {
                    "job_id": job_uuid,
                    "status": "failed",
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
                deliver_webhook(job_uuid, webhook_url, payload)
    finally:
        db.close()


# ============================================
# ENDPOINTS
# ============================================

@app.get("/")
def read_root():
    return {"message": "Webhook Callbacks API is running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/predict", response_model=schemas.JobResponse)
def create_prediction(
    request: schemas.JobCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Submit job with optional webhook notification"""
    
    job_uuid = f"job-{uuid.uuid4().hex[:12]}"
    
    new_job = models.MLJob(
        job_uuid=job_uuid,
        input_text=request.text,
        status="pending",
        webhook_url=request.webhook_url
    )
    db.add(new_job)
    db.commit()
    
    # Start background processing
    background_tasks.add_task(
        process_ml_job, 
        job_uuid, 
        request.text, 
        request.webhook_url
    )
    
    return schemas.JobResponse(
        job_id=job_uuid,
        status="processing",
        webhook_registered=bool(request.webhook_url)
    )


@app.get("/jobs/{job_id}", response_model=schemas.JobStatusResponse)
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """Get job status"""
    
    job = db.query(models.MLJob).filter(models.MLJob.job_uuid == job_id).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return schemas.JobStatusResponse(
        job_id=job.job_uuid,
        status=job.status,
        result_label=job.result_label,
        result_score=job.result_score
    )


@app.get("/webhooks/{job_id}/status", response_model=schemas.WebhookStatusResponse)
def get_webhook_status(job_id: str, db: Session = Depends(get_db)):
    """Get webhook delivery status for a job"""
    
    job = db.query(models.MLJob).filter(models.MLJob.job_uuid == job_id).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if not job.webhook_url:
        raise HTTPException(status_code=400, detail="No webhook configured for this job")
    
    # Get delivery attempts
    attempts = db.query(models.WebhookDelivery).filter(
        models.WebhookDelivery.job_uuid == job_id
    ).order_by(models.WebhookDelivery.attempt_number).all()
    
    # Determine delivery status
    if not attempts:
        if job.status in ["pending", "processing"]:
            delivery_status = "pending"
        else:
            delivery_status = "pending"
    elif any(a.success for a in attempts):
        delivery_status = "delivered"
    elif len(attempts) >= MAX_WEBHOOK_RETRIES:
        delivery_status = "failed"
    else:
        delivery_status = "retrying"
    
    return schemas.WebhookStatusResponse(
        job_id=job_id,
        webhook_url=job.webhook_url,
        delivery_status=delivery_status,
        total_attempts=len(attempts),
        attempts=[
            schemas.WebhookAttempt(
                attempt=a.attempt_number,
                timestamp=a.created_at,
                status_code=a.status_code,
                success=a.success,
                error_message=a.error_message
            )
            for a in attempts
        ]
    )


@app.post("/webhooks/{job_id}/retry")
def retry_webhook(job_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Manually retry webhook delivery"""
    
    job = db.query(models.MLJob).filter(models.MLJob.job_uuid == job_id).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if not job.webhook_url:
        raise HTTPException(status_code=400, detail="No webhook configured")
    
    if job.status not in ["completed", "failed"]:
        raise HTTPException(status_code=400, detail="Job not yet finished")
    
    # Build payload
    payload = {
        "job_id": job_id,
        "status": job.status,
        "result": {
            "sentiment": job.result_label,
            "confidence": job.result_score
        } if job.result_label else None,
        "timestamp": datetime.utcnow().isoformat(),
        "is_retry": True
    }
    
    # Queue webhook delivery
    background_tasks.add_task(deliver_webhook, job_id, job.webhook_url, payload)
    
    return {"message": "Webhook retry scheduled"}
```

---

## Key Design Decisions

### 1. Exponential Backoff

```python
for attempt in range(1, MAX_RETRIES + 1):
    # ... try delivery
    
    if attempt < MAX_RETRIES:
        backoff = 2 ** (attempt - 1)  # 1s, 2s, 4s
        time.sleep(backoff)
```

**Why exponential backoff?**
- Gives failing server time to recover
- Doesn't overwhelm with immediate retries
- Industry standard pattern

### 2. HMAC Signing

```python
def generate_signature(payload: dict) -> str:
    payload_bytes = json.dumps(payload, sort_keys=True).encode()
    signature = hmac.new(
        WEBHOOK_SECRET.encode(),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()
    return f"sha256={signature}"
```

**Why sign webhooks?**
- Recipient can verify payload wasn't tampered
- Proves webhook came from your service
- Prevents replay attacks (with timestamp)

### 3. Delivery Tracking

Log every attempt for:
- Debugging failed deliveries
- Auditing
- Analytics on webhook reliability

---

## Testing

```bash
# Create simple webhook receiver
cat > receiver.py << 'EOF'
from fastapi import FastAPI, Request
app = FastAPI()
received = []

@app.post("/callback")
async def callback(request: Request):
    body = await request.json()
    print(f"Received: {body}")
    received.append(body)
    return {"status": "ok"}

@app.get("/received")
def get_received():
    return received
EOF

# Run receiver
uvicorn receiver:app --port 9000 &

# Submit job with webhook
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "Great product!", "webhook_url": "http://localhost:9000/callback"}'

# Wait a few seconds, then check
curl http://localhost:9000/received
curl http://localhost:8000/webhooks/JOB_ID/status
```

---

## Interview Discussion

**Q: "How would you handle webhook failures in production?"**

A: Dead letter queue - store failed webhooks for manual review or retry. Alert on high failure rates. Provide UI for customers to see delivery status and retry.

**Q: "How do you prevent webhook replay attacks?"**

A: Include timestamp in payload, recipient rejects if timestamp is too old. Include unique event ID for idempotency.

---

## Time to Implement: 45-60 minutes
