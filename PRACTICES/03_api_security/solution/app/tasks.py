import time
from app.db.session import SessionLocal
from app import models


def process_ml_job(job_id: str):
    """
    Simulates a heavy ML inference task.
    Uses its own DB session (thread-safe).
    """
    db = SessionLocal()
    try:
        # Simulate processing time
        time.sleep(5)

        job = db.query(models.MLJob).filter(models.MLJob.job_uuid == job_id).first()
        if not job:
            return

        # Mock ML Logic
        text_lower = job.input_text.lower()
        if "bad" in text_lower or "terrible" in text_lower:
            sentiment = "negative"
        else:
            sentiment = "positive"

        job.status = "completed"
        job.result_label = sentiment
        job.result_score = 0.95
        db.commit()
        print(f"✅ Job {job_id} processed successfully.")

    except Exception as e:
        print(f"❌ Job {job_id} failed: {e}")
        job = db.query(models.MLJob).filter(models.MLJob.job_uuid == job_id).first()
        if job:
            job.status = "failed"
            db.commit()
    finally:
        db.close()
