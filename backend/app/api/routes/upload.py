# app/api/routes/upload.py
# Handles file uploads for student feedback data.
# Supports both raw datasets (Reports column) and pre-clustered semantic datasets
# (text / cluster / cluster_name / cluster_confidence columns).

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
import os
import pandas as pd
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db, AsyncSessionLocal
from app.services.semantic_nlp_pipeline import SemanticNLPPipeline
from app.services.database_service import DatabaseService
from app.utils.text_labels import strip_leading_decorative_prefix
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize semantic NLP service (singleton, model loaded once at startup)
nlp_service = SemanticNLPPipeline()

# In-memory progress tracker for real-time polling
# Format: { session_id: {"status": "preprocessing", "progress": 10, "error": null, "result": null} }
upload_progress = {}

# ─── SCHEMA CONSTANTS ─────────────────────────────────────────────────────────
# Primary text column candidates (in priority order)
TEXT_COLUMN_CANDIDATES = [
    'Reports', 'report', 'text', 'raw_feedback_text', 'feedback', 'complaint', 'description',
    'review', 'reviews', 'comment', 'comments', 'message', 'remarks', 'response',
    'student_feedback', 'issue', 'content'
]

# Columns that indicate legacy pre-clustered CSVs
SEMANTIC_INDICATOR_LEGACY = {'cluster', 'cluster_name', 'cluster_confidence'}
# Phase-2 batch pipeline exports (SentenceTransformer + UMAP + HDBSCAN + VADER)
SEMANTIC_INDICATOR_PHASE2 = {'sem_cluster', 'sem_confidence'}

# Optional extra columns carried from pre-clustered / phase-2 datasets
OPTIONAL_SEMANTIC_COLUMNS = [
    'processed_text', 'cluster_name', 'cluster_confidence', 'sentiment',
    'sentiment_score', 'umap_x', 'umap_y',
]


def _detect_text_column(data: pd.DataFrame) -> str | None:
    """Return the best matching text column using semantic aliases and length heuristics."""
    columns = list(data.columns)
    possible_cols = []
    
    # 1. Find all candidate matches using case-insensitive semantic aliases
    for candidate in TEXT_COLUMN_CANDIDATES:
        if candidate in columns and candidate not in possible_cols:
            possible_cols.append(candidate)
        else:
            for col in columns:
                if col.strip().lower() == candidate.lower() and col not in possible_cols:
                    possible_cols.append(col)
                    
    # 2. Select from matches
    if len(possible_cols) == 1:
        logger.info(f"[SCHEMA] Detected NLP text column: {possible_cols[0]}")
        return possible_cols[0]
        
    if len(possible_cols) > 1:
        best_col = None
        max_avg_len = -1
        for col in possible_cols:
            sample = data[col].dropna().head(1000).astype(str)
            avg_len = sample.str.len().mean() if len(sample) > 0 else 0
            if avg_len > max_avg_len:
                max_avg_len = avg_len
                best_col = col
        
        logger.info(f"[SCHEMA] Multiple candidates found: {possible_cols}. Selected '{best_col}' via highest average text length ({max_avg_len:.1f}).")
        return best_col

    # 3. Fallback heuristic: Longest average text length among all non-numeric columns
    logger.info("[SCHEMA] No standard NLP column found. Applying semantic heuristic fallback.")
    best_col = None
    max_avg_len = 0
    
    for col in columns:
        if pd.api.types.is_numeric_dtype(data[col]) or pd.api.types.is_bool_dtype(data[col]) or pd.api.types.is_datetime64_any_dtype(data[col]):
            continue
            
        sample = data[col].dropna().head(1000).astype(str)
        if len(sample) == 0:
            continue
            
        avg_len = sample.str.len().mean()
        if avg_len > max_avg_len:
            max_avg_len = avg_len
            best_col = col
            
    if best_col and max_avg_len > 5:
        logger.info(f"[SCHEMA] Detected NLP text column via longest average text length ({max_avg_len:.1f} chars): {best_col}")
        return best_col
        
    return None


