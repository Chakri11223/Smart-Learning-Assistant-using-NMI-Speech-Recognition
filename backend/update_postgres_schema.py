
from app import app, db
from sqlalchemy import text

def update_schema():
    print("Updating Postgres schema...")
    with app.app_context():
        # Check if columns exist
        try:
            with db.engine.connect() as conn:
                # Add video_watched
                try:
                    conn.execute(text("ALTER TABLE learning_path_steps ADD COLUMN video_watched BOOLEAN DEFAULT FALSE"))
                    print("Added video_watched column")
                except Exception as e:
                    print(f"video_watched maybe exists: {e}")

                # Add code_practiced
                try:
                    conn.execute(text("ALTER TABLE learning_path_steps ADD COLUMN code_practiced BOOLEAN DEFAULT FALSE"))
                    print("Added code_practiced column")
                except Exception as e:
                    print(f"code_practiced maybe exists: {e}")
                
                conn.commit()
                print("Schema update finished.")
        except Exception as e:
            print(f"Connection error: {e}")

if __name__ == "__main__":
    update_schema()
