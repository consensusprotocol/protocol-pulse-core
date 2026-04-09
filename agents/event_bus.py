#!/usr/bin/env python3
"""
event_bus.py - Sovereign Event Bus for Protocol Pulse Agent Fleet

File + SQLite based, zero external dependencies.
Agents emit events, other agents consume them.
Persistent state survives reboots.

Usage:
    from agents.event_bus import emit, consume, save_state, load_state, log_metric
"""
import sqlite3
import json
import os
import time
import logging
from datetime import datetime
from contextlib import contextmanager

logger = logging.getLogger("agent_bus")

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state", "agent_state.db")


@contextmanager
def _db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── Event Bus ────────────────────────────────────────────────────────────────

def emit(source, event_type, payload, target=None):
    """Agent emits an event. Target agents pick it up on next cycle."""
    with _db() as conn:
        conn.execute(
            "INSERT INTO agent_events (source_agent, target_agent, event_type, payload_json) VALUES (?,?,?,?)",
            (source, target, event_type, json.dumps(payload, default=str))
        )
    logger.info(f"EVENT: {source} -> {target or 'broadcast'}: {event_type}")


def consume(agent_name, event_types=None, limit=10):
    """Agent consumes pending events targeted at it (or broadcast)."""
    with _db() as conn:
        query = ("SELECT id, source_agent, event_type, payload_json, timestamp "
                 "FROM agent_events WHERE status = 'pending' "
                 "AND (target_agent = ? OR target_agent IS NULL)")
        params = [agent_name]
        if event_types:
            placeholders = ",".join("?" * len(event_types))
            query += f" AND event_type IN ({placeholders})"
            params.extend(event_types)
        query += f" ORDER BY timestamp ASC LIMIT {limit}"

        rows = conn.execute(query, params).fetchall()
        events = []
        for row in rows:
            conn.execute("UPDATE agent_events SET status='processing' WHERE id=?", (row["id"],))
            events.append({
                "id": row["id"],
                "source": row["source_agent"],
                "type": row["event_type"],
                "payload": json.loads(row["payload_json"]) if row["payload_json"] else {},
                "timestamp": row["timestamp"],
            })
    return events


def complete_event(event_id):
    """Mark event as completed."""
    with _db() as conn:
        conn.execute("UPDATE agent_events SET status='completed' WHERE id=?", (event_id,))


def fail_event(event_id, error=""):
    """Mark event as failed with error context."""
    with _db() as conn:
        conn.execute(
            "UPDATE agent_events SET status='failed', payload_json=json_set(payload_json, '$.error', ?) WHERE id=?",
            (str(error), event_id)
        )


def pending_count(agent_name=None):
    """Count pending events, optionally filtered by target agent."""
    with _db() as conn:
        if agent_name:
            row = conn.execute(
                "SELECT COUNT(*) FROM agent_events WHERE status='pending' AND (target_agent=? OR target_agent IS NULL)",
                (agent_name,)
            ).fetchone()
        else:
            row = conn.execute("SELECT COUNT(*) FROM agent_events WHERE status='pending'").fetchone()
    return row[0] if row else 0


# ── Persistent State ─────────────────────────────────────────────────────────

def save_state(agent_name, state, last_action="", self_eval=None, notes=""):
    """Save agent session state. Next run loads this via load_state()."""
    with _db() as conn:
        conn.execute(
            "INSERT INTO agent_sessions (agent_name, session_start, status, state_json, last_action, self_eval_score, self_eval_notes) "
            "VALUES (?, ?, 'completed', ?, ?, ?, ?)",
            (agent_name, datetime.now().isoformat(), json.dumps(state, default=str), last_action, self_eval, notes)
        )
    logger.info(f"STATE SAVED: {agent_name} eval={self_eval} action={last_action}")


def load_state(agent_name):
    """Load the most recent state for this agent. Returns {} if none."""
    with _db() as conn:
        row = conn.execute(
            "SELECT state_json, self_eval_score, self_eval_notes, last_action, session_start "
            "FROM agent_sessions WHERE agent_name=? ORDER BY id DESC LIMIT 1",
            (agent_name,)
        ).fetchone()
    if not row or not row["state_json"]:
        return {}
    state = json.loads(row["state_json"])
    state["_meta"] = {
        "last_eval": row["self_eval_score"],
        "last_notes": row["self_eval_notes"],
        "last_action": row["last_action"],
        "last_session": row["session_start"],
    }
    return state


