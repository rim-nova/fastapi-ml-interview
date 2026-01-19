# Solution: Batch Processing Pipeline

## Approach

This solution processes large CSV files efficiently using:
1. **Chunked Processing** - Process 100 rows at a time
2. **Bulk Inserts** - Single DB operation for many rows
3. **Progress Tracking** - Real-time updates during processing
4. **Background Tasks** - Non-blocking file processing

---

## Architecture

```
CSV Upload → Parse CSV → Create Batch Job → Return batch_id
                              ↓
                    Background Task starts
                              ↓
              ┌───────────────┴───────────────┐
              ↓                               ↓
         Chunk 1 (100 rows)            Chunk 2 (100 rows)
              ↓                               ↓
         Bulk Insert                    Bulk Insert
              ↓                               ↓
         Update Progress               Update Progress
              └───────────────┬───────────────┘
                              ↓
                    Mark as Completed
```

---

## Complete Code Implementation

### File: `app/models.py`

```python
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSON
from datetime import datetime
from .database import Base

class BatchJob(Base):
    """Batch processing job"""
    __tablename__ = "batch_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    batch_uuid = Column(String, unique=True, index=True)
    status = Column(String, default="pending")  # pending, processing, completed, failed
    total_count = Column(Integer, default=0)
    processed_count = Column(Integer, default=0)
    summary = Column(JSON, nullable=True)  # Store summary stats
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


class BatchResult(Base):
    """Individual result within a batch"""
    __tablename__ = "batch_results"
    
    id = Column(Integer, primary_key=True, index=True)
    batch_uuid = Column(String, index=True)
    row_id = Column(String)
    original_text = Column(Text)
    sentiment = Column(String)
    score = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
```

### File: `app/schemas.py`

```python
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime

class BatchCreateResponse(BaseModel):
    batch_id: str
    status: str
    total_count: int
    processed_count: int

class BatchStatusResponse(BaseModel):
    batch_id: str
    status: str
    total_count: int
    processed_count: int
    progress_percent: float
    summary: Optional[Dict[str, int]] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

class ResultItem(BaseModel):
    row_id: str
    text: str
    sentiment: str
    score: float

class BatchResultsResponse(BaseModel):
    batch_id: str
    page: int
    per_page: int
    total_results: int
    total_pages: int
    results: List[ResultItem]
```

### File: `app/main.py`

