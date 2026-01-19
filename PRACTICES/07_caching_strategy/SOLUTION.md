# Solution: Caching Strategy

## Approach

This solution implements an in-memory cache with TTL (Time-To-Live) to avoid redundant ML inference for identical inputs. Key features:

1. **Cache Key Generation**: SHA256 hash of normalized text
2. **TTL-based Expiration**: Default 1 hour, configurable
3. **LRU Eviction**: Removes oldest entries when max size reached
4. **Thread Safety**: Uses Lock for concurrent access
5. **Cache Headers**: Returns X-Cache (HIT/MISS) in response

---

## Architecture

```
Request → Normalize Text → Generate Cache Key → Check Cache
                                                     ↓
                                           ┌────────┴────────┐
                                           │                 │
                                         HIT               MISS
                                           │                 │
                                    Return Cached      Run ML Inference
                                    (X-Cache: HIT)           │
                                                        Store in Cache
                                                        (X-Cache: MISS)
```

---

## Key Implementation Details

### 1. Cache Class with TTL

```python
import hashlib
import time
from threading import Lock
from typing import Optional, Any
from dataclasses import dataclass

@dataclass
class CacheEntry:
    value: Any
    created_at: float
    last_accessed: float

class InMemoryCache:
    """Thread-safe in-memory cache with TTL and LRU eviction."""
    
    def __init__(self, ttl_seconds: int = 3600, max_size: int = 10000):
        self._cache: dict[str, CacheEntry] = {}
        self._lock = Lock()
        self._ttl = ttl_seconds
        self._max_size = max_size
        self._hits = 0
        self._misses = 0
    
    def _generate_key(self, text: str) -> str:
        """Generate cache key from normalized text."""
        # Normalize: lowercase, strip whitespace, collapse multiple spaces
        normalized = " ".join(text.lower().strip().split())
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]
    
    def get(self, text: str) -> Optional[dict]:
        """Get cached result for text. Returns None if not found or expired."""
        key = self._generate_key(text)
        
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None
            
            entry = self._cache[key]
            
            # Check TTL
            if time.time() - entry.created_at > self._ttl:
                del self._cache[key]
                self._misses += 1
                return None
            
            # Update access time (for LRU)
            entry.last_accessed = time.time()
            self._hits += 1
            return entry.value
    
    def set(self, text: str, value: dict) -> str:
        """Store result in cache. Returns cache key."""
        key = self._generate_key(text)
        now = time.time()
        
        with self._lock:
            # Evict if at capacity (LRU)
            if len(self._cache) >= self._max_size and key not in self._cache:
                self._evict_lru()
            
            self._cache[key] = CacheEntry(
                value=value,
                created_at=now,
                last_accessed=now
            )
        
        return key
    
    def _evict_lru(self):
        """Remove least recently used entry."""
        if not self._cache:
            return
        
        oldest_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k].last_accessed
        )
        del self._cache[oldest_key]
    
    def clear(self):
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
    
    def stats(self) -> dict:
        """Return cache statistics."""
        with self._lock:
            total = self._hits + self._misses
            return {
                "size": len(self._cache),
                "max_size": self._max_size,
                "ttl_seconds": self._ttl,
                "hits": self._hits,
                "misses": self._misses,
                "hit_ratio": round(self._hits / total, 3) if total > 0 else 0,
                "memory_mb": self._estimate_memory_mb()
            }
    
    def _estimate_memory_mb(self) -> float:
        """Rough estimate of cache memory usage."""
        import sys
        total_bytes = sum(
            sys.getsizeof(k) + sys.getsizeof(v.value)
            for k, v in self._cache.items()
        )
        return round(total_bytes / (1024 * 1024), 2)
```

### 2. Integration with FastAPI

