# Practice 08: Database Optimization

**Difficulty:** ⭐⭐⭐⭐ (Hard)  
**Time Estimate:** 60-75 minutes  
**Job Requirement:** "Optimize data access across PostgreSQL"

---

## 📝 Problem Statement

Your ML jobs table has grown to millions of rows. Queries are slow, and the API is timing out. Optimize the database for production scale.

### Requirements

1. **Indexing Strategy**
   - Add appropriate indexes
   - Use partial indexes for status queries
   - Composite indexes for common filters

2. **Query Optimization**
   - Efficient pagination (not OFFSET)
   - Batch operations
   - Connection pooling

3. **Data Archival**
   - Archive completed jobs older than 30 days
   - Maintain archive table for auditing
   - Cleanup routine

4. **Monitoring**
   - Slow query logging
   - Index usage statistics
   - Table size monitoring

### Problem Scenarios

```sql
-- These queries are slow with 10M rows:

-- 1. Get pending jobs (status filter)
SELECT * FROM ml_jobs WHERE status = 'pending' ORDER BY created_at;

-- 2. Paginate through results (OFFSET is slow)
SELECT * FROM ml_jobs ORDER BY created_at DESC LIMIT 50 OFFSET 1000000;

-- 3. Get jobs for date range
SELECT * FROM ml_jobs 
WHERE created_at BETWEEN '2024-01-01' AND '2024-01-31'
AND status = 'completed';

-- 4. Count by status (full table scan)
SELECT status, COUNT(*) FROM ml_jobs GROUP BY status;
```

### Example Optimized Usage

```bash
# Efficient cursor-based pagination
curl "http://localhost:8000/jobs?limit=50&cursor=job_abc123"

# Get status counts (cached/materialized)
curl http://localhost:8000/jobs/stats

# Archive old jobs
curl -X POST http://localhost:8000/admin/archive-jobs?days_old=30

# Check database health
curl http://localhost:8000/admin/db-health
```

---

## 🎯 Learning Objectives

1. **Index Design** - B-tree, partial, composite indexes
2. **Cursor Pagination** - Keyset pagination pattern
3. **Connection Pooling** - SQLAlchemy pool configuration
4. **Query Analysis** - EXPLAIN ANALYZE
5. **Data Lifecycle** - Archival and cleanup

---

## 💡 Hints

<details>
<summary>Hint 1: Creating effective indexes</summary>

```python
# In models.py or alembic migration
from sqlalchemy import Index

class MLJob(Base):
    __tablename__ = "ml_jobs"
    
    # ... columns ...
    
    __table_args__ = (
        # Composite index for common query pattern
        Index('idx_status_created', 'status', 'created_at'),
        
        # Partial index for pending jobs only
        Index(
            'idx_pending_jobs',
            'created_at',
            postgresql_where=text("status = 'pending'")
        ),
        
        # Index for pagination
        Index('idx_created_desc', 'created_at', postgresql_using='btree'),
    )
```
</details>

<details>
<summary>Hint 2: Cursor-based pagination</summary>

```python
@app.get("/jobs")
def list_jobs(
    limit: int = 50,
    cursor: Optional[str] = None,  # Last job_uuid from previous page
    db: Session = Depends(get_db)
):
    query = db.query(MLJob).order_by(MLJob.created_at.desc())
    
    if cursor:
        # Get the timestamp of the cursor job
        cursor_job = db.query(MLJob).filter(MLJob.job_uuid == cursor).first()
        if cursor_job:
            # Get jobs created before the cursor
            query = query.filter(MLJob.created_at < cursor_job.created_at)
    
    jobs = query.limit(limit + 1).all()  # Get one extra to check if more exist
    
    has_more = len(jobs) > limit
    jobs = jobs[:limit]
    
    return {
        "jobs": jobs,
        "next_cursor": jobs[-1].job_uuid if has_more else None,
        "has_more": has_more
    }
```
</details>

<details>
<summary>Hint 3: Connection pooling configuration</summary>

```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,          # Number of connections to keep open
    max_overflow=20,       # Allow 20 more connections under load
    pool_timeout=30,       # Timeout waiting for connection
    pool_recycle=1800,     # Recycle connections after 30 min
    pool_pre_ping=True     # Test connections before using
)
```
</details>

<details>
<summary>Hint 4: Archival pattern</summary>

