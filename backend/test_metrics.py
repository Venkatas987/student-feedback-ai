import asyncio
import json
from app.core.database import AsyncSessionLocal
from app.api.routes.analytics import clustering_metrics

async def main():
    async with AsyncSessionLocal() as db:
        metrics = await clustering_metrics(db)
        print(json.dumps(metrics, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
