"""
Replit Sync — Push episode data to protocolpulse.replit.app
=============================================================
After an episode is produced, this module:
  1. Inserts clip_job records into the Replit DB (via relay)
  2. Pushes latest episode metadata for the /clips page
  3. Syncs shorts metadata

Uses base64-encoded Python scripts to avoid shell quoting issues.

Usage:
    python3 -m services.video_engine.distribution.replit_sync
    python3 -m services.video_engine.distribution.replit_sync --date 2026-03-03
"""
import base64
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

logger = logging.getLogger("ReplitSync")

REPLIT_RELAY_URL = "https://protocolpulse.replit.app/api/admin/exec"
REPLIT_TOKEN = "581b1076ca6d8a8809997d24f0869431ffd75c64de9ea703b6ab0f3e39fbd552"

ULTRON_BASE_URL = "https://relay.protocolpulse.io"


def _exec_replit(cmd: str, timeout: int = 30) -> dict:
    """Execute a command on Replit via the admin relay."""
    import requests
    try:
        resp = requests.post(
            REPLIT_RELAY_URL,
            json={"token": REPLIT_TOKEN, "cmd": cmd},
            timeout=timeout,
        )
        return resp.json()
    except Exception as e:
        logger.error(f"  Replit relay error: {e}")
        return {"returncode": 1, "stderr": str(e), "stdout": ""}


def _run_script_on_replit(script: str) -> dict:
    """Write a base64-encoded Python script to /tmp on Replit, then execute it."""
    encoded = base64.b64encode(script.encode()).decode()
    write_cmd = f"python3 -c \"import base64; open('/tmp/_sync.py','wb').write(base64.b64decode('{encoded}'))\""
    _exec_replit(write_cmd)
    return _exec_replit("python3 /tmp/_sync.py")


def sync_episode(date_str: str = None) -> dict:
    """
    Sync an episode's metadata to Replit.

    Args:
        date_str: Episode date (YYYY-MM-DD). Defaults to latest.

    Returns:
        dict with sync results
    """
    results = {"synced": [], "errors": []}

    if not date_str:
        status_path = Path("data/episodes/latest_status.json")
        if status_path.exists():
            status = json.loads(status_path.read_text())
            date_str = status.get("date")
        else:
            date_str = datetime.now().strftime("%Y-%m-%d")

    bundle = Path(f"data/episodes/{date_str}")
    if not bundle.exists():
        logger.error(f"  Episode bundle not found: {bundle}")
        results["errors"].append(f"Bundle not found: {bundle}")
        return results

    status_path = Path("data/episodes/latest_status.json")
    status = {}
    if status_path.exists():
        status = json.loads(status_path.read_text())

    plan_path = bundle / "manifest" / "show_plan.json"
    plan = {}
    if plan_path.exists():
        plan = json.loads(plan_path.read_text())

    logger.info(f"  Syncing episode: {date_str}")
    logger.info(f"  Headline: {status.get('headline', 'Unknown')}")

    # ── Step 1: Insert clip_job records ──
    logger.info("  Step 1: Syncing clip_job records...")
    clip_count = _sync_clip_jobs(date_str, plan, status)
    if clip_count > 0:
        results["synced"].append(f"{clip_count} clip_job records")
        logger.info(f"    Inserted {clip_count} clip_job records")

    # ── Step 2: Push latest episode JSON ──
    logger.info("  Step 2: Pushing episode metadata...")
    meta_ok = _push_episode_metadata(date_str, status, plan)
    if meta_ok:
        results["synced"].append("episode metadata")
        logger.info("    Episode metadata pushed")

    # ── Step 3: Sync shorts metadata ──
    logger.info("  Step 3: Syncing shorts...")
    shorts_count = _sync_shorts(date_str, plan, bundle)
    if shorts_count > 0:
        results["synced"].append(f"{shorts_count} shorts")
        logger.info(f"    {shorts_count} shorts synced")

    logger.info(f"  Sync complete: {len(results['synced'])} items, {len(results['errors'])} errors")
    return results


