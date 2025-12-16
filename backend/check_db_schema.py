
from app import app, db
from sqlalchemy import inspect

def check_db_schema():
    print(f"DEBUG: SQLALCHEMY_DATABASE_URI = {app.config['SQLALCHEMY_DATABASE_URI']}")
    
    with app.app_context():
        inspector = inspect(db.engine)
        if not inspector.has_table('users'):
            print("Users table NOT found!")
            return

        columns = [c['name'] for c in inspector.get_columns('users')]
        print(f"Users table columns: {columns}")
        
        missing = []
        for col in ['current_streak', 'last_activity_date', 'max_streak']:
            if col not in columns:
                missing.append(col)
                
        if missing:
            print(f"MISSING COLUMNS: {missing}")
        else:
            print("All streak columns present.")

if __name__ == "__main__":
    check_db_schema()