```python
from fastapi import FastAPI, Depends, BackgroundTasks, Response, Header
from typing import Optional

app = FastAPI()

# Global cache instance
cache = InMemoryCache(ttl_seconds=3600, max_size=10000)

@app.post("/predict")
def predict(
    request: JobCreate,
    response: Response,
    background_tasks: BackgroundTasks,
    cache_control: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    ML prediction with caching.
    
    Headers:
    - Cache-Control: no-cache - Skip cache lookup
    
    Response Headers:
    - X-Cache: HIT or MISS
    - X-Cache-Key: The cache key used
    """
    
    # Generate cache key
    cache_key = cache._generate_key(request.text)
    response.headers["X-Cache-Key"] = cache_key
    
    # Check cache (unless Cache-Control: no-cache)
    if cache_control != "no-cache":
        cached_result = cache.get(request.text)
        if cached_result:
            response.headers["X-Cache"] = "HIT"
            return {
                "job_id": cached_result["job_id"],
                "status": "completed",
                "result": cached_result["result"],
                "cached": True
            }
    
    # Cache miss - run inference
    response.headers["X-Cache"] = "MISS"
    
    # Create job
    job_id = str(uuid.uuid4())
    new_job = models.MLJob(
        job_uuid=job_id,
        input_text=request.text,
        status="processing"
    )
    db.add(new_job)
    db.commit()
    
    # Start background processing (will cache result)
    background_tasks.add_task(
        process_and_cache,
        job_id,
        request.text
    )
    
    return {
        "job_id": job_id,
        "status": "processing",
        "cached": False
    }

def process_and_cache(job_id: str, text: str):
    """Process ML job and cache the result."""
    db = SessionLocal()
    try:
        # Simulate ML inference
        time.sleep(5)
        
        result = {
            "sentiment": "positive",
            "confidence": 0.95
        }
        
        # Update database
        job = db.query(models.MLJob).filter(
            models.MLJob.job_uuid == job_id
        ).first()
        
        if job:
            job.status = "completed"
            job.result_label = result["sentiment"]
            job.result_score = result["confidence"]
            db.commit()
        
        # Cache the result
        cache.set(text, {
            "job_id": job_id,
            "result": result
        })
        
        print(f"✅ Cached result for job {job_id}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

@app.get("/cache/stats")
def get_cache_stats():
    """Return cache statistics."""
    return cache.stats()

@app.delete("/cache")
def clear_cache():
    """Clear entire cache."""
    cache.clear()
    return {"message": "Cache cleared"}
```

---

## Complete Solution Files

### File: `app/cache.py`

```python
import hashlib
import time
import sys
from threading import Lock
from typing import Optional, Any, Dict
from dataclasses import dataclass

@dataclass
class CacheEntry:
    """Single cache entry with metadata."""
    value: Any
    created_at: float
    last_accessed: float

class InMemoryCache:
    """
    Thread-safe in-memory cache with TTL and LRU eviction.
    
    Features:
    - TTL-based expiration
    - LRU eviction when at capacity
    - Thread-safe with Lock
    - Statistics tracking (hits, misses, hit ratio)
    """
    
    def __init__(self, ttl_seconds: int = 3600, max_size: int = 10000):
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = Lock()
        self._ttl = ttl_seconds
        self._max_size = max_size
        self._hits = 0
        self._misses = 0
    
    def _generate_key(self, text: str) -> str:
        """
        Generate cache key from normalized text.
        
        Normalization:
        1. Convert to lowercase
        2. Strip leading/trailing whitespace
        3. Collapse multiple spaces to single space
        """
        normalized = " ".join(text.lower().strip().split())
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]
    
    def get(self, text: str) -> Optional[dict]:
        """
        Get cached result for text.
        
        Returns:
            Cached value if found and not expired, None otherwise.
        """
        key = self._generate_key(text)
        
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None
            
            entry = self._cache[key]
            
            # Check TTL expiration
            if time.time() - entry.created_at > self._ttl:
                del self._cache[key]
                self._misses += 1
                return None
            
            # Update access time for LRU tracking
            entry.last_accessed = time.time()
            self._hits += 1
            return entry.value
    
    def set(self, text: str, value: dict) -> str:
        """
        Store result in cache.
        
        Returns:
            The cache key used.
        """
        key = self._generate_key(text)
        now = time.time()
        
        with self._lock:
            # Evict LRU entry if at capacity
            if len(self._cache) >= self._max_size and key not in self._cache:
                self._evict_lru()
            
            self._cache[key] = CacheEntry(
                value=value,
                created_at=now,
                last_accessed=now
            )
        
        return key
    
    def _evict_lru(self):
        """Remove least recently used entry."""
        if not self._cache:
            return
        
        # Find entry with oldest last_accessed time
        oldest_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k].last_accessed
        )
        del self._cache[oldest_key]
    
    def delete(self, text: str) -> bool:
        """Delete specific entry. Returns True if found and deleted."""
        key = self._generate_key(text)
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def clear(self):
        """Clear all cache entries and reset stats."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
    
    def stats(self) -> dict:
        """Return cache statistics."""
        with self._lock:
            total = self._hits + self._misses
            return {
                "size": len(self._cache),
                "max_size": self._max_size,
                "ttl_seconds": self._ttl,
                "hits": self._hits,
                "misses": self._misses,
                "hit_ratio": round(self._hits / total, 3) if total > 0 else 0,
                "memory_mb": self._estimate_memory_mb()
            }
    
    def _estimate_memory_mb(self) -> float:
        """Rough estimate of cache memory usage in MB."""
        total_bytes = sum(
            sys.getsizeof(k) + sys.getsizeof(v.value)
            for k, v in self._cache.items()
        )
        return round(total_bytes / (1024 * 1024), 2)

# Global cache instance
prediction_cache = InMemoryCache(ttl_seconds=3600, max_size=10000)
```

