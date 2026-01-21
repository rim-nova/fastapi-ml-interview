import uuid
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.db.session import get_db
from app import schemas, models
from app.tasks import process_ml_job

# Create the router instance
router = APIRouter()


@router.post("/predict", response_model=schemas.JobResponse)
def create_prediction(
        request: schemas.JobCreate,
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db)
):
    """
    Submit text for sentiment analysis.
    Returns immediately with a Job ID.
    """
    # 1. Generate ID
    job_id = str(uuid.uuid4())

    # 2. Create DB Record (Pending)
    new_job = models.MLJob(
        job_uuid=job_id,
        input_text=request.text,
        status="pending"
    )
    db.add(new_job)
    db.commit()

    # 3. Queue the background task
    background_tasks.add_task(process_ml_job, job_id, request.text)

    # 4. Return immediately
    return schemas.JobResponse(job_uuid=job_id, status="pending")


@router.get("/jobs/{job_id}", response_model=schemas.JobResponse)
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """
    Poll this endpoint to check if the job is finished.
    """
    job = db.query(models.MLJob).filter(models.MLJob.job_uuid == job_id).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return job
