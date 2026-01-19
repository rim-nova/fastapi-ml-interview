# Practice 07: Caching Strategy

**Difficulty:** ⭐⭐⭐ (Medium-Hard)  
**Time Estimate:** 45-60 minutes  
**Job Requirement:** "Optimize... meet latency, throughput, caching"

---

## 📝 Problem Statement

Your ML inference is expensive (5 seconds per request). Many users send identical texts. Implement caching to avoid redundant processing.

### Requirements

1. **Cache Layer**
   - Cache ML results by input text hash
   - Configurable TTL (time-to-live)
   - Support both in-memory and Redis

2. **Cache Control**
   - `Cache-Control` header support
   - Force cache bypass option
   - Cache invalidation endpoint

3. **Cache Metrics**
   - Hit/miss ratio
   - Cache size
   - Eviction count

4. **Smart Caching**
   - Only cache successful results
   - Consider input normalization

### Example Usage

```bash
# First request - cache miss (5 seconds)
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "This product is amazing!"}'

# Response headers:
# X-Cache: MISS
# X-Cache-Key: hash123...

# Second identical request - cache hit (instant)
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "This product is amazing!"}'

# Response headers:
# X-Cache: HIT

# Force bypass cache
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -H "Cache-Control: no-cache" \
  -d '{"text": "This product is amazing!"}'

# Cache stats
curl http://localhost:8000/cache/stats
# {
#   "hits": 150,
#   "misses": 50,
#   "hit_ratio": 0.75,
#   "size": 200,
#   "memory_mb": 15.5
# }

# Clear cache
curl -X DELETE http://localhost:8000/cache
```

---

## 🎯 Learning Objectives

1. **Cache Strategies** - When and what to cache
2. **Cache Keys** - Designing effective keys
3. **TTL Management** - Expiration policies
4. **Cache Invalidation** - The hardest problem in CS
5. **Hit Ratio Optimization** - Measuring cache effectiveness

---

## 💡 Hints

<details>
<summary>Hint 1: Simple in-memory cache</summary>

```python
from functools import lru_cache
import hashlib
import time

class SimpleCache:
    def __init__(self, ttl_seconds: int = 3600):
        self.cache = {}
        self.ttl = ttl_seconds
        self.hits = 0
        self.misses = 0
    
    def _hash_key(self, text: str) -> str:
        normalized = text.lower().strip()
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]
    
    def get(self, text: str):
        key = self._hash_key(text)
        if key in self.cache:
            value, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                self.hits += 1
                return value
            del self.cache[key]
        self.misses += 1
        return None
    
    def set(self, text: str, value: dict):
        key = self._hash_key(text)
        self.cache[key] = (value, time.time())
    
    def stats(self):
        total = self.hits + self.misses
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_ratio": self.hits / total if total > 0 else 0,
            "size": len(self.cache)
        }

cache = SimpleCache(ttl_seconds=3600)
```
</details>

<details>
<summary>Hint 2: Redis cache implementation</summary>

```python
import redis
import json

class RedisCache:
    def __init__(self, host="localhost", port=6379, ttl=3600):
        self.client = redis.Redis(host=host, port=port, decode_responses=True)
        self.ttl = ttl
        self.prefix = "ml_cache:"
    
    def _key(self, text: str) -> str:
        normalized = text.lower().strip()
        hash_val = hashlib.sha256(normalized.encode()).hexdigest()[:16]
        return f"{self.prefix}{hash_val}"
    
    def get(self, text: str):
        key = self._key(text)
        value = self.client.get(key)
        if value:
            self.client.incr("cache:hits")
            return json.loads(value)
        self.client.incr("cache:misses")
        return None
    
    def set(self, text: str, value: dict):
        key = self._key(text)
        self.client.setex(key, self.ttl, json.dumps(value))
```
</details>

---

## ✅ Success Criteria

- [ ] Identical requests return cached results
- [ ] Cache headers indicate hit/miss
- [ ] Cache bypass works with header
- [ ] Stats endpoint shows hit ratio
- [ ] Cache expires after TTL
- [ ] Invalidation clears cache

---

# Solution: Caching Strategy

## Complete Implementation

### File: `app/cache.py`

