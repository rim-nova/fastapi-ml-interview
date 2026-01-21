from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
import uuid

from app import schemas, models, tasks
from app.db.session import get_db
from app.core.security import verify_api_key
from app.core.ratelimit import rate_limiter

router = APIRouter(
    prefix="/predict",
    tags=["Inference"]
)


@router.post(
    "",
    response_model=schemas.JobResponse,
    dependencies=[Depends(verify_api_key), Depends(rate_limiter)]
)
def create_prediction(
        job_in: schemas.JobCreate,
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db)
):
    """
    Submit text for analysis.
    Protected by API Key and Rate Limiter.
    """
    job_id = str(uuid.uuid4())

    # Create DB entry
    db_job = models.MLJob(
        job_uuid=job_id,
        input_text=job_in.text,
        status="pending"
    )
    db.add(db_job)
    db.commit()
    db.refresh(db_job)

    # Dispatch background task
    background_tasks.add_task(tasks.process_ml_job, job_id)

    return db_job
