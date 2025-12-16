from app import app, db
from sqlalchemy import text

def update_db():
    with app.app_context():
        # Create tables for Community features
        with db.engine.connect() as conn:
            # Check if community_topics table exists
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='community_topics'"))
            if not result.fetchone():
                print("Creating community_topics table...")
                conn.execute(text("""
                    CREATE TABLE community_topics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        title VARCHAR(255) NOT NULL,
                        content TEXT NOT NULL,
                        likes INTEGER DEFAULT 0,
                        created_at DATETIME NOT NULL,
                        FOREIGN KEY(user_id) REFERENCES users(id)
                    )
                """))
                conn.execute(text("CREATE INDEX ix_community_topics_user_id ON community_topics (user_id)"))

            # Check if community_comments table exists
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='community_comments'"))
            if not result.fetchone():
                print("Creating community_comments table...")
                conn.execute(text("""
                    CREATE TABLE community_comments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        topic_id INTEGER NOT NULL,
                        user_id INTEGER NOT NULL,
                        content TEXT NOT NULL,
                        created_at DATETIME NOT NULL,
                        FOREIGN KEY(topic_id) REFERENCES community_topics(id),
                        FOREIGN KEY(user_id) REFERENCES users(id)
                    )
                """))
                conn.execute(text("CREATE INDEX ix_community_comments_topic_id ON community_comments (topic_id)"))

            # Check for Analytics updates (Streaks) columns in User table
            # current_streak, last_activity_date, max_streak
            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN current_streak INTEGER DEFAULT 0"))
                print("Added current_streak column to users.")
            except Exception:
                pass # Column likely exists

            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN max_streak INTEGER DEFAULT 0"))
                print("Added max_streak column to users.")
            except Exception:
                pass

            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN last_activity_date DATETIME"))
                print("Added last_activity_date column to users.")
            except Exception:
                pass

            conn.commit()
            print("Database update for Community and Analytics completed successfully.")

if __name__ == "__main__":
    update_db()
