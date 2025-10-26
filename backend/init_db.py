"""Initialize database tables."""

import asyncio
from backend.app.db.base import engine
from backend.app.models.base import Base
# Import all models to register them
from backend.app.models.session import Session
from backend.app.models.user import User
from backend.app.models.idea import Idea
from backend.app.models.cluster import Cluster


async def init_db():
    """Create all database tables."""
    async with engine.begin() as conn:
        # Drop all tables (for development)
        await conn.run_sync(Base.metadata.drop_all)
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)

    print("Database tables created successfully!")


if __name__ == "__main__":
    asyncio.run(init_db())