### File: `app/main.py`

```python
from fastapi import FastAPI, Depends, BackgroundTasks, Response, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Optional
import time
import uuid

from . import models, schemas
from .database import engine, get_db, SessionLocal
from .cache import prediction_cache

# Create tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="ML API with Caching",
    description="Production ML API with intelligent caching",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "ML API with Caching is running"}

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/predict")
def predict(
    request: schemas.JobCreate,
    response: Response,
    background_tasks: BackgroundTasks,
    cache_control: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Create ML prediction with caching.
    
    Cache behavior:
    - Cache hit: Returns immediately with cached result
    - Cache miss: Creates background job, caches on completion
    
    Headers:
    - Cache-Control: no-cache - Force cache bypass
    
    Response headers:
    - X-Cache: HIT or MISS
    - X-Cache-Key: Hash of normalized input
    """
    # Generate cache key for response header
    cache_key = prediction_cache._generate_key(request.text)
    response.headers["X-Cache-Key"] = cache_key
    
    # Check cache (unless bypassed)
    if cache_control != "no-cache":
        cached = prediction_cache.get(request.text)
        if cached:
            response.headers["X-Cache"] = "HIT"
            return {
                "job_id": cached["job_id"],
                "status": "completed",
                "result": cached["result"],
                "cached": True
            }
    
    # Cache miss
    response.headers["X-Cache"] = "MISS"
    
    # Create new job
    job_id = str(uuid.uuid4())
    job = models.MLJob(
        job_uuid=job_id,
        input_text=request.text,
        status="processing"
    )
    db.add(job)
    db.commit()
    
    # Process in background (will cache result)
    background_tasks.add_task(process_and_cache, job_id, request.text)
    
    return {
        "job_id": job_id,
        "status": "processing",
        "cached": False
    }

@app.get("/jobs/{job_id}")
def get_job(job_id: str, db: Session = Depends(get_db)):
    """Get job status and result."""
    job = db.query(models.MLJob).filter(
        models.MLJob.job_uuid == job_id
    ).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    result = None
    if job.status == "completed":
        result = {
            "sentiment": job.result_label,
            "confidence": job.result_score
        }
    
    return {
        "job_id": job.job_uuid,
        "status": job.status,
        "result": result
    }

@app.get("/cache/stats")
def cache_stats():
    """Get cache statistics."""
    return prediction_cache.stats()

@app.delete("/cache")
def clear_cache():
    """Clear the entire cache."""
    prediction_cache.clear()
    return {"message": "Cache cleared", "stats": prediction_cache.stats()}

# ============================================
# BACKGROUND PROCESSING
# ============================================

def process_and_cache(job_id: str, text: str):
    """Process ML inference and cache the result."""
    db = SessionLocal()
    try:
        # Simulate ML inference (5 second delay)
        time.sleep(5)
        
        # Mock ML result
        sentiment = "positive" if any(
            word in text.lower()
            for word in ["good", "great", "love", "amazing", "excellent"]
        ) else "negative" if any(
            word in text.lower()
            for word in ["bad", "terrible", "hate", "awful", "horrible"]
        ) else "neutral"
        
        confidence = 0.95
        
        # Update database
        job = db.query(models.MLJob).filter(
            models.MLJob.job_uuid == job_id
        ).first()
        
        if job:
            job.status = "completed"
            job.result_label = sentiment
            job.result_score = confidence
            db.commit()
        
        # Cache the result for future identical requests
        prediction_cache.set(text, {
            "job_id": job_id,
            "result": {
                "sentiment": sentiment,
                "confidence": confidence
            }
        })
        
        print(f"✅ Job {job_id} completed and cached: {sentiment}")
        
    except Exception as e:
        print(f"❌ Job {job_id} failed: {e}")
        job = db.query(models.MLJob).filter(
            models.MLJob.job_uuid == job_id
        ).first()
        if job:
            job.status = "failed"
            db.commit()
    finally:
        db.close()
```

