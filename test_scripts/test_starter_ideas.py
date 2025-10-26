"""Test McDonald's theory - starter ideas generation."""

import asyncio
import httpx
import sys
import time

# Force UTF-8 encoding for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')


async def test_session_creation_with_starters():
    """Test that creating a session automatically generates starter ideas."""
    print("=" * 80)
    print("Testing McDonald's Theory - Starter Ideas on Session Creation")
    print("=" * 80)

    base_url = "http://127.0.0.1:8000/api"

    async with httpx.AsyncClient() as client:
        # Step 1: Create a new session
        print("\n1. Creating new session...")
        session_payload = {
            "title": "テストセッション - スターターアイデア",
            "description": "McDonald's理論のテスト",
            "duration": 1800,  # 30 minutes in seconds
        }

        try:
            response = await client.post(
                f"{base_url}/sessions/",
                json=session_payload,
                timeout=10.0
            )
            response.raise_for_status()
            session_data = response.json()
            session_id = session_data["id"]

            print(f"✓ Session created: {session_id}")
            print(f"  Title: {session_data['title']}")
            print(f"  Participant count: {session_data['participant_count']}")
            print(f"  Idea count: {session_data['idea_count']}")

        except httpx.HTTPError as e:
            print(f"✗ Failed to create session: {e}")
            return

        # Step 2: Wait for background task to complete
        # (LLM formatting + embedding generation takes ~10-15 seconds for 3 ideas)
        print("\n2. Waiting for starter ideas to be generated (15 seconds)...")
        await asyncio.sleep(15)

        # Step 3: Check if ideas were created
        print("\n3. Fetching ideas from session...")
        try:
            response = await client.get(
                f"{base_url}/ideas/{session_id}",
                timeout=10.0
            )
            response.raise_for_status()
            ideas_data = response.json()

            print(f"✓ Found {ideas_data['total']} ideas")
            print("-" * 80)

            if ideas_data['total'] > 0:
                for i, idea in enumerate(ideas_data['ideas'], 1):
                    print(f"\nStarter Idea #{i}:")
                    print(f"  User: {idea['user_name']}")
                    print(f"  Raw: {idea['raw_text']}")
                    print(f"  Formatted: {idea['formatted_text']}")
                    print(f"  Novelty Score: {idea['novelty_score']}")
                    print(f"  Position: ({idea['x']:.2f}, {idea['y']:.2f})")
            else:
                print("⚠ No starter ideas found - check backend logs for errors")

            print("-" * 80)

        except httpx.HTTPError as e:
            print(f"✗ Failed to fetch ideas: {e}")

        # Step 4: Check users
        print("\n4. Checking session participants...")
        try:
            response = await client.get(
                f"{base_url}/sessions/{session_id}",
                timeout=10.0
            )
            response.raise_for_status()
            session_updated = response.json()

            print(f"✓ Participant count: {session_updated['participant_count']}")
            print(f"✓ Idea count: {session_updated['idea_count']}")

        except httpx.HTTPError as e:
            print(f"✗ Failed to fetch session: {e}")


async def main():
    """Run test."""
    await test_session_creation_with_starters()


if __name__ == "__main__":
    asyncio.run(main())
