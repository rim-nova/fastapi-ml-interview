# Solution: Database Optimization

## Approach

This solution implements production-grade database optimizations:

1. **Cursor-based Pagination**: Uses `created_at` + `job_uuid` instead of OFFSET
2. **Strategic Indexes**: Composite, partial, and B-tree indexes
3. **Connection Pooling**: Configured pool with health checks
4. **Slow Query Logging**: Monitors queries exceeding threshold
5. **Archive Strategy**: Moves old jobs to archive table

---

## Architecture

```
API Request
    │
    ▼
┌─────────────────────────────────────────────────┐
│           Connection Pool (QueuePool)            │
│    pool_size=10, max_overflow=20, pre_ping=True  │
└─────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────┐
│              Query Execution                      │
│  - Composite indexes for common filters          │
│  - Partial indexes for status queries            │
│  - Cursor pagination (no OFFSET)                 │
└─────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────┐
│           Slow Query Logger                       │
│  - Logs queries > 1 second                       │
│  - Records execution time                        │
└─────────────────────────────────────────────────┘
```

---

## Key Implementation Details

### 1. Optimized Database Connection

```python
import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
import time

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:password@db:5432/mldb"
)

# Optimized engine configuration
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,          # Maintained connections
    max_overflow=20,       # Additional connections when busy
    pool_pre_ping=True,    # Validate connection before use
    pool_recycle=3600,     # Recycle connections after 1 hour
    echo=False             # Set True for SQL logging
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ============================================
# SLOW QUERY LOGGING
# ============================================

SLOW_QUERY_THRESHOLD = 1.0  # seconds

@event.listens_for(engine, "before_cursor_execute")
def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault('query_start_time', []).append(time.time())

@event.listens_for(engine, "after_cursor_execute")
def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total_time = time.time() - conn.info['query_start_time'].pop(-1)
    if total_time > SLOW_QUERY_THRESHOLD:
        print(f"⚠️ SLOW QUERY ({total_time:.2f}s): {statement[:100]}...")
```

### 2. Strategic Index Configuration

```python
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Index
from datetime import datetime
from .database import Base

class MLJob(Base):
    __tablename__ = "ml_jobs"
    
    id = Column(Integer, primary_key=True)
    job_uuid = Column(String(36), unique=True, nullable=False)
    input_text = Column(Text)
    status = Column(String(20), default="pending", nullable=False)
    result_score = Column(Float)
    result_label = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        # Composite index for status + time filtering
        Index('idx_status_created', 'status', 'created_at'),
        
        # Partial index for pending jobs (most common query)
        Index(
            'idx_pending_jobs',
            'created_at',
            postgresql_where=(status == 'pending')
        ),
        
        # Index for job lookup
        Index('idx_job_uuid', 'job_uuid'),
        
        # Descending index for recent jobs
        Index('idx_created_desc', created_at.desc()),
    )
```

### 3. Cursor-Based Pagination

```python
from typing import Optional, List
from datetime import datetime

def get_jobs_cursor_paginated(
    db: Session,
    cursor: Optional[str] = None,
    limit: int = 20,
    status: Optional[str] = None
) -> dict:
    """
    Cursor-based pagination using created_at + job_uuid.
    
    Why cursor pagination?
    - OFFSET becomes slow with large datasets (scans all skipped rows)
    - Cursor pagination is O(log n) with proper indexes
    - Handles concurrent inserts correctly
    
    Args:
        cursor: job_uuid of last item from previous page
        limit: Number of items to return
        status: Optional status filter
    
    Returns:
        {items: [...], next_cursor: str|None, has_more: bool}
    """
    query = db.query(MLJob)
    
    # Apply status filter
    if status:
        query = query.filter(MLJob.status == status)
    
    # Apply cursor (for pagination)
    if cursor:
        # Get cursor item
        cursor_item = db.query(MLJob).filter(
            MLJob.job_uuid == cursor
        ).first()
        
        if cursor_item:
            # Get items AFTER cursor (older than cursor for DESC order)
            query = query.filter(
                (MLJob.created_at < cursor_item.created_at) |
                (
                    (MLJob.created_at == cursor_item.created_at) &
                    (MLJob.job_uuid < cursor_item.job_uuid)
                )
            )
    
    # Order by created_at DESC, job_uuid DESC (tiebreaker)
    query = query.order_by(
        MLJob.created_at.desc(),
        MLJob.job_uuid.desc()
    )
    
    # Fetch limit + 1 to check if there's more
    items = query.limit(limit + 1).all()
    
    # Determine if there's a next page
    has_more = len(items) > limit
    if has_more:
        items = items[:limit]  # Remove extra item
    
    # Next cursor is the last item's UUID
    next_cursor = items[-1].job_uuid if items and has_more else None
    
    return {
        "items": items,
        "next_cursor": next_cursor,
        "has_more": has_more,
        "count": len(items)
    }
```

