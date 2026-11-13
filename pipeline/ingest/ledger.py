"""pipeline/ingest/ledger.py: the append-only moment ledger and the packager's adapter.

append()  one locked O_APPEND write per video (every line of it), flushed and fsynced; lines are never rewritten. With
          stamp (the service), every line's mined.at is set under the lock, so the file is in mined.at order. Every
          line is checked first (line_problems): one bad line and nothing is written (ValueError). A torn tail left
          by a failed write (ENOSPC, EIO, a crash) is closed with a newline under the same lock before writing.
seal()    the same closing, on start; a torn line stays one unreadable line; readers skip and count unreadable lines
best_unused_moments(path, since, now, delivered_ids, ...)
          the read the packager makes (pp-selectid contract v0): lines mined at or after `since` or published inside the
          horizon (12 h), de-duplicated by moment_id (the latest line wins), minus EXPIRED moments (rulings 76 + 77: a
          moment is usable only within 12 h of its video's publish time, then never again; the row stays in this file
          as the receipt that it was said and seen), minus moments delivered in the previous 24 h,
          with the contract's exclusions pre-applied (never relaxed): hard risk flags (law L-u), altcoin / not about
          Bitcoin, a measured speaker change inside, re-uploads (L-v 3), opted-out or unregistered channels, a line
          whose ids no longer give its text under the current contract definitions (fail closed). Left to the packager,
          by the contract: eligibility.ok (re-judged with word timing) and speaker.turn_change_inside == false (needs
          diarisation; null = not measured).
"""
import fcntl
import json
import os
import re
from datetime import datetime, timedelta, timezone

from . import config, contract, mine

VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")       # a YouTube id: record_by_sha joins it into a path
REQUIRED = {"schema": str, "moment_id": str, "video_id": str, "channel_id": str, "channel_name": str,
            "published_at": str, "title": str, "transcript_sha256": str, "transcript_method": str, "timing": str,
            "words": list, "sentences": list, "text": str, "speaker": dict, "scores": dict, "names_person": bool,
            "risk": list, "topics": list, "reason": str, "eligibility": dict, "mined": dict}


def append(path, lines, stamp=None):
    """stamp: a callable giving the time written as every line's mined.at, taken under the lock (the file is then in
    mined.at order, exactly: freeze audit c1)."""
    if not lines:
        return 0
    for i, l in enumerate(lines):
        p = line_problems(l)
        if p:
            raise ValueError(f"line {i} ({(l or {}).get('moment_id') if isinstance(l, dict) else None}) is not a "
                             f"usable pp.moment/1 line: {'; '.join(p)}; nothing written")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd = os.open(path, os.O_RDWR | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        try:
            if stamp is not None:
                at = stamp()
                for l in lines:
                    l["mined"]["at"] = at
            data = "".join(json.dumps(l, ensure_ascii=False, sort_keys=True) + "\n" for l in lines).encode()
            size = os.fstat(fd).st_size
            if size and os.pread(fd, 1, size - 1) != b"\n":
                data = b"\n" + data                    # a torn tail: closed, so the first new line stays whole
            view = memoryview(data)
            while view:
                n = os.write(fd, view)
                view = view[n:]
            os.fsync(fd)
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)
    return len(lines)


def seal(path):
    """True when a torn tail was closed."""
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return False
    with open(path, "rb") as f:
        f.seek(-1, os.SEEK_END)
        if f.read(1) == b"\n":
            return False
    fd = os.open(path, os.O_WRONLY | os.O_APPEND)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        os.write(fd, b"\n")
        os.fsync(fd)
        fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)
    return True


