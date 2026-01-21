import csv
import codecs
import uuid
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File
from sqlalchemy.orm import Session
from app.db.session import get_db
from app import models, schemas
from app.tasks import process_batch_job

router = APIRouter()


@router.post("/upload", response_model=schemas.BatchCreateResponse)
async def upload_batch(
        file: UploadFile = File(...),
        background_tasks: BackgroundTasks = None,
        db: Session = Depends(get_db)
):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    try:
        csv_reader = csv.DictReader(codecs.iterdecode(file.file, 'utf-8'))
        rows = list(csv_reader)

        if not rows or 'text' not in rows[0]:
            raise HTTPException(status_code=400, detail="CSV empty or missing 'text' column")

        total_count = len(rows)

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid CSV: {str(e)}")

    # Create Job Record
    batch_uuid = f"batch-{uuid.uuid4().hex[:12]}"
    batch_job = models.BatchJob(
        batch_uuid=batch_uuid,
        status="pending",
        total_count=total_count,
        processed_count=0
    )
    db.add(batch_job)
    db.commit()

    # Trigger Background Task
    background_tasks.add_task(process_batch_job, batch_uuid, rows)

    return {
        "batch_id": batch_uuid,
        "status": "processing",
        "total_count": total_count,
        "processed_count": 0
    }


@router.get("/{batch_id}", response_model=schemas.BatchStatusResponse)
def get_batch_status(batch_id: str, db: Session = Depends(get_db)):
    batch = db.query(models.BatchJob).filter(models.BatchJob.batch_uuid == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    progress = 0.0
    if batch.total_count > 0:
        progress = round((batch.processed_count / batch.total_count) * 100, 1)

    # FIX: Explicitly map the fields.
    # Do NOT use **batch.__dict__ because it misses the renaming logic.
    return {
        "batch_id": batch.batch_uuid,
        "status": batch.status,
        "total_count": batch.total_count,
        "processed_count": batch.processed_count,
        "progress_percent": progress,
        "summary": batch.summary,
        "error_message": batch.error_message,
        "created_at": batch.created_at,
        "completed_at": batch.completed_at
    }
