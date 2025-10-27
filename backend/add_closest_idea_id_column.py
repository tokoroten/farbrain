"""
Add closest_idea_id column to ideas table.

This migration adds the new closest_idea_id field to track the most similar
existing idea at the time of submission.
"""

import asyncio
import sys
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir.parent))

from sqlalchemy import text
from backend.app.db.base import AsyncSessionLocal


async def add_closest_idea_id_column():
    """Add closest_idea_id column to ideas table."""

    async with AsyncSessionLocal() as db:
        try:
            # Check if column already exists
            result = await db.execute(text("PRAGMA table_info(ideas)"))
            columns = result.fetchall()
            column_names = [col[1] for col in columns]

            if 'closest_idea_id' in column_names:
                print("✓ Column 'closest_idea_id' already exists")
                return

            # Add the column
            print("Adding 'closest_idea_id' column to ideas table...")
            await db.execute(text(
                "ALTER TABLE ideas ADD COLUMN closest_idea_id VARCHAR(36)"
            ))
            await db.commit()

            print("✓ Successfully added 'closest_idea_id' column")
            print("\nNote: Existing ideas will have NULL for closest_idea_id.")
            print("New ideas will automatically track their closest idea.")

        except Exception as e:
            print(f"✗ Error adding column: {e}")
            await db.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(add_closest_idea_id_column())
