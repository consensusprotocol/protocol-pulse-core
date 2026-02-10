"""
One-time schema update for Premium Hub: Article.premium_tier and PremiumAsk table.
Run from project root with venv: venv/bin/python -m core.scripts.add_premium_schema
"""
import os
import sys

# Allow running as script from core/ or as module from project root
if __name__ == "__main__":
    core_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if core_dir not in sys.path:
        sys.path.insert(0, core_dir)
    os.chdir(core_dir)

from app import app, db

def add_premium_schema():
    with app.app_context():
        # Ensure all tables exist (creates premium_ask if missing)
        db.create_all()
        # Add Article.premium_tier if missing (SQLite/Postgres compatible)
        backend = db.engine.url.get_backend_name()
        with db.engine.connect() as conn:
            trans = conn.begin()
            try:
                if backend == "sqlite":
                    cur = conn.execute(db.text(
                        "SELECT COUNT(*) FROM pragma_table_info('article') WHERE name='premium_tier'"
                    ))
                    has_col = cur.scalar() > 0
                    if not has_col:
                        conn.execute(db.text("ALTER TABLE article ADD COLUMN premium_tier VARCHAR(30)"))
                        print("Added article.premium_tier")
                    else:
                        print("article.premium_tier already exists")
                    cur = conn.execute(db.text(
                        "SELECT COUNT(*) FROM pragma_table_info('user') WHERE name='mega_whale_email_alerts'"
                    ))
                    has_mega = cur.scalar() > 0
                    if not has_mega:
                        conn.execute(db.text("ALTER TABLE user ADD COLUMN mega_whale_email_alerts BOOLEAN DEFAULT 0"))
                        print("Added user.mega_whale_email_alerts")
                    else:
                        print("user.mega_whale_email_alerts already exists")
                else:
                    conn.execute(db.text(
                        "ALTER TABLE article ADD COLUMN IF NOT EXISTS premium_tier VARCHAR(30)"
                    ))
                    print("Added article.premium_tier (if not exists)")
                    try:
                        conn.execute(db.text(
                            "ALTER TABLE user ADD COLUMN IF NOT EXISTS mega_whale_email_alerts BOOLEAN DEFAULT FALSE"
                        ))
                        print("Added user.mega_whale_email_alerts (if not exists)")
                    except Exception:
                        pass
                trans.commit()
            except Exception as e:
                trans.rollback()
                if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                    print("article.premium_tier already present")
                else:
                    raise
        print("Premium schema update done.")

if __name__ == "__main__":
    add_premium_schema()
