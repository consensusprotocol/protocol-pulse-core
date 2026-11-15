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
    try:
        json.loads(t)
        return "closed JSON"
    except ValueError:
        return RY.shape(text, out_tokens, cap)
```
If `text` is `None`, `t` is `""`. `json.loads("")` raises `ValueError`.
`RY.shape(None, ...)` is called.
In `replay111.py` (not shown, but assumed), `shape` likely handles `None`.
If `text` is a dict (unlikely from API, but possible if parsing failed earlier), `json.loads` expects a string.
`urllib` returns bytes, `json.loads(raw)` in `Capture` returns a dict.
`backend.complete` returns `text`.
If `text` is not a string, `json.loads` will raise `TypeError`, not `ValueError`.
`TypeError` is not caught.
**Severity:** [P2] - Should catch `Exception` or specifically `TypeError` as well, or ensure `text` is a string.

**4. [P2] `add_spend` Rounding Precision**
```python
d = {"usd_reported": round(spent(path) + float(usd or 0.0), 8)}
```
Rounding to 8 decimal places is fine for USD.
However, `spent` reads the file. If the file is corrupted, `spent` returns 0.0.
This is a "fail open" for the spend ledger. If the ledger is lost, the script will think it has spent $0 and continue until the cap is hit again.
Given the cap is $0.14, this is a minor risk, but technically a "fail open" on a financial constraint.
**Severity:** [P2] - Should probably fail closed (raise error) if the ledger file exists but is invalid, or if it's missing on a resume.

**5. [P3] `report` Function: `keys` Counter Logic**
```python
keys = collections.Counter()
for p in pairs.values():
    if len(p) == 2:
        a, b = p["with"].get("response_headers") or {}, p["without"].get("response_headers") or {}
        keys.update(k.lower() for k in set(a) | set(b) if a.get(k) != b.get(k))
```
This counts how many *records* have a differing header.
The report says: "Response headers whose value differs between the two legs of a record (count of records)".
This matches the code.

**6. [P1] `ask` Function: `usage` Variable Shadowing/Confusion**
```python
def ask(backend, rec, leg):
    # ...
    with capturing(HEADER if leg == "with" else {}) as cap:
        try:
            text, usage, secs = backend.complete(rec["prompt"], mt, seed, system=rec.get("system"))
        except Exception as e:
            # ...
    u = cap.seen.get("usage") or {}
    out = int(u.get("completion_tokens") or usage.get("out") or 0)
    row.update(seconds=round(secs, 2), **cap.seen, out_tokens=out, usd_reported=usage.get("usd_reported"), ...)
```
`backend.complete` returns `usage`.
`cap.seen` also contains `usage` (from the raw HTTP response).
`u` is `cap.seen["usage"]`.
`out` is taken from `u` (raw response) or `usage` (backend wrapper).
`usd_reported` is taken from `usage` (backend wrapper).
This assumes `backend.complete` returns a `usage` dict that contains `usd_reported`.
If `backend.complete` returns `None` for usage on error, `usage.get` will crash.
But `ask` catches exceptions from `backend.complete`.
If `backend.complete` succeeds but returns `usage=None`, `usage.get` crashes.
**Severity:** [P1] - Potential `AttributeError` if `backend.complete` returns `None` for usage.

**7. [P2] `run` Function: `src["record"]` Path Construction**
```python
for i, src in enumerate(pick(unclosed(), n)):
    with open(os.path.join(WT, src["record"])) as f:
        rec = json.load(f)
```
`src["record"]` is a path relative to `WT`.
In `unclosed`, `r["record"]` comes from `OUT_OF_CONTRACT.jsonl`.
If `OUT_OF_CONTRACT.jsonl` contains absolute paths or paths with `..`, this could be a path traversal issue, though it's a local test script.
More importantly, if the file doesn't exist, `open` raises `FileNotFoundError`, which is not caught in `run`.
**Severity:** [P2] - Unhandled exception if a record file is missing.

**8. [P3] `test_replay114.py`: `Gateway` Class `pop(0)`**
```python
def __call__(self, req, timeout=None):
    # ...
    text, fin = self.answers.pop(0)
```
If the test makes more calls than `answers` provided, `IndexError` is raised.
The tests provide exactly the right number of answers.
This is fine for tests.

**9. [P1] `replay114.py`: `pick` Function `rest` List Comprehension**
```python
rest = [r for r in rows if r not in first]
```
`r not in first` uses `==` comparison.
`rows` are dicts.
If two records have identical content (same `record`, `type`, `out_tokens`, `shape`), they are indistinguishable.
However, `record` is a unique ID (filename).
So `r not in first` works.
But it is O(N*M). For 93 records, this is fine.

**10. [P2] `replay114.py`: `Capture` Class `__call__` Exception Handling**
```python
except urllib.error.HTTPError as e:
    self.seen = {"status": e.code, "response_headers": dict((e.headers or {}).items())}
    raise
