"""
Pre-warm the analytics cache from existing database data.
Run this after clearing the stale cache to immediately populate
correct values without waiting for another upload.
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def warmup():
    from app.core.database import AsyncSessionLocal, init_db
    from app.api.routes.analytics import get_dashboard_summary, clustering_metrics, cluster_sentiment_heatmap
    from app.api.routes.clusters import get_clusters
    from app.services.cache_service import CacheService

    print("Initializing DB...")
    await init_db()

    print("Opening session...")
    async with AsyncSessionLocal() as db:
        print("Precomputing dashboard summary...")
        try:
            summary = await get_dashboard_summary(db)
            data = summary.model_dump() if hasattr(summary, "model_dump") else summary
            CacheService.set("summary", data)
            print(f"  summary: total_complaints={data.get('total_complaints')}, sessions={data.get('total_sessions')}")
        except Exception as e:
            print(f"  ERROR summary: {e}")

        print("Precomputing clustering metrics...")
        try:
            metrics = await clustering_metrics(db)
            CacheService.set("clustering_metrics", metrics)
            print(f"  metrics: silhouette={metrics.get('silhouette_score')}, total_points={metrics.get('total_evaluated_points')}")
        except Exception as e:
            print(f"  ERROR clustering_metrics: {e}")

        print("Precomputing cluster sentiment heatmap...")
        try:
            heatmap = await cluster_sentiment_heatmap(db)
            CacheService.set("cluster_sentiment_heatmap", heatmap)
            print(f"  heatmap: {len(heatmap.get('cluster_labels', []))} clusters")
        except Exception as e:
            print(f"  ERROR cluster_sentiment_heatmap: {e}")

        print("Precomputing clusters...")
        try:
            clusters = await get_clusters(db)
            CacheService.set("clusters", clusters)
            print(f"  clusters: {len(clusters)} items")
        except Exception as e:
            print(f"  ERROR clusters: {e}")

    print("\nCache warmup complete.")

if __name__ == "__main__":
    asyncio.run(warmup())
