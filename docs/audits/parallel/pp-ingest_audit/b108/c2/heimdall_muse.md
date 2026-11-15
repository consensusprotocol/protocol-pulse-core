# heimdall_muse (meta-models/muse-spark-open-816b-a42b, 192.6 s, $0.005, finish stop)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT (FINAL)

**Branch:** `pp-ingest` @ `9b8a5136` | **Scope:** `pipeline/ingest/batch.*`, `spend.py`, `providers.py`, `downsignal.py`, `service.py`, `cycles.py`, `tests/ingest/xllm_audit.py` | **Cap:** $0.30 (<60 lines) / $1.00

---

## 1. WHAT DID THEY CATCH THAT I MISSED?

**Heimdall_qwen caught the documentation/contract mismatch I glossed over.** My Cycle 1 called `share_left()`'s `now+1.0` "fragile but not a bug" (C2 LOW). Qwen correctly framed it as a **design-contract violation**: the spec says "counted from batch start to latest whole hour, line 1 changes once an hour" — but enforcement (`share_left` → `RoleCaps.reserve_why`) is real-time, not hourly. I verified the mechanics; qwen verified the *meaning*. The display and the gate use different clocks. That's not just fragile — it's misleading to operators reading STATE.md.

**Qwen also did the lock-order proof I should have done.** I asserted "no deadlock" implicitly by not flagging one. Qwen actually traced `RoleCaps.lock → queue.lock → batch._lock → queue.lock` and proved consistency. My analysis was correct in conclusion but incomplete in rigor.

**What I caught that qwen missed:** The N+1 query storm in `abandoned_usd()` (my C1 HIGH), the `_segments`/`_place` edge cases, the `estimate()`/`cap_check` interaction with `--only`, and the `notify_path` lock-file divergence subtlety. Qwen's `abandoned_usd` analysis focused on rate bias (interesting but not the operational risk); the real risk is the query amplification on the hot path.

