"""
Reset database - Delete existing database and create fresh schema.

WARNING: This will delete all existing data!
"""

import asyncio
import sys
from pathlib import Path

# Force UTF-8 encoding for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Add backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir.parent))


async def reset_database():
    """Delete existing database and create fresh schema."""

    db_path = backend_dir / "farbrain.db"

    # Delete existing database
    if db_path.exists():
        print(f"Deleting existing database: {db_path}")
        db_path.unlink()
        print("✓ Database deleted")
    else:
        print("No existing database found")

    # Import Base and models to ensure all tables are registered
    from backend.app.db.base import Base, engine
    from backend.app.models.session import Session
    from backend.app.models.user import User
    from backend.app.models.idea import Idea
    from backend.app.models.cluster import Cluster

    # Create all tables
    print("Creating new database schema...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print("✓ Database schema created successfully!")
    print(f"\nNew database location: {db_path}")
    print("\nYou can now:")
    print("  1. Run create_test_session.py to create a test session")
    print("  2. Run create_demo_session.py to create a demo session with 100 ideas")


if __name__ == "__main__":
    asyncio.run(reset_database())
