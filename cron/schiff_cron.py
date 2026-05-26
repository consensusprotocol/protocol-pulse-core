"""
schiff_cron.py — Daily Schiff-Bot score update cron job.

Run daily at 00:00 UTC:
  cd ~/protocol_pulse && python3 cron/schiff_cron.py

Idempotent: exits 0 without re-inserting if today's score already exists.
"""
import sys
import os
import logging
from datetime import date

# Allow running from repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("schiff_cron")


def main():
    # Import app
    try:
        from app import app
    except ImportError:
        try:
            from core.app import app
        except ImportError:
            logger.error("Cannot import Flask app — check working directory (run from ~/protocol_pulse/)")
            sys.exit(1)

    # Import service
    try:
        from pp_services.schiff_service import update_score, seed_statements
    except ImportError:
        try:
            from core.services.schiff_service import update_score, seed_statements
        except ImportError:
            logger.error("Cannot import schiff_service")
            sys.exit(1)

    # Seed statements on first run (idempotent)
    logger.info("Ensuring statements are seeded…")
    try:
        seed_statements(app)
    except Exception as e:
        logger.warning("Seed failed (non-fatal): %s", e)

    # Idempotency check — bail early if today's score already exists
    with app.app_context():
        try:
            import models
            today_row = models.SchiffHypocrisy.query.filter_by(
                score_date=date.today()
            ).first()
            if today_row:
                logger.info(
                    "Today's score already exists (%.1f/100) — skipping update",
                    today_row.score,
                )
                sys.exit(0)
        except Exception as e:
            logger.warning("Idempotency check error (will proceed): %s", e)

    # Run score update
    logger.info("Running Schiff score update pipeline…")
    result = update_score(app=app)

    if result["success"]:
        score = result["score"]
        logger.info(
            "Score updated: %.1f/100 (%s) | Gold AUM: $%s | Filing: %s",
            score["score"],
            score.get("label", ""),
            f"{score.get('gold_holdings_usd', 0):,.0f}",
            score.get("filing_date", "unknown"),
        )
        sys.exit(0)
    else:
        logger.error("Score update FAILED: %s", result.get("error"))
        sys.exit(1)


if __name__ == "__main__":
    main()
