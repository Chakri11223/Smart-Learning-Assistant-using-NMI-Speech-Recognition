import requests
import sys

try:
    print("Sending request...")
    resp = requests.post(
        "http://127.0.0.1:5000/api/summarize-url", 
        json={"url": "https://www.youtube.com/watch?v=kqtD5dpn9C8", "maxWords": 100},
        timeout=60
    )
    print(f"Status: {resp.status_code}")
    print(f"Body: {resp.text[:200]}")
except Exception as e:
    print(f"Error: {e}")
