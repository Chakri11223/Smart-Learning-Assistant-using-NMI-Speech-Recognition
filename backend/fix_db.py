from app import app, db
from sqlalchemy import text, inspect

with app.app_context():
    print("Inspecting database...")
    inspector = inspect(db.engine)
    columns = [c['name'] for c in inspector.get_columns('chat_sessions')]
    print(f"Current columns in chat_sessions: {columns}")
    
    if 'mode' not in columns:
        print("Adding 'mode' column...")
        try:
            with db.engine.connect() as conn:
                conn.execute(text("ALTER TABLE chat_sessions ADD COLUMN mode VARCHAR(50) DEFAULT 'chat'"))
                conn.commit()
            print("Successfully added 'mode' column.")
        except Exception as e:
            print(f"Error adding column: {e}")
    else:
        print("'mode' column already exists.")
        
    # Verify again
    inspector = inspect(db.engine)
    columns = [c['name'] for c in inspector.get_columns('chat_sessions')]
    print(f"Final columns in chat_sessions: {columns}")
