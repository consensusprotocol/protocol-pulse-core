"""pipeline/ingest/batch.py: ruling 108 (orchestrator 21:22 ET Nov 14), the batch's money on pp-ingest's side.

One ledger holds everything every session spends on the pipeline (the builder keeps it). pp-ingest's spend goes to it
every hour as 'BATCH <n> ingest spend: $x (...)' FIRST on STATE line 1 (spend.write_batch_notice). The batch (its
name, its 24 h and pp-ingest's share, "mining and checks") is batch.json, read again whenever it changes: a new batch
is a data change, with no restart. Counted, from the batch's start to its latest whole hour (21:10, 22:10, ...: line 1
changes once an hour):
- every call the watcher made, from its call records (the queue's calls: mining, the hook pass, the flag checks with
  their calibration, ruling 87's probes, ruling 98's paid route; a cached reply is free), at the vendor's own figure
  where its replies carry one (providers.json cost_from_usage / cost_reported), else at the price table (said apart);
- an ABANDONED call (a timeout, or a call cut off after CUT_S in flight with no answer, a dropped connection: nothing
  booked) at the model's own rate (ruling 107: the model's reported dollars per prompt token x the prompt, the role's
  average on that model; the list price of the prompt until the model has 3 reported calls); an error the vendor
  answered (an HTTP status) books what it reported;
- pp-ingest's audits, from their cost ledger (tests/ingest/xllm_audit.py appends one record per review).
Ruling 98's paid route is held inside the share: share_left() is what the router's RoleCaps checks before a paid call
starts, counted to NOW (the check is live; only line 1's figure waits for the hour: audit b108 c1). Outside a batch (or with the batch file unreadable) nothing is left: the paid route spends nothing until the
next batch's money is set (the stricter reading of a money hold, ruling 106 (b)).
"""
import hashlib
import json
import math
import os
import re
import threading
from datetime import datetime
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
SPEC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "batch.json")
NAME_RE = re.compile(r"BATCH \d+")
USE = {"mine": "mining", "mine_paid": "mining", "hook": "hook pass", "spotlight": "hook pass",
       "flagcheck": "flag checks and calibration", "probe": "probes"}
ORDER = ("mining", "hook pass", "flag checks and calibration", "probes", "other")
MIN_REPORTED = 3                     # ruling 107: the list price of the prompt until the model has 3 reported calls
CUT_S = 30.0                         # a call that failed after this long in flight with no answer may have been billed
HOUR_S = 3600

_lock = threading.Lock()
_cache = {}


def _et_ts(s):
    return datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=ET).timestamp()


def _hm(ts, fmt="%H:%M ET"):
    return datetime.fromtimestamp(ts, ET).strftime(fmt)


def load(path=None):
    """The batch: {name, t0, t1, share_usd, share_of}; read again when the file changes. Raises (OSError, ValueError,
    KeyError, TypeError) when it cannot be read or holds no batch: every caller fails closed (nothing left to spend)."""
    path = path or SPEC
    with open(path, "rb") as f:                       # a few hundred bytes: read every time, keyed by its content (a
        raw = f.read()                                 # same-size edit inside one mtime tick is still seen: audit b108
    key = (path, hashlib.sha256(raw).hexdigest())      # c1)
    with _lock:
        if _cache.get("key") == key:
            return _cache["spec"]
    j = json.loads(raw.decode("utf-8"))
    name, share = j["name"], float(j["share_usd"])
    t0, t1 = _et_ts(j["start_et"]), _et_ts(j["end_et"])
    if not (isinstance(name, str) and NAME_RE.fullmatch(name)) or not t1 > t0 or not (math.isfinite(share) and
                                                                                       share >= 0):
        raise ValueError(f"{path} holds no batch (a name 'BATCH <n>', an end after the start, a finite share >= 0)")
    spec = {"name": name, "t0": t0, "t1": t1, "share_usd": share,
            "share_of": str(j.get("share_of") or "mining and checks")}
    with _lock:
        _cache.update(key=key, spec=spec)
    return spec


def _reports_cost(bcfg):
    """A back-end whose replies carry their own cost (providers.json: cost_from_usage, or cost_reported)."""
    return bool(bcfg.get("cost_from_usage") or bcfg.get("cost_reported"))


