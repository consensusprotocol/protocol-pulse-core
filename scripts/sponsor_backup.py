#!/usr/bin/env python3
"""Nightly CSV backup of sponsors table (LAW 3 compliance).

Cron: 0 3 * * * cd ~/protocol_pulse && python3 scripts/sponsor_backup.py
"""

import csv
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# Resolve DB path same way as services/sponsor_radar_v2.py
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
BACKUP_DIR = DATA_DIR / "backups"


def get_db_path():
    """Get DB path from DATABASE_URL or default."""
    db_url = os.environ.get("DATABASE_URL", "")
    if db_url.startswith("sqlite:///"):
        return db_url.replace("sqlite:///", "")
    return str(ROOT / "pp.db")


def backup_sponsors():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    db_path = get_db_path()

    if not os.path.exists(db_path):
        print(f"[sponsor_backup] DB not found at {db_path}, skipping.")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        # Check if sponsors table exists
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sponsors'")
        if not cur.fetchone():
            print("[sponsor_backup] sponsors table does not exist, skipping.")
            return

        cur.execute("SELECT * FROM sponsors WHERE is_deleted=0 ORDER BY id")
        rows = cur.fetchall()

        if not rows:
            print("[sponsor_backup] No active sponsors to back up.")
            return

        columns = [desc[0] for desc in cur.description]
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = BACKUP_DIR / f"sponsors_{timestamp}.csv"

        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            for row in rows:
                writer.writerow(list(row))

        print(f"[sponsor_backup] Backed up {len(rows)} sponsors to {filename}")

        # Prune old backups (keep last 30)
        backups = sorted(BACKUP_DIR.glob("sponsors_*.csv"), reverse=True)
        for old in backups[30:]:
            old.unlink()
            print(f"[sponsor_backup] Pruned old backup: {old.name}")

    finally:
        conn.close()


if __name__ == "__main__":
    backup_sponsors()
