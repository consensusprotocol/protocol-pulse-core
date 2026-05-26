#!/usr/bin/env python3
"""
social_daemon.py — Protocol Pulse Social Automation Daemon

Runs continuously via systemd. Executes social tasks on schedule:
  - Reply engine: every 2h (draft replies to mentions)
  - Comment radar: every 3h (engage thought leader tweets)
  - Reply-back engine: every 4h (respond to replies on our tweets)
  - Nostr crosspost: every 6h (best tweet → Nostr)

All tasks run with retry+backoff and crash isolation.
"""

import logging
import os
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

BASE = Path("/home/ultron/protocol_pulse")
LOG_PATH = BASE / "logs" / "social_daemon.log"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

# Ensure imports resolve
for p in [str(BASE / "core"), str(BASE)]:
    if p not in sys.path:
        sys.path.insert(0, p)
os.chdir(str(BASE / "core"))

logging.basicConfig(
    level=logging.INFO,
    format="[social_daemon] %(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(LOG_PATH), logging.StreamHandler()],
)
logger = logging.getLogger("social_daemon")


def load_env():
    env_path = BASE / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                os.environ[k.strip()] = v.strip().strip("'\"")  # Force-set so new keys picked up


def safe_run(name, func):
    """Run a task with crash isolation and logging."""
    logger.info("=== Running %s ===", name)
    # Reload .env before each task so new keys (XAI_API_KEY etc.) are picked up
    # without requiring a daemon restart
    load_env()
    try:
        result = func()
        logger.info("%s completed: %s", name, result)
        return True
    except Exception as e:
        logger.error("%s FAILED: %s\n%s", name, e, traceback.format_exc())
        return False


def run_reply_engine():
    from pp_services.reply_engine import main as reply_main
    reply_main()
    return "ok"


def run_comment_radar():
    from pp_services.comment_radar import CommentRadar
    radar = CommentRadar()
    return radar.run_cycle()


def run_reply_back():
    from pp_services.reply_back_engine import run_reply_back
    return run_reply_back()


def run_nostr_crosspost():
    from pp_services.nostr_crosspost import run_nostr_crosspost
    return run_nostr_crosspost()


# Schedule: (name, func, interval_seconds, last_run_epoch)
TASKS = [
    ["reply_engine",    run_reply_engine,    7200,  0],  # 2h
    ["comment_radar",   run_comment_radar,   10800, 0],  # 3h
    ["reply_back",      run_reply_back,      14400, 0],  # 4h
    ["nostr_crosspost", run_nostr_crosspost, 21600, 0],  # 6h
]


def main():
    load_env()
    logger.info("Social daemon starting — PID %d", os.getpid())
    logger.info("Tasks: %s", ", ".join(t[0] for t in TASKS))

    while True:
        now = time.time()
        for task in TASKS:
            name, func, interval, last_run = task
            if now - last_run >= interval:
                safe_run(name, func)
                task[3] = time.time()

        # Sleep 60s between schedule checks
        time.sleep(60)


if __name__ == "__main__":
    main()
