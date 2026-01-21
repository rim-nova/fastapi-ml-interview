import uuid
import time
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

# Import our custom modules
from app.config import settings
from app.db.session import create_tables, engine, get_db, SessionLocal
from app import models, schemas

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# Lifespan (Startup/Shutdown)
# =============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    # Startup: Create database tables
    create_tables()
    logger.info("Database tables created.")
    yield
    # Shutdown: Close connections
    engine.dispose()


# =============================================================================
# FastAPI App Definition
# =============================================================================
app = FastAPI(
    title="Async ML Inference API",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Background Task Logic
# =============================================================================
def process_ml_job(job_id: str, text: str):
    """
    Simulates a heavy ML inference task (5 seconds).

    CRITICAL: We must create a NEW database session here.
    The session passed to the API endpoint is closed after the response is sent.
    """
    db = SessionLocal()
    try:
        # 1. Retrieve the job
        job = db.query(models.MLJob).filter(models.MLJob.job_uuid == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found in background task.")
            return

        # 2. Update status to processing
        job.status = "processing"
        db.commit()

        # 3. Simulate Heavy ML Computation
        logger.info(f"Starting inference for job {job_id}...")
        time.sleep(5)

        # 4. Mock Inference Logic
        sentiment = "positive" if "amazing" in text.lower() else "negative"
        confidence = 0.95

        # 5. Save Results
        job.status = "completed"
        job.result_label = sentiment
        job.result_score = confidence
        db.commit()
        logger.info(f"Job {job_id} completed successfully.")

    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}")
        # Ideally, we should update the DB status to "failed" here
        try:
            job.status = "failed"
            db.commit()
        except:
            pass
    finally:
        db.close()  # Always close manually created sessions


# =============================================================================
# API Endpoints
# =============================================================================

@app.post("/predict", response_model=schemas.JobResponse)
def create_prediction(
        request: schemas.JobCreate,
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db)
):
    """
    1. Create Job in DB (status: pending)
    2. Trigger background task
    3. Return Job ID immediately
    """
    # Generate ID
    job_id = str(uuid.uuid4())

    # Create DB Record
    new_job = models.MLJob(
        job_uuid=job_id,
        input_text=request.text,
        status="pending"
    )
    db.add(new_job)
    db.commit()

    # Add to Background Tasks
    background_tasks.add_task(process_ml_job, job_id, request.text)

    return schemas.JobResponse(job_uuid=job_id, status="pending")


@app.get("/jobs/{job_id}", response_model=schemas.JobResponse)
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """
    Poll this endpoint to check if the job is finished.
    """
    job = db.query(models.MLJob).filter(models.MLJob.job_uuid == job_id).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return job
