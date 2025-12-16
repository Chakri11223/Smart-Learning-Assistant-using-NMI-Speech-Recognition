from app import app, db
from sqlalchemy import inspect

with app.app_context():
    inspector = inspect(db.engine)
    print("Checking chat_sessions columns:")
    for column in inspector.get_columns('chat_sessions'):
        print(f"  - {column['name']} ({column['type']})")
