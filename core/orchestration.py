from __future__ import annotations

from datetime import datetime
from typing import Dict

from core.event_bus import emit_event


def run_cycle() -> Dict:
    """Centralized deterministic cycle orchestrator for intelligence lanes."""
    from scripts.intelligence_loop import run_x_sentry_cycle, run_nostr_sentry_cycle, run_whale_watcher_cycle

    started = datetime.utcnow().isoformat()
    x = run_x_sentry_cycle()
    n = run_nostr_sentry_cycle()
    w = run_whale_watcher_cycle()
    summary = {
        "started_at": started,
        "finished_at": datetime.utcnow().isoformat(),
        "sentry": {"fetched": int(x.get("fetched", 0)), "drafted": int(x.get("drafted", 0))},
        "nostr": {"fetched": int(n.get("fetched", 0)), "drafted": int(n.get("drafted", 0))},
        "whale": {"scanned": int(w.get("scanned", 0)), "inserted": int(w.get("inserted", 0)), "mega": int(w.get("mega_inserted", 0))},
    }
    emit_event(
        event_type="cycle_summary",
        source="orchestration.run_cycle",
        lane="system",
        severity="info",
        title="intelligence cycle summary",
        detail=f"sentry={summary['sentry']['drafted']} whale={summary['whale']['inserted']} nostr={summary['nostr']['drafted']}",
        payload=summary,
    )
    return summary


def emit_cycle_summary(x_result: Dict, n_result: Dict, w_result: Dict) -> Dict:
    summary = {
        "started_at": datetime.utcnow().isoformat(),
        "finished_at": datetime.utcnow().isoformat(),
        "sentry": {"fetched": int(x_result.get("fetched", 0)), "drafted": int(x_result.get("drafted", 0))},
        "nostr": {"fetched": int(n_result.get("fetched", 0)), "drafted": int(n_result.get("drafted", 0))},
        "whale": {"scanned": int(w_result.get("scanned", 0)), "inserted": int(w_result.get("inserted", 0)), "mega": int(w_result.get("mega_inserted", 0))},
    }
    emit_event(
        event_type="cycle_summary",
        source="orchestration.emit_cycle_summary",
        lane="system",
        severity="info",
        title="intelligence cycle summary",
        detail=f"sentry={summary['sentry']['drafted']} whale={summary['whale']['inserted']} nostr={summary['nostr']['drafted']}",
        payload=summary,
    )
    return summary

