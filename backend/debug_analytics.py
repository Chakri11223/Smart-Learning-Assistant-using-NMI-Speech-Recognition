
from app import app, db, User
import json

def debug_analytics():
    with app.app_context():
        # Find a test user
        user = User.query.first()
        if not user:
            print("No users found in database.")
            return

        print(f"Testing with user: {user.email} (ID: {user.id})")
        
        client = app.test_client()
        headers = {'X-User-Id': str(user.id)}
        
        try:
            response = client.get('/api/analytics/dashboard', headers=headers)
            print(f"Status Code: {response.status_code}")
            if response.status_code != 200:
                print("Error Response:")
                print(response.get_data(as_text=True))
            else:
                print("Success!")
                data = json.loads(response.get_data(as_text=True))
                print("Keys in response:", data.keys())
        except Exception as e:
            print(f"Exception occurred: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    debug_analytics()
