# qwen3.8-27b (qwen/qwen3.8-27b) 118 s finish=stop usage in 15717 / out 5094 usd_reported=0.004363 usd~0.124 (upper-bound price)

To perform a rigorous code audit of `C1_STEP.diff` (RULING 110: Heimdall Candidates), I will analyze the provided code against the **Governing Laws**, the **Technology Stack**, and the specific **Checklist** items requested.

### Context Analysis
The code introduces `tests/package/replay110.py`, a driver to re-evaluate recorded Grok verdicts (from Ruling 85.1) using two new DeepSeek models via the Heimdall gateway. It also includes `tests/package/test_replay110.py`.

**Key Constraints:**
1.  **No Routing Change:** The code must not alter production routing.
2.  **Spend Control:** Strict limits on API spend ($3.00 limit, $0.75 stop).
3.  **Deadline Logic:** Must correctly classify responses as `in_time`, `late`, `timeout`, `error`, or `out_of_contract` based on Ruling 100's deadlines.
4.  **Data Integrity:** Must reuse Ruling 85.1's records and decision logic (`replay85`).
5.  **Fail Closed:** Errors or missing data must not result in a "pass" or incorrect aggregation.

---

### Findings

#### 1. Classification Logic & Deadline Handling

**[P1] Incorrect `timeout` classification in `replay_one`**
In `replay110.py`, lines 133-139:
```python
    except P.ProviderError as e:
        if "HTTP 429" in str(e):
            sleep(30)
            return None
        row.update(seconds=round(time.time() - t0, 2), heimdall=None, heimdall_error=f"{type(e).__name__}: "
                   f"{str(e)[:200]}", outcome="timeout" if "abandoned at the deadline" in str(e) else "error")
        return row
```
The code checks for the string `"abandoned at the deadline"` to classify a `ProviderError` as a `timeout`. However, the docstring and the `P.ProviderError` behavior (implied by the stack) might not guarantee this exact string for *all* timeout scenarios, or it might be a specific implementation detail of `providers.py` that is fragile. More critically, if the `Router.call` raises a `ProviderError` due to a network failure *before* the deadline, it is correctly labeled `error`. But if the `Router` enforces the deadline by raising a specific exception, relying on string matching is brittle.
*However*, looking at the test `test_no_answer_by_the_cap_is_a_timeout_with_no_decision` (line 419-423), it uses `Timed(GROK, 0.6)` with `cap_s=0.2`. The `Timed` class sleeps for 0.6s. The `Router` is expected to interrupt this. If the `Router` raises a `ProviderError` with the message "abandoned at the deadline", this works.
**The real issue:** The `outcome` is set to `timeout` *only* if the string matches. If the `Router` raises a generic `TimeoutError` or a `ProviderError` with a different message (e.g., "Request timed out"), it will be classified as `error` instead of `timeout`. This violates the requirement to accurately measure latency and missed deadlines. The classification should rely on the exception type or a specific attribute, not a substring match on the error message, unless `providers.py` strictly guarantees this message. Given the "Fail Closed" law, misclassifying a timeout as an error might hide latency issues.
*Refinement:* The prompt states "a call is cut at CAP_S... TIMEOUT when it gave no answer by the cap". The `Router` is responsible for this cut. If the `Router` raises `P.ProviderError` with that specific message, it's acceptable *if* that's the contract. But it's a P1 risk if the contract is not explicit. Let's look closer at `replay85` or `providers` usage. The code imports `providers as P`. Without seeing `providers.py`, we must assume the string match is the intended interface.
**Wait**, there is a more subtle bug.
Line 150: `row["outcome"] = "in_time" if dl is None or secs <= dl else "late"`.
This line is reached *only* if `router.call` succeeds (no exception).
If `router.call` raises `P.ProviderError` (timeout), it returns at line 139.
If `router.call` succeeds, it calculates `secs`.
The logic seems consistent *if* the `Router` raises the specific error for timeouts.

**[P2] `deadline_100_s` can be `None`**
Line 118: `dl = router.effective_deadline(...)`.
Line 150: `if dl is None or secs <= dl`.
If `dl` is `None`, the outcome is `in_time`.
The docstring says: "IN TIME when it answered within the deadline... else the gateway's configured 120 s".
If `effective_deadline` returns `None`, it implies no deadline or a default. The code treats `None` as "in time" regardless of `secs`. This might be incorrect if `None` means "unknown" or "no limit". If there is no limit, any time is "in time". This seems logically sound for "no deadline", but the variable name `deadline_100_s` suggests a specific value. If `None` is returned, the table will show `None` (handled by `_s` as `-`). This is acceptable.

