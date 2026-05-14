from fastapi import APIRouter

from app.api.routes import (
    auth,
    complaints,
    analytics,
    clusters,
    upload,
    feedback,
    insights,
    semantic_taxonomy,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(upload.router, prefix="/upload", tags=["upload"])
api_router.include_router(complaints.router, prefix="/complaints", tags=["complaints"])
api_router.include_router(clusters.router, prefix="/clusters", tags=["clusters"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(feedback.router, prefix="/feedback", tags=["feedback"])
api_router.include_router(insights.router, prefix="/insights", tags=["insights"])
api_router.include_router(
    semantic_taxonomy.router,
    prefix="/semantic-taxonomy",
    tags=["semantic-taxonomy"],
)
