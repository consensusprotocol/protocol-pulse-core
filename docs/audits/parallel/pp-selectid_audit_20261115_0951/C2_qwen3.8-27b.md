# qwen3.8-27b (qwen/qwen3.8-27b) 36 s finish=stop usage in 15125 / out 2492 usd_reported=0.002480 usd~0.083 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261115_0951
# Reviewer: Claude (Cycle 2)

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

**GLM-5.3-FLASH** caught the single most important defect in Cycle 1: the original `refused` set (`set(last) - set(out)`) was **not** equivalent to "moments the worker will never re-work." The worker's `passed_ids` logic (in `word_pass_worker.py:121-133`) counts a row as "worked" for *every* row except an acquisition failure matching YouTube's sign-in wording **without** `control_ok`. A moment whose only rows are such block failures would be incorrectly classified as "refused" (final) when in fact the worker *will* pick it again. This was a P1: the report's one new fact was wrong for a real, observable case (the Scott Melker moments).

**GROK-4.20** correctly identified that the two surviving mutations (driver ruling-95 path, funnel script) are acceptable given current coverage, and confirmed no governing-law violations.

**QWEN3.8-27B** did a thorough line-by-line verification of the no-window branch arithmetic and confirmed no double-counting, but did not flag the worker-semantics gap.

**My Cycle 1 output** (as provided in the prompt) was not fully visible, but the consensus notes indicate I was aligned with the integrator's claim without independently verifying the worker's `passed_ids` semantics. That was the miss.

## 2. WHERE DO YOU AGREE OR DISAGREE?

| Finding | Source | Verdict |
|---|---|---|
| P1: `refused` must mirror worker's `passed_ids`, not just `last - out` | GLM | **AGREE.** The fix (`worked_by_worker` + `worked` set) is correct. A moment is refused only if *any* of its rows counts as worked by the worker AND no usable window record emerged. |
| P2: `word_pass` and `word_pass_refused` must come from the same `word_pass_index()` call | GLM | **AGREE, RESOLVED.** The docstring at `build_inputs` (line 75-76) now states this explicitly. The driver (`proof_ledger.py:404-411`) is the only caller and takes both from one call. |
| P2: `word_pass_waiting` can go negative with mismatched inputs | GLM | **DISAGREE (as a defect).** In `spotlight.next_attempt` (line 172-180): `n_ref` counts rows where `mid in refused AND mid not in word_pass`; `ready` counts rows where `word_pass.get(mid)` is sentence-ready. These are disjoint by the guard `mid not in word_pass` in `n_ref`. So `ready + n_ref ≤ len(rs)` for *any* inputs, matched or not. `word_pass_waiting = len(rs) - ready - n_ref ≥ 0` always. No fix needed. |
| P2: All-refused video vanishes from per-video report | GLM | **AGREE, RESOLVED.** `report["window_refused_videos"]` (line 119) now names each video with refused rows. Tested: `{vidW: 1, vidX: 2, vidZ: 1}`. |
| P3: Docstring could state "last row wins for both ready and refused" | GROK | **PARTIALLY AGREE.** The docstring (lines 39-44) now explains the `worked` set and the block-failure exception. It does not explicitly say "last row wins for the ready index" because the refused logic is no longer last-row-only—it's any-row-worked. The current wording is accurate. |
| P3: Redundant `mid not in word_pass` guard in `next_attempt` | GROK | **AGREE (nit).** It is defensive and harmless. Given the disjointness argument above, it is also *necessary* for the invariant to hold if a future caller passes a stale pair. Keep it. |
| P2: Two surviving mutations | GROK | **AGREE (acceptable).** The driver mutation (ruling-95 call without `refused=`) is unreachable in current tests because the harness stops at the router. The funnel mutation is a report script not run in CI. Neither affects build correctness. A follow-up test is recommended but not blocking. |

## 3. NEW FINDINGS FROM THIS REVIEW

**[P2] `worked_by_worker` regex is a mirror, not a link — drift risk.**
`WORKER_BLOCK` (line 17) is a hand-mirrored copy of the worker's `BLOCK` regex at `word_pass_worker.py:68`. The comment (lines 18-20) explains why it cannot be imported (the worker loads `transcript_store`, which `rows()`'s store guard refuses in one process). This is the right call for process isolation, but it creates a **silent drift risk**: if the integrator changes the worker's `BLOCK` regex (e.g., YouTube updates its sign-in wording), `worked_by_worker` will disagree, and the refused set will be wrong with no test failure. The docstring cites the file, lines, and commit (`b22a5e56`), which is good. **Recommendation:** add a comment or a CI check (even a grep-based one) that alerts when `word_pass_worker.py:68` changes. This is not a defect in the current code, but it is the most likely future failure mode.

