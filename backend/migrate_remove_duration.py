"""
Migration script to remove duration and ended_at columns from sessions table.
"""

import sqlite3
import sys
from pathlib import Path

def migrate():
    db_path = Path(__file__).parent / "farbrain.db"

    if not db_path.exists():
        print(f"Database not found at {db_path}")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # SQLite doesn't support DROP COLUMN directly, so we need to:
        # 1. Create a new table without the columns
        # 2. Copy data
        # 3. Drop old table
        # 4. Rename new table

        print("Creating new sessions table without duration and ended_at...")
        cursor.execute("""
            CREATE TABLE sessions_new (
                id VARCHAR(36) NOT NULL,
                title VARCHAR(255) NOT NULL,
                description TEXT,
                start_time DATETIME NOT NULL,
                status VARCHAR(20) NOT NULL,
                password_hash VARCHAR(255),
                accepting_ideas BOOLEAN NOT NULL DEFAULT 1,
                formatting_prompt TEXT,
                summarization_prompt TEXT,
                fixed_cluster_count INTEGER,
                created_at DATETIME NOT NULL,
                PRIMARY KEY (id)
            )
        """)

        print("Copying data from old table to new table...")
        cursor.execute("""
            INSERT INTO sessions_new (
                id, title, description, start_time, status, password_hash,
                accepting_ideas, formatting_prompt, summarization_prompt,
                fixed_cluster_count, created_at
            )
            SELECT
                id, title, description, start_time, status, password_hash,
                accepting_ideas, formatting_prompt, summarization_prompt,
                fixed_cluster_count, created_at
            FROM sessions
        """)

        print("Dropping old sessions table...")
        cursor.execute("DROP TABLE sessions")

        print("Renaming new table to sessions...")
        cursor.execute("ALTER TABLE sessions_new RENAME TO sessions")

        print("Creating indexes...")
        cursor.execute("CREATE INDEX ix_sessions_id ON sessions (id)")

        conn.commit()
        print("✓ Migration completed successfully!")

    except Exception as e:
        conn.rollback()
        print(f"✗ Migration failed: {e}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
