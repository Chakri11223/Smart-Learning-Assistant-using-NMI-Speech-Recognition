"""
Database initialization script.
Run this once to create the database tables.
"""
from app import app, db
from models import User, QuizScore, ChatHistory

def init_database():
    """Create all database tables"""
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        print("Database tables created successfully!")
        print("\nTables created:")
        print("  - users")
        print("  - quiz_scores")
        print("  - chat_history")

if __name__ == '__main__':
    init_database()

