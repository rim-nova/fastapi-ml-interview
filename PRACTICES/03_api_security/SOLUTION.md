# Solution: API Security & Rate Limiting

## Approach

This solution implements three security layers:
1. **API Key Authentication** using FastAPI's dependency injection
2. **Rate Limiting** with in-memory request tracking
3. **Input Validation** using Pydantic validators

All security checks happen BEFORE the main business logic executes, following the principle of "fail fast."

---

## Architecture

```
Request → Rate Limiter → API Key Auth → Input Validation → Business Logic
          ↓ 429         ↓ 401          ↓ 400              ↓ 200
```

---

## Key Implementation Details

### 1. API Key Authentication

We use FastAPI's `Header` dependency to extract and validate the API key:

```python
from fastapi import Header, HTTPException

VALID_API_KEYS = {"user-key-1", "user-key-2", "test-secret-key"}

async def verify_api_key(x_api_key: str = Header(...)):
    """
    Dependency that verifies API key from header.
    Raises 401 if key is invalid or missing.
    """
    if x_api_key not in VALID_API_KEYS:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API Key"
        )
    return x_api_key
```

**Why this works:**
- `Header(...)` makes the header required
- `x_api_key` gets the value from `X-API-Key` header (case-insensitive)
- Returning the key allows it to be used in the endpoint function if needed

### 2. Rate Limiting

We track requests per IP address using an in-memory dictionary:

```python
import time
from collections import defaultdict

# Global storage (in production, use Redis)
request_history = defaultdict(list)
RATE_LIMIT = 5  # requests
TIME_WINDOW = 60  # seconds

def check_rate_limit(request: Request):
    """
    Allows 5 requests per minute per IP.
    Raises 429 if limit exceeded.
    """
    ip = request.client.host
    now = time.time()
    
    # Get request timestamps for this IP
    history = request_history[ip]
    
    # Filter: keep only requests from last 60 seconds
    recent_requests = [t for t in history if now - t < TIME_WINDOW]
    
    # Check if limit exceeded
    if len(recent_requests) >= RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Try again in {int(TIME_WINDOW - (now - recent_requests[0]))} seconds."
        )
    
    # Update history with current request
    recent_requests.append(now)
    request_history[ip] = recent_requests
    
    return True
```

**Limitations (Important to mention in interview):**
- ❌ In-memory storage lost on server restart
- ❌ Doesn't work across multiple server instances
- ❌ Memory usage grows with unique IPs
- ✅ **Production Solution**: Use Redis with TTL

### 3. Input Validation

We use Pydantic's built-in validation with custom error messages:

```python
from pydantic import BaseModel, Field, validator

class JobCreate(BaseModel):
    text: str = Field(
        ..., 
        min_length=10, 
        max_length=5000,
        example="This is a sample text for ML processing"
    )
    
    @validator('text')
    def validate_text_content(cls, v):
        stripped = v.strip()
        
        if len(stripped) < 10:
            raise ValueError("Text must contain at least 10 non-whitespace characters")
        
        if not any(c.isalnum() for c in stripped):
            raise ValueError("Text must contain at least some alphanumeric characters")
        
        return v
```

---

## Complete Code Implementation

### File: `app/main.py`

```python
from fastapi import FastAPI, Depends, HTTPException, Header, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Optional
import time
import uuid
from collections import defaultdict

from . import models, schemas
from .database import engine, get_db, SessionLocal

# Create tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Secure ML API",
    description="ML API with authentication and rate limiting",
    version="1.0.0"
)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# SECURITY LAYER 1: API KEY AUTHENTICATION
# ============================================

VALID_API_KEYS = {
    "user-key-1",
    "user-key-2",
    "test-secret-key"
}

async def verify_api_key(x_api_key: str = Header(...)):
    """
    Verify API key from request header.
    Raises 401 if invalid.
    """
    if x_api_key not in VALID_API_KEYS:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API Key"
        )
    return x_api_key

# ============================================
# SECURITY LAYER 2: RATE LIMITING
# ============================================

request_history = defaultdict(list)
RATE_LIMIT = 5  # requests
TIME_WINDOW = 60  # seconds

async def check_rate_limit(request: Request):
    """
    Rate limiter: 5 requests per 60 seconds per IP.
    Raises 429 if exceeded.
    """
    ip = request.client.host
    now = time.time()
    
    # Get history
    history = request_history[ip]
    
    # Keep only recent requests (sliding window)
    recent = [t for t in history if now - t < TIME_WINDOW]
    
    if len(recent) >= RATE_LIMIT:
        # Calculate wait time
        oldest = recent[0]
        wait_time = int(TIME_WINDOW - (now - oldest))
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Try again in {wait_time} seconds."
        )
    
    # Add current request
    recent.append(now)
    request_history[ip] = recent
    
    return True

# ============================================
# ENDPOINTS
# ============================================

@app.get("/")
def read_root():
    """Public endpoint"""
    return {"message": "Secure ML API is running"}

@app.get("/health")
def health_check():
    """Health check - no authentication required"""
    return {"status": "healthy"}

@app.post(
    "/predict",
    response_model=schemas.JobResponse,
    dependencies=[Depends(check_rate_limit), Depends(verify_api_key)]
)
def create_prediction(
    request: schemas.JobCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Create ML prediction job.
    Requires valid API key and respects rate limits.
    """
    # Generate job ID
    job_id = str(uuid.uuid4())
    
    # Save to database
    new_job = models.MLJob(
        job_uuid=job_id,
        input_text=request.text,
        status="pending"
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    
    # Start background processing
    background_tasks.add_task(process_ml_job, job_id)
    
    return schemas.JobResponse(
        job_uuid=job_id,
        status="processing",
        result_label=None,
        result_score=None
    )

@app.get(
    "/jobs/{job_id}",
    response_model=schemas.JobResponse,
    dependencies=[Depends(verify_api_key)]
)
def get_job_status(
    job_id: str,
    db: Session = Depends(get_db)
):
    """Get job status. Requires valid API key."""
    job = db.query(models.MLJob).filter(models.MLJob.job_uuid == job_id).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return schemas.JobResponse(
        job_uuid=job.job_uuid,
        status=job.status,
        result_label=job.result_label,
        result_score=job.result_score
    )

# ============================================
# BACKGROUND TASKS
# ============================================

def process_ml_job(job_id: str):
    """Simulate ML processing. Updates job status in database."""
    db = SessionLocal()
    try:
        # Simulate ML model delay
        time.sleep(5)
        
        # Get job
        job = db.query(models.MLJob).filter(models.MLJob.job_uuid == job_id).first()
        
        if job:
            # Simulate ML result
            sentiment = "positive" if "good" in job.input_text.lower() else "neutral"
            
            job.status = "completed"
            job.result_label = sentiment
            job.result_score = 0.95
            db.commit()
            
            print(f"✅ Job {job_id} completed: {sentiment}")
        
    except Exception as e:
        print(f"❌ Job {job_id} failed: {e}")
        job = db.query(models.MLJob).filter(models.MLJob.job_uuid == job_id).first()
        if job:
            job.status = "failed"
            db.commit()
    finally:
        db.close()
```