def _detect_schema(data: pd.DataFrame) -> dict:
    """
    Inspect DataFrame columns and return schema detection metadata.

    Returns:
        {
            schema_type: 'semantic_clustered_dataset' | 'raw_feedback_dataset',
            text_column: str,
            semantic_columns_found: list[str],
            clustering_detected: bool,
        }
    """
    actual_columns = set(data.columns)
    text_col = _detect_text_column(data)

    legacy_found = [c for c in SEMANTIC_INDICATOR_LEGACY if c in actual_columns]
    phase2_found = [c for c in SEMANTIC_INDICATOR_PHASE2 if c in actual_columns]
    semantic_cols_found = sorted(set(legacy_found + phase2_found))

    clustering_detected = (
        'cluster' in actual_columns
        or 'sem_cluster' in actual_columns
    )

    if clustering_detected and text_col is not None:
        if phase2_found:
            schema_type = 'phase2_semantic_dataset'
        else:
            schema_type = 'semantic_clustered_dataset'
    else:
        schema_type = 'raw_feedback_dataset'

    return {
        'schema_type': schema_type,
        'text_column': text_col,
        'semantic_columns_found': semantic_cols_found,
        'clustering_detected': clustering_detected,
        'phase2_columns_found': phase2_found,
    }


def _normalize_dataframe(data: pd.DataFrame, text_column: str) -> pd.DataFrame:
    """
    Normalize dataframe so downstream code always works with 'Reports' as the
    primary text column. Maps Phase-2 column names (sem_*) to internal names.
    """
    normalized = pd.DataFrame()
    normalized['Reports'] = data[text_column].astype(str)

    for col in OPTIONAL_SEMANTIC_COLUMNS:
        if col in data.columns and col not in ('cluster_name', 'cluster_confidence'):
            normalized[col] = data[col]

    # ── Cluster id (Phase 2 uses sem_cluster) ───────────────────────────────
    if 'sem_cluster' in data.columns:
        normalized['cluster'] = data['sem_cluster']
    elif 'cluster' in data.columns:
        normalized['cluster'] = data['cluster']

    # ── Membership confidence (Phase 2: sem_confidence = HDBSCAN probability) ─
    if 'sem_confidence' in data.columns:
        normalized['cluster_confidence'] = data['sem_confidence']
    elif 'cluster_confidence' in data.columns:
        normalized['cluster_confidence'] = data['cluster_confidence']

    # ── Human-readable theme (prefer rich Phase-2 name) ─────────────────────
    label_series = None
    if 'sem_cluster_name' in data.columns:
        label_series = data['sem_cluster_name']
    elif 'cluster_label' in data.columns:
        label_series = data['cluster_label']
    elif 'cluster_name' in data.columns:
        label_series = data['cluster_name']

    if label_series is not None:
        normalized['cluster_label'] = label_series.map(
            lambda v: strip_leading_decorative_prefix(v) if pd.notna(v) else ""
        )

    return normalized


@router.get("/status/{session_id}")
async def get_upload_status(session_id: int):
    """
    Real-time progress polling endpoint.

    Priority:
    1. In-memory progress dict (active pipeline)
    2. DB session row (after server restart / reload)
    3. 'unknown' fallback (session never existed)
    """
    if session_id in upload_progress:
        return upload_progress[session_id]

    # Server may have restarted — check DB for authoritative status
    try:
        from sqlalchemy.future import select as _sel
        from app.models.session import UploadSession as _US
        async with AsyncSessionLocal() as _db:
            row = (await _db.execute(_sel(_US).where(_US.id == session_id))).scalars().first()
        if row is not None:
            db_status = row.processing_status  # 'completed' | 'failed' | 'processing'
            if db_status == "completed":
                return {"status": "complete", "progress": 100, "error": None, "result": {
                    "message": "Processing was completed (recovered from server restart).",
                    "session_id": session_id,
                    "filename": row.filename,
                    "data_summary": {"total_rows": row.total_rows, "processed_rows": row.total_rows, "removed_rows": 0},
                    "persistence_summary": {"complaints_saved": row.total_rows, "predictions_saved": row.total_rows},
                }}
            if db_status == "failed":
                return {"status": "error", "progress": 0, "error": "Processing failed (check server logs for details).", "result": None}
            # Still 'processing' in DB — server restart wiped our progress dict
            return {"status": "unknown", "progress": 0, "error": None, "result": None}
    except Exception as _e:
        logger.warning(f"[STATUS] DB fallback failed for session {session_id}: {_e}")

    return {"status": "unknown", "progress": 0, "error": None, "result": None}