```
It re-raises the `HTTPError`.
In `ask`:
```python
try:
    text, usage, secs = backend.complete(...)
except Exception as e:
    row.update(..., error=f"{type(e).__name__}: {str(e)[:200]}", **cap.seen)
    return row
```
`cap.seen` is updated in the `except` block of `Capture`.
So `cap.seen` will contain the error status/headers.
This is correct.

**11. [P1] `replay114.py`: `ask` Function `secs` Variable**
```python
t0 = time.time()
with capturing(...) as cap:
    try:
        text, usage, secs = backend.complete(...)
    except Exception as e:
        row.update(seconds=round(time.time() - t0, 2), ...)
        return row
# ...
row.update(seconds=round(secs, 2), ...)
```
If `backend.complete` raises an exception, `secs` is not defined in the `except` block, but `time.time() - t0` is used.
If `backend.complete` succeeds, `secs` is returned.
This is correct.

**12. [P2] `replay114.py`: `report` Function `s["usd_reported"]`**
```python
s = {
    # ...
    "usd_reported": round(sum(float(r.get("usd_reported") or 0) for r in rows), 6)
}
```
This sums the `usd_reported` from the rows.
The `add_spend` function also tracks this in `SPEND_R114.json`.
The report uses the rows, not the ledger.
This is consistent.

**13. [P1] `replay114.py`: `pick` Function `k` Calculation**
```python
k = min(n - len(first), len(rest))
return first + [rest[int(i * len(rest) / k)] for i in range(k)] if k > 0 else first[:n]
```
If `n` is 30, `len(first)` is 5. `k = 25`.
`len(rest)` is 88 (93 - 5).
`k = 25`.
`rest[int(i * 88 / 25)]` for `i` in `0..24`.
Indices: `0, 3, 6, 9, 12, 15, 18, 21, 24, 27, 30, 33, 36, 39, 42, 45, 48, 51, 54, 57, 60, 63, 66, 69, 72`.
This picks 25 records from `rest`.
Total 30.
This is correct.

**14. [P2] `replay114.py`: `run` Function `done` Set**
```python
done = set()
if os.path.exists(results):
    with open(results) as f:
        done = {(x["record"], x["leg"]) for x in map(json.loads, f)}
```
If `RESULTS.jsonl` contains a malformed line, `json.loads` raises `JSONDecodeError`.
**Severity:** [P2] - Unhandled exception on resume if log is corrupted.

**15. [P3] `replay114.py`: `main` Function**
```python
def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=N)
    ap.add_argument("--report-only", action="store_true")
    a = ap.parse_args(argv)
    if not a.report_only:
        run(a.n)
    print(json.dumps(report(), indent=1))
    return 0
```
If `run` fails, `report` is still called.
`report` reads `RESULTS.jsonl`. If it doesn't exist, `open` raises `FileNotFoundError`.
**Severity:** [P2] - `report` should handle missing file gracefully or `main` should check.

### Summary of Findings

1.  **[P1] `ask` Function: Potential `AttributeError` if `backend.complete` returns `None` for `usage`.**
    *   `usage.get("usd_reported")` will crash if `usage` is `None`.
    *   Fix: `usage = usage or {}`.

2.  **[P2] `shape_of` Function: `TypeError` not caught.**
    *   `json.loads` raises `TypeError` if input is not a string.
    *   Fix: Catch `Exception` or ensure `text` is a string.

3.  **[P2] `add_spend` Function: Fail-Open on Corrupted Ledger.**
    *   If `SPEND_R114.json` is corrupted, `spent` returns 0.0, allowing overspend.
    *   Fix: Raise error if file exists but is invalid.

4.  **[P2] `run` Function: Unhandled `FileNotFoundError` for Record Files.**
    *   If a record file is missing, the script crashes.
    *   Fix: Catch `FileNotFoundError` and log/skip.

5.  **[P2] `run` Function: Unhandled `JSONDecodeError` on Resume.**
    *   If `RESULTS.jsonl` is corrupted, the script crashes.
    *   Fix: Catch `JSONDecodeError` and skip/log.

6.  **[P2] `report` Function: Unhandled `FileNotFoundError`.**
    *   If `RESULTS.jsonl` is missing, `report` crashes.
    *   Fix: Handle missing file.

7.  **[P3] `pick` Function: O(N*M) Complexity.**
    *   Not an issue for N=93, but worth noting.

8.  **[P3] `test_replay114.py`: `Gateway` `pop(0)` IndexError.**
    *   Not an issue for controlled tests.

P1_OR_WORSE: 1