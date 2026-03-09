"""
Sponsor Follow-up Scheduler — auto follow-up sequence for Protocol Pulse sponsor pipeline.

Sequences:
- T+3 days: First follow-up (if no reply)
- T+7 days: Second follow-up (shorter, different angle)
- T+14 days: Final follow-up (breakup email)

Run: python3 -m services.sponsor_followup --run
Cron: Daily at 9 AM UTC.
"""

import json
import logging
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def _get_db_path() -> str:
    try:
        from app import app
        uri = app.config.get("SQLALCHEMY_DATABASE_URI", "sqlite:///pp.db")
        if uri.startswith("sqlite:///"):
            path = uri.replace("sqlite:///", "")
            if not os.path.isabs(path):
                path = os.path.join(os.path.dirname(os.path.dirname(__file__)), path)
            return path
    except Exception:
        pass
    return "pp.db"


def _get_config(db_path: str) -> Dict:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM sponsor_config WHERE id = 1")
        row = cur.fetchone()
        if row:
            return dict(row)
        return {"followup_days_1": 3, "followup_days_2": 7, "followup_days_3": 14,
                "daily_send_limit": 25, "auto_draft_enabled": 0}
    except sqlite3.Error:
        return {"followup_days_1": 3, "followup_days_2": 7, "followup_days_3": 14,
                "daily_send_limit": 25, "auto_draft_enabled": 0}
    finally:
        conn.close()


