# Practice 05: Webhook Callbacks

**Difficulty:** ⭐⭐⭐ (Medium-Hard)  
**Time Estimate:** 45-60 minutes  
**Job Requirement:** "Event-driven systems using Kafka or RabbitMQ"

---

## 📝 Problem Statement

Your clients want to be notified when ML jobs complete instead of polling for status. Build a webhook system that sends HTTP callbacks when processing finishes.

### Requirements

1. **POST /predict** - Submit job with optional webhook URL
   - Accept `webhook_url` parameter
   - Return job ID immediately
   - Call webhook when job completes

2. **Webhook Payload**
   - POST request to the provided URL
   - Include: job_id, status, result, timestamp
   - Include signature for verification

3. **Retry Logic**
   - Retry failed webhooks up to 3 times
   - Exponential backoff (1s, 2s, 4s)
   - Log all delivery attempts

4. **GET /webhooks/{job_id}/status** - Check webhook delivery status
   - Show delivery attempts
   - Show success/failure status

### Example Usage

```bash
# Submit job with webhook
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Great product!",
    "webhook_url": "https://your-server.com/callback"
  }'

# Response:
{
  "job_id": "job-abc123",
  "status": "processing",
  "webhook_registered": true
}

# Your server receives (after processing):
POST https://your-server.com/callback
Content-Type: application/json
X-Signature: sha256=abc123...

{
  "job_id": "job-abc123",
  "status": "completed",
  "result": {
    "sentiment": "positive",
    "confidence": 0.95
  },
  "timestamp": "2024-01-15T10:30:00Z"
}

# Check webhook delivery status
curl http://localhost:8000/webhooks/job-abc123/status

# Response:
{
  "job_id": "job-abc123",
  "webhook_url": "https://your-server.com/callback",
  "delivery_status": "delivered",
  "attempts": [
    {
      "attempt": 1,
      "timestamp": "2024-01-15T10:30:01Z",
      "status_code": 200,
      "success": true
    }
  ]
}
```

---

## 🎯 Learning Objectives

1. **Webhook Design** - HTTP callback patterns
2. **Retry Logic** - Exponential backoff implementation
3. **Request Signing** - HMAC verification for security
4. **Delivery Tracking** - Logging attempt history
5. **Async HTTP Calls** - Non-blocking webhook delivery

---

## 🚀 Getting Started

1. Copy the boilerplate
2. Add webhook URL field to job model
3. Implement webhook delivery after job completion
4. Add retry logic with exponential backoff
5. Test with a mock webhook receiver

---

## 💡 Hints

<details>
<summary>Hint 1: Sending webhooks with requests</summary>

```python
import requests
import time

def send_webhook(url: str, payload: dict, max_retries: int = 3):
    """Send webhook with retry logic"""
    
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(
                url,
                json=payload,
                timeout=10,
                headers={"X-Signature": generate_signature(payload)}
            )
            
            if response.status_code < 400:
                return {"success": True, "status_code": response.status_code}
            
        except requests.RequestException as e:
            print(f"Webhook attempt {attempt} failed: {e}")
        
        # Exponential backoff
        if attempt < max_retries:
            time.sleep(2 ** (attempt - 1))  # 1s, 2s, 4s
    
    return {"success": False, "error": "Max retries exceeded"}
```
</details>

<details>
<summary>Hint 2: Generating signature for verification</summary>

```python
import hmac
import hashlib
import json

WEBHOOK_SECRET = "your-secret-key"

def generate_signature(payload: dict) -> str:
    """Generate HMAC signature for payload"""
    payload_bytes = json.dumps(payload, sort_keys=True).encode()
    signature = hmac.new(
        WEBHOOK_SECRET.encode(),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()
    return f"sha256={signature}"
```
</details>

<details>
<summary>Hint 3: Database model for webhook tracking</summary>

```python
class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"
    
    id = Column(Integer, primary_key=True)
    job_uuid = Column(String, index=True)
    webhook_url = Column(String)
    attempt_number = Column(Integer)
    status_code = Column(Integer, nullable=True)
    success = Column(Boolean)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```
</details>

<details>
<summary>Hint 4: Testing webhooks locally</summary>

```python
# Create a simple webhook receiver
# test_receiver.py

from fastapi import FastAPI, Request

app = FastAPI()
received_webhooks = []

@app.post("/callback")
async def receive_webhook(request: Request):
    body = await request.json()
    received_webhooks.append(body)
    print(f"Received webhook: {body}")
    return {"status": "received"}

@app.get("/callbacks")
def list_callbacks():
    return received_webhooks

# Run: uvicorn test_receiver:app --port 9000
# Use webhook_url: http://localhost:9000/callback
```
</details>

---

## ✅ Success Criteria

- [ ] Jobs accept optional webhook_url
- [ ] Webhook sent when job completes
- [ ] Payload includes all required fields
- [ ] Signature generated correctly
- [ ] Retry logic works (test by returning 500 first)
- [ ] Delivery attempts logged
- [ ] Status endpoint shows delivery history

---

## 🔍 What Interviewers Look For

**Good:**
- ✅ Basic webhook delivery
- ✅ Simple retry logic
- ✅ Error handling

**Great:**
- ✅ Exponential backoff
- ✅ Request signing
- ✅ Delivery tracking

**Excellent:**
- ✅ Configurable retry policy
- ✅ Dead letter queue concept
- ✅ Idempotency handling

---

## 📚 Key Concepts

- **Webhooks**: HTTP callbacks for event notification
- **Idempotency**: Safely handle duplicate deliveries
- **Exponential Backoff**: Gradually increase retry delay
- **Request Signing**: HMAC for payload verification
- **Dead Letter Queue**: Store failed deliveries for manual review

---

## ⏱️ Time Management

- **10 min**: Database model for webhook tracking
- **10 min**: Add webhook_url to predict endpoint
- **15 min**: Implement webhook delivery with retry
- **10 min**: Implement signature generation
- **10 min**: Status endpoint for delivery tracking
- **5 min**: Testing

**Total: 60 minutes**

---

## 🧪 Testing

```bash
# Start webhook receiver (in another terminal)
# Save the test_receiver.py code from Hint 4
uvicorn test_receiver:app --port 9000

# Submit job with webhook
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Great product!",
    "webhook_url": "http://localhost:9000/callback"
  }'

# Wait for processing, then check received webhooks
curl http://localhost:9000/callbacks

# Check delivery status
curl http://localhost:8000/webhooks/JOB_ID/status
```

---

**Master webhooks - they're essential for event-driven architectures!**
