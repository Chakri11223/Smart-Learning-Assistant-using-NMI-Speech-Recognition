import requests
import json

url = "http://localhost:5000/api/learning-path-plan"
payload = {
    "topic": "Python Basics",
    "level": "beginner",
    "durationWeeks": 1
}

try:
    print("Sending request...")
    response = requests.post(url, json=payload)
    print(f"Status: {response.status_code}")
    data = response.json()
    # print(json.dumps(data, indent=2))
    
    plan = data.get('plan', [])
    if isinstance(plan, list):
        for step in plan:
            print(f"Step: {step.get('title')}")
            print(f"Video Query: {step.get('videoQuery')}")
            print(f"Video Link: {step.get('videoLink')}")
            print("-" * 20)
    else:
        print("Plan is not a list")

except Exception as e:
    print(f"Error: {e}")
