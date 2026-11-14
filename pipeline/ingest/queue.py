"""pipeline/ingest/queue.py: the durable queue (SQLite, WAL, one connection behind a lock).

channels  the per-channel last-seen ledger: last poll / success, listing source, ETag / Last-Modified, errors, backoff
videos    one row per video id ever listed, with its state (STATES) and the time it is next due
calls     every model attempt (role, back-end, model, kind, latency, tokens, dollars): live numbers and spend
events    every state change and notable fact, append-only
"""
import json
import os
import sqlite3
import threading
import time

from . import config

DISCOVERED, PROBE_RETRY, SEEN_OLD = "discovered", "probe_retry", "seen_old"
SHORT, UPCOMING, LIVE, CAPTIONS_PENDING = "short", "upcoming_waiting", "live_waiting", "captions_pending"
NO_CAPTIONS, TOO_LONG, UNAVAILABLE, DUPLICATE, OPTOUT = "no_captions", "too_long", "unavailable", "duplicate", \
    "excluded_optout"
TRANSCRIBED, MINING, MINE_WAIT, MINED, MINED_PARTIAL = "transcribed", "mining", "mine_waiting", "mined", \
    "mined_partial"
PROBING = "probing"

FETCH_DUE = (DISCOVERED, PROBE_RETRY, UPCOMING, LIVE, CAPTIONS_PENDING, UNAVAILABLE)
MINE_DUE = (TRANSCRIBED, MINE_WAIT, MINED_PARTIAL)      # a partial video stays retryable (integrator B2)
TERMINAL = (SEEN_OLD, SHORT, NO_CAPTIONS, TOO_LONG, DUPLICATE, OPTOUT, MINED)

SCHEMA = """
CREATE TABLE IF NOT EXISTS channels (
  channel_id TEXT PRIMARY KEY, display_name TEXT, slug TEXT,
  last_poll_at TEXT, last_ok_at TEXT, last_source TEXT, etag TEXT, last_modified TEXT,
  consecutive_errors INTEGER NOT NULL DEFAULT 0, backoff_until REAL NOT NULL DEFAULT 0, last_error TEXT,
  newest_published TEXT, listed INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS videos (
  video_id TEXT PRIMARY KEY, channel_id TEXT NOT NULL, title TEXT,
  discovered_at TEXT NOT NULL, discovered_ts REAL NOT NULL, discovered_via TEXT,
  listing_ts REAL, listing_live_status TEXT, listing_duration REAL, listing_url TEXT,
  published_at TEXT, published_ts REAL, published_source TEXT, media_type TEXT, live_status TEXT, duration REAL,
  state TEXT NOT NULL, state_at TEXT NOT NULL, next_at REAL NOT NULL DEFAULT 0, tries INTEGER NOT NULL DEFAULT 0,
  mine_tries INTEGER NOT NULL DEFAULT 0, reason TEXT,
  transcript_sha256 TEXT, transcript_method TEXT, transcribed_at TEXT, transcribed_ts REAL,
  mined_at TEXT, mined_ts REAL, miners TEXT, moments INTEGER, windows INTEGER, windows_screened INTEGER,
  windows_failed INTEGER, mine_cost_usd REAL, duplicate_of TEXT, title_canon TEXT, text_fp TEXT,
  first_sight INTEGER NOT NULL DEFAULT 0);
CREATE INDEX IF NOT EXISTS videos_due ON videos(state, next_at);
CREATE INDEX IF NOT EXISTS videos_channel ON videos(channel_id, published_ts);
CREATE INDEX IF NOT EXISTS videos_dup ON videos(title_canon);
CREATE INDEX IF NOT EXISTS videos_fp ON videos(text_fp);
CREATE TABLE IF NOT EXISTS calls (
  id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL, ts REAL NOT NULL, role TEXT, backend TEXT, model TEXT,
  provider TEXT, video_id TEXT, win TEXT, attempt INTEGER, kind TEXT, http_status INTEGER, latency_s REAL,
  prompt_tokens INTEGER, completion_tokens INTEGER, cost_usd REAL, error TEXT);
CREATE INDEX IF NOT EXISTS calls_ts ON calls(ts);
CREATE INDEX IF NOT EXISTS calls_video ON calls(video_id);
CREATE INDEX IF NOT EXISTS calls_backend ON calls(backend, cost_usd);
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL, ts REAL NOT NULL, video_id TEXT, channel_id TEXT,
  kind TEXT NOT NULL, detail TEXT);
CREATE INDEX IF NOT EXISTS events_ts ON events(ts);
CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT);
"""

VIDEO_FIELDS = ("title", "published_at", "published_ts", "published_source", "media_type", "live_status", "duration",
                "reason", "transcript_sha256", "transcript_method", "transcribed_at", "transcribed_ts", "mined_at",
                "mined_ts", "miners", "moments", "windows", "windows_screened", "windows_failed", "mine_cost_usd",
                "duplicate_of", "title_canon", "text_fp", "tries", "mine_tries", "listing_url")


