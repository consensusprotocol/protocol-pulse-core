#!/usr/bin/env python3
"""
Sovereign Heartbeat loop:
- Runs X-Sentry engagement cycle (fetch + draft replies)
- Runs WhaleWatcher ingest cycle
- Sleeps 5 minutes between cycles
"""

from __future__ import annotations

import logging
import os
import signal
import sys
import time
import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict

# Ensure project root is importable when running as /path/to/scripts/intelligence_loop.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import app, db
from models import WhaleTransaction, TargetAlert
from services.feature_flags import is_enabled
from services.runtime_status import update_status


LOOP_SECONDS = int(os.environ.get("INTEL_LOOP_SECONDS", "300"))  # default: 5 minutes
STOP_REQUESTED = False
PULSE_EVENTS_PATH = Path("/home/ultron/protocol_pulse/data/pulse_events.jsonl")


class SignalLogger:
    """humanized, lower-case intelligence stream for commander hub."""

    def __init__(self) -> None:
        self._log = logging.getLogger("signal")

    def emit(self, tag: str, message: str) -> None:
        tag = tag.lower().strip()
        msg = message.lower().strip()
        self._log.info("[%s] %s", tag, msg)
        # Structured event stream for UI/testing (separate from raw logs).
        try:
            PULSE_EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
            event = {
                "ts": datetime.utcnow().isoformat(),
                "tag": tag,
                "message": msg,
            }
            with PULSE_EVENTS_PATH.open("a", encoding="utf-8") as fp:
                fp.write(json.dumps(event, ensure_ascii=True) + "\n")
        except Exception:
            pass

    def cycle_open(self) -> None:
        self.emit("signal", "heartbeat thump | entering fresh scan window...")

    def sentry_update(self, x_result: Dict[str, Any]) -> None:
        drafted = int(x_result.get("drafted", 0))
        fetched = int(x_result.get("fetched", 0))
        handles = x_result.get("handles") or []
        if drafted > 0 and handles:
            self.emit(
                "sentry",
                f"drafted reply to @{handles[0]} | sentiment: dry/neutral | awaiting loop approval...",
            )
        elif drafted > 0:
            self.emit("sentry", f"{drafted} fresh reply drafts queued | awaiting loop approval...")
        else:
            self.emit("sentry", f"scan complete | {fetched} source posts checked | no high-signal drafts.")

    def whale_update(self, w_result: Dict[str, Any]) -> None:
        scanned = int(w_result.get("scanned", 0))
        inserted = int(w_result.get("inserted", 0))
        fee_btc = float(w_result.get("avg_fee_btc", 0.0))
        mega = int(w_result.get("mega_inserted", 0))
        if inserted > 0:
            self.emit(
                "signal",
                f"new block detected | {fee_btc:.2f} btc fee avg | scanning for whale footprints...",
            )
            self.emit(
                "whale",
                f"{inserted} fresh whale trails logged ({mega} mega) | {scanned} signatures inspected.",
            )
        else:
            self.emit("whale", f"quiet water | {scanned} flows inspected | no new whale prints.")

    def cycle_close(self, x_result: Dict[str, Any], w_result: Dict[str, Any]) -> None:
        self.emit(
            "signal",
            "cycle sealed | "
            f"sentry drafts: {int(x_result.get('drafted', 0))} | "
            f"whale inserts: {int(w_result.get('inserted', 0))}.",
        )


def _handle_signal(signum: int, _frame: Any) -> None:
    global STOP_REQUESTED
    logging.info("received signal %s, shutting down intelligence loop", signum)
    STOP_REQUESTED = True


def _setup_logging() -> None:
    log_dir = Path("/home/ultron/protocol_pulse/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    logfile = log_dir / "automation.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(logfile, encoding="utf-8"),
        ],
        force=True,
    )
    # Kill noisy transport logs so hub terminal stays tactical.
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    logging.getLogger("flask_limiter").setLevel(logging.WARNING)


def _extract_response_json(response: Any) -> Dict[str, Any]:
    """Support Flask view responses that may be a Response or (Response, status)."""
    if isinstance(response, tuple):
        response = response[0]
    data = response.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def run_x_sentry_cycle(dry_run: bool = False, seed_posts: Any = None) -> Dict[str, Any]:
    """
    X-Sentry cycle:
    - fetch fresh high-signal X posts
    - draft one-line replies
    - persist drafts to TargetAlert for review/automation
    """
    from services.target_monitor import target_monitor
    from services.social_listener import social_listener

    posts = list(seed_posts or target_monitor.get_new_x_posts(hours_back=2))
    fetched = len(posts)
    drafted = 0
    handles = []

    for post in posts[:50]:
        handle = (post.get("handle") or "").strip()
        post_id = (post.get("post_id") or "").strip()
        text = (post.get("text") or "").strip()
        if not handle or not post_id or not text:
            continue

        source_url = f"https://x.com/{handle}/status/{post_id}"
        existing = TargetAlert.query.filter_by(source_url=source_url).first()
        if existing:
            continue

        draft = social_listener.generate_reply_one_liner(tweet_text=text, author_handle=handle)
        if not draft:
            draft = "signal noted. context added."

        if not dry_run:
            alert = TargetAlert(
                trigger_type="x_sentry",
                source_url=source_url,
                source_account=handle,
                content_snippet=text[:500],
                strategy_suggested="auto_reply_draft",
                draft_replies=json.dumps([{"style": "default", "reply": draft}]),
                status="pending",
            )
            db.session.add(alert)
        drafted += 1
        handles.append(handle)

    if drafted and not dry_run:
        db.session.commit()
    result = {"fetched": fetched, "drafted": drafted, "handles": handles[:5], "dry_run": dry_run}
    try:
        update_status("sentry", {"last_run": datetime.utcnow().isoformat(), **result})
    except Exception:
        pass
    return result