### 4. Archive Strategy

```python
class MLJobArchive(Base):
    """Archive table for completed/failed jobs older than retention period."""
    __tablename__ = "ml_jobs_archive"
    
    id = Column(Integer, primary_key=True)
    job_uuid = Column(String(36), nullable=False)
    input_text = Column(Text)
    status = Column(String(20), nullable=False)
    result_score = Column(Float)
    result_label = Column(String(50))
    created_at = Column(DateTime, nullable=False)
    archived_at = Column(DateTime, default=datetime.utcnow)

def archive_old_jobs(db: Session, days_old: int = 30) -> dict:
    """
    Move old completed/failed jobs to archive table.
    
    This keeps the main table small for fast queries.
    """
    from datetime import timedelta
    
    cutoff = datetime.utcnow() - timedelta(days=days_old)
    
    # Find jobs to archive
    jobs_to_archive = db.query(MLJob).filter(
        MLJob.created_at < cutoff,
        MLJob.status.in_(['completed', 'failed'])
    ).all()
    
    if not jobs_to_archive:
        return {"archived": 0, "message": "No jobs to archive"}
    
    # Create archive entries
    archive_entries = [
        MLJobArchive(
            job_uuid=job.job_uuid,
            input_text=job.input_text,
            status=job.status,
            result_score=job.result_score,
            result_label=job.result_label,
            created_at=job.created_at
        )
        for job in jobs_to_archive
    ]
    
    # Bulk insert to archive
    db.bulk_save_objects(archive_entries)
    
    # Delete from main table
    job_ids = [job.id for job in jobs_to_archive]
    db.query(MLJob).filter(MLJob.id.in_(job_ids)).delete(
        synchronize_session=False
    )
    
    db.commit()
    
    return {
        "archived": len(archive_entries),
        "cutoff_date": cutoff.isoformat(),
        "message": f"Archived {len(archive_entries)} jobs"
    }
```

---

## Complete Solution Files

### File: `app/database.py`

```python
import os
import time
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:password@db:5432/mldb"
)

# Production-optimized engine
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Slow query logging
SLOW_QUERY_THRESHOLD = 1.0

@event.listens_for(engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault('query_start_time', []).append(time.time())

@event.listens_for(engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = time.time() - conn.info['query_start_time'].pop(-1)
    if total > SLOW_QUERY_THRESHOLD:
        print(f"⚠️ SLOW QUERY ({total:.2f}s): {statement[:200]}...")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### File: `app/models.py`

```python
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Index
from datetime import datetime
from .database import Base

class MLJob(Base):
    __tablename__ = "ml_jobs"
    
    id = Column(Integer, primary_key=True)
    job_uuid = Column(String(36), unique=True, nullable=False, index=True)
    input_text = Column(Text)
    status = Column(String(20), default="pending", nullable=False)
    result_score = Column(Float)
    result_label = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        # Composite index: status queries with time ordering
        Index('idx_status_created', 'status', 'created_at'),
        
        # Partial index: fast lookup for pending jobs only
        Index(
            'idx_pending_jobs',
            'created_at',
            postgresql_where=(status == 'pending')
        ),
        
        # Descending index for recent-first queries
        Index('idx_created_desc', created_at.desc()),
    )

