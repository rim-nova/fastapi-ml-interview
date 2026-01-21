import logging
from transformers import pipeline
from app.db.session import SessionLocal
from app import models

logger = logging.getLogger(__name__)

# Initialize the model globally to avoid reloading it for every request.
# In a real interview, mention: "I'm loading this here to simulate a heavy resource."
# It will download the model (~260MB) on the first run.
sentiment_pipeline = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")


def process_ml_job(job_id: str, text: str):
    """
    Background task that runs REAL ML inference.
    """
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

        logger.info(f"🧠 Starting AI inference for job {job_id}...")

        # 3. RUN REAL INFERENCE
        # This blocks the CPU, making it perfect for a background task demo.
        # Example output: [{'label': 'POSITIVE', 'score': 0.9998}]
        prediction = sentiment_pipeline(text)[0]

        sentiment = prediction['label'].lower()  # 'positive' or 'negative'
        confidence = prediction['score']

        # 4. Save results
        job.status = "completed"
        job.result_label = sentiment
        job.result_score = confidence
        db.commit()

        logger.info(f"✅ Job {job_id} completed: {sentiment} ({confidence:.4f})")

    except Exception as e:
        logger.error(f"❌ Job {job_id} failed: {e}")
        # Ideally set status to 'failed' here
        try:
            job.status = "failed"
            db.commit()
        except Exception as e:
            logger.exception(e)
            pass
    finally:
        db.close()
