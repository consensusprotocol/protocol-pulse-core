#!/usr/bin/env python3
"""agent_runner.py — Sovereign Agent Fleet daemon supervisor.

Runs Herald / Sentinel / Archivist / RenderLoop in a thread pool.
Each thread calls agent.cycle() every POLL_INTERVAL seconds.

Modes:
    python3 agents/agent_runner.py            # run forever (cron @reboot)
    python3 agents/agent_runner.py --test     # run one cycle per agent and exit
    python3 agents/agent_runner.py --status   # print fleet status JSON and exit

Startup hardening:
    1. init_db() creates tables if missing.
    2. Stuck 'processing' events older than STUCK_THRESHOLD are reset to 'pending'
       so a prior crash can't wedge the event bus.
"""
import argparse
import json
import logging
import os
import signal
import sqlite3
import sys
import threading
import time

_AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
if _AGENT_DIR not in sys.path:
    sys.path.insert(0, _AGENT_DIR)

from db_init import init_db, DB_PATH
from event_bus import fleet_status, pending_count
from herald_agent import HeraldAgent
from sentinel_agent import SentinelAgent
from archivist_agent import ArchivistAgent
from render_loop_agent import RenderLoopAgent

POLL_INTERVAL = 10
STUCK_THRESHOLD_MIN = 30

logger = logging.getLogger("agent_runner")
_stop_event = threading.Event()


def _reset_stuck_events(threshold_minutes=STUCK_THRESHOLD_MIN):
    """Reset events stuck in 'processing' past threshold back to 'pending'."""
    if not os.path.exists(DB_PATH):
        return 0
    conn = sqlite3.connect(DB_PATH, timeout=10)
    try:
        cur = conn.execute(
            "UPDATE agent_events SET status='pending' "
            "WHERE status='processing' AND timestamp < datetime('now', '-' || ? || ' minutes')",
            (int(threshold_minutes),),
        )
        reset = cur.rowcount
        conn.commit()
    finally:
        conn.close()
    if reset:
        logger.warning(f"reset {reset} stuck 'processing' events → 'pending'")
    return reset


def _run_agent(agent, once=False):
    """Poll loop for a single agent. Exits after one cycle if once=True."""
    logger.info(f"agent thread started: {agent.name}")
    while not _stop_event.is_set():
        try:
            handled = agent.cycle()
            if handled:
                logger.info(f"{agent.name}: handled {handled} event(s)")
        except Exception as exc:
            logger.exception(f"{agent.name}: cycle error — {exc}")
        if once:
            break
        if _stop_event.wait(POLL_INTERVAL):
            break
    logger.info(f"agent thread exiting: {agent.name}")


def _handle_signal(signum, frame):
    logger.info(f"signal {signum} — stopping fleet")
    _stop_event.set()


def run(once=False):
    init_db()
    _reset_stuck_events()

    agents = [HeraldAgent(), SentinelAgent(), ArchivistAgent(), RenderLoopAgent()]
    threads = [
        threading.Thread(target=_run_agent, args=(a, once),
                         name=f"agent-{a.name}", daemon=True)
        for a in agents
    ]
    for t in threads:
        t.start()

    logger.info(
        "Sovereign Agent Fleet running. %d agents active: %s",
        len(agents), ", ".join(a.name for a in agents),
    )

    if once:
        for t in threads:
            t.join(timeout=30)
        return _summary(agents)

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    try:
        while not _stop_event.is_set():
            time.sleep(60)
            logger.info(
                "fleet heartbeat: %s",
                {a.name: pending_count(a.name) for a in agents},
            )
    finally:
        _stop_event.set()
        for t in threads:
            t.join(timeout=15)


def _summary(agents):
    return {
        "status": "ok",
        "agents": [a.name for a in agents],
        "pending": {a.name: pending_count(a.name) for a in agents},
        "fleet": fleet_status(),
    }


def main():
    parser = argparse.ArgumentParser(description="Protocol Pulse Sovereign Agent Fleet")
    parser.add_argument("--test", action="store_true",
                        help="Run one cycle per agent and exit (for CI / smoke test)")
    parser.add_argument("--status", action="store_true",
                        help="Print fleet status JSON and exit")
    parser.add_argument("--log-level", default="INFO",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="[%(asctime)s] [%(name)s] %(levelname)s %(message)s",
    )

    if args.status:
        init_db()
        print(json.dumps(fleet_status(), indent=2, default=str))
        return

    if args.test:
        summary = run(once=True)
        print(json.dumps(summary, indent=2, default=str))
        return

    run(once=False)


if __name__ == "__main__":
    main()
