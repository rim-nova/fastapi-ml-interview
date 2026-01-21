# FastAPI SQL Boilerplate

A production-ready FastAPI boilerplate with **PostgreSQL** and **Alembic** migrations. Ideal for applications requiring
robust database management.

## ✨ Features

- 🚀 **FastAPI** with async support
- 🐘 **PostgreSQL** database
- 📦 **Alembic** migrations (version control for database schema)
- 🔐 **JWT Authentication** (access + refresh tokens)
- 🏗️ **SQLAlchemy 2.0** ORM
- ✅ **Pydantic v2** for validation
- 📝 **Auto-generated API docs**
- 🔄 **CRUD endpoints** with pagination
- 🐳 **Docker** ready with PostgreSQL
- 🧪 **pytest** setup included

## 🚀 Quick Start

### Option 1: Docker (Recommended)

```bash
# Start all services (API + PostgreSQL)
docker-compose up --build

# Run migrations
docker-compose exec api alembic upgrade head

# Seed database (optional)
docker-compose exec api python scripts/seed_data.py

# View logs
docker-compose logs -f api
```

### Option 2: Local Development

```bash
# 1. Start PostgreSQL (or use Docker)
docker run -d --name postgres -p 5432:5432 \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=fastapi_db \
  postgres:15-alpine

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy and configure environment
cp .env.example .env
# Edit .env with your settings

# 5. Run migrations
alembic upgrade head

# 6. Seed database (optional)
python scripts/seed_data.py

# 7. Start the server
uvicorn app.main:app --reload
```

## 🔄 Alembic Migrations

### Essential Commands

```bash
# Apply all migrations
alembic upgrade head

# Revert last migration
alembic downgrade -1

# Revert all migrations
alembic downgrade base

# Show current migration
alembic current

# Show migration history
alembic history
```

### Creating New Migrations

```bash
# Auto-generate from model changes
alembic revision --autogenerate -m "Add user profile fields"

# Create empty migration (for manual changes)
alembic revision -m "Add custom indexes"
```

### Migration Best Practices

1. **Always review auto-generated migrations** - Alembic may miss some changes
2. **Test migrations both ways** - Run upgrade and downgrade
3. **Use meaningful names** - `add_user_avatar` not `migration_001`
4. **Small, focused migrations** - One logical change per migration
5. **Never edit applied migrations** - Create new ones instead

## 🔧 Configuration

### Database Settings

```env
# PostgreSQL connection
DATABASE_URL=postgresql://user:pass@localhost:5432/dbname

# Connection pool (production tuning)
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
```

### Environment-Based Configuration

| Setting       | Development | Production      |
|---------------|-------------|-----------------|
| DEBUG         | true        | false           |
| DB_ECHO       | true        | false           |
| DOCS_URL      | /docs       | null (disabled) |
| LOG_LEVEL     | DEBUG       | INFO            |
| BCRYPT_ROUNDS | 10          | 12              |

## 🐳 Docker Commands

```bash
# Start services
docker-compose up -d

# Start with PgAdmin
docker-compose --profile tools up -d

# View PostgreSQL logs
docker-compose logs -f postgres

# Access PostgreSQL CLI
docker-compose exec postgres psql -U postgres -d fastapi_db

# Run migrations in container
docker-compose exec api alembic upgrade head

# Backup database
docker-compose exec postgres pg_dump -U postgres fastapi_db > backup.sql

# Restore database
docker-compose exec -T postgres psql -U postgres fastapi_db < backup.sql
```

## 🧪 Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_auth.py -v

# Run with output
pytest -s
```

## 📦 Database Seeding

After running migrations, seed the database with sample data:

```bash
python scripts/seed_data.py
```

### Test Credentials

| Email             | Password  | Role       |
|-------------------|-----------|------------|
| admin@example.com | Admin123! | Superuser  |
| user@example.com  | User123!  | Regular    |
| test@example.com  | Test123!  | Unverified |

## 🔗 API Endpoints

Same as BOILERPLATE_MINIMAL, plus:

### Database Management (Dev Only)

| Method | Endpoint                  | Description           |
|--------|---------------------------|-----------------------|
| GET    | `/api/v1/health/ready`    | DB connectivity check |
| GET    | `/api/v1/health/detailed` | Full health status    |

## 🚀 Production Deployment

### Environment Setup

```bash
# Generate secure secret key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Set production environment
export ENVIRONMENT=production
export DEBUG=false
export DATABASE_URL=postgresql://user:pass@prod-db:5432/app
```

### Production Checklist

- [ ] Secure `SECRET_KEY` (min 32 chars, randomly generated)
- [ ] Set `DEBUG=false`
- [ ] Configure proper `CORS_ORIGINS`
- [ ] Set up database backups
- [ ] Configure connection pool for load
- [ ] Enable SSL for database connection
- [ ] Set up monitoring (health checks)
- [ ] Configure log aggregation

### Scaling Tips

1. **Connection Pooling**: Use PgBouncer for many connections
2. **Read Replicas**: Route read queries to replicas
3. **Caching**: Add Redis for frequently accessed data
4. **Async**: Use asyncpg for better throughput

## 📝 Adding New Models

1. Create model in `app/models/`:

```python
# app/models/product.py
from app.models.base import Base, TimestampMixin


class Product(Base, TimestampMixin):
    name: Mapped[str] = mapped_column(String(255))
    price: Mapped[float] = mapped_column(Float)
```

2. Import in `alembic/env.py`:

```python
from app.models.product import Product
```

3. Generate migration:

```bash
alembic revision --autogenerate -m "Add product table"
```

4. Apply migration:

```bash
alembic upgrade head
```

## 📄 License

MIT