async def _process_upload_background(
    session_id: int, 
    file_path: str, 
    safe_name: str, 
    data: pd.DataFrame, 
    schema_info: dict,
    text_column: str,
    total_raw_rows: int
):
    """Background task for executing the heavy ML pipeline without blocking the client."""
    try:
        upload_progress[session_id] = {"status": "preprocessing", "progress": 10, "error": None, "result": None}
        
        # ─── NORMALIZE DATAFRAME ──────────────────────────────────────────────
        feedback_data = _normalize_dataframe(data, text_column)

        # Drop rows where text is null, empty, or only whitespace
        feedback_data = feedback_data[
            feedback_data['Reports'].str.strip().str.len() > 0
        ].copy()
        feedback_data = feedback_data[
            feedback_data['Reports'].str.lower() != 'nan'
        ].copy()

        if feedback_data.empty:
            raise Exception("All text rows are null or empty after cleaning.")

        processed_row_count = len(feedback_data)
        removed_row_count = total_raw_rows - processed_row_count
        
        clustering_detected = schema_info['clustering_detected']
        reduced_embeddings = None

        if clustering_detected:
            upload_progress[session_id] = {"status": "insights", "progress": 80, "error": None, "result": None}
            nlp_result, clustering_results = _build_result_from_semantic_dataset(
                feedback_data, schema_info
            )
        else:
            # We run the pipeline synchronously in this thread, but we can pass a progress callback
            def _progress_cb(stage: str):
                stages = {
                    "embeddings": 25,
                    "umap": 45,
                    "clustering": 65,
                    "sentiment": 80,
                }
                if stage in stages:
                    upload_progress[session_id] = {"status": stage, "progress": stages[stage], "error": None, "result": None}

            nlp_result = nlp_service.process_feedback(feedback_data, progress_callback=_progress_cb)

            if 'error' in nlp_result:
                raise Exception(nlp_result['error'])

            clustering_results = nlp_result.get('clustering_results', {})
            feedback_data = nlp_result.get('processed_data', feedback_data)
            reduced_embeddings = nlp_result.get('reduced_embeddings', None)

        upload_progress[session_id] = {"status": "database", "progress": 90, "error": None, "result": None}

        # ─── DATABASE PERSISTENCE ──────────────────────────────────────────────
        async with AsyncSessionLocal() as db_session:
            # Update session row count
            from sqlalchemy.future import select
            from app.models.session import UploadSession
            from sqlalchemy import update
            
            await db_session.execute(
                update(UploadSession).where(UploadSession.id == session_id).values(total_rows=processed_row_count)
            )
            
            complaints_saved, predictions_saved = await DatabaseService.save_complaints_and_predictions(
                db=db_session,
                processed_data=feedback_data,
                session_id=session_id,
                clustering_results=clustering_results,
                reduced_embeddings=reduced_embeddings,
            )
            
            await DatabaseService.update_session_status(db_session, session_id, "completed")
            await db_session.commit()

        # ─── PRECOMPUTE ML ANALYTICS (fresh session) ──────────────────────
        # Use a SEPARATE session after the persistence session has been closed.
        # This guarantees we read committed data and avoids any expired-state issues.
        from app.api.routes.analytics import get_dashboard_summary, clustering_metrics, cluster_sentiment_heatmap
        from app.api.routes.clusters import get_clusters
        from app.services.cache_service import CacheService

        # Wipe any stale cache that may have been written from a previous run
        # (e.g. an aborted session that wrote zeros before the data was committed).
        CacheService.invalidate_all()
        logger.info("[PRECOMPUTE] Stale cache cleared. Starting analytics precompute...")

        upload_progress[session_id] = {"status": "analytics_ready", "progress": 95, "error": None, "result": None}

        async with AsyncSessionLocal() as precompute_session:
            # Each call is isolated — a failure in one must NOT prevent others.
            try:
                summary = await get_dashboard_summary(precompute_session)
                CacheService.set("summary", summary.model_dump() if hasattr(summary, "model_dump") else summary)
                logger.info("[PRECOMPUTE] summary cached.")
            except Exception as _e:
                logger.error(f"Precompute failed – summary: {_e}")

            try:
                metrics = await clustering_metrics(precompute_session)
                CacheService.set("clustering_metrics", metrics)
                logger.info("[PRECOMPUTE] clustering_metrics cached.")
            except Exception as _e:
                logger.error(f"Precompute failed – clustering_metrics: {_e}")

            try:
                heatmap = await cluster_sentiment_heatmap(precompute_session)
                CacheService.set("cluster_sentiment_heatmap", heatmap)
                logger.info("[PRECOMPUTE] cluster_sentiment_heatmap cached.")
            except Exception as _e:
                logger.error(f"Precompute failed – cluster_sentiment_heatmap: {_e}")

            try:
                clusters_list = await get_clusters(precompute_session)
                CacheService.set("clusters", clusters_list)
                logger.info("[PRECOMPUTE] clusters cached.")
            except Exception as _e:
                logger.error(f"Precompute failed – clusters: {_e}")

        logger.info("[PRECOMPUTE] All analytics precomputed and cached.")

        response_preview = {k: v for k, v in nlp_result.items() if k != 'processed_data'}
        
        result_data = {
            "status": "success",
            "message": "File processed successfully.",
            "filename": safe_name,
            "session_id": session_id,
            "schema_detected": schema_info['schema_type'],
            "data_summary": {
                "total_rows": total_raw_rows,
                "processed_rows": processed_row_count,
                "removed_rows": removed_row_count,
            },
            "persistence_summary": {
                "complaints_saved": complaints_saved,
                "predictions_saved": predictions_saved,
            },
            "nlp_preview": response_preview
        }
        
        upload_progress[session_id] = {"status": "complete", "progress": 100, "error": None, "result": result_data}

    except Exception as e:
        logger.error(f"[BACKGROUND] Error processing session {session_id}: {str(e)}", exc_info=True)
        upload_progress[session_id] = {"status": "error", "progress": 0, "error": str(e), "result": None}
        try:
            async with AsyncSessionLocal() as db_session:
                await DatabaseService.update_session_status(db_session, session_id, "failed")
                await db_session.commit()
        except:
            pass

