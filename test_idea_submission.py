"""Test script to verify idea formatting via API."""
import requests
import json
from datetime import datetime, timedelta
import sys
import io
import uuid

# Fix encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE_URL = "http://localhost:8001/api"

def test_idea_formatting():
    """Test complete idea submission flow."""
    print("=" * 60)
    print("Testing Idea Formatting Flow")
    print("=" * 60)

    # Step 1: Create a session
    print("\n1. Creating test session...")
    session_data = {
        "title": "LLM Format Test Session",
        "description": "Testing LLM idea formatting",
        "start_time": datetime.now().isoformat(),
        "duration": 3600,
        "password": None
    }

    response = requests.post(f"{BASE_URL}/sessions/", json=session_data)
    if response.status_code != 201:
        print(f"Failed to create session: {response.status_code}")
        print(response.text)
        return

    session = response.json()
    session_id = session["id"]
    print(f"✓ Session created: {session_id}")

    # Step 2: Join the session
    print("\n2. Joining session as test user...")
    user_id = str(uuid.uuid4())
    join_data = {"user_id": user_id, "name": "Test User"}
    response = requests.post(
        f"{BASE_URL}/users/{session_id}/join",
        json=join_data
    )
    if response.status_code != 201:
        print(f"Failed to join session: {response.status_code}")
        print(response.text)
        return

    user_data = response.json()
    print(f"✓ Joined as: {user_id}")

    # Step 3: Submit an idea WITH formatting (default)
    print("\n3. Submitting idea WITH LLM formatting...")
    raw_text = "AIを使って教育をもっと良くしたい"
    idea_data = {
        "session_id": session_id,
        "user_id": user_id,
        "raw_text": raw_text,
        "skip_formatting": False  # Enable LLM formatting
    }

    print(f"   Raw text: {raw_text}")
    response = requests.post(f"{BASE_URL}/ideas", json=idea_data)

    if response.status_code != 201:
        print(f"✗ Failed to submit idea: {response.status_code}")
        print(response.text)
        return

    idea = response.json()
    formatted_text = idea["formatted_text"]
    print(f"   ✓ Formatted text: {formatted_text}")

    # Check if formatting happened
    if raw_text == formatted_text:
        print("   ⚠ WARNING: Text was NOT formatted (same as input)")
    elif len(formatted_text) < 5:
        print("   ⚠ WARNING: Formatted text is too short")
    elif "お待ちしています" in formatted_text or "教えてください" in formatted_text:
        print("   ⚠ WARNING: LLM returned meta-comments instead of formatting")
    else:
        print("   ✓ Formatting appears successful!")

    # Step 4: Submit an idea WITHOUT formatting
    print("\n4. Submitting idea WITHOUT LLM formatting (skip_formatting=True)...")
    raw_text2 = "これは整形されないテキストです"
    idea_data2 = {
        "session_id": session_id,
        "user_id": user_id,
        "raw_text": raw_text2,
        "skip_formatting": True  # Skip LLM formatting
    }

    print(f"   Raw text: {raw_text2}")
    response = requests.post(f"{BASE_URL}/ideas", json=idea_data2)

    if response.status_code != 201:
        print(f"✗ Failed to submit idea: {response.status_code}")
        print(response.text)
        return

    idea2 = response.json()
    formatted_text2 = idea2["formatted_text"]
    print(f"   Formatted text: {formatted_text2}")

    if raw_text2 == formatted_text2:
        print("   ✓ Text was NOT formatted (as expected)")
    else:
        print("   ⚠ WARNING: Text was formatted even with skip_formatting=True")

    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)

if __name__ == "__main__":
    try:
        test_idea_formatting()
    except Exception as e:
        print(f"\nTest failed with exception: {e}")
        import traceback
        traceback.print_exc()
