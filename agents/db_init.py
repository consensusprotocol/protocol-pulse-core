#!/usr/bin/env python3
"""db_init.py — Idempotent schema init for the Sovereign Agent Fleet DB.

Mirrors the production schema at /home/ultron/protocol_pulse/agents/state/agent_state.db.
Called once from agent_runner.py startup so fresh worktrees / fresh clones never hit a
"no such table" error on the first emit.
"""
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state", "agent_state.db")


SCHEMA = """
CREATE TABLE IF NOT EXISTS agent_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL,
    session_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    session_end TIMESTAMP,
    status TEXT DEFAULT 'running',
    state_json TEXT,
    last_action TEXT,
    error_context TEXT,
    self_eval_score REAL,
    self_eval_notes TEXT
);

CREATE TABLE IF NOT EXISTS agent_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source_agent TEXT NOT NULL,
    target_agent TEXT,
    event_type TEXT NOT NULL,
    payload_json TEXT,
    status TEXT DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS agent_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    agent_name TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value REAL,
    context TEXT
);

CREATE TABLE IF NOT EXISTS episode_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    episode_date TEXT NOT NULL,
    episode_title TEXT,
    topics_covered TEXT,
    channels_featured TEXT,
    clips_used TEXT,
    btc_price TEXT,
    dominance TEXT,
    fear_greed TEXT,
    hashrate TEXT,
    cold_open_topic TEXT,
    narrative_theme TEXT,
    quality_score REAL,
    grade TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_events_pending
    ON agent_events(status, target_agent, timestamp);

CREATE INDEX IF NOT EXISTS idx_sessions_agent
    ON agent_sessions(agent_name, id DESC);

CREATE INDEX IF NOT EXISTS idx_metrics_agent
    ON agent_metrics(agent_name, metric_name, timestamp DESC);
"""


def init_db(db_path=DB_PATH):
    """Create tables if not present. Safe to call every startup."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=10)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()
    return db_path


if __name__ == "__main__":
    path = init_db()
    print(f"schema OK: {path}")
