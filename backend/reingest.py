"""
reingest.py
Re-ingests all CSV files from the uploads/ directory directly into the DB.
Bypasses the HTTP API and runs the NLP pipeline directly.
Run with: python reingest.py
"""
import asyncio
import os
import sys
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Priority order: smallest file first for quick verification, big file next
PRIORITY_FILES = [
    "data.csv",
    "Datasetprojpowerbi.csv",
    "all_tickets_processed_improved_v3.csv",
]

UPLOADS_DIR = os.path.join(os.path.dirname(__file__), "uploads")


async def reingest_file(filename: str):
    from app.core.database import AsyncSessionLocal
    from app.services.semantic_nlp_pipeline import SemanticNLPPipeline
    from app.services.database_service import DatabaseService
    from app.api.routes.upload import _detect_schema, _normalize_dataframe
    from sqlalchemy import update
    from sqlalchemy.future import select
    from app.models.session import UploadSession

    filepath = os.path.join(UPLOADS_DIR, filename)
    if not os.path.exists(filepath):
        logger.warning(f"File not found, skipping: {filepath}")
        return

    logger.info(f"{'='*60}")
    logger.info(f"Re-ingesting: {filename} ({os.path.getsize(filepath)/1024/1024:.2f} MB)")
    logger.info(f"{'='*60}")

    data = pd.read_csv(filepath)
    logger.info(f"Loaded {len(data)} rows, columns: {list(data.columns)}")

    schema_info = _detect_schema(data)
    text_column = schema_info["text_column"]
    if not text_column:
        logger.error(f"No text column detected in {filename}, skipping.")
        return

    logger.info(f"Schema: {schema_info['schema_type']}, text col: {text_column}")

    # Create session record
    async with AsyncSessionLocal() as db:
        from app.services.database_service import DatabaseService
        session_record = await DatabaseService.create_upload_session(
            db=db, filename=filename, total_rows=len(data), user_id=None
        )
        session_id = session_record.id
        await db.commit()
    logger.info(f"Created session ID: {session_id}")

    # Normalize
    feedback_data = _normalize_dataframe(data, text_column)
    feedback_data = feedback_data[feedback_data["Reports"].str.strip().str.len() > 0].copy()
    feedback_data = feedback_data[feedback_data["Reports"].str.lower() != "nan"].copy()
    logger.info(f"After cleaning: {len(feedback_data)} rows")

    clustering_detected = schema_info["clustering_detected"]
    reduced_embeddings = None

    if clustering_detected:
        logger.info("Pre-clustered dataset — skipping NLP pipeline")
        from app.api.routes.upload import _build_result_from_semantic_dataset
        nlp_result, clustering_results = _build_result_from_semantic_dataset(feedback_data, schema_info)
    else:
        logger.info("Raw dataset — running full semantic NLP pipeline...")
        nlp_service = SemanticNLPPipeline()

        def _progress(stage):
            logger.info(f"  Pipeline stage: {stage}")

        nlp_result = nlp_service.process_feedback(feedback_data, progress_callback=_progress)
        if "error" in nlp_result:
            raise Exception(nlp_result["error"])
        clustering_results = nlp_result.get("clustering_results", {})
        feedback_data = nlp_result.get("processed_data", feedback_data)
        reduced_embeddings = nlp_result.get("reduced_embeddings", None)

    # Persist to DB
    logger.info("Saving to database...")
    async with AsyncSessionLocal() as db:
        await db.execute(
            update(UploadSession)
            .where(UploadSession.id == session_id)
            .values(total_rows=len(feedback_data))
        )
        complaints_saved, predictions_saved = await DatabaseService.save_complaints_and_predictions(
            db=db,
            processed_data=feedback_data,
            session_id=session_id,
            clustering_results=clustering_results,
            reduced_embeddings=reduced_embeddings,
        )
        await DatabaseService.update_session_status(db, session_id, "completed")
        await db.commit()

    logger.info(f"Saved {complaints_saved} complaints, {predictions_saved} predictions")
    logger.info(f"Done: {filename}")
    return complaints_saved


async def main():
    # Init DB tables
    from app.core.database import init_db
    await init_db()

    total = 0
    for fname in PRIORITY_FILES:
        try:
            count = await reingest_file(fname)
            if count:
                total += count
        except Exception as e:
            logger.error(f"Failed to re-ingest {fname}: {e}", exc_info=True)

    logger.info(f"\n{'='*60}")
    logger.info(f"Re-ingestion complete. Total records saved: {total}")
    logger.info(f"{'='*60}")

    # Warm up the cache
    logger.info("Pre-computing analytics cache...")
    from app.core.database import AsyncSessionLocal
    from app.api.routes.analytics import get_dashboard_summary, clustering_metrics, cluster_sentiment_heatmap
    from app.api.routes.clusters import get_clusters
    from app.services.cache_service import CacheService

    async with AsyncSessionLocal() as db:
        try:
            summary = await get_dashboard_summary(db)
            CacheService.set("summary", summary.model_dump() if hasattr(summary, "model_dump") else summary)
            logger.info("summary cached.")
        except Exception as e:
            logger.error(f"Cache warm-up failed – summary: {e}")

        try:
            metrics = await clustering_metrics(db)
            CacheService.set("clustering_metrics", metrics)
            logger.info("clustering_metrics cached.")
        except Exception as e:
            logger.error(f"Cache warm-up failed – clustering_metrics: {e}")

    logger.info("All done. You can now refresh the dashboard.")


if __name__ == "__main__":
    asyncio.run(main())
