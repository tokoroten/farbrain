"""Test various OpenAI model names to find valid ones."""

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

api_key = os.getenv("OPENAI_API_KEY")


async def test_model(model_name: str, use_max_completion_tokens: bool = False):
    """Test if a model name is valid."""
    messages = [{"role": "user", "content": "Say hi"}]

    params = {
        "model": model_name,
        "messages": messages,
        "temperature": 0.7,
    }

    if use_max_completion_tokens:
        params["max_completion_tokens"] = 100
    else:
        params["max_tokens"] = 100

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=params,
                timeout=30.0,
            )

            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                return f"✓ SUCCESS: {content[:30]}..."
            else:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", "Unknown error")
                return f"✗ FAILED ({response.status_code}): {error_msg[:80]}..."

        except Exception as e:
            return f"✗ EXCEPTION: {str(e)[:80]}..."


async def main():
    """Test various model names."""
    print("=" * 80)
    print("Testing OpenAI Model Names")
    print("=" * 80)

    # Test models with max_tokens
    print("\n--- Testing with max_tokens parameter ---")
    models_to_test = [
        "gpt-4o-mini",
        "gpt-4o",
        "gpt-4-turbo",
        "gpt-4",
        "gpt-3.5-turbo",
    ]

    for model in models_to_test:
        print(f"\n{model}:")
        result = await test_model(model, use_max_completion_tokens=False)
        print(f"  {result}")

    # Test with max_completion_tokens
    print("\n\n--- Testing with max_completion_tokens parameter ---")
    for model in models_to_test:
        print(f"\n{model}:")
        result = await test_model(model, use_max_completion_tokens=True)
        print(f"  {result}")


if __name__ == "__main__":
    asyncio.run(main())
