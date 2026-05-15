from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.models.complaint import Complaint
from app.models.prediction import Prediction
from app.schemas.complaint import ComplaintWithPrediction
from app.api.routes.cluster_labels import get_normalized_cluster_label_map

from sqlalchemy.orm import joinedload

router = APIRouter()


def serialize_complaint_with_prediction(
    complaint: Complaint,
    cluster_labels: dict[int | None, str],
) -> dict:
    prediction = complaint.prediction

    return {
        "id": complaint.id,
        "raw_text": complaint.raw_text,
        "processed_text": complaint.processed_text,
        "session_id": complaint.session_id,
        "created_at": complaint.created_at,
        "prediction": None if prediction is None else {
            "cluster_id": prediction.cluster_id,
            "cluster_label": cluster_labels.get(
                prediction.cluster_id,
                prediction.cluster_label,
            ),
            "confidence_score": prediction.confidence_score,
            "sentiment": prediction.sentiment,
            "sentiment_score": prediction.sentiment_score,
            "umap_x": prediction.umap_x,
            "umap_y": prediction.umap_y,
        },
    }

@router.get("/", response_model=List[ComplaintWithPrediction])
async def get_complaints(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    cluster_id: Optional[int] = None
):
    query = select(Complaint).options(joinedload(Complaint.prediction)).join(Prediction, isouter=True)
    
    if cluster_id is not None:
        query = query.where(Prediction.cluster_id == cluster_id)
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    complaints = result.scalars().all()
    cluster_labels = await get_normalized_cluster_label_map(db)
    
    return [
        serialize_complaint_with_prediction(complaint, cluster_labels)
        for complaint in complaints
    ]

@router.get("/{complaint_id}", response_model=ComplaintWithPrediction)
async def get_complaint(
    complaint_id: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Complaint)
        .options(joinedload(Complaint.prediction))
        .where(Complaint.id == complaint_id)
    )
    complaint = result.unique().scalar_one_or_none()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    cluster_labels = await get_normalized_cluster_label_map(db)
    return serialize_complaint_with_prediction(complaint, cluster_labels)
