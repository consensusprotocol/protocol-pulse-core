# qwen3.8-27b (qwen/qwen3.8-27b) 59 s finish=stop usage in 20456 / out 3773 usd~0.118 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-0041
# Reviewer: Claude (Cycle 2)

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

**Grok's `now` parameter finding was correct and I missed it in Cycle 1.** In Cycle 1, I focused on the `pending_verdict` synthetic-score issue and the snap/trim interaction. Grok correctly identified that `next_attempt`'s `now` parameter was declared but unused in the function body. Looking at the fixed diff, line 195 now reads `age = E.age_hours(rs[0].get("published_at"), now)`, which confirms the fix was applied. I should have caught this in Cycle 1.

**Qwen's timezone parsing concern was valid but partially addressed.** Qwen flagged that `strptime(pub, "%Y-%m-%dT%H:%M:%SZ")` would crash on non-`Z` offsets. The test at line 517 uses `"2026-11-13T18:00:00+00:00"` (with `+00:00`, not `Z`), and the assertion at line 532 expects `"2026-11-13T20:00:00Z"` (normalized to `Z`). This means `P.utc_z()` must be normalizing the offset to `Z` format before the `strptime` call. If `P.utc_z` does not normalize, the `strptime` at line 193 will raise `ValueError`. The `try/except` in `proof_ledger.py` (lines 352–355) catches this, but it means the Ruling 95 report silently degrades to `{"error": "..."}` rather than providing the measured fact. This is a **latent fragility**: the function works only if `P.utc_z` always returns `Z`-suffixed strings.

**GLM's snap-prepends-sentence concern was refuted by the integrator, and I agree with the refutation.** When `snap()` extends backward (prepends a sentence), the new first word is no longer the conjunction. The `hook_trim(v)` check at line 142 re-evaluates on the snapped text. If the snapped text no longer opens on a trim word, the trim block is skipped, and the moment is judged by the opener rule on its new first word. This is correct behavior per Ruling 94(a): the trim variant is only what opens *if* the moment still opens on a trim word after snapping.

## 2. WHERE DO YOU AGREE OR DISAGREE?

| Finding | Source | My Position |
|---|---|---|
| `pending_verdict` synthetic (5, None) leaks into sealed pin | Qwen (critical), GLM (high) | **Agree with the fix, disagree with the severity in the fixed code.** The fixed `_can_open` (lines 49–68) no longer fabricates a score. `defer` (line 59) is `True` only when `pending_verdict=True AND v is None AND third_opener(m)`. When `defer` is `True`, `opens()` returns `True` without consulting a score, but this is *only* on the spotlight path (line 218: `P._can_open(m, pending_verdict=True)`). The medley path calls `_can_open(m)` with `pending_verdict=False` (default), so `defer` is always `False` there. The spotlight's ALONE scorer (>= 4) is the final gate. **The synthetic 5 is gone.** |
| `hook_trim` re-check on snapped `v` may skip trim | GLM (high) | **Disagree.** As noted above, if snap prepends a sentence, the first word changes and `hook_trim(v)` correctly returns `False`. The moment is then judged by the opener rule on its new first word. This is the intended behavior. |
| `next_attempt` `now` unused | Grok (medium) | **Agree.** Fixed at line 195. |
| `P.utc_z` module scope | Grok (medium) | **Agree with integrator's refutation.** `spotlight.py` imports `package as P` at module level (standard in this codebase). `P.utc_z` is accessible. |
| Timezone parsing fragility | Qwen (medium) | **Partially agree.** The `strptime` at line 193 assumes `Z` suffix. If `P.utc_z` normalizes, it's fine. If not, it crashes. The `try/except` in `proof_ledger.py` mitigates but degrades the report. |
| `check_edl` rates third-person hooks | Integrator | **Agree.** Lines 271–274 add `kind == "hook" and ... in THIRD` to the `need` list. The test at lines 307–310 confirms: `check_edl` with `rate` passes, without `rate` fails closed. |

## 3. NEW FINDINGS FROM THIS REVIEW

### <medium> — `next_attempt` line 193: `strptime` assumes `Z`-suffixed `published_at`

**File:** `pipeline/spotlight.py`, line 193 (diff line 193)