### File: `app/schemas.py`

```python
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime

class JobCreate(BaseModel):
    """Schema for creating ML job"""
    text: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        example="This is a sample text for ML processing"
    )
    
    @validator('text')
    def validate_text_content(cls, v):
        """Additional validation"""
        stripped = v.strip()
        
        if len(stripped) < 10:
            raise ValueError("Text must contain at least 10 non-whitespace characters")
        
        if not any(c.isalnum() for c in stripped):
            raise ValueError("Text must contain alphanumeric characters")
        
        return v

class JobResponse(BaseModel):
    """Schema for job response"""
    job_uuid: str
    status: str
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
    __tablename__ = "ml_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    job_uuid = Column(String, unique=True, index=True)
    input_text = Column(Text)
    status = Column(String, default="pending")
    result_score = Column(Float, nullable=True)
    result_label = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

---

## What Makes This Solution "Senior Level"

### 1. **Separation of Concerns**
- Authentication, rate limiting, and business logic are separate
- Each layer can be modified independently
- Easy to test each component

### 2. **Proper Error Handling**
- Different HTTP status codes for different errors:
  - 400: Client input error
  - 401: Authentication error
  - 404: Resource not found
  - 429: Too many requests
  - 500: Server error
- Clear error messages help API consumers

### 3. **Production Awareness**
- Comments explain limitations (in-memory storage)
- Suggests production alternatives (Redis)
- Considers distributed systems (multiple servers)

---

## Interview Follow-up Questions & Answers

**Q1: "Why store rate limit data in memory? What are the problems?"**

A: In-memory storage has several issues:
- Data is lost on server restart
- Doesn't work with multiple server instances (horizontal scaling)
- Memory usage grows with unique IPs

**Production solution:** Use Redis with TTL:
```python
import redis

redis_client = redis.Redis(host='localhost', port=6379)

def check_rate_limit(ip: str):
    key = f"rate_limit:{ip}"
    count = redis_client.incr(key)
    if count == 1:
        redis_client.expire(key, 60)  # TTL: 60 seconds
    return count <= 5
```

**Q2: "How would you handle different rate limits for different user tiers?"**

A: Store user tier in database, pass it to rate limiter:

```python
async def check_rate_limit(request: Request, user_key: str):
    user_tier = get_user_tier(user_key)  # Query DB
    limit = 20 if user_tier == "premium" else 5
    # ... rest of logic
```

**Q3: "What about API key rotation? How do you handle that?"**

A: Store keys in database with expiration dates:

```python
class APIKey(Base):
    key = Column(String, unique=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    expires_at = Column(DateTime)
    is_active = Column(Boolean, default=True)
```

---

## Testing Commands

```bash
# Test 1: Health check (public)
curl http://localhost:8000/health
# Expected: 200 OK

# Test 2: No API key
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "This should fail"}'
# Expected: 401 Unauthorized

# Test 3: Valid API key
curl -X POST http://localhost:8000/predict \
  -H "x-api-key: user-key-1" \
  -H "Content-Type: application/json" \
  -d '{"text": "This should work perfectly"}'
# Expected: 200 OK with job_id

# Test 4: Rate limit (run 6 times)
for i in {1..6}; do
  curl -X POST http://localhost:8000/predict \
    -H "x-api-key: user-key-1" \
    -H "Content-Type: application/json" \
    -d '{"text": "Rate limit test iteration '$i'"}'
done
# Expected: First 5 succeed, 6th returns 429

# Test 5: Input validation (too short)
curl -X POST http://localhost:8000/predict \
  -H "x-api-key: user-key-1" \
  -H "Content-Type: application/json" \
  -d '{"text": "short"}'
# Expected: 422 Unprocessable Entity
```

---

## Key Takeaways

1. **Use dependency injection** for reusable security checks
2. **Fail fast** - validate early, before expensive operations
3. **Be aware of limitations** - know when in-memory isn't enough
4. **Return proper status codes** - helps API consumers debug
5. **Think production** - mention scalability considerations

**Time to implement from scratch: 30-40 minutes (with practice)**
