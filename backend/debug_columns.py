
import sqlite3

def show_schema():
    conn = sqlite3.connect('chat_assistant.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f"Tables found: {tables}")
    
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='learning_path_steps'")
    schema = cursor.fetchone()
    if schema:
        print(schema[0])
    else:
        print("Table not found")
    conn.close()

if __name__ == "__main__":
    show_schema()
