"""
Migration-safe DB column additions for p3-sentiment-intel.
Uses ALTER TABLE IF NOT EXISTS pattern (SQLite-compatible via try/except).
Idempotent — safe to call on every app startup.
"""

import logging

logger = logging.getLogger(__name__)


def run_migrations(db):
    """
    Add all new columns and tables for the sentiment intelligence feature.
    Skips if columns/tables already exist (idempotent).
    """
    from sqlalchemy import text

    # ── New article columns ───────────────────────────────────────────────────
    article_cols = [
        ("sentiment", "TEXT"),
        ("sentiment_confidence", "REAL"),
        ("narrative_label", "TEXT"),
        ("importance_score", "INTEGER DEFAULT 50"),
        ("sentiment_dimensions", "TEXT"),
        ("market_impact_magnitude", "REAL"),
        ("sentiment_at", "DATETIME"),
    ]

    with db.engine.connect() as conn:
        for col_name, col_type in article_cols:
            try:
                conn.execute(
                    text(f"ALTER TABLE articles ADD COLUMN {col_name} {col_type}")
                )
                conn.commit()
                logger.info("db_migrate: added articles.%s", col_name)
            except Exception as e:
                # Column already exists — safe to ignore
                if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                    pass
                else:
                    logger.warning("db_migrate: articles.%s error: %s", col_name, e)

        # ── New sentiment_reports table (with extended columns) ───────────────
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS sentiment_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_date DATE UNIQUE NOT NULL,
                    overall_sentiment TEXT,
                    score INTEGER DEFAULT 50,
                    bullish_pct REAL DEFAULT 0,
                    bearish_pct REAL DEFAULT 0,
                    neutral_pct REAL DEFAULT 100,
                    narrative TEXT,
                    top_bullish_signals TEXT,
                    top_bearish_signals TEXT,
                    dominant_narrative TEXT,
                    anomaly_detected INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
            logger.info("db_migrate: sentiment_reports table ensured")
        except Exception as e:
            logger.warning("db_migrate: sentiment_reports table: %s", e)

        # ── intelligence_events table ─────────────────────────────────────────
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS intelligence_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    severity TEXT DEFAULT 'info',
                    description TEXT,
                    data_snapshot TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
            logger.info("db_migrate: intelligence_events table ensured")
        except Exception as e:
            logger.warning("db_migrate: intelligence_events table: %s", e)

        # ── Indexes ───────────────────────────────────────────────────────────
        indexes = [
            ("idx_articles_sentiment", "CREATE INDEX IF NOT EXISTS idx_articles_sentiment ON articles(sentiment, created_at)"),
            ("idx_articles_narrative", "CREATE INDEX IF NOT EXISTS idx_articles_narrative ON articles(narrative_label)"),
            ("idx_articles_importance", "CREATE INDEX IF NOT EXISTS idx_articles_importance ON articles(importance_score DESC)"),
            ("idx_intelligence_events_created", "CREATE INDEX IF NOT EXISTS idx_intelligence_events_created ON intelligence_events(created_at DESC)"),
        ]
        for idx_name, idx_sql in indexes:
            try:
                conn.execute(text(idx_sql))
                conn.commit()
            except Exception as e:
                if "already exists" not in str(e).lower():
                    logger.warning("db_migrate: index %s: %s", idx_name, e)

    logger.info("db_migrate: sentiment-intel migrations complete")
