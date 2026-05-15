"""Aggregated institutional insights derived from persisted Phase 2 predictions."""

from typing import Any, List

from fastapi import APIRouter, Depends
from sqlalchemy import Float, case, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.prediction import Prediction
from app.api.routes.cluster_labels import get_normalized_cluster_distribution

router = APIRouter()


@router.get("/priorities")
async def institutional_priorities(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Rank semantic themes by volume, negative sentiment share, and confidence gaps.
    Uses only stored prediction rows (no synthetic KPIs).
    """
    total_row = await db.execute(select(func.count(Prediction.id)))
    total = int(total_row.scalar() or 0)
    if total == 0:
        return {"total_feedback": 0, "themes": []}

    neg = func.sum(case((Prediction.sentiment == "negative", 1), else_=0))
    stmt = (
        select(
            Prediction.cluster_id,
            func.max(Prediction.cluster_label).label("sample_label"),
            func.count(Prediction.id).label("count"),
            func.avg(Prediction.confidence_score).label("avg_confidence"),
            cast(neg, Float) / cast(func.count(Prediction.id), Float),
        )
        .group_by(Prediction.cluster_id)
    )
    res = await db.execute(stmt)
    rows = res.all()

    normalized = await get_normalized_cluster_distribution(db, total, include_subthemes=True)
    label_map = {c["cluster_id"]: c["cluster_label"] for c in normalized}
    sub_map = {c["cluster_id"]: c.get("subthemes", []) for c in normalized}

    themes: List[dict[str, Any]] = []
    for cluster_id, _sample_label, count, avg_conf, neg_share in rows:
        cid = cluster_id
        cnt = int(count or 0)
        avg_c = float(avg_conf or 0.0)
        ns = float(neg_share or 0.0)
        share = round(cnt / total * 100, 2) if total else 0.0
        # Heuristic priority: volume + distress signal, damped by confidence
        priority = round(cnt * (0.35 + ns) * (1.05 - min(avg_c, 0.99)), 4)
        themes.append(
            {
                "cluster_id": cid,
                "cluster_label": label_map.get(cid, _sample_label or f"Semantic cluster {cid}"),
                "count": cnt,
                "percentage_of_feedback": share,
                "avg_confidence": round(avg_c, 4),
                "negative_sentiment_share": round(ns, 4),
                "priority_score": priority,
                "subthemes": sub_map.get(cid, []),
            }
        )

    themes.sort(key=lambda t: t["priority_score"], reverse=True)
    return {"total_feedback": total, "themes": themes}
