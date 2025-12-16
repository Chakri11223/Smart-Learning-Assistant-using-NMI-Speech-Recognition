import requests
import json

# Use a video known to have no captions or force fallback by using a URL that might fail caption fetch but succeed download
# Or just rely on the fact that my code prefers captions but falls back.
# I'll use a video that definitely has audio.
URL = "https://www.youtube.com/watch?v=jNQXAC9IVRw" # Me at the zoo - short, has audio, maybe auto-captions but good for testing download

print(f"Testing Audio Fallback with URL: {URL}")
try:
    # Increase timeout significantly as audio download + whisper takes time
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
        elif data.get('summary'):
            print("\nPARTIAL SUCCESS: Summary generated (might have used captions if available).")
        else:
            print("\nFAIL: No summary generated.")
            
    except:
        print(f"Body: {resp.text}")
except Exception as e:
    print(f"Error: {e}")
