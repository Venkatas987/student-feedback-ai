import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from sqlalchemy import func
from app.models.complaint import Complaint
from app.models.session import UploadSession
from app.models.prediction import Prediction
import os

async def check_summary():
    SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./student_feedback.db"
    engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # Total counts
        total_complaints = await db.execute(select(func.count(Complaint.id)))
        total_sessions = await db.execute(select(func.count(UploadSession.id)))
        
        tc = total_complaints.scalar()
        ts = total_sessions.scalar()
        
        print(f"Total Complaints: {tc}")
        print(f"Total Sessions: {ts}")
        
        # Cluster distribution
        cluster_query = select(
            Prediction.cluster_id, 
            Prediction.cluster_label, 
            func.count(Prediction.id).label("count")
        ).group_by(Prediction.cluster_id, Prediction.cluster_label)
        
        cluster_results = await db.execute(cluster_query)
        clusters = cluster_results.all()
        print(f"Clusters: {clusters}")

if __name__ == "__main__":
    asyncio.run(check_summary())
