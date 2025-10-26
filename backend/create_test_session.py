"""Create a test session with unlimited duration for debugging.

This script creates a test brainstorming session with:
- Unlimited duration (999999 minutes)
- No password protection
- Pre-configured prompts
- Accepting ideas by default
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

from sqlalchemy import select
from backend.app.db.base import AsyncSessionLocal
from backend.app.models.session import Session
from datetime import datetime


async def create_test_session():
    """Create an unlimited test session for debugging."""

    async with AsyncSessionLocal() as db:
        # Check if a test session already exists
        result = await db.execute(
            select(Session).where(Session.title == "デバッグ用テストセッション")
        )
        existing_session = result.scalar_one_or_none()

        if existing_session:
            print("Test session already exists")
            print(f"Session ID: {existing_session.id}")
            print(f"Title: {existing_session.title}")
            print(f"Status: {existing_session.status}")
            print(f"Join URL: http://localhost:5173/session/{existing_session.id}/join")
            return existing_session.id

        # Create new test session
        test_session = Session(
            title="デバッグ用テストセッション",
            description="開発・デバッグ用の無制限テストセッション",
            start_time=datetime.utcnow(),
            duration=999999,  # Unlimited (999999 minutes ≈ 694 days)
            status="active",
            password_hash=None,  # No password protection
            accepting_ideas=True,
            formatting_prompt="あなたは創造的なアイデアを洗練させる専門家です。ユーザーが入力した生のアイデアを、より明確で魅力的な形に整形してください。",
            summarization_prompt="以下のアイデア群に基づいて、このクラスターの特徴を表す簡潔なラベルを生成してください。",
        )

        db.add(test_session)
        await db.commit()
        await db.refresh(test_session)

        print("Test session created successfully!")
        print(f"Session ID: {test_session.id}")
        print(f"Title: {test_session.title}")
        print(f"Duration: {test_session.duration} minutes (unlimited)")
        print(f"Status: {test_session.status}")
        print(f"Password: None (public session)")
        print(f"Join URL: http://localhost:5173/session/{test_session.id}/join")

        return test_session.id


if __name__ == "__main__":
    session_id = asyncio.run(create_test_session())
