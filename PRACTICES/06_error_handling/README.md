# Practice 06: Error Handling & Observability

**Difficulty:** ⭐⭐⭐ (Medium-Hard)  
**Time Estimate:** 45-60 minutes  
**Job Requirement:** "Implement observability (logging, metrics, tracing)"

---

## 📝 Problem Statement

Your ML API is in production but you have no visibility into errors or performance. Build comprehensive error handling and observability features.

### Requirements

1. **Structured Logging**
   - Log all requests with correlation ID
   - Log errors with stack traces
   - JSON format for log aggregation

2. **Error Handling Middleware**
   - Catch all unhandled exceptions
   - Return consistent error response format
   - Log errors with context

3. **Health Check Endpoints**
   - `/health` - Basic liveness check
   - `/health/ready` - Readiness (database connection)
   - `/health/detailed` - Component status

4. **Metrics Endpoint**
   - Request count by endpoint
   - Error rate
   - Average response time
   - Active jobs count

5. **Request Tracing**
   - Add correlation ID to all requests
   - Pass through to background tasks
   - Include in error logs

### Example Usage

```bash
# All responses include correlation ID
curl http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "test"}'

# Response headers:
# X-Correlation-ID: req-abc123-def456

# Error response format:
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Text must be at least 10 characters",
    "correlation_id": "req-abc123-def456",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}

# Health checks
curl http://localhost:8000/health
# {"status": "healthy"}

curl http://localhost:8000/health/ready
# {"status": "ready", "database": "connected"}

curl http://localhost:8000/health/detailed
# {
#   "status": "healthy",
#   "components": {
#     "database": {"status": "healthy", "latency_ms": 2},
#     "ml_model": {"status": "healthy", "version": "1.0.0"}
#   },
#   "uptime_seconds": 3600
# }

# Metrics
curl http://localhost:8000/metrics
# {
#   "requests": {
#     "total": 1500,
#     "by_endpoint": {
#       "/predict": 1200,
#       "/jobs/{id}": 300
#     },
#     "by_status": {
#       "2xx": 1450,
#       "4xx": 45,
#       "5xx": 5
#     }
#   },
#   "performance": {
#     "avg_response_ms": 45,
#     "p95_response_ms": 120
#   },
#   "jobs": {
#     "pending": 5,
#     "processing": 3,
#     "completed_today": 500
#   }
# }
```

---

## 🎯 Learning Objectives

1. **Structured Logging** - JSON logs with context
2. **Error Middleware** - Global exception handling
3. **Correlation IDs** - Request tracing
4. **Health Checks** - Kubernetes-style probes
5. **Metrics Collection** - Basic observability

---

## 🚀 Getting Started

1. Copy the boilerplate
2. Implement correlation ID middleware
3. Add structured logging
4. Create error handling middleware
5. Implement health checks
6. Add metrics collection

---

## 💡 Hints

<details>
<summary>Hint 1: Correlation ID middleware</summary>

```python
import uuid
from starlette.middleware.base import BaseHTTPMiddleware

class CorrelationIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Get or generate correlation ID
        correlation_id = request.headers.get(
            "X-Correlation-ID", 
            f"req-{uuid.uuid4().hex[:16]}"
        )
        
        # Store in request state
        request.state.correlation_id = correlation_id
        
        # Process request
        response = await call_next(request)
        
        # Add to response headers
        response.headers["X-Correlation-ID"] = correlation_id
        
        return response
```
</details>

<details>
<summary>Hint 2: Structured logging</summary>

```python
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add extra fields
        if hasattr(record, "correlation_id"):
            log_obj["correlation_id"] = record.correlation_id
        if hasattr(record, "extra"):
            log_obj.update(record.extra)
        
        return json.dumps(log_obj)

# Setup
logger = logging.getLogger("ml_api")
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger.addHandler(handler)
logger.setLevel(logging.INFO)
```
</details>

<details>
<summary>Hint 3: Exception handler</summary>

```python
from fastapi import Request
from fastapi.responses import JSONResponse
from datetime import datetime

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    
    # Log error
    logger.error(
        f"Unhandled exception: {exc}",
        extra={
            "correlation_id": correlation_id,
            "path": request.url.path,
            "method": request.method,
            "error_type": type(exc).__name__
        },
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "correlation_id": correlation_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )
```
</details>

<details>
<summary>Hint 4: Metrics collection</summary>

```python
from collections import defaultdict
import time

# In-memory metrics (use Prometheus in production)
metrics = {
    "requests": defaultdict(int),
    "errors": defaultdict(int),
    "response_times": [],
    "start_time": time.time()
}

class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.time()
        
        response = await call_next(request)
        
        # Record metrics
        duration_ms = (time.time() - start) * 1000
        path = request.url.path
        
        metrics["requests"][path] += 1
        metrics["requests"][f"status_{response.status_code // 100}xx"] += 1
        metrics["response_times"].append(duration_ms)
        
        # Keep only last 1000 response times
        if len(metrics["response_times"]) > 1000:
            metrics["response_times"] = metrics["response_times"][-1000:]
        
        return response
```
</details>

---

## ✅ Success Criteria

- [ ] All requests have correlation ID
- [ ] Errors return consistent JSON format
- [ ] Stack traces logged but not exposed to clients
- [ ] Health check distinguishes liveness vs readiness
- [ ] Metrics accurately track request counts
- [ ] Logs are JSON formatted

---

## 🔍 What Interviewers Look For

**Good:**
- ✅ Basic error handling
- ✅ Health endpoint
- ✅ Logging

**Great:**
- ✅ Correlation IDs
- ✅ Structured JSON logs
- ✅ Readiness vs liveness

**Excellent:**
- ✅ Metrics collection
- ✅ Detailed health checks
- ✅ Can discuss Prometheus/Grafana

---

## 📚 Key Concepts

- **Correlation ID**: Trace requests across services
- **Structured Logging**: Machine-parseable logs (ELK, Splunk)
- **Liveness Probe**: Is the process running?
- **Readiness Probe**: Can it handle traffic?
- **SLI/SLO**: Service Level Indicators/Objectives

---

## ⏱️ Time Management

- **10 min**: Correlation ID middleware
- **10 min**: Structured logging setup
- **10 min**: Error handling middleware
- **10 min**: Health check endpoints
- **10 min**: Metrics collection
- **5 min**: Testing

**Total: 55 minutes**

---

**Observability is critical for production ML systems!**
