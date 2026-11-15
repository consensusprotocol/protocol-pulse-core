#!/usr/bin/env python3
"""pipeline/oracle/llm.py — transport plumbing shared by every back-end: keys by name, prices, the spend ledger.

No vendor and no model name lives here (law L-x): back-ends, endpoints, models and their prices are the provider config
(pipeline/oracle/providers.py), which is also the only module that calls a model.
keys    read by NAME through the pipeline's loader, relay.get_key (the main tree's copy); never printed, logged or
        written
spend   every call's measured usage priced per back-end and appended to a ledger; a call whose worst case would take
        the ledger past the cap is never made (SpendStop); in-flight worst cases stay reserved until the call returns
"""
import contextlib
import fcntl
import json
import math
import os
import re
import threading
import uuid

# The pipeline's key loader (integrator merge, audits batch 89; the house rule that held pp-tests in batch 78: keys by
# NAME through it, never a key-file path parsed here). It finds the project's key files from its own location, so it is
# the MAIN tree's copy, pinned (never taken from the environment: that would choose a file to execute in a process that
# holds keys) and loaded by file path, so sys.path is left alone and no bytecode is written in the main tree.
KEY_LOADER = "/home/ultron/protocol_pulse/video_pipeline_v3/relay.py"
SPEND_CAP_USD = 60.0
NO_TOOLS = " You have no tools and cannot read anything else: answer fully in this one message."


class SpendStop(RuntimeError):
    pass


_SECRETS = set()                 # every key value this process has loaded: masked wherever text leaves the process
_KEYLIKE = re.compile(r"(sk-(?:proj-|ant-|svcacct-)?[A-Za-z0-9_\-*]{6,}|xai-[A-Za-z0-9_\-*]{6,}|Bearer\s+\S+)")


_GET_KEY = []
_KEY_LOCK = threading.Lock()


def _loader():
    """relay.get_key from KEY_LOADER, loaded once per process (a missing loader file raises FileNotFoundError naming
    it). sys.dont_write_bytecode is process-wide: while it loads, another thread's import skips its own .pyc too."""
    with _KEY_LOCK:
        if not _GET_KEY:
            import importlib.util
            import sys
            spec = importlib.util.spec_from_file_location("_pp_oracle_relay", KEY_LOADER)
            mod = importlib.util.module_from_spec(spec)
            prev, sys.dont_write_bytecode = sys.dont_write_bytecode, True     # no __pycache__ in the main tree
            try:
                spec.loader.exec_module(mod)
            finally:
                sys.dont_write_bytecode = prev
            _GET_KEY.append(mod.get_key)
        return _GET_KEY[0]


def env_key(name):
    """One key's value by NAME through relay.get_key (the process environment first, then the project's key files);
    never printed, remembered only so redact() can mask it. A missing or empty key raises KeyError."""
    v = _loader()(name, required=False)
    if not v:
        raise KeyError(f"{name} not set")
    _SECRETS.add(v)
    return v


def redact(text):
    """Text safe to print or persist: every loaded key value and every key-shaped token (an SDK error may echo part
    of a key) replaced by [REDACTED]."""
    out = str(text)
    for v in sorted(_SECRETS, key=len, reverse=True):
        out = out.replace(v, "[REDACTED]")
    return _KEYLIKE.sub("[REDACTED]", out)


def cost(price, tokens_in, tokens_out):
    """USD for one call at a back-end's price {in, out[, in_long, out_long, long_above]} (USD per 1M tokens)."""
    if not price:
        return 0.0
    long = tokens_in > price.get("long_above", float("inf"))
    return round(tokens_in / 1e6 * price["in_long" if long else "in"]
                 + tokens_out / 1e6 * price["out_long" if long else "out"], 4)


def _alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


