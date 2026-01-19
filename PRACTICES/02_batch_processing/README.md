# Practice 02: Batch Processing Pipeline

**Difficulty:** ⭐⭐⭐ (Medium-Hard)  
**Time Estimate:** 60-75 minutes  
**Job Requirement:** "Optimize data access across PostgreSQL"

---

## 📝 Problem Statement

Your company needs to process thousands of text documents for sentiment analysis. Processing them one-by-one is too slow. Build a batch processing API that can handle CSV uploads efficiently.

### Requirements

1. **POST /batch/upload**
   - Accepts CSV file upload
   - CSV format: `id,text` (header row + data rows)
   - Returns a batch job ID immediately
   - Processes all rows in the background

2. **GET /batch/{batch_id}**
   - Returns batch job status
   - Shows progress: `processed_count` / `total_count`
   - When complete, shows summary statistics

3. **GET /batch/{batch_id}/results**
   - Returns paginated results for completed batch
   - Each result includes: original text, sentiment, confidence

4. **Database Design**
   - Store batch jobs (id, status, total_count, processed_count)
   - Store individual results (batch_id, text, sentiment, score)

5. **Performance Requirements**
   - Use bulk database inserts (not one-by-one)
   - Process in chunks of 100 rows
   - Handle files with 10,000+ rows

### Example Usage

```bash
# Upload CSV file
curl -X POST http://localhost:8000/batch/upload \
  -F "file=@sample_data.csv"

# Response:
{
  "batch_id": "batch-123e4567",
  "status": "processing",
  "total_count": 1000,
  "processed_count": 0
}

# Check progress
curl http://localhost:8000/batch/batch-123e4567

# Response (in progress):
{
  "batch_id": "batch-123e4567",
  "status": "processing",
  "total_count": 1000,
  "processed_count": 450,
  "progress_percent": 45.0
}

# Response (completed):
{
  "batch_id": "batch-123e4567",
  "status": "completed",
  "total_count": 1000,
  "processed_count": 1000,
  "progress_percent": 100.0,
  "summary": {
    "positive": 523,
    "negative": 312,
    "neutral": 165
  }
}

# Get results (paginated)
curl "http://localhost:8000/batch/batch-123e4567/results?page=1&per_page=50"

# Response:
{
  "batch_id": "batch-123e4567",
  "page": 1,
  "per_page": 50,
  "total_results": 1000,
  "results": [
    {"id": "row-1", "text": "Great product!", "sentiment": "positive", "score": 0.95},
    {"id": "row-2", "text": "Terrible service", "sentiment": "negative", "score": 0.91},
    ...
  ]
}
```

### Sample CSV Format

```csv
id,text
1,This product exceeded my expectations!
2,Terrible customer service experience
3,Average quality, nothing special
4,Absolutely love this! Will buy again
5,Complete waste of money
```

---

## 🎯 Learning Objectives

1. **File Upload Handling** - CSV parsing in FastAPI
2. **Bulk Database Operations** - Efficient inserts with SQLAlchemy
3. **Progress Tracking** - Real-time batch status updates
4. **Chunked Processing** - Memory-efficient large file handling
5. **Pagination** - API design for large result sets

---

## 🚀 Getting Started

1. Copy the boilerplate:
   ```bash
   cp -r ../../BOILERPLATE ./practice
   cd practice
   ```

2. Create a sample CSV file for testing:
   ```bash
   echo "id,text" > sample_data.csv
   echo "1,This is amazing!" >> sample_data.csv
   echo "2,Terrible experience" >> sample_data.csv
   echo "3,Just okay" >> sample_data.csv
   ```

3. Implement the solution

4. Test with larger files (generate 1000+ rows)

---

## 💡 Hints

<details>
<summary>Hint 1: How to read CSV from upload?</summary>

```python
import csv
import codecs
from fastapi import UploadFile, File

@app.post("/batch/upload")
async def upload_batch(file: UploadFile = File(...)):
    # Read CSV
    csv_reader = csv.DictReader(
        codecs.iterdecode(file.file, 'utf-8')
    )
    
    rows = list(csv_reader)
    total_count = len(rows)
    
    # Process rows...
```
</details>

