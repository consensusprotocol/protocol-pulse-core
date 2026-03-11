"""
Daily Runner — Sponsor Agent V2
================================
Finds new prospects and drafts outreach emails.
Does NOT auto-send. Human approves via dashboard.

Usage:
    python3 -m sponsor_agent.daily_run
"""

import logging
import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def run():
    """Execute daily sponsor agent pipeline."""
    from app import app

    with app.app_context():
        from sponsor_agent.prospect_finder import find_new_prospects
        from sponsor_agent.email_writer import draft_emails_for_prospects

        # Step 1: Find new prospects
        logger.info("=== Sponsor Agent Daily Run ===")
        prospects = find_new_prospects(count=5)
        logger.info("Found %d new prospects", len(prospects))

        # Step 2: Draft emails for all unprocessed prospects
        drafted = draft_emails_for_prospects()
        logger.info("Drafted %d emails", drafted)

        logger.info("=== Daily run complete. %d prospects, %d drafts. ===", len(prospects), drafted)


if __name__ == "__main__":
    run()
