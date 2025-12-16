import requests
import json

BASE_URL = "http://127.0.0.1:5000"

def verify_response():
    print("Testing Summarize URL Response Content...")
    # Use a known safe video
    url = "https://www.youtube.com/watch?v=kqtD5dpn9C8" 
    payload = {"url": url, "maxWords": 100}
    
    try:
        print("Sending POST request...")
        # Timeout 60s should be enough for fallback if yt-dlp fails fast or we want to catch the guidance
        response = requests.post(f"{BASE_URL}/api/summarize-url", json=payload, timeout=60, proxies={})
        print(f"Status: {response.status_code}")
        print("Response JSON:")
        try:
            data = response.json()
            print(json.dumps(data, indent=2))
            
            summary = data.get('summary', '')
            if "In that case" in summary or "I'll wait" in summary:
                print("\nFAIL: LLM is still replying conversationally.")
            elif "This is a YouTube video" in summary and "Captions were unavailable" in summary:
                print("\nSUCCESS: Guidance message returned directly.")
            else:
                print("\nUNKNOWN: Check output above.")
                
        except Exception as e:
            print(f"Could not parse JSON: {response.text}")
            
    except Exception as e:
        print(f"Request Error: {e}")

if __name__ == "__main__":
    verify_response()