def save_error(agent_name, error, context=""):
    """Save a failed session with error context for next run to recover from."""
    with _db() as conn:
        conn.execute(
            "INSERT INTO agent_sessions (agent_name, session_start, status, error_context, last_action, self_eval_score) "
            "VALUES (?, ?, 'failed', ?, ?, 0.0)",
            (agent_name, datetime.now().isoformat(), str(error), context)
        )
    logger.warning(f"ERROR SAVED: {agent_name}: {str(error)[:100]}")


def get_session_history(agent_name, limit=10):
    """Get recent session history for trend analysis."""
    with _db() as conn:
        rows = conn.execute(
            "SELECT session_start, status, self_eval_score, self_eval_notes, last_action "
            "FROM agent_sessions WHERE agent_name=? ORDER BY id DESC LIMIT ?",
            (agent_name, limit)
        ).fetchall()
    return [dict(r) for r in rows]


# ── Metrics ──────────────────────────────────────────────────────────────────

def log_metric(agent_name, metric, value, context=""):
    """Log a time-series metric for trend tracking."""
    with _db() as conn:
        conn.execute(
            "INSERT INTO agent_metrics (agent_name, metric_name, metric_value, context) VALUES (?,?,?,?)",
            (agent_name, metric, float(value), context)
        )


def get_metrics(agent_name, metric, limit=50):
    """Get recent metric values for trend analysis."""
    with _db() as conn:
        rows = conn.execute(
            "SELECT timestamp, metric_value, context FROM agent_metrics "
            "WHERE agent_name=? AND metric_name=? ORDER BY id DESC LIMIT ?",
            (agent_name, metric, limit)
        ).fetchall()
    return [dict(r) for r in rows]


def get_metric_avg(agent_name, metric, window_hours=24):
    """Get average metric value over a time window."""
    with _db() as conn:
        row = conn.execute(
            "SELECT AVG(metric_value) FROM agent_metrics "
            "WHERE agent_name=? AND metric_name=? "
            "AND timestamp > datetime('now', '-' || ? || ' hours')",
            (agent_name, metric, window_hours)
        ).fetchone()
    return row[0] if row and row[0] is not None else 0.0


# ── Dashboard ────────────────────────────────────────────────────────────────

def fleet_status():
    """Get status of all agents — for dashboard/monitoring."""
    with _db() as conn:
        agents = {}
        rows = conn.execute(
            "SELECT agent_name, MAX(id) as latest_id FROM agent_sessions GROUP BY agent_name"
        ).fetchall()
        for row in rows:
            latest = conn.execute(
                "SELECT * FROM agent_sessions WHERE id=?", (row["latest_id"],)
            ).fetchone()
            pending = conn.execute(
                "SELECT COUNT(*) FROM agent_events WHERE status='pending' AND (target_agent=? OR target_agent IS NULL)",
                (row["agent_name"],)
            ).fetchone()[0]
            agents[row["agent_name"]] = {
                "status": latest["status"],
                "last_session": latest["session_start"],
                "last_eval": latest["self_eval_score"],
                "last_action": latest["last_action"],
                "pending_events": pending,
            }
    return agents


if __name__ == "__main__":
    # Self-test
    print("=== Event Bus Self-Test ===")

    # Test emit + consume
    emit("test_source", "test_event", {"msg": "hello"}, target="test_target")
    events = consume("test_target", ["test_event"])
    assert len(events) == 1, f"Expected 1 event, got {len(events)}"
    assert events[0]["payload"]["msg"] == "hello"
    complete_event(events[0]["id"])
    print("  emit/consume/complete: PASS")

    # Test state
    save_state("test_agent", {"counter": 42}, last_action="test_run", self_eval=0.95, notes="all good")
    state = load_state("test_agent")
    assert state["counter"] == 42
    assert state["_meta"]["last_eval"] == 0.95
    print("  save/load state: PASS")

    # Test metrics
    log_metric("test_agent", "quality", 96.0, "v34 render")
    avg = get_metric_avg("test_agent", "quality", 24)
    assert avg == 96.0
    print("  log/get metrics: PASS")

    # Test fleet status
    status = fleet_status()
    assert "test_agent" in status
    print("  fleet_status: PASS")

    # Test error recovery
    save_error("test_agent", "disk full", "render step 7")
    history = get_session_history("test_agent", 5)
    assert history[0]["status"] == "failed"
    print("  error recovery: PASS")

    print("\n=== ALL TESTS PASSED ===")
    print(f"DB: {DB_PATH}")
    print(f"Fleet: {json.dumps(fleet_status(), indent=2)}")
