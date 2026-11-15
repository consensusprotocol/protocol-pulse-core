# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261115_1418
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 258 s finish=stop usage in 11543 / out 6846 usd_reported=0.001207 usd~0.137 (upper-bound price)

# Code Audit: replay114 (RULING 114)

**Scope**: `tests/package/replay114.py` + `tests/package/test_replay114.py`. Nothing in `pipeline/` changes; no build reads these outputs; Heimdall-only, cap $0.15. I audit against the stated order and the stated checks (1)–(5).

---

## Findings

### [P1] F1 — `pick()` can return fewer than `n` records silently, and the spread arithmetic breaks when `k` divides unevenly
`replay114.py:55-66`

```python
rest = [r for r in rows if r not in first]
k = min(n - len(first), len(rest))
return first + [rest[int(i * len(rest) / k)] for i in range(k)] if k > 0 else first[:n]
```

Three defects in one expression:

1. **`r not in first` uses `==` on dicts.** Two *distinct* records with identical content (same prompt/max_tokens/seed/system — plausible: replay111 asked the same record text at different stages) compare equal, so the second one is dropped from `rest` and the "30 **distinct** records" guarantee silently becomes 29. The order says "30 of the 93 records … (the same 5 I sent the team among them)". Identity should be by `record` key, not dict equality: `rest = [r for r in rows if r["record"] not in {x["record"] for x in first}]`.
2. **`k` can be 0 while `n - len(first) > 0`** when `len(rest) == 0` — then the ternary yields `first[:n]`, which is fine, but if `len(rest) > 0` and `n - len(first) == 0`, `k=0` and the ternary's *else* branch returns `first[:n]` — correct. However when `k > 0`, `int(i * len(rest) / k)` for `i in range(k)` can pick the **same index twice** (e.g. `len(rest)=7, k=5`: indices 0,1,2,4,5 — fine; but `len(rest)=3, k=3` → 0,1,2 fine; `len(rest)=5, k=4` → 0,1,2,3 — fine; the real risk: `len(rest)=4, k=3` → 0,1,2 — fine). Actually the classic failure: `len(rest)=6, k=5` → `int(i*6/5)` = 0,1,2,3,4 — fine. The genuinely broken case is **duplicates in `rest`** (see 1) making `len(rest)` overcount relative to distinct records, so the "spread evenly" claim in the report is computed over a multiset, not a set.
3. **No guard that `len(first) <= n`.** If a future order names more than `n` out_tokens (NAMED grows, `--n` lowered), `first` alone exceeds `n` and the function returns more than `n` records; `run()` then spends past the intended sample. Today NAMED=5, N=30, so latent.

Also: `pick` raises `ValueError` if any named out_tokens value is missing — good fail-closed behavior, but the error message doesn't say which value, which will cost a debugging round-trip when replay111's fixture changes.

**Fix**: key by `record`; `k = max(0, min(n - len(first), len(rest)))`; include the missing token in the `ValueError`; assert `len(got) == len(set(r["record"] for r in got))`.

---

### [P2] F2 — Spend ledger: read-modify-write race and a lost-update window; also `usd_reported` key mismatch risk
`replay114.py:131-146, 167-172`

