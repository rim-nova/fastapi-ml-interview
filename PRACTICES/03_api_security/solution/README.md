# Secure ML Inference API (Practice 03)

An asynchronous ML inference API secured with API Key authentication, Rate Limiting, and Input Validation.

## 🔒 Security Features

1. **API Key Auth**: Requires `x-api-key` header for all operations except `/health`.
2. **Rate Limiting**: Limits IP addresses to 5 requests per minute.
3. **Input Validation**: Enforces text length (10-5000 chars) via Pydantic.

## 🚀 Usage

1. **Start Services**:
   ```bash
   docker-compose up --build
   ```

2. **Health Check (Public)**:
   ```bash
   curl http://localhost:8000/health
   ```

3. **Submit Job (Protected)**:
   ```bash
   curl -X POST http://localhost:8000/predict \
     -H "x-api-key: user-key-1" \
     -H "Content-Type: application/json" \
     -d '{"text": "This product is amazing!"}'
   ```

4. **Test Rate Limit**:
   Run the above command 6 times quickly. The 6th request will return `429 Too Many Requests`.