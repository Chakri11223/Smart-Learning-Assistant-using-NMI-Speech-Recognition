
from app import app, db
from sqlalchemy import inspect
import os

def check_and_fix():
    print("Checking database tables...")
    with app.app_context():
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"Existing tables: {tables}")
        
        required = ['users', 'quiz_scores', 'video_summaries', 'feynman_scores', 'learning_paths', 'learning_path_steps']
        missing = [t for t in required if t not in tables]
        
        if missing:
            print(f"Missing tables: {missing}")
            print("Creating missing tables...")
            db.create_all()
            print("Tables created.")
        else:
            print("All required tables exist.")

if __name__ == "__main__":
    check_and_fix()