`add_spend` does read→add→tmp→`os.replace` with no lock. "One call at a time" is enforced only by convention (the driver is single-threaded today), but the order says "no call starts once it holds STOP_USD" — the check `if spent() >= stop_usd` happens **before** the call, and the cost is added **after** it, so a call that starts just under the cap can overshoot: with ~$0.0003/call and a $0.14 stop against a $0.15 order, the overshoot is bounded (~1 call, ~$0.0003) — acceptable, but the *last* call's cost is added even if it pushes past the cap, and there's no final reconciliation. Also `add_spend(row.get("usd_reported"))` — if the response's usage lacks `usd_reported` (the fake gateway's usage has `cost`, not `usd_reported`!), the ledger adds 0.0 and the run never stops. Note the test's `Gateway` returns `{"cost": 0.0001}` while the driver reads `usage.get("usd_reported")` — the test passes only because it never exercises the cap via the real key. **The test's fake and the driver's read disagree on the usage key** — that's exactly the kind of drift the test should catch. (The driver's `usd_reported=usage.get("usd_reported")` at line 125 reads the *parsed* usage dict from `backend.complete`'s return, whose shape is replay111's contract — but the fake gateway's `usage` block is what `Capture` sees, and `Capture` stores `usage=j.get("usage")` — so the row's `usd_reported` comes from the *raw* usage, while `out` comes from `completion_tokens` **or** `usage.get("out")` — two different usage shapes consulted in one function. Pick one contract and assert it.)

Wait — checking more carefully: `ask()` line 123-124: `u = cap.seen.get("usage") or {}` then `out = int(u.get("completion_tokens") or u.get("out") or 0)`. And line 125: `usd_reported=usage.get("usd_reported")` — **`usage` here is the value returned by `backend.complete`, not `u`**. So the row's `out_tokens` comes from the *response* usage, while `usd_reported` comes from the *backend's* return. If the backend's return usage lacks `usd_reported` (or the response's us

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 126 s finish=stop usage in 12879 / out 4277 usd_reported=0.004952 usd~0.103 (upper-bound price)

I have reviewed the code in `C1_STEP.diff` against the provided context, laws, and specific check requests.

### Contextual Note
The "Governing Laws" provided in the prompt (SENTENCE LAW, SELECTION LOCK, etc.) pertain to a video editing pipeline (`pipeline/run_fresh.py`, `sentence_law.py`). The code under review (`tests/package/replay114.py`) is a **network diagnostic tool** for an LLM API gateway (Heimdall/xinfer). It does not interact with the video pipeline, does not modify `pipeline/` code, and does not touch the video assets. Therefore, the video-specific laws (L-a through L-l, SENTENCE LAW, etc.) are **not applicable** to this specific diff. The audit focuses on the correctness, security, and robustness of the diagnostic script itself, as requested in the "PLEASE CHECK" section.

### Findings

**1. [P1] Spend Cap Check Occurs After State Mutation (Race Condition / Overspend)**
In `replay114.py`, the `run()` function checks the spend cap *before* making a call, but the `add_spend` function updates the ledger *after* the call completes.
```python
# Line 167-169
if spent() >= stop_usd:
    print(...)
    return
# Line 170-172
row = dict(ask(b, rec, leg), ...)
add_spend(row.get("usd_reported"))
```
While the check `spent() >= stop_usd` happens before `ask`, the `add_spend` happens after. If the current spend is $0.139 and the cap is $0.14, the check passes. The call is made. If that call costs $0.002, the new spend is $0.141. The loop continues to the next record. The check `spent() >= stop_usd` will now fail, and it will stop.
However, the requirement is "no call starts once it holds STOP_USD". The code *does* prevent the *next* call from starting if the cap is exceeded. But there is a subtle issue: `add_spend` reads the file, adds, and writes. If `ask` fails (exception), `add_spend` is still called with `row.get("usd_reported")` which might be `None` or 0. This is handled.
The real risk is if `spent()` reads a stale value or if the file write in `add_spend` is not atomic enough for concurrent reads (though this is single-threaded).
Actually, looking closer at `add_spend`:
```python
def add_spend(usd, path=None):
    path = path or SPEND
    d = {"usd_reported": round(spent(path) + float(usd or 0.0), 8)}
    with open(path + ".tmp", "w") as f:
        json.dump(d, f)
    os.replace(path + ".tmp", path)
```
This is atomic. The logic holds: Check -> Call -> Update. The next iteration checks the updated value. This is correct for a single-threaded script.
**However**, there is a logic flaw in `pick` and `run` interaction regarding the "named" records.
In `pick`, it returns a list of 30 records.
In `run`, it iterates `for i, src in enumerate(pick(unclosed(), n))`.
If the script is interrupted and resumed, `pick` is called again. `pick` is deterministic (sorts by `out_tokens` and `record`). So it will pick the same 30 records.
The `done` set is built from `RESULTS.jsonl`.
This seems robust.

Let's look at **Security/Leakage** (Check 2).
The `Capture` class:
```python
def __call__(self, url, body, headers, timeout):
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", **headers, **self.extra})
    # ...
    self.seen = {"status": resp.status, "response_headers": dict(resp.headers.items())}
```
It stores `response_headers`. It does **not** store `headers` (the request headers).
The `ask` function:
```python
row = {"leg": leg, "x_bf_header_sent": leg == "with", "seed": seed, "max_tokens": mt}
# ...
row.update(seconds=round(secs, 2), **cap.seen, out_tokens=out, ...)
```
`cap.seen` contains `status`, `response_headers`, `id`, `finish_reason`, `usage`, `response_model`.
It does **not** contain the request `Authorization` header.
The test `test_the_header_only_on_its_leg_the_same_request_otherwise_and_no_key_in_a_row` verifies that `KEY` is not in the row.
This looks correct.

**2. [P1] `pick` Function Logic Error with `k=0`**
In `replay114.py`:
```python
def pick(rows, n=N, named=NAMED):
    # ...
    rest = [r for r in rows if r not in first]
    k = min(n - len(first), len(rest))
    return first + [rest[int(i * len(rest) / k)] for i in range(k)] if k > 0 else first[:n]
```
If `n` (30) is less than `len(first)` (5), `k` becomes negative? No, `min` handles it.
If `n` is 30, `len(first)` is 5. `k = min(25, len(rest))`.
If `len(rest)` is 0 (only 5 unclosed records exist), `k=0`.
Return `first[:n]` -> `first[:30]` -> `first` (5 items).
This is correct.
However, if `n` is 30, and `len(first)` is 5, and `len(rest)` is 10. `k = 10`.
`rest[int(i * 10 / 10)]` for `i` in `0..9`.
Indices: `0, 1, 2, 3, 4, 5, 6, 7, 8, 9`.
This picks all 10.
Total 15.
This is correct.

**3. [P2] `shape_of` Potential Crash on Non-String Text**
```python
def shape_of(text, out_tokens, cap):
    t = (text or "").strip()
    t

## CLAUDE'S CYCLE 1 CONSENSUS
# C1 CONSENSUS — pp-selectid audit 20261115_1418 (ruling 114's x-bf-tunnel-instance replay, tests/package/replay114.py)

Reviewers: qwen3.8-27b (P1_OR_WORSE: 1) and glm-5.3-flash (P1_OR_WORSE: 1). Both raise a P1, so they agree on the
count and Grok was not asked. Cycle 1: $0.0062 vendor-reported. No paid call of the driver has been made.

THE TWO P1s:
1. qwen [P1] "`usage` may be None if backend.complete returns None for it". replay111.FormatBackend.complete always
   returns a dict (tests/package/replay111.py:84-86, UNCHANGED), so it cannot happen today; GUARDED anyway
   (`usage or {}`), as a defence that costs nothing.
2. glm [P1] F1 "pick() compares whole dicts (`r not in first`), so two rows with the same content collapse; distinct
   records are not guaranteed". FIXED: the rows are de-duplicated BY RECORD PATH first (one row a record), and the
   rest is taken by record path, never by dict equality. The test now feeds a record twice and still gets 30 distinct
   records. On the real file the pick is unchanged: 30 distinct records, the five named first (7, 122, 171, 497, 1564).

THE P2s ACTED ON:
3. glm F18 "a call retried by providers._with_backoff (429 / 5xx) keeps only the LAST attempt's headers; an earlier
   attempt's instance header is exactly the evidence probed". FIXED: Capture keeps every attempt's status and headers
   in order ("attempts"); the row's top level is the last. New test: a 429 (x-bf-instance vllm-3) then a 200
   (pinga282): both kept. The report counts retried calls.
4. glm F10 "header names compared case-sensitively". FIXED: names are lowercased at capture (headers_of), a repeated
   header's values joined in order, so the differing-headers count compares like with like.
5. glm F10b "the report names the x-bf headers but not their VALUES (the instance names)". FIXED: the report lists
   every x-bf header with its value and count, per leg, over every attempt.
6. glm F3 "a 200 whose body is not JSON loses everything". FIXED: the first 500 characters of such a body are kept
   (diagnosis only). (The gateway's body is JSON; it is the content inside it that comes back unclosed.)
7. qwen "a corrupted spend ledger reads as $0 and lets calls past the cap". FIXED: a ledger that exists but cannot be
   read stops the run (RuntimeError) before any call; no ledger yet is $0. New test: no call is made.
8. qwen "an unreadable record file crashes the run". FIXED: an error row for each leg, no call.
9. qwen "shape_of on a non-string". GUARDED: str(text or "").

THE OTHERS:
10. glm F2 "the ledger is read-modify-write with no lock; the check is before the call and the cost after, so the last
    call may pass the stop". The driver is single-threaded by design (one call at a time); the stop is $0.14 against
    the order's $0.15 cap, and a call is ~$0.0003 (replay111: 96 step-A calls $0.032), so the overshoot is at most one
    call. No change.
11. glm F5 "on a resume, which leg goes first depends on the pick index". The source (repla

---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261115_1418/C2_STEP.diff (435 lines)
```
   1 | diff --git a/tests/package/replay114.py b/tests/package/replay114.py
   2 | new file mode 100644
   3 | index 0000000..0184400
   4 | --- /dev/null
   5 | +++ b/tests/package/replay114.py
   6 | @@ -0,0 +1,264 @@
   7 | +#!/usr/bin/env python3
   8 | +"""RULING 114 (orchestrator 13:18 ET Nov 15): V4 ON AN XINFER WORKER. The Heimdall team: the unclosed JSON is "the
   9 | +usual vllm schema problem; the xinfer workers don't have this issue", and a request carrying the HTTP header
  10 | +x-bf-tunnel-instance: pinga282 goes to an xinfer worker IF the gateway forwards the header.
  11 | +(a) 30 of the 93 records that came back unclosed ("truncated") in replay111, the five the team was sent among them
  12 | +    (out_tokens 7, 122, 171, 497, 1564), asked exactly as replay111 asked them (replay111.FormatBackend: the v4
  13 | +    abliterated, response_format json_object, reasoning_effort none; the record's own max_tokens, seed and system),
  14 | +    ONCE WITH the header and ONCE WITHOUT, at the same seed. The legs alternate which goes first.
  15 | +(b) Per call: finish_reason, the response's id, EVERY response header, out_tokens, seconds, the answer's shape
  16 | +    (closed JSON, or replay111.shape) and its text (diagnosis only, never a verdict). Our own request's headers are
  17 | +    NEVER recorded (the Authorization is among them): a row says only whether the x-bf header was sent.
  18 | +(c) REPORT.md: unclosed with / without the header; the response headers that differ between the legs (an instance
  19 | +    name would show there); finish_reason counts for the unclosed answers.
  20 | +SPEND: Heimdall only, vendor-reported (usage.cost), on its own ledger SPEND_R114.json; no call starts once it holds
  21 | +STOP_USD ($0.14 of the order's $0.15). One call at a time. No routing change: nothing here is read by a build.
  22 | +Usage: python3 -B tests/package/replay114.py [--n 30] [--report-only]"""
  23 | +import argparse
  24 | +import collections
  25 | +import contextlib
  26 | +import json
  27 | +import os
  28 | +import sys
  29 | +import time
  30 | +import urllib.error
  31 | +import urllib.request
  32 | +
  33 | +HERE = os.path.dirname(os.path.abspath(__file__))
  34 | +REPO = os.path.dirname(os.path.dirname(HERE))
  35 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
  36 | +sys.path.insert(0, HERE)
  37 | +import providers as P  # noqa: E402
  38 | +import replay111 as RY  # noqa: E402
  39 | +
  40 | +WT = RY.WT
  41 | +OUT = os.path.join(WT, "tests", "package", "proof", "replay114")
  42 | +SPEND = os.path.join(WT, "tests", "package", "proof", "SPEND_R114.json")
  43 | +SOURCE = os.path.join(RY.OUT, "OUT_OF_CONTRACT.jsonl")
  44 | +HEADER = {"x-bf-tunnel-instance": "pinga282"}
  45 | +NAMED = (7, 122, 171, 497, 1564)
  46 | +N, STOP_USD = 30, 0.14
  47 | +
  48 | +
  49 | +def unclosed(path=SOURCE):
  50 | +    """replay111's unclosed answers: its out-of-contract rows of shape "truncated"."""
  51 | +    with open(path) as f:
  52 | +        return [r for r in map(json.loads, f) if r.get("shape") == "truncated"]
  53 | +
  54 | +
  55 | +def pick(rows, n=N, named=NAMED):
  56 | +    """One record for each named out_tokens first, then the others spread evenly in out_tokens order (ties by record)."""
  57 | +    rows = sorted({r["record"]: r for r in reversed(rows)}.values(),      # one row a record (glm F1), then sorted
  58 | +                  key=lambda r: (r.get("out_tokens") or 0, r["record"]))
  59 | +    first = []
  60 | +    for t in named:
  61 | +        hit = [r for r in rows if r.get("out_tokens") == t]
  62 | +        if not hit:
  63 | +            raise ValueError(f"no unclosed record with out_tokens {t}")
  64 | +        first.append(hit[0])
  65 | +    taken = {r["record"] for r in first}
  66 | +    rest = [r for r in rows if r["record"] not in taken]
  67 | +    k = min(n - len(first), len(rest))
  68 | +    return first + [rest[int(i * len(rest) / k)] for i in range(k)] if k > 0 else first[:n]
  69 | +
  70 | +
  71 | +def headers_of(msg):
  72 | +    """Every response header, names lowercased, a repeated header's values joined in order (RFC 9110 5.3)."""
  73 | +    out = {}
  74 | +    for k, v in (msg.items() if msg is not None else ()):
  75 | +        out[k.lower()] = f"{out[k.lower()]}, {v}" if k.lower() in out else v
  76 | +    return out
  77 | +
  78 | +
  79 | +class Capture:
  80 | +    """providers._http_json for one call, with `extra` headers added. It keeps the RESPONSE of EVERY attempt
  81 | +    (providers._with_backoff may retry a 429 / 5xx: each attempt's status and headers are kept in "attempts", in
  82 | +    order; audit 1418 C1, glm F18) and the last one's status, headers, id, finish_reason, usage and model. The
  83 | +    request's own headers are never kept."""
  84 | +
  85 | +    def __init__(self, extra):
  86 | +        self.extra, self.seen = dict(extra), {"attempts": []}
  87 | +
  88 | +    def _attempt(self, status, msg):
  89 | +        a = {"status": status, "response_headers": headers_of(msg)}
  90 | +        self.seen = dict(a, attempts=self.seen["attempts"] + [a])
  91 | +
  92 | +    def __call__(self, url, body, headers, timeout):
  93 | +        req = urllib.request.Request(url, data=json.dumps(body).encode(),
  94 | +                                     headers={"Content-Type": "application/json", **headers, **self.extra})
  95 | +        try:
  96 | +            with urllib.request.urlopen(req, timeout=timeout) as resp:
  97 | +                raw = resp.read()
  98 | +                self._attempt(resp.status, resp.headers)
  99 | +        except urllib.error.HTTPError as e:
 100 | +            self._attempt(e.code, e.headers)
 101 | +            raise
 102 | +        try:
 103 | +            j = json.loads(raw)
 104 | +        except ValueError:
 105 | +            self.seen["body_head"] = raw[:500].decode("utf-8", "replace")    # diagnosis only (glm F3)
 106 | +            raise
 107 | +        ch = ((j.get("choices") or [{}])[0] or {}) if isinstance(j, dict) else {}
 108 | +        self.seen.update(id=j.get("id"), finish_reason=ch.get("finish_reason"), usage=j.get("usage"),
 109 | +                         response_model=j.get("model"))
 110 | +        return j
 111 | +
 112 | +
 113 | +@contextlib.contextmanager
 114 | +def capturing(extra):
 115 | +    real, cap = P._http_json, Capture(extra)
 116 | +    P._http_json = cap
 117 | +    try:
 118 | +        yield cap
 119 | +    finally:
 120 | +        P._http_json = real
 121 | +
 122 | +
 123 | +def shape_of(text, out_tokens, cap):
 124 | +    t = str(text or "").strip()
 125 | +    try:
 126 | +        json.loads(t)
 127 | +        return "closed JSON"
 128 | +    except ValueError:
 129 | +        return RY.shape(text, out_tokens, cap)
 130 | +
 131 | +
 132 | +def ask(backend, rec, leg):
 133 | +    """One call of `rec` on the v4 backend, leg "with" (the header) or "without" -> its row."""
 134 | +    mt, seed = int(rec.get("max_tokens") or 2000), int(rec.get("seed") or 7)
 135 | +    row = {"leg": leg, "x_bf_header_sent": leg == "with", "seed": seed, "max_tokens": mt}
 136 | +    t0 = time.time()
 137 | +    with capturing(HEADER if leg == "with" else {}) as cap:
 138 | +        try:
 139 | +            text, usage, secs = backend.complete(rec["prompt"], mt, seed, system=rec.get("system"))
 140 | +        except Exception as e:                            # noqa: BLE001  any failure is a row, never the run's end
 141 | +            row.update(seconds=round(time.time() - t0, 2), error=f"{type(e).__name__}: {str(e)[:200]}", **cap.seen)
 142 | +            return row
 143 | +    u, usage = cap.seen.get("usage") or {}, usage or {}
 144 | +    out = int(u.get("completion_tokens") or usage.get("out") or 0)
 145 | +    row.update(seconds=round(secs, 2), **cap.seen, out_tokens=out, usd_reported=usage.get("usd_reported"),
 146 | +               shape=shape_of(text, out, backend.max_out(mt)), text=text[:6000])
 147 | +    row["unclosed"] = row["shape"] == "truncated"
 148 | +    return row
 149 | +
 150 | +
 151 | +def spent(path=None):
 152 | +    """The ledger's vendor-reported total (SPEND, read when called): 0.0 when there is none yet; a ledger that exists
 153 | +    but cannot be read stops the run (fail closed: never a $0 that lets calls past the cap; audit 1418 C1, qwen)."""
 154 | +    path = path or SPEND
 155 | +    if not os.path.exists(path):
 156 | +        return 0.0
 157 | +    try:
 158 | +        with open(path) as f:
 159 | +            return float(json.load(f)["usd_reported"])
 160 | +    except (OSError, ValueError, KeyError, TypeError) as e:
 161 | +        raise RuntimeError(f"replay114: the spend ledger {path} cannot be read ({type(e).__name__}): refused") from e
 162 | +
 163 | +
 164 | +def add_spend(usd, path=None):
 165 | +    path = path or SPEND
 166 | +    d = {"usd_reported": round(spent(path) + float(usd or 0.0), 8)}
 167 | +    with open(path + ".tmp", "w") as f:
 168 | +        json.dump(d, f)
 169 | +    os.replace(path + ".tmp", path)
 170 | +
 171 | +
 172 | +def backend():
 173 | +    r = RY.build_router(("none",), spend_path=None)
 174 | +    return r.backends[RY.bname("none")]
 175 | +
 176 | +
 177 | +def run(n=N, b=None, stop_usd=STOP_USD, results=None):
 178 | +    results = results or os.path.join(OUT, "RESULTS.jsonl")
 179 | +    os.makedirs(os.path.dirname(results), exist_ok=True)
 180 | +    b = b or backend()
 181 | +    done = set()
 182 | +    if os.path.exists(results):
 183 | +        with open(results) as f:
 184 | +            done = {(x["record"], x["leg"]) for x in map(json.loads, f)}
 185 | +    for i, src in enumerate(pick(unclosed(), n)):
 186 | +        try:
 187 | +            with open(os.path.join(WT, src["record"])) as f:
 188 | +                rec = json.load(f)
 189 | +        except (OSError, ValueError) as e:             # no call: an error row for each leg (audit 1418 C1, qwen)
 190 | +            rec = {"error": f"the record cannot be read ({type(e).__name__})"}
 191 | +        for leg in (("with", "without") if i % 2 == 0 else ("without", "with")):
 192 | +            if (src["record"], leg) in done:
 193 | +                continue
 194 | +            if spent() >= stop_usd:
 195 | +                print(f"replay114: stopped at ${spent():.4f} (stop ${stop_usd:.2f})", flush=True)
 196 | +                return
 197 | +            row = dict(ask(b, rec, leg) if "error" not in rec else {"leg": leg, "error": rec["error"]},
 198 | +                       record=src["record"], type=src["type"], replay111_out_tokens=src.get("out_tokens"), order=i)
 199 | +            add_spend(row.get("usd_reported"))
 200 | +            with open(results, "a") as f:
 201 | +                f.write(json.dumps(row) + "\n")
 202 | +            print(f"  {i + 1}/{n} {leg}: {row.get('shape') or row.get('error')}, {row.get('finish_reason')}, "
 203 | +                  f"{row.get('out_tokens')} tokens, {row.get('seconds')} s; ${spent():.4f}", flush=True)
 204 | +
 205 | +
 206 | +def report(results=None):
 207 | +    results = results or os.path.join(OUT, "RESULTS.jsonl")
 208 | +    with open(results) as f:
 209 | +        rows = [json.loads(x) for x in f]
 210 | +    legs = {lg: [r for r in rows if r["leg"] == lg] for lg in ("with", "without")}
 211 | +    pairs = {}
 212 | +    for r in rows:
 213 | +        pairs.setdefault(r["record"], {})[r["leg"]] = r
 214 | +    keys = collections.Counter()
 215 | +    for p in pairs.values():
 216 | +        if len(p) == 2:
 217 | +            a, b = p["with"].get("response_headers") or {}, p["without"].get("response_headers") or {}
 218 | +            keys.update(k for k in set(a) | set(b) if a.get(k) != b.get(k))     # names are lowercased at capture
 219 | +    bf = {lg: dict(collections.Counter(f"{k}: {v}" for r in rs for at in (r.get("attempts") or [r])
 220 | +                                       for k, v in (at.get("response_headers") or {}).items() if k.startswith("x-bf")))
 221 | +          for lg, rs in legs.items()}                                          # the VALUES, per leg (glm F10b)
 222 | +    s = {"at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "records": len(pairs), "calls": len(rows),
 223 | +         "usd_reported": round(sum(float(r.get("usd_reported") or 0) for r in rows), 6)}
 224 | +    for lg, rs in legs.items():
 225 | +        s[lg] = {"calls": len(rs), "errors": sum(1 for r in rs if r.get("error")),
 226 | +                 "unclosed": sum(1 for r in rs if r.get("unclosed")),
 227 | +                 "shapes": dict(collections.Counter(r.get("shape") or "error" for r in rs)),
 228 | +                 "finish_reason_unclosed": dict(collections.Counter(str(r.get("finish_reason"))
 229 | +                                                                    for r in rs if r.get("unclosed"))),
 230 | +                 "finish_reason_all": dict(collections.Counter(str(r.get("finish_reason")) for r in rs)),
 231 | +                 "response_models": dict(collections.Counter(str(r.get("response_model")) for r in rs))}
 232 | +    s["headers_differing_within_a_pair"] = dict(keys.most_common())
 233 | +    s["x_bf_response_headers"] = bf
 234 | +    s["retried_calls"] = sum(1 for r in rows if len(r.get("attempts") or []) > 1)
 235 | +    with open(os.path.join(OUT, "SUMMARY.json"), "w") as f:
 236 | +        json.dump(s, f, indent=1)
 237 | +    w, wo = s["with"], s["without"]
 238 | +    L = ["# RULING 114: V4 ON AN XINFER WORKER (the x-bf-tunnel-instance header)", "",
 239 | +         f"{RY.MODEL}, response_format json_object, reasoning_effort none, each record's own max_tokens / seed / "
 240 | +         f"system (as replay111). {s['records']} of replay111's 93 unclosed records, each asked WITH the header "
 241 | +         f"`x-bf-tunnel-instance: pinga282` and WITHOUT it, the same seed. ${s['usd_reported']:.4f} reported.", "",
 242 | +         "| | calls | errors | unclosed | finish_reason of the unclosed | shapes |", "|---|---|---|---|---|---|",
 243 | +         f"| with the header | {w['calls']} | {w['errors']} | {w['unclosed']} | {w['finish_reason_unclosed']} | "
 244 | +         f"{w['shapes']} |",
 245 | +         f"| without | {wo['calls']} | {wo['errors']} | {wo['unclosed']} | {wo['finish_reason_unclosed']} | "
 246 | +         f"{wo['shapes']} |", "",
 247 | +         f"- x-bf-* response headers and their values (every attempt), with the header: {bf['with'] or 'none'}; "
 248 | +         f"without: {bf['without'] or 'none'}.",
 249 | +         f"- Calls retried by the gateway client (429 / 5xx; every attempt's headers kept): {s['retried_calls']}.",
 250 | +         f"- Response headers whose value differs between the two legs of a record (count of records): "
 251 | +         f"{s['headers_differing_within_a_pair'] or 'none'}.",
 252 | +         f"- The model each response names: with {w['response_models']}; without {wo['response_models']}."]
 253 | +    with open(os.path.join(OUT, "REPORT.md"), "w") as f:
 254 | +        f.write("\n".join(L) + "\n")
 255 | +    return s
 256 | +
 257 | +
 258 | +def main(argv=None):
 259 | +    ap = argparse.ArgumentParser()
 260 | +    ap.add_argument("--n", type=int, default=N)
 261 | +    ap.add_argument("--report-only", action="store_true")
 262 | +    a = ap.parse_args(argv)
 263 | +    if not a.report_only:
 264 | +        run(a.n)
 265 | +    print(json.dumps(report(), indent=1))
 266 | +    return 0
 267 | +
 268 | +
 269 | +if __name__ == "__main__":
 270 | +    sys.exit(main())
 271 | diff --git a/tests/package/test_replay114.py b/tests/package/test_replay114.py
 272 | new file mode 100644
 273 | index 0000000..6de6f32
 274 | --- /dev/null
 275 | +++ b/tests/package/test_replay114.py
 276 | @@ -0,0 +1,158 @@
 277 | +#!/usr/bin/env python3
 278 | +"""RULING 114: the x-bf-tunnel-instance replay (tests/package/replay114.py). Offline: urlopen is replaced by a fake
 279 | +gateway; the key is a fake one; files go to a temporary directory."""
 280 | +import io
 281 | +import json
 282 | +import os
 283 | +import sys
 284 | +import tempfile
 285 | +import unittest
 286 | +from email.message import Message
 287 | +from unittest import mock
 288 | +
 289 | +HERE = os.path.dirname(os.path.abspath(__file__))
 290 | +sys.path.insert(0, HERE)
 291 | +import replay114 as RT  # noqa: E402
 292 | +
 293 | +KEY = "sk-FAKE-KEY-never-in-a-row"
 294 | +
 295 | +
 296 | +class Gateway:
 297 | +    """A fake Heimdall: answers each request from `answers` (text, finish_reason), with response headers that name the
 298 | +    instance (x-bf-instance) by whether the request carried the header; it keeps every request it saw."""
 299 | +
 300 | +    def __init__(self, answers):
 301 | +        self.answers, self.seen = list(answers), []
 302 | +
 303 | +    def __call__(self, req, timeout=None):
 304 | +        self.seen.append({"headers": {k.lower(): v for k, v in req.header_items()}, "body": json.loads(req.data)})
 305 | +        text, fin = self.answers.pop(0)
 306 | +        sent = "x-bf-tunnel-instance" in self.seen[-1]["headers"]
 307 | +        h = Message()
 308 | +        h["x-bf-instance"] = "pinga282" if sent else "vllm-7"
 309 | +        h["content-type"] = "application/json"
 310 | +        body = {"id": f"chatcmpl-{len(self.seen)}", "model": "deepseek/deepseek-v4-flash-0731-abliterated",
 311 | +                "choices": [{"message": {"content": text}, "finish_reason": fin}],
 312 | +                "usage": {"prompt_tokens": 100, "completion_tokens": 50, "cost": 0.0001}}
 313 | +        r = io.BytesIO(json.dumps(body).encode())
 314 | +        r.status, r.headers = 200, h
 315 | +        return r
 316 | +
 317 | +
 318 | +def rec():
 319 | +    return {"prompt": "Judge it.", "max_tokens": 1200, "seed": 28, "system": "Be brief."}
 320 | +
 321 | +
 322 | +class TestPick(unittest.TestCase):
 323 | +    def test_the_named_five_first_then_spread_and_refused_without_one(self):
 324 | +        rows = [{"record": f"r{i:03d}", "type": "t", "out_tokens": t, "shape": "truncated"}
 325 | +                for i, t in enumerate([7, 122, 171, 497, 1564] + list(range(200, 1200, 10)))]
 326 | +        got = RT.pick(rows + [dict(rows[7])], 30)                               # a record twice is one record
 327 | +        self.assertEqual([r["out_tokens"] for r in got[:5]], [7, 122, 171, 497, 1564])
 328 | +        self.assertEqual(len({r["record"] for r in got}), 30)
 329 | +        self.assertLess(got[5]["out_tokens"], got[-1]["out_tokens"])           # spread over the out_tokens order
 330 | +        with self.assertRaises(ValueError):
 331 | +            RT.pick([r for r in rows if r["out_tokens"] != 497], 30)
 332 | +
 333 | +
 334 | +class TestAsk(unittest.TestCase):
 335 | +    def setUp(self):
 336 | +        self.b = RT.backend()
 337 | +        self.b.key = lambda name: KEY
 338 | +
 339 | +    def test_the_header_only_on_its_leg_the_same_request_otherwise_and_no_key_in_a_row(self):
 340 | +        g = Gateway([('{"a": 1', "length"), ('{"a": 1}', "stop")])
 341 | +        with mock.patch("urllib.request.urlopen", g):
 342 | +            w = RT.ask(self.b, rec(), "with")
 343 | +            wo = RT.ask(self.b, rec(), "without")
 344 | +        self.assertEqual(g.seen[0]["headers"].get("x-bf-tunnel-instance"), "pinga282")
 345 | +        self.assertNotIn("x-bf-tunnel-instance", g.seen[1]["headers"])
 346 | +        self.assertEqual(g.seen[0]["body"], g.seen[1]["body"])                     # the same request, same seed
 347 | +        body = g.seen[0]["body"]
 348 | +        self.assertEqual((body["seed"], body["response_format"], body["reasoning_effort"], body["model"]),
 349 | +                         (28, {"type": "json_object"}, "none", "deepseek/deepseek-v4-flash-0731-abliterated"))
 350 | +        self.assertEqual((w["finish_reason"], w["id"], w["out_tokens"], w["shape"], w["unclosed"]),
 351 | +                         ("length", "chatcmpl-1", 50, "truncated", True))
 352 | +        self.assertEqual((wo["shape"], wo["unclosed"], wo["response_headers"]["x-bf-instance"]),
 353 | +                         ("closed JSON", False, "vllm-7"))
 354 | +        self.assertEqual([a["response_headers"]["x-bf-instance"] for a in w["attempts"]], ["pinga282"])
 355 | +        for row in (w, wo):
 356 | +            s = json.dumps(row)
 357 | +            self.assertNotIn(KEY, s)
 358 | +            self.assertNotIn("Bearer", s)
 359 | +            self.assertNotIn("authorization", s.lower())
 360 | +
 361 | +    def test_every_attempt_of_a_retried_call_keeps_its_headers(self):
 362 | +        """glm F18: providers._with_backoff retries a 429; the first attempt's instance header is evidence too."""
 363 | +        import urllib.error
 364 | +        g, n = Gateway([('{"a": 1}', "stop")]), [0]
 365 | +
 366 | +        def flaky(req, timeout=None):
 367 | +            n[0] += 1
 368 | +            if n[0] == 1:
 369 | +                h = Message()
 370 | +                h["X-BF-Instance"] = "vllm-3"
 371 | +                raise urllib.error.HTTPError(req.full_url, 429, "slow down", h, io.BytesIO(b"{}"))
 372 | +            return g(req, timeout)
 373 | +        with mock.patch("urllib.request.urlopen", flaky), mock.patch.object(RT.P, "BACKOFF_S", (0,)):
 374 | +            row = RT.ask(self.b, rec(), "with")
 375 | +        self.assertEqual([(a["status"], a["response_headers"]["x-bf-instance"]) for a in row["attempts"]],
 376 | +                         [(429, "vllm-3"), (200, "pinga282")])                # names lowercased, both kept
 377 | +        self.assertEqual((row["status"], row["shape"]), (200, "closed JSON"))
 378 | +
 379 | +    def test_a_failed_call_is_a_row_with_the_responses_headers(self):
 380 | +        import urllib.error
 381 | +
 382 | +        def refuse(req, timeout=None):
 383 | +            h = Message()
 384 | +            h["x-bf-instance"] = "gw-1"
 385 | +            raise urllib.error.HTTPError(req.full_url, 400, "bad", h, io.BytesIO(b"{}"))
 386 | +        with mock.patch("urllib.request.urlopen", refuse):
 387 | +            row = RT.ask(self.b, rec(), "with")
 388 | +        self.assertIn("error", row)
 389 | +        self.assertEqual((row["status"], row["response_headers"]["x-bf-instance"]), (400, "gw-1"))
 390 | +        self.assertNotIn(KEY, json.dumps(row))
 391 | +
 392 | +
 393 | +class TestRun(unittest.TestCase):
 394 | +    def test_both_legs_alternating_resumed_and_stopped_at_the_cap(self):
 395 | +        with tempfile.TemporaryDirectory() as d:
 396 | +            src = [{"record": f"rec{i}.json", "type": "step_a", "out_tokens": t, "shape": "truncated"}
 397 | +                   for i, t in enumerate((7, 122, 171, 497, 1564, 900))]
 398 | +            for s in src:
 399 | +                with open(os.path.join(d, s["record"]), "w") as f:
 400 | +                    json.dump(rec(), f)
 401 | +            b = RT.backend()
 402 | +            b.key = lambda name: KEY
 403 | +            res, spend = os.path.join(d, "RESULTS.jsonl"), os.path.join(d, "SPEND.json")
 404 | +            real = RT.SPEND
 405 | +            before = os.path.exists(real)
 406 | +            g = Gateway([('{"a": 1}', "stop")] * 12)
 407 | +            with mock.patch.object(RT, "unclosed", lambda: src), mock.patch.object(RT, "WT", d), \
 408 | +                    mock.patch.object(RT, "SPEND", spend), mock.patch("urllib.request.urlopen", g):
 409 | +                RT.run(3, b, stop_usd=1.0, results=res)
 410 | +                rows = [json.loads(x) for x in open(res)]
 411 | +                self.assertEqual([r["leg"] for r in rows], ["with", "without", "without", "with", "with", "without"])
 412 | +                RT.run(3, b, stop_usd=1.0, results=res)                         # resumed: nothing asked again
 413 | +                self.assertEqual(len(g.seen), 6)
 414 | +                RT.run(4, b, stop_usd=0.0005, results=res)                      # the ledger holds 0.0006: stopped
 415 | +                self.assertEqual(len(g.seen), 6)
 416 | +                self.assertAlmostEqual(RT.spent(spend), 0.0006)
 417 | +            self.assertEqual(os.path.exists(real), before)                      # the real ledger never touched
 418 | +
 419 | +    def test_an_unreadable_ledger_stops_before_any_call(self):
 420 | +        with tempfile.TemporaryDirectory() as d:
 421 | +            spend = os.path.join(d, "SPEND.json")
 422 | +            with open(spend, "w") as f:
 423 | +                f.write("{torn")
 424 | +            g = Gateway([('{"a": 1}', "stop")])
 425 | +            with mock.patch.object(RT, "SPEND", spend), mock.patch.object(RT, "unclosed", lambda: [
 426 | +                    {"record": f"x{t}.json", "type": "t", "out_tokens": t, "shape": "truncated"} for t in RT.NAMED]), \
 427 | +                    mock.patch("urllib.request.urlopen", g):
 428 | +                with self.assertRaises(RuntimeError):
 429 | +                    RT.run(1, RT.backend(), results=os.path.join(d, "R.jsonl"))
 430 | +            self.assertEqual(g.seen, [])
 431 | +
 432 | +
 433 | +if __name__ == "__main__":
 434 | +    unittest.main()
 435 | 
```

---

pp-selectid: RULING 114 (orchestrator 13:18 ET Nov 15), V4 ON AN XINFER WORKER. A new measurement driver,
tests/package/replay114.py, and its offline tests tests/package/test_replay114.py. Nothing in pipeline/ changes; no
build reads anything this writes; no routing change.

THE ORDER, verbatim: "The Heimdall team read our v4 samples. Jon Pry: the unclosed JSON is "the usual vllm schema
problem; the xinfer workers don't have this issue", and a request carrying the HTTP header x-bf-tunnel-instance:
pinga282 goes to an xinfer worker IF the gateway forwards the header (he has asked Thanos whether it does; we can
simply try). DO: (a) 30 of the 93 records that came back unclosed in replay111 (the same 5 I sent the team among them:
out_tokens 7, 122, 171, 497, 1564), same settings as replay111 (json_object, reasoning effort none), ONCE WITH the
header and ONCE WITHOUT, same seed. (b) THIS TIME RECORD per call: finish_reason, the response's id, and every
response header (so we can see which instance answered, e.g. any x-bf-* header), plus out_tokens and seconds. Never
log our own request's Authorization. (c) Report: unclosed with header / without header; whether any response header
shows the instance changed; finish_reason counts for the unclosed ones. If the header changes nothing, say so: it may
not be forwarded. (d) Proof to proof/replay114/." Heimdall only, cap $0.15.

THE DRIVER:
- unclosed(): replay111's OUT_OF_CONTRACT.jsonl rows of shape "truncated" (93). pick(): one record for each of the
  five named out_tokens first, then the others spread evenly in out_tokens order -> 30 distinct records (today: 15
  step_a, 14 clips_alone, 1 coherence).
- ask(): the call is replay111's own: replay111.FormatBackend("none").complete(prompt, max_tokens, seed,
  system) with the record's own prompt, max_tokens, seed and system (tests/package/replay111.py:56-87, UNCHANGED:
  model deepseek/deepseek-v4-flash-0731-abliterated, response_format json_object, reasoning_effort "none",
  max_tokens via max_out, temperature from the template spec, the system line + " Reply with one JSON object
  only."). The only change is the transport: capturing() swaps providers._http_json (the function FormatBackend
  calls, providers.py:124-127, UNCHANGED) for a Capture that sends the same request plus the extra header on the
  "with" leg and keeps the RESPONSE's status, every header, id, finish_reason, usage and model. On an HTTP error it
  keeps that response's status and headers and re-raises (providers._with_backoff, UNCHANGED, still retries 429 /
  5xx). The real _http_json is restored in a finally.
- The request's headers (the Authorization among them) are never put in a row: a row holds leg, x_bf_header_sent,
  seed, max_tokens, seconds, status, response_headers, id, finish_reason, usage, response_model, out_tokens,
  usd_reported, shape, unclosed, text (diagnosis only), and the record's id.
- shape_of(): "closed JSON" when the text parses, else replay111.shape (unchanged); unclosed = "truncated".
- run(): one call at a time; the two legs alternate which goes first (record i even: with first); a re-run skips
  (record, leg) pairs already in RESULTS.jsonl; no call starts once SPEND_R114.json holds STOP_USD $0.14
  (vendor-reported usage.cost, added after each call). Calls are ~$0.0003 (replay111: 96 step-A calls $0.032).
- report(): per leg: calls, errors, unclosed, shapes, finish_reason counts (all, and the unclosed); the response
  headers whose value differs between a record's two legs; every x-bf* response header seen; REPORT.md and
  SUMMARY.json.

TESTS (offline: urlopen replaced by a fake gateway, a fake key, temporary files): the pick; the header sent on its
leg only and the two requests otherwise identical (seed, model, response_format, reasoning_effort); the row's fields;
no key, "Bearer" or "authorization" in any row; a failed call is a row with the response's headers; both legs,
alternating, resumed without re-asking, stopped at the cap, and the real ledger never touched. (A first version bound
the ledger path at definition time, so the test's patch missed it: fixed, and the test now checks the real ledger.)

PLEASE CHECK: (1) that the request is byte-for-byte replay111's apart from the one header; (2) that no request header
(the Authorization) can reach a row, the report or a log line; (3) the stop under the cap; (4) the report's counts;
(5) the tests.


---

## CYCLE 2 INSTRUCTIONS

You've now seen what the other models said. This is your final review.

1. WHAT DID THEY CATCH THAT YOU MISSED?
   Review their findings. Be honest about what you overlooked.

2. WHERE DO YOU AGREE OR DISAGREE?
   For each of their key findings: agree / disagree / partially agree + why.

3. NEW FINDINGS FROM THIS REVIEW
   Anything the combined analysis revealed that nobody caught in Cycle 1?

4. REVISED SCORES
   Update your scores from Cycle 1. Did anything change your assessment?
   | Subsystem | Cycle 1 | Cycle 2 | Why changed |

5. FINAL PRIORITY LIST
   Your definitive list of what must change before this ships.
   P0 CRITICAL | P1 HIGH | P2 MEDIUM — cite file and line numbers.

6. THE SINGLE HIGHEST-LEVERAGE CHANGE
   After seeing everything — one sentence. What matters most?

7. PRODUCTION READY?
   Yes / No / Yes with conditions. State your conditions precisely.


Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
