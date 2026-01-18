# SQLAlchemy Patterns Cheat Sheet

## 1. Database Connection Setup (Memorize This)

```python
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Get connection string from environment
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://user:password@localhost:5432/dbname"
)

# Create engine
engine = create_engine(DATABASE_URL)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

# Dependency for FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

---

## 2. Model Definition Patterns

### Basic Model
```python
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime
from datetime import datetime

class MLJob(Base):
    __tablename__ = "ml_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    job_uuid = Column(String, unique=True, index=True)
    input_text = Column(Text)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
```

### Model with JSON Field (For Flexible Data)
```python
from sqlalchemy.dialects.postgresql import JSON

class MLJob(Base):
    __tablename__ = "ml_jobs"
    
    id = Column(Integer, primary_key=True)
    job_uuid = Column(String, unique=True, index=True)
    
    # Store complex/changing data as JSON
    input_metadata = Column(JSON, nullable=True)
    result_data = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
```

### Model with Foreign Key
```python
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)

class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    job_name = Column(String)
```

---

## 3. Creating Tables

```python
# In main.py or database.py
from app.database import engine, Base
from app import models  # Import all models

# Create all tables
Base.metadata.create_all(bind=engine)
```

---

## 4. CRUD Operations

### Create (Insert)
```python
def create_job(db: Session, job_data: dict):
    new_job = MLJob(
        job_uuid=str(uuid.uuid4()),
        input_text=job_data["text"],
        status="pending"
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)  # Get updated data (like auto-generated ID)
    return new_job
```

### Read (Select)
```python
# Get by ID
def get_job(db: Session, job_id: int):
    return db.query(MLJob).filter(MLJob.id == job_id).first()

# Get by UUID
def get_job_by_uuid(db: Session, job_uuid: str):
    return db.query(MLJob).filter(MLJob.job_uuid == job_uuid).first()

# Get all
def get_all_jobs(db: Session, skip: int = 0, limit: int = 10):
    return db.query(MLJob).offset(skip).limit(limit).all()
```

### Update
```python
def update_job_status(db: Session, job_uuid: str, new_status: str):
    job = db.query(MLJob).filter(MLJob.job_uuid == job_uuid).first()
    if job:
        job.status = new_status
        job.result_data = {"score": 0.95}  # Update multiple fields
        db.commit()
        db.refresh(job)
    return job
```

### Delete
```python
def delete_job(db: Session, job_id: int):
    job = db.query(MLJob).filter(MLJob.id == job_id).first()
    if job:
        db.delete(job)
        db.commit()
    return job
```

---

## 5. Query Patterns (The Interview Favorites)

### Filter by Status
```python
def get_pending_jobs(db: Session):
    return db.query(MLJob).filter(MLJob.status == "pending").all()
```

### Multiple Filters (AND)
```python
def get_completed_jobs_for_version(db: Session, version: str):
    return db.query(MLJob).filter(
        MLJob.status == "completed",
        MLJob.model_version == version
    ).all()
```

### OR Filters
```python
from sqlalchemy import or_

def get_active_or_pending(db: Session):
    return db.query(MLJob).filter(
        or_(MLJob.status == "pending", MLJob.status == "processing")
    ).all()
```

### Search with LIKE (Text Search)
```python
def search_jobs(db: Session, keyword: str):
    return db.query(MLJob).filter(
        MLJob.input_text.ilike(f"%{keyword}%")  # Case-insensitive
    ).all()
```

### Count
```python
def count_jobs_by_status(db: Session, status: str):
    return db.query(MLJob).filter(MLJob.status == status).count()
```

### Order By
```python
def get_recent_jobs(db: Session, limit: int = 10):
    return db.query(MLJob).order_by(
        MLJob.created_at.desc()  # Most recent first
    ).limit(limit).all()
```

### Pagination Pattern
```python
def get_jobs_paginated(db: Session, page: int = 1, per_page: int = 10):
    skip = (page - 1) * per_page
    jobs = db.query(MLJob).offset(skip).limit(per_page).all()
    total = db.query(MLJob).count()
    return {
        "jobs": jobs,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page
    }
```

---

## 6. Bulk Operations (For Batch Processing)

### Bulk Insert
```python
def bulk_create_jobs(db: Session, job_data_list: List[dict]):
    jobs = [
        MLJob(
            job_uuid=str(uuid.uuid4()),
            input_text=data["text"],
            status="pending"
        )
        for data in job_data_list
    ]
    db.bulk_save_objects(jobs)
    db.commit()
    return len(jobs)
