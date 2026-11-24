"""pipeline/spend_ceiling.py: ONE spend ledger for the spend day, the $1.50 CEILING across the builder, the audio lock
service and the renderer (the owner's assignment for build 172, R1, 15:25 ET Nov 24). THIS FILE IS BYTE-IDENTICAL on the
builder's branch (pp-lean) and the release's (lean-release); a test on each checks the other's copy.

THE LEDGER: one JSON file a spend day (21:10 ET to 21:10 ET, named by the date the day starts on), at a FIXED absolute
path outside every worktree: LEDGER_DIR/SPEND_D<YYYYMMDD>.json (LEDGER_DIR /home/ultron/pp_spend; the environment's
PP_SPEND_LEDGER_DIR only in tests). Its format and its lock are providers.Router's own (the builder's router reads and
writes this very file when its spend path is set here, ceiling mode): {"usd_estimate", "usd_reported",
"usd_unreported_estimate", "calls", "by_backend", "by_role", "reserved", ...}; the lock is fcntl.flock on
"<ledger>.lock". What counts against the cap (basis): every capped back-end's vendor-reported dollars, plus every
unreported estimate (a metered cost: Scribe by audio seconds), plus every reservation held, plus what other ledgers
spent that day (seeded at launch as "carried_in:<source>" back-ends). Heimdall is in-house: recorded, never capped.

RESERVE THEN SETTLE (`charge()`): before the vendor is asked, the call's upper bound is reserved under the lock; a call
whose reservation would pass CAP_USD is refused (CeilingRefused) before any network use. After the call its cost is
settled: the vendor's reported figure, or our metered one. FAIL CLOSED:
  - the ledger unreadable, or its lock not taken within LOCK_WAIT_S: refused;
  - a call that ends with its cost unknown (it raised after it may have reached the vendor, or nobody settled it): its
    reservation stays counted at its full amount and the ledger STOPS: no further paid call by any program, until the
    owner clears it (clear_stop, logged in the ledger);
  - a bill above its reservation: counted as billed, and the ledger stops;
  - a process that died between reserve and settle: its reservation stays counted (never released by anyone), and the
    next reservation by any program finds it and STOPS the ledger (its cost is unknown).
A call the vendor REFUSED with a 4xx status (rejected, rate-limited, unauthorised: not processed) and a call refused
before it was sent release their reservation.
THE VOICE (ElevenLabs TTS) bills characters against the plan's monthly quota; no USD rate is established offline (the
plan's character_limit 363000; the last eight render preflights, Nov 14-23, logged 351,580 to 354,985 characters left;
whether usage past the limit is billed was not read). VOICE_MODE "chars" (the default): outside the dollar ceiling, held to
VOICE_CHAR_CAP characters PER BUILD (the launch names the build: PP_SPEND_RUN), a reservation of characters refused past
it; with the preflight's own floor (no render starts with fewer than 2,000 characters left) a build never reaches
past the plan's included characters. "usd": counted at the owner's stated rate (PP_VOICE_USD_PER_1K_CHARS); never a
rate of ours.
THE GUARD (`install_guard()`): urllib, requests and httpx refuse a request to a PAID endpoint unless this thread holds a
live reservation (`charge()` or `bound()`): no paid client is reachable without the ledger. Free endpoints (Heimdall,
Telegram, YouTube, ElevenLabs' account reads) pass."""
import contextlib
import fcntl
import json
import os
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