@router.post("/upload-csv")
async def upload_csv(background_tasks: BackgroundTasks, file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    """
    Upload a CSV file containing student feedback data.

    Supports:
    1. Raw feedback CSV → `Reports` / `text` / `raw_feedback_text` → live pipeline
       (SentenceTransformer + UMAP + HDBSCAN + VADER).
    2. Legacy pre-clustered CSV → `cluster`, optional `cluster_name` / `cluster_confidence`.
    3. Phase 2 production CSV → `sem_cluster`, `sem_confidence`, optional `sem_cluster_name`,
       `sentiment`, `sentiment_score`, `umap_x`, `umap_y` (reuses your batch outputs; no re-clustering).

    Flow (raw):    Upload → Normalize → Semantic pipeline → DB
    Flow (reuse):  Upload → Normalize → Persist precomputed clusters & VADER fields
    """
    session_id = None
    file_path = None

    try:
        safe_name = os.path.basename(file.filename or "")
        logger.info("=" * 70)
        logger.info(f"[UPLOAD] Started: {safe_name}")
        logger.info("=" * 70)

        # ─── FILE TYPE VALIDATION ─────────────────────────────────────────────
        if not safe_name.lower().endswith(".csv"):
            raise HTTPException(
                status_code=400,
                detail="Only UTF-8 CSV uploads are supported for this endpoint.",
            )

        # ─── DUPLICATE UPLOAD DETECTION ──────────────────────────────────────
        from sqlalchemy.future import select as sa_select
        from app.models.session import UploadSession as UpSession
        existing_q = await db.execute(
            sa_select(UpSession)
            .where(UpSession.filename == safe_name)
            .where(UpSession.processing_status == "completed")
            .order_by(UpSession.uploaded_at.desc())
        )
        existing_session = existing_q.scalars().first()
        if existing_session is not None:
            logger.warning(f"[UPLOAD] Duplicate detected: '{safe_name}' already ingested (session {existing_session.id})")
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Dataset '{safe_name}' has already been uploaded and processed "
                    f"(session_id={existing_session.id}). "
                    f"To re-ingest, rename the file or delete the existing session first."
                )
            )

        file_content = await file.read()
        if len(file_content) == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        if len(file_content) > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Max {settings.MAX_FILE_SIZE // (1024 * 1024)}MB."
            )

        logger.info(f"[UPLOAD] File size: {len(file_content) / (1024 * 1024):.2f} MB")

        # ─── SAVE FILE ────────────────────────────────────────────────────────
        file_path = os.path.join(settings.UPLOAD_DIR, safe_name)
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

        with open(file_path, "wb") as f:
            f.write(file_content)

        logger.info(f"[UPLOAD] File saved: {file_path}")

        # ─── READ CSV ─────────────────────────────────────────────────────────
        try:
            data = pd.read_csv(file_path)
        except Exception as parse_err:
            raise HTTPException(
                status_code=400,
                detail=f"Malformed CSV file. Could not parse: {str(parse_err)}"
            )

        if data.empty:
            raise HTTPException(status_code=400, detail="The uploaded CSV contains no rows.")

        logger.info(f"[UPLOAD] Rows loaded: {len(data)}, Columns: {list(data.columns)}")

        # ─── SCHEMA DETECTION ─────────────────────────────────────────────────
        schema_info = _detect_schema(data)
        schema_type = schema_info['schema_type']
        text_column = schema_info['text_column']
        semantic_cols_found = schema_info['semantic_columns_found']
        clustering_detected = schema_info['clustering_detected']

        logger.info(f"[SCHEMA] Detected: {schema_type}")
        logger.info(f"[SCHEMA] Text column selected: {text_column}")
        logger.info(f"[SCHEMA] Semantic columns found: {semantic_cols_found}")
        logger.info(f"[SCHEMA] Clustering pre-computed: {clustering_detected}")

        if text_column is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"No recognizable text column found. "
                    f"Expected one of {TEXT_COLUMN_CANDIDATES}. "
                    f"Found: {list(data.columns)}"
                )
            )

        # ─── CREATE DB SESSION & TRIGGER BACKGROUND TASK ──────────────────────
        logger.info("[DB] Creating upload session...")
        
        session_record = await DatabaseService.create_upload_session(
            db=db,
            filename=safe_name,
            total_rows=len(data), # Will be updated to processed count later
            user_id=None
        )
        session_id = session_record.id
        await db.commit()

        # Initialize progress tracking
        upload_progress[session_id] = {"status": "upload", "progress": 5, "error": None, "result": None}

        background_tasks.add_task(
            _process_upload_background,
            session_id,
            file_path,
            safe_name,
            data,
            schema_info,
            text_column,
            len(data)
        )

        return JSONResponse(status_code=202, content={
            "status": "processing",
            "message": f"Upload accepted. AI pipeline started in background.",
            "session_id": session_id,
        })

    except HTTPException as he:
        logger.error(f"[UPLOAD] HTTP Exception: {he.detail}")
        await db.rollback()
        raise he

    except Exception as e:
        logger.error(f"[UPLOAD] Unexpected error: {str(e)}", exc_info=True)
        if session_id:
            try:
                await DatabaseService.update_session_status(db, session_id, "failed")
                await db.commit()
            except Exception:
                pass
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


