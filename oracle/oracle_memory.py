"""
Visitor memory system for Oracle.
Stores cross-session context in SQLite.
No PII stored — fingerprint hash only.
"""

import os, json, time, sqlite3, hashlib, logging
from pathlib import Path

logger = logging.getLogger("oracle_memory")
DB_PATH = Path(__file__).parent / "data" / "visitor_memory.db"
DB_PATH.parent.mkdir(exist_ok=True)


def _get_conn():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS visitor_memory (
            fingerprint     TEXT PRIMARY KEY,
            last_seen       INTEGER NOT NULL,
            session_count   INTEGER DEFAULT 1,
            personality     TEXT,
            session_summaries TEXT DEFAULT '[]',
            setup_device    TEXT,
            setup_step      INTEGER DEFAULT 0,
            topics_seen     TEXT DEFAULT '[]',
            products_shown  TEXT DEFAULT '[]',
            recent_turns    TEXT DEFAULT '[]'
        )
    """)
    conn.commit()
    # Migrate existing DB — add recent_turns if missing
    try:
        conn.execute("ALTER TABLE visitor_memory ADD COLUMN recent_turns TEXT DEFAULT '[]'")
        conn.commit()
    except Exception:
        pass  # Column already exists
    return conn


def make_fingerprint(ip: str, user_agent: str, visitor_token: str = "") -> str:
    """Create anonymous fingerprint from server + client signals."""
    raw = f"{ip}|{user_agent}|{visitor_token}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def load_visitor(fingerprint: str) -> dict | None:
    """Return visitor memory if exists and < 30 days old."""
    try:
        conn = _get_conn()
        row = conn.execute(
            "SELECT * FROM visitor_memory WHERE fingerprint = ?", (fingerprint,)
        ).fetchone()
        conn.close()
        if not row:
            return None
        # Expire after 30 days
        if time.time() - row[1] > 30 * 86400:
            return None
        cols = ["fingerprint", "last_seen", "session_count", "personality",
                "session_summaries", "setup_device", "setup_step",
                "topics_seen", "products_shown", "recent_turns"]
        data = dict(zip(cols, row))
        data["session_summaries"] = json.loads(data["session_summaries"] or "[]")
        data["topics_seen"] = json.loads(data["topics_seen"] or "[]")
        data["products_shown"] = json.loads(data["products_shown"] or "[]")
        data["recent_turns"] = json.loads(data.get("recent_turns") or "[]")
        return data
    except Exception as e:
        logger.warning(f"[MEMORY] load error: {e}")
        return None


def save_visitor(fingerprint: str, session_data: dict):
    """Upsert visitor memory after session ends or on update."""
    try:
        conn = _get_conn()
        existing = conn.execute(
            "SELECT session_count FROM visitor_memory WHERE fingerprint = ?",
            (fingerprint,)
        ).fetchone()
        count = (existing[0] + 1) if existing else 1
        conn.execute("""
            INSERT INTO visitor_memory
                (fingerprint, last_seen, session_count, personality,
                 session_summaries, setup_device, setup_step, topics_seen, products_shown,
                 recent_turns)
            VALUES (?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(fingerprint) DO UPDATE SET
                last_seen = excluded.last_seen,
                session_count = excluded.session_count,
                personality = excluded.personality,
                session_summaries = excluded.session_summaries,
                setup_device = excluded.setup_device,
                setup_step = excluded.setup_step,
                topics_seen = excluded.topics_seen,
                products_shown = excluded.products_shown,
                recent_turns = excluded.recent_turns
        """, (
            fingerprint,
            int(time.time()),
            count,
            session_data.get("personality", "AMIABLE"),
            json.dumps(session_data.get("session_summaries", [])[-3:]),
            session_data.get("setup_device"),
            session_data.get("setup_step", 0),
            json.dumps(list(set(session_data.get("topics_seen", [])))[-20:]),
            json.dumps(list(set(session_data.get("products_shown", [])))),
            json.dumps(session_data.get("recent_turns", [])[-3:])
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning(f"[MEMORY] save error: {e}")


def generate_session_summary(history: list, anthropic_key: str) -> str:
    """Summarize a conversation for long-term memory storage."""
    if not history or len(history) < 2:
        return ""
    try:
        import requests
        turns = "\n".join([
            f"{'User' if h['role']=='user' else 'Oracle'}: {h['content'][:100]}"
            for h in history[-8:]
        ])
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": anthropic_key, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json={"model": "claude-haiku-4-5-20251001", "max_tokens": 60,
                  "system": "Summarize this Bitcoin support conversation in 1-2 sentences, max 200 chars. Focus on what the user wanted and what was resolved.",
                  "messages": [{"role": "user", "content": turns}]},
            timeout=8
        )
        if resp.ok:
            return resp.json()["content"][0]["text"].strip()[:200]
    except Exception as e:
        logger.debug(f"[MEMORY] summary generation failed: {e}")
    return ""
