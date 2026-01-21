import logging
import uuid
import time
from datetime import datetime
from typing import List
from app.db.session import SessionLocal
from app import models

logger = logging.getLogger(__name__)


def chunk_list(items: list, chunk_size: int = 100):
    """Helper to split list into chunks for bulk processing."""
    for i in range(0, len(items), chunk_size):
        yield items[i:i + chunk_size]


def mock_sentiment_analysis(text: str) -> tuple[str, float]:
    """
    Simulates ML inference.
    In a real scenario, this would import a pipeline like Practice 1.
    """
    text_lower = text.lower()
    if any(word in text_lower for word in ["great", "amazing", "love", "excellent"]):
        return "positive", 0.92
    elif any(word in text_lower for word in ["terrible", "awful", "hate", "bad"]):
        return "negative", 0.89
    return "neutral", 0.75


def process_batch_job(batch_uuid: str, rows: List[dict]):
    """
    Background task to process CSV rows in chunks.
    Uses its own DB session to avoid 'Session is closed' errors.
    """
    db = SessionLocal()
    logger.info(f"🚀 Starting batch job {batch_uuid} with {len(rows)} rows")

    try:
        # 1. Retrieve job
        batch = db.query(models.BatchJob).filter(
            models.BatchJob.batch_uuid == batch_uuid
        ).first()

        if not batch:
            logger.error(f"❌ Batch {batch_uuid} not found in DB")
            return

        batch.status = "processing"
        db.commit()

        sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}

        # 2. Process in chunks
        for chunk in chunk_list(rows, chunk_size=100):
            results_to_insert = []

            for row in chunk:
                # Simulate ML latency
                time.sleep(0.005)

                row_id = row.get("id", str(uuid.uuid4()))
                text = row.get("text", "")

                sentiment, score = mock_sentiment_analysis(text)
                sentiment_counts[sentiment] += 1

                # Prepare object for bulk insert
                results_to_insert.append(
                    models.BatchResult(
                        batch_uuid=batch_uuid,
                        row_id=str(row_id),
                        original_text=text,
                        sentiment=sentiment,
                        score=score
                    )
                )

            # 3. Bulk Insert & Update Progress
            db.bulk_save_objects(results_to_insert)
            batch.processed_count += len(chunk)
            db.commit()

            logger.info(f"🔄 Batch {batch_uuid}: {batch.processed_count}/{batch.total_count} processed")

        # 4. Finalize
        batch.status = "completed"
        batch.summary = sentiment_counts
        batch.completed_at = datetime.utcnow()
        db.commit()

        logger.info(f"✅ Batch {batch_uuid} completed successfully.")

    except Exception as e:
        logger.exception(f"❌ Batch {batch_uuid} failed: {e}")
        try:
            batch.status = "failed"
            batch.error_message = str(e)
            db.commit()
        except Exception as e:
            logger.exception(e)
            pass
    finally:
        db.close()
