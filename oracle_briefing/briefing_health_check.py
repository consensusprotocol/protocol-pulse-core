#!/usr/bin/env python3
"""Briefing Health Check — Verify HeyGen Sarah briefings are running.

Checks for briefing output files in the last 25 hours.
If none found, sends a Resend alert to contact@consensusprotocol.org.

Cron: 0 19 * * * (run daily at 2 PM EST / 19 UTC)
"""
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Load env
for env_path in [
    os.path.join(os.path.dirname(__file__), ".env"),
    os.path.join(os.path.dirname(__file__), "..", ".env"),
]:
    if os.path.exists(env_path):
        for line in open(env_path):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def check_recent_briefings(hours: int = 25) -> list[dict]:
    """Check for briefing files generated within the last N hours."""
    output_dir = Path(os.path.dirname(__file__)) / "output"
    cutoff = datetime.now() - timedelta(hours=hours)
    found = []

    if not output_dir.exists():
        return found

    for date_dir in sorted(output_dir.iterdir(), reverse=True):
        if not date_dir.is_dir():
            continue
        try:
            dir_date = datetime.strptime(date_dir.name, "%Y-%m-%d")
            if dir_date.date() < (cutoff - timedelta(days=1)).date():
                break
        except ValueError:
            continue

        for f in date_dir.glob("briefing_*.mp4"):
            stat = f.stat()
            mod_time = datetime.fromtimestamp(stat.st_mtime)
            if mod_time >= cutoff:
                found.append({
                    "file": str(f),
                    "size_mb": round(stat.st_size / 1024 / 1024, 1),
                    "modified": mod_time.isoformat(),
                    "type": f.stem.split("_")[1] if "_" in f.stem else "unknown",
                })

    return found


def send_alert(message: str):
    """Send Resend alert."""
    try:
        import resend
        resend.api_key = os.environ.get("RESEND_API_KEY", "")
        if not resend.api_key:
            print("  WARN: RESEND_API_KEY not set")
            return
        resend.Emails.send({
            "from": "pulse@protocolpulse.io",
            "to": ["contact@consensusprotocol.org"],
            "subject": "ALERT: HeyGen briefings missing",
            "html": f"<pre>{message}</pre>",
        })
        print("  Alert sent via Resend")
    except Exception as e:
        print(f"  Resend alert failed: {e}")


def main():
    print(f"\n[Briefing Health Check] {datetime.now().isoformat()}")

    briefings = check_recent_briefings(hours=25)

    if briefings:
        print(f"  OK: {len(briefings)} briefings found in last 25h")
        for b in briefings:
            print(f"    {b['type']}: {b['size_mb']}MB @ {b['modified']}")
    else:
        msg = (
            f"No HeyGen briefings found in the last 25 hours.\n"
            f"Expected 3 daily briefings (morning/midday/evening).\n"
            f"Check: crontab -l | grep heygen\n"
            f"Check: tail -50 ~/protocol_pulse/logs/heygen_briefing.log\n"
            f"Timestamp: {datetime.now().isoformat()}"
        )
        print(f"  ALERT: {msg}")
        send_alert(msg)
        sys.exit(1)


if __name__ == "__main__":
    main()
