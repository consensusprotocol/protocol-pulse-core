#!/usr/bin/env python3
"""
Sovereign Heartbeat loop:
- Runs Sentry engagement cycle (X + Nostr fetch + draft replies)
- Runs WhaleWatcher ingest cycle
- Sleeps 120 seconds between cycles (configurable)
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
from typing import Any, Dict, List

# Ensure project root is importable when running as /path/to/scripts/intelligence_loop.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import app, db
from models import WhaleTransaction, TargetAlert, CuratedPost, SentryQueue, XInboxTweet
from services.feature_flags import is_enabled
from services.runtime_status import update_status
from services import ollama_runtime
from core.event_bus import emit_event


LOOP_SECONDS = int(os.environ.get("INTEL_LOOP_SECONDS", "120"))  # default: 120s
STOP_REQUESTED = False
PULSE_EVENTS_PATH = Path("/home/ultron/protocol_pulse/data/pulse_events.jsonl")
SOCIAL_TARGETS_PATH = Path("/home/ultron/protocol_pulse/config/social_targets.json")
DAILY_BRIEFS_PATH = Path("/home/ultron/protocol_pulse/data/daily_briefs.json")
SENTINEL_STATE_PATH = Path("/home/ultron/protocol_pulse/logs/sentinel_state.json")


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
            emit_event(
                event_type=f"{tag}_signal",
                source="intelligence_loop",
                lane=tag if tag in {"whale", "sentry", "risk", "medley"} else "system",
                severity="info",
                title=tag,
                detail=msg,
                payload={"tag": tag, "message": msg},
            )
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


def _load_bol_handles(limit: int = 30) -> List[str]:
    try:
        data = json.loads(SOCIAL_TARGETS_PATH.read_text(encoding="utf-8"))
        handles = []
        for row in data.get("targets", []):
            handle = str((row or {}).get("handle") or "").strip().lstrip("@").lower()
            if handle:
                handles.append(handle)
        if handles:
            return handles[:limit]
    except Exception:
        pass
    return [
        "saylor", "elonmusk", "jackmallers", "lynaldencontact", "jack",
        "lopp", "saifedean", "adam3us", "jeffbooth", "prestonpysh",
        "martybent", "pierre_rochard", "natbrunell", "documentingbtc",
        "bitcoinmagazine", "nvk", "woonomic", "coryklippsten",
    ][:limit]


def run_x_sentry_cycle(dry_run: bool = False, seed_posts: Any = None, handles: List[str] | None = None) -> Dict[str, Any]:
    """
    X-Sentry cycle:
    - fetch fresh high-signal X posts
    - draft one-line replies
    - persist drafts to TargetAlert for review/automation
    """
    from services.target_monitor import target_monitor
    from services.social_listener import social_listener

    posts = list(seed_posts or target_monitor.get_new_x_posts(hours_back=2, handles=handles or _load_bol_handles()))
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


def run_nostr_sentry_cycle(dry_run: bool = False) -> Dict[str, Any]:
    """
    Nostr sentry cycle:
    - fetch high-signal Nostr notes
    - draft one-line replies
    - persist drafts to TargetAlert for review/automation
    """
    from services.sentiment_tracker_service import SentimentTrackerService
    from services.social_listener import social_listener

    tracker = SentimentTrackerService()
    notes = tracker.fetch_nostr_notes(hours_back=2, limit=50)
    fetched = len(notes)
    drafted = 0
    handles = []

    for note in notes:
        post_id = (note.get("post_id") or "").strip()
        text = (note.get("content") or "").strip()
        source_url = (note.get("url") or "").strip()
        handle = (note.get("author_handle") or "nostr").strip()
        if not post_id or not text:
            continue
        if not source_url:
            source_url = f"https://primal.net/e/{post_id.replace('nostr_', '')}"

        existing = TargetAlert.query.filter_by(source_url=source_url).first()
        if existing:
            continue

        draft = social_listener.generate_reply_one_liner(tweet_text=text, author_handle=handle)
        if not draft:
            draft = "signal noted. context added."

        if not dry_run:
            alert = TargetAlert(
                trigger_type="nostr_sentry",
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
        update_status("nostr_sentry", {"last_run": datetime.utcnow().isoformat(), **result})
    except Exception:
        pass
    return result


def run_whale_watcher_cycle() -> Dict[str, Any]:
    """
    Pull live whale data using existing route logic and persist new tx rows.
    Returns simple counters for observability in logs.
    """
    from services.whale_watcher import whale_watcher

    whales = whale_watcher.fetch_live_whales(min_btc=10.0)
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


def _load_json(path: Path, fallback: Dict[str, Any]) -> Dict[str, Any]:
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return fallback


def _save_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def _extract_urgent_events(posts: List[CuratedPost], whales: Dict[str, Any]) -> List[str]:
    events: List[str] = []
    mega = int(whales.get("mega_inserted", 0))
    if mega > 0:
        events.append(f"massive btc outflow cluster detected: {mega} mega-whale movements.")
    threat_keywords = [
        "bank failure", "bank collapse", "insolvency", "liquidity crunch",
        "regulatory crackdown", "sec action", "ban", "sanction",
        "exchange freeze", "capital controls",
    ]
    for p in posts:
        text = f"{(p.title or '')} {(p.content_preview or '')}".lower()
        if any(k in text for k in threat_keywords):
            events.append(f"urgent narrative shift from value stream: {(p.title or 'untitled signal')[:120]}.")
            if len(events) >= 3:
                break
    return events


def run_deep_context_scan(whale_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a 5-bullet sovereign brief from the latest 100 Value Stream entries,
    detect urgent narrative shifts, and persist to data/daily_briefs.json.
    """
    posts = (
        CuratedPost.query.order_by(CuratedPost.submitted_at.desc())
        .limit(100)
        .all()
    )
    if not posts:
        return {"ok": False, "error": "no_value_stream_entries"}

    lines = []
    for p in posts[:100]:
        lines.append(
            f"- title: {(p.title or 'untitled')[:140]} | sats={int(p.total_sats or 0)} | zaps={int(p.zap_count or 0)} | platform={p.platform or 'n/a'}"
        )
    digest = "\n".join(lines)
    prompt = (
        "you are sovereign intelligence director. summarize context into exactly 5 bullets.\n"
        "style: lowercase, sharp, tactical, no emojis.\n"
        "include where narrative momentum is rising/falling.\n"
        "if clear threat signals exist, mention urgency.\n\n"
        f"value stream sample:\n{digest[:12000]}"
    )
    summary = ollama_runtime.generate(
        prompt=prompt,
        preferred_model="llama3.1",
        options={"temperature": 0.25, "num_predict": 260},
        timeout=12,
    )
    if not summary:
        # deterministic fallback if model unavailable
        top = posts[:5]
        summary = "\n".join(
            [f"- {(p.title or 'untitled signal')[:100]} (sats {int(p.total_sats or 0)})" for p in top]
        )
    urgent_events = _extract_urgent_events(posts, whale_result)

    store = _load_json(DAILY_BRIEFS_PATH, {"briefs": []})
    briefs = list(store.get("briefs") or [])
    row = {
        "ts": datetime.utcnow().isoformat(),
        "type": "sovereign_brief",
        "source_count": len(posts),
        "summary": summary.strip(),
        "urgent_events": urgent_events,
    }
    briefs.append(row)
    store["briefs"] = briefs[-200:]
    _save_json(DAILY_BRIEFS_PATH, store)
    try:
        update_status(
            "sentinel_brief",
            {
                "last_run": row["ts"],
                "source_count": len(posts),
                "urgent_count": len(urgent_events),
                "focus": (urgent_events[0] if urgent_events else "market structure and flows"),
            },
        )
    except Exception:
        pass
    return {"ok": True, "brief": row}