CAP_USD = 1.50                     # THE ONE DAY CAP (amendment C, Nov 24): never raised here
LEDGER_DIR = "/home/ultron/pp_spend"   # THE fixed place, outside every worktree (PP_SPEND_LEDGER_DIR: tests only)
DAY_ET = ZoneInfo("America/New_York")
DAY_START = (21, 10)               # ruling 118: a spend day runs 21:10 ET to 21:10 ET
LOCK_WAIT_S = float(os.environ.get("PP_SPEND_LOCK_WAIT_S") or 10.0)
UNCAPPED = ("heimdall",)           # ruling 118 (b): in-house, recorded, never capped (providers.Router's own reading)
VOICE_MODE = os.environ.get("PP_VOICE_MODE") or "chars"
VOICE_CHAR_CAP = int(os.environ.get("PP_VOICE_CHAR_CAP") or 1000)  # PER BUILD: 4.5 x the one real render the outside
#   ledger holds (223 characters: a bridge line 98 + the sign-off 125, Nov 23 22:43 ET, service "render"); its 20 other
#   TTS lines are test runs (service "unknown", the same two stub texts), not measurements
VOICE_USD_PER_1K = os.environ.get("PP_VOICE_USD_PER_1K_CHARS")      # set by the owner, or the voice is not in dollars
# THE RELEASE'S CHARGEABLE CALLS (lean-release; the builder's are providers.Router's back-ends, reserved there):
SCRIBE_USD_PER_MIN = 0.012         # second_recogniser.scribe_words: the code's own rate (ruling 131); metered by the
#   request's own audio (16 kHz mono 16-bit: 32,000 bytes a second), reserved before, settled at the same figure
SIGNOFF_RESERVE_USD = 0.05         # signoff.generate_signoff, ONE round (grok-3-mini, max_tokens 500): a STATED bound, 12 x
#   its one recorded bill ($0.004013, Nov 24); settled at xAI's reported figure; a bill above it stops the ledger
VISION_RESERVE_USD = 0.50          # visual_check._call_xai (an 'xai:' vision model; none is seated: VISION_MODELS are
#   Heimdall's): a STATED bound for max_tokens 4000 and one image; settled at xAI's reported figure
PAID = (("api.x.ai", ""), ("api.openai.com", ""), ("api.anthropic.com", ""),
        ("generativelanguage.googleapis.com", ""), ("api.elevenlabs.io", "/v1/speech-to-text"),
        ("api.elevenlabs.io", "/v1/text-to-speech"))                # (host, path prefix): every other endpoint is free


def run_name():
    """The build the voice's characters are counted for (the launch sets PP_SPEND_RUN)."""
    return os.environ.get("PP_SPEND_RUN") or "unnamed"


class CeilingRefused(Exception):
    """A paid call refused BEFORE the vendor is asked: the ceiling, the stop, the lock or an unreadable ledger."""


def day_start(now=None):
    t = (now or datetime.now(timezone.utc)).astimezone(DAY_ET)
    s = t.replace(hour=DAY_START[0], minute=DAY_START[1], second=0, microsecond=0)
    return s - timedelta(days=1) if t < s else s


def ledger_path(now=None, ledger_dir=None):
    return os.path.join(ledger_dir or os.environ.get("PP_SPEND_LEDGER_DIR") or LEDGER_DIR,
                        f"SPEND_D{day_start(now):%Y%m%d}.json")


@contextlib.contextmanager
def locked(path, wait_s=None):
    """The ledger's lock (providers.Router._lock's file), taken within wait_s or refused (fail closed)."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    fd = os.open(path + ".lock", os.O_CREAT | os.O_RDWR, 0o644)
    end = time.time() + (LOCK_WAIT_S if wait_s is None else wait_s)
    try:
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.time() >= end:
                    raise CeilingRefused(f"the spend ledger's lock was not free within {wait_s or LOCK_WAIT_S:g} s: "
                                         f"no paid call (fail closed)") from None
                time.sleep(0.02)
        yield
    finally:
        os.close(fd)                                   # closing the descriptor releases the lock


def read(path):
    """The ledger (a missing file is an empty one); unreadable: CeilingRefused. Reservations are NEVER released here,
    a dead process's included: a crash between reserve and settle stays counted."""
    if not os.path.exists(path):
        return {"usd_estimate": 0.0, "usd_reported": 0.0, "usd_unreported_estimate": 0.0, "calls": 0,
                "by_backend": {}, "by_role": {}, "reserved": {}}
    try:
        with open(path) as f:
            d = json.load(f)
        if not isinstance(d, dict) or not isinstance(d.get("usd_estimate", 0.0), (int, float)) or \
                not isinstance(d.get("by_backend", {}), dict) or not isinstance(d.get("reserved", {}), dict):
            raise ValueError("not a ledger")
    except (OSError, ValueError) as e:
        raise CeilingRefused(f"the spend ledger {path} is unreadable ({type(e).__name__}): no paid call") from None
    for k, v in (("calls", 0), ("by_backend", {}), ("by_role", {}), ("reserved", {}), ("usd_reported", 0.0),
                 ("usd_unreported_estimate", 0.0)):
        d.setdefault(k, v)
    return d


def write(path, d):
    tmp = f"{path}.{os.getpid()}.{threading.get_ident()}.tmp"
    with open(tmp, "w") as f:
        json.dump(d, f, indent=1)
    os.replace(tmp, path)


def capped(name):
    return str(name).split(":", 1)[0] not in UNCAPPED


def spent(d):
    """What counts against the cap, held reservations excluded (providers.Router._basis_total, uncapped Heimdall): the
    capped back-ends' vendor-reported dollars (carried_in entries included) and every unreported estimate."""
    return sum(float(v.get("usd_reported", 0.0) or 0.0) for k, v in d["by_backend"].items() if capped(k)) + \
        float(d.get("usd_unreported_estimate", 0.0) or 0.0)


