#!/usr/bin/env python3
"""RULING 114 (orchestrator 13:18 ET Nov 15): V4 ON AN XINFER WORKER. The Heimdall team: the unclosed JSON is "the
usual vllm schema problem; the xinfer workers don't have this issue", and a request carrying the HTTP header
x-bf-tunnel-instance: pinga282 goes to an xinfer worker IF the gateway forwards the header.
(a) 30 of the 93 records that came back unclosed ("truncated") in replay111, the five the team was sent among them
    (out_tokens 7, 122, 171, 497, 1564), asked exactly as replay111 asked them (replay111.FormatBackend: the v4
    abliterated, response_format json_object, reasoning_effort none; the record's own max_tokens, seed and system),
    ONCE WITH the header and ONCE WITHOUT, at the same seed. The legs alternate which goes first.
(b) Per call: finish_reason, the response's id, EVERY response header, out_tokens, seconds, the answer's shape
    (closed JSON, or replay111.shape) and its text (diagnosis only, never a verdict). Our own request's headers are
    NEVER recorded (the Authorization is among them): a row says only whether the x-bf header was sent.
(c) REPORT.md: unclosed with / without the header; the response headers that differ between the legs (an instance
    name would show there); finish_reason counts for the unclosed answers.
SPEND: Heimdall only, vendor-reported (usage.cost), on its own ledger SPEND_R114.json; no call starts once it holds
STOP_USD ($0.14 of the order's $0.15). One call at a time. No routing change: nothing here is read by a build.
Usage: python3 -B tests/package/replay114.py [--n 30] [--report-only]"""
import argparse
import collections
import contextlib
import json
import os
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "pipeline"))
sys.path.insert(0, HERE)
import providers as P  # noqa: E402
import replay111 as RY  # noqa: E402

WT = RY.WT
OUT = os.path.join(WT, "tests", "package", "proof", "replay114")
SPEND = os.path.join(WT, "tests", "package", "proof", "SPEND_R114.json")
SOURCE = os.path.join(RY.OUT, "OUT_OF_CONTRACT.jsonl")
HEADER = {"x-bf-tunnel-instance": "pinga282"}
NAMED = (7, 122, 171, 497, 1564)
N, STOP_USD = 30, 0.14
UNREPORTED_USD = 0.002   # a call whose reply carries no cost counts this (an upper bound: replay111's v4 calls were a
#   median $0.00006, at most $0.0011), on its own ledger line, so the stop never reads an unpriced call as $0


def unclosed(path=SOURCE):
    """replay111's unclosed answers: its out-of-contract rows of shape "truncated"."""
    with open(path) as f:
        return [r for r in map(json.loads, f) if r.get("shape") == "truncated"]


def pick(rows, n=N, named=NAMED):
    """One record for each named out_tokens first, then the others spread evenly in out_tokens order (ties by record)."""
    rows = sorted({r["record"]: r for r in reversed(rows)}.values(),      # one row a record (glm F1), then sorted
                  key=lambda r: (r.get("out_tokens") or 0, r["record"]))
    first = []
    for t in named:
        hit = [r for r in rows if r.get("out_tokens") == t]
        if not hit:
            raise ValueError(f"no unclosed record with out_tokens {t}")
        first.append(hit[0])
    taken = {r["record"] for r in first}
    rest = [r for r in rows if r["record"] not in taken]
    k = min(n - len(first), len(rest))
    return first + [rest[int(i * len(rest) / k)] for i in range(k)] if k > 0 else first[:n]


def headers_of(msg):
    """Every response header, names lowercased, a repeated header's values joined in order (RFC 9110 5.3)."""
    out = {}
    for k, v in (msg.items() if msg is not None else ()):
        out[k.lower()] = f"{out[k.lower()]}, {v}" if k.lower() in out else v
    return out


class Capture:
    """providers._http_json for one call, with `extra` headers added. It keeps the RESPONSE of EVERY attempt
    (providers._with_backoff may retry a 429 / 5xx: each attempt's status and headers are kept in "attempts", in
    order; audit 1418 C1, glm F18) and the last one's status, headers, id, finish_reason, usage and model. The
    request's own headers are never kept."""

    def __init__(self, extra):
        self.extra, self.seen = dict(extra), {"attempts": []}

    def _attempt(self, status, msg):
        a = {"status": status, "response_headers": headers_of(msg)}
        self.seen = dict(a, attempts=self.seen["attempts"] + [a])

    def __call__(self, url, body, headers, timeout):
        req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json", **headers, **self.extra})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
                self._attempt(resp.status, resp.headers)
        except urllib.error.HTTPError as e:
            self._attempt(e.code, e.headers)
            raise
        try:
            j = json.loads(raw)
        except ValueError:
            self.seen["body_head"] = raw[:500].decode("utf-8", "replace")    # diagnosis only (glm F3)
            raise
        ch = ((j.get("choices") or [{}])[0] or {}) if isinstance(j, dict) else {}
        self.seen.update(id=j.get("id"), finish_reason=ch.get("finish_reason"), usage=j.get("usage"),
                         response_model=j.get("model"))
        return j