```python
def archive_old_jobs(db: Session, days_old: int = 30):
    """Move old completed jobs to archive table"""
    cutoff_date = datetime.utcnow() - timedelta(days=days_old)
    
    # Use raw SQL for efficiency
    archive_query = text("""
        INSERT INTO ml_jobs_archive
        SELECT * FROM ml_jobs
        WHERE status IN ('completed', 'failed')
        AND created_at < :cutoff
    """)
    
    delete_query = text("""
        DELETE FROM ml_jobs
        WHERE status IN ('completed', 'failed')
        AND created_at < :cutoff
    """)
    
    db.execute(archive_query, {"cutoff": cutoff_date})
    result = db.execute(delete_query, {"cutoff": cutoff_date})
    db.commit()
    
    return result.rowcount
```
</details>

---

## ✅ Success Criteria

- [ ] Status queries use index (check with EXPLAIN)
- [ ] Pagination works without OFFSET
- [ ] Connection pool configured properly
- [ ] Archive moves old data efficiently
- [ ] Database health endpoint shows stats

---

# Solution: Database Optimization

## Complete Implementation

### File: `app/models.py`

```python
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Index, text
from datetime import datetime
from .database import Base

class MLJob(Base):
    __tablename__ = "ml_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    job_uuid = Column(String(36), unique=True, index=True)
    input_text = Column(Text)
    status = Column(String(20), default="pending", index=True)
    result_score = Column(Float, nullable=True)
    result_label = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)
    
    __table_args__ = (
        # Composite index for status + date queries
        Index('idx_status_created_at', 'status', 'created_at'),
        
        # Partial index for pending jobs (most queried)
        Index(
            'idx_pending_jobs',
            'created_at',
            postgresql_where=text("status = 'pending'")
        ),
        
        # Index for date range queries
        Index('idx_created_at_desc', 'created_at', postgresql_ops={'created_at': 'DESC'}),
    )


class MLJobArchive(Base):
    """Archive table for old jobs"""
    __tablename__ = "ml_jobs_archive"
    
    id = Column(Integer, primary_key=True)
    job_uuid = Column(String(36), index=True)
    input_text = Column(Text)
    status = Column(String(20))
    result_score = Column(Float, nullable=True)
    result_label = Column(String(50), nullable=True)
    created_at = Column(DateTime)
    completed_at = Column(DateTime, nullable=True)
    archived_at = Column(DateTime, default=datetime.utcnow)
```

### File: `app/database.py`

```python
import os
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
import logging
import time

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/mldb"
)

# Optimized connection pool
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True,
    echo=os.getenv("SQL_DEBUG", "false").lower() == "true"
)

# Slow query logging
SLOW_QUERY_THRESHOLD = 1.0  # seconds

@event.listens_for(engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault("query_start_time", []).append(time.time())

@event.listens_for(engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = time.time() - conn.info["query_start_time"].pop()
    if total > SLOW_QUERY_THRESHOLD:
        logging.warning(f"Slow query ({total:.2f}s): {statement[:200]}")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### File: `app/main.py`

```python
from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from datetime import datetime, timedelta
from typing import Optional, List

from . import models
from .database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Database Optimization Demo")

# ============================================
# OPTIMIZED ENDPOINTS
# ============================================

