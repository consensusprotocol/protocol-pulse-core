#!/usr/bin/env python3
"""
Reset admin account to username: admin, password: admin.
Run from the core directory:  python reset_admin.py
"""
import os
import sys

# Run from core/ so we use the same database as the app
if __name__ == "__main__":
    from app import app, db
    from models import User

    with app.app_context():
        u = User.query.filter_by(username="admin").first()
        if not u:
            u = User(
                username="admin",
                email="admin@protocolpulse.com",
                is_admin=True,
            )
            db.session.add(u)
        u.set_password("admin")
        db.session.commit()
        print("Admin account set: username=admin, password=admin")
        print("Log in at http://127.0.0.1:5000/login")