@contextlib.contextmanager
def capturing(extra):
    real, cap = P._http_json, Capture(extra)
    P._http_json = cap
    try:
        yield cap
    finally:
        P._http_json = real


def shape_of(text, out_tokens, cap):
    t = str(text or "").strip()
    try:
        json.loads(t)
        return "closed JSON"
    except ValueError:
        return RY.shape(text, out_tokens, cap)


def ask(backend, rec, leg):
    """One call of `rec` on the v4 backend, leg "with" (the header) or "without" -> its row."""
    mt, seed = int(rec.get("max_tokens") or 2000), int(rec.get("seed") or 7)
    row = {"leg": leg, "x_bf_header_sent": leg == "with", "seed": seed, "max_tokens": mt}
    t0 = time.time()
    with capturing(HEADER if leg == "with" else {}) as cap:
        try:
            text, usage, secs = backend.complete(rec["prompt"], mt, seed, system=rec.get("system"))
        except Exception as e:                            # noqa: BLE001  any failure is a row, never the run's end
            row.update(seconds=round(time.time() - t0, 2), error=f"{type(e).__name__}: {str(e)[:200]}", **cap.seen)
            return row
    u, usage = cap.seen.get("usage") or {}, usage or {}
    out = int(u.get("completion_tokens") or usage.get("out") or 0)
    row.update(seconds=round(secs, 2), **cap.seen, out_tokens=out, usd_reported=usage.get("usd_reported"),
               shape=shape_of(text, out, backend.max_out(mt)), text=text[:6000])
    if row["usd_reported"] is None:              # unpriced (FormatBackend's usage carries "usd_reported" from the
        row["usd_unreported_estimate"] = UNREPORTED_USD   # reply's cost, providers._reported): counted at the bound
    row["unclosed"] = row["shape"] == "truncated"
    return row


def ledger(path=None):
    """The ledger (SPEND, read when called): {"usd_reported", "usd_unreported_estimate"}; zeros when there is none yet.
    A ledger that exists but cannot be read stops the run (fail closed: never a $0 that lets calls past the cap;
    audit 1418 C1, qwen)."""
    path = path or SPEND
    if not os.path.exists(path):
        return {"usd_reported": 0.0, "usd_unreported_estimate": 0.0}
    try:
        with open(path) as f:
            d = json.load(f)
        return {"usd_reported": float(d["usd_reported"]), "usd_unreported_estimate":
                float(d.get("usd_unreported_estimate") or 0.0)}
    except (OSError, ValueError, KeyError, TypeError) as e:
        raise RuntimeError(f"replay114: the spend ledger {path} cannot be read ({type(e).__name__}): refused") from e


def spent(path=None):
    """What the stop reads: the vendor-reported total plus the estimate for calls that came back unpriced."""
    d = ledger(path)
    return d["usd_reported"] + d["usd_unreported_estimate"]


def add_spend(usd, estimate=None, path=None):
    path = path or SPEND
    d = ledger(path)
    d = {"usd_reported": round(d["usd_reported"] + float(usd or 0.0), 8),
         "usd_unreported_estimate": round(d["usd_unreported_estimate"] + float(estimate or 0.0), 8)}
    with open(path + ".tmp", "w") as f:
        json.dump(d, f)
    os.replace(path + ".tmp", path)


def backend():
    r = RY.build_router(("none",), spend_path=None)
    return r.backends[RY.bname("none")]


def run(n=N, b=None, stop_usd=STOP_USD, results=None):
    results = results or os.path.join(OUT, "RESULTS.jsonl")
    os.makedirs(os.path.dirname(results), exist_ok=True)
    b = b or backend()
    done = set()
    if os.path.exists(results):
        with open(results) as f:
            done = {(x["record"], x["leg"]) for x in map(json.loads, f)}
    for i, src in enumerate(pick(unclosed(), n)):
        try:
            with open(os.path.join(WT, src["record"])) as f:
                rec = json.load(f)
        except (OSError, ValueError) as e:             # no call: an error row for each leg (audit 1418 C1, qwen)
            rec = {"error": f"the record cannot be read ({type(e).__name__})"}
        for leg in (("with", "without") if i % 2 == 0 else ("without", "with")):
            if (src["record"], leg) in done:
                continue
            if spent() >= stop_usd:
                print(f"replay114: stopped at ${spent():.4f} (stop ${stop_usd:.2f})", flush=True)
                return
            row = dict(ask(b, rec, leg) if "error" not in rec else {"leg": leg, "error": rec["error"]},
                       record=src["record"], type=src["type"], replay111_out_tokens=src.get("out_tokens"), order=i)
            add_spend(row.get("usd_reported"), row.get("usd_unreported_estimate"))
            with open(results, "a") as f:
                f.write(json.dumps(row) + "\n")
            print(f"  {i + 1}/{n} {leg}: {row.get('shape') or row.get('error')}, {row.get('finish_reason')}, "
                  f"{row.get('out_tokens')} tokens, {row.get('seconds')} s; ${spent():.4f}", flush=True)


