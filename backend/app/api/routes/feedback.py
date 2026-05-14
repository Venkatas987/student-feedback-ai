"""Semantic feedback search and UMAP scatter helpers (Phase 2 data in DB)."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import or_, select
from sqlalchemy.orm import joinedload

from app.core.database import get_db
from app.models.complaint import Complaint
from app.models.prediction import Prediction
from app.api.routes.cluster_labels import get_normalized_cluster_label_map

router = APIRouter()


def _serialize(
    complaint: Complaint,
    cluster_labels: dict,
) -> dict:
    pred = complaint.prediction
    if pred is None:
        return {
            "id": complaint.id,
            "raw_text": complaint.raw_text,
            "processed_text": complaint.processed_text,
            "session_id": complaint.session_id,
            "created_at": complaint.created_at,
            "prediction": None,
        }
    return {
        "id": complaint.id,
        "raw_text": complaint.raw_text,
        "processed_text": complaint.processed_text,
        "session_id": complaint.session_id,
        "created_at": complaint.created_at,
        "prediction": {
            "cluster_id": pred.cluster_id,
            "cluster_label": cluster_labels.get(pred.cluster_id, pred.cluster_label),
            "confidence_score": pred.confidence_score,
            "sentiment": pred.sentiment,
            "sentiment_score": pred.sentiment_score,
            "umap_x": pred.umap_x,
            "umap_y": pred.umap_y,
        },
    }


@router.get("/search")
async def search_feedback(
    db: AsyncSession = Depends(get_db),
    q: Optional[str] = Query(None, description="Substring match on raw or processed text"),
    cluster_id: Optional[int] = Query(None),
    sentiment: Optional[str] = Query(None),
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    if sentiment is not None:
        s = sentiment.strip().lower()
        if s not in ("positive", "negative", "neutral"):
            raise HTTPException(status_code=400, detail="sentiment must be positive, negative, or neutral")
        sentiment = s
    stmt = (
        select(Complaint)
        .options(joinedload(Complaint.prediction))
        .join(Prediction, Complaint.id == Prediction.complaint_id)
    )

    if q and q.strip():
        term = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Complaint.raw_text.ilike(term),
                Complaint.processed_text.ilike(term),
            )
        )

    if cluster_id is not None:
        stmt = stmt.where(Prediction.cluster_id == cluster_id)

    if sentiment:
        stmt = stmt.where(Prediction.sentiment == sentiment.lower())

    if min_confidence is not None:
        stmt = stmt.where(Prediction.confidence_score >= min_confidence)

    stmt = stmt.order_by(Complaint.id.desc()).offset(skip).limit(limit)

    result = await db.execute(stmt)
    rows: List[Complaint] = result.unique().scalars().all()
    cluster_labels = await get_normalized_cluster_label_map(db)

    return [_serialize(c, cluster_labels) for c in rows]


@router.get("/umap")
async def umap_projection(
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(1000, ge=10, le=5000),
):
    """Return stored UMAP coordinates for scatter plots (ingested from Phase 2 CSV)."""
    from app.services.cache_service import CacheService
    cache_key = f"umap_{skip}_{limit}"
    cached = CacheService.get(cache_key, ttl_seconds=300)
    if cached:
        return cached

    stmt = (
        select(Complaint, Prediction)
        .join(Prediction, Complaint.id == Prediction.complaint_id)
        .where(Prediction.umap_x.isnot(None), Prediction.umap_y.isnot(None))
        .offset(skip)
        .limit(limit)
    )
    res = await db.execute(stmt)
    cluster_labels = await get_normalized_cluster_label_map(db)
    out = []
    for complaint, pred in res.all():
        raw = complaint.raw_text or ""
        preview = raw if len(raw) <= 360 else raw[:357].rstrip() + "…"
        out.append(
            {
                "id": complaint.id,
                "x": float(pred.umap_x),
                "y": float(pred.umap_y),
                "cluster_id": pred.cluster_id,
                "cluster_label": cluster_labels.get(pred.cluster_id, pred.cluster_label),
                "confidence": pred.confidence_score,
                "sentiment": pred.sentiment,
                "sentiment_score": pred.sentiment_score,
                "text_preview": preview,
            }
        )
    
    result_data = {"points": out, "count": len(out), "skip": skip, "limit": limit}
    CacheService.set(cache_key, result_data)
    return result_data
