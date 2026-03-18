"""
spaces_state.py — SQLite-backed idempotent state machine for X Spaces.

States: discovered -> downloading -> transcribed -> summarized -> injected -> published
Each state is a timestamp column. NULL = not yet reached.
Prevents cron races. Atomic upsert via INSERT ... ON CONFLICT.
"""

import os
import sqlite3
import threading
from datetime import datetime, timezone

STATE_ORDER = ["discovered", "downloaded", "transcribed", "summarized", "injected", "published"]

_ALL_COLUMNS = [
    "space_id", "title", "host", "url", "started_at", "ended_at",
    "transcript_source", "transcript_word_count", "transcript_quality_score",
    "impact_score", "discovered_at", "downloaded_at", "transcribed_at",
    "summarized_at", "injected_at", "published_at", "error",
]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS spaces (
    space_id TEXT PRIMARY KEY,
    title TEXT,
    host TEXT,
    url TEXT,
    started_at TEXT,
    ended_at TEXT,
    transcript_source TEXT,
    transcript_word_count INTEGER DEFAULT 0,
    transcript_quality_score REAL DEFAULT 0.0,
    impact_score INTEGER DEFAULT 0,
    discovered_at TEXT,
    downloaded_at TEXT,
    transcribed_at TEXT,
    summarized_at TEXT,
    injected_at TEXT,
    published_at TEXT,
    error TEXT,
    UNIQUE(space_id)
);
CREATE INDEX IF NOT EXISTS idx_spaces_discovered ON spaces(discovered_at);
CREATE INDEX IF NOT EXISTS idx_spaces_downloaded ON spaces(downloaded_at);
CREATE INDEX IF NOT EXISTS idx_spaces_transcribed ON spaces(transcribed_at);
CREATE INDEX IF NOT EXISTS idx_spaces_injected ON spaces(injected_at);
CREATE INDEX IF NOT EXISTS idx_spaces_error ON spaces(error);
"""

from pathlib import Path as _Path

_BASE_DIR = _Path(os.environ.get("PP_BASE_DIR", _Path(__file__).parent.parent))
DEFAULT_DB_PATH = str(_BASE_DIR / "data" / "spaces_state.db")


class SpaceStateDB:
    def __init__(self, db_path=None):
        self.db_path = db_path or DEFAULT_DB_PATH
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._lock = threading.Lock()
        self.conn = sqlite3.connect(self.db_path, timeout=10, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    def upsert(self, space_id, **kwargs):
        """Atomic insert-or-update. COALESCE preserves existing non-null values."""
        kwargs["space_id"] = space_id
        values = [kwargs.get(col) for col in _ALL_COLUMNS]
        update_cols = _ALL_COLUMNS[1:]
        update_clause = ", ".join(
            f"{col} = COALESCE(excluded.{col}, spaces.{col})"
            for col in update_cols
        )
        placeholders = ", ".join("?" for _ in _ALL_COLUMNS)
        col_names = ", ".join(_ALL_COLUMNS)
        with self._lock:
            self.conn.execute(
                f"INSERT INTO spaces ({col_names}) VALUES ({placeholders}) "
                f"ON CONFLICT(space_id) DO UPDATE SET {update_clause}",
                values,
            )
            self.conn.commit()

    def get(self, space_id):
        """Get a space record by ID. Returns dict or None."""
        row = self.conn.execute(
            "SELECT * FROM spaces WHERE space_id = ?", (space_id,)
        ).fetchone()
        if row is None:
            return None
        return dict(row)

    def get_pending(self, state):
        """Return spaces where {state}_at IS NULL and previous state IS NOT NULL.

        e.g. get_pending("transcribed") = downloaded but not yet transcribed.
        """
        state_col = f"{state}_at"
        idx = STATE_ORDER.index(state) if state in STATE_ORDER else -1
        if idx <= 0:
            # For "discovered" or unknown: return where discovered_at is set but state is not
            return self._query_pending(state_col, "discovered_at")

        prev_state = STATE_ORDER[idx - 1]
        prev_col = f"{prev_state}_at"
        return self._query_pending(state_col, prev_col)

    def _query_pending(self, state_col, prev_col):
        rows = self.conn.execute(
            f"SELECT * FROM spaces WHERE {state_col} IS NULL AND {prev_col} IS NOT NULL"
        ).fetchall()
        return [dict(r) for r in rows]

    def mark(self, space_id, state):
        """Set {state}_at = now() for the given space. Creates row if missing via upsert."""
        col = f"{state}_at"
        allowed = {"discovered", "downloaded", "transcribed", "summarized", "injected", "published"}
        if state not in allowed:
            raise ValueError(f"Unknown state: {state}")
        self.upsert(space_id, **{col: datetime.now(timezone.utc).isoformat()})

    def needs_processing(self, space_id, state):
        """Return True if space exists but hasn't reached this state yet."""
        record = self.get(space_id)
        if record is None:
            return False
        col = f"{state}_at"
        return record.get(col) is None

    def get_injected_ids(self):
        """Return set of space_ids where injected_at IS NOT NULL."""
        rows = self.conn.execute(
            "SELECT space_id FROM spaces WHERE injected_at IS NOT NULL"
        ).fetchall()
        return {r[0] for r in rows}

    def close(self):
        self.conn.close()
