"""Test PDF generation."""

import requests

# Test session ID
SESSION_ID = "535588e7-d827-4014-a2aa-4fd09bd3cca3"
API_URL = "http://localhost:8000"


def test_pdf_report():
    """Test PDF report generation."""
    print(f"\n[TEST] Generating PDF report for session {SESSION_ID}...")

    try:
        response = requests.get(
            f"{API_URL}/api/reports/{SESSION_ID}/pdf",
            timeout=120  # 2 minute timeout for LLM processing
        )

        if response.status_code == 200:
            print("[SUCCESS] PDF generated successfully!")
            print(f"[INFO] Content length: {len(response.content)} bytes")

            # Save to file for inspection
            output_file = "test_report_output.pdf"
            with open(output_file, 'wb') as f:
                f.write(response.content)
            print(f"[INFO] Saved to: {output_file}")

            # Check if it's a valid PDF
            if response.content[:4] == b'%PDF':
                print("[✓] Valid PDF file generated")
            else:
                print("[✗] NOT a valid PDF file")

        else:
            print(f"[ERROR] Failed with status {response.status_code}")
            print(f"[ERROR] Response: {response.text}")

    except Exception as e:
        print(f"[ERROR] Exception: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_pdf_report()