class MLJobArchive(Base):
    """Archive table for old completed/failed jobs."""
    __tablename__ = "ml_jobs_archive"
    
    id = Column(Integer, primary_key=True)
    job_uuid = Column(String(36), nullable=False, index=True)
    input_text = Column(Text)
    status = Column(String(20), nullable=False)
    result_score = Column(Float)
    result_label = Column(String(50))
    created_at = Column(DateTime, nullable=False)
    archived_at = Column(DateTime, default=datetime.utcnow)
```

### File: `app/main.py`

```python
from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from typing import Optional
from datetime import datetime, timedelta
import uuid
import time

from . import models, schemas
from .database import engine, get_db, SessionLocal

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Optimized ML API",
    description="Database-optimized ML Backend",
    version="1.0.0"
)

# ============================================
# STANDARD ENDPOINTS
# ============================================

@app.get("/")
def root():
    return {"message": "Optimized ML API is running"}

@app.get("/health")
def health(db: Session = Depends(get_db)):
    """Health check with database connectivity test."""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": str(e)}

@app.post("/predict")
def predict(request: schemas.JobCreate, db: Session = Depends(get_db)):
    """Create ML prediction job."""
    job_id = str(uuid.uuid4())
    job = models.MLJob(
        job_uuid=job_id,
        input_text=request.text,
        status="pending"
    )
    db.add(job)
    db.commit()
    return {"job_id": job_id, "status": "pending"}

# ============================================
# CURSOR PAGINATION ENDPOINT
# ============================================

