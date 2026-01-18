# Practice 03: API Security & Rate Limiting

**Difficulty:** ⭐⭐ (Medium)  
**Time Estimate:** 30-45 minutes  
**Job Requirement:** "Implement secure systems with authentication, rate limiting, input validation"

---

## 📝 Problem Statement

Your ML API is getting spammed by bots. You need to add security layers to protect your resources.

### Requirements

1. **API Key Authentication**
   - All endpoints (except /health) require valid API key
   - API key must be sent in `x-api-key` header
   - Return 401 for missing/invalid keys

2. **Rate Limiting**
   - Limit: 5 requests per minute per IP address
   - Return 429 (Too Many Requests) when exceeded
   - Reset counter after 60 seconds

3. **Input Validation**
   - Text must be between 10-5000 characters
   - Return 400 (Bad Request) with helpful error message

4. **Maintain Existing Functionality**
   - All previous features still work
   - Health check endpoint remains public (no auth required)

### Valid API Keys (For Testing)
```
user-key-1
user-key-2
test-secret-key
```

### Example Usage

```bash
# Without API key - REJECTED
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "test"}'

# Response: 401 Unauthorized

# With valid API key - ACCEPTED
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -H "x-api-key: user-key-1" \
  -d '{"text": "This is a valid text for processing"}'

# Response: 200 OK

# Too many requests - RATE LIMITED
# (After 5 requests within 1 minute)
curl -X POST http://localhost:8000/predict \
  -H "x-api-key: user-key-1" \
  -H "Content-Type: application/json" \
  -d '{"text": "test"}'

# Response: 429 Too Many Requests
{
  "detail": "Rate limit exceeded. Try again in 30 seconds."
}

# Invalid text (too short) - VALIDATION ERROR
curl -X POST http://localhost:8000/predict \
  -H "x-api-key: user-key-1" \
  -H "Content-Type: application/json" \
  -d '{"text": "short"}'

# Response: 400 Bad Request
{
  "detail": "Text must be between 10 and 5000 characters"
}
```

---

## 🎯 Learning Objectives

1. **FastAPI Security Patterns** - Dependency injection for auth
2. **Rate Limiting Logic** - Time-based request tracking
3. **Pydantic Validation** - Custom validators with clear errors
4. **HTTP Status Codes** - 401 vs 403 vs 429
5. **Production Security** - Real-world API protection

---

## 🚀 Getting Started

1. Start with your Practice 01 solution (or copy boilerplate)
2. Add authentication layer
3. Add rate limiting
4. Add input validation
5. Test all scenarios

---

## 💡 Hints

<details>
<summary>Hint 1: How to check API keys?</summary>

Create a dependency function:

```python
from fastapi import Header, HTTPException

VALID_API_KEYS = {"user-key-1", "user-key-2", "test-secret-key"}

async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key not in VALID_API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return x_api_key
```

Then add to endpoints:
```python
@app.post("/predict", dependencies=[Depends(verify_api_key)])
```
</details>

<details>
<summary>Hint 2: How to implement rate limiting?</summary>

Use a dictionary to track requests per IP:

```python
from fastapi import Request
import time

# Global storage (in production, use Redis)
request_history = {}

def check_rate_limit(request: Request):
    ip = request.client.host
    now = time.time()
    
    # Get history for this IP
    history = request_history.get(ip, [])
    
    # Filter requests from last 60 seconds
    recent = [t for t in history if now - t < 60]
    
    # Check limit
    if len(recent) >= 5:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # Update history
    recent.append(now)
    request_history[ip] = recent
```
</details>

<details>
<summary>Hint 3: How to validate input length?</summary>

Use Pydantic validators:

```python
from pydantic import BaseModel, Field, validator

class JobCreate(BaseModel):
    text: str = Field(..., min_length=10, max_length=5000)
    
    @validator('text')
    def validate_text(cls, v):
        if len(v.strip()) < 10:
            raise ValueError("Text must be at least 10 characters")
        return v
```
</details>

---

## ✅ Success Criteria

- [ ] Health endpoint works WITHOUT authentication
- [ ] All other endpoints REQUIRE valid API key
- [ ] Invalid API key returns 401
- [ ] 6th request within 60 seconds returns 429
- [ ] Text with 5 characters returns 400 with clear message
- [ ] Rate limit resets after 60 seconds
- [ ] All tests pass

---

## 🔍 What Interviewers Look For

**Good:**
- ✅ Working authentication
- ✅ Basic rate limiting

**Great:**
- ✅ All of above, plus:
- ✅ Clear error messages
- ✅ Proper HTTP status codes
- ✅ Rate limit logic is correct

**Excellent:**
- ✅ All of above, plus:
- ✅ Explains limitations (in-memory vs Redis)
- ✅ Discusses production considerations
- ✅ Handles edge cases (empty text, whitespace)

---

## 📚 Related Concepts

- HTTP authentication methods (Bearer, API Key, OAuth)
- Rate limiting algorithms (Token bucket, Leaky bucket, Fixed window)
- Redis for distributed rate limiting
- Security headers (CORS, CSP, etc.)

---

## ⏱️ Time Management

- **5 min**: Review Practice 01 code
- **10 min**: Add API key authentication
- **10 min**: Implement rate limiting
- **5 min**: Add input validation
- **10 min**: Test all scenarios
- **5 min**: Handle edge cases

**Total: 45 minutes**

---

## 🎓 After You're Done

1. Can you explain why rate limiting uses IP address?
2. What are the limitations of in-memory rate limiting?
3. How would you implement this with Redis in production?
4. What other security measures could you add?

---

## 🔧 Testing Commands

```bash
# Test without auth (should fail)
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "This should be rejected"}'

# Test with valid auth (should succeed)
curl -X POST http://localhost:8000/predict \
  -H "x-api-key: user-key-1" \
  -H "Content-Type: application/json" \
  -d '{"text": "This should work perfectly fine"}'

# Test rate limit (run 6 times quickly)
for i in {1..6}; do
  curl -X POST http://localhost:8000/predict \
    -H "x-api-key: user-key-1" \
    -H "Content-Type: application/json" \
    -d '{"text": "Testing rate limit iteration '$i'"}'
  echo "\n---"
done

# Test validation (too short)
curl -X POST http://localhost:8000/predict \
  -H "x-api-key: user-key-1" \
  -H "Content-Type: application/json" \
  -d '{"text": "short"}'

# Health check (no auth required)
curl http://localhost:8000/health
```

---

**This is a CRITICAL practice. Master it before the interview!**
