# app/models/complaint.py
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, index=True)
    raw_text = Column(Text, nullable=False)
    processed_text = Column(Text)
    session_id = Column(Integer, ForeignKey("upload_sessions.id"), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    session = relationship("UploadSession", back_populates="complaints")
    prediction = relationship("Prediction", back_populates="complaint", uselist=False)
