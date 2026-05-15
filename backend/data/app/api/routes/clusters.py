from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.routes.cluster_labels import get_normalized_cluster_distribution

router = APIRouter()

@router.get("/")
async def get_clusters(
    db: AsyncSession = Depends(get_db)
):
    from app.services.cache_service import CacheService
    cached = CacheService.get("clusters", ttl_seconds=300)
    if cached:
        return cached

    clusters = await get_normalized_cluster_distribution(db, include_subthemes=True)
    
    result = [
        {
            "id": cluster["cluster_id"],
            "label": cluster["cluster_label"],
            "count": cluster["count"],
            "subthemes": cluster.get("subthemes", []),
        } for cluster in clusters
    ]
    CacheService.set("clusters", result)
    return result