class History:
    """Ruling 107's basis for the abandoned calls of one count, read in TWO grouped queries (whatever the number of
    models and roles: audit b108 c2), only when the count holds an abandoned call, from the calls recorded before
    `until` (the end of the hour counted: an hour's figure never moves once it is out)."""

    def __init__(self, q, until):
        self.rate = {r["model"]: (float(r["c"]), float(r["p"]), int(r["k"])) for r in q.rows(
            "SELECT model, SUM(cost_usd) AS c, SUM(prompt_tokens) AS p, COUNT(*) AS k FROM calls WHERE cost_usd > 0 "
            "AND prompt_tokens > 0 AND ts < ? GROUP BY model", (until,))}
        self.sums = {(r["model"], r["role"]): (float(r["s"]), int(r["n"])) for r in q.rows(
            "SELECT model, role, SUM(prompt_tokens) AS s, COUNT(*) AS n FROM calls WHERE prompt_tokens > 0 AND ts < ? "
            "GROUP BY model, role", (until,))}

    def _avg(self, keep):
        s = sum(v[0] for k, v in self.sums.items() if keep(k))
        n = sum(v[1] for k, v in self.sums.items() if keep(k))
        return s / n if n else None

    def usd(self, model, role, price):
        """An abandoned call at the model's own rate: its reported dollars per prompt token (every call of the model
        that booked a cost) x the prompt (the role's average on the model, else the role's on any model, else the
        model's); at the list price of the prompt (price in_per_mtok) until the model has MIN_REPORTED such calls.
        None when no prompt size is known at all (said on the line, never read as $0)."""
        avg = None
        for keep in (lambda k: k == (model, role), lambda k: k[1] == role, lambda k: k[0] == model):
            avg = self._avg(keep)
            if avg is not None:
                break
        if avg is None:
            return None
        c, p, k = self.rate.get(model, (0.0, 0.0, 0))
        rate = c / p if k >= MIN_REPORTED and p else float((price or {}).get("in_per_mtok") or 0.0) / 1e6
        return avg * rate


def abandoned(r):
    """A call with no cost booked that may have been billed: abandoned at its deadline (a timeout), or cut off after
    CUT_S in flight with no answer (no HTTP status: a dropped connection); the stricter reading of ruling 108's basis
    (ruling 106 (b)). An error the vendor answered (a status) is what it reported."""
    return r["cost_usd"] is None and (r["kind"] == "timeout" or (r["http_status"] is None and
                                                                 float(r["latency_s"] or 0.0) >= CUT_S))


def watcher_spend(q, t0, t1, cfg):
    """The watcher's spend in [t0, t1) from its call records (cache hits are free and skipped): {"by": {use: usd},
    "reported", "estimated", "abandoned": usd, "abandoned_n", "unpriced_n", "calls": counts}."""
    be = cfg.get("backends") or {}
    out = {"by": {}, "reported": 0.0, "estimated": 0.0, "abandoned": 0.0, "abandoned_n": 0, "unpriced_n": 0,
           "calls": 0}
    hist = None
    for r in q.rows("SELECT role, backend, model, kind, cost_usd, http_status, latency_s FROM calls WHERE ts >= ? AND "
                    "ts < ? AND COALESCE(kind, '') != 'cache'", (t0, t1)):
        use = USE.get(r["role"], "other")
        if abandoned(r):
            hist = hist or History(q, t1)
            usd = hist.usd(r["model"], r["role"], (be.get(r["backend"]) or {}).get("price"))
            if usd is None:
                out["unpriced_n"] += 1
                usd = 0.0
            else:
                out["abandoned"] += usd
                out["abandoned_n"] += 1
        else:
            usd = float(r["cost_usd"] or 0.0)
            out["reported" if _reports_cost(be.get(r["backend"]) or {}) else "estimated"] += usd
        out["by"][use] = out["by"].get(use, 0.0) + usd
        out["calls"] += 1
    return out


