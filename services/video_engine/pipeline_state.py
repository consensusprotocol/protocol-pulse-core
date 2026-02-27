"""
PIPELINE STATE
===============
SQLite-backed state machine for the intelligence pipeline.
Enables crash recovery, resume, audit trail, and analytics.

Tables:
  - runs: Pipeline run metadata and status
  - channel_scans: Per-channel scan status within a run
  - highlights: All analyzed highlights with scores
  - distributions: Track what was distributed where
"""

import sqlite3
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum

logger = logging.getLogger("PipelineState")

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "video_engine" / "pipeline_state.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


class RunStage(str, Enum):
    STARTED = "started"
    SCANNING = "scanning"
    ANALYZING = "analyzing"
    SELECTING = "selecting"
    PRODUCING = "producing"
    DISTRIBUTING = "distributing"
    COMPLETE = "complete"
    FAILED = "failed"


class ChannelStage(str, Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    TRANSCRIBING = "transcribing"
    ANALYZING = "analyzing"
    COMPLETE = "complete"
    SKIPPED = "skipped"
    FAILED = "failed"


def _get_conn() -> sqlite3.Connection:
    """Get a database connection with row factory."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Initialize database tables."""
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT PRIMARY KEY,
            date TEXT NOT NULL,
            stage TEXT NOT NULL DEFAULT 'started',
            channels_total INTEGER DEFAULT 0,
            channels_scanned INTEGER DEFAULT 0,
            highlights_found INTEGER DEFAULT 0,
            clips_selected INTEGER DEFAULT 0,
            videos_produced INTEGER DEFAULT 0,
            shorts_produced INTEGER DEFAULT 0,
            error TEXT,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            metadata TEXT DEFAULT '{}'
        );

        CREATE TABLE IF NOT EXISTS channel_scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            channel_name TEXT NOT NULL,
            channel_id TEXT NOT NULL,
            stage TEXT NOT NULL DEFAULT 'pending',
            video_id TEXT,
            video_title TEXT,
            transcript_chars INTEGER DEFAULT 0,
            hook_score INTEGER,
            error TEXT,
            started_at TEXT,
            completed_at TEXT,
            FOREIGN KEY (run_id) REFERENCES runs(run_id)
        );

        CREATE TABLE IF NOT EXISTS highlights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            channel_name TEXT NOT NULL,
            video_id TEXT NOT NULL,
            video_title TEXT,
            start_time REAL,
            end_time REAL,
            key_quote TEXT,
            hook_score INTEGER NOT NULL DEFAULT 0,
            themes TEXT DEFAULT '[]',
            tweet_text TEXT,
            summary TEXT,
            narrator_intro TEXT,
            vertical_caption TEXT,
            selected_for_video INTEGER DEFAULT 0,
            clip_path TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (run_id) REFERENCES runs(run_id)
        );

        CREATE TABLE IF NOT EXISTS distributions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            platform TEXT NOT NULL,
            content_type TEXT NOT NULL,
            filename TEXT,
            url TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            error TEXT,
            distributed_at TEXT,
            FOREIGN KEY (run_id) REFERENCES runs(run_id)
        );

        CREATE INDEX IF NOT EXISTS idx_scans_run ON channel_scans(run_id);
        CREATE INDEX IF NOT EXISTS idx_highlights_run ON highlights(run_id);
        CREATE INDEX IF NOT EXISTS idx_highlights_score ON highlights(hook_score DESC);
        CREATE INDEX IF NOT EXISTS idx_distributions_run ON distributions(run_id);
    """)
    conn.commit()
    conn.close()


# Initialize on import
init_db()


# --- Run Management ---

def create_run(run_id: str, date: str, channels_total: int) -> str:
    """Create a new pipeline run."""
    conn = _get_conn()
    conn.execute(
        "INSERT INTO runs (run_id, date, stage, channels_total, started_at) VALUES (?, ?, ?, ?, ?)",
        (run_id, date, RunStage.STARTED, channels_total, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()
    logger.info(f"Created run: {run_id} ({channels_total} channels)")
    return run_id


def update_run(run_id: str, **kwargs):
    """Update run metadata."""
    conn = _get_conn()
    sets = []
    vals = []
    for key, value in kwargs.items():
        sets.append(f"{key} = ?")
        vals.append(value)
    vals.append(run_id)

    if sets:
        conn.execute(f"UPDATE runs SET {', '.join(sets)} WHERE run_id = ?", vals)
        conn.commit()
    conn.close()


def complete_run(run_id: str, error: str = None):
    """Mark a run as complete or failed."""
    stage = RunStage.FAILED if error else RunStage.COMPLETE
    conn = _get_conn()
    conn.execute(
        "UPDATE runs SET stage = ?, completed_at = ?, error = ? WHERE run_id = ?",
        (stage, datetime.utcnow().isoformat(), error, run_id)
    )
    conn.commit()
    conn.close()


def get_run(run_id: str) -> Optional[Dict]:
    """Get run details."""
    conn = _get_conn()
    row = conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_recent_runs(limit: int = 10) -> List[Dict]:
    """Get recent pipeline runs."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM runs ORDER BY started_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# --- Channel Scan Management ---

