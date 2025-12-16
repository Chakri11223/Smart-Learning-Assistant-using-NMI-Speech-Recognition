import requests
import json

try:
    print("Sending non-YouTube request...")
    resp = requests.post(
        "http://127.0.0.1:5000/api/summarize-url", 
        json={"url": "https://example.com/video", "maxWords": 100},
        timeout=10
    )
    print(f"Status: {resp.status_code}")
    try:
        data = resp.json()
        print(json.dumps(data, indent=2))
        summary = data.get('summary', '')
        if "In that case" in summary or "I'll wait" in summary:
            print("\nFAIL: LLM is still replying conversationally.")
        elif "This appears to be a non-YouTube URL" in summary:
            print("\nSUCCESS: Guidance message returned directly.")
        else:
            print("\nUNKNOWN: Check output above.")
    except:
        print(f"Body: {resp.text}")
except Exception as e:
    print(f"Error: {e}")
