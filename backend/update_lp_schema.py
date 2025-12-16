
import sqlite3
import os

# Database file path (adjust if different)
DB_PATH = 'chat_assistant.db'

def update_schema():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Add video_watched column
        print("Adding video_watched column...")
        cursor.execute("ALTER TABLE learning_path_steps ADD COLUMN video_watched BOOLEAN DEFAULT 0")
        print("Success.")
    except sqlite3.OperationalError as e:
        print(f"Skipping video_watched: {e}")

    try:
        # Add code_practiced column
        print("Adding code_practiced column...")
        cursor.execute("ALTER TABLE learning_path_steps ADD COLUMN code_practiced BOOLEAN DEFAULT 0")
        print("Success.")
    except sqlite3.OperationalError as e:
        print(f"Skipping code_practiced: {e}")

    conn.commit()
    conn.close()
    print("Schema update complete.")

if __name__ == "__main__":
    update_schema()