---

## Testing Commands

```bash
# Test 1: First request (cache miss)
curl -i -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "This is a great product!"}'
# Look for: X-Cache: MISS

# Test 2: Wait 5 seconds, check status
curl http://localhost:8000/jobs/YOUR_JOB_ID

# Test 3: Same request again (cache hit)
curl -i -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "This is a great product!"}'
# Look for: X-Cache: HIT

# Test 4: Bypass cache
curl -i -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -H "Cache-Control: no-cache" \
  -d '{"text": "This is a great product!"}'
# Look for: X-Cache: MISS (forced)

# Test 5: Check cache stats
curl http://localhost:8000/cache/stats

# Test 6: Clear cache
curl -X DELETE http://localhost:8000/cache
```

---

## Key Patterns

### 1. Cache Key Normalization
```python
# "  Hello   World  " and "hello world" produce same key
normalized = " ".join(text.lower().strip().split())
key = hashlib.sha256(normalized.encode()).hexdigest()[:16]
```

### 2. Thread-Safe Operations
```python
with self._lock:
    # All cache operations are atomic
    if key in self._cache:
        return self._cache[key]
```

### 3. TTL Expiration Check
```python
if time.time() - entry.created_at > self._ttl:
    del self._cache[key]  # Lazy expiration
    return None
```

### 4. LRU Eviction
```python
# Find oldest by last_accessed timestamp
oldest_key = min(
    self._cache.keys(),
    key=lambda k: self._cache[k].last_accessed
)
del self._cache[oldest_key]
```

---

## Interview Questions & Answers

**Q1: "Why use in-memory cache instead of Redis?"**

A: Trade-offs:
- In-memory: Zero latency, simple setup, but single-server only
- Redis: Network hop (~1ms), works across servers, persistent

**For interviews:** Start with in-memory, mention Redis for production multi-server deployments.

**Q2: "How do you handle cache invalidation?"**

A: Several strategies:
1. **TTL-based**: Entries expire after set time (this solution)
2. **Event-based**: Invalidate when source data changes
3. **Version-based**: Include version in cache key

**Q3: "What's your cache key strategy?"**

A: Normalize input → Hash → Truncate:
```python
normalized = " ".join(text.lower().strip().split())
key = sha256(normalized)[:16]
```

This ensures "Hello World" and "hello   world" hit the same cache entry.

---

## Production Considerations

1. **Use Redis** for multi-server deployments
2. **Monitor hit ratio** - Target 60%+ for ML caches
3. **Set appropriate TTL** based on data freshness requirements
4. **Consider cache warming** for predictable queries
5. **Add cache bypass** headers for debugging

**Time to implement from scratch: 45-60 minutes**