def line_problems(l):
    """Why a parsed line is not a usable pp.moment/1 line ([] = usable)."""
    out = []
    if type(l) is not dict:
        return ["not an object"]
    for k, t in REQUIRED.items():
        if type(l.get(k)) is not t:
            out.append(f"{k} missing or not {t.__name__}")
    if out:
        return out
    if l["schema"] != contract.SCHEMA:
        out.append(f"schema {l['schema']!r}")
    if not VIDEO_ID.match(l["video_id"]):
        out.append(f"video_id {l['video_id'][:40]!r} is not a YouTube id")
    for k in ("words", "sentences"):
        v = l[k]
        if len(v) != 2 or any(type(x) is not int for x in v) or v[0] > v[1]:
            out.append(f"{k} {v!r}")
    if set(l["scores"]) != set(mine.AXES) or any(type(v) is not int or not 0 <= v <= 5 for v in l["scores"].values()):
        out.append("scores")
    if any(r not in mine.RISKS for r in l["risk"]):
        out.append("risk value")
    if not out and contract.moment_id(l["video_id"], l["transcript_sha256"], *l["words"]) != l["moment_id"]:
        out.append("moment_id does not match video|sha|w0|w1")
    return out


def _mined_at(raw):
    try:
        return _aware(json.loads(raw)["mined"]["at"])
    except (ValueError, KeyError, TypeError):
        return None


def offset_before(path, cutoff):
    """A byte offset at or before the first line mined at or after `cutoff` (aware datetime), by bisection over the
    file. Lines are in mined.at order: the service stamps mined.at under the append lock (append(stamp=...)); lines
    written before that stamp carry their pass's start, at most one mining pass (minutes) out of order, which the
    caller's one day of margin covers (a skipped line is then older than both `since` and the 72 h horizon:
    tests/ingest/test_ledger_coverage.py). Unreadable lines are stepped over; where no time can be read the bisection
    moves towards the start (a fuller read is never wrong, only slower)."""
    try:
        size = os.path.getsize(path)
    except OSError:
        return 0
    lo, hi = 0, size
    with open(path, "rb") as f:
        while hi - lo > (1 << 16):
            mid = (lo + hi) // 2
            f.seek(mid)
            f.readline()                                 # the rest of the line we landed in
            t = None
            while t is None:
                raw = f.readline()
                if not raw:
                    break
                t = _mined_at(raw)
            if t is None or t >= cutoff:
                hi = mid
            else:
                lo = mid
    return lo


def read(path, from_time=None):
    """(lines in file order, bad [(line number, why)]). from_time: skip the part of the file mined before it
    (offset_before); line numbers then count from that offset."""
    lines, bad = [], []
    try:
        f = open(path, "rb")
    except FileNotFoundError:
        return [], []
    with f:
        off = offset_before(path, from_time) if from_time is not None else 0
        if off:
            f.seek(off)
            f.readline()                                 # a partial line at the offset
        for n, raw in enumerate(f, 1):
            raw = raw.decode("utf-8", "replace")
            if not raw.strip():
                continue
            try:
                l = json.loads(raw)
            except ValueError as e:
                bad.append((n, f"unparseable: {e}"))
                continue
            p = line_problems(l)
            if p:
                bad.append((n, "; ".join(p)))
                continue
            lines.append(l)
    return lines, bad


def video_moment_ids(path, video_id, since):
    """The distinct moment ids of one video among the lines mined at or after `since` (aware datetime)."""
    return {l["moment_id"] for l in read(path, from_time=since)[0] if l["video_id"] == video_id}


def record_by_sha(store_root, video_id, sha):
    d = os.path.join(store_root, "transcripts", video_id)
    try:
        names = sorted(os.listdir(d))
    except OSError:
        return None
    for name in names:
        if name.startswith("transcript.") and name.endswith(".json"):
            try:
                with open(os.path.join(d, name)) as f:
                    rec = json.load(f)
            except (OSError, ValueError):
                continue
            if rec.get("transcript_sha256") == sha:
                return rec
    return None


def _aware(s):
    try:
        d = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return d if d.tzinfo else None
    except (TypeError, ValueError):
        return None


def expiry(l):
    """When a line's moment stops being usable (rulings 76 + 77): the EARLIER of its recorded `expires_at` and its
    publish time + 12 h (a line mined before the field existed has only the second; fail closed); None when neither
    is measured (such a line is refused anyway: its publish time is not measured)."""
    ts = [t for t in (config.aware(l.get("expires_at")), config.aware(config.expires_at(l.get("published_at"))))
          if t is not None]
    return min(ts) if ts else None


