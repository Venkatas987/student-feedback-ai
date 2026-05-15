# app/services/database_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging
import numpy as np
import pandas as pd
from app.models.session import UploadSession
from app.models.complaint import Complaint
from app.models.prediction import Prediction
from app.utils.text_labels import strip_leading_decorative_prefix

logger = logging.getLogger(__name__)


class DatabaseService:
    """Service layer for database persistence operations."""

    @staticmethod
    async def create_upload_session(
        db: AsyncSession,
        filename: str,
        total_rows: int,
        user_id: int = None
    ) -> UploadSession:
        """Create and save upload session record."""
        session_record = UploadSession(
            filename=filename,
            total_rows=total_rows,
            user_id=user_id,
            processing_status="processing"
        )
        db.add(session_record)
        await db.flush()
        logger.info(f"Created upload session {session_record.id} for file: {filename}")
        return session_record

    @staticmethod
    async def save_complaints_and_predictions(
        db: AsyncSession,
        processed_data: pd.DataFrame,
        session_id: int,
        clustering_results: dict,
        reduced_embeddings: np.ndarray | None = None,
    ) -> tuple[int, int]:
        """
        Save complaint and prediction records for processed data.

        Supports two data shapes:
        - Raw pipeline output: cluster labels/confidence come from clustering_results dict.
          Pass reduced_embeddings (shape: [n, 2]) to persist real umap_x / umap_y.
        - Pre-clustered semantic dataset: cluster_label, cluster_confidence, umap_x, umap_y
          columns exist directly in the DataFrame rows and take priority.

        Args:
            db: AsyncSession
            processed_data: DataFrame with 'Reports', 'cluster', and optional
                            'cluster_label', 'cluster_confidence', 'sentiment' columns.
            session_id: ID of the upload session
            clustering_results: Clustering results dict (may be empty for reuse mode)
            reduced_embeddings: Optional (n, 2) UMAP projection from live pipeline run.
                                When provided and the DataFrame has no umap_x/umap_y columns,
                                these coordinates are written per-row using positional index.

        Returns:
            Tuple of (complaints_saved, predictions_saved)
        """
        complaints_saved = 0
        predictions_saved = 0

        # Pre-compute lookups from clustering_results for efficiency
        cluster_names_lookup = (clustering_results or {}).get('cluster_names', {})
        confidence_lookup = (
            (clustering_results or {}).get('cluster_confidence_scores')
            or (clustering_results or {}).get('cluster_confidence_diagnostics')
            or {}
        )

        # Determine which columns are available in the DataFrame
        has_row_label = 'cluster_label' in processed_data.columns
        has_row_confidence = 'cluster_confidence' in processed_data.columns
        has_row_sentiment = 'sentiment' in processed_data.columns
        has_sentiment_score = 'sentiment_score' in processed_data.columns
        has_umap_x = 'umap_x' in processed_data.columns
        has_umap_y = 'umap_y' in processed_data.columns

        # Index lookup for pipeline-produced embeddings (positional)
        use_pipeline_umap = (
            reduced_embeddings is not None
            and isinstance(reduced_embeddings, np.ndarray)
            and reduced_embeddings.ndim == 2
            and reduced_embeddings.shape[1] >= 2
            and not (has_umap_x and has_umap_y)
        )
        if use_pipeline_umap:
            logger.info(f"[DB] Persisting live UMAP coordinates from pipeline "
                        f"(shape: {reduced_embeddings.shape})")
        # Build positional index mapping: DataFrame index -> row position in processed_data
        row_positions = {idx: pos for pos, idx in enumerate(processed_data.index)}

        for idx, row in processed_data.iterrows():
            try:
                raw_text = str(row['Reports']).strip()
                if not raw_text or raw_text.lower() == 'nan':
                    logger.warning(f"Skipping row {idx}: empty text")
                    continue

                processed_text = str(row.get('processed_text', "") or "")
                cluster_id = int(row['cluster'])

                # ── Complaint ────────────────────────────────────────────────
                complaint = Complaint(
                    raw_text=raw_text,
                    processed_text=processed_text,
                    session_id=session_id
                )
                db.add(complaint)
                # DO NOT flush per row. We will flush in batches to avoid N+1 latency.
                complaints_saved += 1


                # ── Prediction ───────────────────────────────────────────────
                # 1. cluster_label: prefer row column, fall back to lookup dict
                if has_row_label:
                    raw_lbl = row['cluster_label']
                    cluster_label = (
                        strip_leading_decorative_prefix(str(raw_lbl))
                        if pd.notna(raw_lbl) and str(raw_lbl).strip()
                        else cluster_names_lookup.get(str(cluster_id), f"Cluster {cluster_id}")
                    )
                    if not cluster_label:
                        cluster_label = cluster_names_lookup.get(str(cluster_id), f"Cluster {cluster_id}")
                else:
                    cluster_label = cluster_names_lookup.get(str(cluster_id), f"Cluster {cluster_id}")

                # 2. confidence_score: prefer row column, fall back to lookup dict
                if has_row_confidence:
                    try:
                        confidence_score = float(row['cluster_confidence'])
                    except (TypeError, ValueError):
                        confidence_score = float(confidence_lookup.get(str(cluster_id), 0.0))
                elif isinstance(confidence_lookup.get(str(cluster_id)), dict):
                    # Old pipeline format: {cluster_id: {'naming_confidence_score': ...}}
                    confidence_score = confidence_lookup[str(cluster_id)].get('naming_confidence_score', 0.0)
                else:
                    confidence_score = float(confidence_lookup.get(str(cluster_id), 0.0))

                # 3. sentiment: prefer row column, fall back to heuristic
                if has_row_sentiment and pd.notna(row.get('sentiment')):
                    sentiment = DatabaseService._normalize_sentiment(str(row['sentiment']))
                else:
                    sentiment = DatabaseService._extract_sentiment(processed_text or raw_text)

                sentiment_score = None
                if has_sentiment_score and pd.notna(row.get('sentiment_score')):
                    try:
                        sentiment_score = float(row['sentiment_score'])
                    except (TypeError, ValueError):
                        sentiment_score = None

                umap_x = None
                umap_y = None
                if has_umap_x and pd.notna(row.get('umap_x')):
                    try:
                        umap_x = float(row['umap_x'])
                    except (TypeError, ValueError):
                        umap_x = None
                if has_umap_y and pd.notna(row.get('umap_y')):
                    try:
                        umap_y = float(row['umap_y'])
                    except (TypeError, ValueError):
                        umap_y = None

                # Fall back to pipeline-produced UMAP coordinates when CSV has none
                if umap_x is None and umap_y is None and use_pipeline_umap:
                    pos = row_positions.get(idx)
                    if pos is not None and pos < len(reduced_embeddings):
                        umap_x = float(reduced_embeddings[pos, 0])
                        umap_y = float(reduced_embeddings[pos, 1])

                prediction = Prediction(
                    # We will assign complaint_id after flushing complaints
                    complaint=complaint,
                    cluster_id=cluster_id,
                    cluster_label=cluster_label,
                    confidence_score=confidence_score,
                    sentiment=sentiment,
                    sentiment_score=sentiment_score,
                    umap_x=umap_x,
                    umap_y=umap_y,
                )
                db.add(prediction)
                predictions_saved += 1

                # Flush in batches of 1000
                if complaints_saved % 1000 == 0:
                    await db.flush()

            except Exception as e:
                logger.error(f"Error saving complaint/prediction for row {idx}: {str(e)}")
                raise

        # Final flush for any remaining records
        if complaints_saved % 1000 != 0:
            await db.flush()

        logger.info(f"Saved {complaints_saved} complaints and {predictions_saved} predictions")
        return complaints_saved, predictions_saved

    @staticmethod
    def _normalize_sentiment(label: str) -> str:
        s = (label or "").strip().lower()
        if s in ("positive", "pos", "compound_pos"):
            return "positive"
        if s in ("negative", "neg", "compound_neg"):
            return "negative"
        if s in ("neutral", "neu", "compound_neu"):
            return "neutral"
        return "neutral"

    @staticmethod
    def _extract_sentiment(text: str) -> str:
        """
        Extract sentiment from processed text.
        Simple heuristic-based sentiment extraction.
        """
        if not text:
            return "neutral"

        text_lower = text.lower()

        positive_keywords = {
            'good', 'great', 'excellent', 'amazing', 'wonderful',
            'fantastic', 'best', 'perfect', 'love', 'enjoy', 'grateful',
            'appreciate', 'satisfied', 'happy', 'glad'
        }

        negative_keywords = {
            'bad', 'poor', 'terrible', 'awful', 'horrible',
            'worst', 'hate', 'disappointing', 'disappointed',
            'frustrated', 'angry', 'problem', 'issue', 'broken',
            'slow', 'crash', 'fail', 'error', 'bug'
        }

        positive_count = sum(1 for word in positive_keywords if word in text_lower)
        negative_count = sum(1 for word in negative_keywords if word in text_lower)

        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"

    @staticmethod
    async def update_session_status(
        db: AsyncSession,
        session_id: int,
        status: str
    ) -> None:
        """Update upload session status."""
        stmt = select(UploadSession).where(UploadSession.id == session_id)
        result = await db.execute(stmt)
        session_record = result.scalar_one_or_none()

        if session_record:
            session_record.processing_status = status
            await db.flush()
            logger.info(f"Updated session {session_id} status to: {status}")
        else:
            logger.warning(f"Session {session_id} not found for status update")

    @staticmethod
    async def get_session_summary(
        db: AsyncSession,
        session_id: int
    ) -> dict:
        """Get summary statistics for an upload session."""
        stmt = select(UploadSession).where(UploadSession.id == session_id)
        result = await db.execute(stmt)
        session_record = result.scalar_one_or_none()

        if not session_record:
            return None

        complaint_stmt = select(Complaint).where(
            Complaint.session_id == session_id
        )
        complaints_result = await db.execute(complaint_stmt)
        complaints = complaints_result.scalars().all()

        prediction_stmt = select(Prediction).where(
            Prediction.complaint_id.in_([c.id for c in complaints])
        )
        predictions_result = await db.execute(prediction_stmt)
        predictions = predictions_result.scalars().all()

        return {
            "session_id": session_id,
            "filename": session_record.filename,
            "total_rows": session_record.total_rows,
            "complaints_count": len(complaints),
            "predictions_count": len(predictions),
            "processing_status": session_record.processing_status,
            "uploaded_at": session_record.uploaded_at.isoformat() if session_record.uploaded_at else None
        }
