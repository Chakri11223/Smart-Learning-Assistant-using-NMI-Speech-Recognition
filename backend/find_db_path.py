
from app import app, db
import os

with app.app_context():
    uri = app.config['SQLALCHEMY_DATABASE_URI']
    print(f"URI: {uri}")
    engine = db.engine
    print(f"Engine URL: {engine.url}")
    if 'sqlite' in str(engine.url):
        print(f"File path: {engine.url.database}")
        abs_path = os.path.abspath(engine.url.database)
        print(f"Absolute path: {abs_path}")
