from app import app, db
from models import User

with app.app_context():
    # 1. Create all tables
    db.create_all()
    print("✅ Database tables confirmed!")

    # 2. Create the Admin User with the required email
    if not User.query.filter_by(username='admin').first():
        u = User(
            username='admin', 
            email='admin@protocolpulse.com',  # Added this to satisfy the NOT NULL constraint
            is_admin=True
        )
        u.set_password('bitcoin2026')
        db.session.add(u)
        db.session.commit()
        print("✅ Admin user created! (User: admin | Pass: bitcoin2026)")
    else:
        print("ℹ️ Admin user already exists.")