class Ledger:
    """Append-only spend ledger (jsonl), shared by every thread AND every process that names the same path.
    spent() = the sum of every recorded call's measured cost. A priced call's worst case is reserved in
    <path>.inflight under an exclusive file lock (<path>.lock) until the call settles (its measured row appended and
    its reservation dropped in one locked step), so concurrent calls, in one process or several, can never pass the
    cap together. A reservation of a process that no longer exists is charged at its worst case (it may have been
    billed). An unpriced call is refused once the recorded spend has reached the cap."""

    def __init__(self, path, cap=SPEND_CAP_USD):
        self.path, self.cap = path, cap
        self._tlock = threading.Lock()

    @contextlib.contextmanager
    def _locked(self):
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with self._tlock, open(self.path + ".lock", "a", encoding="utf-8") as lk:
            fcntl.flock(lk, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lk, fcntl.LOCK_UN)

    def _spent(self):
        if not os.path.exists(self.path):
            return 0.0
        with open(self.path, encoding="utf-8") as f:
            return round(sum(json.loads(line).get("usd") or 0.0 for line in f if line.strip()), 4)

    def _inflight(self):
        """The live reservations. A reservation whose process has ended was sent and may have been billed: it is
        charged at its worst case as an 'orphaned' row (never dropped), then removed (call under the lock)."""
        p = self.path + ".inflight"
        if not os.path.exists(p):
            return {}
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        dead = {k: v for k, v in d.items() if not _alive(v["pid"])}
        for k, v in dead.items():
            self._append({"tag": f"orphaned reservation {k}", "label": v.get("label"), "usd": v["usd"],
                          "usd_source": "orphaned: worst case (the process ended mid-call)", "pid": v["pid"]})
        live = {k: v for k, v in d.items() if k not in dead}
        if dead:
            self._write_inflight(live)
        return live

    def _write_inflight(self, d):
        p = self.path + ".inflight"
        with open(p + ".tmp", "w", encoding="utf-8") as f:
            json.dump(d, f)
        os.replace(p + ".tmp", p)

    def _append(self, row):
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, sort_keys=True) + "\n")

    def spent(self):
        with self._locked():
            self._inflight()                         # charge any orphaned reservation first
            return self._spent()

    def in_flight(self):
        with self._locked():
            return round(sum(v["usd"] for v in self._inflight().values()), 4)

    def allow(self, price, est_in, max_out, label=""):
        """Reserve a priced call's worst case; returns the reservation token (SpendStop if it would pass the cap)."""
        return self.reserve(cost(price, est_in, max_out), label)

    def reserve(self, worst, label=""):
        """Reserve `worst` USD for one call in flight; returns the token (SpendStop if it would pass the cap)."""
        with self._locked():
            inf, spent = self._inflight(), self._spent()
            held = sum(v["usd"] for v in inf.values())
            if spent + held + worst > self.cap:
                raise SpendStop(f"spend guard: {spent:.2f} spent + {held:.2f} in flight + worst case {worst:.2f} "
                                f"for {label} > cap {self.cap:.2f} USD")
            token = f"{os.getpid()}-{uuid.uuid4().hex[:12]}"
            inf[token] = {"pid": os.getpid(), "usd": worst, "label": label}
            self._write_inflight(inf)
        return token

    def allow_unpriced(self, label=""):
        """An unpriced call (cost known only afterwards) is refused once the recorded spend has reached the cap."""
        with self._locked():
            spent = self._spent()
            if spent >= self.cap:
                raise SpendStop(f"spend guard: {spent:.2f} spent >= cap {self.cap:.2f} USD ({label})")

    def release(self, token):
        """Drop a reservation without a row (the call was never made, or failed before the vendor billed it)."""
        with self._locked():
            inf = self._inflight()
            if inf.pop(token, None) is not None:
                self._write_inflight(inf)

    def settle(self, token, **row):
        """Append the call's measured row and drop its reservation in one locked step."""
        with self._locked():
            self._append(row)
            inf = self._inflight()
            if token is not None and inf.pop(token, None) is not None:
                self._write_inflight(inf)

    def record(self, **row):
        with self._locked():
            self._append(row)


# Below every tokenizer measured on this instrument's own stored prompts (2026-11-12: the writer's 2.93-3.06 and the
# judge's 1.84-2.07 characters per token), so the estimate errs towards MORE tokens: it decides whether a prompt fits a
# context window (a cut prompt is never sent) and how much of the spend cap an in-flight call reserves.
CHARS_PER_TOKEN_MIN = 1.75


def est_tokens(*texts):
    return math.ceil(sum(len(t) for t in texts) / CHARS_PER_TOKEN_MIN)
