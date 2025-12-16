import requests
import sys

def test_analytics():
    try:
        # First, try to login to get a token/user context if needed, 
        # but the endpoint uses _get_current_user which checks X-User-Id header.
        # We'll try to simulate a request with a user ID.
        # We need a valid user ID. Let's assume ID 1 exists or try to find one.
        
        # Actually, let's just try to hit the endpoint. If it returns 401, at least we know it exists.
        # If it returns 404, it doesn't exist.
        
        url = 'http://localhost:5000/api/analytics/dashboard'
        print(f"Testing {url}...")
        
        # Try with a dummy user ID header
        headers = {'X-User-Id': '1'} 
        
        response = requests.get(url, headers=headers)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
        
        if response.status_code == 404:
            print("ERROR: Endpoint not found. Backend might not be restarted.")
        elif response.status_code == 200:
            print("SUCCESS: Endpoint is reachable.")
        elif response.status_code == 401:
            print("SUCCESS: Endpoint exists (401 Unauthorized is expected if user 1 doesn't exist or logic fails).")
        else:
            print(f"WARNING: Unexpected status code {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("ERROR: Connection refused. Backend is likely not running.")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    test_analytics()
