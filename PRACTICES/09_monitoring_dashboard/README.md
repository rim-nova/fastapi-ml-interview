# Practice 09: Monitoring Dashboard

**Difficulty:** ⭐⭐⭐ (Medium-Hard)  
**Time Estimate:** 60-75 minutes  
**Job Requirement:** "Build internal dashboards and tools"

---

## 📝 Problem Statement

Your ML API is in production, but you have no visibility into its performance. Build a monitoring dashboard that provides real-time insights into your system's health, performance, and usage patterns.

### Requirements

1. **Metrics Collection**
   - Request count (total, per endpoint, per status)
   - Response time distribution (avg, p50, p95, p99)
   - Active requests (concurrency)
   - Error rates by type

2. **Time-Series Data**
   - Store metrics with timestamps
   - Support time range queries (last 1h, 24h, 7d)
   - Calculate rolling averages

3. **Dashboard Endpoints**
   - GET /dashboard/overview - high-level stats
   - GET /dashboard/requests - request analytics
   - GET /dashboard/errors - error breakdown
   - GET /dashboard/latency - response time analysis

4. **Alerting (Bonus)**
   - Define thresholds
   - Track threshold violations
   - Simple alert history

### Example Usage

```bash
# After some API traffic...

# Get overview
curl http://localhost:8000/dashboard/overview
# {
#   "uptime_seconds": 3600,
#   "total_requests": 15000,
#   "requests_per_minute": 25.5,
#   "error_rate": 0.02,
#   "avg_response_time_ms": 45,
#   "active_requests": 3
# }

# Request analytics
curl "http://localhost:8000/dashboard/requests?period=1h"
# {
#   "period": "1h",
#   "total": 1500,
#   "by_endpoint": {
#     "/predict": 1200,
#     "/health": 300
#   },
#   "by_status": {
#     "200": 1450,
#     "400": 30,
#     "500": 20
#   },
#   "by_minute": [
#     {"timestamp": "2024-01-15T10:00:00Z", "count": 25},
#     {"timestamp": "2024-01-15T10:01:00Z", "count": 28}
#   ]
# }

# Latency analysis
curl "http://localhost:8000/dashboard/latency?period=1h"
# {
#   "period": "1h",
#   "avg_ms": 45,
#   "p50_ms": 35,
#   "p95_ms": 120,
#   "p99_ms": 250,
#   "by_endpoint": {
#     "/predict": {"avg": 150, "p95": 300},
#     "/health": {"avg": 2, "p95": 5}
#   }
# }

# Error breakdown
curl "http://localhost:8000/dashboard/errors?period=24h"
# {
#   "period": "24h",
#   "total_errors": 50,
#   "by_type": {
#     "ValidationError": 30,
#     "TimeoutError": 15,
#     "InternalError": 5
#   },
#   "recent": [
#     {"timestamp": "...", "endpoint": "/predict", "error": "ValidationError", "message": "..."}
#   ]
# }
```

---

## 🎯 Learning Objectives

1. **Metrics Design** - What to measure and why
2. **Time-Series Storage** - Efficient data structures for time data
3. **Percentile Calculations** - Understanding p50/p95/p99
4. **Middleware Pattern** - Intercepting requests for metrics
5. **Dashboard UX** - Presenting data meaningfully

---

## 💡 Hints

<details>
<summary>Hint 1: Metrics collection middleware</summary>

```python
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import time

class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.time()
        metrics.active_requests += 1
        
        try:
            response = await call_next(request)
            duration_ms = (time.time() - start) * 1000
            
            metrics.record_request(
                endpoint=request.url.path,
                method=request.method,
                status=response.status_code,
                duration_ms=duration_ms
            )
            
            return response
        finally:
            metrics.active_requests -= 1
```
</details>

<details>
<summary>Hint 2: Time-series storage structure</summary>

```python
from collections import deque
from dataclasses import dataclass
from datetime import datetime
import threading

@dataclass
class MetricPoint:
    timestamp: datetime
    endpoint: str
    method: str
    status: int
    duration_ms: float

class TimeSeriesStore:
    def __init__(self, max_age_seconds: int = 86400):  # 24h default
        self.points: deque = deque()
        self.max_age = max_age_seconds
        self.lock = threading.Lock()
    
    def add(self, point: MetricPoint):
        with self.lock:
            self.points.append(point)
            self._cleanup()
    
    def _cleanup(self):
        cutoff = datetime.utcnow().timestamp() - self.max_age
        while self.points and self.points[0].timestamp.timestamp() < cutoff:
            self.points.popleft()
    
    def query(self, since: datetime) -> list:
        with self.lock:
            return [p for p in self.points if p.timestamp >= since]
```
</details>

<details>
<summary>Hint 3: Percentile calculation</summary>

```python
import statistics

def calculate_percentiles(values: list[float]) -> dict:
    if not values:
        return {"avg": 0, "p50": 0, "p95": 0, "p99": 0}
    
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    
    return {
        "avg": round(statistics.mean(values), 2),
        "p50": sorted_vals[int(n * 0.50)],
        "p95": sorted_vals[int(n * 0.95)] if n > 20 else sorted_vals[-1],
        "p99": sorted_vals[int(n * 0.99)] if n > 100 else sorted_vals[-1]
    }
```
</details>

---

## ✅ Success Criteria

- [ ] All dashboard endpoints return meaningful data
- [ ] Metrics update in real-time as requests come in
- [ ] Time range filtering works correctly
- [ ] Percentiles are calculated accurately
- [ ] Dashboard handles high request volumes efficiently
- [ ] No significant performance impact from metrics collection

---

## 🧪 Testing Commands

```bash
# Start the server
uvicorn app.main:app --reload

# Generate test traffic
for i in {1..100}; do
    curl -s http://localhost:8000/predict \
        -H "Content-Type: application/json" \
        -d '{"text": "test message '$i'"}' &
done
wait

# Some error traffic
for i in {1..10}; do
    curl -s http://localhost:8000/predict \
        -H "Content-Type: application/json" \
        -d '{"invalid": "data"}' &
done
wait

# Check dashboard
curl http://localhost:8000/dashboard/overview | jq
curl "http://localhost:8000/dashboard/requests?period=1h" | jq
curl "http://localhost:8000/dashboard/latency?period=1h" | jq
curl "http://localhost:8000/dashboard/errors?period=1h" | jq
```

---

## Time to Implement: 60-75 minutes