def get_due_followups(db_path: str) -> List[Dict]:
    """
    Find sponsors in 'contacted' status whose last_contacted_at has passed
    the configured follow-up intervals without a reply.
    """
    config = _get_config(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        # Get all contacted sponsors with auto_followup_enabled
        cur.execute("""
            SELECT s.id, s.company_name, s.status, s.last_contacted_at,
                   s.contact_email, s.auto_followup_enabled,
                   COUNT(so.id) as outreach_count
            FROM sponsors s
            LEFT JOIN sponsor_outreach so ON so.sponsor_id = s.id AND so.sent_at IS NOT NULL
            WHERE s.status = 'contacted'
              AND s.is_deleted = 0
              AND s.auto_followup_enabled = 1
            GROUP BY s.id
        """)
        rows = [dict(r) for r in cur.fetchall()]
        due = []
        now = datetime.utcnow()

        for row in rows:
            last_contacted = row.get("last_contacted_at")
            if not last_contacted:
                continue
            try:
                lc_dt = datetime.fromisoformat(last_contacted)
            except ValueError:
                continue

            days_since = (now - lc_dt).days
            count = row.get("outreach_count", 1)

            followup_needed = False
            followup_num = 0
            if count == 1 and days_since >= config["followup_days_1"]:
                followup_needed, followup_num = True, 1
            elif count == 2 and days_since >= config["followup_days_2"]:
                followup_needed, followup_num = True, 2
            elif count == 3 and days_since >= config["followup_days_3"]:
                followup_needed, followup_num = True, 3

            if followup_needed:
                row["followup_number"] = followup_num
                row["days_since_contact"] = days_since
                due.append(row)

        return due
    except sqlite3.Error as e:
        logger.error("Error fetching due followups: %s", e)
        return []
    finally:
        conn.close()


def generate_followup_draft(sponsor_id: int, followup_number: int) -> Optional[Dict]:
    """Generate a follow-up draft (shorter, different angle each time)."""
    db_path = _get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM sponsors WHERE id = ? AND is_deleted = 0", (sponsor_id,))
        sponsor = dict(cur.fetchone() or {})
        if not sponsor:
            return None

        # Get original draft for context
        cur.execute("""
            SELECT subject, body FROM sponsor_outreach
            WHERE sponsor_id = ? AND channel = 'email'
            ORDER BY version ASC LIMIT 1
        """, (sponsor_id,))
        orig = cur.fetchone()
        original_subject = (orig["subject"] if orig else
                            f"Partnership opportunity: Protocol Pulse × {sponsor.get('company_name')}")
    except sqlite3.Error as e:
        logger.error("DB error in generate_followup_draft: %s", e)
        return None
    finally:
        conn.close()

    name = sponsor.get("company_name", "")
    angle = sponsor.get("outreach_angle", "Bitcoin audience fit")

    # Different angles per follow-up number
    if followup_number == 1:
        subject = f"Re: {original_subject}"
        body = f"""Hi again,

I wanted to follow up on my previous message about a partnership with Protocol Pulse.

We just published our latest Bitcoin intelligence briefing — if you'd like to see the content quality and audience engagement firsthand, happy to share a preview.

{angle}

Still worth a 15-minute call? Happy to work around your schedule.

Best,
PBX
Protocol Pulse | protocolpulse.io"""

    elif followup_number == 2:
        subject = f"Quick question — {name}"
        body = f"""Hi,

Two quick questions:

1. Is podcast/content sponsorship something {name} is actively exploring for Q2?
2. If so, who's the right person to talk to about media partnerships?

Protocol Pulse reaches {10000}+ engaged Bitcoin users monthly. Happy to send our media kit if useful.

Either way — appreciate you considering it.

PBX
Protocol Pulse"""

    else:  # Final
        subject = f"Last note — {name} × Protocol Pulse"
        body = f"""Hi,

I'll make this my last message so I'm not cluttering your inbox.

If the timing isn't right for a Protocol Pulse partnership, no worries at all. We'll be here when it is.

If you'd like to revisit this in Q3, just reply to this thread and I'll set something up.

Best of luck with your campaigns.

PBX
Protocol Pulse | protocolpulse.io"""

    return {
        "sponsor_id": sponsor_id,
        "subject": subject,
        "body": body,
        "followup_number": followup_number,
        "channel": "email",
    }


def schedule_followups(dry_run: bool = False) -> Dict:
    """
    Main runner: find due follow-ups, generate drafts, optionally queue for sending.
    Returns summary stats.
    """
    db_path = _get_db_path()

    try:
        # Ensure tables exist
        from services.sponsor_radar_v2 import ensure_tables
        ensure_tables()
    except Exception:
        pass

    due = get_due_followups(db_path)
    stats = {"checked": len(due), "drafted": 0, "errors": 0}

    for item in due:
        try:
            draft = generate_followup_draft(item["id"], item["followup_number"])
            if not draft:
                continue

            if not dry_run:
                # Save follow-up draft
                conn = sqlite3.connect(db_path)
                try:
                    cur = conn.cursor()
                    cur.execute("""
                        SELECT MAX(version) FROM sponsor_outreach
                        WHERE sponsor_id = ? AND channel = 'email'
                    """, (item["id"],))
                    row = cur.fetchone()
                    next_version = (row[0] or 0) + 1

                    cur.execute("""
                        INSERT INTO sponsor_outreach (
                            sponsor_id, version, channel, subject, body,
                            grok_review_score, grok_review_notes, created_at
                        ) VALUES (?,?,?,?,?,?,?,?)
                    """, (
                        item["id"], next_version, "email",
                        draft["subject"], draft["body"],
                        75, f"Auto-generated follow-up #{item['followup_number']}",
                        datetime.utcnow().isoformat()
                    ))
                    cur.execute("""
                        INSERT INTO sponsor_activity_log (sponsor_id, action, detail, actor)
                        VALUES (?,?,?,?)
                    """, (
                        item["id"], "followup_drafted",
                        f"Follow-up #{item['followup_number']} drafted — {item['days_since_contact']}d since last contact",
                        "system"
                    ))
                    conn.commit()
                    stats["drafted"] += 1
                except sqlite3.Error as e:
                    conn.rollback()
                    logger.error("Failed to save followup for sponsor %s: %s", item["id"], e)
                    stats["errors"] += 1
                finally:
                    conn.close()
            else:
                logger.info("DRY RUN: Would draft follow-up #%s for %s",
                            item["followup_number"], item["company_name"])
                stats["drafted"] += 1

        except Exception as e:
            logger.error("Follow-up error for sponsor %s: %s", item.get("id"), e, exc_info=True)
            stats["errors"] += 1

    return stats


if __name__ == "__main__":
    import argparse
    import sys

    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.run or args.dry_run:
        sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
        os.chdir(os.path.dirname(os.path.dirname(__file__)))
        stats = schedule_followups(dry_run=args.dry_run)
        print(f"Follow-up stats: {stats}")
    else:
        parser.print_help()
