import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import Float, case, cast, func

logger = logging.getLogger(__name__)

from app.core.database import get_db
from app.models.complaint import Complaint
from app.models.prediction import Prediction
from app.models.session import UploadSession
from app.schemas.analytics import (
    ClusterDistribution,
    DashboardSummary,
    SentimentDistribution,
)
from app.api.routes.cluster_labels import get_normalized_cluster_distribution
from app.services.clustering_metrics import ClusteringMetricsService

router = APIRouter()

@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    db: AsyncSession = Depends(get_db)
):
    from app.services.cache_service import CacheService
    cached = CacheService.get("summary", ttl_seconds=300)
    if cached:
        return cached

    # Total counts
    total_complaints = await db.execute(select(func.count(Complaint.id)))
    total_sessions = await db.execute(select(func.count(UploadSession.id)))
    mean_confidence_result = await db.execute(select(func.avg(Prediction.confidence_score)))
    total_c = total_complaints.scalar()
    avg_confidence = mean_confidence_result.scalar() or 0.0
    mean_confidence = round(float(avg_confidence) * 100, 1)

    # Cluster distribution, normalized to one semantic label per cluster_id.
    normalized_clusters = await get_normalized_cluster_distribution(
        db,
        total_c,
        include_subthemes=True,
    )
    dist = [
        ClusterDistribution(
            cluster_id=cluster["cluster_id"],
            cluster_label=cluster["cluster_label"],
            count=cluster["count"],
            percentage=cluster["percentage"],
            subthemes=cluster.get("subthemes", []),
        ) for cluster in normalized_clusters
    ]

    sentiment_query = select(
        Prediction.sentiment,
        func.count(Prediction.id).label("count"),
    ).group_by(Prediction.sentiment)
    sentiment_results = await db.execute(sentiment_query)
    sentiment_counts = {
        (row.sentiment or "neutral").lower(): int(row.count or 0)
        for row in sentiment_results.all()
    }

    sentiment_distribution = [
        SentimentDistribution(
            label=label,
            count=sentiment_counts.get(label, 0),
            percentage=round((sentiment_counts.get(label, 0) / total_c * 100), 2)
            if total_c > 0
            else 0,
        )
        for label in ("negative", "neutral", "positive")
    ]
    
    # Per-cluster negative sentiment ratios (for risk scoring) — full dataset
    # Uses CASE WHEN to count negative rows without invalid func.cast(bool)
    neg_stmt = (
        select(
            Prediction.cluster_id,
            func.count(Prediction.id).label("total"),
            func.sum(
                case((Prediction.sentiment == "negative", 1), else_=0)
            ).label("neg_count"),
            func.avg(Prediction.confidence_score).label("avg_conf"),
        ).group_by(Prediction.cluster_id)
    )
    neg_result = await db.execute(neg_stmt)
    cluster_risk_map: dict = {}
    for row in neg_result.all():
        cid = row.cluster_id
        total_in_cluster = int(row.total or 1)
        neg_count = int(row.neg_count or 0)
        avg_conf = float(row.avg_conf or 0.0)
        neg_ratio = neg_count / total_in_cluster
        vol_ratio = total_in_cluster / max(total_c, 1)
        risk = round((neg_ratio * 0.4) + (vol_ratio * 0.4) + ((1 - avg_conf) * 0.2), 4)
        cluster_risk_map[cid] = {"risk_score": risk, "mean_confidence": round(avg_conf * 100, 2)}

    # Enrich cluster distribution with backend-computed risk scores
    for c in dist:
        info = cluster_risk_map.get(c.cluster_id, {})
        c.risk_score = info.get("risk_score", 0.0)
        c.cluster_confidence = info.get("mean_confidence", 0.0)

    result = DashboardSummary(
        total_complaints=total_c,
        total_sessions=total_sessions.scalar(),
        mean_confidence=mean_confidence,
        cluster_distribution=dist,
        sentiment_distribution=sentiment_distribution,
    )
    # Write to cache so subsequent requests are instant (self-healing cache).
    # Only reached on a cold-cache request — future requests return early at line 26.
    try:
        CacheService.set("summary", result.model_dump())
    except Exception as _ce:
        logger.warning(f"Cache write failed for summary: {_ce}")
    return result


