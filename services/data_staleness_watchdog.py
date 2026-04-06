"""
Data Staleness Watchdog — monitors freshness of all Protocol Pulse data sources.

Checks every data source the terminal and intelligence systems depend on.
Logs WARNING if >1 hour stale, CRITICAL if >6 hours stale.

Usage:
    python3 services/data_staleness_watchdog.py

Cron: */30 * * * * cd ~/protocol_pulse && python3 services/data_staleness_watchdog.py >> logs/staleness_watchdog.log 2>&1
"""

import json
import logging
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
FLASK_DB = BASE_DIR / "instance" / "protocol_pulse.db"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [WATCHDOG] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("staleness_watchdog")

# Thresholds in seconds
WARN_THRESHOLD = 3600       # 1 hour
CRITICAL_THRESHOLD = 21600  # 6 hours


def _file_age_seconds(path: Path) -> float:
    """Return age of file in seconds from its mtime, or -1 if missing."""
    if not path.exists():
        return -1
    return time.time() - path.stat().st_mtime


def _json_ts_age(path: Path, ts_key: str = "timestamp") -> float:
    """Read a JSON file, extract a timestamp field, return age in seconds."""
    if not path.exists():
        return -1
    try:
        with open(path) as f:
            data = json.load(f)
        ts_str = data.get(ts_key, "")
        if not ts_str:
            # Fall back to file mtime
            return _file_age_seconds(path)
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - dt).total_seconds()
    except Exception:
        return _file_age_seconds(path)


def _db_signal_age() -> dict:
    """Check freshness of signal_normalizer data in DB."""
    if not FLASK_DB.exists():
        return {"mcx": -1, "epx": -1, "ihx": -1, "convergence": -1}

    result = {}
    try:
        conn = sqlite3.connect(str(FLASK_DB))
        conn.row_factory = sqlite3.Row

        for key, label in [
            ("miner_conviction", "mcx"),
            ("exchange_pressure", "epx"),
            ("insider_heat", "ihx"),
        ]:
            row = conn.execute(
                "SELECT computed_at FROM signals_normalized "
                "WHERE signal_key = ? ORDER BY computed_at DESC LIMIT 1",
                (key,),
            ).fetchone()
            if row and row["computed_at"]:
                dt = datetime.fromisoformat(row["computed_at"])
                dt = dt.replace(tzinfo=timezone.utc)
                result[label] = (datetime.now(timezone.utc) - dt).total_seconds()
            else:
                result[label] = -1

        row = conn.execute(
            "SELECT computed_at FROM convergence_state "
            "ORDER BY computed_at DESC LIMIT 1"
        ).fetchone()
        if row and row["computed_at"]:
            dt = datetime.fromisoformat(row["computed_at"])
            dt = dt.replace(tzinfo=timezone.utc)
            result["convergence"] = (datetime.now(timezone.utc) - dt).total_seconds()
        else:
            result["convergence"] = -1

        conn.close()
    except Exception as e:
        log.error("DB read error: %s", e)
        return {"mcx": -1, "epx": -1, "ihx": -1, "convergence": -1}

    return result