HOOK_COLUMNS = (("hook_ts", "REAL"), ("hook_rows", "INTEGER"), ("hook_cost_usd", "REAL"), ("hook_next_ts", "REAL"),
                ("hook_note", "TEXT"), ("hook_tries", "INTEGER"),
                ("episode_markers", "INTEGER"), ("episode_tpm", "REAL"))   # ruling 92: the turn measure, per video


class Queue:
    def __init__(self, path, clock=time.time):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.path, self.clock = path, clock
        self.db = sqlite3.connect(path, check_same_thread=False, timeout=30, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.lock = threading.RLock()
        with self.lock:
            self.db.execute("PRAGMA journal_mode=WAL")
            self.db.execute("PRAGMA synchronous=FULL")
            self.db.executescript(SCHEMA)
            cols = {r[1] for r in self.db.execute("PRAGMA table_info(videos)").fetchall()}
            if "first_sight" not in cols:          # queues created before the column (2026-11-12 03:26 ET)
                self.db.execute("ALTER TABLE videos ADD COLUMN first_sight INTEGER NOT NULL DEFAULT 0")
            for c, t in HOOK_COLUMNS:               # ruling 80 (2026-11-13): the hook pass's state, per video
                if c not in cols:
                    self.db.execute(f"ALTER TABLE videos ADD COLUMN {c} {t}")
            self.db.execute("CREATE INDEX IF NOT EXISTS videos_hook ON videos(state, published_ts)")   # hook_due

    def x(self, sql, args=()):
        with self.lock:
            return self.db.execute(sql, args)

    def rows(self, sql, args=()):
        with self.lock:
            return [dict(r) for r in self.db.execute(sql, args).fetchall()]

    # ── events / kv ──

    def event(self, kind, video_id=None, channel_id=None, **detail):
        self.x("INSERT INTO events(at, ts, video_id, channel_id, kind, detail) VALUES (?,?,?,?,?,?)",
               (config.iso(), self.clock(), video_id, channel_id, kind,
                json.dumps(detail, default=str)[:4000] if detail else None))

    def kv_get(self, k, default=None):
        r = self.rows("SELECT v FROM kv WHERE k=?", (k,))
        return json.loads(r[0]["v"]) if r else default

    def kv_set(self, k, v):
        self.x("INSERT INTO kv(k, v) VALUES (?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", (k, json.dumps(v)))

    # ── channels ──

    def channel(self, cid):
        r = self.rows("SELECT * FROM channels WHERE channel_id=?", (cid,))
        return r[0] if r else None

    def ensure_channel(self, c):
        self.x("INSERT OR IGNORE INTO channels(channel_id, display_name, slug) VALUES (?,?,?)",
               (c["channel_id"], c.get("display_name"), c.get("slug")))
        self.x("UPDATE channels SET display_name=?, slug=? WHERE channel_id=?",
               (c.get("display_name"), c.get("slug"), c["channel_id"]))

    def channel_update(self, cid, **f):
        if f:
            cols = ", ".join(f"{k}=?" for k in f)
            self.x(f"UPDATE channels SET {cols} WHERE channel_id=?", tuple(f.values()) + (cid,))

    # ── videos ──

    def video(self, vid):
        r = self.rows("SELECT * FROM videos WHERE video_id=?", (vid,))
        return r[0] if r else None

    def add_video(self, vid, cid, title, via, listing_ts=None, listing_live_status=None, listing_duration=None,
                  listing_url=None, state=DISCOVERED, reason=None, first_sight=False):
        """True when the id is new. A known id is never re-added (the last-seen ledger is the videos table).
        first_sight: listed in the channel's first listing (the backfill), not discovered as a new upload."""
        now = self.clock()
        with self.lock:
            cur = self.db.execute(
                "INSERT OR IGNORE INTO videos(video_id, channel_id, title, discovered_at, discovered_ts, discovered_via,"
                " listing_ts, listing_live_status, listing_duration, listing_url, state, state_at, next_at, reason,"
                " first_sight) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (vid, cid, title, config.iso(), now, via, listing_ts, listing_live_status, listing_duration,
                 listing_url, state, config.iso(), now, reason, 1 if first_sight else 0))
            new = cur.rowcount == 1
        if new:
            self.event("discovered", vid, cid, via=via, state=state, title=title, listing_ts=listing_ts,
                       live_status=listing_live_status)
        return new

    def set_state(self, vid, state, next_at=None, **f):
        bad = [k for k in f if k not in VIDEO_FIELDS]
        if bad:
            raise KeyError(f"unknown video fields {bad}")
        f = dict(f, state=state, state_at=config.iso(), next_at=self.clock() if next_at is None else next_at)
        cols = ", ".join(f"{k}=?" for k in f)
        self.x(f"UPDATE videos SET {cols} WHERE video_id=?", tuple(f.values()) + (vid,))
        self.event("state", vid, None, state=state, reason=f.get("reason"))

    def claim(self, vid, from_states, to_state):
        """Atomic transition: True only for the caller that moved it."""
        q = ",".join("?" * len(from_states))
        with self.lock:
            cur = self.db.execute(f"UPDATE videos SET state=?, state_at=? WHERE video_id=? AND state IN ({q})",
                                  (to_state, config.iso(), vid) + tuple(from_states))
            return cur.rowcount == 1

    def due(self, states, limit=50):
        q = ",".join("?" * len(states))
        return self.rows(f"SELECT * FROM videos WHERE state IN ({q}) AND next_at <= ? "
                         "ORDER BY COALESCE(published_ts, listing_ts, discovered_ts) DESC LIMIT ?",
                         tuple(states) + (self.clock(), limit))

    def hook_due(self, horizon_s, limit=50):
        """Ruling 80: mined videos published inside the last `horizon_s` (12 h) whose hook pass has not run, newest
        first; a pass that waited on an outage is due again at hook_next_ts."""
        now = self.clock()
        return self.rows(f"SELECT * FROM videos WHERE state IN (?, ?) AND hook_ts IS NULL AND COALESCE(hook_next_ts, 0) "
                         "<= ? AND published_ts >= ? ORDER BY published_ts DESC LIMIT ?",
                         (MINED, MINED_PARTIAL, now, now - horizon_s, limit))

    def set_hook(self, vid, **kw):
        bad = [k for k in kw if k not in dict(HOOK_COLUMNS)]
        if bad:
            raise ValueError(f"not hook columns: {bad}")
        cols = ", ".join(f"{k}=?" for k in kw)
        self.x(f"UPDATE videos SET {cols} WHERE video_id=?", tuple(kw.values()) + (vid,))

    def recover(self):
        """After a restart: a probe or a mining pass that was running is due again (cached replies make it free)."""
        n1 = self.x("UPDATE videos SET state=?, next_at=? WHERE state=?", (DISCOVERED, self.clock(), PROBING)).rowcount
        n2 = self.x("UPDATE videos SET state=?, next_at=? WHERE state=?", (TRANSCRIBED, self.clock(), MINING)).rowcount
        if n1 or n2:
            self.event("recover", None, None, probing=n1, mining=n2)
        return n1, n2

    def find_duplicate(self, vid, title_canon=None, duration=None, text_fp=None, tol=config.DUP_DURATION_TOL_S):
        """An EARLIER video (by discovery) with the same text fingerprint, or the same canonical title and a duration
        within tol seconds."""
        me = self.video(vid)
        before = me["discovered_ts"] if me else self.clock()
        if text_fp:
            r = self.rows("SELECT video_id FROM videos WHERE text_fp=? AND video_id<>? AND discovered_ts<=? "
                          "ORDER BY discovered_ts LIMIT 1", (text_fp, vid, before))
            if r:
                return r[0]["video_id"], "same transcript text fingerprint"
        if title_canon and duration:
            r = self.rows("SELECT video_id, duration FROM videos WHERE title_canon=? AND video_id<>? "
                          "AND discovered_ts<=? AND duration IS NOT NULL ORDER BY discovered_ts", (title_canon, vid, before))
            for x in r:
                if abs(float(x["duration"]) - float(duration)) <= tol:
                    return x["video_id"], f"same title, duration within {tol} s"
        return None, None

    # ── calls / spend ──

    def call(self, rec):
        u = rec.get("usage") or {}
        tag = rec.get("tag") or {}
        self.x("INSERT INTO calls(at, ts, role, backend, model, provider, video_id, win, attempt, kind, http_status,"
               " latency_s, prompt_tokens, completion_tokens, cost_usd, error) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
               (config.iso(), self.clock(), rec.get("role"), rec.get("backend"), rec.get("model"),
                str(rec.get("provider")) if rec.get("provider") is not None else None,
                tag.get("video_id") if isinstance(tag, dict) else None,
                json.dumps(tag.get("window")) if isinstance(tag, dict) and tag.get("window") is not None else None,
                rec.get("attempt"), rec.get("kind"), rec.get("http_status"), rec.get("latency_s"),
                u.get("prompt_tokens") or u.get("input_tokens"), u.get("completion_tokens") or u.get("output_tokens"),
                rec.get("cost_usd"), (rec.get("error") or "")[:500] or None))

    def spend_by_day(self, day):
        """{backend: dollars} for one UTC day (YYYY-MM-DD)."""
        rows = self.rows("SELECT backend, SUM(COALESCE(cost_usd,0)) AS usd FROM calls WHERE substr(at,1,10)=? "
                         "GROUP BY backend", (day,))
        return {r["backend"]: r["usd"] or 0.0 for r in rows}