def held(d):
    return sum(float(x) for x in d["reserved"].values())


_tl = threading.local()


def _key():
    return f"{os.getpid()}:{uuid.uuid4().hex[:10]}"


def reserve(backend, usd, role="", chars=0, path=None, now=None):
    """Reserve `usd` (and, for the voice, `chars`) for one call of `backend` -> the reservation key. CeilingRefused, before
    any network use, when the ledger is stopped, or spent + held + usd would pass CAP_USD, or the voice's characters would
    pass VOICE_CHAR_CAP, or the ledger cannot be read or locked."""
    path = path or ledger_path(now)
    usd = round(max(0.0, float(usd)), 6)
    with locked(path):
        d = read(path)
        if mark_dead(d):
            write(path, d)
        if d.get("stop"):
            raise CeilingRefused(f"the spend ledger is STOPPED ({d['stop'].get('why')}): no paid call until the owner "
                                 f"clears it")
        s, h = spent(d), held(d)
        if s + h + usd > CAP_USD + 1e-9:
            raise CeilingRefused(f"the ceiling: spent ${s:.4f} + held ${h:.4f} + this {backend} call's ${usd:.4f} > "
                                 f"${CAP_USD:.2f}: refused before the vendor is asked")
        if chars:
            vc = d.setdefault("voice", {}).setdefault("runs", {}).setdefault(run_name(), {"chars": 0, "reserved": {}})
            vh = sum(int(x) for x in vc["reserved"].values())
            if VOICE_MODE == "chars" and vc["chars"] + vh + int(chars) > VOICE_CHAR_CAP:
                raise CeilingRefused(f"the voice's character cap: {vc['chars']} said + {vh} held + {chars} > "
                                     f"{VOICE_CHAR_CAP} characters for build {run_name()}")
        k = _key()
        d["reserved"][k] = usd
        d.setdefault("reservations", {})[k] = {"backend": backend, "role": role, "usd": usd, "chars": int(chars or 0),
                                               "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        if chars:
            vc["reserved"][k] = int(chars)
        write(path, d)
    return k


def _pid_dead(key):
    try:
        os.kill(int(str(key).split(":")[0]), 0)
        return False
    except PermissionError:
        return False                                   # another user's live process
    except (ValueError, ProcessLookupError, OSError):
        return True


def mark_dead(d):
    """A reservation whose process has ended before it settled: its cost is unknown. It stays counted and the ledger
    STOPS (fail closed). -> True when the ledger was changed."""
    dead = [k for k in d["reserved"] if _pid_dead(k)]
    if dead and not d.get("stop"):
        _stop(d, f"{len(dead)} reservation(s) of a process that ended before it settled ({dead[0]}): the cost is "
                 f"unknown", dead[0])
        return True
    return False


def settle(key, backend, usd, reported=True, role="", usage=None, path=None, now=None):
    """The call's cost after it: `usd` the vendor's reported figure (reported=True) or ours (metered); usd None: the cost
    is unknown: the reservation stays counted and the ledger STOPS. A bill above its reservation: counted, and the
    ledger stops. -> the ledger's spent total after."""
    path = path or ledger_path(now)
    with locked(path):
        d = read(path)
        res = d["reserved"].get(key)
        if usd is None:
            _stop(d, f"the cost of a {backend} call is unknown after it ({role}): its ${float(res or 0):.4f} stays "
                     f"counted", key)
            write(path, d)
            return spent(d) + held(d)
        d["reserved"].pop(key, None)
        (d.get("reservations") or {}).pop(key, None)
        for vc in ((d.get("voice") or {}).get("runs") or {}).values():
            if key in vc.get("reserved", {}):
                vc["chars"] += int(vc["reserved"].pop(key))
        usd = round(float(usd), 8)
        b = d["by_backend"].setdefault(backend, {"calls": 0, "in": 0, "out": 0, "usd_estimate": 0.0})
        r = d["by_role"].setdefault(role, {"calls": 0, "usd_estimate": 0.0})
        b["calls"] += 1
        r["calls"] += 1
        d["calls"] = d.get("calls", 0) + 1
        for k_, v_ in (usage or {}).items():
            if isinstance(v_, (int, float)) and not isinstance(v_, bool):
                b[k_] = round(float(b.get(k_, 0) or 0) + float(v_), 6)
        b["usd_estimate"] = round(float(b.get("usd_estimate", 0.0)) + usd, 6)
        r["usd_estimate"] = round(float(r.get("usd_estimate", 0.0)) + usd, 6)
        d["usd_estimate"] = round(float(d.get("usd_estimate", 0.0)) + usd, 6)
        if reported:
            b["usd_reported"] = round(float(b.get("usd_reported", 0.0) or 0.0) + usd, 8)
            b["reported_calls"] = b.get("reported_calls", 0) + 1
            d["usd_reported"] = round(float(d.get("usd_reported", 0.0)) + usd, 8)
        else:
            d["usd_unreported_estimate"] = round(float(d.get("usd_unreported_estimate", 0.0)) + usd, 6)
        if res is not None and usd > float(res) + 1e-9:
            _stop(d, f"a {backend} call billed ${usd:.4f}, above its ${float(res):.4f} reservation ({role})", key)
        write(path, d)
        return spent(d) + held(d)


def _stop(d, why, key=None):
    if not d.get("stop"):
        d["stop"] = {"why": why[:300], "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "key": key}


def clear_stop(by, why, path=None, now=None):
    """The owner's step, never a program's: the stop is cleared and the clearing logged in the ledger."""
    path = path or ledger_path(now)
    with locked(path):
        d = read(path)
        if d.get("stop"):
            d.setdefault("stops_cleared", []).append(dict(d.pop("stop"), cleared_by=by, cleared_why=why,
                                                          cleared_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())))
            write(path, d)


def status(path=None, now=None):
    path = path or ledger_path(now)
    with locked(path):
        d = read(path)
    s, h = spent(d), held(d)
    return {"ledger": path, "day_starts": day_start(now).isoformat(), "spent": round(s, 6), "held": round(h, 6),
            "room": round(CAP_USD - s - h, 6), "cap": CAP_USD, "stop": d.get("stop"),
            "carried_in": {k: v.get("usd_reported") for k, v in d["by_backend"].items() if k.startswith("carried_in:")},
            "voice": dict({"mode": VOICE_MODE, "cap_chars_per_build": VOICE_CHAR_CAP, "run": run_name(),
                           "carried_in_chars": (d.get("voice") or {}).get("carried_in_chars", 0)},
                          **(((d.get("voice") or {}).get("runs") or {}).get(run_name()) or {"chars": 0, "reserved": {}})),
            "reserved": dict(d["reserved"])}


def peek(path=None, now=None):
    """status() without the lock and without creating anything (a dry run's read: every write is an atomic replace, so
    the file read is always one whole version). Unreadable: CeilingRefused."""
    path = path or ledger_path(now)
    d = read(path)
    s, h = spent(d), held(d)
    return {"ledger": path, "day_starts": day_start(now).isoformat(), "spent": round(s, 6), "held": round(h, 6),
            "room": round(CAP_USD - s - h, 6), "cap": CAP_USD, "stop": d.get("stop"), "exists": os.path.exists(path)}


def seed(parts, path=None, now=None):
    """What other ledgers spent on this spend day, carried in as "carried_in:<source>" back-ends (counted like any
    capped vendor's reported dollars). Re-seeding sets each source to its latest figure (never twice)."""
    path = path or ledger_path(now)
    with locked(path):
        d = read(path)
        for src, usd in parts.items():
            d["by_backend"][f"carried_in:{src}"] = {"calls": 0, "usd_estimate": round(float(usd), 6),
                                                    "usd_reported": round(float(usd), 6), "carried_in": True,
                                                    "seeded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        write(path, d)
    return status(path)


@contextlib.contextmanager
def charge(backend, usd, role="", chars=0, path=None):
    """Reserve, run the call, settle: `with charge(...) as c: <the one vendor call>; c.cost(usd, reported)`. An exception
    inside, or no cost set, is a cost unknown: the reservation stays counted and the ledger stops (fail closed); a call
    refused BEFORE the request was made marks c.not_sent() and releases its reservation."""
    path = path or ledger_path()
    if usd is None or usd <= 0 and not chars:
        raise CeilingRefused(f"{backend}: no upper bound for the call: refused (an unbounded call is never made)")
    key = reserve(backend, usd if usd is not None else 0.0, role, chars, path)
    c = _Charge(key)
    prev = getattr(_tl, "keys", ())
    _tl.keys = prev + (key,)
    try:
        yield c
    except BaseException as e:
        _tl.keys = prev
        if c.sent is False or isinstance(e, CeilingRefused) or refused_by_vendor(e):
            _release(key, path)
        else:
            settle(key, backend, None, role=role, path=path)
        raise
    _tl.keys = prev
    if c.sent is False:
        _release(key, path)
    elif c.usd is None:
        settle(key, backend, None, role=role, path=path)
    else:
        settle(key, backend, c.usd, c.reported, role, c.usage, path)


class _Charge:
    def __init__(self, key):
        self.key, self.usd, self.reported, self.usage, self.sent = key, None, True, None, None

    def cost(self, usd, reported=True, usage=None):
        self.usd, self.reported, self.usage, self.sent = usd, reported, usage, True

    def not_sent(self):
        self.sent = False


def _release(key, path):
    with locked(path):
        d = read(path)
        d["reserved"].pop(key, None)
        (d.get("reservations") or {}).pop(key, None)
        for vc in ((d.get("voice") or {}).get("runs") or {}).values():
            vc.get("reserved", {}).pop(key, None)
        write(path, d)


def refused_by_vendor(e):
    """The vendor ANSWERED with a 4xx status (urllib's HTTPError, requests' and httpx's HTTP errors, the SDKs' API
    errors): the request was refused, not processed, not billed. Anything else is not known to be free."""
    import urllib.error
    status = e.code if isinstance(e, urllib.error.HTTPError) else getattr(e, "status_code", None)
    if status is None:
        status = getattr(getattr(e, "response", None), "status_code", None)
    try:
        return 400 <= int(status) < 500
    except (TypeError, ValueError):
        return False


def xai_reported_usd(body):
    """xAI's own figure for a call (usage.cost_in_usd_ticks, 1 USD = 1e10 ticks), or None (then the cost is unknown)."""
    u = body.get("usage") if isinstance(body, dict) else None
    t = u.get("cost_in_usd_ticks") if isinstance(u, dict) else None
    return t / 1e10 if isinstance(t, (int, float)) and not isinstance(t, bool) else None


def voice_usd(chars):
    """The voice in dollars: 0.0 in "chars" mode (the plan's included characters, held by the per-build character cap);
    in "usd" mode the owner's stated rate, or CeilingRefused (never a rate of ours)."""
    if VOICE_MODE == "chars":
        return 0.0
    if not VOICE_USD_PER_1K:
        raise CeilingRefused("PP_VOICE_MODE=usd needs the owner's PP_VOICE_USD_PER_1K_CHARS: no rate of ours")
    return round(int(chars) / 1000.0 * float(VOICE_USD_PER_1K), 6)


def bound(key, fn):
    """fn with `key` held in the thread that runs it (providers.Router runs a call in a deadline thread)."""
    def run(*a, **k):
        prev = getattr(_tl, "keys", ())
        _tl.keys = prev + (key,)
        try:
            return fn(*a, **k)
        finally:
            _tl.keys = prev
    return run


def is_paid(url):
    from urllib.parse import urlsplit
    u = urlsplit(str(url))
    host, p = (u.hostname or "").lower(), u.path or "/"
    return any((host == h or host.endswith("." + h)) and p.startswith(pre) for h, pre in PAID)


def check_url(url):
    """The guard: a paid endpoint needs a live reservation in this thread."""
    if is_paid(url) and not getattr(_tl, "keys", ()):
        raise CeilingRefused(f"a paid request with no reservation in the spend ledger: {str(url).split('?')[0][:120]}")


_GUARDED = {}


def install_guard():
    """Every paid request through urllib, requests or httpx passes check_url first (idempotent)."""
    import urllib.request as U
    if "urllib" not in _GUARDED:
        _open = U.OpenerDirector.open

        def open_(self, fullurl, *a, **k):
            check_url(getattr(fullurl, "full_url", fullurl))
            return _open(self, fullurl, *a, **k)
        U.OpenerDirector.open, _GUARDED["urllib"] = open_, _open
    try:
        import requests.sessions as R
        if "requests" not in _GUARDED:
            _req = R.Session.request

            def request(self, method, url, *a, **k):
                check_url(url)
                return _req(self, method, url, *a, **k)
            R.Session.request, _GUARDED["requests"] = request, _req
    except ImportError:
        pass
    try:
        import httpx as H
        if "httpx" not in _GUARDED:
            _s1, _s2 = H.Client.send, H.AsyncClient.send

            def send(self, request, *a, **k):
                check_url(request.url)
                return _s1(self, request, *a, **k)

            async def asend(self, request, *a, **k):
                check_url(request.url)
                return await _s2(self, request, *a, **k)
            H.Client.send, H.AsyncClient.send, _GUARDED["httpx"] = send, asend, (_s1, _s2)
    except ImportError:
        pass
    return sorted(_GUARDED)