<details>
<summary>Hint 2: How to do bulk inserts?</summary>

```python
def bulk_insert_results(db: Session, results: list[dict]):
    """Insert many rows at once"""
    objects = [
        BatchResult(
            batch_id=r["batch_id"],
            original_text=r["text"],
            sentiment=r["sentiment"],
            score=r["score"]
        )
        for r in results
    ]
    db.bulk_save_objects(objects)
    db.commit()
```
</details>

<details>
<summary>Hint 3: How to process in chunks?</summary>

```python
def process_in_chunks(items: list, chunk_size: int = 100):
    """Yield successive chunks from list"""
    for i in range(0, len(items), chunk_size):
        yield items[i:i + chunk_size]

# Usage:
for chunk in process_in_chunks(all_rows, 100):
    results = [process_row(row) for row in chunk]
    bulk_insert_results(db, results)
    
    # Update progress
    batch.processed_count += len(chunk)
    db.commit()
```
</details>

<details>
<summary>Hint 4: Database models for batch processing</summary>

```python
class BatchJob(Base):
    __tablename__ = "batch_jobs"
    
    id = Column(Integer, primary_key=True)
    batch_uuid = Column(String, unique=True, index=True)
    status = Column(String, default="pending")
    total_count = Column(Integer, default=0)
    processed_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class BatchResult(Base):
    __tablename__ = "batch_results"
    
    id = Column(Integer, primary_key=True)
    batch_uuid = Column(String, index=True)  # Foreign key to batch
    row_id = Column(String)
    original_text = Column(Text)
    sentiment = Column(String)
    score = Column(Float)
```
</details>

---

## ✅ Success Criteria

- [ ] CSV upload creates batch job immediately
- [ ] Background processing handles all rows
- [ ] Progress updates visible during processing
- [ ] Bulk inserts used (not row-by-row)
- [ ] Pagination works correctly on results
- [ ] Handles 1000+ row files without memory issues
- [ ] Proper error handling for invalid CSV

---

## 🔍 What Interviewers Look For

**Good:**
- ✅ Working file upload
- ✅ Basic batch processing
- ✅ Progress tracking

**Great:**
- ✅ All of above, plus:
- ✅ Chunked processing for memory efficiency
- ✅ Bulk database operations
- ✅ Proper pagination

**Excellent:**
- ✅ All of above, plus:
- ✅ Handles malformed CSV gracefully
- ✅ Summary statistics on completion
- ✅ Can explain why chunking matters

---

## 📚 Key Concepts

- **Bulk Operations**: `db.bulk_save_objects()` vs individual `db.add()`
- **Chunking**: Process N items at a time to control memory
- **Progress Tracking**: Update database periodically, not every row
- **Pagination**: `OFFSET` and `LIMIT` in SQL

---

## ⏱️ Time Management

- **10 min**: Database models (BatchJob, BatchResult)
- **15 min**: File upload and CSV parsing
- **15 min**: Background processing with chunking
- **10 min**: Progress tracking endpoint
- **10 min**: Results pagination endpoint
- **10 min**: Testing and error handling
- **5 min**: Code cleanup

**Total: 75 minutes**

---

## 🧪 Testing Commands

```bash
# Generate test file with 1000 rows
python -c "
import random
sentiments = ['Great product!', 'Terrible service', 'Just average', 'Love it!', 'Hate it!']
print('id,text')
for i in range(1000):
    print(f'{i},{random.choice(sentiments)} Row {i}')
" > test_1000.csv

# Upload
curl -X POST http://localhost:8000/batch/upload -F "file=@test_1000.csv"

# Monitor progress (run multiple times)
watch -n 2 'curl -s http://localhost:8000/batch/YOUR_BATCH_ID | python -m json.tool'

# Get results
curl "http://localhost:8000/batch/YOUR_BATCH_ID/results?page=1&per_page=10"
```

---

**This practice teaches you to handle real-world data processing at scale!**