def _is_high_engagement(post: Dict[str, Any]) -> bool:
    # Use engagement fields when available; otherwise keep traffic by default.
    score = 0
    for key in ("likes", "like_count", "retweets", "reposts", "reply_count", "views"):
        val = post.get(key)
        if isinstance(val, (int, float)):
            score += float(val)
    if score > 0:
        return score >= 150
    text_len = len(str(post.get("text") or ""))
    return text_len >= 50


def run_ghostwriter_autodraft(handles: List[str], max_drafts: int = 60) -> Dict[str, Any]:
    """
    Scan target-list X posts and write sovereign witty draft replies into SentryQueue.
    """
    from services.target_monitor import target_monitor

    posts = target_monitor.get_new_x_posts(hours_back=2, handles=handles or _load_bol_handles())
    if not posts:
        fallback_alerts = (
            TargetAlert.query.filter(TargetAlert.source_account.isnot(None))
            .order_by(TargetAlert.created_at.desc())
            .limit(120)
            .all()
        )
        for a in fallback_alerts:
            source = str(a.source_url or "")
            if "/status/" not in source:
                continue
            post_id = source.rsplit("/status/", 1)[-1].split("?", 1)[0].strip()
            posts.append(
                {
                    "handle": str(a.source_account or "").strip().lstrip("@").lower(),
                    "post_id": post_id,
                    "text": str(a.content_snippet or "")[:500],
                }
            )
    if not posts:
        inbox_rows = (
            XInboxTweet.query
            .order_by(XInboxTweet.created_at.desc())
            .limit(200)
            .all()
        )
        for row in inbox_rows:
            if not row.tweet_id or not row.author_handle:
                continue
            posts.append(
                {
                    "handle": str(row.author_handle).strip().lstrip("@").lower(),
                    "post_id": str(row.tweet_id).strip(),
                    "text": str(row.tweet_text or "")[:500],
                }
            )
    created = 0
    scanned = len(posts)
    for post in posts:
        if created >= max_drafts:
            break
        if not _is_high_engagement(post):
            continue
        handle = str(post.get("handle") or "").strip().lstrip("@").lower()
        post_id = str(post.get("post_id") or "").strip()
        text = str(post.get("text") or "").strip()
        if not handle or not post_id or not text:
            continue
        source_key = f"ghostwriter:{handle}:{post_id}"
        exists = SentryQueue.query.filter_by(source=source_key).first()
        if exists:
            continue

        prompt = (
            "draft one x reply.\n"
            "rules: sovereign-aligned, witty/sharp, lowercase, <= 260 chars, subtle cta to protocol pulse, no emojis.\n"
            f"target @{handle}\n"
            f"post: {text[:500]}"
        )
        draft = ollama_runtime.generate(
            prompt=prompt,
            preferred_model="llama3.1",
            options={"temperature": 0.55, "num_predict": 120},
            timeout=9,
        )
        if not draft:
            draft = "strong signal. market reads this wrong. protocol pulse has the cleaner map."
        payload = f"@{handle} {draft.strip()}"
        row = SentryQueue(
            content=payload[:3000],
            platforms_json=json.dumps(["x"]),
            status="draft",
            dry_run=True,
            source=source_key,
            created_by=None,
        )
        db.session.add(row)
        created += 1
    if created:
        db.session.commit()
    try:
        update_status("ghostwriter", {"last_run": datetime.utcnow().isoformat(), "scanned": scanned, "drafted": created})
    except Exception:
        pass
    return {"scanned": scanned, "drafted": created}


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
                    bol_handles = _load_bol_handles()
                    x_result = run_x_sentry_cycle(handles=bol_handles)
                    n_result = run_nostr_sentry_cycle()
                    x_result["nostr_fetched"] = int(n_result.get("fetched", 0))
                    x_result["nostr_drafted"] = int(n_result.get("drafted", 0))
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
                    mega_events = w_result.get("mega_events") or []
                    if mega_events:
                        from services.web_push_service import web_push_service
                        for event in mega_events:
                            usd = float(event.get("usd_value") or 0)
                            btc = float(event.get("btc_amount") or 0)
                            if usd >= 100_000_000 or btc >= 2500:
                                msg = (
                                    f"Whale Move Detected: {btc:,.0f} BTC moved to cold storage. "
                                    "the exit window is narrowing."
                                )
                                push_result = web_push_service.notify_sovereign_whale(
                                    btc_amount=btc,
                                    message=msg,
                                    txid=(event.get("txid") or ""),
                                )
                                logging.info("whale push dispatch: %s", push_result)
                except Exception:
                    logging.exception("whale web-push dispatch failed")
                try:
                    from services.matty_ice_engagement import matty_ice_agent

                    if is_enabled("ENABLE_MATTY_ICE_ENGAGEMENT"):
                        matty_result = matty_ice_agent.run_cycle()
                        if (matty_result.get("replies") or []):
                            signal_logger.emit("sentry", "matty ice engaged | live alpha reply dropped.")
                            logging.info("matty-ice cycle result: %s", matty_result)
                except Exception:
                    logging.exception("matty-ice cycle failed")
                try:
                    sentinel_brief = run_deep_context_scan(w_result)
                    brief_row = sentinel_brief.get("brief") or {}
                    focus = ((brief_row.get("urgent_events") or [])[:1] or ["market structure"])[0]
                    signal_logger.emit("signal", f"sentinel brief refreshed | focus: {focus[:120]}")
                except Exception:
                    logging.exception("sentinel deep context scan failed")
                try:
                    gw_result = run_ghostwriter_autodraft(handles=_load_bol_handles(), max_drafts=60)
                    if int(gw_result.get("drafted", 0)) > 0:
                        signal_logger.emit("sentry", f"ghostwriter queued {int(gw_result.get('drafted', 0))} sharp drafts.")
                except Exception:
                    logging.exception("ghostwriter autodraft failed")
                try:
                    from services.media_generator import media_generator
                    media_result = media_generator.maybe_render_from_latest_brief()
                    if media_result.get("rendered"):
                        signal_logger.emit("signal", "media factory shipped daily pulse render on gpu 1.")
                except Exception:
                    logging.exception("media generator run failed")
                try:
                    from services.nostr_broadcaster import nostr_broadcaster
                    retry_result = nostr_broadcaster.retry_pending()
                    if int(retry_result.get("retried", 0)) > 0:
                        signal_logger.emit("signal", f"nostr retry sweep completed | retried={retry_result.get('retried')}.")
                except Exception:
                    logging.exception("nostr retry sweep failed")
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
