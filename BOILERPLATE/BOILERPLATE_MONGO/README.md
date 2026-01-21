# FastAPI MongoDB Boilerplate

A production-ready FastAPI boilerplate with **MongoDB** using **Motor** (async driver). Perfect for applications
requiring flexible schemas, horizontal scaling, and document-oriented data.

## ✨ Features

- 🚀 **FastAPI** with full async support
- 🍃 **MongoDB** with Motor (async driver)
- 🔐 **JWT Authentication** (access + refresh tokens)
- 📝 **Pydantic v2** for validation
- 🔍 **Full-text search** support
- 📦 **Document-oriented** models
- 🔄 **CRUD endpoints** with pagination, filtering
- 📊 **Flexible schema** with metadata fields
- 🐳 **Docker** ready with MongoDB
- 🧪 **pytest** setup included

## 🚀 Quick Start

### Option 1: Docker (Recommended)

```bash
# Start all services (API + MongoDB)
docker-compose up --build

# Seed database (optional)
docker-compose exec api python scripts/seed_data.py

# View logs
docker-compose logs -f api

# Access MongoDB admin (if tools profile enabled)
docker-compose --profile tools up -d
# Open http://localhost:8081
```

### Option 2: Local Development

```bash
# 1. Start MongoDB (or use Docker)
docker run -d --name mongodb -p 27017:27017 mongo:7

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy and configure environment
cp .env.example .env
# Edit .env with your settings

# 5. Seed database (optional)
python scripts/seed_data.py

# 6. Start the server
uvicorn app.main:app --reload
```

## 🍃 MongoDB Advantages

### Why MongoDB for this project?

1. **Flexible Schema**: Add fields without migrations
2. **Embedded Documents**: Store related data together
3. **Horizontal Scaling**: Easy sharding for growth
4. **Full-Text Search**: Built-in text indexing
5. **Aggregation Pipeline**: Complex queries and analytics
6. **Async Driver**: Motor provides true async support

### Document Structure

```javascript
// User Document
{
    "_id"
:
    ObjectId("..."),
        "email"
:
    "user@example.com",
        "hashed_password"
:
    "...",
        "full_name"
:
    "John Doe",
        "is_active"
:
    true,
        "is_superuser"
:
    false,
        "created_at"
:
    ISODate("..."),
        "updated_at"
:
    ISODate("...")
}

// Item Document (flexible schema!)
{
    "_id"
:
    ObjectId("..."),
        "title"
:
    "My Item",
        "description"
:
    "...",
        "status"
:
    "active",
        "priority"
:
    "high",
        "price"
:
    99.99,
        "quantity"
:
    10,
        "tags"
:
    ["tag1", "tag2"],
        "metadata"
:
    {
        "custom_field"
    :
        "any value",
            "nested"
    :
        {
            "data"
        :
            "here"
        }
    }
,
    "owner_id"
:
    "user_id_string",
        "is_deleted"
:
    false,
        "created_at"
:
    ISODate("..."),
        "updated_at"
:
    ISODate("...")
}
```

## 🔗 API Endpoints

### Health

| Method | Endpoint                  | Description                |
|--------|---------------------------|----------------------------|
| GET    | `/api/v1/health`          | Basic health check         |
| GET    | `/api/v1/health/ready`    | MongoDB connectivity check |
| GET    | `/api/v1/health/detailed` | Full health status         |

### Authentication

| Method | Endpoint                       | Description          |
|--------|--------------------------------|----------------------|
| POST   | `/api/v1/auth/register`        | Register new user    |
| POST   | `/api/v1/auth/login`           | Login (OAuth2 form)  |
| POST   | `/api/v1/auth/login/json`      | Login (JSON body)    |
| POST   | `/api/v1/auth/refresh`         | Refresh access token |
| GET    | `/api/v1/auth/me`              | Get current user     |
| POST   | `/api/v1/auth/change-password` | Change password      |

### Items (CRUD)

