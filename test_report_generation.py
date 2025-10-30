"""Test report generation with LLM analysis."""

import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

import requests

# Test session ID
SESSION_ID = "535588e7-d827-4014-a2aa-4fd09bd3cca3"
API_URL = "http://localhost:8000"


def test_markdown_report():
    """Test Markdown report generation."""
    print(f"\n[TEST] Generating Markdown report for session {SESSION_ID}...")

    try:
        response = requests.get(
            f"{API_URL}/api/reports/{SESSION_ID}/markdown",
            timeout=120  # 2 minute timeout for LLM processing
        )

        if response.status_code == 200:
            print("[SUCCESS] Report generated successfully!")
            print(f"[INFO] Content length: {len(response.content)} bytes")

            # Save to file for inspection
            output_file = Path("test_report_output.md")
            output_file.write_bytes(response.content)
            print(f"[INFO] Saved to: {output_file}")

            # Show first 500 chars
            content = response.content.decode('utf-8')
            print("\n[PREVIEW] First 500 characters:")
            print("=" * 80)
            print(content[:500])
            print("=" * 80)

            # Check for LLM analysis sections
            if "## 🔍 セッション全体の総括" in content:
                print("[✓] Overall conclusion section found")
            else:
                print("[✗] Overall conclusion section NOT found")

            if "**📊 AI分析**:" in content:
                print("[✓] Cluster analysis sections found")
            else:
                print("[✗] Cluster analysis sections NOT found")

        else:
            print(f"[ERROR] Failed with status {response.status_code}")
            print(f"[ERROR] Response: {response.text}")

    except Exception as e:
        print(f"[ERROR] Exception: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_markdown_report()
