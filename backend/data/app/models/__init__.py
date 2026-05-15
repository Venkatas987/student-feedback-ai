"""
SQLAlchemy models package.
Imports all models to ensure their metadata is registered with Base.
"""

from app.models.user import User
from app.models.complaint import Complaint
from app.models.prediction import Prediction
from app.models.session import UploadSession

__all__ = ["User", "Complaint", "Prediction", "UploadSession"]