**[P3] `word_pass_index` docstring says "the worker never works a moment again" but the `worked` set is per-row, not per-moment.**
Line 41: "every moment the worker has WORKED (worked_by_worker) and no usable window record came of: it is final, never 'waiting', because the worker never works a moment again." The `worked` set accumulates across *all* rows of a moment (line 54-55: `if worked_by_worker(r): worked.add(r["moment_id"])`). So a moment is "worked" if *any* of its rows counts. The docstring's "never works a moment again" is the worker's invariant (once a row counts, the moment is in `passed_ids`), and the code correctly mirrors it. The wording is slightly imprecise but not wrong. Nit.

**[P3] `build_inputs` log line (line 137-138) says "refused by the word pass (not sentence-ready or failed: never re-worked)" but the actual criterion is "worked by the worker and no usable window record."**
A row can be `sentence_ready` but lack a `record_sha256` (test case "U"), making it not in `out` but still in `worked`. The log's parenthetical is a simplification. It is accurate for the common cases (failed, not-ready) but omits the "ready but no sha256" edge. Nit; the docstring is more precise.

**[P3] `funnel.py` supply line (line 192-193) says "its row is not sentence-ready or failed; never re-worked" — same simplification as above.** Nit.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| `word_pass_index` / `worked_by_worker` | P1 (refused set wrong) | **P2** (drift risk on mirrored regex) | The P1 defect is fixed. Remaining risk is maintenance, not correctness. |
| `build_inputs` refused/waiting counts | P2 (all-refused video invisible) | **P3** (log wording nit) | `window_refused_videos` added and tested. Arithmetic verified correct. |
| `spotlight.next_attempt` | P2 (negative waiting) | **P3** (defensive guard) | Negative waiting is impossible; guard is correct. |
| Driver wiring (`proof_ledger.py`) | P2 (surviving mutation) | **P3** (acceptable) | Only caller; both args from one call; log carries count not ids. |
| Tests | P2 (worker semantics untested) | **P3** (adequate) | New tests cover block-failure, control_ok, last-row-wins, all-refused video, backward compat. 12/14 mutations killed. |
| `funnel.py` | P3 | **P3** | Report script; one supply line added; not in CI. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None.

**P1 HIGH:** None. The Cycle 1 P1 (worker-semantics mismatch) is fixed.

**P2 MEDIUM:**
1. **`ledger_build.py:17` — `WORKER_BLOCK` drift risk.** The mirrored regex will silently disagree if the worker's `BLOCK` changes. Add a CI grep check or a prominent `# TODO: keep in sync with word_pass_worker.py:68 (b22a5e56)` comment. Not blocking, but the most likely future failure.

**P3 NITS:**
1. `ledger_build.py:41` — docstring "never works a moment again" could say "once any row counts as worked, the moment is in passed_ids."
2. `ledger_build.py:137-138` — log parenthetical omits the "ready but no sha256" case.
3. `funnel.py:192-193` — same log simplification.
4. `spotlight.py:172` — `mid not in word_pass` guard is defensive; a one-line comment explaining the disjointness invariant would help future readers.
5. Two surviving mutations (driver ruling-95, funnel) — add a follow-up test when the driver harness is extended past the router.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The `worked_by_worker` mirror is the linchpin: if it drifts from the worker's `passed_ids`, the entire refused/waiting distinction collapses silently. A CI check that fails when `word_pass_worker.py:68` changes without a corresponding update to `WORKER_BLOCK` would prevent the most likely future regression.

## 7. PRODUCTION READY?

**Yes with conditions.**

Conditions:
1. The integrator confirms that `word_pass_worker.py:68` (the `BLOCK` regex) has not changed since commit `b22a5e56`, and agrees to update `WORKER_BLOCK` in `ledger_build.py` if it does.
2. A follow-up test is added (non-blocking) to exercise the driver's ruling-95 call site past the router, killing the surviving mutation.
3. The two surviving mutations are acknowledged in the audit record as acceptable given current coverage.

No gate, verdict, or selection changes. No moment enters or leaves a build. The change is purely diagnostic and correct as written.

P1_OR_WORSE: 0