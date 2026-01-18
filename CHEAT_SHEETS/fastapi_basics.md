# FastAPI Basics Cheat Sheet

## 1. Minimal FastAPI App (Copy-Paste Ready)

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello World"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

## 2. Essential Imports (Memorize This Block)

```python
# Core FastAPI
from fastapi import FastAPI, HTTPException, Depends, Header, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

# Pydantic for validation
from pydantic import BaseModel, Field
from typing import Optional, List

# Database
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# Standard library
import os
import uuid
import time
from datetime import datetime
```

---

## 3. Pydantic Models (Request/Response Schemas)

### Basic Pattern
```python
class ItemCreate(BaseModel):
    name: str
    description: Optional[str] = None
    price: float = Field(..., gt=0)  # Must be > 0

class ItemResponse(BaseModel):
    id: int
    name: str
    price: float
    created_at: datetime
    
    class Config:
        orm_mode = True  # Allows conversion from SQLAlchemy models
```

### With Examples (For Swagger Docs)
```python
class PredictionRequest(BaseModel):
    text: str = Field(..., example="This is a sample text")
    model_version: str = Field(default="v1", example="v1")
    
class PredictionResponse(BaseModel):
    job_id: str
    status: str = Field(..., example="processing")
```

---

## 4. Request/Response Patterns

### POST Endpoint (Create)
```python
@app.post("/items", response_model=ItemResponse)
def create_item(item: ItemCreate):
    # Logic here
    return {"id": 1, "name": item.name, "price": item.price}
```

### GET Endpoint (Read)
```python
@app.get("/items/{item_id}", response_model=ItemResponse)
def get_item(item_id: int):
    # Logic here
    return {"id": item_id, "name": "Sample", "price": 99.99}
```

### GET with Query Parameters
```python
@app.get("/items")
def list_items(skip: int = 0, limit: int = 10, search: Optional[str] = None):
    return {"skip": skip, "limit": limit, "search": search}
```

---

## 5. Error Handling

### Raise HTTP Exceptions
```python
@app.get("/items/{item_id}")
def get_item(item_id: int):
    if item_id not in database:
        raise HTTPException(status_code=404, detail="Item not found")
    return database[item_id]
```

### Try-Except Pattern
```python
@app.post("/predict")
def predict(data: dict):
    try:
        result = ml_model.inference(data["text"])
        return {"result": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid input: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")
```

---

## 6. Dependency Injection

### Database Session Dependency
```python
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/items")
def create_item(item: ItemCreate, db: Session = Depends(get_db)):
    # Use db here
    return {}
```

### Authentication Dependency
```python
async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != "SECRET_KEY":
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return x_api_key

@app.post("/protected", dependencies=[Depends(verify_api_key)])
def protected_endpoint():
    return {"message": "You have access"}
```

---

## 7. Background Tasks (For Async Processing)

```python
def heavy_processing(job_id: str, data: str):
    print(f"Starting job {job_id}")
    time.sleep(10)  # Simulate ML model
    print(f"Job {job_id} completed")

@app.post("/process")
def process_data(data: dict, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    background_tasks.add_task(heavy_processing, job_id, data["text"])
    return {"job_id": job_id, "status": "processing"}
```

---

## 8. File Upload

```python
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    contents = await file.read()
    return {
        "filename": file.filename,
        "size": len(contents),
        "content_type": file.content_type
    }
```

### CSV Upload Pattern
```python
import csv
import codecs

@app.post("/upload-csv")
async def upload_csv(file: UploadFile = File(...)):
    csv_reader = csv.reader(codecs.iterdecode(file.file, 'utf-8'))
    next(csv_reader)  # Skip header
    
    data = []
    for row in csv_reader:
        data.append({"text": row[0], "label": row[1]})
    
    return {"rows_processed": len(data)}
```

---

## 9. CORS Setup (For Frontend Integration)

```python
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 10. Startup/Shutdown Events

```python
@app.on_event("startup")
async def startup_event():
    print("Application starting...")
    # Initialize connections, load models, etc.

@app.on_event("shutdown")
async def shutdown_event():
    print("Application shutting down...")
    # Close connections, cleanup, etc.
```

---

## 11. Response Status Codes

```python
from fastapi import status

@app.post("/items", status_code=status.HTTP_201_CREATED)
def create_item(item: ItemCreate):
    return {"message": "Created"}

@app.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: int):
    # Delete logic
    return  # No content returned
```

---

## 12. Path & Query Parameter Validation

```python
from fastapi import Path, Query

@app.get("/items/{item_id}")
def get_item(
    item_id: int = Path(..., gt=0, description="The ID must be positive"),
    q: Optional[str] = Query(None, max_length=50)
):
    return {"item_id": item_id, "q": q}
```

---

## Common Patterns Decision Tree

**If they ask for:**
- "Process this slowly" → Use `BackgroundTasks`
- "Upload a file" → Use `UploadFile = File(...)`
- "Secure endpoint" → Use `Depends(verify_api_key)`
- "Return different status" → Use `status_code=status.HTTP_XXX`
- "Frontend integration" → Add `CORSMiddleware`
- "Input validation" → Use Pydantic `Field` with constraints

---

## Testing Commands

```bash
# Start the app
uvicorn main:app --reload

# Test with curl
curl http://localhost:8000/
curl -X POST http://localhost:8000/items -H "Content-Type: application/json" -d '{"name": "test", "price": 10}'

# With API Key
curl -X GET http://localhost:8000/protected -H "x-api-key: SECRET_KEY"
```

---

## Quick Debugging Checklist

If the app won't start:
1. Check imports - typo in module name?
2. Check port - is 8000 already in use?
3. Check syntax - missing colon or parenthesis?

If endpoint returns 422:
1. Check Pydantic model - does request match schema?
2. Check required fields - are they all provided?
3. Check data types - string vs int mismatch?

If endpoint returns 500:
1. Check logs - what's the actual error?
2. Check database connection - is it up?
3. Add try/except - catch the specific error

---

**Print this page and keep it during the interview!**
