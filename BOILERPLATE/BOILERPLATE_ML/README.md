# FastAPI ML Backend Boilerplate

This is your starter template for all practice exercises.

## Quick Start

```bash
# 1. Copy this boilerplate to a new directory
cp -r BOILERPLATE/ my_practice/

# 2. Navigate to the new directory
cd my_practice/

# 3. Start the services
docker-compose up --build

# 4. Test the API
curl http://localhost:8000/
```

## What's Included

- **Dockerfile**: Production-ready container configuration
- **docker-compose.yml**: Multi-service orchestration (API + Database)
- **requirements.txt**: Python dependencies
- **app/database.py**: Database connection and session management
- **app/models.py**: SQLAlchemy ORM models
- **app/schemas.py**: Pydantic validation schemas
- **app/main.py**: FastAPI application entry point

## Testing Endpoints

```bash
# Health check
curl http://localhost:8000/health

# Root endpoint
curl http://localhost:8000/
```

## Common Commands

```bash
# View logs
docker-compose logs -f

# Access container shell
docker-compose exec web bash

# Access database
docker-compose exec db psql -U postgres -d mldb

# Stop services
docker-compose down

# Reset everything (including database)
docker-compose down -v
```

## Modifying for Your Needs

1. **Add new models**: Edit `app/models.py`
2. **Add new schemas**: Edit `app/schemas.py`
3. **Add new endpoints**: Edit `app/main.py`
4. **Add new dependencies**: Edit `requirements.txt` and rebuild

## Troubleshooting

If services don't start:

```bash
# Rebuild from scratch
docker-compose down -v
docker-compose build --no-cache
docker-compose up
```

If port 8000 is in use:

```bash
# Change port in docker-compose.yml
ports:
  - "8001:8000"  # Use 8001 instead
```
