#!/usr/bin/env python3
"""
End-to-end test for semantic clustering pipeline.
Tests semantic embeddings, UMAP reduction, HDBSCAN clustering, and database persistence.
"""

import asyncio
import sys
import os
import pandas as pd
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
from app.core.database import Base
from app.models.session import UploadSession
from app.models.complaint import Complaint
from app.models.prediction import Prediction
from app.services.semantic_nlp_pipeline import SemanticNLPPipeline
from app.services.database_service import DatabaseService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TEST_DB_URL = "sqlite+aiosqlite:///./test_semantic_feedback.db"


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


def create_semantic_test_csv():
    """Create test CSV with diverse feedback for semantic analysis."""
    test_data = {
        'Reports': [
            # Network connectivity issues
            "The WiFi network is extremely slow and keeps disconnecting during my online classes.",
            "Internet connection keeps dropping. Need stable network for virtual meetings.",
            "Network connectivity is poor. Can barely stream video or download files.",
            "WiFi signal is very weak in the dormitory. Need better coverage.",
            "Internet speed is inadequate for remote learning. Experiencing constant lag.",
            "Network keeps disconnecting. Very frustrating during presentations.",
            "WiFi is unreliable. Please upgrade network infrastructure.",
            "Poor internet speed affecting my online classes. Needs urgent fix.",

            # Password and access issues
            "Cannot reset my password. Account is locked. Need urgent help.",
            "Password reset link is not working. Cannot access my account.",
            "Account locked after wrong password attempts. Need manual unlock.",
            "Having trouble with multi-factor authentication. Cannot login.",
            "Access to student portal is denied. Password change not working.",
            "Account verification process is broken. Cannot complete login.",

            # Hardware requests
            "Need new laptop for my coursework. Current one is too old.",
            "Requesting hardware: monitor and keyboard for my workstation.",
            "Can I get a new printer assigned to my lab? Current one is broken.",
            "Need to upgrade my computer. Can I get approval for new hardware?",
            "Requesting budget approval to purchase new computing equipment.",

            # Email and system issues
            "Email server is down. Cannot access any emails.",
            "Email system not working. Urgent messages not being received.",
            "Mail server is having issues. Needs immediate attention.",
            "Cannot send emails from university account. System error.",

            # Positive feedback
            "Great job on the recent system upgrade! Everything works smoothly now.",
            "Excellent support from IT team. Problem resolved quickly.",
            "The new software update improved productivity significantly.",
            "Amazing experience with technical support. Very helpful!",
            "Thank you for upgrading the WiFi. Internet is much faster now.",
        ]
    }

    df = pd.DataFrame(test_data)
    test_file = "test_semantic_feedback.csv"
    df.to_csv(test_file, index=False)
    logger.info(f"Created semantic test CSV: {test_file} with {len(df)} rows")
    return test_file