```python
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
import csv
import codecs
import uuid
import time
from datetime import datetime
from typing import List

from . import models, schemas
from .database import engine, get_db, SessionLocal

# Create tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Batch Processing API",
    description="Process large CSV files efficiently",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# HELPER FUNCTIONS
# ============================================

def chunk_list(items: list, chunk_size: int = 100):
    """Split list into chunks"""
    for i in range(0, len(items), chunk_size):
        yield items[i:i + chunk_size]


def mock_sentiment_analysis(text: str) -> tuple[str, float]:
    """Mock ML model - returns (sentiment, confidence)"""
    text_lower = text.lower()
    
    if any(word in text_lower for word in ["great", "amazing", "love", "excellent", "best"]):
        return "positive", 0.92
    elif any(word in text_lower for word in ["terrible", "awful", "hate", "worst", "bad"]):
        return "negative", 0.89
    else:
        return "neutral", 0.75


def process_batch_job(batch_uuid: str, rows: List[dict]):
    """Background task for batch processing"""
    db = SessionLocal()
    
    try:
        # Get batch job
        batch = db.query(models.BatchJob).filter(
            models.BatchJob.batch_uuid == batch_uuid
        ).first()
        
        if not batch:
            print(f"Batch {batch_uuid} not found")
            return
        
        batch.status = "processing"
        db.commit()
        
        # Track sentiment counts for summary
        sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}
        
        # Process in chunks
        for chunk in chunk_list(rows, chunk_size=100):
            results_to_insert = []
            
            for row in chunk:
                # Simulate processing delay (remove in production)
                time.sleep(0.01)  # 10ms per row
                
                row_id = row.get("id", str(uuid.uuid4()))
                text = row.get("text", "")
                
                sentiment, score = mock_sentiment_analysis(text)
                sentiment_counts[sentiment] += 1
                
                results_to_insert.append(
                    models.BatchResult(
                        batch_uuid=batch_uuid,
                        row_id=str(row_id),
                        original_text=text,
                        sentiment=sentiment,
                        score=score
                    )
                )
            
            # Bulk insert chunk
            db.bulk_save_objects(results_to_insert)
            
            # Update progress
            batch.processed_count += len(chunk)
            db.commit()
            
            print(f"Batch {batch_uuid}: {batch.processed_count}/{batch.total_count}")
        
        # Mark as completed
        batch.status = "completed"
        batch.summary = sentiment_counts
        batch.completed_at = datetime.utcnow()
        db.commit()
        
        print(f"✅ Batch {batch_uuid} completed: {sentiment_counts}")
        
    except Exception as e:
        print(f"❌ Batch {batch_uuid} failed: {e}")
        batch = db.query(models.BatchJob).filter(
            models.BatchJob.batch_uuid == batch_uuid
        ).first()
        if batch:
            batch.status = "failed"
            batch.error_message = str(e)
            db.commit()
    finally:
        db.close()


# ============================================
# ENDPOINTS
# ============================================

@app.get("/")
def read_root():
    return {"message": "Batch Processing API is running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/batch/upload", response_model=schemas.BatchCreateResponse)
async def upload_batch(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """
    Upload CSV file for batch processing.
    CSV must have 'id' and 'text' columns.
    """
    # Validate file type
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=400, 
            detail="File must be a CSV"
        )
    
    try:
        # Parse CSV
        csv_reader = csv.DictReader(
            codecs.iterdecode(file.file, 'utf-8')
        )
        rows = list(csv_reader)
        
        # Validate CSV structure
        if not rows:
            raise HTTPException(
                status_code=400, 
                detail="CSV file is empty"
            )
        
        if 'text' not in rows[0]:
            raise HTTPException(
                status_code=400, 
                detail="CSV must have 'text' column"
            )
        
        total_count = len(rows)
        
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400, 
            detail="Invalid file encoding. Use UTF-8."
        )
    except csv.Error as e:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid CSV format: {e}"
        )
    
    # Create batch job
    batch_uuid = f"batch-{uuid.uuid4().hex[:12]}"
    
    batch_job = models.BatchJob(
        batch_uuid=batch_uuid,
        status="pending",
        total_count=total_count,
        processed_count=0
    )
    db.add(batch_job)
    db.commit()
    
    # Start background processing
    background_tasks.add_task(process_batch_job, batch_uuid, rows)
    
    return schemas.BatchCreateResponse(
        batch_id=batch_uuid,
        status="processing",
        total_count=total_count,
        processed_count=0
    )


@app.get("/batch/{batch_id}", response_model=schemas.BatchStatusResponse)
def get_batch_status(batch_id: str, db: Session = Depends(get_db)):
    """Get batch processing status"""
    batch = db.query(models.BatchJob).filter(
        models.BatchJob.batch_uuid == batch_id
    ).first()
    
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    progress = 0.0
    if batch.total_count > 0:
        progress = round((batch.processed_count / batch.total_count) * 100, 1)
    
    return schemas.BatchStatusResponse(
        batch_id=batch.batch_uuid,
        status=batch.status,
        total_count=batch.total_count,
        processed_count=batch.processed_count,
        progress_percent=progress,
        summary=batch.summary,
        error_message=batch.error_message,
        created_at=batch.created_at,
        completed_at=batch.completed_at
    )


@app.get("/batch/{batch_id}/results", response_model=schemas.BatchResultsResponse)
def get_batch_results(
    batch_id: str,
    page: int = 1,
    per_page: int = 50,
    db: Session = Depends(get_db)
):
    """Get paginated results for a batch"""
    # Validate batch exists
    batch = db.query(models.BatchJob).filter(
        models.BatchJob.batch_uuid == batch_id
    ).first()
    
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    # Validate pagination params
    if page < 1:
        page = 1
    if per_page < 1 or per_page > 100:
        per_page = 50
    
    # Get total count
    total_results = db.query(models.BatchResult).filter(
        models.BatchResult.batch_uuid == batch_id
    ).count()
    
    total_pages = (total_results + per_page - 1) // per_page
    
    # Get paginated results
    offset = (page - 1) * per_page
    results = db.query(models.BatchResult).filter(
        models.BatchResult.batch_uuid == batch_id
    ).offset(offset).limit(per_page).all()
    
    return schemas.BatchResultsResponse(
        batch_id=batch_id,
        page=page,
        per_page=per_page,
        total_results=total_results,
        total_pages=total_pages,
        results=[
            schemas.ResultItem(
                row_id=r.row_id,
                text=r.original_text,
                sentiment=r.sentiment,
                score=r.score
            )
            for r in results
        ]
    )


@app.get("/batches", response_model=List[schemas.BatchStatusResponse])
def list_batches(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """List all batch jobs"""
    batches = db.query(models.BatchJob).order_by(
        models.BatchJob.created_at.desc()
    ).offset(skip).limit(limit).all()
    
    return [
        schemas.BatchStatusResponse(
            batch_id=b.batch_uuid,
            status=b.status,
            total_count=b.total_count,
            processed_count=b.processed_count,
            progress_percent=round((b.processed_count / b.total_count) * 100, 1) if b.total_count > 0 else 0,
            summary=b.summary,
            error_message=b.error_message,
            created_at=b.created_at,
            completed_at=b.completed_at
        )
        for b in batches
    ]


@app.delete("/batch/{batch_id}")
def delete_batch(batch_id: str, db: Session = Depends(get_db)):
    """Delete a batch and all its results"""
    batch = db.query(models.BatchJob).filter(
        models.BatchJob.batch_uuid == batch_id
    ).first()
    
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    # Delete results first
    db.query(models.BatchResult).filter(
        models.BatchResult.batch_uuid == batch_id
    ).delete()
    
    # Delete batch
    db.delete(batch)
    db.commit()
    
    return {"message": f"Batch {batch_id} deleted"}
```

