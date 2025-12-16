from app import app, db, User

with app.app_context():
    users = User.query.all()
    print(f"Total Users: {len(users)}")
    for user in users:
        print(f"ID: {user.id}, Name: {user.name}, Email: {user.email}, Verified: {user.verified}")
