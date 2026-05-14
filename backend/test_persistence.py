#!/usr/bin/env python3
"""
End-to-end test script for database persistence.
Tests the complete flow: CSV upload → NLP processing → Database storage.
"""

import asyncio
import sys
import os
import pandas as pd
import logging
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
from app.core.database import Base
from app.models.session import UploadSession
from app.models.complaint import Complaint
from app.models.prediction import Prediction
from app.services.nlp_pipeline import NLPPipeline
from app.services.database_service import DatabaseService
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Use test database
TEST_DB_URL = "sqlite+aiosqlite:///./test_student_feedback.db"


async def setup_test_db():
    """Initialize test database."""
    engine = create_async_engine(TEST_DB_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    return engine


async def create_test_session(engine):
    """Create async session for testing."""
    AsyncSessionLocal = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False
    )
    return AsyncSessionLocal()


def create_test_csv():
    """Create test CSV file with sample feedback."""
    test_data = {
        'Reports': [
            "The wifi network is very slow and keeps disconnecting. Please fix the internet connectivity issues.",
            "I would like to purchase new software licenses for development. Can we get approval for this?",
            "The hardware installation for my laptop is not working properly. Need urgent support.",
            "Great job on the recent updates! The system is running much better now.",
            "Email server is down. Cannot access my university email. This is very frustrating.",
            "The password reset process is confusing. I need help resetting my account access.",
            "Amazing service! Really happy with the support team. Thank you so much!",
            "Network connectivity problem during my online class. Lost connection multiple times.",
            "Need to order new hardware - printer and mouse for the office.",
            "Poor quality of the recent system update. Many features are broken now.",
            # Additional rows for better TF-IDF
            "The network is down again. We need better WiFi infrastructure.",
            "Cannot login to my account. Password reset is not working.",
            "Email is still broken. Please restore the email service immediately.",
            "Hardware support team did great work installing my equipment.",
            "Software licenses need renewal. Requesting budget approval now.",
            "WiFi disconnects frequently during important meetings.",
            "Access issues preventing me from doing my work.",
            "Great experience with the technical support team today.",
            "Printer and monitor installation completed successfully.",
            "Network speed is too slow for video conferencing.",
        ]
    }

    df = pd.DataFrame(test_data)
    test_file = "test_feedback.csv"
    df.to_csv(test_file, index=False)
    logger.info(f"Created test CSV: {test_file} with {len(df)} rows")
    return test_file