@app.get("/jobs")
def list_jobs(
    cursor: Optional[str] = Query(None, description="job_uuid for pagination"),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    List jobs with cursor-based pagination.
    
    Why cursor pagination over OFFSET?
    - OFFSET scans all skipped rows (O(offset + limit))
    - Cursor uses index seek (O(log n))
    - Handles concurrent inserts correctly
    """
    query = db.query(models.MLJob)
    
    # Status filter
    if status:
        query = query.filter(models.MLJob.status == status)
    
    # Cursor-based pagination
    if cursor:
        cursor_item = db.query(models.MLJob).filter(
            models.MLJob.job_uuid == cursor
        ).first()
        
        if cursor_item:
            query = query.filter(
                models.MLJob.created_at < cursor_item.created_at
            )
    
    # Order and limit
    query = query.order_by(models.MLJob.created_at.desc())
    items = query.limit(limit + 1).all()
    
    # Check for more pages
    has_more = len(items) > limit
    if has_more:
        items = items[:limit]
    
    next_cursor = items[-1].job_uuid if items and has_more else None
    
    return {
        "items": [
            {
                "job_id": j.job_uuid,
                "status": j.status,
                "created_at": j.created_at.isoformat()
            }
            for j in items
        ],
        "next_cursor": next_cursor,
        "has_more": has_more
    }

# ============================================
# ADMIN ENDPOINTS
# ============================================

@app.post("/admin/archive-jobs")
def archive_jobs(
    days_old: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """Archive completed/failed jobs older than specified days."""
    cutoff = datetime.utcnow() - timedelta(days=days_old)
    
    # Find jobs to archive
    jobs = db.query(models.MLJob).filter(
        models.MLJob.created_at < cutoff,
        models.MLJob.status.in_(['completed', 'failed'])
    ).all()
    
    if not jobs:
        return {"archived": 0, "message": "No jobs to archive"}
    
    # Create archive entries
    archives = [
        models.MLJobArchive(
            job_uuid=j.job_uuid,
            input_text=j.input_text,
            status=j.status,
            result_score=j.result_score,
            result_label=j.result_label,
            created_at=j.created_at
        )
        for j in jobs
    ]
    
    db.bulk_save_objects(archives)
    
    # Delete from main table
    db.query(models.MLJob).filter(
        models.MLJob.id.in_([j.id for j in jobs])
    ).delete(synchronize_session=False)
    
    db.commit()
    
    return {
        "archived": len(archives),
        "cutoff": cutoff.isoformat()
    }

@app.get("/admin/db-health")
def db_health(db: Session = Depends(get_db)):
    """Database health and statistics."""
    # Table sizes
    main_count = db.query(func.count(models.MLJob.id)).scalar()
    archive_count = db.query(func.count(models.MLJobArchive.id)).scalar()
    
    # Status distribution
    status_counts = db.query(
        models.MLJob.status,
        func.count(models.MLJob.id)
    ).group_by(models.MLJob.status).all()
    
    # Pool stats
    pool = engine.pool
    
    return {
        "tables": {
            "ml_jobs": main_count,
            "ml_jobs_archive": archive_count
        },
        "status_distribution": dict(status_counts),
        "connection_pool": {
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow()
        }
    }

@app.get("/admin/explain")
def explain_query(
    query_type: str = Query(..., enum=["recent", "pending", "by_status"]),
    db: Session = Depends(get_db)
):
    """Run EXPLAIN ANALYZE on common queries."""
    queries = {
        "recent": "SELECT * FROM ml_jobs ORDER BY created_at DESC LIMIT 20",
        "pending": "SELECT * FROM ml_jobs WHERE status = 'pending' ORDER BY created_at",
        "by_status": "SELECT status, COUNT(*) FROM ml_jobs GROUP BY status"
    }
    
    sql = queries.get(query_type)
    result = db.execute(text(f"EXPLAIN ANALYZE {sql}"))
    plan = [row[0] for row in result]
    
    return {
        "query": sql,
        "plan": plan
    }
```

---

## Testing Commands

```bash
# Create test data (100 jobs)
for i in {1..100}; do
  curl -X POST http://localhost:8000/predict \
    -H "Content-Type: application/json" \
    -d "{\"text\": \"Test job $i\"}"
done

# Test cursor pagination
curl "http://localhost:8000/jobs?limit=10"
# Note the next_cursor value

# Get next page
curl "http://localhost:8000/jobs?limit=10&cursor=YOUR_CURSOR"

# Check database health
curl http://localhost:8000/admin/db-health

# Archive old jobs
curl -X POST "http://localhost:8000/admin/archive-jobs?days_old=7"

# Explain query execution
curl "http://localhost:8000/admin/explain?query_type=recent"
```

---

## Key Patterns

### 1. Cursor Pagination vs OFFSET

```python
# ❌ OFFSET (slow for large datasets)
query.offset(1000).limit(20)  # Scans 1020 rows

# ✅ Cursor (fast, uses index)
query.filter(Model.created_at < cursor_time).limit(20)  # Index seek
```

### 2. Composite Index Usage

```python
# Index: (status, created_at)
# ✅ Uses index (prefix match)
query.filter(status == 'pending').order_by(created_at)

# ❌ Doesn't use index efficiently
query.filter(created_at > x).order_by(status)
```

### 3. Partial Index

```python
# Only indexes rows where status='pending'
Index('idx_pending', 'created_at', postgresql_where=(status == 'pending'))

# Query that uses it:
query.filter(status == 'pending').order_by(created_at)
```

---

## Interview Questions & Answers

**Q1: "Why cursor pagination instead of OFFSET?"**

A: Performance. OFFSET must scan all skipped rows:
- `OFFSET 10000 LIMIT 20` → scans 10,020 rows
- Cursor with index → scans ~20 rows (log n seek)

Also handles concurrent inserts correctly (OFFSET can skip/duplicate items).

**Q2: "When would you add an index?"**

A: When a query:
1. Filters on a column (WHERE clause)
2. Orders by a column (ORDER BY)
3. Is executed frequently
4. Scans more than 5-10% of the table

**Q3: "What's connection pooling and why use it?"**

A: Pooling maintains reusable database connections:
- Creating connections is expensive (~100ms)
- Pool reuses existing connections (~1ms)
- `pool_pre_ping` validates connections before use
- `max_overflow` handles traffic spikes

---

## Production Checklist

- [ ] Connection pooling configured
- [ ] Slow query logging enabled
- [ ] Indexes on filtered/sorted columns
- [ ] Archive strategy for old data
- [ ] Cursor pagination for large datasets
- [ ] Database health monitoring endpoint

**Time to implement from scratch: 60-75 minutes**
