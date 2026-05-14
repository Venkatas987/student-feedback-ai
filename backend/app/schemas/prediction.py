from typing import List, Optional
from pydantic import BaseModel

class PredictionResult(BaseModel):
    complaint_id: int
    cluster_id: int
    cluster_label: str
    confidence_score: float
    sentiment: str = "neutral"

class BatchPredictionResponse(BaseModel):
    session_id: int
    predictions: List[PredictionResult]
    total_processed: int
