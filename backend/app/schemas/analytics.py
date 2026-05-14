from typing import List, Dict, Any
from pydantic import BaseModel, Field

class ClusterDistribution(BaseModel):
    cluster_id: int
    cluster_label: str
    count: int
    percentage: float
    subthemes: List[str] = Field(default_factory=list)
    risk_score: float = 0.0
    cluster_confidence: float = 0.0

class SentimentDistribution(BaseModel):
    label: str
    count: int
    percentage: float

class DashboardSummary(BaseModel):
    total_complaints: int
    total_sessions: int
    mean_confidence: float
    cluster_distribution: List[ClusterDistribution]
    sentiment_distribution: List[SentimentDistribution]
    # Add more fields as needed for the dashboard
