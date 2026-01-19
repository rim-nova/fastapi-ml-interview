# Solution: Monitoring Dashboard

## Complete Implementation

### File: `app/metrics.py`

```python
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import threading
import statistics
import time


@dataclass
class MetricPoint:
    """Single metric data point"""
    timestamp: datetime
    endpoint: str
    method: str
    status: int
    duration_ms: float
    error_type: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class ErrorRecord:
    """Detailed error record"""
    timestamp: datetime
    endpoint: str
    method: str
    error_type: str
    error_message: str
    status_code: int


class MetricsCollector:
    """
    Thread-safe metrics collector with time-series storage.
    
    Key design decisions:
    - Use deque for O(1) append and efficient cleanup
    - Lock for thread safety
    - Configurable retention period
    - Lazy cleanup on access
    """
    
    def __init__(self, retention_seconds: int = 86400):
        self.retention_seconds = retention_seconds
        self.points: deque = deque()
        self.errors: deque = deque()
        self.lock = threading.Lock()
        
        # Real-time counters
        self.active_requests = 0
        self.total_requests = 0
        self.start_time = time.time()
    
    def record_request(
        self,
        endpoint: str,
        method: str,
        status: int,
        duration_ms: float,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None
    ):
        """Record a completed request"""
        point = MetricPoint(
            timestamp=datetime.utcnow(),
            endpoint=endpoint,
            method=method,
            status=status,
            duration_ms=duration_ms,
            error_type=error_type,
            error_message=error_message
        )
        
        with self.lock:
            self.points.append(point)
            self.total_requests += 1
            
            # Record error separately for detailed tracking
            if status >= 400 and error_type:
                self.errors.append(ErrorRecord(
                    timestamp=point.timestamp,
                    endpoint=endpoint,
                    method=method,
                    error_type=error_type,
                    error_message=error_message or "",
                    status_code=status
                ))
            
            self._cleanup()
    
    def _cleanup(self):
        """Remove expired data points"""
        cutoff = datetime.utcnow() - timedelta(seconds=self.retention_seconds)
        
        while self.points and self.points[0].timestamp < cutoff:
            self.points.popleft()
        
        while self.errors and self.errors[0].timestamp < cutoff:
            self.errors.popleft()
    
    def _get_points_since(self, since: datetime) -> List[MetricPoint]:
        """Get all points since given timestamp"""
        with self.lock:
            self._cleanup()
            return [p for p in self.points if p.timestamp >= since]
    
    def _get_errors_since(self, since: datetime) -> List[ErrorRecord]:
        """Get all errors since given timestamp"""
        with self.lock:
            self._cleanup()
            return [e for e in self.errors if e.timestamp >= since]
    
    def get_overview(self) -> Dict[str, Any]:
        """High-level system overview"""
        uptime = time.time() - self.start_time
        
        # Get last hour's data for rate calculations
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        recent_points = self._get_points_since(one_hour_ago)
        
        # Calculate metrics
        total_recent = len(recent_points)
        errors_recent = sum(1 for p in recent_points if p.status >= 400)
        durations = [p.duration_ms for p in recent_points]
        
        return {
            "uptime_seconds": int(uptime),
            "total_requests": self.total_requests,
            "requests_last_hour": total_recent,
            "requests_per_minute": round(total_recent / 60, 2) if total_recent > 0 else 0,
            "error_rate": round(errors_recent / total_recent, 4) if total_recent > 0 else 0,
            "avg_response_time_ms": round(statistics.mean(durations), 2) if durations else 0,
            "active_requests": self.active_requests,
            "data_retention_hours": self.retention_seconds / 3600
        }
    
    def get_request_analytics(self, period: str = "1h") -> Dict[str, Any]:
        """Detailed request analytics"""
        since = self._parse_period(period)
        points = self._get_points_since(since)
        
        # Aggregate by endpoint
        by_endpoint: Dict[str, int] = {}
        by_status: Dict[str, int] = {}
        by_method: Dict[str, int] = {}
        by_minute: Dict[str, int] = {}
        
        for p in points:
            by_endpoint[p.endpoint] = by_endpoint.get(p.endpoint, 0) + 1
            by_status[str(p.status)] = by_status.get(str(p.status), 0) + 1
            by_method[p.method] = by_method.get(p.method, 0) + 1
            
            # Truncate to minute for time series
            minute_key = p.timestamp.strftime("%Y-%m-%dT%H:%M:00Z")
            by_minute[minute_key] = by_minute.get(minute_key, 0) + 1
        
        # Convert minute data to sorted list
        time_series = [
            {"timestamp": ts, "count": count}
            for ts, count in sorted(by_minute.items())
        ]
        
        return {
            "period": period,
            "since": since.isoformat() + "Z",
            "total": len(points),
            "by_endpoint": dict(sorted(by_endpoint.items(), key=lambda x: -x[1])),
            "by_status": dict(sorted(by_status.items())),
            "by_method": by_method,
            "by_minute": time_series[-60:]  # Last 60 minutes max
        }
    
    def get_latency_analytics(self, period: str = "1h") -> Dict[str, Any]:
        """Response time analysis"""
        since = self._parse_period(period)
        points = self._get_points_since(since)
        
        if not points:
            return {
                "period": period,
                "since": since.isoformat() + "Z",
                "total_requests": 0,
                "overall": {"avg_ms": 0, "p50_ms": 0, "p95_ms": 0, "p99_ms": 0},
                "by_endpoint": {}
            }
        
        # Overall latency
        all_durations = [p.duration_ms for p in points]
        overall = self._calculate_percentiles(all_durations)
        
        # Per-endpoint latency
        by_endpoint: Dict[str, List[float]] = {}
        for p in points:
            if p.endpoint not in by_endpoint:
                by_endpoint[p.endpoint] = []
            by_endpoint[p.endpoint].append(p.duration_ms)
        
        endpoint_stats = {
            endpoint: self._calculate_percentiles(durations)
            for endpoint, durations in by_endpoint.items()
        }
        
        # Sort by avg latency descending
        endpoint_stats = dict(
            sorted(endpoint_stats.items(), key=lambda x: -x[1]["avg_ms"])
        )
        
        return {
            "period": period,
            "since": since.isoformat() + "Z",
            "total_requests": len(points),
            "overall": overall,
            "by_endpoint": endpoint_stats
        }
    
    def get_error_analytics(self, period: str = "24h") -> Dict[str, Any]:
        """Error breakdown and details"""
        since = self._parse_period(period)
        errors = self._get_errors_since(since)
        points = self._get_points_since(since)
        
        # Count errors by type
        by_type: Dict[str, int] = {}
        by_endpoint: Dict[str, int] = {}
        by_status: Dict[str, int] = {}
        
        for e in errors:
            by_type[e.error_type] = by_type.get(e.error_type, 0) + 1
            by_endpoint[e.endpoint] = by_endpoint.get(e.endpoint, 0) + 1
            by_status[str(e.status_code)] = by_status.get(str(e.status_code), 0) + 1
        
        # Recent errors (last 10)
        recent = [
            {
                "timestamp": e.timestamp.isoformat() + "Z",
                "endpoint": e.endpoint,
                "method": e.method,
                "error_type": e.error_type,
                "message": e.error_message[:200] if e.error_message else "",
                "status_code": e.status_code
            }
            for e in sorted(errors, key=lambda x: x.timestamp, reverse=True)[:10]
        ]
        
        total_requests = len(points)
        total_errors = len(errors)
        
        return {
            "period": period,
            "since": since.isoformat() + "Z",
            "total_requests": total_requests,
            "total_errors": total_errors,
            "error_rate": round(total_errors / total_requests, 4) if total_requests > 0 else 0,
            "by_type": dict(sorted(by_type.items(), key=lambda x: -x[1])),
            "by_endpoint": dict(sorted(by_endpoint.items(), key=lambda x: -x[1])),
            "by_status": dict(sorted(by_status.items())),
            "recent": recent
        }
    
    def _parse_period(self, period: str) -> datetime:
        """Convert period string to datetime"""
        now = datetime.utcnow()
        
        if period.endswith("m"):
            minutes = int(period[:-1])
            return now - timedelta(minutes=minutes)
        elif period.endswith("h"):
            hours = int(period[:-1])
            return now - timedelta(hours=hours)
        elif period.endswith("d"):
            days = int(period[:-1])
            return now - timedelta(days=days)
        else:
            # Default to 1 hour
            return now - timedelta(hours=1)
    
    def _calculate_percentiles(self, values: List[float]) -> Dict[str, float]:
        """Calculate latency percentiles"""
        if not values:
            return {"avg_ms": 0, "p50_ms": 0, "p95_ms": 0, "p99_ms": 0}
        
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        
        def percentile(p: float) -> float:
            idx = int(n * p)
            idx = min(idx, n - 1)
            return round(sorted_vals[idx], 2)
        
        return {
            "avg_ms": round(statistics.mean(values), 2),
            "min_ms": round(min(values), 2),
            "max_ms": round(max(values), 2),
            "p50_ms": percentile(0.50),
            "p95_ms": percentile(0.95),
            "p99_ms": percentile(0.99)
        }


# Global metrics instance
metrics = MetricsCollector(retention_seconds=86400)  # 24 hours
```

