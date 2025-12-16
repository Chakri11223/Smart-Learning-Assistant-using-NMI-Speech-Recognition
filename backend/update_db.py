from app import app, db
from models import FeynmanScore
from sqlalchemy import text

with app.app_context():
    try:
        print("Updating database schema...")
    
        # Create tables if they don't exist
        db.create_all()
        print("Tables created (if not existed).")

        # Check if 'mode' column exists in 'chat_sessions'
        with db.engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(chat_sessions)"))
            columns = [row[1] for row in result]
            
            if 'mode' not in columns:
                print("Adding 'mode' column to 'chat_sessions'...")
                conn.execute(text("ALTER TABLE chat_sessions ADD COLUMN mode VARCHAR(50) DEFAULT 'chat'"))
                conn.commit()
                print("'mode' column added.")
            else:
                print("'mode' column already exists.")

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error: {e}")

    print("Database update complete.")
