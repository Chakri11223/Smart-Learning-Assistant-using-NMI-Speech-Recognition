
import requests

try:
    # Assuming user ID 1 exists and has data, or at least exists
    r = requests.get('http://localhost:5000/api/analytics/dashboard', headers={'X-User-Id': '1'})
    print(f"Status: {r.status_code}")
    if r.status_code != 200:
        print("Error content:")
        print(r.text[:2000]) # Print first 2000 chars of error
    else:
        print("Success")
except Exception as e:
    print(f"Request failed: {e}")
