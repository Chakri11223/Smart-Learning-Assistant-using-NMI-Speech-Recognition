import requests
import json

# Use a dummy URL param to trigger the forced failure I just added
URL = "https://www.youtube.com/watch?v=jNQXAC9IVRw&force_fail=true" 

print(f"Testing Forced Audio Fallback with URL: {URL}")
try:
    resp = requests.post(
        "http://127.0.0.1:5000/api/summarize-url", 
        json={"url": URL, "maxWords": 100},
        timeout=300
    )
    print(f"Status: {resp.status_code}")
    try:
        data = resp.json()
        print(json.dumps(data, indent=2))
        
        if 'generated_from_audio' in data.get('warnings', []):
            print("\nSUCCESS: Audio fallback triggered and succeeded.")
        else:
            print("\nFAIL: Audio fallback did not trigger or failed.")
            
    except:
        print(f"Body: {resp.text}")
except Exception as e:
    print(f"Error: {e}")
