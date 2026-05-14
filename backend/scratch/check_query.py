import asyncio
import httpx

async def test_api():
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        # We need a token. Let's assume we can get one or the API is open (it shouldn't be).
        # Actually, let's just check the DB directly to see if the query in the route is correct.
        pass

if __name__ == "__main__":
    # Just check the route logic in a separate script using the same DB
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.future import select
    from app.models.complaint import Complaint
    from app.models.prediction import Prediction
    import os

    SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./student_feedback.db"
    engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def check_query():
        async with async_session() as session:
            query = select(Complaint).join(Prediction, isouter=True).limit(10)
            result = await session.execute(query)
            complaints = result.scalars().all()
            print(f"Found {len(complaints)} complaints")
            for c in complaints:
                print(f"ID: {c.id}, Prediction: {c.prediction}")

    asyncio.run(check_query())
