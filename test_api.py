#!/usr/bin/env python3
"""Quick test script for MVP API"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_content_generation():
    print("Testing Content Generation...")
    response = requests.post(
        f"{BASE_URL}/api/content/generate",
        json={
            "prompt": "Write a social media post about learning Python",
            "language": "hindi",
            "tone": "casual"
        }
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}\n")

def test_translation():
    print("Testing Translation...")
    response = requests.post(
        f"{BASE_URL}/api/translation/translate",
        json={
            "text": "Hello, how are you?",
            "source_language": "english",
            "target_language": "hindi",
            "tone": "neutral"
        }
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}\n")

if __name__ == "__main__":
    print("=== Bharat Content AI - MVP API Tests ===\n")
    try:
        test_content_generation()
        test_translation()
        print("✓ All tests completed!")
    except Exception as e:
        print(f"✗ Error: {e}")
        print("Make sure the backend server is running on http://localhost:8000")