def add_channel_scan(run_id: str, channel_name: str, channel_id: str) -> int:
    """Add a channel to be scanned in this run."""
    conn = _get_conn()
    cursor = conn.execute(
        "INSERT INTO channel_scans (run_id, channel_name, channel_id, started_at) VALUES (?, ?, ?, ?)",
        (run_id, channel_name, channel_id, datetime.utcnow().isoformat())
    )
    scan_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return scan_id


def update_channel(run_id: str, channel_name: str, **kwargs):
    """Update a channel scan status."""
    conn = _get_conn()
    sets = []
    vals = []
    for key, value in kwargs.items():
        sets.append(f"{key} = ?")
        vals.append(value)
    vals.extend([run_id, channel_name])

    if sets:
        conn.execute(
            f"UPDATE channel_scans SET {', '.join(sets)} WHERE run_id = ? AND channel_name = ?",
            vals
        )
        conn.commit()
    conn.close()


def get_incomplete_channels(run_id: str) -> List[Dict]:
    """Get channels that haven't completed scanning."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM channel_scans WHERE run_id = ? AND stage NOT IN ('complete', 'skipped', 'failed')",
        (run_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_completed_channels(run_id: str) -> List[Dict]:
    """Get successfully completed channel scans."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM channel_scans WHERE run_id = ? AND stage = 'complete'",
        (run_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# --- Highlight Management ---

def save_highlight(run_id: str, highlight: Dict) -> int:
    """Save an analyzed highlight."""
    conn = _get_conn()
    cursor = conn.execute(
        """INSERT INTO highlights
           (run_id, channel_name, video_id, video_title, start_time, end_time,
            key_quote, hook_score, themes, tweet_text, summary, narrator_intro,
            vertical_caption, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            run_id,
            highlight.get("channel_name", ""),
            highlight.get("video_id", ""),
            highlight.get("video_title", ""),
            highlight.get("start_time", 0),
            highlight.get("end_time", 0),
            highlight.get("key_quote", ""),
            highlight.get("hook_score", 0),
            json.dumps(highlight.get("themes", [])),
            highlight.get("tweet_text", ""),
            highlight.get("summary", ""),
            highlight.get("narrator_intro", ""),
            highlight.get("vertical_caption", ""),
            datetime.utcnow().isoformat()
        )
    )
    highlight_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return highlight_id


def mark_selected(run_id: str, video_ids: List[str]):
    """Mark highlights as selected for video production."""
    conn = _get_conn()
    for vid in video_ids:
        conn.execute(
            "UPDATE highlights SET selected_for_video = 1 WHERE run_id = ? AND video_id = ?",
            (run_id, vid)
        )
    conn.commit()
    conn.close()


def get_highlights(run_id: str, min_score: int = 0) -> List[Dict]:
    """Get highlights for a run, optionally filtered by minimum score."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM highlights WHERE run_id = ? AND hook_score >= ? ORDER BY hook_score DESC",
        (run_id, min_score)
    ).fetchall()
    conn.close()
    results = []
    for r in rows:
        d = dict(r)
        d["themes"] = json.loads(d.get("themes", "[]"))
        results.append(d)
    return results


# --- Distribution Tracking ---

def add_distribution(run_id: str, platform: str, content_type: str,
                     filename: str = None) -> int:
    """Record a distribution attempt."""
    conn = _get_conn()
    cursor = conn.execute(
        "INSERT INTO distributions (run_id, platform, content_type, filename, distributed_at) VALUES (?, ?, ?, ?, ?)",
        (run_id, platform, content_type, filename, datetime.utcnow().isoformat())
    )
    dist_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return dist_id


def update_distribution(dist_id: int, status: str, url: str = None, error: str = None):
    """Update distribution status."""
    conn = _get_conn()
    conn.execute(
        "UPDATE distributions SET status = ?, url = ?, error = ? WHERE id = ?",
        (status, url, error, dist_id)
    )
    conn.commit()
    conn.close()


def get_distributions(run_id: str) -> List[Dict]:
    """Get all distributions for a run."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM distributions WHERE run_id = ? ORDER BY distributed_at",
        (run_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# --- Analytics ---

def get_daily_stats(date: str) -> Dict:
    """Get aggregate stats for a given date."""
    conn = _get_conn()
    run = conn.execute(
        "SELECT * FROM runs WHERE date = ? ORDER BY started_at DESC LIMIT 1",
        (date,)
    ).fetchone()

    if not run:
        conn.close()
        return {"date": date, "status": "no_run"}

    run_id = run["run_id"]
    highlights = conn.execute(
        "SELECT COUNT(*) as total, AVG(hook_score) as avg_score, MAX(hook_score) as max_score "
        "FROM highlights WHERE run_id = ?",
        (run_id,)
    ).fetchone()

    distributions = conn.execute(
        "SELECT platform, status, COUNT(*) as count FROM distributions "
        "WHERE run_id = ? GROUP BY platform, status",
        (run_id,)
    ).fetchall()

    conn.close()

    return {
        "date": date,
        "run_id": run_id,
        "stage": run["stage"],
        "channels_scanned": run["channels_scanned"],
        "highlights_total": highlights["total"] if highlights else 0,
        "avg_score": round(highlights["avg_score"], 1) if highlights and highlights["avg_score"] else 0,
        "max_score": highlights["max_score"] if highlights else 0,
        "distributions": [dict(d) for d in distributions]
    }