#### 2. Record Set & Decision Reuse

**[P1] `source_records` deduplication logic is flawed**
Lines 62-87:
```python
def source_records(path=SOURCE, wt=WT):
    seen, out, missing = set(), [], []
    with open(path) as f:
        for line in f:
            try:
                x = json.loads(line)
            except ValueError:
                continue
            rel = x.get("record")
            if not rel or rel in seen:
                continue
            seen.add(rel)
            # ... load rec ...
            k = R.kind(rec)
            if k is None or k != x.get("type"):
                missing.append(rel)
                continue
            out.append(...)
    return out, missing
```
The `seen` set tracks `rel` (the record path).
If a record appears multiple times in `RESULTS.jsonl` with *different* types (which shouldn't happen if `R.kind` is deterministic, but might if the file is corrupted or inconsistent), the first occurrence is processed.
However, the check `if k is None or k != x.get("type")` adds to `missing` if the type in the JSONL doesn't match the type derived from the record file.
**The Bug:** If a record is in `seen` (processed successfully), it is skipped. If a record is in `seen` but *failed* the type check (added to `missing`), it is *still* in `seen`.
Wait, `seen.add(rel)` happens *before* the type check.
So, if `rel` is encountered, it is added to `seen`.
If the type check fails, it is added to `missing`.
If `rel` is encountered *again* later in the file, `rel in seen` is True, so it is skipped.
This means if a record has inconsistent types in the JSONL, only the first one is checked. This is likely fine for "once each".
**However**, consider the case where `rel` is valid, but `R.kind(rec)` returns `None`. It is added to `missing`.
Is `missing` unique? No. If the same `rel` appears twice and fails both times, it will be in `missing` twice.
The test `test_the_records_are_ruling_85s_once_each...` (line 451) checks `sorted(missing)`.
In the test, `r/gone.json` is in the JSONL but not on disk. `open` fails -> `missing.append(rel)`.
If `r/gone.json` appeared twice in the JSONL, `missing` would have it twice.
The code does not deduplicate `missing`.
**Severity:** [P2] `missing` list may contain duplicates. The summary counts `len(missing)`. If duplicates exist, the count is wrong.

**[P1] `replay_one` does not verify the record content matches the prompt**
The code uses `rec["prompt"]` and `rec["text"]` from the loaded JSON file.
It assumes the `RESULTS.jsonl` entry `x` corresponds to the file at `rel`.
It does *not* verify that the `prompt` in `x` matches the `prompt` in `rec`.
If the `RESULTS.jsonl` is stale or corrupted, the comparison `R.compare(k, _tupled(g), _tupled(row["heimdall"].get(u)))` uses `g` from `R.decide(k, rec["text"], rec["prompt"])`.
`rec["text"]` is the *Grok* response. `rec["prompt"]` is the prompt.
This seems correct: we are re-asking the *same* prompt to the new model and comparing the new model's decision to the *recorded* Grok decision.
The `anchors` are taken from `x` (the JSONL entry).
This logic holds.

#### 3. Spend Stop and Guard

**[P0] Race Condition in Spend Check**
Lines 115-116:
```python
    if router.spent() >= stop_usd:
        return "stopped"
```
`router.spent()` reads the current spend.
Multiple threads (`per_model` uses `ThreadPoolExecutor`) call `replay_one` concurrently.
`router.spent()` is likely not atomic with the subsequent `router.call`.
Thread A checks `spent() < stop_usd`.
Thread B checks `spent() < stop_usd`.
Both proceed to `router.call`.
If `router.call` increments the spend, the total might exceed `stop_usd`.
The `Router` class (in `providers.py`) likely has internal locking for spend updates, but the *check* here is outside that lock.
The docstring says: "NO CALL STARTS once the ledger holds $0.75".
If two calls start simultaneously when spend is $0.74, and each costs $0.02, the spend becomes $0.78.
This violates the "No call starts" rule if interpreted strictly as "spend must not exceed stop_usd".
However, `LIMIT_USD` is $3.00. `STOP_USD` is $0.75.
The `Router` has `limit_usd=LIMIT_USD`.
Does the `Router` enforce `STOP_USD`? No, `STOP_USD` is a local variable in `replay110.py`.
The `Router` enforces `LIMIT_USD` ($3.00).
The local check is a *soft* stop to save money, but it is racy.
**Impact:** The script might spend slightly more than $0.75.
**Severity:** [P1] The spend stop is not atomic. It can be bypassed by concurrent threads. This is a "real defect" because it violates the specific spend constraint logic defined in the docstring ("NO CALL STARTS once...").

**[P2] `router.reject(rep)` on Out of Contract**
Line 148: `router.reject(rep)`.
If the model returns an out-of-contract response, the code rejects it.
Does `reject` refund the spend? Or mark it as wasted?
If it marks it as wasted, the spend counter increases.
This is correct behavior for "failed call".

#### 4. Production State & Routing

**[P1] `build_router` modifies `r.config`**
Lines 90-100:
```python
def build_router(models, ...):
    r = P.Router(...)
    tmpl = r.config["backends"][TEMPLATE]
    for m in models:
        r.backends[name(m)] = P.HeimdallBackend(...)
        r.chains[f"replay110_{m}"] = [name(m)]
    return r
```
`r.config` is likely a dictionary loaded from a file or environment.
Modifying `r.backends` and `r.chains` on the *instance* `r` is safe *if* `r` is a new instance.
`P.Router(...)` creates a new instance.
However, `r.config` might be a shared reference if `Router` doesn't deep-copy the config.
If `Router` shares the config dict with other instances or the global state, modifying `r.backends` could affect other parts of the system.
Given `Router` is instantiated locally in `build_router`, and `replay110` is a test script, this is likely isolated.
**But**, `P.Router` might load `ENV` or `STATE` files.
The docstring says: "NO routing change... no config file changes".
The code creates a *new* Router instance. It does not write to config files.
It *does* modify the in-memory config of that instance.
This is acceptable for a test driver.

**[P2] `DT.load(DT.STATE, None)`**
Line 95: `deadlines=DT.load(DT.STATE, None)`.
`DT.STATE` is likely a path to the production deadline table.
`DT.load` reads it.
The docstring says: "read, never rewritten".
`DT.load` with `None` as the second arg (likely `save_path` or `record_dir`) implies read-only.
This is safe.

#### 5. Table Arithmetic

**[P1] `summary` function: `usd_reported` calculation**
Lines 242-243:
```python
"usd_reported": round(sum(float(r["usd_reported"]) for r in rs if P._num(r.get("usd_reported"))
                          and not r.get("cached")), 6)
```
It sums `usd_reported` for rows where `usd_reported` is a number and `cached` is False.
`r.get("cached")` is set in `replay_one` line 141: `cached=bool(rep.cached)`.
If `rep.cached` is `None`, `bool(None)` is `False`.
If `rep.cached` is `True`, it is excluded.
This seems correct: we only count spend for non-cached calls.
**However**, `P._num` is used. If `usd_reported` is `None`, `P._num` likely returns `False` or `0`.
If `usd_reported` is missing, `r.get("usd_reported")` is `None`.
`P._num(None)` should handle this.
Assuming `P._num` is robust, this is fine.

**[P2] `p50_s` and `p90_s` calculation**
Lines 232-233:
```python
secs = [r["seconds"] for r in rs if r.get("outcome") in ("in_time", "late", "out_of_contract")
        and isinstance(r.get("seconds"), (int, float))]
```
It includes `out_of_contract` in the latency stats.
The docstring says: "p50/p90 latency".
Should `out_of_contract` calls count towards latency?
They *did* take time to respond (the model returned a bad format).
Yes, they should count.
`timeout` and `error` are excluded.
`timeout` has no `seconds` (or `seconds` is the cap?).
In `replay_one`, if `timeout` (exception), `row.update(seconds=round(time.time() - t0, 2)...)`.
So `timeout` rows *do* have `seconds`.
But `summary` excludes `timeout` from `secs`.
Why?
"p50/p90 over answers only".
A timeout is not an "answer". It's a failure to answer.
So excluding `timeout` is correct.
Excluding `error` is correct.
Including `out_of_contract` is correct (it's an answer, just a bad one).
Including `in_time` and `late` is correct.
This logic holds.

**[P1] `missed` calculation**
Line 236: `"missed": len(by["late"]) + len(by["timeout"])`.
This is correct.

**[P2] `agree_in_time_pct`**
Line 238: `100 * cin.count("agree") / len(cin) if cin else None`.
`cin` is comparisons from `in_time` rows.
This is correct.

#### 6. Tests

**[P1] `test_an_answer_inside_ruling_100s_deadline_is_in_time_and_compared`**
Line 410: `row = RX.replay_one(candidate(d, Timed(GROK, 0.05)), job(d), cap_s=2.0)`.
`candidate` sets `deadline_s=0.3`.
`Timed` sleeps 0.05s.
`secs` will be ~0.05.
`dl` is 0.3.
`0.05 <= 0.3` -> `in_time`.
`compare` is calculated.
This test passes.

**[P1] `test_an_answer_after_the_deadline_is_late...`**
Line 415: `Timed(FAILS, 0.5)`. `deadline_s=0.3`.
`secs` ~0.5.
`0.5 > 0.3` -> `late`.
`compare` is calculated.
This test passes.

**[P1] `test_no_answer_by_the_cap_is_a_timeout...`**
Line 421: `Timed(GROK, 0.6)`. `cap_s=0.2`.
`Router` should raise `ProviderError` with "abandoned at the deadline".
`replay_one` catches it.
`outcome` = `timeout`.
`heimdall` = `None`.
`compare` not in row.
This test relies on the `Router` raising the specific error.
If the `Router` doesn't, the test fails.
This is a valid test of the integration.

**[P2] `test_the_records_are_ruling_85s_once_each...`**
Line 461: `recs, missing = RX.source_records(src, wt=d)`.
The test creates `r/a.json` and `r/b.json`.
`RESULTS.jsonl` has entries for `r/a.json` (step_a), `r/a.json` (step_a - duplicate), `r/b.json` (step_a), `r/gone.json` (step_a).
`source_records`:
1. `r/a.json`: `seen` empty. Add to `seen`. Load `r/a.json`. `R.kind` returns `step_a` (assumed). `x.get("type")` is `step_a`. Match. Add to `out`.
2. `r/a.json`: `seen` has `r/a.json`. Skip.
3. `r/b.json`: `seen` empty. Add to `seen`. Load `r/b.json`. `R.kind` returns `fidelity_verdict` (from test setup `dict(good, role="fidelity_verdict")`). `x.get("type")` is `step_a`. Mismatch. Add to `missing`.
4. `r/gone.json`: `seen` empty. Add to `seen`. Load fails. Add to `missing`.
Result: `out` has 1 record. `missing` has `r/b.json`, `r/gone.json`.
Test asserts `missing` is `["r/b.json", "r/gone.json"]`.
This passes.

**[P1] `test_agreement_in_time_leaves_late_answers_out...`**
Line 472: `x = RX.summary(rows)[("step_a", M)]`.
Rows:
1. `in_time`, `agree`.
2. `in_time`, `stricter`.
3. `late`, `agree`.
4. `timeout`.
5. `error`.
`by["in_time"]` has 2 rows.
`cin` has 2 comparisons: `agree`, `stricter`.
`agree_in_time_pct` = 50%.
`by["late"]` has 1 row.
`by["timeout"]` has 1 row.
`missed` = 1 + 1 = 2.
`secs` for `in_time`/`late`/`out_of_contract`:
Row 1: 10.0.
Row 2: 30.0.
Row 3: 200.0.
Row 4: `timeout` excluded.
Row 5: `error` excluded.
`secs` = [10.0, 30.0, 200.0].
`p50` = 30.0.
`p90` = 166.0 (interpolated).
Test asserts `p50_s` 30.0, `p90_s` 166.0.
This passes.

---

### Summary of Findings

1.  **[P1] Race Condition in Spend Stop:** The check `if router.spent() >= stop_usd` is not atomic with the call. Concurrent threads can bypass the stop limit, leading to overspend.
2.  **[P1] Fragile Timeout Classification:** Relying on the string `"abandoned at the deadline"` in `ProviderError` to classify timeouts is brittle. If the `Router` changes the error message, timeouts will be misclassified as `error`, skewing latency and missed-deadline stats.
3.  **[P2] Duplicate Entries in `missing` List:** `source_records` does not deduplicate the `missing` list. If a record fails multiple times (or appears multiple times in the source JSONL and fails), it will be counted multiple times in `len(missing)`.
4.  **[P2] `usd_reported` Summation:** The summation logic in `summary` is correct but relies on `P._num` handling `None`/missing keys gracefully. If `P._num` raises an exception on `None`, the summary will crash. (Assuming `P._num` is robust, this is low risk).

### Final Count

P1_OR_WORSE: 2