```python
exp = (datetime.strptime(pub, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc) +
       timedelta(hours=PPN.WINDOW_H)).strftime("%Y-%m-%dT%H:%M:%SZ") if pub else None
```

**Concrete scenario:** If `P.utc_z()` returns `"2026-11-13T20:00:00+00:00"` (ISO 8601 with explicit offset, not `Z`), `strptime` raises `ValueError: time data '2026-11-13T20:00:00+00:00' does not match format '%Y-%m-%dT%H:%M:%SZ'`. The `try/except` in `proof_ledger.py` (lines 352–355) catches this, and `res["next_attempt"]` becomes `{"error": "ValueError: ..."}`. The Ruling 95 report is silently degraded.

**Verification:** The test at line 517 uses `"2026-11-13T18:00:00+00:00"` as input, and the assertion at line 532 expects `"2026-11-13T20:00:00Z"` as output. This means `P.utc_z` *must* normalize `+00:00` to `Z` for the test to pass. If the test passes, `P.utc_z` is doing the normalization, and the `strptime` is safe. **However, this is an implicit contract not documented in the diff.** If a future change to `P.utc_z` breaks the normalization, `next_attempt` will silently fail.

**Fix:** Use `datetime.fromisoformat(pub)` (Python 3.7+ handles `Z` and `+00:00` uniformly) or explicitly normalize before `strptime`.

### <medium> — `next_attempt` line 182: `rs[0]` assumes all rows for a `video_id` share `published_at` and `channel_name`

**File:** `pipeline/spotlight.py`, line 182 (diff line 182)

```python
pub = P.utc_z(rs[0].get("published_at"))
...
"channel": rs[0].get("channel_name"),
```

**Concrete scenario:** If the adapter returns two rows for the same `video_id` with different `published_at` values (e.g., a re-ingest with a corrected timestamp), `rs[0]` is arbitrary (list order from the adapter). The reported `published_at` and `channel` may not reflect the authoritative value. The `age_h` calculation (line 195) uses `rs[0].get("published_at")`, so the age is also based on the arbitrary first row.

**Verification:** The test at lines 523–528 has two rows for `video_id="mid"` with the same `published_at` and `channel_name`, so the test does not cover the disagreement case.

**Fix:** Use the maximum `published_at` (most recent) or document that the adapter guarantees consistency.

### <low> — `spotlight.py` line 158: `SA.opener("hook", v.get("text") or "")` called without `moments=True`

**File:** `pipeline/spotlight.py`, line 155 (diff line 155)

```python
ok, w = SA.opener("hook", v.get("text") or "")
```

This call does not pass `score` or `fault`, so `score=None, fault=None`. For a third-person opener, `opener` returns `False, "hook opens on the pronoun ... and no clip-scorer verdict is available (fail closed)"`. The guard at line 158 (`if not ok and not P.third_opener(v)`) then *skips* the rejection for third-person openers, allowing them into the pool. This is correct: the ALONE scorer will decide later.

However, for a **first/second-person** opener, `opener` returns `True` (no pronoun check needed). For a **conjunction/reply** opener, `opener` returns `False`, and `P.third_opener(v)` is `False`, so the moment is rejected. This is correct.

**No bug here**, but the logic is subtle: the `third_opener` guard at line 158 is the *only* thing that lets a third-person hook through the pool. If `SA.opener`'s behavior changes, this guard may need updating.

### <low> — `package.py` line 64: `elig` computation is opaque

**File:** `pipeline/package.py`, line 64 (diff line 64)

```python
elig = hook.get("ok") or (set(hook.get("reasons") or []) == {"opener"} and opens())
```

This means: the hook is eligible if (a) the ledger says `ok=True`, OR (b) the ledger's *only* reason for failure is `"opener"` AND the opener rule (with verdict) passes. This is correct per Ruling 94(b): a third-person hook fails the ledger's opener test (no verdict at ledger time), but can be re-admitted at the pin stage with a verdict.

**However**, if the ledger has `ok=False` with reasons `["opener", "hook_lead"]`, the `set(...) == {"opener"}` check fails, and the hook is not eligible. This is correct: a hook with *other* faults (e.g., `hook_lead`) should not be rescued by the opener re-check.