def run_whale_watcher_cycle() -> Dict[str, Any]:
    """
    Pull live whale data using existing route logic and persist new tx rows.
    Returns simple counters for observability in logs.
    """
    from routes import api_whales_live

    with app.test_request_context("/api/whales/live?min_btc=10"):
        payload = _extract_response_json(api_whales_live())

    whales = payload.get("whales", []) if isinstance(payload, dict) else []
    scanned = 0
    inserted = 0
    fee_samples = []
    mega_inserted = 0
    mega_events = []

    for item in whales:
        txid = str(item.get("txid", "")).strip()
        if not txid:
            continue
        scanned += 1

        existing = WhaleTransaction.query.filter_by(txid=txid).first()
        if existing:
            continue

        btc_amount = float(item.get("btc") or 0)
        fee_sats = item.get("fee")
        if isinstance(fee_sats, (int, float)):
            fee_samples.append(float(fee_sats) / 100_000_000)
        whale = WhaleTransaction(
            txid=txid,
            btc_amount=btc_amount,
            usd_value=item.get("usd"),
            fee_sats=item.get("fee"),
            block_height=item.get("block"),
            is_mega=btc_amount >= 1000,
        )
        db.session.add(whale)
        inserted += 1
        if btc_amount >= 1000:
            mega_inserted += 1
            mega_events.append(
                {
                    "txid": txid,
                    "btc_amount": btc_amount,
                    "usd_value": item.get("usd"),
                    "block_height": item.get("block"),
                }
            )

    if inserted:
        db.session.commit()

    avg_fee_btc = (sum(fee_samples) / len(fee_samples)) if fee_samples else 0.0
    result = {
        "scanned": scanned,
        "inserted": inserted,
        "mega_inserted": mega_inserted,
        "avg_fee_btc": avg_fee_btc,
        "mega_events": mega_events,
    }
    try:
        update_status("whale", {"last_run": datetime.utcnow().isoformat(), **result})
    except Exception:
        pass
    return result


def main() -> None:
    _setup_logging()
    signal_logger = SignalLogger()
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    signal_logger.emit("signal", f"sovereign heartbeat started | interval locked at {LOOP_SECONDS}s.")

    while not STOP_REQUESTED:
        try:
            signal_logger.cycle_open()
            with app.app_context():
                update_status("heartbeat", {"last_heartbeat": datetime.utcnow().isoformat()})
                if is_enabled("ENABLE_SOCIAL_LISTENER"):
                    x_result = run_x_sentry_cycle()
                else:
                    x_result = {"fetched": 0, "drafted": 0, "handles": []}
                if is_enabled("ENABLE_WHALE_HEARTBEAT"):
                    w_result = run_whale_watcher_cycle()
                else:
                    w_result = {"scanned": 0, "inserted": 0, "mega_inserted": 0, "avg_fee_btc": 0.0, "mega_events": []}
                try:
                    from services.distribution_manager import distribution_manager

                    if is_enabled("ENABLE_DISTRIBUTION_ENGINE"):
                        schedule_result = distribution_manager.run_scheduled_dispatch()
                        if schedule_result.get("scheduled"):
                            logging.info("distribution daily dispatch: %s", schedule_result)
                        mega_events = w_result.get("mega_events") or []
                        if mega_events:
                            whale_post_results = distribution_manager.dispatch_whale_alerts(mega_events)
                            logging.info("distribution whale dispatch: %s", whale_post_results)
                except Exception:
                    logging.exception("distribution dispatch failed")
                try:
                    from services.matty_ice_engagement import matty_ice_agent

                    if is_enabled("ENABLE_MATTY_ICE_ENGAGEMENT"):
                        matty_result = matty_ice_agent.run_cycle()
                        if (matty_result.get("replies") or []):
                            signal_logger.emit("sentry", "matty ice engaged | live alpha reply dropped.")
                            logging.info("matty-ice cycle result: %s", matty_result)
                except Exception:
                    logging.exception("matty-ice cycle failed")
            signal_logger.sentry_update(x_result)
            signal_logger.whale_update(w_result)
            signal_logger.cycle_close(x_result, w_result)
        except Exception:
            logging.exception("cycle failed")
            # Ensure the next loop iteration starts from a clean DB session state.
            with app.app_context():
                db.session.rollback()

        for _ in range(LOOP_SECONDS):
            if STOP_REQUESTED:
                break
            time.sleep(1)

    signal_logger.emit("signal", "sovereign heartbeat stopped.")


if __name__ == "__main__":
    main()
