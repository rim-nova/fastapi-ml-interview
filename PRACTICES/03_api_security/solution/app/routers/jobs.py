from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import schemas, models
from app.db.session import get_db
from app.core.security import verify_api_key

router = APIRouter(
    prefix="/jobs",
    tags=["Jobs"]
)


@router.get(
    "/{job_id}",
    response_model=schemas.JobResponse,
    dependencies=[Depends(verify_api_key)]
)
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """Check job status. Protected by API Key."""
    job = db.query(models.MLJob).filter(models.MLJob.job_uuid == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
