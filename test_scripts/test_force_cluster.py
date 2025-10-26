"""Test script for force-cluster endpoint."""

import requests
import json

# Test force-cluster endpoint with LLM labels
session_id = "99dab077-1a18-4adb-8bc0-8ecf7a35aa96"

print(f"Testing force-cluster endpoint for session: {session_id}")
print("Testing with use_llm_labels=True...")

response = requests.post(
    "http://localhost:8000/api/debug/force-cluster",
    json={
        "session_id": session_id,
        "use_llm_labels": True,
        "fixed_cluster_count": None
    }
)

print(f"\nStatus Code: {response.status_code}")
print(f"Response:\n{json.dumps(response.json(), indent=2, ensure_ascii=False)}")
