from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from datetime import datetime

class ComplaintBase(BaseModel):
    raw_text: str

class ComplaintCreate(ComplaintBase):
    session_id: Optional[int] = None

class Complaint(ComplaintBase):
    id: int
    processed_text: Optional[str] = None
    session_id: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class PredictionBase(BaseModel):
    cluster_id: int
    cluster_label: str
    confidence_score: Optional[float] = None
    sentiment: Optional[str] = "neutral"
    sentiment_score: Optional[float] = None
    umap_x: Optional[float] = None
    umap_y: Optional[float] = None

class ComplaintWithPrediction(Complaint):
    prediction: Optional[PredictionBase] = None
