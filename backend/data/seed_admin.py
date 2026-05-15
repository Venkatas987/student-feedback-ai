"""
seed_admin.py — Run ONCE after first deployment to create the admin user.

Usage (from backend/data/ directory):
    python seed_admin.py

Or from Render Shell:
    cd data && python seed_admin.py
"""

import asyncio
import os
import sys

# Allow running from backend/data/ directly
sys.path.insert(0, os.path.dirname(__file__))

from app.core.database import AsyncSessionLocal, init_db
from app.core.security import get_password_hash
from app.models.user import User
from sqlalchemy.future import select


ADMIN_EMAIL = "admin@institution.edu"
ADMIN_PASSWORD = "Admin@1234"
ADMIN_FULL_NAME = "Institution Administrator"


async def seed():
    print("Initializing database tables...")
    await init_db()

    async with AsyncSessionLocal() as db:
        # Check if admin already exists
        result = await db.execute(select(User).where(User.email == ADMIN_EMAIL))
        existing = result.scalars().first()

        if existing:
            print(f"ℹ️  Admin user already exists: {ADMIN_EMAIL}")
            return

        # Create admin user
        admin = User(
            email=ADMIN_EMAIL,
            hashed_password=get_password_hash(ADMIN_PASSWORD),
            full_name=ADMIN_FULL_NAME,
            is_active=True,
            is_superuser=True,
        )
        db.add(admin)
        await db.commit()
        await db.refresh(admin)

        print("=" * 50)
        print("✅ Admin user created successfully!")
        print(f"   Email   : {ADMIN_EMAIL}")
        print(f"   Password: {ADMIN_PASSWORD}")
        print(f"   Name    : {ADMIN_FULL_NAME}")
        print("=" * 50)
        print("⚠️  Change the password after first login!")


if __name__ == "__main__":
    asyncio.run(seed())
