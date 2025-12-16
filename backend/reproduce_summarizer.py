import requests
import json

BASE_URL = "http://127.0.0.1:5000"

def test_health():
    print("Testing Health Check...")
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        print(f"Health Status: {response.status_code}")
        print(f"Health Response: {response.text}")
    except Exception as e:
        print(f"Health Error: {e}")

def test_summarize_url():
    print("Testing Summarize URL...")
    # Use a known safe video (e.g., a short Python tutorial)
    url = "https://www.youtube.com/watch?v=kqtD5dpn9C8" 
    payload = {"url": url, "maxWords": 100}
    
    try:
        print("Sending POST request...")
        response = requests.post(f"{BASE_URL}/api/summarize-url", json=payload, timeout=120, proxies={})
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Summarize Error: {e}")

def test_dummy():
    print("Testing Dummy Endpoint...")
    try:
        response = requests.post(f"{BASE_URL}/api/test", json={}, timeout=5)
        print(f"Dummy Status: {response.status_code}")
        print(f"Dummy Response: {response.text}")
    except Exception as e:
        print(f"Dummy Error: {e}")

if __name__ == "__main__":
    test_health()
    test_dummy()
    test_summarize_url()