```

### Bulk Update
```python
def mark_all_as_processed(db: Session, job_ids: List[int]):
    db.query(MLJob).filter(MLJob.id.in_(job_ids)).update(
        {"status": "completed"},
        synchronize_session=False
    )
    db.commit()
```

---

## 7. JSON Column Queries (PostgreSQL)

### Store JSON Data
```python
job.result_data = {
    "score": 0.95,
    "label": "positive",
    "confidence": 0.87
}
db.commit()
```

### Query JSON Fields
```python
# Get jobs where result score > 0.9
from sqlalchemy.dialects.postgresql import JSONB

jobs = db.query(MLJob).filter(
    MLJob.result_data["score"].astext.cast(Float) > 0.9
).all()
```

---

## 8. Transactions (For Complex Operations)

```python
def process_with_transaction(db: Session, job_id: int):
    try:
        # Start transaction (implicit with session)
        job = db.query(MLJob).filter(MLJob.id == job_id).first()
        
        # Multiple operations
        job.status = "processing"
        db.commit()  # Intermediate commit
        
        # Simulate processing
        result = expensive_ml_inference(job.input_text)
        
        # Update result
        job.status = "completed"
        job.result_data = result
        db.commit()  # Final commit
        
        return job
        
    except Exception as e:
        db.rollback()  # Rollback on error
        raise e
```

---

## 9. Common Errors & Fixes

### Error: "No such table"
**Cause:** Forgot to create tables
**Fix:**
```python
Base.metadata.create_all(bind=engine)
```

### Error: "Could not locate column"
**Cause:** Model column name doesn't match query
**Fix:** Check spelling, refresh model definition

### Error: "Instance is not bound to a Session"
**Cause:** Trying to access relationship after session closed
**Fix:** Use `db.refresh(obj)` or eager loading

---

## 10. Database Connection Strings

### PostgreSQL
```python
# Local
"postgresql://user:password@localhost:5432/dbname"

# Docker (service name as host)
"postgresql://user:password@db:5432/dbname"

# With special characters in password
from urllib.parse import quote_plus
password = quote_plus("p@ssw0rd!")
f"postgresql://user:{password}@localhost:5432/dbname"
```

### SQLite (For Testing)
```python
"sqlite:///./test.db"
```

---

## 11. Index Creation (For Performance)

```python
class MLJob(Base):
    __tablename__ = "ml_jobs"
    
    id = Column(Integer, primary_key=True)
    job_uuid = Column(String, unique=True, index=True)  # Index for fast lookup
    status = Column(String, index=True)  # Index for filtering
    created_at = Column(DateTime, index=True)  # Index for sorting
```

---

## 12. Integration with FastAPI

### Full Pattern
```python
# In main.py
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app import models

@app.post("/jobs")
def create_job(job_data: dict, db: Session = Depends(get_db)):
    new_job = models.MLJob(
        job_uuid=str(uuid.uuid4()),
        input_text=job_data["text"],
        status="pending"
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    
    return {
        "job_id": new_job.job_uuid,
        "status": new_job.status
    }

@app.get("/jobs/{job_uuid}")
def get_job(job_uuid: str, db: Session = Depends(get_db)):
    job = db.query(models.MLJob).filter(
        models.MLJob.job_uuid == job_uuid
    ).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "job_id": job.job_uuid,
        "status": job.status,
        "result": job.result_data
    }
```

---

## Decision Tree

**If they ask for:**
- "Store data" → Create model + use `db.add()` + `db.commit()`
- "Search by keyword" → Use `.filter(Model.field.ilike(f"%{keyword}%"))`
- "Get recent items" → Use `.order_by(Model.created_at.desc())`
- "Pagination" → Use `.offset()` + `.limit()`
- "Flexible schema" → Use JSON column
- "Batch insert" → Use `bulk_save_objects()`

---

## Testing Database Operations

```python
# In a test file or notebook
from app.database import SessionLocal, engine
from app import models

# Create tables
models.Base.metadata.create_all(bind=engine)

# Test insert
db = SessionLocal()
job = models.MLJob(job_uuid="test-123", input_text="test")
db.add(job)
db.commit()

# Test query
result = db.query(models.MLJob).filter(models.MLJob.job_uuid == "test-123").first()
print(result.input_text)

db.close()
```

---

**Keep this sheet open during coding!**
