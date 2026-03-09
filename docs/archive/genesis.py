from app import app, db
from models import User

with app.app_context():
    # 1. Create all tables
    db.create_all()
    print("✅ Database tables confirmed!")

    # 2. Create or reset the Admin User (username: admin, password: admin)
    u = User.query.filter_by(username='admin').first()
    if not u:
        u = User(
            username='admin',
            email='admin@protocolpulse.com',
            is_admin=True
        )
        db.session.add(u)
    u.set_password('admin')
    db.session.commit()
    print("✅ Admin ready! Username: admin | Password: admin")
