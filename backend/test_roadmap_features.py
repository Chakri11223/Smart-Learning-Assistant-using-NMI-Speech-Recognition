import requests
import json

BASE_URL = "http://localhost:5000/api"
USER_ID = "1" # Assuming user ID 1 exists, or we might need to login/signup first. 
# For simplicity, if the backend uses a mock user or allows 'demo' session, we'll try that.
# Based on LearningPath.js, it sends X-User-Id header.

HEADERS = {"X-User-Id": "1"}

def test_save_roadmap():
    print("Testing Save Roadmap...")
    payload = {
        "topic": "Test Topic",
        "level": "beginner",
        "plan": [
            {
                "step": 1,
                "title": "Step 1: Basics",
                "details": "Learn the basics.",
                "videoQuery": "python basics",
                "codingLink": "https://leetcode.com/problemset/all/?search=basics"
            },
            {
                "step": 2,
                "title": "Step 2: Practice",
                "details": "Practice coding.",
                "videoQuery": "python practice",
                "codingLink": "https://leetcode.com/problemset/all/?search=practice"
            }
        ]
    }
    
    try:
        response = requests.post(f"{BASE_URL}/learning-path/save", json=payload, headers=HEADERS)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        if response.status_code == 200:
            return response.json().get('id')
    except Exception as e:
        print(f"Error: {e}")
    return None

def test_get_roadmaps():
    print("\nTesting Get Roadmaps...")
    try:
        response = requests.get(f"{BASE_URL}/learning-paths", headers=HEADERS)
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Paths count: {len(data.get('paths', []))}")
        if data.get('paths'):
            print(f"First path topic: {data['paths'][0]['topic']}")
    except Exception as e:
        print(f"Error: {e}")

def test_toggle_step(path_id):
    if not path_id:
        print("\nSkipping Toggle Step (no path ID)")
        return

    print("\nTesting Toggle Step...")
    # First get the path details to find a step ID
    try:
        response = requests.get(f"{BASE_URL}/learning-path/{path_id}", headers=HEADERS)
        data = response.json()
        steps = data.get('path', {}).get('steps', [])
        if not steps:
            print("No steps found to toggle")
            return
            
        step_id = steps[0]['id']
        print(f"Toggling step ID: {step_id}")
        
        toggle_res = requests.post(f"{BASE_URL}/learning-path/step/{step_id}/toggle", headers=HEADERS)
        print(f"Status: {toggle_res.status_code}")
        print(f"Response: {toggle_res.text}")
        
    except Exception as e:
        print(f"Error: {e}")

def test_delete_roadmap(path_id):
    if not path_id:
        return
    print("\nTesting Delete Roadmap...")
    try:
        response = requests.delete(f"{BASE_URL}/learning-path/{path_id}", headers=HEADERS)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Ensure we have a user. If not, this might fail with 401.
    # The current auth implementation seems to rely on X-User-Id for some endpoints 
    # or session based. Let's try with the header.
    
    path_id = test_save_roadmap()
    if path_id:
        test_get_roadmaps()
        test_toggle_step(path_id)
        test_delete_roadmap(path_id)
