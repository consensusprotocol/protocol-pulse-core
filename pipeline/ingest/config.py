"""pipeline/ingest/config.py: paths, constants and the store guard.

The store is a staging copy of the editorial transcript store (same layout as /home/ultron/protocol_pulse/data/editorial)
plus the ingest state. transcript_store reads its root from PP_EDITORIAL_STORE at import time, so it is imported only
through ts(), after the variable is set, and ts() checks the module really writes where this service writes.
"""
import os
import sys
from datetime import datetime, timedelta, timezone

PKG_DIR = os.path.dirname(os.path.abspath(__file__))
PIPELINE_DIR = os.path.dirname(PKG_DIR)
REPO = os.path.dirname(PIPELINE_DIR)
MAIN_TREE = "/home/ultron/protocol_pulse"
MAIN_STORE = os.path.join(MAIN_TREE, "data", "editorial")

if PIPELINE_DIR not in sys.path:            # the pipeline's own modules use flat imports (transcript_store, canon, ...)
    sys.path.insert(0, PIPELINE_DIR)

REGISTRY_PATH = os.path.join(PIPELINE_DIR, "channels.json")
OPTOUT_PATH = os.path.join(PIPELINE_DIR, "optout.json")          # PBX 02:35: an opt-out registry (channel ids)
PROVIDERS_PATH = os.path.join(PKG_DIR, "providers.json")
STATE_DOC = os.path.join(REPO, "docs", "audits", "parallel", "pp-ingest_STATE.md")

POLL_S = 600                 # every registered channel listed every ~10 min
POLL_JITTER_S = 60
YTDLP_CONCURRENCY = 3        # yt-dlp processes at once (listing, probe, captions)
LIST_N = 30                  # uploads listed per channel per poll
RSS_CANARY_S = 1800          # RSS answered 404 for every channel (2026-11-07, 2026-11-12): one canary per 30 min
VOD_MAX_S = 6 * 3600         # captions cost nothing to fetch; the selector keeps its own 3 h ceiling
CAPTION_DEADLINE_H = 48      # no English captions 48 h after publish: no_captions (the pipeline's Whisper can do it)
CAPTION_RETRY_S = (600, 1200, 2400, 4800)    # then every 2 h
LIVE_REPROBE_S = 1200
UPCOMING_REPROBE_S = 1800
DUP_DURATION_TOL_S = 2.0
EXPIRY_H = 12                # rulings 76 + 77 (2026-11-13): a moment is usable only within 12 h of its video's
                             # publish time, then never again; its row stays in the ledger (the receipt)
PURGE_SPEC = os.path.join(PKG_DIR, "purge.json")    # ruling 77: what the watcher's purge may delete, and what never


class StoreGuard(RuntimeError):
    pass


def now():
    return datetime.now(timezone.utc)


def iso(dt=None):
    return (dt or now()).isoformat()


def aware(s):
    """An ISO time with its zone, or None (a time without a zone is not a measured time: fail closed)."""
    try:
        d = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return d if d.tzinfo else None


def expires_at(published_at, hours=EXPIRY_H):
    """The moment of expiry of a video's moments (rulings 76 + 77): its publish time + 12 h; None when unknown."""
    d = aware(published_at)
    return None if d is None else (d + timedelta(hours=hours)).isoformat()


def store_root():
    return os.path.realpath(os.environ.get("PP_INGEST_STORE") or os.path.join(REPO, "data", "editorial"))


def check_store(root=None):
    """The service writes only to its own store. Inside the main tree only when the integrator says so."""
    root = os.path.realpath(root or store_root())
    main = os.path.realpath(MAIN_TREE)
    if (root == main or root.startswith(main + os.sep)) and os.environ.get("PP_INGEST_ALLOW_MAIN_STORE") != "1":
        raise StoreGuard(f"store {root} is inside the main tree {main}: refused (set PP_INGEST_ALLOW_MAIN_STORE=1 "
                         "only when the integrator wires this service into the main tree)")
    return root


def paths(root=None):
    root = check_store(root)
    ing = os.path.join(root, "ingest")
    return {
        "root": root,
        "transcripts": os.path.join(root, "transcripts"),
        "moments": os.path.join(root, "moments"),
        "ledger": os.path.join(root, "moments", "moment_ledger.jsonl"),
        "ingest": ing,
        "queue": os.path.join(ing, "queue.sqlite"),
        "replies": os.path.join(ing, "replies"),
        "replies_log": os.path.join(ing, "replies_log"),
        "live": os.path.join(ing, "live.json"),
        "coverage": os.path.join(ing, "coverage"),
        "notify": os.path.join(ing, "NOTIFY.txt"),
        "overrides": os.path.join(ing, "overrides.json"),
        "work": os.path.join(ing, "work"),
        "purge": os.path.join(ing, "purge"),
        "signal": os.path.join(ing, "down_signal.jsonl"),         # ruling 87: this watcher's evidence file
    }


_TS = None


def ts():
    """transcript_store bound to this service's store, or StoreGuard. Never a module writing somewhere else."""
    global _TS
    root = check_store()
    if _TS is None:
        prev = os.environ.get("PP_EDITORIAL_STORE")
        if "transcript_store" in sys.modules and os.path.realpath(sys.modules["transcript_store"].STORE_DIR) != root:
            raise StoreGuard("transcript_store was imported before the ingest store was bound "
                             f"(STORE_DIR {sys.modules['transcript_store'].STORE_DIR})")
        if prev and os.path.realpath(prev) != root:
            raise StoreGuard(f"PP_EDITORIAL_STORE={prev} differs from the ingest store {root}")
        os.environ["PP_EDITORIAL_STORE"] = root
        import transcript_store
        _TS = transcript_store
    if os.path.realpath(_TS.STORE_DIR) != root:
        raise StoreGuard(f"transcript_store writes to {_TS.STORE_DIR}, the ingest store is {root}")
    return _TS
