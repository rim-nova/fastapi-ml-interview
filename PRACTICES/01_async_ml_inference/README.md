# Practice 01: Async ML Inference

**Difficulty:** ⭐⭐ (Medium)  
**Time Estimate:** 45-60 minutes  
**Job Requirement:** "Integrate ML models into production systems"

---

## 📝 Problem Statement

You need to build an API for a text sentiment analysis model. The ML model takes approximately 5 seconds to process each request. Users should NOT have to wait 5 seconds for an HTTP response.

### Requirements

1. **POST /predict**
   - Accepts JSON with `text` field
   - Immediately returns a job ID and status "processing"
   - Starts ML inference in the background

2. **GET /jobs/{job_id}**
   - Returns current status of the job (pending, processing, completed, failed)
   - If completed, includes the result (sentiment label and confidence score)

3. **Database Integration**
   - Store all jobs in PostgreSQL
   - Track job status throughout lifecycle

4. **Mock ML Model**
   - Simulate a 5-second inference delay
   - Return sentiment: "positive" or "negative" with a confidence score

### Example Usage

```bash
# Submit job
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "This product is amazing!"}'

# Response:
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "processing"
}

# Check status (immediately)
curl http://localhost:8000/jobs/123e4567-e89b-12d3-a456-426614174000

# Response:
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "processing",
  "result": null
}

# Check status (after 5 seconds)
curl http://localhost:8000/jobs/123e4567-e89b-12d3-a456-426614174000

# Response:
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "completed",
  "result": {
    "sentiment": "positive",
    "confidence": 0.95
  }
}
```

---

## 🎯 Learning Objectives

By completing this practice, you will master:

1. **FastAPI BackgroundTasks** - The correct way to handle slow operations
2. **Database State Management** - Updating job status across async operations
3. **UUID Generation** - Creating unique job identifiers
4. **Error Handling** - What happens if ML inference fails?

---

## 🚀 Getting Started

1. Copy the boilerplate:
   ```bash
   cp -r ../../BOILERPLATE ./practice
   cd practice
   ```

2. Try to solve the problem yourself FIRST (no peeking at solution!)

3. Run your solution:
   ```bash
   docker-compose up --build
   ```

4. Test it:
   ```bash
   curl -X POST http://localhost:8000/predict -H "Content-Type: application/json" -d '{"text": "test"}'
   ```

---

## 💡 Hints (If You're Stuck)

<details>
<summary>Hint 1: How to run code in the background?</summary>

FastAPI has a built-in `BackgroundTasks` class. Import it and add it as a parameter:

```python
from fastapi import BackgroundTasks

@app.post("/predict")
def predict(data: dict, background_tasks: BackgroundTasks):
    background_tasks.add_task(your_function, arg1, arg2)
    return {"status": "processing"}
```
</details>

<details>
<summary>Hint 2: How to generate unique IDs?</summary>

Use Python's `uuid` library:

```python
import uuid

job_id = str(uuid.uuid4())
```
</details>

<details>
<summary>Hint 3: How to update database inside background task?</summary>

Pass a NEW database session to the background task:

```python
def process_job(job_id: str, text: str):
    # Create new session inside the task
    db = SessionLocal()
    try:
        job = db.query(MLJob).filter(MLJob.job_uuid == job_id).first()
        job.status = "completed"
        db.commit()
    finally:
        db.close()
```
</details>

---

## ✅ Success Criteria

Your solution is correct if:

- [ ] POST /predict returns immediately (< 1 second)
- [ ] GET /jobs/{id} returns "processing" initially
- [ ] GET /jobs/{id} returns "completed" after 5+ seconds
- [ ] Database correctly stores all job states
- [ ] Docker setup works with a single command
- [ ] Code handles errors (try sending invalid data)

---

## 🔍 What Interviewers Look For

**Good:**
- ✅ Uses BackgroundTasks correctly
- ✅ Proper database session management
- ✅ Basic error handling

**Great:**
- ✅ All of the above, plus:
- ✅ Logs progress of background tasks
- ✅ Returns 404 for non-existent job IDs
- ✅ Validates input (text not empty, reasonable length)

**Excellent:**
- ✅ All of the above, plus:
- ✅ Adds a /jobs endpoint to list all jobs
- ✅ Implements job cleanup (delete old jobs)
- ✅ Swagger docs are clear and useful

---

## 📚 Key Concepts to Review

Before attempting this:
- FastAPI dependencies (Depends)
- SQLAlchemy basic queries
- Background task patterns
- HTTP status codes (200, 404, 422)

---

## ⏱️ Time Management

- **10 min**: Set up boilerplate and database model
- **15 min**: Implement POST /predict endpoint
- **10 min**: Implement background task function
- **10 min**: Implement GET /jobs/{id} endpoint
- **10 min**: Testing and debugging
- **5 min**: Add error handling and logging

**Total: 60 minutes**

---

## 🎓 After You're Done

1. Compare your solution to `SOLUTION.md`
2. Run the provided tests: `cd tests && pytest`
3. Can you improve your solution based on the reference?
4. Time yourself: Can you rebuild it in 45 minutes?

---

**Ready? Start coding! Remember: Try it yourself first before looking at the solution.**
