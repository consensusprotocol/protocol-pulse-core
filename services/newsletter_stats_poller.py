#!/usr/bin/env python3
"""
Newsletter Stats Poller — Protocol Pulse
=========================================
Polls Resend API for open/click/delivery status on recent newsletter sends.

For each newsletter_sends row from the last 14 days, GETs the status of each
Resend message ID and updates open_count/click_count on the row. Stores
per-message event data in newsletter_send_events table.

Usage:
  python3 services/newsletter_stats_poller.py              # run
  python3 services/newsletter_stats_poller.py --dry-run    # print without updating
  python3 services/newsletter_stats_poller.py --db /tmp/nl_test/protocol_pulse.db

Proposed cron (do NOT install — write to doc only):
  0 * * * * flock -n /tmp/nl_stats_poller.lock python3 /home/ultron/protocol_pulse/services/newsletter_stats_poller.py >> /home/ultron/protocol_pulse/logs/newsletter_stats.log 2>&1
"""

import argparse
import json
import logging
import os
import sqlite3
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Load .env
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
if _ENV_PATH.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(_ENV_PATH, override=False)
    except ImportError:
        with open(_ENV_PATH) as _f:
            for _line in _f:
                _line = _line.strip()
                if _line and not _line.startswith('#') and '=' in _line:
                    _k, _v = _line.split('=', 1)
                    _k = _k.strip()
                    _v = _v.strip().strip('"').strip("'")
                    if _k and _k not in os.environ:
                        os.environ[_k] = _v

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [newsletter_stats] %(levelname)s: %(message)s",
)
logger = logging.getLogger("newsletter_stats")

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
RATE_LIMIT_DELAY = 0.5  # 2 req/s


def _default_db_path() -> str:
    return str(Path(__file__).resolve().parent.parent / "instance" / "protocol_pulse.db")


def _ensure_events_table(conn: sqlite3.Connection):
    """Create newsletter_send_events table if it doesn't exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS newsletter_send_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            send_id INTEGER NOT NULL,
            message_id TEXT NOT NULL,
            last_event TEXT,
            checked_at TEXT NOT NULL,
            UNIQUE(send_id, message_id)
        )
    """)
    conn.commit()


def _get_recent_sends(conn: sqlite3.Connection, days: int = 14):
    """Get newsletter_sends rows from the last N days with message IDs."""
    cutoff = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    rows = conn.execute(
        "SELECT id, subject, resend_message_id, recipient_count, open_count, click_count "
        "FROM newsletter_sends WHERE sent_at >= ? ORDER BY sent_at DESC",
        (cutoff,),
    ).fetchall()
    return rows


def _get_message_status(message_id: str) -> dict:
    """GET https://api.resend.com/emails/{id} — read-only."""
    import requests
    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "User-Agent": "ProtocolPulse-StatsPoller/1.0",
    }
    try:
        resp = requests.get(
            f"https://api.resend.com/emails/{message_id}",
            headers=headers,
            timeout=15,
        )
        if resp.status_code == 200:
            return resp.json()
        logger.warning(f"Resend GET {message_id}: HTTP {resp.status_code}")
        return {"error": f"HTTP {resp.status_code}"}
    except Exception as e:
        logger.warning(f"Resend GET {message_id} failed: {e}")
        return {"error": str(e)}


def _check_domain_tracking() -> dict:
    """Check if open/click tracking is enabled on the Resend domain."""
    import requests
    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "User-Agent": "ProtocolPulse-StatsPoller/1.0",
    }
    try:
        resp = requests.get(
            "https://api.resend.com/domains",
            headers=headers,
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            domains = data.get("data", [])
            result = {}
            for d in domains:
                result[d.get("name", "?")] = {
                    "open_tracking": d.get("open_tracking", "unknown"),
                    "click_tracking": d.get("click_tracking", "unknown"),
                    "status": d.get("status", "unknown"),
                }
            return result
        return {"error": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"error": str(e)}


def poll(db_path: str = None, dry_run: bool = False, days: int = 14):
    """Main polling loop."""
    if not RESEND_API_KEY and not dry_run:
        logger.error("RESEND_API_KEY not set — cannot poll (use --dry-run to inspect)")
        return

    db_path = db_path or _default_db_path()
    conn = sqlite3.connect(db_path)
    try:
        _ensure_events_table(conn)

        sends = _get_recent_sends(conn, days)
        if not sends:
            logger.info("No newsletter_sends rows in last %d days", days)
            return

        logger.info("Found %d sends to poll", len(sends))

        for send_id, subject, msg_ids_json, recipient_count, old_opens, old_clicks in sends:
            if not msg_ids_json:
                continue

            try:
                message_ids = json.loads(msg_ids_json)
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Send {send_id}: invalid message_ids JSON, skipping")
                continue

            if not message_ids:
                continue

            opens = 0
            clicks = 0
            delivered = 0
            bounced = 0
            complained = 0
            now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

            logger.info(f"Send {send_id} ({(subject or '')[:40]}...): polling {len(message_ids)} message IDs")

            for mid in message_ids:
                if dry_run:
                    print(f"  [dry-run] Would GET https://api.resend.com/emails/{mid}")
                    continue

                status = _get_message_status(mid)
                time.sleep(RATE_LIMIT_DELAY)

                last_event = status.get("last_event", "")

                if last_event in ("opened", "clicked"):
                    opens += 1
                if last_event == "clicked":
                    clicks += 1
                if last_event == "delivered":
                    delivered += 1
                if last_event == "bounced":
                    bounced += 1
                if last_event == "complained":
                    complained += 1

                # Upsert event record
                try:
                    conn.execute(
                        "INSERT INTO newsletter_send_events (send_id, message_id, last_event, checked_at) "
                        "VALUES (?, ?, ?, ?) "
                        "ON CONFLICT(send_id, message_id) DO UPDATE SET "
                        "last_event=excluded.last_event, checked_at=excluded.checked_at",
                        (send_id, mid, last_event, now_str),
                    )
                except Exception as e:
                    logger.warning(f"Event upsert failed for {mid}: {e}")

            if dry_run:
                print(f"  [dry-run] Send {send_id}: {len(message_ids)} messages, no updates")
                continue

            # Update counts on newsletter_sends row
            conn.execute(
                "UPDATE newsletter_sends SET open_count=?, click_count=? WHERE id=?",
                (opens, clicks, send_id),
            )
            conn.commit()

            logger.info(
                f"Send {send_id}: opens={opens} clicks={clicks} "
                f"delivered={delivered} bounced={bounced} complained={complained}"
            )

        logger.info("Poll complete")
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Newsletter Stats Poller")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be updated")
    parser.add_argument("--db", type=str, help="Override DB path")
    parser.add_argument("--days", type=int, default=14, help="Look back N days (default 14)")
    parser.add_argument("--check-tracking", action="store_true",
                        help="Check Resend domain open/click tracking settings")
    args = parser.parse_args()

    if args.check_tracking:
        result = _check_domain_tracking()
        print(json.dumps(result, indent=2))
        return

    poll(db_path=args.db, dry_run=args.dry_run, days=args.days)


if __name__ == "__main__":
    main()