def _build_result_from_semantic_dataset(
    data: pd.DataFrame,
    schema_info: dict
) -> tuple[dict, dict]:
    """
    Build nlp_result and clustering_results dicts by reusing pre-computed
    cluster data from a semantic clustered CSV (skips full NLP pipeline).

    Returns:
        (nlp_result dict, clustering_results dict)
    """
    import numpy as np

    clusters = data['cluster'].dropna().unique()
    cluster_names = {}
    confidence_scores = {}

    for cluster_id in clusters:
        cid = int(cluster_id)
        # Prefer cluster_label column (mapped from cluster_name during normalization)
        if 'cluster_label' in data.columns:
            labels_for_cluster = data.loc[data['cluster'] == cluster_id, 'cluster_label'].dropna()
            raw = labels_for_cluster.mode()[0] if not labels_for_cluster.empty else f"Cluster {cid}"
            name = strip_leading_decorative_prefix(str(raw)) or f"Cluster {cid}"
        else:
            name = f"Cluster {cid}"

        cluster_names[str(cid)] = name

        if 'cluster_confidence' in data.columns:
            confs = data.loc[data['cluster'] == cluster_id, 'cluster_confidence'].dropna()
            confidence_scores[str(cid)] = round(float(confs.mean()), 4) if not confs.empty else 0.8
        else:
            confidence_scores[str(cid)] = 0.8  # default confidence

    n_clusters = len([c for c in clusters if int(c) != -1])
    cluster_distribution = {
        str(int(k)): int(v)
        for k, v in data['cluster'].value_counts().to_dict().items()
    }

    clustering_results = {
        "optimal_clusters": n_clusters,
        "silhouette_score": None,  # not recomputed for pre-clustered datasets
        "outlier_count": int((data['cluster'] == -1).sum()),
        "outlier_percentage": round(float((data['cluster'] == -1).mean()) * 100, 2),
        "cluster_distribution": cluster_distribution,
        "cluster_names": cluster_names,
        "cluster_confidence_scores": confidence_scores,
        "top_keywords_per_cluster": {},  # skipped for pre-clustered datasets
        "reused_semantic_data": True,
    }

    nlp_result = {
        "total_reports": len(data),
        "valid_reports": len(data),
        "removed_noise": 0,
        "text_preview": data[['Reports']].head(5).to_dict(orient='records'),
        "embedding_stats": {
            "model": "pre-clustered (reused)",
            "dimensions": "N/A",
            "reduction_method": "pre-computed",
            "clustering_method": "pre-computed"
        },
        "clustering_results": clustering_results,
        "processed_data": data,
        "status": "Semantic Dataset Ingested (Cluster Reuse Mode)"
    }

    logger.info(f"[REUSE] Reused {n_clusters} clusters from pre-clustered dataset.")
    logger.info(f"[REUSE] Cluster names: {cluster_names}")

    return nlp_result, clustering_results