def _sync_clip_jobs(date_str: str, plan: dict, status: dict) -> int:
    """Insert clip_job records into Replit DB via a single batch script."""
    headline = status.get("headline", plan.get("episode_headline", "Pulse Check"))

    rows = []
    for story in plan.get("stories", []):
        sn = story.get("story_number", 0)
        story_headline = story.get("headline", "")

        for ci, clip in enumerate(story.get("clips", [])):
            rows.append({
                "video_id": clip.get("source_id", f"s{sn}_c{ci}"),
                "timestamps": f"{clip.get('start_time', '00:00')}-{clip.get('end_time', '02:00')}",
                "narrative": clip.get("context_setup", "") or "",
                "channel": clip.get("source_name", "") or clip.get("speaker", ""),
                "metadata": json.dumps({
                    "episode_date": date_str,
                    "story_number": sn,
                    "clip_index": ci,
                    "headline": headline,
                    "story_headline": story_headline,
                    "speaker": clip.get("speaker", ""),
                    "pipeline": "v5",
                }),
            })

    if not rows:
        return 0

    rows_b64 = base64.b64encode(json.dumps(rows).encode()).decode()

    script = f"""
import sqlite3, datetime, json, base64

db = sqlite3.connect("instance/protocol_pulse.db")
c = db.cursor()
rows = json.loads(base64.b64decode("{rows_b64}").decode())
count = 0
for r in rows:
    try:
        c.execute(
            "INSERT INTO clip_job (video_id, timestamps_json, narrative_context, "
            "channel_name, metadata_json, created_at, status) VALUES (?,?,?,?,?,?,?)",
            [r["video_id"], r["timestamps"], r["narrative"], r["channel"],
             r["metadata"], datetime.datetime.now().isoformat(), "complete"]
        )
        count += 1
    except Exception as e:
        print(f"ERR: {{e}}")
db.commit()
print(f"OK:{{count}}")
"""

    result = _run_script_on_replit(script)
    stdout = result.get("stdout", "")
    if "OK:" in stdout:
        try:
            return int(stdout.split("OK:")[1].strip())
        except (ValueError, IndexError):
            pass
    else:
        logger.warning(f"    clip_job batch failed: {result.get('stderr', '')[:200]}")
    return 0


def _push_episode_metadata(date_str: str, status: dict, plan: dict) -> bool:
    """Push episode metadata JSON to Replit."""
    episode_meta = {
        "date": date_str,
        "headline": status.get("headline", ""),
        "duration_sec": status.get("duration_sec", 0),
        "clips": status.get("clips", 0),
        "shorts": status.get("shorts", 0),
        "voiceovers": status.get("voiceovers", 0),
        "status": status.get("status", "unknown"),
        "stories": [
            {
                "story_number": s.get("story_number", 0),
                "headline": s.get("headline", ""),
                "story_type": s.get("story_type", ""),
            }
            for s in plan.get("stories", [])
        ],
        "video_url": f"{ULTRON_BASE_URL}/episodes/{date_str}/video",
        "audio_url": f"{ULTRON_BASE_URL}/episodes/{date_str}/audio",
        "teaser_url": f"{ULTRON_BASE_URL}/episodes/{date_str}/teaser",
        "thumbnail_url": f"{ULTRON_BASE_URL}/episodes/{date_str}/thumbnail",
    }

    meta_b64 = base64.b64encode(json.dumps(episode_meta).encode()).decode()

    script = f"""
import json, base64
data = json.loads(base64.b64decode("{meta_b64}").decode())
open("data/latest_episode.json", "w").write(json.dumps(data, indent=2))
print("OK")
"""

    result = _run_script_on_replit(script)
    return "OK" in result.get("stdout", "")


def _sync_shorts(date_str: str, plan: dict, bundle: Path) -> int:
    """Sync shorts metadata to Replit DB."""
    shorts_dir = bundle / "shorts"
    if not shorts_dir.exists():
        return 0

    shorts_plan = plan.get("shorts_plan", [])
    rows = []

    for i, short in enumerate(shorts_plan):
        filename = f"short_{i:02d}_{date_str}.mp4"
        if not (shorts_dir / filename).exists():
            continue

        rows.append({
            "video_id": f"short_{i}_{date_str}",
            "timestamps": "0-60",
            "narrative": short.get("hook_text", ""),
            "channel": "Pulse Check Short",
            "metadata": json.dumps({
                "episode_date": date_str,
                "short_index": i,
                "hook_text": short.get("hook_text", ""),
                "story_ref": short.get("story_ref", 0),
                "pipeline": "v5",
                "url": f"{ULTRON_BASE_URL}/episodes/{date_str}/short/{i}",
            }),
        })

    if not rows:
        return 0

    rows_b64 = base64.b64encode(json.dumps(rows).encode()).decode()

    script = f"""
import sqlite3, datetime, json, base64

db = sqlite3.connect("instance/protocol_pulse.db")
c = db.cursor()
rows = json.loads(base64.b64decode("{rows_b64}").decode())
count = 0
for r in rows:
    try:
        c.execute(
            "INSERT INTO clip_job (video_id, timestamps_json, narrative_context, "
            "channel_name, metadata_json, created_at, status) VALUES (?,?,?,?,?,?,?)",
            [r["video_id"], r["timestamps"], r["narrative"], r["channel"],
             r["metadata"], datetime.datetime.now().isoformat(), "complete"]
        )
        count += 1
    except Exception as e:
        print(f"ERR: {{e}}")
db.commit()
print(f"OK:{{count}}")
"""

    result = _run_script_on_replit(script)
    stdout = result.get("stdout", "")
    if "OK:" in stdout:
        try:
            return int(stdout.split("OK:")[1].strip())
        except (ValueError, IndexError):
            pass
    return 0


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    parser = argparse.ArgumentParser(description="Sync episode data to Replit")
    parser.add_argument("--date", help="Episode date (YYYY-MM-DD)")
    args = parser.parse_args()

    result = sync_episode(args.date)
    print(json.dumps(result, indent=2))
