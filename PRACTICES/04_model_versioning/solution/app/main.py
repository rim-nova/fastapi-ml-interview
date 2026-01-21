from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.db.session import engine
from app.models import sql
from app.routers import registry, inference

# Initialize DB Tables
sql.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routers
app.include_router(registry.router)
app.include_router(inference.router)


@app.get("/health")
def health_check():
    return {"status": "healthy"}
