"""Test OpenAI API directly to diagnose the issue."""

import asyncio
import httpx
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Force UTF-8 encoding for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Load environment variables from backend/.env
backend_dir = Path(__file__).parent.parent / "backend"
env_path = backend_dir / ".env"
load_dotenv(env_path)

# Get settings
api_key = os.getenv("OPENAI_API_KEY")
model = os.getenv("OPENAI_MODEL", "gpt-4")


async def test_openai_api():
    """Test OpenAI API with current configuration."""
    print("=" * 60)
    print("OpenAI API Configuration Test")
    print("=" * 60)

    # Show current configuration
    print(f"\nAPI Key (first 10 chars): {api_key[:10] if api_key else 'NOT SET'}...")
    print(f"API Key (last 10 chars): ...{api_key[-10:] if api_key else 'NOT SET'}")
    print(f"Model: {model}")
    print(f"\n" + "=" * 60)

    # Test message
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Say hello in Japanese."}
    ]

    print("\nSending test request to OpenAI API...")
    print(f"URL: https://api.openai.com/v1/chat/completions")
    print(f"Model: {model}")
    print(f"Messages: {messages}")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 100,
                },
                timeout=30.0,
            )

            print(f"\n{'=' * 60}")
            print(f"Response Status: {response.status_code}")
            print(f"{'=' * 60}")

            # Try to get JSON regardless of status
            try:
                data = response.json()
                print(f"\nResponse JSON:")
                import json
                print(json.dumps(data, indent=2, ensure_ascii=False))
            except Exception as e:
                print(f"\nCould not parse JSON: {e}")
                print(f"Response text: {response.text}")

            # Raise for status to see the error
            response.raise_for_status()

            # If successful, extract content
            if response.status_code == 200:
                content = data["choices"][0]["message"]["content"]
                print(f"\n{'=' * 60}")
                print(f"SUCCESS: {content}")
                print(f"{'=' * 60}")

        except httpx.HTTPStatusError as e:
            print(f"\n{'=' * 60}")
            print(f"HTTP Error: {e}")
            print(f"{'=' * 60}")
            print(f"\nStatus Code: {e.response.status_code}")
            print(f"Response Headers: {dict(e.response.headers)}")
            print(f"Response Text: {e.response.text}")
        except Exception as e:
            print(f"\n{'=' * 60}")
            print(f"Unexpected Error: {type(e).__name__}: {e}")
            print(f"{'=' * 60}")


if __name__ == "__main__":
    asyncio.run(test_openai_api())
