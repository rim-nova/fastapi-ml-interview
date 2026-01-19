# Solution: Error Handling & Observability

## Approach

This solution implements production-grade observability:
1. **Correlation IDs** - Track requests across the system
2. **Structured Logging** - JSON format for log aggregation
3. **Global Error Handling** - Consistent error responses
4. **Health Checks** - Kubernetes-compatible probes
5. **Metrics** - Request counts and performance stats

---

## Complete Code Implementation

### File: `app/main.py`

```python
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from collections import defaultdict
import uuid
import time
import logging
import json
import traceback
from datetime import datetime
from typing import Dict, Any

from . import models, schemas
from .database import engine, get_db, SessionLocal

# Create tables
models.Base.metadata.create_all(bind=engine)

# ============================================
# STRUCTURED LOGGING
# ============================================

class JSONFormatter(logging.Formatter):
    """Format logs as JSON for aggregation systems"""
    
    def format(self, record):
        log_obj = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add extra fields
        if hasattr(record, "correlation_id"):
            log_obj["correlation_id"] = record.correlation_id
        if hasattr(record, "extra_data"):
            log_obj["data"] = record.extra_data
        if record.exc_info:
            log_obj["exception"] = traceback.format_exception(*record.exc_info)
        
        return json.dumps(log_obj)

# Setup logger
logger = logging.getLogger("ml_api")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger.handlers = [handler]

def log_with_context(level: str, message: str, correlation_id: str = None, **extra):
    """Helper to log with correlation ID and extra data"""
    record = logging.LogRecord(
        name="ml_api",
        level=getattr(logging, level.upper()),
        pathname="",
        lineno=0,
        msg=message,
        args=(),
        exc_info=None
    )
    if correlation_id:
        record.correlation_id = correlation_id
    if extra:
        record.extra_data = extra
    logger.handle(record)

# ============================================
# METRICS COLLECTION
# ============================================

class Metrics:
    """Simple in-memory metrics (use Prometheus in production)"""
    
    def __init__(self):
        self.start_time = time.time()
        self.request_count = defaultdict(int)
        self.status_count = defaultdict(int)
        self.error_count = defaultdict(int)
        self.response_times = []
        self.max_response_times = 10000
    
    def record_request(self, path: str, method: str, status: int, duration_ms: float):
        self.request_count[f"{method} {path}"] += 1
        self.status_count[f"{status // 100}xx"] += 1
        self.response_times.append(duration_ms)
        
        # Keep bounded list
        if len(self.response_times) > self.max_response_times:
            self.response_times = self.response_times[-self.max_response_times:]
    
    def record_error(self, error_type: str):
        self.error_count[error_type] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        sorted_times = sorted(self.response_times) if self.response_times else [0]
        p95_idx = int(len(sorted_times) * 0.95)
        
        return {
            "requests": {
                "total": sum(self.request_count.values()),
                "by_endpoint": dict(self.request_count),
                "by_status": dict(self.status_count)
            },
            "errors": dict(self.error_count),
            "performance": {
                "avg_response_ms": round(sum(sorted_times) / len(sorted_times), 2),
                "p95_response_ms": round(sorted_times[p95_idx], 2),
                "min_response_ms": round(min(sorted_times), 2),
                "max_response_ms": round(max(sorted_times), 2)
            },
            "uptime_seconds": int(time.time() - self.start_time)
        }

metrics = Metrics()

# ============================================
# MIDDLEWARE
# ============================================

class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Add correlation ID to all requests"""
    
    async def dispatch(self, request: Request, call_next):
        # Get existing or generate new correlation ID
        correlation_id = request.headers.get(
            "X-Correlation-ID",
            f"req-{uuid.uuid4().hex[:16]}"
        )
        
        # Store in request state for access in handlers
        request.state.correlation_id = correlation_id
        
        # Log request
        log_with_context(
            "info",
            f"Request started: {request.method} {request.url.path}",
            correlation_id,
            method=request.method,
            path=str(request.url.path),
            query=str(request.query_params)
        )
        
        # Process request with timing
        start_time = time.time()
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000
        
        # Add correlation ID to response
        response.headers["X-Correlation-ID"] = correlation_id
        
        # Record metrics
        metrics.record_request(
            request.url.path,
            request.method,
            response.status_code,
            duration_ms
        )
        
        # Log response
        log_with_context(
            "info",
            f"Request completed: {response.status_code}",
            correlation_id,
            status=response.status_code,
            duration_ms=round(duration_ms, 2)
        )
        
        return response

# ============================================
# ERROR HANDLING
# ============================================

class APIError(Exception):
    """Custom API error with code and message"""
    
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)

def create_error_response(
    code: str,
    message: str,
    correlation_id: str,
    status_code: int = 400
) -> JSONResponse:
    """Create consistent error response"""
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "correlation_id": correlation_id,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        }
    )

# ============================================
# APP SETUP
# ============================================

app = FastAPI(
    title="Observability Demo API",
    description="ML API with comprehensive error handling and metrics",
    version="1.0.0"
)

# Add middlewares (order matters - first added = outermost)
app.add_middleware(CorrelationIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# EXCEPTION HANDLERS
# ============================================

@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError):
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    
    log_with_context(
        "warning",
        f"API error: {exc.message}",
        correlation_id,
        error_code=exc.code
    )
    
    metrics.record_error(exc.code)
    
    return create_error_response(
        exc.code,
        exc.message,
        correlation_id,
        exc.status_code
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    
    log_with_context(
        "warning",
        f"HTTP exception: {exc.detail}",
        correlation_id,
        status_code=exc.status_code
    )
    
    return create_error_response(
        f"HTTP_{exc.status_code}",
        str(exc.detail),
        correlation_id,
        exc.status_code
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    
    # Log full error with stack trace
    log_with_context(
        "error",
        f"Unhandled exception: {type(exc).__name__}: {str(exc)}",
        correlation_id,
        error_type=type(exc).__name__,
        traceback=traceback.format_exc()
    )
    
    metrics.record_error("INTERNAL_ERROR")
    
    # Don't expose internal details to client
    return create_error_response(
        "INTERNAL_ERROR",
        "An unexpected error occurred. Please try again later.",
        correlation_id,
        500
    )

# ============================================
# HEALTH CHECK ENDPOINTS
# ============================================

@app.get("/health")
def health_check():
    """Basic liveness probe - is the process running?"""
    return {"status": "healthy"}

@app.get("/health/ready")
def readiness_check(db: Session = Depends(get_db)):
    """Readiness probe - can we handle traffic?"""
    try:
        # Check database connection
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "database": "disconnected",
                "error": str(e)
            }
        )
    
    return {
        "status": "ready",
        "database": db_status
    }

@app.get("/health/detailed")
def detailed_health_check(db: Session = Depends(get_db)):
    """Detailed health with component status"""
    components = {}
    overall_healthy = True
    
    # Check database
    try:
        start = time.time()
        db.execute(text("SELECT 1"))
        db_latency = (time.time() - start) * 1000
        components["database"] = {
            "status": "healthy",
            "latency_ms": round(db_latency, 2)
        }
    except Exception as e:
        components["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        overall_healthy = False
    
    # Check ML model (mock)
    components["ml_model"] = {
        "status": "healthy",
        "version": "1.0.0"
    }
    
    return {
        "status": "healthy" if overall_healthy else "degraded",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "components": components,
        "uptime_seconds": int(time.time() - metrics.start_time)
    }

# ============================================
# METRICS ENDPOINT
# ============================================

@app.get("/metrics")
def get_metrics(db: Session = Depends(get_db)):
    """Get application metrics"""
    stats = metrics.get_stats()
    
    # Add job counts from database
    try:
        job_counts = {}
        for status in ["pending", "processing", "completed", "failed"]:
            count = db.query(models.MLJob).filter(
                models.MLJob.status == status
            ).count()
            job_counts[status] = count
        
        stats["jobs"] = job_counts
    except Exception:
        stats["jobs"] = {"error": "Could not fetch job counts"}
    
    return stats

# ============================================
# API ENDPOINTS
# ============================================

@app.get("/")
def read_root():
    return {"message": "Observability Demo API is running"}

@app.post("/predict")
def create_prediction(
    request: Request,
    data: schemas.JobCreate,
    db: Session = Depends(get_db)
):
    """Create prediction with full observability"""
    correlation_id = request.state.correlation_id
    
    # Validation
    if len(data.text.strip()) < 10:
        raise APIError(
            "VALIDATION_ERROR",
            "Text must be at least 10 characters",
            400
        )
    
    # Create job
    job_uuid = f"job-{uuid.uuid4().hex[:12]}"
    
    new_job = models.MLJob(
        job_uuid=job_uuid,
        input_text=data.text,
        status="pending"
    )
    db.add(new_job)
    db.commit()
    
    log_with_context(
        "info",
        f"Job created: {job_uuid}",
        correlation_id,
        job_id=job_uuid
    )
    
    return {
        "job_id": job_uuid,
        "status": "pending",
        "correlation_id": correlation_id
    }

@app.get("/error-test")
def test_error():
    """Endpoint to test error handling"""
    raise ValueError("This is a test error")
```

---

## Key Design Decisions

### 1. Correlation ID Flow
- Generated on request if not provided
- Stored in `request.state`
- Added to all logs
- Returned in response header
- Passed to background tasks

### 2. Structured Logging
JSON format enables log aggregation tools:
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "ERROR",
  "message": "Job failed",
  "correlation_id": "req-abc123",
  "data": {"job_id": "job-xyz"}
}
```

### 3. Error Response Consistency
All errors return same structure:
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human readable message",
    "correlation_id": "req-abc123",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

---

## Testing

```bash
# Test correlation ID
curl -v http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "This is a test message"}'
# Check X-Correlation-ID header in response

# Test error handling
curl http://localhost:8000/error-test
# Should return 500 with error structure

# Test validation error
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "short"}'
# Should return 400 VALIDATION_ERROR

# Check health
curl http://localhost:8000/health
curl http://localhost:8000/health/ready
curl http://localhost:8000/health/detailed

# Check metrics
curl http://localhost:8000/metrics
```

---

## Time to Implement: 45-60 minutes