**No bug**, but the logic is worth a comment.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| `stand_alone.py` opener rule | 8/10 | 9/10 | The `THIRD`/`FIRST_SECOND` split is clean. `check_edl` correctly rates third-person hooks. The test coverage (lines 301–310) is thorough. Minor: the `moments=True` parameter is not always passed consistently, but the behavior is correct. |
| `package.py` `_can_open` | 5/10 | 9/10 | The synthetic `(5, None)` is gone. `defer` is correctly scoped to spotlight-only. The `elig` computation is correct. The `scorer_pass` change (lines 23–24) correctly asks for trim variants and third-person openers. |
| `spotlight.py` pool/build | 6/10 | 8/10 | The `TRIM_MARGIN_S` snap is correct. The trim variant check (lines 142–154) is thorough. The `pending_verdict=True` call (line 218) is correctly scoped. The unclean trim stop (lines 215–217) is correct. Minor: the `SA.opener` call at line 155 relies on the `third_opener` guard at line 158, which is subtle but correct. |
| `spotlight.py` `next_attempt` | N/A | 7/10 | The function is well-structured. The `now` parameter is now used (line 195). The `try/except` in `proof_ledger.py` provides a safety net. **Deductions:** (1) `strptime` assumes `Z` suffix (line 193); (2) `rs[0]` assumes row consistency (line 182); (3) the implicit contract with `P.utc_z` is not documented. |
| Tests | 7/10 | 9/10 | The new tests (lines 388–444, 476–538) cover the key scenarios: first/second-person pass, third-person needs scorer, trim variant joins pool, unclean trim stop, `next_attempt` state. **Gap:** no test for `next_attempt` with inconsistent `published_at` across rows for the same `video_id`. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None. The synthetic `(5, None)` is gone. `pending_verdict` cannot leak into the medley (it's only passed `True` at spotlight.py:218). A third-person hook cannot be sealed without an affirming verdict (the ALONE scorer >= 4 gate, and `check_edl` with `rate=None` fails closed).

**P1 HIGH:** None. The trim variant is correctly checked for clean cut (spotlight.py:215–217) and scorer affirmation (via `check_edl`). The `TRIM_MARGIN_S` ensures the trimmed spotlight stays at or over `SNAP_TO_S` (13.7 s).

**P2 MEDIUM:**
1. **`spotlight.py:193`** — `strptime` assumes `Z`-suffixed `published_at`. If `P.utc_z` does not normalize, `next_attempt` silently degrades. **Fix:** Use `datetime.fromisoformat(pub)` or document the `P.utc_z` contract.
2. **`spotlight.py:182`** — `rs[0]` assumes all rows for a `video_id` share `published_at`/`channel_name`. **Fix:** Use the max `published_at` or document the adapter contract.
3. **`spotlight.py:155`** — The `SA.opener` call without `score`/`fault` relies on the `third_opener` guard at line 158. This is correct but subtle. **Fix:** Add a comment explaining the guard.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The removal of the synthetic `(5, None)` score and the introduction of the `defer` mechanism (package.py:59–62) is the single highest-leverage change: it eliminates the only path where an unmeasured verdict could be treated as a pass, while preserving the spotlight's ability to defer third-person openers to the ALONE scorer. This directly satisfies Law L-m ("nothing measured is never a pass") and the audit requirement that `pending_verdict` cannot leak into a sealed pin.

## 7. PRODUCTION READY?

**Yes with conditions.**

**Conditions:**
1. **Verify `P.utc_z` normalizes to `Z` suffix.** If it does not, change `spotlight.py:193` to use `datetime.fromisoformat(pub)` or add explicit normalization. The test at line 517–532 must pass with `+00:00` input.
2. **Document or enforce row consistency for `next_attempt`.** Either (a) add a test with inconsistent `published_at` values for the same `video_id` and assert the behavior, or (b) change `spotlight.py:182` to use the max `published_at` and document the choice.
3. **Add a comment at `spotlight.py:155–159`** explaining that the `third_opener` guard is the mechanism that lets third-person hooks through the pool to the ALONE scorer.

If these three conditions are met, the code is production-ready. The core logic (Ruling 94a/94b, Ruling 95) is correct, the fail-closed behavior is preserved, and the test coverage is sufficient for the critical paths.