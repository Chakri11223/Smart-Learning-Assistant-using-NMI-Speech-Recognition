
import requests
import sys

BASE_URL = "http://localhost:5000/api"
HEADERS = {'X-User-Id': '1'}

def test_paths():
    print("Fetching paths...")
    try:
        r = requests.get(f"{BASE_URL}/learning-paths", headers=HEADERS)
        print(f"List Status: {r.status_code}")
        if r.status_code != 200:
            print(r.text)
            return
            
        data = r.json()
        paths = data.get('paths', [])
        print(f"Found {len(paths)} paths")
        
        if paths:
            first_id = paths[0]['id']
            print(f"Fetching details for path {first_id}...")
            r2 = requests.get(f"{BASE_URL}/learning-path/{first_id}", headers=HEADERS)
            print(f"Details Status: {r2.status_code}")
            print("Response text:")
            print(r2.text)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_paths()