def check_all() -> list:
    """Check all data sources. Returns list of dicts with name, age, status."""
    sources = []

    # 1. signals.json (written by signal_data_fetcher every 5 min)
    path = BASE_DIR / "data" / "signals.json"
    age = _file_age_seconds(path)
    sources.append({
        "name": "signals.json",
        "path": str(path),
        "age_seconds": round(age, 1),
        "expected_refresh": "5 min",
    })

    # 2. sovereign_context/latest.json (written by sovereign_context_engine every 5 min)
    path = BASE_DIR / "data" / "sovereign_context" / "latest.json"
    age = _json_ts_age(path, "timestamp")
    sources.append({
        "name": "sovereign_context/latest.json",
        "path": str(path),
        "age_seconds": round(age, 1),
        "expected_refresh": "5 min",
    })

    # 3. Signal matrix indices from DB (MCX, EPX, IHX, convergence)
    db_ages = _db_signal_age()
    for label, desc in [
        ("mcx", "MCX (Miner Conviction)"),
        ("epx", "EPX (Exchange Pressure)"),
        ("ihx", "IHX (Insider Heat)"),
        ("convergence", "Convergence Score"),
    ]:
        sources.append({
            "name": f"signal_matrix/{desc}",
            "path": str(FLASK_DB),
            "age_seconds": round(db_ages.get(label, -1), 1),
            "expected_refresh": "5 min",
        })

    # 4. morning_intelligence_brief.json (written 3x daily)
    path = BASE_DIR / "data" / "intelligence" / "morning_intelligence_brief.json"
    age = _file_age_seconds(path)
    sources.append({
        "name": "morning_intelligence_brief.json",
        "path": str(path),
        "age_seconds": round(age, 1),
        "expected_refresh": "8 hours",
    })

    # 5. narrative_context.json (should refresh daily)
    path = BASE_DIR / "video_pipeline_v3" / "data" / "intelligence" / "narrative_context.json"
    age = _file_age_seconds(path)
    sources.append({
        "name": "narrative_context.json",
        "path": str(path),
        "age_seconds": round(age, 1),
        "expected_refresh": "daily",
    })

    # 6. raw_tweets.json (nitter scraper every 6h)
    path = BASE_DIR / "data" / "tweet_study" / "raw_tweets.json"
    age = _file_age_seconds(path)
    sources.append({
        "name": "raw_tweets.json",
        "path": str(path),
        "age_seconds": round(age, 1),
        "expected_refresh": "6 hours",
    })

    # Classify status
    for s in sources:
        age = s["age_seconds"]
        if age < 0:
            s["status"] = "MISSING"
        elif age > CRITICAL_THRESHOLD:
            s["status"] = "CRITICAL"
        elif age > WARN_THRESHOLD:
            s["status"] = "WARNING"
        else:
            s["status"] = "OK"

        # Human-readable age
        if age < 0:
            s["age_human"] = "missing"
        elif age < 60:
            s["age_human"] = f"{int(age)}s"
        elif age < 3600:
            s["age_human"] = f"{int(age/60)}m"
        elif age < 86400:
            s["age_human"] = f"{age/3600:.1f}h"
        else:
            s["age_human"] = f"{age/86400:.1f}d"

    return sources


def run_watchdog():
    """Run staleness check and log results."""
    sources = check_all()

    log.info("=== Staleness Watchdog Run ===")
    critical_count = 0
    warn_count = 0

    for s in sources:
        status = s["status"]
        msg = f"{s['name']}: age={s['age_human']} status={status}"
        if status == "CRITICAL":
            log.critical(msg)
            critical_count += 1
        elif status == "WARNING":
            log.warning(msg)
            warn_count += 1
        elif status == "MISSING":
            log.error(msg)
            critical_count += 1
        else:
            log.info(msg)

    if critical_count > 0:
        log.critical(
            "STALENESS ALERT: %d CRITICAL, %d WARNING sources",
            critical_count, warn_count,
        )
        # SMS alert via Twilio if configured
        _send_sms_alert(critical_count, warn_count, sources)
    elif warn_count > 0:
        log.warning("Staleness check: %d WARNING sources", warn_count)
    else:
        log.info("All data sources fresh.")

    return sources


def _send_sms_alert(critical: int, warn: int, sources: list):
    """Send SMS alert if Twilio is configured."""
    twilio_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    twilio_token = os.environ.get("TWILIO_AUTH_TOKEN")
    twilio_from = os.environ.get("TWILIO_FROM_NUMBER")
    twilio_to = os.environ.get("TWILIO_TO_NUMBER")

    if not all([twilio_sid, twilio_token, twilio_from, twilio_to]):
        log.debug("Twilio not configured, skipping SMS alert")
        return

    try:
        from twilio.rest import Client
        client = Client(twilio_sid, twilio_token)

        stale = [s for s in sources if s["status"] in ("CRITICAL", "MISSING")]
        names = ", ".join(s["name"] for s in stale[:3])
        body = f"PP STALENESS ALERT: {critical} critical sources. {names}"

        client.messages.create(body=body, from_=twilio_from, to=twilio_to)
        log.info("SMS alert sent to %s", twilio_to)
    except Exception as e:
        log.error("SMS alert failed: %s", e)


if __name__ == "__main__":
    run_watchdog()