---

## Key Design Decisions

### 1. Chunked Processing

```python
def chunk_list(items: list, chunk_size: int = 100):
    for i in range(0, len(items), chunk_size):
        yield items[i:i + chunk_size]
```

**Why 100 rows per chunk?**
- Small enough to fit in memory
- Large enough for efficient bulk inserts
- Allows frequent progress updates

### 2. Bulk Inserts

```python
# ❌ Slow: One insert per row
for row in rows:
    db.add(BatchResult(...))
    db.commit()  # 1000 commits = slow!

# ✅ Fast: Bulk insert
results = [BatchResult(...) for row in chunk]
db.bulk_save_objects(results)
db.commit()  # 1 commit per chunk
```

**Performance difference:**
- Individual inserts: ~5 seconds for 1000 rows
- Bulk inserts: ~0.2 seconds for 1000 rows

### 3. Progress Tracking

Update progress after each chunk, not each row:
- Reduces database writes
- Still provides good visibility
- Updates every ~1-2 seconds during processing

### 4. Pagination for Results

```python
offset = (page - 1) * per_page
results = db.query(BatchResult).offset(offset).limit(per_page).all()
```

**Why pagination?**
- Can't load 10,000 results into memory
- Better API response times
- Client controls how much data to fetch

---

## Testing

```bash
# Create test CSV
cat > test.csv << 'EOF'
id,text
1,This product is amazing and exceeded expectations!
2,Terrible service, would not recommend
3,Just average, nothing special
4,Love this! Best purchase ever!
5,Waste of money, very disappointed
6,Good quality but overpriced
7,Perfect for my needs
8,Absolutely horrible experience
9,Decent value for the price
10,Outstanding customer support!
EOF

# Upload
curl -X POST http://localhost:8000/batch/upload -F "file=@test.csv"

# Check status
curl http://localhost:8000/batch/batch-xxxx

# Get results
curl "http://localhost:8000/batch/batch-xxxx/results?page=1&per_page=5"

# List all batches
curl http://localhost:8000/batches
```

### Generate Large Test File

```python
# generate_test.py
import random

sentiments = [
    "This is amazing! Love it!",
    "Terrible product, waste of money",
    "Average quality, nothing special",
    "Best purchase I've ever made!",
    "Would not recommend to anyone",
    "Pretty good overall",
    "Exceeded my expectations",
    "Very disappointed with this",
    "Great value for money",
    "Absolutely horrible experience"
]

with open("large_test.csv", "w") as f:
    f.write("id,text\n")
    for i in range(10000):
        text = random.choice(sentiments)
        f.write(f'{i},"{text} - Row {i}"\n')

print("Generated large_test.csv with 10,000 rows")
```

---

## Interview Discussion Points

**Q: "Why use background tasks instead of processing synchronously?"**

A: Files with 10,000 rows take 1-2 minutes to process. HTTP connections would timeout, and users would have a bad experience waiting. Background processing lets us return immediately and show progress.

**Q: "What are the limitations of this approach?"**

A: 
1. Data is loaded into memory (CSV parsing) - for huge files, use streaming
2. Background tasks aren't persistent - server restart loses in-progress jobs
3. Single-threaded processing - could parallelize for more speed

**Q: "How would you scale this?"**

A:
1. Use Celery with Redis for distributed task processing
2. Stream CSV parsing for very large files
3. Parallelize chunks across workers
4. Add retry logic for failed chunks

**Q: "How would you handle partial failures?"**

A: Store success/failure status per row, allow retry of failed rows only, provide detailed error report.

---

## Time to Implement: 60-75 minutes

**Breakdown:**
- 10 min: Database models
- 15 min: CSV upload and parsing
- 15 min: Background processing with chunking
- 10 min: Status endpoint
- 10 min: Paginated results endpoint
- 10 min: Testing
- 5 min: Error handling