async def run_semantic_test():
    """Run complete semantic clustering test."""
    logger.info("=" * 80)
    logger.info("SEMANTIC CLUSTERING END-TO-END TEST")
    logger.info("=" * 80)

    try:
        # ─── SETUP ────────────────────────────────────────────────────────────
        logger.info("\n[SETUP] Initializing test environment...")
        engine = await setup_test_db()
        db = await create_test_session(engine)
        logger.info("✓ Test database initialized")

        # ─── TEST DATA ────────────────────────────────────────────────────────
        logger.info("\n[DATA] Creating semantic test dataset...")
        test_file = create_semantic_test_csv()
        test_df = pd.read_csv(test_file)
        logger.info(f"✓ Test CSV created with {len(test_df)} diverse feedback samples")

        # ─── SEMANTIC NLP PIPELINE ────────────────────────────────────────────
        logger.info("\n[SEMANTIC NLP] Starting semantic clustering pipeline...")
        logger.info("-" * 80)

        nlp_pipeline = SemanticNLPPipeline()
        nlp_result = nlp_pipeline.process_feedback(test_df)

        if 'error' in nlp_result:
            logger.error(f"✗ NLP processing failed: {nlp_result['error']}")
            return False

        processed_data = nlp_result.get('processed_data')
        clustering_results = nlp_result.get('clustering_results', {})

        logger.info("-" * 80)
        logger.info("✓ Semantic NLP pipeline complete")

        # ─── SEMANTIC CLUSTERING ANALYSIS ─────────────────────────────────
        logger.info("\n[CLUSTERING ANALYSIS]")
        logger.info(f"  • Embedding Model: {nlp_result['embedding_stats']['model']}")
        logger.info(f"  • Embedding Dimensions: {nlp_result['embedding_stats']['dimensions']}")
        logger.info(f"  • Reduction Method: {nlp_result['embedding_stats']['reduction_method']}")
        logger.info(f"  • Clustering Method: {nlp_result['embedding_stats']['clustering_method']}")
        logger.info(f"  • Valid Reports: {nlp_result['valid_reports']}")
        logger.info(f"  • Clusters Created: {clustering_results.get('optimal_clusters', 0)}")
        logger.info(f"  • Silhouette Score: {clustering_results.get('silhouette_score', 'N/A')}")
        logger.info(f"  • Outliers: {clustering_results.get('outlier_count', 0)} ({clustering_results.get('outlier_percentage', 0)}%)")

        # ─── CLUSTER DETAILS ──────────────────────────────────────────────
        logger.info("\n[CLUSTER DETAILS]")
        cluster_names = clustering_results.get('cluster_names', {})
        cluster_dist = clustering_results.get('cluster_distribution', {})
        keywords = clustering_results.get('top_keywords_per_cluster', {})
        confidence = clustering_results.get('cluster_confidence_scores', {})

        for cluster_id in sorted([int(k) for k in cluster_names.keys()]):
            cluster_id_str = str(cluster_id)
            logger.info(f"\n  Cluster {cluster_id}: {cluster_names.get(cluster_id_str, 'Unknown')}")
            logger.info(f"    • Size: {cluster_dist.get(cluster_id_str, 0)} reports")
            logger.info(f"    • Confidence: {confidence.get(cluster_id_str, 0.0)}")
            logger.info(f"    • Keywords: {', '.join(keywords.get(cluster_id_str, [])[:5])}")

        # ─── DATABASE PERSISTENCE ─────────────────────────────────────────
        logger.info("\n[DATABASE PERSISTENCE]")
        logger.info("  Creating upload session...")

        session_record = await DatabaseService.create_upload_session(
            db=db,
            filename=test_file,
            total_rows=len(processed_data),
            user_id=None
        )
        session_id = session_record.id
        logger.info(f"  ✓ Session created: ID={session_id}")

        logger.info("  Saving complaints and predictions...")

        complaints_saved, predictions_saved = await DatabaseService.save_complaints_and_predictions(
            db=db,
            processed_data=processed_data,
            session_id=session_id,
            clustering_results=clustering_results
        )

        logger.info(f"  ✓ Complaints saved: {complaints_saved}")
        logger.info(f"  ✓ Predictions saved: {predictions_saved}")

        await DatabaseService.update_session_status(db, session_id, "completed")
        await db.commit()
        logger.info("  ✓ Database commit successful")

        # ─── VERIFICATION ────────────────────────────────────────────────
        logger.info("\n[VERIFICATION]")

        # Verify session
        stmt = select(UploadSession).where(UploadSession.id == session_id)
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()

        if session:
            logger.info(f"  ✓ Session found: {session.filename}")
            logger.info(f"    Status: {session.processing_status}, Rows: {session.total_rows}")
        else:
            logger.error("  ✗ Session not found!")
            return False

        # Verify complaints and predictions
        complaint_stmt = select(Complaint).where(Complaint.session_id == session_id)
        complaint_result = await db.execute(complaint_stmt)
        complaints = complaint_result.scalars().all()

        prediction_stmt = select(Prediction)
        prediction_result = await db.execute(prediction_stmt)
        predictions = prediction_result.scalars().all()

        logger.info(f"  ✓ Complaints in DB: {len(complaints)}")
        logger.info(f"  ✓ Predictions in DB: {len(predictions)}")

        # Show sample predictions
        logger.info("\n[SAMPLE PREDICTIONS]")
        for pred in predictions[:3]:
            comp_stmt = select(Complaint).where(Complaint.id == pred.complaint_id)
            comp_result = await db.execute(comp_stmt)
            complaint = comp_result.scalar_one()

            logger.info(f"\n  Sample {pred.id}:")
            logger.info(f"    Text: {complaint.raw_text[:60]}...")
            logger.info(f"    Cluster: {pred.cluster_label}")
            logger.info(f"    Confidence: {pred.confidence_score}")
            logger.info(f"    Sentiment: {pred.sentiment}")

        # ─── FINAL SUMMARY ────────────────────────────────────────────────
        logger.info("\n" + "=" * 80)
        logger.info("SEMANTIC CLUSTERING TEST RESULTS")
        logger.info("=" * 80)

        all_passed = (
            session is not None and
            len(complaints) == complaints_saved and
            len(predictions) == predictions_saved and
            clustering_results.get('optimal_clusters', 0) > 0
        )

        if all_passed:
            logger.info("✓ ALL TESTS PASSED!")
            logger.info(f"\nSemantic Clustering Improvements:")
            logger.info(f"  • Clustering Method: HDBSCAN (density-based) vs KMeans (centroid-based)")
            logger.info(f"  • Embeddings: Semantic (SentenceTransformer) vs TF-IDF keywords")
            logger.info(f"  • Silhouette Score: {clustering_results.get('silhouette_score', 'N/A')}")
            logger.info(f"  • Clusters Discovered: {clustering_results.get('optimal_clusters', 0)}")
            logger.info(f"  • Outlier Detection: {clustering_results.get('outlier_count', 0)} points identified")
            logger.info(f"\nDatabase Records:")
            logger.info(f"  • Sessions: 1")
            logger.info(f"  • Complaints: {len(complaints)}")
            logger.info(f"  • Predictions: {len(predictions)}")
        else:
            logger.error("✗ SOME TESTS FAILED!")
            if session is None:
                logger.error("  - Session not found")
            if clustering_results.get('optimal_clusters', 0) == 0:
                logger.error("  - No clusters detected")

        logger.info("=" * 80)

        # Cleanup
        os.remove(test_file)
        await engine.dispose()

        return all_passed

    except Exception as e:
        logger.error(f"\n✗ TEST FAILED: {str(e)}", exc_info=True)
        return False


if __name__ == "__main__":
    success = asyncio.run(run_semantic_test())
    sys.exit(0 if success else 1)