async def run_end_to_end_test():
    """Run complete end-to-end test."""
    logger.info("=" * 70)
    logger.info("START: END-TO-END DATABASE PERSISTENCE TEST")
    logger.info("=" * 70)

    try:
        # ─── SETUP ────────────────────────────────────────────────────────────
        logger.info("\n[SETUP] Initializing test database...")
        engine = await setup_test_db()
        db = await create_test_session(engine)
        logger.info("✓ Test database initialized")

        # ─── CREATE TEST DATA ─────────────────────────────────────────────────
        logger.info("\n[DATA] Creating test CSV file...")
        test_file = create_test_csv()
        test_df = pd.read_csv(test_file)
        logger.info(f"✓ Test CSV created with {len(test_df)} rows")

        # ─── NLP PROCESSING ───────────────────────────────────────────────────
        logger.info("\n[NLP] Processing feedback through NLP pipeline...")
        nlp_pipeline = NLPPipeline(min_df=1, max_df=0.95)  # Adjusted for test data
        nlp_result = nlp_pipeline.process_feedback(test_df)

        if 'error' in nlp_result:
            logger.error(f"✗ NLP processing failed: {nlp_result['error']}")
            return False

        processed_data = nlp_result.get('processed_data')
        logger.info(f"✓ NLP processing complete")
        logger.info(f"  - Valid reports: {nlp_result['valid_reports']}")
        logger.info(f"  - Removed noise: {nlp_result['removed_noise']}")
        logger.info(f"  - Clusters created: {len(nlp_result['clustering_results']['cluster_names'])}")

        # ─── DATABASE PERSISTENCE ─────────────────────────────────────────────
        logger.info("\n[DATABASE] Starting persistence flow...")

        # Create upload session
        logger.info("  Creating upload session...")
        session_record = await DatabaseService.create_upload_session(
            db=db,
            filename=test_file,
            total_rows=len(processed_data),
            user_id=None
        )
        session_id = session_record.id
        logger.info(f"  ✓ Session created: ID={session_id}")

        # Save complaints and predictions
        logger.info("  Saving complaints and predictions...")
        complaints_saved, predictions_saved = await DatabaseService.save_complaints_and_predictions(
            db=db,
            processed_data=processed_data,
            session_id=session_id,
            clustering_results=nlp_result.get('clustering_results', {})
        )
        logger.info(f"  ✓ Complaints saved: {complaints_saved}")
        logger.info(f"  ✓ Predictions saved: {predictions_saved}")

        # Update session status
        await DatabaseService.update_session_status(db, session_id, "completed")
        await db.commit()
        logger.info("  ✓ Database commit successful")

        # ─── VERIFICATION ────────────────────────────────────────────────────
        logger.info("\n[VERIFICATION] Verifying database records...")

        # Verify session
        stmt = select(UploadSession).where(UploadSession.id == session_id)
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()

        if session:
            logger.info(f"  ✓ Session found: {session.filename}")
            logger.info(f"    - Status: {session.processing_status}")
            logger.info(f"    - Total rows: {session.total_rows}")
            logger.info(f"    - Uploaded at: {session.uploaded_at}")
        else:
            logger.error("  ✗ Session not found!")
            return False

        # Verify complaints
        complaint_stmt = select(Complaint).where(Complaint.session_id == session_id)
        complaint_result = await db.execute(complaint_stmt)
        complaints = complaint_result.scalars().all()

        logger.info(f"  ✓ Complaints in DB: {len(complaints)}")
        if complaints:
            logger.info(f"    - First complaint ID: {complaints[0].id}")
            logger.info(f"    - First complaint text (raw): {complaints[0].raw_text[:50]}...")
            logger.info(f"    - First complaint processed: {complaints[0].processed_text[:50]}...")

        # Verify predictions
        prediction_stmt = select(Prediction)
        prediction_result = await db.execute(prediction_stmt)
        predictions = prediction_result.scalars().all()

        logger.info(f"  ✓ Predictions in DB: {len(predictions)}")
        if predictions:
            logger.info(f"    - First prediction ID: {predictions[0].id}")
            logger.info(f"    - Cluster: {predictions[0].cluster_label}")
            logger.info(f"    - Confidence: {predictions[0].confidence_score}")
            logger.info(f"    - Sentiment: {predictions[0].sentiment}")

        # Verify relationships
        logger.info("\n[RELATIONSHIPS] Verifying foreign key relationships...")
        relationships_ok = True

        for complaint in complaints[:3]:
            prediction_stmt = select(Prediction).where(Prediction.complaint_id == complaint.id)
            pred_result = await db.execute(prediction_stmt)
            pred = pred_result.scalar_one_or_none()

            if pred:
                logger.info(f"  ✓ Complaint {complaint.id} → Prediction {pred.id}")
            else:
                logger.warning(f"  ⚠ Complaint {complaint.id} has no prediction")
                relationships_ok = False

        # ─── SUMMARY ──────────────────────────────────────────────────────────
        logger.info("\n" + "=" * 70)
        logger.info("TEST RESULTS SUMMARY")
        logger.info("=" * 70)

        all_passed = (
            session is not None and
            len(complaints) == complaints_saved and
            len(predictions) == predictions_saved and
            relationships_ok
        )

        if all_passed:
            logger.info("✓ ALL TESTS PASSED!")
            logger.info(f"\nDatabase Records Created:")
            logger.info(f"  • Upload Session: 1")
            logger.info(f"  • Complaints: {len(complaints)}")
            logger.info(f"  • Predictions: {len(predictions)}")
            logger.info(f"  • Verified Relationships: {len(predictions)}")
        else:
            logger.error("✗ SOME TESTS FAILED!")
            if session is None:
                logger.error("  - Session record not found")
            if len(complaints) != complaints_saved:
                logger.error(f"  - Complaint count mismatch: expected {complaints_saved}, got {len(complaints)}")
            if len(predictions) != predictions_saved:
                logger.error(f"  - Prediction count mismatch: expected {predictions_saved}, got {len(predictions)}")
            if not relationships_ok:
                logger.error("  - Some relationships are broken")

        logger.info("=" * 70)

        # Cleanup
        os.remove(test_file)
        await engine.dispose()

        return all_passed

    except Exception as e:
        logger.error(f"\n✗ TEST FAILED WITH EXCEPTION: {str(e)}", exc_info=True)
        return False


if __name__ == "__main__":
    success = asyncio.run(run_end_to_end_test())
    sys.exit(0 if success else 1)