### File: `app/middleware.py`

```python
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import time
import traceback

from .metrics import metrics


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to collect request metrics automatically.
    
    Tracks:
    - Request duration
    - Status codes
    - Active request count
    - Error types
    """
    
    # Endpoints to exclude from metrics (health checks, metrics itself)
    EXCLUDE_PATHS = {"/health", "/health/ready", "/dashboard/overview"}
    
    async def dispatch(self, request: Request, call_next):
        # Skip metrics collection for excluded paths
        if request.url.path in self.EXCLUDE_PATHS:
            return await call_next(request)
        
        start_time = time.time()
        metrics.active_requests += 1
        
        error_type = None
        error_message = None
        status_code = 500
        
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
            
        except Exception as e:
            error_type = type(e).__name__
            error_message = str(e)
            raise
            
        finally:
            metrics.active_requests -= 1
            duration_ms = (time.time() - start_time) * 1000
            
            # Record the metric
            metrics.record_request(
                endpoint=request.url.path,
                method=request.method,
                status=status_code,
                duration_ms=duration_ms,
                error_type=error_type,
                error_message=error_message
            )
```

### File: `app/main.py`

```python
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import time
import random

from .metrics import metrics
from .middleware import MetricsMiddleware

app = FastAPI(title="Monitoring Dashboard Demo")

# Add metrics middleware
app.add_middleware(MetricsMiddleware)


class PredictRequest(BaseModel):
    text: str


class PredictResponse(BaseModel):
    sentiment: str
    confidence: float


# ==================== ML Endpoint ====================

@app.post("/predict", response_model=PredictResponse)
def predict(data: PredictRequest):
    """Mock ML prediction endpoint with variable latency"""
    
    # Simulate variable processing time (50-500ms)
    latency = random.uniform(0.05, 0.5)
    time.sleep(latency)
    
    # Occasionally fail for testing error tracking
    if random.random() < 0.05:  # 5% error rate
        raise HTTPException(status_code=500, detail="Random ML failure")
    
    # Mock sentiment analysis
    text_lower = data.text.lower()
    if any(w in text_lower for w in ["great", "amazing", "love", "excellent"]):
        return PredictResponse(sentiment="positive", confidence=0.92)
    elif any(w in text_lower for w in ["bad", "terrible", "hate", "awful"]):
        return PredictResponse(sentiment="negative", confidence=0.88)
    return PredictResponse(sentiment="neutral", confidence=0.75)


# ==================== Dashboard Endpoints ====================

@app.get("/dashboard/overview")
def dashboard_overview():
    """
    High-level system overview.
    
    Returns key metrics at a glance:
    - Uptime
    - Request volume
    - Error rate
    - Average latency
    - Active connections
    """
    return metrics.get_overview()


@app.get("/dashboard/requests")
def dashboard_requests(
    period: str = Query("1h", regex="^[0-9]+[mhd]$", description="Time period: 30m, 1h, 24h, 7d")
):
    """
    Detailed request analytics.
    
    Breakdowns by:
    - Endpoint
    - Status code
    - HTTP method
    - Time (per minute)
    """
    return metrics.get_request_analytics(period)


@app.get("/dashboard/latency")
def dashboard_latency(
    period: str = Query("1h", regex="^[0-9]+[mhd]$", description="Time period: 30m, 1h, 24h, 7d")
):
    """
    Response time analysis.
    
    Percentiles (p50, p95, p99) overall and per endpoint.
    """
    return metrics.get_latency_analytics(period)


@app.get("/dashboard/errors")
def dashboard_errors(
    period: str = Query("24h", regex="^[0-9]+[mhd]$", description="Time period: 30m, 1h, 24h, 7d")
):
    """
    Error breakdown and recent errors.
    
    Groups by error type, endpoint, and status code.
    Shows 10 most recent errors with details.
    """
    return metrics.get_error_analytics(period)


# ==================== Health Endpoints ====================

@app.get("/health")
def health():
    """Basic liveness check"""
    return {"status": "healthy"}


@app.get("/health/ready")
def health_ready():
    """Readiness check with system stats"""
    overview = metrics.get_overview()
    return {
        "status": "ready",
        "uptime_seconds": overview["uptime_seconds"],
        "active_requests": overview["active_requests"]
    }


# ==================== Error Handling ====================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Capture HTTP exceptions for metrics"""
    metrics.record_request(
        endpoint=request.url.path,
        method=request.method,
        status=exc.status_code,
        duration_ms=0,  # Will be recorded by middleware
        error_type="HTTPException",
        error_message=exc.detail
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Capture unhandled exceptions for metrics"""
    metrics.record_request(
        endpoint=request.url.path,
        method=request.method,
        status=500,
        duration_ms=0,
        error_type=type(exc).__name__,
        error_message=str(exc)
    )
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )
```