def audit_spend(path, t0, t1):
    """pp-ingest's audits in [t0, t1) from their cost ledger (one JSON record per review, or a correction: ts, usd,
    reported, basis) -> (usd, records, unreadable records, usd booked at the model's own rate). A record without
    'reported' is reported when its basis says so. A missing ledger is no audit yet."""
    usd, n, bad, booked = 0.0, 0, 0, 0.0
    try:
        f = open(path)
    except FileNotFoundError:
        return 0.0, 0, 0, 0.0
    with f:
        for line in f:
            if not line.strip():
                continue
            try:
                r = json.loads(line)
                ts, u = float(r["ts"]), float(r["usd"])
                if not (math.isfinite(ts) and math.isfinite(u) and u >= 0):
                    raise ValueError(line[:80])
            except (ValueError, KeyError, TypeError):
                bad += 1
                continue
            if t0 <= ts < t1:
                usd += u
                n += 1
                rep = r.get("reported")
                if not (rep if isinstance(rep, bool) else str(r.get("basis") or "").startswith("reported")):
                    booked += u
    return usd, n, bad, booked


def notice(q, now, cfg, audit_path, quiet="", spec_path=None):
    """'BATCH <n> ingest spend: $x (...)' for STATE line 1: the spend from the batch's start to its latest whole hour,
    closed at its end; quiet: the cycles' 3-hour note, said on line 1 too (the orchestrator's 21:22 order). Raises when
    the batch file cannot be read (the caller logs it; line 1 keeps its last figure)."""
    b = load(spec_path)
    tail = f"; {quiet}" if quiet else ""
    if now < b["t0"]:
        return f"{b['name']} ingest spend: $0.0000 (the batch starts {_hm(b['t0'], '%H:%M ET %b %d')}){tail}"
    mark = min(b["t1"], b["t0"] + int((now - b["t0"]) // HOUR_S) * HOUR_S)
    closed = mark >= b["t1"]
    w = watcher_spend(q, b["t0"], mark, cfg)
    au, an, bad, ab = audit_spend(audit_path, b["t0"], mark)
    mc = sum(w["by"].values())
    uses = ", ".join(f"{u} ${w['by'][u]:.4f}" for u in ORDER if u in w["by"])
    span = f"{_hm(b['t0'], '%H:%M ET %b %d')} to {_hm(mark, '%H:%M ET %b %d' if closed else '%H:%M ET')}"
    basis = ["vendor-reported"]
    if w["abandoned_n"]:
        basis.append(f"${w['abandoned']:.4f} booked for {w['abandoned_n']} abandoned call(s) at the model's own rate")
    if ab:
        basis.append(f"${ab:.4f} of the audits booked for reviews cut off or abandoned, at the model's own rate")
    if w["estimated"]:
        basis.append(f"${w['estimated']:.4f} priced from the table (its vendor reports no cost)")
    if w["unpriced_n"]:
        basis.append(f"{w['unpriced_n']} abandoned call(s) NOT PRICED (no prompt size known)")
    if bad:
        basis.append(f"{bad} audit cost record(s) UNREADABLE (not counted)")
    text = (f"{b['name']} ingest spend: ${mc + au:.4f} ({'CLOSED, ' if closed else ''}{span}: {b['share_of']} "
            f"${mc:.4f} of the ${b['share_usd']:.2f} share" + (f" ({uses})" if uses else "") +
            f", {w['calls']} model call(s); audits ${au:.4f}, {an} cost record(s); " + "; ".join(basis) + ")")
    if closed:
        text += (f"; NO BATCH OPEN SINCE {_hm(b['t1'], '%H:%M ET %b %d')}: the paid route spends nothing until the "
                 "next batch's money is set")
    return text + tail


def share_left(q, now, cfg, spec_path=None):
    """Ruling 108 for ruling 98's paid route: (dollars left of the batch's share for mining and checks, what it is),
    counted to now. Outside a batch, or with the batch file unreadable: (0.0, why): the paid route spends nothing."""
    try:
        b = load(spec_path)
    except Exception as e:                                # noqa: BLE001 (fail closed: no money is set)
        return 0.0, f"the batch file cannot be read ({type(e).__name__}): no batch money is set"
    if not b["t0"] <= now < b["t1"]:
        return 0.0, (f"no batch open ({b['name']} runs {_hm(b['t0'], '%H:%M ET %b %d')} to "
                     f"{_hm(b['t1'], '%H:%M ET %b %d')})")
    w = watcher_spend(q, b["t0"], now + 1.0, cfg)          # [t0, now]: a call recorded in this second counts too
    return b["share_usd"] - sum(w["by"].values()), f"{b['name']}'s ${b['share_usd']:.2f} share for {b['share_of']}"
