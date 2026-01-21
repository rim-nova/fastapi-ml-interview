# FastAPI Minimal Boilerplate

A lightweight, production-ready FastAPI boilerplate with SQLite. Perfect for quick prototypes, interviews, and small
projects.

## ✨ Features

- 🚀 **FastAPI** with async support
- 🔐 **JWT Authentication** (access + refresh tokens)
- 📦 **SQLite** database (zero configuration)
- 🏗️ **SQLAlchemy 2.0** ORM with async support
- ✅ **Pydantic v2** for validation
- 📝 **Auto-generated API docs** (Swagger & ReDoc)
- 🔄 **CRUD endpoints** with pagination, filtering, search
- 🛡️ **Security middleware** (rate limiting, request logging)
- 🐳 **Docker** ready with multi-stage build

## 🚀 Quick Start

### Option 1: Local Development

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy environment file
cp .env.example .env

# 4. Run the server
uvicorn app.main:app --reload

# 5. Open API docs
# http://localhost:8000/docs
```

### Option 2: Docker

```bash
# Build and run
docker-compose up --build

# Or just run
docker-compose up -d

# View logs
docker-compose logs -f api
```

## 🔗 API Endpoints

### Health

| Method | Endpoint                  | Description               |
|--------|---------------------------|---------------------------|
| GET    | `/api/v1/health`          | Basic health check        |
| GET    | `/api/v1/health/ready`    | Readiness check (with DB) |
| GET    | `/api/v1/health/detailed` | Detailed health status    |

### Authentication

| Method | Endpoint                       | Description          |
|--------|--------------------------------|----------------------|
| POST   | `/api/v1/auth/register`        | Register new user    |
| POST   | `/api/v1/auth/login`           | Login (OAuth2 form)  |
| POST   | `/api/v1/auth/login/json`      | Login (JSON body)    |
| POST   | `/api/v1/auth/refresh`         | Refresh access token |
| GET    | `/api/v1/auth/me`              | Get current user     |
| POST   | `/api/v1/auth/change-password` | Change password      |
| POST   | `/api/v1/auth/logout`          | Logout               |

### Items (CRUD)

| Method | Endpoint                     | Description            |
|--------|------------------------------|------------------------|
| GET    | `/api/v1/items`              | List items (paginated) |
| POST   | `/api/v1/items`              | Create item            |
| GET    | `/api/v1/items/{id}`         | Get item               |
| PUT    | `/api/v1/items/{id}`         | Update item            |
| DELETE | `/api/v1/items/{id}`         | Delete item (soft)     |
| POST   | `/api/v1/items/bulk`         | Bulk create items      |
| DELETE | `/api/v1/items/bulk/delete`  | Bulk delete items      |
| POST   | `/api/v1/items/{id}/restore` | Restore deleted item   |

## 🔧 Configuration

All settings are managed via environment variables. See `.env.example`:

```env
# Application
APP_NAME=FastAPI App
DEBUG=true
API_V1_PREFIX=/api/v1

# Database (SQLite for minimal setup)
DATABASE_URL=sqlite:///./data/app.db

# Security
SECRET_KEY=your-super-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
ALGORITHM=HS256

# CORS
CORS_ORIGINS=["http://localhost:3000","http://localhost:8080"]
```

## 🔐 Authentication Flow

1. **Register**: `POST /api/v1/auth/register`
2. **Login**: `POST /api/v1/auth/login` → Returns access + refresh tokens
3. **Use API**: Add `Authorization: Bearer <access_token>` header
4. **Refresh**: `POST /api/v1/auth/refresh` with refresh token
5. **Logout**: `POST /api/v1/auth/logout`

### Example Login

```bash
# Using curl
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.com&password=password123"

# Using httpie
http --form POST :8000/api/v1/auth/login username=user@example.com password=password123
```

## 📦 Query Parameters for List Endpoints

```
GET /api/v1/items?page=1&page_size=20&status=active&search=keyword&sort_by=created_at&sort_order=desc
```

| Parameter    | Type   | Description                            |
|--------------|--------|----------------------------------------|
| `page`       | int    | Page number (default: 1)               |
| `page_size`  | int    | Items per page (default: 20, max: 100) |
| `status`     | string | Filter by status                       |
| `search`     | string | Search in title/description            |
| `sort_by`    | string | Sort field                             |
| `sort_order` | string | asc or desc                            |

## 🧪 Testing

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest

# With coverage
pytest --cov=app --cov-report=html
```

## 🐳 Docker Commands

```bash
# Build image
docker build -t fastapi-app .

# Run container
docker run -p 8000:8000 fastapi-app

# Development with docker-compose
docker-compose up --build

# Production
docker-compose -f docker-compose.yml up -d
```

## 📝 Development Tips

### Adding a New Endpoint

1. Create endpoint file in `app/api/v1/endpoints/`
2. Import and include router in `app/api/v1/router.py`
3. Add schemas in `app/schemas/`
4. Add models in `app/models/`

### Switching to PostgreSQL

1. Install driver: `pip install psycopg2-binary`
2. Update `DATABASE_URL` in `.env`:
   ```
   DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
   ```
3. Uncomment PostgreSQL service in `docker-compose.yml`

## 📄 License

MIT
