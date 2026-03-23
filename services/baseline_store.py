# services/baseline_store.py
"""
Rolling 30-day baseline SQLite store for convergence signal history.

Tables:
  signal_daily_values — per-signal daily snapshots
  pattern_events      — convergence pattern state transitions
  baseline_snapshots  — full signal dict snapshots

SQLite configuration:
  WAL mode:            concurrent reads during writes (gunicorn + sentinel)
  synchronous=NORMAL:  safe under WAL, faster than FULL (not financial ledger)
  busy_timeout=10000:  10s wait before OperationalError on lock contention
  check_same_thread=False: sentinel writes from asyncio background thread
"""

import json
import logging
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

logger = logging.getLogger(__name__)

# Path resolved from file location — no CWD dependency
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "baseline_store.db"


# ── Connection factory ────────────────────────────────────────────────────────

def _get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """
    Returns a fully configured SQLite connection.
    All PRAGMA settings applied on every connection open.
    WAL mode is idempotent — safe to set repeatedly.
    """
    conn = sqlite3.connect(
        str(db_path),
        timeout=10,               # seconds — Python-level lock wait
        check_same_thread=False,  # sentinel writes from non-main thread
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")    # safe under WAL, faster than FULL
    conn.execute("PRAGMA busy_timeout = 10000;")    # ms — redundant with timeout, but explicit
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


@contextmanager
def db_session(db_path: Path = DB_PATH) -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager: open connection, yield, commit or rollback, always close.
    Use this for ALL database access — never hold a connection outside this scope.
    """
    conn = _get_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── Schema ────────────────────────────────────────────────────────────────────

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS signal_daily_values (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       REAL    NOT NULL,
    signal_name     TEXT    NOT NULL,
    signal_value    TEXT    NOT NULL,
    confirmed       INTEGER NOT NULL DEFAULT 1,
    decay_weight    REAL    NOT NULL DEFAULT 1.0
);

CREATE INDEX IF NOT EXISTS idx_sdv_timestamp
    ON signal_daily_values (timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_sdv_signal_name
    ON signal_daily_values (signal_name, timestamp DESC);

CREATE TABLE IF NOT EXISTS pattern_events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       REAL    NOT NULL,
    pattern_name    TEXT    NOT NULL,
    from_state      TEXT    NOT NULL,
    to_state        TEXT    NOT NULL,
    signal_snapshot TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_pe_timestamp
    ON pattern_events (timestamp DESC);

CREATE TABLE IF NOT EXISTS baseline_snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       REAL    NOT NULL,
    signal_data     TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_bs_timestamp
    ON baseline_snapshots (timestamp DESC);
"""


class BaselineStore:
    """
    Rolling 30-day baseline store. Thread-safe via WAL + per-operation connections.
    sentinel.py writes; Flask/gunicorn workers read.
    """

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = Path(db_path) if not isinstance(db_path, Path) else db_path
        self._initialize_schema()
        self._retention_days = 30

    def _initialize_schema(self) -> None:
        with db_session(self.db_path) as conn:
            conn.executescript(SCHEMA_SQL)
        logger.info(f"BaselineStore schema initialized at {self.db_path}")

    def _connect(self) -> sqlite3.Connection:
        """Direct connection for testing (TEST 3 uses this)."""
        return _get_connection(self.db_path)

    # ── Writes (sentinel.py) ──────────────────────────────────────────────────

    def record_signal(
        self,
        signal_name: str,
        signal_value: Any,
        confirmed: bool,
        decay_weight: float,
        timestamp: Optional[float] = None,
    ) -> None:
        ts = timestamp or time.time()
        with db_session(self.db_path) as conn:
            conn.execute(
                """INSERT INTO signal_daily_values
                   (timestamp, signal_name, signal_value, confirmed, decay_weight)
                   VALUES (?, ?, ?, ?, ?)""",
                (ts, signal_name, json.dumps(signal_value), int(confirmed), decay_weight),
            )

    def record_pattern_event(
        self,
        pattern_name: str,
        from_state: str,
        to_state: str,
        signal_snapshot: List[Dict],
        timestamp: Optional[float] = None,
    ) -> None:
        ts = timestamp or time.time()
        with db_session(self.db_path) as conn:
            conn.execute(
                """INSERT INTO pattern_events
                   (timestamp, pattern_name, from_state, to_state, signal_snapshot)
                   VALUES (?, ?, ?, ?, ?)""",
                (ts, pattern_name, from_state, to_state, json.dumps(signal_snapshot)),
            )

    def record_snapshot(self, signal_data: Dict[str, Any], timestamp: Optional[float] = None) -> None:
        ts = timestamp or time.time()
        with db_session(self.db_path) as conn:
            conn.execute(
                "INSERT INTO baseline_snapshots (timestamp, signal_data) VALUES (?, ?)",
                (ts, json.dumps(signal_data)),
            )

    def purge_old_records(self) -> None:
        """Remove records older than retention window. Call periodically from sentinel."""
        cutoff = time.time() - (86400 * self._retention_days)
        with db_session(self.db_path) as conn:
            conn.execute("DELETE FROM signal_daily_values WHERE timestamp < ?", (cutoff,))
            conn.execute("DELETE FROM pattern_events WHERE timestamp < ?", (cutoff,))
            conn.execute("DELETE FROM baseline_snapshots WHERE timestamp < ?", (cutoff,))
        logger.debug(f"BaselineStore purged records older than {self._retention_days} days.")

    # ── Reads (Flask/gunicorn workers) ────────────────────────────────────────

    def get_30d_baseline(self) -> List[Dict]:
        cutoff = time.time() - (86400 * self._retention_days)
        with db_session(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT * FROM baseline_snapshots WHERE timestamp > ? ORDER BY timestamp DESC",
                (cutoff,),
            )
            rows = [dict(row) for row in cursor.fetchall()]
        if not rows:
            logger.warning("BaselineStore: get_30d_baseline returned empty result set.")
        return rows

    def get_recent_signals(self, signal_name: str, limit: int = 100) -> List[Dict]:
        with db_session(self.db_path) as conn:
            cursor = conn.execute(
                """SELECT * FROM signal_daily_values
                   WHERE signal_name = ?
                   ORDER BY timestamp DESC LIMIT ?""",
                (signal_name, limit),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_pattern_history(self, pattern_name: str, days: int = 7) -> List[Dict]:
        cutoff = time.time() - (86400 * days)
        with db_session(self.db_path) as conn:
            cursor = conn.execute(
                """SELECT * FROM pattern_events
                   WHERE pattern_name = ? AND timestamp > ?
                   ORDER BY timestamp DESC""",
                (pattern_name, cutoff),
            )
            return [dict(row) for row in cursor.fetchall()]