---

## Key Insights

### 1. What to Measure

**The Four Golden Signals (Google SRE):**
- **Latency**: Response time distribution, not just average
- **Traffic**: Request rate and volume
- **Errors**: Error rate and types
- **Saturation**: Active requests, queue depth

### 2. Time-Series Storage Efficiency

```python
# deque with maxlen is O(1) for append and popleft
# Perfect for sliding window metrics
from collections import deque

# Cleanup strategy: lazy cleanup on access
# Don't waste cycles cleaning up constantly
def _cleanup(self):
    cutoff = datetime.utcnow() - timedelta(seconds=self.retention)
    while self.points and self.points[0].timestamp < cutoff:
        self.points.popleft()  # O(1) removal
```

### 3. Percentile Calculation

P95 means 95% of requests are faster than this value. It's more useful than average because it captures tail latency.

```python
def percentile(values: list, p: float) -> float:
    """
    Simple percentile calculation.
    For production, consider:
    - T-Digest for streaming percentiles
    - Histogram approximation for memory efficiency
    """
    sorted_vals = sorted(values)
    idx = int(len(sorted_vals) * p)
    return sorted_vals[min(idx, len(sorted_vals) - 1)]
```

### 4. Middleware Pattern

Middleware captures ALL requests automatically without modifying endpoint code:

```python
class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Before request
        start = time.time()
        metrics.active_requests += 1
        
        try:
            response = await call_next(request)
            return response
        finally:
            # After request (always runs)
            metrics.active_requests -= 1
            duration = time.time() - start
            metrics.record(...)
```

### 5. Production Considerations

**In-Memory Limitations:**
- Lost on restart
- Single server only
- Memory growth

**Production Solutions:**
- **Prometheus** + **Grafana** for metrics
- **StatsD** for aggregation
- **InfluxDB** for time-series storage
- **OpenTelemetry** for standardized instrumentation

---

## Testing Commands

```bash
# Start server
uvicorn app.main:app --reload

# Generate varied traffic (positive, negative, neutral)
for i in {1..50}; do
    curl -s -X POST http://localhost:8000/predict \
        -H "Content-Type: application/json" \
        -d '{"text": "This is amazing!"}' &
    curl -s -X POST http://localhost:8000/predict \
        -H "Content-Type: application/json" \
        -d '{"text": "This is terrible!"}' &
    curl -s -X POST http://localhost:8000/predict \
        -H "Content-Type: application/json" \
        -d '{"text": "This is okay"}' &
done
wait

# Generate some validation errors
for i in {1..10}; do
    curl -s -X POST http://localhost:8000/predict \
        -H "Content-Type: application/json" \
        -d '{}' &
done
wait

# Check dashboard endpoints
echo "=== Overview ==="
curl -s http://localhost:8000/dashboard/overview | jq

echo "=== Requests (last hour) ==="
curl -s "http://localhost:8000/dashboard/requests?period=1h" | jq

echo "=== Latency (last hour) ==="
curl -s "http://localhost:8000/dashboard/latency?period=1h" | jq

echo "=== Errors (last 24h) ==="
curl -s "http://localhost:8000/dashboard/errors?period=24h" | jq
```

---

## Interview Questions

**Q: Why use percentiles instead of averages?**
A: Averages hide outliers. If 99% of requests take 50ms but 1% take 10 seconds, the average might look fine (150ms) but users are having terrible experiences. P95/P99 reveal tail latency issues.

**Q: How would you scale this for distributed systems?**
A: Use centralized metrics collection (Prometheus, StatsD) where each server pushes metrics. Use pre-aggregation at each node to reduce network traffic. Consider sampling for high-volume systems.

**Q: What's the memory impact of storing all requests?**
A: With 1000 req/sec and 24h retention, that's 86.4M data points. Each MetricPoint is ~200 bytes, so ~17GB. In production, use aggregation (per-minute buckets) or sampling to reduce memory.

---

## Time to Implement: 60-75 minutes