```python
import hashlib
import time
import json
from typing import Optional, Dict, Any
from dataclasses import dataclass
from threading import Lock
import os

@dataclass
class CacheEntry:
    value: Dict[str, Any]
    created_at: float
    hits: int = 0

class InMemoryCache:
    """Thread-safe in-memory cache with TTL"""
    
    def __init__(self, ttl_seconds: int = 3600, max_size: int = 10000):
        self.cache: Dict[str, CacheEntry] = {}
        self.ttl = ttl_seconds
        self.max_size = max_size
        self.lock = Lock()
        self.total_hits = 0
        self.total_misses = 0
        self.evictions = 0
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for consistent caching"""
        return " ".join(text.lower().strip().split())
    
    def _hash_key(self, text: str) -> str:
        """Generate cache key from text"""
        normalized = self._normalize_text(text)
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]
    
    def _is_expired(self, entry: CacheEntry) -> bool:
        return time.time() - entry.created_at > self.ttl
    
    def _evict_if_needed(self):
        """Evict oldest entries if cache is full"""
        if len(self.cache) >= self.max_size:
            # Remove 10% oldest entries
            sorted_entries = sorted(
                self.cache.items(),
                key=lambda x: x[1].created_at
            )
            to_remove = len(sorted_entries) // 10
            for key, _ in sorted_entries[:to_remove]:
                del self.cache[key]
                self.evictions += 1
    
    def get(self, text: str) -> tuple[Optional[Dict], str]:
        """
        Get cached value.
        Returns (value, cache_key) or (None, cache_key)
        """
        key = self._hash_key(text)
        
        with self.lock:
            if key in self.cache:
                entry = self.cache[key]
                if not self._is_expired(entry):
                    entry.hits += 1
                    self.total_hits += 1
                    return entry.value, key
                else:
                    del self.cache[key]
            
            self.total_misses += 1
            return None, key
    
    def set(self, text: str, value: Dict[str, Any]) -> str:
        """Store value in cache. Returns cache key."""
        key = self._hash_key(text)
        
        with self.lock:
            self._evict_if_needed()
            self.cache[key] = CacheEntry(
                value=value,
                created_at=time.time()
            )
        
        return key
    
    def delete(self, text: str) -> bool:
        """Delete specific entry"""
        key = self._hash_key(text)
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False
    
    def clear(self):
        """Clear entire cache"""
        with self.lock:
            self.cache.clear()
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.total_hits + self.total_misses
        
        with self.lock:
            # Calculate memory usage (rough estimate)
            memory_bytes = sum(
                len(json.dumps(e.value)) 
                for e in self.cache.values()
            )
        
        return {
            "hits": self.total_hits,
            "misses": self.total_misses,
            "hit_ratio": round(self.total_hits / total_requests, 4) if total_requests > 0 else 0,
            "size": len(self.cache),
            "max_size": self.max_size,
            "evictions": self.evictions,
            "ttl_seconds": self.ttl,
            "memory_mb": round(memory_bytes / (1024 * 1024), 2)
        }

# Global cache instance
cache = InMemoryCache(
    ttl_seconds=int(os.getenv("CACHE_TTL", 3600)),
    max_size=int(os.getenv("CACHE_MAX_SIZE", 10000))
)
```

### File: `app/main.py`

```python
from fastapi import FastAPI, Depends, Request, Header
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import uuid
import time
from typing import Optional

from . import models, schemas
from .database import engine, get_db
from .cache import cache

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Caching Demo API")

def mock_ml_inference(text: str) -> dict:
    """Expensive ML inference (5 seconds)"""
    time.sleep(5)
    text_lower = text.lower()
    if any(w in text_lower for w in ["great", "amazing", "love"]):
        return {"sentiment": "positive", "confidence": 0.95}
    elif any(w in text_lower for w in ["bad", "terrible", "hate"]):
        return {"sentiment": "negative", "confidence": 0.91}
    return {"sentiment": "neutral", "confidence": 0.75}

@app.post("/predict")
def predict(
    data: schemas.JobCreate,
    cache_control: Optional[str] = Header(None, alias="Cache-Control")
):
    """Predict with caching"""
    bypass_cache = cache_control == "no-cache"
    
    # Try cache first (unless bypassed)
    if not bypass_cache:
        cached_result, cache_key = cache.get(data.text)
        if cached_result:
            response = JSONResponse(content={
                "result": cached_result,
                "cached": True
            })
            response.headers["X-Cache"] = "HIT"
            response.headers["X-Cache-Key"] = cache_key
            return response
    
    # Cache miss - run inference
    start = time.time()
    result = mock_ml_inference(data.text)
    duration = time.time() - start
    
    # Store in cache
    cache_key = cache.set(data.text, result)
    
    response = JSONResponse(content={
        "result": result,
        "cached": False,
        "inference_time_ms": round(duration * 1000)
    })
    response.headers["X-Cache"] = "MISS"
    response.headers["X-Cache-Key"] = cache_key
    
    return response

@app.get("/cache/stats")
def cache_stats():
    """Get cache statistics"""
    return cache.stats()

@app.delete("/cache")
def clear_cache():
    """Clear entire cache"""
    cache.clear()
    return {"message": "Cache cleared"}

@app.delete("/cache/{key}")
def delete_cache_entry(key: str):
    """Delete specific cache entry by key"""
    # Note: In practice, you might want to delete by text hash
    return {"message": "Not implemented - use text-based deletion"}
```

---

## Key Insights

### Cache Key Design
- Normalize text (lowercase, strip whitespace)
- Use hash for consistent, fixed-length keys
- Consider including model version in key

### When NOT to Cache
- Results with errors
- Real-time data (stock prices)
- User-specific results

### Production Considerations
- Use Redis for distributed caching
- Set appropriate TTL based on data freshness needs
- Monitor hit ratio - below 50% may indicate issues

---

## Time to Implement: 45-60 minutes
