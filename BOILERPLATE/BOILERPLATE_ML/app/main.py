from fastapi import FastAPI
from . import models
from .database import engine

# Create database tables
models.Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title="ML Backend Service",
    description="Production-ready ML API",
    version="1.0.0"
)

@app.get("/")
def read_root():
    """Root endpoint"""
    return {"message": "ML Backend Service is running"}

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

# Add your endpoints below this line
