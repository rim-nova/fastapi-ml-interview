# Common Pitfalls & Debugging Guide

## 1. CORS Errors (Frontend Integration)

### Symptom
```
Access to XMLHttpRequest has been blocked by CORS policy
```

### Why It Happens
Frontend (React) on `localhost:3000` trying to call API on `localhost:8000`

### The Fix (Memorize This)
```python
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Add IMMEDIATELY after creating app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production: ["https://yourdomain.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 2. Database Connection Errors

### Symptom
```
sqlalchemy.exc.OperationalError: could not connect to server
```

### Common Causes & Fixes

#### Cause 1: Wrong Connection String
```python
# ❌ Wrong
DATABASE_URL = "postgresql://localhost:5432/mldb"

# ✅ Correct (includes user and password)
DATABASE_URL = "postgresql://postgres:password@localhost:5432/mldb"
```

#### Cause 2: Database Not Running
```bash
# Check if PostgreSQL container is running
docker ps

# If not, start it
docker-compose up db
```

#### Cause 3: Wrong Host in Docker
```python
# ❌ Wrong (inside Docker)
DATABASE_URL = "postgresql://postgres:password@localhost:5432/mldb"

# ✅ Correct (use service name)
DATABASE_URL = "postgresql://postgres:password@db:5432/mldb"
```

---

## 3. Pydantic Validation Errors (422)

### Symptom
```json
{
  "detail": [
    {
      "loc": ["body", "price"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### Common Causes & Fixes

#### Cause 1: Missing Required Field
```python
# Model expects
class Item(BaseModel):
    name: str
    price: float  # Required!

# But you send
{
    "name": "test"  # Missing price!
}
```

**Fix:** Make field optional or provide value
```python
class Item(BaseModel):
    name: str
    price: Optional[float] = None  # Now optional
```

#### Cause 2: Wrong Data Type
```python
# Model expects int
class Item(BaseModel):
    quantity: int

# But you send string
{
    "quantity": "five"  # ❌ Should be 5
}
```

**Fix:** Send correct type or add validator
```python
from pydantic import validator

class Item(BaseModel):
    quantity: int
    
    @validator('quantity', pre=True)
    def parse_quantity(cls, v):
        if isinstance(v, str):
            return int(v)
        return v
```

---

## 4. Import Errors

### Symptom
```
ModuleNotFoundError: No module named 'app'
```

### Common Causes & Fixes

#### Cause 1: Wrong Project Structure
```
# ❌ Wrong
my_project/
  main.py
  models.py

# In main.py:
from app.models import MLJob  # Fails!
```

```
# ✅ Correct
my_project/
  app/
    __init__.py  # Important!
    main.py
    models.py
```

#### Cause 2: Missing __init__.py
Every Python package directory MUST have `__init__.py` (can be empty)

```bash
touch app/__init__.py
```

#### Cause 3: Wrong Import Path
```python
# If structure is:
# app/
#   main.py
#   models.py

# In main.py:
from models import MLJob  # ❌ Wrong (relative without dot)
from .models import MLJob  # ✅ Correct (relative with dot)
from app.models import MLJob  # ✅ Also correct (absolute)
```

---

## 5. Background Task Not Running

### Symptom
```python
background_tasks.add_task(process_job, job_id)
# But the function never executes!
```

### Common Causes & Fixes

#### Cause 1: Blocking the Main Thread
```python
# ❌ Wrong
def process_job(job_id):
    time.sleep(10)  # This blocks everything!

# ✅ Better (but still blocking)
def process_job(job_id):
    import asyncio
    asyncio.sleep(10)  # Non-blocking
```

#### Cause 2: Uncaught Exception
```python
# ❌ Task fails silently
def process_job(job_id):
    result = 1 / 0  # Exception kills task, no one knows!

# ✅ Log errors
def process_job(job_id):
    try:
        result = 1 / 0
    except Exception as e:
        print(f"Task failed: {e}")  # At least we see it!
```

#### Cause 3: Server Restarted
Background tasks are NOT persistent. If server restarts, tasks are lost.
**Solution:** Use Celery or message queue for important tasks.

---

## 6. Database Session Issues

### Symptom
```
sqlalchemy.orm.exc.DetachedInstanceError: Instance is not bound to a Session
```

### Why It Happens
You tried to access a relationship after the session closed.

```python
# ❌ Wrong
@app.get("/jobs/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(MLJob).filter(MLJob.id == job_id).first()
    return job  # Session closes here

# Later in code (after session closed):
print(job.user.name)  # Error! Session is closed
```

### The Fix
```python
# ✅ Option 1: Access within session
@app.get("/jobs/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(MLJob).filter(MLJob.id == job_id).first()
    user_name = job.user.name  # Access before return
    return {"job": job, "user": user_name}

# ✅ Option 2: Eager loading
from sqlalchemy.orm import joinedload

job = db.query(MLJob).options(joinedload(MLJob.user)).filter(...).first()
```

---

## 7. JSON Serialization Errors

### Symptom
```
TypeError: Object of type datetime is not JSON serializable
```

### Why It Happens
FastAPI can't serialize Python datetime to JSON automatically.

### The Fix
```python
# ✅ Option 1: Use Pydantic response model
from pydantic import BaseModel
from datetime import datetime

class JobResponse(BaseModel):
    id: int
    created_at: datetime  # Pydantic handles this
    
    class Config:
        orm_mode = True  # Allows conversion from SQLAlchemy model

@app.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: int, db: Session = Depends(get_db)):
    return db.query(MLJob).filter(MLJob.id == job_id).first()
```

```python
# ✅ Option 2: Manual conversion
from datetime import datetime

@app.get("/jobs/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(MLJob).filter(MLJob.id == job_id).first()
    return {
        "id": job.id,
        "created_at": job.created_at.isoformat()  # Convert to string
    }
```

---

## 8. Port Already in Use

### Symptom
```
OSError: [Errno 48] Address already in use
```

### The Fix
```bash
# Find what's using port 8000
lsof -i :8000

# Kill it
kill -9 <PID>

# Or use a different port
uvicorn main:app --port 8001
```

---

## 9. Docker Container Exits Immediately

### Symptom
```bash
docker-compose up
# Container starts then immediately exits
```

### Common Causes & Fixes

#### Cause 1: Syntax Error in Code
```bash
# Check logs
docker-compose logs web

# You'll see the Python error
```

#### Cause 2: Wrong CMD in Dockerfile
```dockerfile
# ❌ Wrong
CMD ["python", "main.py"]  # File doesn't exist!

# ✅ Correct
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Cause 3: Database Not Ready
```yaml
# Add depends_on
services:
  web:
    depends_on:
      - db  # Wait for db to start
```

---

## 10. File Upload Errors

### Symptom
```
422 Unprocessable Entity
```

### Why It Happens
Sending file wrong way, or missing Content-Type.

### The Fix
```python
# ✅ Correct endpoint
from fastapi import UploadFile, File

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    contents = await file.read()
    return {"filename": file.filename}
```

```bash
# ✅ Correct curl command
curl -X POST http://localhost:8000/upload \
  -F "file=@/path/to/file.csv"
```

---

## 11. Environment Variables Not Loading

### Symptom
```python
DATABASE_URL = os.getenv("DATABASE_URL")
print(DATABASE_URL)  # None
```

### Common Causes & Fixes

#### Cause 1: .env File Not Loaded
```python
# ✅ Install python-dotenv
pip install python-dotenv

# ✅ Load .env file
from dotenv import load_dotenv
load_dotenv()  # Must be BEFORE os.getenv()

DATABASE_URL = os.getenv("DATABASE_URL")
```

#### Cause 2: Wrong Variable Name
```env
# .env file
DATABASE_URL=postgresql://...

# Code
DB_URL = os.getenv("DB_URL")  # ❌ Typo!
```

#### Cause 3: .env Not in Docker
```yaml
# docker-compose.yml
services:
  web:
    env_file:
      - .env  # Load .env file
```

---

## 12. SQL Injection Vulnerability

### Symptom (Not an error, but dangerous!)
```python
# ❌ NEVER DO THIS
@app.get("/search")
def search(keyword: str, db: Session = Depends(get_db)):
    query = f"SELECT * FROM jobs WHERE text LIKE '%{keyword}%'"  # VULNERABLE!
    return db.execute(query).fetchall()
```

### The Fix
```python
# ✅ Use SQLAlchemy ORM (automatically safe)
@app.get("/search")
def search(keyword: str, db: Session = Depends(get_db)):
    return db.query(MLJob).filter(
        MLJob.text.ilike(f"%{keyword}%")  # Safe!
    ).all()

# ✅ Or use parameterized queries
from sqlalchemy import text

query = text("SELECT * FROM jobs WHERE text LIKE :keyword")
results = db.execute(query, {"keyword": f"%{keyword}%"})
```

---

## Quick Debugging Workflow

When something breaks:

1. **Check the error message carefully**
   - Read the FULL traceback
   - Look for the actual line that failed

2. **Add print statements**
   ```python
   print(f"DEBUG: job_id = {job_id}")
   print(f"DEBUG: query result = {result}")
   ```

3. **Check Docker logs**
   ```bash
   docker-compose logs -f web
   ```

4. **Test endpoint with curl**
   ```bash
   curl -X POST http://localhost:8000/predict \
     -H "Content-Type: application/json" \
     -d '{"text": "test"}'
   ```

5. **Check database**
   ```bash
   docker-compose exec db psql -U postgres -d mldb -c "SELECT * FROM ml_jobs;"
   ```

---

## Interview Day Debugging Strategy

### If Stuck for More Than 10 Minutes:

1. **Simplify**
   - Comment out complex logic
   - Test with hardcoded values
   - Does the SIMPLE case work?

2. **Search Your GitHub**
   - "I've done this before in Practice 03"
   - Copy your own pattern

3. **Check Official Docs**
   - FastAPI: https://fastapi.tiangolo.com/
   - SQLAlchemy: https://docs.sqlalchemy.org/

4. **Ask Clarifying Questions**
   - "Should this handle errors gracefully?"
   - "Is X expected behavior?"

### Things NOT to Say:
- ❌ "I can't do this without AI"
- ❌ "I'm not sure about anything"
- ❌ "This is impossible"

### Things TO Say:
- ✅ "Let me try a simpler approach first"
- ✅ "I'm going to check my reference code"
- ✅ "I'll add logging to debug this"

---

## Final Reminder

> **Every bug you encounter during practice is a bug you WON'T encounter during the interview.**

That's why practicing WITHOUT AI is crucial. You need to learn how to debug independently.

**Keep this open during the interview!**
