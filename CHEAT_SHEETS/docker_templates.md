# Docker Templates Cheat Sheet

## 1. Dockerfile (Python FastAPI) - MEMORIZE THIS

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies (needed for psycopg2)
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 2. docker-compose.yml (Full Stack) - MEMORIZE THIS

```yaml
version: '3.8'

services:
  # FastAPI Backend
  web:
    build: .
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    depends_on:
      - db
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/mldb

  # PostgreSQL Database
  db:
    image: postgres:13
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=mldb
    ports:
      - "5432:5432"

volumes:
  postgres_data:
```

---

## 3. requirements.txt

```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
pydantic==2.5.0
python-multipart==0.0.6
```

---

## 4. Docker Commands (Essential)

### Build and Run
```bash
# Build the image
docker-compose build

# Start services
docker-compose up

# Start in background
docker-compose up -d

# Stop services
docker-compose down

# Rebuild and start
docker-compose up --build
```

### Debugging
```bash
# View logs
docker-compose logs

# Follow logs (real-time)
docker-compose logs -f

# View logs for specific service
docker-compose logs web

# Enter container shell
docker-compose exec web bash

# Run command in container
docker-compose exec web python -c "print('Hello')"
```

### Cleanup
```bash
# Stop and remove containers
docker-compose down

# Remove volumes too (DELETE DATABASE)
docker-compose down -v

# Remove all unused images
docker system prune -a
```

---

## 5. Dockerfile Variations

### With Redis
```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install dependencies including Redis
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Multi-Stage Build (Smaller Image)
```dockerfile
# Stage 1: Builder
FROM python:3.10 as builder

WORKDIR /app

RUN apt-get update && apt-get install -y libpq-dev gcc

COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.txt

# Stage 2: Runtime
FROM python:3.10-slim

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y libpq5 && rm -rf /var/lib/apt/lists/*

# Copy wheels from builder
COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache /wheels/*

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 6. docker-compose.yml Variations

### With Redis Cache
```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - db
      - redis
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/mldb
      - REDIS_URL=redis://redis:6379

  db:
    image: postgres:13
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=mldb

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

### With RabbitMQ (Message Queue)
```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - db
      - rabbitmq
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/mldb
      - RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/

  db:
    image: postgres:13
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=mldb

  rabbitmq:
    image: rabbitmq:3-management
    ports:
      - "5672:5672"   # AMQP port
      - "15672:15672" # Management UI
    environment:
      - RABBITMQ_DEFAULT_USER=guest
      - RABBITMQ_DEFAULT_PASS=guest

volumes:
  postgres_data:
```

### With Volume Mounts (For Development)
```yaml
version: '3.8'

services:
  web:
    build: .
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - .:/app  # Mount current directory
    ports:
      - "8000:8000"
    depends_on:
      - db
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/mldb

  db:
    image: postgres:13
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql  # Load SQL on startup
    environment:
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=mldb

volumes:
  postgres_data:
```

---

## 7. Environment Variables

### .env File (For Secrets)
```env
DATABASE_URL=postgresql://postgres:password@db:5432/mldb
SECRET_KEY=your-secret-key-here
API_KEY=your-api-key-here
REDIS_URL=redis://redis:6379
```

### Load in docker-compose
```yaml
services:
  web:
    build: .
    env_file:
      - .env
```

### Load in Python
```python
import os

DATABASE_URL = os.getenv("DATABASE_URL")
SECRET_KEY = os.getenv("SECRET_KEY", "default-secret")
```

---

## 8. Common Issues & Solutions

### Issue: "Port already in use"
**Error:** `Bind for 0.0.0.0:8000 failed: port is already allocated`

**Solution:**
```bash
# Find process using port
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or change port in docker-compose.yml
ports:
  - "8001:8000"  # Host:Container
```

### Issue: "Database connection refused"
**Error:** `could not connect to server: Connection refused`

**Solution:**
1. Check `depends_on` in docker-compose
2. Wait for database to be ready:
```python
import time
from sqlalchemy import create_engine

def wait_for_db(url, max_retries=5):
    for i in range(max_retries):
        try:
            engine = create_engine(url)
            engine.connect()
            return True
        except Exception:
            time.sleep(2)
    return False
```

### Issue: "Module not found"
**Error:** `ModuleNotFoundError: No module named 'fastapi'`

**Solution:**
1. Check requirements.txt exists
2. Rebuild image: `docker-compose build --no-cache`

### Issue: "Permission denied"
**Error:** `PermissionError: [Errno 13] Permission denied`

**Solution:**
```dockerfile
# Add this to Dockerfile
RUN useradd -m appuser
USER appuser
```

---

## 9. Health Checks

### In Dockerfile
```dockerfile
HEALTHCHECK --interval=30s --timeout=3s \
  CMD curl -f http://localhost:8000/health || exit 1
```

### In docker-compose.yml
```yaml
services:
  web:
    build: .
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 3s
      retries: 3
```

### Health Check Endpoint (FastAPI)
```python
@app.get("/health")
def health_check():
    return {"status": "healthy"}
```

---

## 10. Database Initialization

### init.sql (Run on First Start)
```sql
-- /init.sql
CREATE TABLE IF NOT EXISTS ml_jobs (
    id SERIAL PRIMARY KEY,
    job_uuid VARCHAR(255) UNIQUE NOT NULL,
    input_text TEXT,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_job_uuid ON ml_jobs(job_uuid);
CREATE INDEX idx_status ON ml_jobs(status);
```

### Mount in docker-compose
```yaml
db:
  image: postgres:13
  volumes:
    - postgres_data:/var/lib/postgresql/data
    - ./init.sql:/docker-entrypoint-initdb.d/init.sql
```

---

## 11. Testing Setup

### docker-compose.test.yml (Separate Test DB)
```yaml
version: '3.8'

services:
  test-db:
    image: postgres:13
    environment:
      - POSTGRES_PASSWORD=test
      - POSTGRES_DB=test_mldb
    ports:
      - "5433:5432"  # Different port to avoid conflicts
```

### Run Tests
```bash
# Start test database
docker-compose -f docker-compose.test.yml up -d

# Run tests
pytest

# Stop test database
docker-compose -f docker-compose.test.yml down -v
```

---

## 12. Production Dockerfile

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 appuser

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Set ownership
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Use production server
CMD ["gunicorn", "app.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000"]
```

---

## Quick Reference Card

### Start Everything
```bash
docker-compose up --build
```

### View Logs
```bash
docker-compose logs -f
```

### Access Container
```bash
docker-compose exec web bash
```

### Reset Everything
```bash
docker-compose down -v && docker-compose up --build
```

### Check Database
```bash
docker-compose exec db psql -U postgres -d mldb -c "SELECT * FROM ml_jobs LIMIT 5;"
```

---

## Interview Day Checklist

Before the interview, verify these work:
- [ ] `docker-compose up` starts without errors
- [ ] API is accessible at `http://localhost:8000`
- [ ] Database connection works
- [ ] Can access container: `docker-compose exec web bash`
- [ ] Logs are visible: `docker-compose logs`

---

**Print this and keep it nearby during the interview!**