@router.get("/cluster-sentiment-heatmap")
async def cluster_sentiment_heatmap(db: AsyncSession = Depends(get_db)):
    """
    Cross-tab of semantic cluster × sentiment for institutional heatmaps.
    Rows ordered by cluster_id; columns fixed: negative, neutral, positive.
    """
    from app.services.cache_service import CacheService
    cached = CacheService.get("cluster_sentiment_heatmap", ttl_seconds=300)
    if cached:
        return cached

    stmt = (
        select(
            Prediction.cluster_id,
            Prediction.sentiment,
            func.count(Prediction.id).label("cnt"),
        )
        .group_by(Prediction.cluster_id, Prediction.sentiment)
    )
    result = await db.execute(stmt)
    rows = result.all()

    label_map_rows = await get_normalized_cluster_distribution(db, include_subthemes=False)
    id_to_label = {r["cluster_id"]: r["cluster_label"] for r in label_map_rows}

    # Group by canonical label instead of cluster_id
    by_canonical_label: dict[str, dict[str, int]] = {}
    for cluster_id, sentiment, cnt in rows:
        base = id_to_label.get(cluster_id, f"Semantic cluster {cluster_id}")
        if cluster_id == -1:
            base = id_to_label.get(-1, "Unclassified institutional")
        
        canonical = str(base).strip()
        
        if canonical not in by_canonical_label:
            by_canonical_label[canonical] = {"negative": 0, "neutral": 0, "positive": 0}
        
        key = (sentiment or "neutral").lower()
        if key not in by_canonical_label[canonical]:
            key = "neutral"
        by_canonical_label[canonical][key] += int(cnt or 0)

    # Sort alphabetically with Unclassified at the end
    ordered_labels = sorted(by_canonical_label.keys(), key=lambda x: (x == "Unclassified institutional", x))
    sentiments = ["negative", "neutral", "positive"]
    matrix: list[list[int]] = []
    
    for label in ordered_labels:
        counts = by_canonical_label[label]
        matrix.append([counts["negative"], counts["neutral"], counts["positive"]])

    result_data = {
        "sentiments": sentiments,
        "cluster_ids": ordered_labels,  # Kept for API compatibility, though they are now labels
        "cluster_labels": ordered_labels,
        "matrix": matrix,
    }
    try:
        CacheService.set("cluster_sentiment_heatmap", result_data)
    except Exception as _ce:
        logger.warning(f"Cache write failed for cluster_sentiment_heatmap: {_ce}")
    return result_data

@router.get("/clustering-metrics")
async def clustering_metrics(db: AsyncSession = Depends(get_db)):
    """
    Returns mathematically rigorous clustering evaluation metrics
    based on the real UMAP topology and HDBSCAN probabilities.
    """
    from app.services.cache_service import CacheService
    cached = CacheService.get("clustering_metrics", ttl_seconds=300)
    if cached:
        return cached

    # Fetch real points from DB
    stmt = select(
        Prediction.cluster_id,
        Prediction.confidence_score,
        Prediction.umap_x,
        Prediction.umap_y
    ).where(Prediction.umap_x.is_not(None)).where(Prediction.umap_y.is_not(None))
    
    result = await db.execute(stmt)
    rows = result.all()

    points = [
        {
            "cluster_id": r.cluster_id,
            "confidence_score": r.confidence_score,
            "umap_x": r.umap_x,
            "umap_y": r.umap_y
        }
        for r in rows
    ]

    metrics = ClusteringMetricsService.calculate_metrics(points)
    try:
        CacheService.set("clustering_metrics", metrics)
    except Exception as _ce:
        logger.warning(f"Cache write failed for clustering_metrics: {_ce}")
    return metrics
