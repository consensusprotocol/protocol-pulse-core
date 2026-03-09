"""
schiff_cron.py — Daily Schiff-Bot score update cron job.

Run daily at 00:00 UTC:
  cd ~/protocol_pulse && python3 cron/schiff_cron.py

Safe to run multiple times (idempotent within same day if score already exists).
"""
import sys
import os
import logging

# Allow running from repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("schiff_cron")


def main():
    try:
        from core.app import app  # noqa: F401 — ensures Flask app context available
    except ImportError:
        try:
            from app import app  # fallback when run from core/
        except ImportError:
            logger.error("Cannot import Flask app — check working directory")
            sys.exit(1)

    try:
        from core.services.schiff_service import update_score, seed_statements
    except ImportError:
        from services.schiff_service import update_score, seed_statements

    # Seed statements on first run
    logger.info("Ensuring statements are seeded…")
    try:
        seed_statements(app)
    except Exception as e:
        logger.warning("Seed failed (non-fatal): %s", e)

    # Run score update
    logger.info("Running Schiff score update pipeline…")
    result = update_score(app=app)

    if result["success"]:
        score = result["score"]
        logger.info(
            "Score updated: %.1f/100 (%s) | Gold AUM: $%s | Filing: %s",
            score["score"],
            score["label"],
            f"{score.get('gold_holdings_usd', 0):,.0f}",
            score.get("filing_date", "unknown"),
        )
        sys.exit(0)
    else:
        logger.error("Score update FAILED: %s", result.get("error"))
        if result.get("score"):
            logger.warning("Serving stale cached score: %.1f", result["score"]["score"])
        sys.exit(1)


if __name__ == "__main__":
    main()
