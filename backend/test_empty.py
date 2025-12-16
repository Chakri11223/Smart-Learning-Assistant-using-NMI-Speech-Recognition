import requests

try:
    print("Sending empty request...")
    resp = requests.post("http://127.0.0.1:5000/api/summarize-url", json={}, timeout=10)
    print(f"Status: {resp.status_code}")
    print(f"Body: {resp.text}")
except Exception as e:
    print(f"Error: {e}")
