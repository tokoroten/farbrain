"""Test dialogue mode API with streaming."""

import asyncio
import httpx
import sys

# Force UTF-8 encoding for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')


async def test_dialogue_deepen():
    """Test the dialogue/deepen endpoint with streaming."""
    print("=" * 80)
    print("Testing Dialogue Mode - /api/dialogue/deepen")
    print("=" * 80)

    url = "http://127.0.0.1:8000/api/dialogue/deepen"
    payload = {
        "message": "リモートワークが普及してきたけど、コミュニケーションの問題がある",
        "conversation_history": None
    }

    print(f"\nSending message: {payload['message']}")
    print("\nStreaming response:")
    print("-" * 80)

    async with httpx.AsyncClient() as client:
        try:
            async with client.stream("POST", url, json=payload, timeout=30.0) as response:
                response.raise_for_status()

                full_response = ""
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]  # Remove "data: " prefix

                        if data == "[DONE]":
                            print("\n" + "-" * 80)
                            print("✓ Stream completed")
                            break
                        elif data.startswith("[ERROR]"):
                            print(f"\n✗ Error: {data}")
                            break
                        else:
                            # Print chunk without newline
                            print(data, end='', flush=True)
                            full_response += data

                print(f"\n\nFull response: {full_response}")

        except httpx.HTTPError as e:
            print(f"✗ HTTP Error: {e}")
        except Exception as e:
            print(f"✗ Unexpected error: {e}")


async def test_dialogue_finalize():
    """Test the dialogue/finalize endpoint."""
    print("\n" + "=" * 80)
    print("Testing Dialogue Mode - /api/dialogue/finalize")
    print("=" * 80)

    url = "http://127.0.0.1:8000/api/dialogue/finalize"
    payload = {
        "message": "定期的なオンラインミーティングとチャットツールの活用で、リモートワークのコミュニケーション課題を解決する",
        "conversation_history": None
    }

    print(f"\nMessage to finalize: {payload['message']}")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, timeout=30.0)
            response.raise_for_status()

            data = response.json()
            print("\n✓ Success!")
            print("-" * 80)
            print(f"Original: {data.get('original_message')}")
            print(f"Formatted: {data.get('formatted_idea')}")
            print("-" * 80)

        except httpx.HTTPStatusError as e:
            print(f"✗ HTTP Status Error: {e}")
            print(f"Response: {e.response.text}")
        except Exception as e:
            print(f"✗ Unexpected error: {e}")


async def main():
    """Run all tests."""
    await test_dialogue_deepen()
    await asyncio.sleep(1)  # Brief pause between tests
    await test_dialogue_finalize()


if __name__ == "__main__":
    asyncio.run(main())
