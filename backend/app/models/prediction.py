# app/models/prediction.py
from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"), unique=True, index=True)
    cluster_id = Column(Integer, nullable=False, index=True)
    cluster_label = Column(String, nullable=False, index=True)
    confidence_score = Column(Float, default=0.0)
    sentiment = Column(String, default="neutral", index=True)
    # Phase 2 semantic exports (VADER compound, UMAP layout from batch pipeline)
    sentiment_score = Column(Float, nullable=True)
    umap_x = Column(Float, nullable=True)
    umap_y = Column(Float, nullable=True)

    complaint = relationship("Complaint", back_populates="prediction")