**What neither of us caught in Cycle 1 that the consensus surfaced:** C1-1 (glm's 420s dropped connection booked as $0) — but this was fixed *during* Cycle 1 itself by the driver, with tests. Both reviewers verified the fix. This is the highest-value finding of the entire audit and it came from production data, not code reading.

---

## 2. WHERE I AGREE OR DISAGREE

| Finding | Verdict | Why |
|---|---|---|
| **Qwen 1.1: Hourly vs real-time inconsistency** | **Agree, upgrade my C2** | My C2 LOW understated this. The docstring at `batch.py:1-15` describes `notice()` semantics but `share_left()` silently uses different semantics. An operator seeing `BATCH 3 spend: $0.12` on STATE.md thinks $0.12 is the enforcement figure — it's not, enforcement is already at $0.18. This is a **MEDIUM** correctness-of-documentation bug, not LOW. |
| **Qwen 1.1: Lock order / deadlock** | **Agree** | Qwen's trace is correct. `RoleCaps.lock → batch._lock → queue.lock` is consistent; no reverse path exists. No deadlock. My Cycle 1 didn't explicitly prove this — qwen did. |
| **Qwen 1.2: `abandoned_usd` rate bias** | **Partially agree** | The bias qwen describes (failed calls skewing `AVG(prompt_tokens)`) is real but second-order. The `AVG` query filters `prompt_tokens > 0` — so it includes both successful and failed calls with tokens. If failed calls have systematically different prompt sizes, the estimate is biased. But the **bigger issue** is the N+1 amplification I flagged: 3 queries × N distinct (model,role) on every `share_left()` call (every paid reservation). Qwen missed the performance dimension; I missed the statistical bias dimension. Both matter. |
| **Qwen 1.2: `r["p"]` / division edge** | **Agree, but already handled** | If `r["k"] >= 3` but `r["p"]` is 0/NULL, `rate` would divide by zero. In practice `r["p"]` is `SUM(prompt_tokens)` where `prompt_tokens > 0` and `cost_usd > 0`, so `r["p"] > 0` when `r["k"] > 0`. The `if r["p"]` guard at `batch.py:92` handles it. Not a live bug. |
| **Consensus: No lost/duplicated notices** | **Agree (my 1.6)** | Both reviewers independently verified `flock + os.replace + _segments + _place`. I add: the `notify_path` lock-file divergence I flagged is the only remaining subtlety, and it's not triggered in current call sites. |
| **Consensus: No paid call past share** | **Agree (my 1.7)** | `reserve_why()` holds `RoleCaps.lock` across `share()` check + `reserved` increment. Atomic. |
| **Consensus: Hour's figure is final** | **Agree (my 1.8)** | `ts < mark` with `mark` as hour boundary; late records carry insert `ts`. Immutable once published. |
| **Consensus: C1-1 fix (abandoned booking)** | **Agree, verified** | `CUT_S = 30`, `http_status is None`, `seconds >= CUT_S` — correctly distinguishes vendor-answered errors (muse 502s) from dropped connections (glm). Tests `test_a_call_cut_off_in_flight` / `test_a_review_cut_off_in_flight` fail without fix. |
| **Consensus: C1-2 fix (time-bounded avg/rate)** | **Agree, verified** | Adding `ts < until` to both `AVG` and `SUM` queries prevents future calls from retroactively changing a closed hour's figure. Mutations M1/M1b killed. |

---

## 3. NEW FINDINGS FROM COMBINED ANALYSIS

### N1 — `xllm_audit.py:book()` `answered` average is cross-reviewer, not per-model (MEDIUM)

```python
# xllm_audit.py:book() — new in this diff
answered = [((r.get("usage") or {}).get("prompt_tokens") or 0) for r in results.values()]
answered = [t for t in answered if t > 0]
# ...
tokens = sum(answered) / len(answered) if answered else len(prompts.get(rid) or "") / 3.0
```

When booking an abandoned review, `tokens` is the **mean prompt_tokens across all reviewers that answered**. If `heimdall_qwen` answered with 2000 tokens and `heimdall_muse` was abandoned, muse's abandoned cost uses qwen's prompt size. These reviewers have different `max_tokens_floor` and different prompt constructions (cycle 2 prompts include per-reviewer C1 excerpts). The correct fallback per ruling 107 is the abandoned reviewer's *own* prompt length (`len(prompts[rid])/3`), not the cross-reviewer mean.

**Impact:** If one reviewer has a much larger prompt (e.g., verbose C1 output), abandoned cost for a different reviewer is over/under-estimated. The `else` branch (`len(prompts[rid])/3`) is correct but only triggers when *no* reviewer answered — the rare case.

**Fix:** Use `prompts[rid]` length for the abandoned reviewer's own prompt; use `answered` mean only as fallback if prompt unavailable.

### N2 — `xllm_audit.py:record()` `while key in cyc["reviews"]` can mask double-booking (LOW)

```python
# xllm_audit.py:record()
for rid, b in booked.items():
    key, k = rid, 1
    while key in cyc["reviews"]:
        k += 1
        key = f"{rid} (run {k})"
    cyc["reviews"][key] = b
```

If `record()` is called twice for the same cycle (retry after partial failure), the second call creates `rid (run 2)` instead of overwriting. `cyc["usd"]` then sums both. This is **intentional** per the comment ("a leg run again costs again") — but it means a retry of a *successful* cycle double-counts. The `cap_check` reads `total_usd` which now includes the duplicate. This is correct for re-running a *failed* leg (new cost) but incorrect for idempotent retry of an already-recorded cycle.

**Not a ship-blocker** — requires manual retry of an already-succeeded cycle, which shouldn't happen in normal operation.

### N3 — `estimate()` calls `prompt_for(rid)` N times, each rebuilding cycle 2 prompt (LOW, perf)

```python
# xllm_audit.py:estimate()
for rid in run:
    tokens, out = len(prompt_for(rid)) / 3.0, max_out(REVIEWERS[rid])
```

For cycle 2, `prompt_for` calls `tool.build_cycle2_prompt()` which reads C1 files and does string replacement. Called once per reviewer in `estimate()`, then again N times in `fire()` via `prompts = {rid: prompt_for(rid) for rid in run}`. That's 2N prompt constructions. Each is ~6K chars — trivial. But `estimate()` is called *before* `cap_check` — if prompt construction has side effects or is slow, it blocks the cap gate.

**Not a bug**, just wasteful. Cache `prompt_for` results.

### N4 — Combined: `abandoned_usd` N+1 + `share_left` on hot path = real production risk (HIGH, upgraded)

Neither reviewer alone connected these two facts:
- `abandoned_usd` does 3 queries per distinct (model,role) — my finding
- `share_left` is called under `RoleCaps.lock` on **every** paid call reservation — qwen's finding

Together: every paid call reservation acquires `RoleCaps.lock`, then `batch._lock`, then does N×3 SQL queries while holding both locks. Under load with many abandoned calls and many concurrent reservations, this serializes all paid call starts behind SQL scans. This is the single highest operational risk in the diff.

---

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| `batch.py:notice()` (hourly display) | 8/10 | 8/10 | No change. Correct, well-tested. |
| `batch.py:share_left()` (enforcement gate) | 7/10 | 6/10 | Downgraded: docstring misleads about hourly vs real-time; N+1 under lock is worse than I initially scored when combined with qwen's lock analysis. |
| `batch.py:abandoned_usd()` | 5/10 | 5/10 | No change. N+1 + statistical bias both confirmed. |
| `spend.py:_rewrite_top()` / writers | 9/10 | 9/10 | No change. Solid. |
| `providers.py:RoleCaps` | 8/10 | 8/10 | No change. Lock discipline correct. |
| `xllm_audit.py:book()` | 7/10 | 6/10 | Downgraded: N1 cross-reviewer token averaging is wrong. |
| `xllm_audit.py:estimate()/cap_check` | 8/10 | 8/10 | No change. Conservative by design. |
| `xllm_audit.py:record()` | 8/10 | 7/10 | Downgraded: N2 double-count on retry. Minor. |
| **Overall** | **7.2/10** | **6.8/10** | Slight downgrade from combined findings. Still shippable with fixes. |

---

## 5. FINAL PRIORITY LIST

### P0 CRITICAL — Must fix before ship
*None.* The C1-1 and C1-2 fixes already landed. No remaining P0.

### P1 HIGH — Fix before ship or track as known issue with mitigation

| # | File:Line | Issue | Fix |
|---|---|---|---|
| P1-1 | `batch.py:82-88,108-119` | `abandoned_usd()` N+1: 3 queries × N distinct (model,role), called under `RoleCaps.lock` on every paid reservation | Batch into 1-2 queries: `SELECT model, role, AVG(prompt_tokens) ... GROUP BY model, role` + single rate query. Or cache with TTL. |
| P1-2 | `xllm_audit.py:book():answered` | Abandoned review's prompt tokens estimated from cross-reviewer mean, not own prompt | Use `len(prompts[rid])/3` as primary; cross-reviewer mean only as fallback |

### P2 MEDIUM — Fix soon, or document as known limitation

| # | File:Line | Issue | Fix |
|---|---|---|---|
| P2-1 | `batch.py:1-15` docstring + `batch.py:195` | Docstring says "latest whole hour" but `share_left()` enforces real-time (`now+1.0`). Operator misreads STATE.md. | Update docstring: distinguish display (hourly) vs enforcement (real-time). Document `+1.0` as inclusive bound. |
| P2-2 | `xllm_audit.py:record():while key` | Retry of already-recorded cycle double-counts in `total_usd` | Check if `rid` already in `cyc["reviews"]` with same `usd` — if so, overwrite instead of creating `run 2`. Or make `record()` idempotent per cycle. |
| P2-3 | `spend.py:68` | `notify_path=None` fallback uses different lock file than `notify_path`-present callers | Assert `notify_path` is always provided, or always use `doc + ".lock"`. Currently safe (all callers pass it) but fragile. |

---

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**Batch `abandoned_usd`'s N+1 queries into grouped SQL so `share_left()` doesn't serialize every paid call reservation behind N×3 table scans while holding `RoleCaps.lock`.**

---

## 7. PRODUCTION READY?

**Yes, with conditions.**

1. **P1-1 acknowledged:** Either fix the N+1 before ship, or confirm that `calls` table will have <10 distinct (model,role) with abandoned rows in production and that `queue.lock` hold time stays <100ms under load. If the table grows, this becomes a P0.
2. **P1-2 fixed or documented:** One-line fix — swap `answered` mean for `prompts[rid]` length in `book()`.
3. **Existing C1-1/C1-2 fixes remain in tree** (they do — verified in `9b8a5136` working tree).
4. **Cap respected:** Current spend $0.0215 / $1.00 — well within budget. No cap concern.

No new P0s. The core invariants (no lost notices, no paid call past share, hour figures final, cap enforced) all hold — verified independently by both reviewers.
