# Practice 04: Model Versioning & A/B Testing

**Difficulty:** ⭐⭐⭐ (Senior Level)
**Tech Stack:** FastAPI, PostgreSQL, SQLAlchemy, Docker, TextBlob (NLP)

This project implements a production-grade **ML Model Registry** and **A/B Testing Router**. It solves the problem of
safely rolling out new model versions by allowing traffic splitting and performance monitoring.

---

## 🏗️ Architecture

The system uses a **Sticky Routing** strategy to ensure consistent user experiences during A/B tests.

```mermaid
[Client Request]
      │
      ▼
[API Gateway / Router]
      │
      ├── (Config Check) ──▶ [Database: Active Models]
      │
      ├── (User ID Hash) ──▶ [Deterministic Bucket (0-99)]
      │
      ▼
[Select Model Version]
      │
      ├── (v1.0.0) ──▶ [TextBlob Basic]
      │
      └── (v2.0.0) ──▶ [TextBlob Advanced]
            │
            ▼
      [Log Result to DB]
            │
            ▼
      [Return Response]

```

---

## 🚀 Key Features

1. **Model Registry**: Register, activate, and manage multiple model versions via API.
2. **Deterministic A/B Testing (Sticky Routing)**:

* Uses `SHA-256` hashing of `user_id` to ensure a specific user *always* sees the same model version.
* Prevents "flickering" (user seeing different results on refresh).


3. **Real ML Inference**:

* **v1.0.0**: Basic polarity check (Fast, simple).
* **v2.0.0**: Advanced subjectivity-weighted logic (Slower, smarter).


4. **Performance Analytics**: Compare models side-by-side based on:

* Latency (ms)
* Confidence Scores
* Request Volume

---

## ⚡ Quick Start

### 1. Start Services

Run the entire stack with Docker Compose. This handles the Database and API.

```bash
docker-compose up --build

```

### 2. Register Models

Open a new terminal. We will register two versions of our sentiment model.

```bash
# Register v1.0.0 (Legacy)
curl -X POST http://localhost:8000/models \
  -H "Content-Type: application/json" \
  -d '{"name": "sentiment", "version": "1.0.0"}'

# Register v2.0.0 (Challenger)
curl -X POST http://localhost:8000/models \
  -H "Content-Type: application/json" \
  -d '{"name": "sentiment", "version": "2.0.0"}'

```

*(Note the UUIDs returned in the response for the next step)*

### 3. Configure A/B Split

Set traffic to 50% for both models. Replace `UUID` with your actual IDs.

```bash
# Activate v1
curl -X POST http://localhost:8000/models/{UUID_V1}/activate \
  -H "Content-Type: application/json" \
  -d '{"percent": 50}'

# Activate v2
curl -X POST http://localhost:8000/models/{UUID_V2}/activate \
  -H "Content-Type: application/json" \
  -d '{"percent": 50}'

```

---

## 🧪 Testing the Routing

### Scenario A: Sticky Routing (Consistent User)

When you provide a `user_id`, the system hashes it to lock the user to a specific model.

```bash
# Run this 5 times. You will see the SAME model version every time.
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "I love this!", "user_id": "user_123"}'

```

### Scenario B: Random Routing (Anonymous User)

Without a `user_id`, the system falls back to pure random selection.

```bash
# Run this 5 times. You will see model versions flip randomly.
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "I love this!"}'

```

---

## 📊 Analytics

Check which model is winning (Higher confidence? Lower latency?).

```bash
curl http://localhost:8000/models/stats

```

**Example Output:**

```json
[
  {
    "model_version": "1.0.0",
    "request_count": 12,
    "avg_latency": 104.2,
    "avg_confidence": 0.75
  },
  {
    "model_version": "2.0.0",
    "request_count": 10,
    "avg_latency": 25.4,
    "avg_confidence": 0.82
  }
]

```

---

## 🧠 Interview Concepts

### Why "Sticky" Routing?

In production, if a user refreshes a page and the ML prediction changes (e.g., a "Recommended for You" widget), it
creates a confusing User Experience (UX). Sticky routing guarantees consistency for the duration of the test.

### Why separate Registry and Logs?

* **OLTP (Registry):** Requires strong consistency (ACID) for configuration management.
* **OLAP (Logs):** High-volume write data. In a real system, `PredictionLog` would likely be moved to a data warehouse (
  Snowflake/BigQuery) or handled asynchronously (Kafka) to prevent slowing down the prediction API.