@app.get("/jobs")
def list_jobs(
    limit: int = Query(50, ge=1, le=100),
    cursor: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Cursor-based pagination (efficient for large datasets).
    Use job_uuid as cursor instead of OFFSET.
    """
    query = db.query(models.MLJob).order_by(models.MLJob.created_at.desc())
    
    # Filter by status
    if status:
        query = query.filter(models.MLJob.status == status)
    
    # Cursor-based pagination
    if cursor:
        cursor_job = db.query(models.MLJob).filter(
            models.MLJob.job_uuid == cursor
        ).first()
        
        if cursor_job:
            query = query.filter(
                models.MLJob.created_at < cursor_job.created_at
            )
    
    # Fetch one extra to determine if more pages exist
    jobs = query.limit(limit + 1).all()
    
    has_more = len(jobs) > limit
    jobs = jobs[:limit]
    
    return {
        "jobs": [
            {
                "job_uuid": j.job_uuid,
                "status": j.status,
                "created_at": j.created_at.isoformat()
            }
            for j in jobs
        ],
        "pagination": {
            "next_cursor": jobs[-1].job_uuid if has_more and jobs else None,
            "has_more": has_more,
            "limit": limit
        }
    }


@app.get("/jobs/stats")
def get_job_stats(db: Session = Depends(get_db)):
    """
    Get job statistics using efficient queries.
    Consider caching this for high-traffic scenarios.
    """
    # Status counts - uses index
    status_counts = db.query(
        models.MLJob.status,
        func.count(models.MLJob.id)
    ).group_by(models.MLJob.status).all()
    
    # Recent job count (last 24 hours)
    yesterday = datetime.utcnow() - timedelta(days=1)
    recent_count = db.query(func.count(models.MLJob.id)).filter(
        models.MLJob.created_at > yesterday
    ).scalar()
    
    return {
        "by_status": {status: count for status, count in status_counts},
        "total": sum(count for _, count in status_counts),
        "last_24_hours": recent_count
    }


# ============================================
# ADMIN ENDPOINTS
# ============================================

@app.post("/admin/archive-jobs")
def archive_old_jobs(
    days_old: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """Archive completed jobs older than specified days"""
    cutoff_date = datetime.utcnow() - timedelta(days=days_old)
    
    # Insert into archive
    insert_sql = text("""
        INSERT INTO ml_jobs_archive (
            job_uuid, input_text, status, result_score, 
            result_label, created_at, completed_at
        )
        SELECT 
            job_uuid, input_text, status, result_score,
            result_label, created_at, completed_at
        FROM ml_jobs
        WHERE status IN ('completed', 'failed')
        AND created_at < :cutoff
    """)
    
    # Delete from main table
    delete_sql = text("""
        DELETE FROM ml_jobs
        WHERE status IN ('completed', 'failed')
        AND created_at < :cutoff
    """)
    
    try:
        db.execute(insert_sql, {"cutoff": cutoff_date})
        result = db.execute(delete_sql, {"cutoff": cutoff_date})
        db.commit()
        
        return {
            "archived_count": result.rowcount,
            "cutoff_date": cutoff_date.isoformat()
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Archive failed: {str(e)}")


@app.get("/admin/db-health")
def database_health(db: Session = Depends(get_db)):
    """Database health and statistics"""
    
    # Table sizes
    size_sql = text("""
        SELECT 
            relname as table_name,
            pg_size_pretty(pg_total_relation_size(relid)) as total_size,
            pg_size_pretty(pg_relation_size(relid)) as table_size,
            pg_size_pretty(pg_total_relation_size(relid) - pg_relation_size(relid)) as index_size
        FROM pg_catalog.pg_statio_user_tables
        WHERE schemaname = 'public'
        ORDER BY pg_total_relation_size(relid) DESC
    """)
    
    # Index usage
    index_sql = text("""
        SELECT 
            indexrelname as index_name,
            idx_scan as scans,
            idx_tup_read as tuples_read,
            idx_tup_fetch as tuples_fetched
        FROM pg_stat_user_indexes
        WHERE schemaname = 'public'
        ORDER BY idx_scan DESC
        LIMIT 10
    """)
    
    # Connection pool stats
    pool = db.get_bind().pool
    
    return {
        "table_sizes": [dict(row) for row in db.execute(size_sql)],
        "top_indexes": [dict(row) for row in db.execute(index_sql)],
        "connection_pool": {
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow()
        }
    }


@app.get("/admin/explain")
def explain_query(
    query_type: str = Query(..., regex="^(pending|recent|status_count)$"),
    db: Session = Depends(get_db)
):
    """Run EXPLAIN ANALYZE on common queries"""
    
    queries = {
        "pending": "SELECT * FROM ml_jobs WHERE status = 'pending' ORDER BY created_at LIMIT 100",
        "recent": "SELECT * FROM ml_jobs ORDER BY created_at DESC LIMIT 100",
        "status_count": "SELECT status, COUNT(*) FROM ml_jobs GROUP BY status"
    }
    
    sql = text(f"EXPLAIN ANALYZE {queries[query_type]}")
    result = db.execute(sql)
    
    return {
        "query": queries[query_type],
        "plan": [row[0] for row in result]
    }
```

---

## Key Optimization Patterns

### 1. Cursor Pagination vs OFFSET
```sql
-- Bad: OFFSET scans and discards rows
SELECT * FROM ml_jobs ORDER BY created_at OFFSET 1000000 LIMIT 50;

-- Good: Cursor skips directly to position
SELECT * FROM ml_jobs 
WHERE created_at < '2024-01-15T10:00:00' 
ORDER BY created_at DESC LIMIT 50;
```

### 2. Partial Indexes
```sql
-- Only index pending jobs (small subset)
CREATE INDEX idx_pending ON ml_jobs(created_at) 
WHERE status = 'pending';
```

### 3. Connection Pooling
- **pool_size**: Persistent connections
- **max_overflow**: Burst capacity
- **pool_pre_ping**: Detect stale connections

---

## Time to Implement: 60-75 minutes
