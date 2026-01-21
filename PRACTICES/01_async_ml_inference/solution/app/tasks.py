import time
import logging
from app.db.session import SessionLocal
from app import models

logger = logging.getLogger(__name__)


def process_ml_job(job_id: str, text: str):
    """
    Background task to simulate ML inference.
    Independent of HTTP logic.
    """
    # CRITICAL: Create a fresh DB session for the background task
    db = SessionLocal()
    try:
        # 1. Retrieve job
        job = db.query(models.MLJob).filter(models.MLJob.job_uuid == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found")
            return

        # 2. Update status to processing
        job.status = "processing"
        db.commit()

        # 3. Simulate heavy computation (5 seconds)
        logger.info(f"Starting inference for job {job_id}")
        time.sleep(5)

        # 4. Mock Inference Logic
        sentiment = "positive" if "amazing" in text.lower() else "negative"
        confidence = 0.95

        # 5. Save results
        job.status = "completed"
        job.result_label = sentiment
        job.result_score = confidence
        db.commit()
        logger.info(f"✅ Job {job_id} completed successfully.")

    except Exception as e:
        logger.error(f"❌ Job {job_id} failed: {e}")
        # Optional: Set status to 'failed' in DB here
    finally:
        db.close()
