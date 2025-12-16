
import sqlite3

def check_columns():
    conn = sqlite3.connect('chat_assistant.db')
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA table_info(learning_path_steps)")
        columns = cursor.fetchall()
        print("Columns in learning_path_steps:")
        for col in columns:
            print(f"- {col[1]}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_columns()
