#!/usr/bin/env python3
"""
Dedicated X Engagement Sentry worker loop.

Runs core.services.x_engagement_sentry.run_cycle on a fixed interval and logs output.
"""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import app

LOG_PATH = Path("/home/ultron/protocol_pulse/logs/sentry_worker.log")
STOP = False


def _on_signal(signum, _frame):
    global STOP
    logging.info("sentry_worker received signal %s, stopping", signum)
    STOP = True


def _setup_logging() -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[logging.FileHandler(LOG_PATH, encoding="utf-8")],
        force=True,
    )


def run_once() -> dict:
    from core.services.x_engagement_sentry import run_cycle
    with app.app_context():
        result = run_cycle()
    logging.info("x_sentry_worker cycle: %s", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Protocol Pulse sentry worker")
    parser.add_argument("--once", action="store_true", help="Run one cycle and exit")
    parser.add_argument("--interval-seconds", type=int, default=300, help="Loop interval in seconds")
    args = parser.parse_args()

    _setup_logging()
    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT, _on_signal)
    logging.info("sentry_worker started at %s", datetime.utcnow().isoformat())

    if args.once:
        run_once()
        return

    while not STOP:
        try:
            run_once()
        except Exception:
            logging.exception("sentry_worker cycle failed")
        for _ in range(max(1, int(args.interval_seconds))):
            if STOP:
                break
            time.sleep(1)

    logging.info("sentry_worker stopped")


if __name__ == "__main__":
    main()