def _median(xs):
    xs = sorted(x for x in xs if isinstance(x, (int, float)))
    return None if not xs else (xs[len(xs) // 2] if len(xs) % 2 else (xs[len(xs) // 2 - 1] + xs[len(xs) // 2]) / 2)


def report(results=None):
    results = results or os.path.join(OUT, "RESULTS.jsonl")
    rows = []
    if os.path.exists(results):                  # no call made (stopped at once): an empty report, never a crash
        with open(results) as f:
            rows = [json.loads(x) for x in f]
    legs = {lg: [r for r in rows if r["leg"] == lg] for lg in ("with", "without")}
    pairs = {}
    for r in rows:
        pairs.setdefault(r["record"], {})[r["leg"]] = r
    keys = collections.Counter()
    for p in pairs.values():
        if len(p) == 2:
            a, b = p["with"].get("response_headers") or {}, p["without"].get("response_headers") or {}
            keys.update(k for k in set(a) | set(b) if a.get(k) != b.get(k))     # names are lowercased at capture
    bf = {lg: dict(collections.Counter(f"{k}: {v}" for r in rs for at in (r.get("attempts") or [r])
                                       for k, v in (at.get("response_headers") or {}).items() if k.startswith("x-bf")))
          for lg, rs in legs.items()}                                          # the VALUES, per leg (glm F10b)
    s = {"at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "records": len(pairs), "calls": len(rows),
         "usd_reported": round(sum(float(r.get("usd_reported") or 0) for r in rows), 6)}
    for lg, rs in legs.items():
        s[lg] = {"calls": len(rs), "errors": sum(1 for r in rs if r.get("error")),
                 "unclosed": sum(1 for r in rs if r.get("unclosed")),
                 "shapes": dict(collections.Counter(r.get("shape") or "error" for r in rs)),
                 "finish_reason_unclosed": dict(collections.Counter(str(r.get("finish_reason"))
                                                                    for r in rs if r.get("unclosed"))),
                 "finish_reason_all": dict(collections.Counter(str(r.get("finish_reason")) for r in rs)),
                 "response_models": dict(collections.Counter(str(r.get("response_model")) for r in rs)),
                 "out_tokens_median": _median([r.get("out_tokens") for r in rs]),
                 "out_tokens_median_unclosed": _median([r.get("out_tokens") for r in rs if r.get("unclosed")])}
    s["headers_differing_within_a_pair"] = dict(keys.most_common())
    s["x_bf_response_headers"] = bf
    s["retried_calls"] = sum(1 for r in rows if len(r.get("attempts") or []) > 1)
    with open(os.path.join(OUT, "SUMMARY.json"), "w") as f:
        json.dump(s, f, indent=1)
    w, wo = s["with"], s["without"]
    L = ["# RULING 114: V4 ON AN XINFER WORKER (the x-bf-tunnel-instance header)", "",
         f"{RY.MODEL}, response_format json_object, reasoning_effort none, each record's own max_tokens / seed / "
         f"system (as replay111). {s['records']} of replay111's 93 unclosed records, each asked WITH the header "
         f"`x-bf-tunnel-instance: pinga282` and WITHOUT it, the same seed. ${s['usd_reported']:.4f} reported.", "",
         "| | calls | errors | unclosed | finish_reason of the unclosed | out_tokens median (unclosed) | shapes |",
         "|---|---|---|---|---|---|---|",
         f"| with the header | {w['calls']} | {w['errors']} | {w['unclosed']} | {w['finish_reason_unclosed']} | "
         f"{w['out_tokens_median']} ({w['out_tokens_median_unclosed']}) | {w['shapes']} |",
         f"| without | {wo['calls']} | {wo['errors']} | {wo['unclosed']} | {wo['finish_reason_unclosed']} | "
         f"{wo['out_tokens_median']} ({wo['out_tokens_median_unclosed']}) | {wo['shapes']} |", "",
         f"- x-bf-* response headers and their values (every attempt), with the header: {bf['with'] or 'none'}; "
         f"without: {bf['without'] or 'none'}.",
         f"- Calls retried by the gateway client (429 / 5xx; every attempt's headers kept): {s['retried_calls']}.",
         f"- Response headers whose value differs between the two legs of a record (count of records): "
         f"{s['headers_differing_within_a_pair'] or 'none'}.",
         f"- The model each response names: with {w['response_models']}; without {wo['response_models']}."]
    with open(os.path.join(OUT, "REPORT.md"), "w") as f:
        f.write("\n".join(L) + "\n")
    return s


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=N)
    ap.add_argument("--report-only", action="store_true")
    a = ap.parse_args(argv)
    if not a.report_only:
        run(a.n)
    print(json.dumps(report(), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
