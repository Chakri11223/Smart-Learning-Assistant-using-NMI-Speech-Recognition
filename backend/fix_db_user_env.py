
import os
import sys
from app import app, db
from sqlalchemy import text

def fix_db():
    print("Starting Database Fix...")
    
    # 1. Print Configuration to confirm we are in the right env
    print(f"DATABASE_URI: {app.config.get('SQLALCHEMY_DATABASE_URI')}")
    
    with app.app_context():
        try:
            # 2. Try to verify connection
            with db.engine.connect() as conn:
                print("Connected to database.")
                
                # 3. Check for users table
                result = conn.execute(text("SELECT count(*) FROM users"))
                print(f"Users table exists. Row count: {result.scalar()}")
                
                # 4. Attempt to Add Columns one by one
                # We use specific SQLite syntax or generic, but SQLAlchemy text() passes it through
                
                columns_to_add = [
                    ("current_streak", "INTEGER DEFAULT 0"),
                    ("last_activity_date", "DATE"), # SQLite doesn't have strict DATE, usually TEXT or numeric, but DATE works for hints
                    ("max_streak", "INTEGER DEFAULT 0")
                ]
                
                for col_name, col_type in columns_to_add:
                    try:
                        print(f"Attempting to add column: {col_name}...")
                        conn.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}"))
                        print(f"SUCCESS: Added {col_name}")
                        conn.commit() # Commit after each add to be safe
                    except Exception as e:
                        err_str = str(e).lower()
                        if "duplicate column" in err_str or "exists" in err_str:
                            print(f"SKIPPED: {col_name} already exists.")
                        else:
                            print(f"ERROR adding {col_name}: {e}")
                            # Don't exit, try next column
                            
            print("\nDatabase Fix Completed.")
            
        except Exception as e:
            print(f"\nCRITICAL ERROR: {e}")
            if "locked" in str(e).lower():
                print("The database is LOCKED. You MUST stop the running 'python app.py' process.")

if __name__ == "__main__":
    fix_db()