def best_unused_moments(path, since, now=None, delivered_ids=(), registry=None, optout=None, store_root=None,
                        horizon_h=config.EXPIRY_H, limit=None):
    """(moments best first, report). since / now: aware datetimes. registry: the channel registry list; optout: the
    opted-out channel ids. Either one left None is READ from its file (pipeline/channels.json, pipeline/optout.json):
    the exclusions are never skipped by default, and an unreadable opt-out file refuses the read (law L-j).
    store_root: where transcript records live (for re-deriving a line mined under other definitions; None = such a
    line is excluded)."""
    now = now or datetime.now(timezone.utc)
    if since.tzinfo is None or now.tzinfo is None:
        raise ValueError("since and now must be aware datetimes")
    if registry is None or optout is None:
        from . import watch
        if registry is None:
            registry, _ = watch.registry()
        if optout is None:
            optout, oerr = watch.optouts()
            if oerr:
                raise ValueError(f"opt-out list unreadable, read refused: {oerr}")
    # every line this read can return was mined at or after min(since, now - horizon): a line inside the horizon was
    # mined after its video was published. One day of margin for the interleaving of concurrent videos.
    cutoff = min(since, now - timedelta(hours=horizon_h)) - timedelta(days=1)
    lines, bad = read(path, from_time=cutoff)
    report = {"lines": len(lines), "bad_lines": len(bad), "bad": bad[:20], "excluded": {}, "drift_checked": 0,
              "expiry_h": config.EXPIRY_H}
    latest = {}
    for l in lines:
        mined_at, pub = _aware(l["mined"].get("at")), _aware(l["published_at"])
        if (mined_at and mined_at >= since) or (pub and pub >= now - timedelta(hours=horizon_h)):
            latest[l["moment_id"]] = l                          # the latest line wins
    enabled = None if registry is None else {c["channel_id"] for c in registry
                                             if c.get("enabled", True) and c.get("channel_id")}
    fp = None
    try:
        fp = contract.fingerprint()
    except Exception as e:
        report["contract"] = f"unavailable: {type(e).__name__}: {e}"
    delivered, optout = set(delivered_ids or ()), set(optout or ())
    out = []

    def drop(why):
        report["excluded"][why] = report["excluded"].get(why, 0) + 1

    for l in latest.values():
        flags = l.get("flags_ext") or {}
        src = l.get("source") or {}
        pub = _aware(l["published_at"])
        exp = expiry(l)
        if exp is not None and now >= exp:
            drop("expired (rulings 76 + 77: 12 h after its video's publish time)")
        elif l["moment_id"] in delivered:
            drop("delivered in the previous 24 h")
        elif pub is None or pub > now:
            drop("publish time not measured or in the future")
        elif l["channel_id"] in optout:
            drop("channel opted out")
        elif enabled is not None and l["channel_id"] not in enabled:
            drop("channel not enabled in the registry")
        elif any(r in mine.HARD_RISKS for r in l["risk"]):
            drop("hard exclusion flag (L-u)")
        elif flags.get("altcoin") is not False or flags.get("about_bitcoin") is not True:
            drop("altcoin or not about Bitcoin")
        elif l["speaker"].get("turn_change_inside") is True:
            drop("speaker change inside (caption marker)")
        elif src.get("duplicate_of"):
            drop("re-upload")
        elif fp is None:
            drop("contract definitions unavailable")
        elif l["mined"].get("contract_fp") != fp:
            report["drift_checked"] += 1
            rec = record_by_sha(store_root, l["video_id"], l["transcript_sha256"]) if store_root else None
            ok, why = contract.verify_line(l, rec) if rec else (False, "record not found")
            if not ok:
                drop(f"contract drift: {why}")
            else:
                out.append(l)
        else:
            out.append(l)
    out.sort(key=lambda l: (-mine.rank_score(l), l["moment_id"]))
    report["returned"] = len(out) if limit is None else min(limit, len(out))
    return (out if limit is None else out[:limit]), report