| Method | Endpoint                     | Description            |
|--------|------------------------------|------------------------|
| GET    | `/api/v1/items`              | List items (paginated) |
| POST   | `/api/v1/items`              | Create item            |
| GET    | `/api/v1/items/{id}`         | Get item               |
| PUT    | `/api/v1/items/{id}`         | Update item            |
| DELETE | `/api/v1/items/{id}`         | Delete item (soft)     |
| POST   | `/api/v1/items/bulk`         | Bulk create            |
| DELETE | `/api/v1/items/bulk/delete`  | Bulk delete            |
| POST   | `/api/v1/items/{id}/restore` | Restore deleted        |
| GET    | `/api/v1/items/search/text`  | **Full-text search**   |

## 🔍 Full-Text Search

MongoDB provides powerful text search capabilities:

```bash
# Search items
GET /api/v1/items/search/text?q=premium+widget

# Results are sorted by text relevance score
```

### Creating Text Indexes

```javascript
// In mongo-init.js or via mongosh
db.items.createIndex(
    {"title": "text", "description": "text"},
    {weights: {"title": 10, "description": 5}}
);
```

## 🔧 Configuration

### MongoDB Settings

```env
# Local MongoDB
MONGODB_URL=mongodb://localhost:27017

# With authentication
MONGODB_URL=mongodb://user:pass@localhost:27017

# MongoDB Atlas
MONGODB_URL=mongodb+srv://user:pass@cluster.xxxxx.mongodb.net

# Database name
MONGODB_DB_NAME=fastapi_db

# Connection pool
MONGODB_MIN_POOL_SIZE=1
MONGODB_MAX_POOL_SIZE=10
```

## 🐳 Docker Commands

```bash
# Start services
docker-compose up -d

# Start with Mongo Express (web admin)
docker-compose --profile tools up -d

# View MongoDB logs
docker-compose logs -f mongodb

# Access MongoDB shell
docker-compose exec mongodb mongosh fastapi_db

# Export database
docker-compose exec mongodb mongodump --db fastapi_db --out /dump

# Import database
docker-compose exec mongodb mongorestore --db fastapi_db /dump/fastapi_db
```

## 🧪 Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=app --cov-report=html

# Run specific test
pytest tests/test_items.py -v
```

## 📦 Database Seeding

```bash
python scripts/seed_data.py
```

### Test Credentials

| Email             | Password  | Role       |
|-------------------|-----------|------------|
| admin@example.com | Admin123! | Superuser  |
| user@example.com  | User123!  | Regular    |
| test@example.com  | Test123!  | Unverified |

## 🎯 MongoDB Best Practices

### 1. Schema Design

```python
# Embed frequently accessed data together
{
    "order_id": "...",
    "customer": {  # Embedded instead of reference
        "name": "John",
        "email": "john@example.com"
    },
    "items": [
        {"product": "Widget", "price": 99.99}
    ]
}
```

### 2. Indexing Strategy

```javascript
// Single field index
db.items.createIndex({"status": 1})

// Compound index (order matters!)
db.items.createIndex({"owner_id": 1, "status": 1})

// Text index for search
db.items.createIndex({"title": "text", "description": "text"})
```

### 3. Query Optimization

```python
# Use projection to limit returned fields
await db.items.find(
    {"status": "active"},
    {"title": 1, "price": 1}  # Only return these fields
).to_list(100)

# Use aggregation for complex queries
pipeline = [
    {"$match": {"status": "active"}},
    {"$group": {"_id": "$owner_id", "count": {"$sum": 1}}},
    {"$sort": {"count": -1}}
]
await db.items.aggregate(pipeline).to_list(100)
```

## 🚀 Production Deployment

### Checklist

- [ ] Use MongoDB Atlas or managed MongoDB
- [ ] Enable authentication
- [ ] Configure replica set for high availability
- [ ] Set up proper indexes
- [ ] Configure connection pool for load
- [ ] Enable TLS/SSL
- [ ] Set up monitoring and alerts
- [ ] Configure backups

### MongoDB Atlas Connection

```env
MONGODB_URL=mongodb+srv://user:password@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
MONGODB_DB_NAME=production_db
```

## 📄 License

MIT
