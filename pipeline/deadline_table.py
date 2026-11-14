"""RULING 100 (orchestrator 12:16 ET Nov 14): DEADLINES FOLLOW THE MODEL, NOT ONE NUMBER. Per (model, verdict type) the
deadline is the recorded p90 of that pair's answered calls x FACTOR (1.5), floor FLOOR_S (60 s), ceiling CEIL_S (300 s),
recomputed from the records daily; ruling 99's "two misses in a row" is against THAT deadline.

- The records: this builder's recorded exchanges (providers.Router's record_dir: one JSON per ANSWERED call, with its
  role, back-end and seconds). A pair with fewer than MIN_N answered calls has no row, and its gateway's configured
  deadline stands (ruling 82's 120 s on Heimdall).
- The table lives in a JSON file with its computed_at; load() recomputes it when it is missing, unreadable or older
  than RECOMPUTE_S (a day); with no record dir it is computed (empty) and never saved over a good one. The Router
  applies a verdict pair's row only where a deadline applies today (the caller's, or the gateway's configured one:
  Heimdall), in place of that number; where none applies (Grok's second screen, a writer), none is added
  (providers.Router.effective_deadline).
- Measured at 12:2x ET Nov 14: deepseek's step A, 32 answers, median 166 s, p90 273 s -> 300 s (the ceiling); glm's step
  A, 3 answers, p90 39 s -> 60 s (the floor), which its 483-532 s runs still miss."""
import glob
import json
import math
import os
from datetime import datetime, timezone

STATE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "package", "proof",
                     "DEADLINE_TABLE.json")
FACTOR, FLOOR_S, CEIL_S = 1.5, 60.0, 300.0      # ruling 100
MIN_N = 3                                      # a pair needs this many answered calls for a row of its own
RECOMPUTE_S = 24 * 3600                        # ruling 100: "recomputed from the records daily"
RULE = "p90 of the pair's recorded answered calls x 1.5, floor 60 s, ceiling 300 s (ruling 100)"


def _iso(t):
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def _t(s):
    try:
        t = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return t if t.tzinfo is not None else None


def percentile(xs, q):
    """Linear interpolation between the closest ranks (numpy's default)."""
    xs = sorted(xs)
    k = (len(xs) - 1) * q
    lo, hi = math.floor(k), math.ceil(k)
    return xs[lo] if lo == hi else xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def compute(record_dir, now=None):
    """-> {"computed_at", "rule", "rows": {"<back-end>|<role>": {"n", "p50", "p90", "deadline_s"}}} from every recorded
    exchange in record_dir (a file that cannot be read, is not an object, or has no back-end, role or positive seconds,
    is skipped). No record_dir: no rows (never the current directory's files)."""
    now = now or datetime.now(timezone.utc)
    seconds = {}
    for p in glob.glob(os.path.join(record_dir, "*", "*.json")) if record_dir else ():
        try:
            with open(p) as f:
                r = json.load(f)
        except (OSError, ValueError):
            continue
        if not isinstance(r, dict):
            continue
        b, role, s = r.get("backend"), r.get("role"), r.get("seconds")
        if isinstance(b, str) and isinstance(role, str) and isinstance(s, (int, float)) and not isinstance(s, bool) \
                and math.isfinite(s) and s > 0:
            seconds.setdefault(f"{b}|{role}", []).append(float(s))
    rows = {}
    for key, xs in sorted(seconds.items()):
        if len(xs) < MIN_N:
            continue
        q = percentile(xs, 0.9)
        rows[key] = {"n": len(xs), "p50": round(percentile(xs, 0.5), 1), "p90": round(q, 1),
                     "deadline_s": round(min(CEIL_S, max(FLOOR_S, FACTOR * q)), 1)}
    return {"computed_at": _iso(now), "rule": RULE, "rows": rows}


def load(path=STATE, record_dir=None, now=None):
    """The table: the saved one while it is younger than RECOMPUTE_S, else computed again from record_dir and saved
    (a save that fails leaves the computed table in use). -> the table dict."""
    now = now or datetime.now(timezone.utc)
    try:
        with open(path) as f:
            t = json.load(f)
        at = _t(t.get("computed_at")) if isinstance(t, dict) else None
        if at is not None and 0 <= (now - at).total_seconds() < RECOMPUTE_S and isinstance(t.get("rows"), dict):
            return t
    except (OSError, ValueError):
        pass
    t = compute(record_dir, now)
    if not record_dir:                                   # nothing to compute from: never overwrite a saved table
        return t
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        tmp = f"{path}.{os.getpid()}.tmp"
        with open(tmp, "w") as f:
            json.dump(t, f, indent=1)
        os.replace(tmp, path)
    except OSError:
        pass
    return t


def deadline(table, backend, role):
    """The pair's own deadline in seconds, inside FLOOR_S..CEIL_S whatever the file says (a hand-edited or older table
    included: glm, audit 20261114_1246 C1), or None when the table has no row for it."""
    row = ((table or {}).get("rows") or {}).get(f"{backend}|{role}") if isinstance(table, dict) else None
    d = row.get("deadline_s") if isinstance(row, dict) else None
    if not (isinstance(d, (int, float)) and not isinstance(d, bool) and math.isfinite(d) and d > 0):
        return None
    return min(CEIL_S, max(FLOOR_S, float(d)))


def text(table, applies=None):
    """The table in one line, for STATE (ruling 100: "say the table on STATE once"); applies(key) keeps the rows a
    Router would use (the build passes the Heimdall verdict pairs)."""
    rows = {k: v for k, v in ((table or {}).get("rows") or {}).items() if applies is None or applies(k)}
    return "; ".join(f"{k.split('|')[0].split('/')[-1]} {k.split('|')[1]}: {v['deadline_s']:g} s (n {v['n']}, p50 "
                     f"{v['p50']:g}, p90 {v['p90']:g})" for k, v in sorted(rows.items()))
