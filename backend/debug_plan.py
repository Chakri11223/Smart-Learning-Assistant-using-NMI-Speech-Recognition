
import requests
import json
import os

# Use localhost for testing
BASE_URL = 'http://localhost:5000/api'

def debug_plan():
    print("Testing /api/learning-path-plan...")
    
    payload = {
        'topic': 'Python Basics',
        'level': 'beginner',
        'durationWeeks': 1
    }
    
    try:
        response = requests.post(f"{BASE_URL}/learning-path-plan", json=payload)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            plan = data.get('plan', [])
            print(f"Plan steps: {len(plan)}")
            
            if plan:
                first_step = plan[0]
                print(f"First step title: {first_step.get('title')}")
                print(f"First step video link: {first_step.get('videoLink')}")
                
                if first_step.get('videoLink'):
                    print("SUCCESS: Video link found!")
                else:
                    print("FAILURE: No video link found.")
            else:
                print("FAILURE: No plan steps returned.")
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    debug_plan()
