"""Test script to verify LLM idea formatting functionality."""
import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.app.services.llm import LLMService

async def test_format_idea():
    """Test idea formatting with LLM."""
    print("Testing LLM idea formatting...")

    # Initialize LLM service
    try:
        llm_service = LLMService()
        print("✓ LLM service initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize LLM service: {e}")
        return

    # Test raw text
    raw_text = "AIを使って教育をもっと良くしたい"

    print(f"\nInput: {raw_text}")
    print("Calling format_idea()...")

    try:
        formatted_text = await llm_service.format_idea(raw_text)
        print(f"\n✓ Success!")
        print(f"Output: {formatted_text}")

        # Check if output is reasonable
        if len(formatted_text) < 5:
            print("\n⚠ Warning: Output seems too short")
        if "お待ちしています" in formatted_text or "教えてください" in formatted_text:
            print("\n⚠ Warning: Output contains meta-comments (LLM not following instructions)")

    except Exception as e:
        print(f"\n✗ Failed to format idea: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_format_idea())
