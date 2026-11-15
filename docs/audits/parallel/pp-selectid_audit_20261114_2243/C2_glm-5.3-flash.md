# glm-5.3-flash (z-ai/glm-5.3-flash) 121 s finish=stop usage in 13329 / out 3297 usd_reported=0.000822 usd~0.089 (upper-bound price)

# CYCLE 2 AUDIT — pp-selectid, C2_STEP.diff (final review)

**Scope:** the fixed diff (providers.py `_reserve` + `reserve_wait_s`, proof_ly.py `meter(**kw)`, proof_ledger.py `build_router` opt-in, two new test files) against the C1 findings and the author's responses.

---

## 1. WHAT THE OTHERS CAUGHT THAT I MISSED

**GLM-5.3-FLASH:**
- **F2's second half — the wait consumes the caller's time budget.** I traced the loop's lock/sleep/raise ordering in detail but under-weighted the *systemic* consequence: `_within` starts after `_reserve` returns, so a 600 s wait silently eats any caller deadline. GLM's framing ("cap the wait by the call's deadline, or show no caller has a budget shorter than 600 s") was the sharper formulation; I had the mechanism but not the demand.
- **F15 — a leaked reservation now blocks a waiter for 600 s, not 0.** I missed this entirely. The `except BaseException: self._settle(key); raise` path in `Router.call` (base :1356-1358) covers most leaks, but a bare `_settle(key)` (no settle args → no booking, reservation released... actually the *reverse*: a raise *before* `_settle` runs, or a process kill between reserve and settle) leaves the reservation in the ledger. Pre-batch-3 that cost a waiter one instant; now it costs it up to 600 s. Mitigated by `_ledger()`'s dead-process sweep, but only when *another* process's `_ledger()` runs — a same-process leak persists for the full wait. Honest miss.
- **F3 — test timing.** I noted the 0.4 s sleeps as a P3 and moved on; GLM's "poll with a deadline" prescription was the right fix and the author took it.

**QWEN3.8-27B:**
- **Thread-pool exhaustion mechanics.** Qwen's point that a caller timing out *around* `Router.call` (a `future.result(timeout=...)`) leaves the thread *inside* `_reserve` still sleeping is a distinct failure mode from "the deadline is consumed": the worker thread is occupied, the pool drains. I said "the caller's budget is consumed"; qwen said "the thread stays blocked after the caller gives up." Both true; qwen's version explains the *resource* consequence. (Largely answered by the opt-in, but only for callers outside the ledger build.)
- **Item 4's careful trace of the "best" arithmetic** — I never independently verified the `rep → booked → usd` fallback chain against the cap's `_basis_total` semantics; qwen did, and reached the same conclusion the author's test now locks in.

**What I caught that they didn't:** the poll-oversleep point (sleep can exceed `t_end` by one interval) — still valid, still P3, still unaddressed (correctly; it's harmless).

## 2. AGREE / DISAGREE WITH THEIR FINDINGS

| Finding | Verdict | Why |
|---|---|---|
| GLM F2: wait before deadline starts | **Agree, was P1; now fixed** | The opt-in (`reserve_wait_s=0.0` default, only `build_router` passes 600) is the right resolution — better than capping by deadline, because it keeps the old contract for every existing caller *and* makes the wait auditable at the call site. The author's justification (ThreadPoolExecutor.map with no timeout at package.py:588-589, shadow_wait 900 s) covers the ledger build's callers. |
| GLM F15: leaked reservation blocks 600 s | **Agree, P2, NOT-CHANGED is acceptable** | Bounded, opt-in, and swept by other processes' `_ledger()`. But note: the sweep runs on *read*; a single-process waiter whose own process leaked the reservation waits the full 600 s. Residual, documented, fine. |
| GLM F4: meter doesn't follow `_replace_booking` | **Agree with NOT-CHANGED** | The meter feeds the per-package budget; the cap's ledger follows replacements. Docstring now says so (proof_ly.py:120-121). Correct division of labor. |
| GLM F5: other wrappers, old signatures | **Agree, resolved** | `**a, **k` / `**kw` everywhere; the grep evidence is adequate. |
| Qwen: thread exhaustion under contention | **Partially agree** | True mechanism, but with the opt-in the only exposed callers are the build's, which have no budgets. Downgrade to P3-observation. |
| Qwen: flock atomicity of reserve | **Agree** | Read-check-write-save all inside one flock; no TOCTOU. Limit cannot be passed by a reservation. |
| GLM F1's self-downgrade of the loop ordering | **Agree** | Their trace is right: fit-check runs before the deadline check each pass, so the last-iteration fit is honored; `waited` is only set after a completed pass. The residual (error message reports last-read `held`) is cosmetic. |

## 3. NEW FINDINGS (this cycle)

**[P2] N1 — `test_ledger_router.py:241-242`: `time.sleep(0.3)` then `assertEqual((track["now"], results), (1, {}))` is still a fixed sleep, not a poll.** The author converted the *other* tests' sleeps to `until(...)` but left this one. If the second thread's `_reserve` hasn't yet reached its first poll (it must: it can't fit, so it sleeps 0.02 s and re-reads), `results` may already... no — the risk is the opposite: if the *second* thread is slow to start, `track["now"]` is 1 and `results` is `{}` trivially, which passes; the real risk is the second thread *not yet having attempted* the call, making the assertion vacuous. It still verifies the essential property (not refused) via the later `results[i][0] == "answer"` check, so this is a weakening, not a break. Should be `until(lambda: results.get(1, ("",))[0:1] == ())`-style or a `waited`-flag probe. Fix: assert the second call's *duration* ≥ 0.3, or poll until `results` has key 1 after release.

**[P3] N2 — `test_reserve_wait.py:354`: `time.sleep(0.2)` after `until(track["now"] == 4)`** — same pattern, same mild weakness: it's there to let the two waiting threads reach their first poll before the reservation-count assert (`len(held) == 4`). If a waiter is slow, `len(held)` could read 3... no: the waiters only *reserve* after release; before release they hold nothing, so `len(held) == 4` counts the four in-flight reservations, which is stable once `track["now"] == 4`. Actually correct as written; the 0.2 s sleep is only guarding the *refusal* counter, which doesn't exist here. Downgrade to P3-cosmetic: the sleep is redundant but harmless.

**[P3] N3 — `providers.py:75`: the "after waiting" message reports `self.reserve_wait_s` (the *configured* wait), not the actual waited duration.** With the oversleep (up to +1 poll interval) the message can understate. Cosmetic; GLM's F1-residual and my C1 oversleep note compound here. No change needed.

**[P3] N4 — `test_reserve_wait.py:312`: `seed()` writes `"calls": 1 if spent else 0`** — a spent-seeded ledger with 0 calls is inconsistent bookkeeping, but nothing in these tests reads `calls`. Nit.

**[P2] N5 — the opt-in's blast radius is one constant, and nothing pins it.** `PL.RESERVE_WAIT_S = 600.0` (proof_ly.py:104) is read by `build_router` at construction. If a future caller of `build_router` *does* acquire a time budget (e.g., the build gains a wall-clock cap), nothing in the code or the constant's comment forces a re-derivation. The comment at :104-107 documents *why* 600 (step-A workers, $0.85 each) but not *the invariant* ("only a caller with no time budget of its own may opt in" — that sentence lives in the `_reserve` docstring, providers.py:43-44, far from the constant). Suggest one line at proof_ly.py:104: "raise this only if no build caller gains a deadline." Cheap insurance.

**[P3] N6 — `test_ledger_router.py:172` imports `wait_for` from `test_providers` but never uses it** (the file's waits use `until` from `test_reserve_wait`). Dead import; also the C1 "cross-test import" P3 (importing helpers across test modules) is now *doubled* — `test_ledger_router.py` imports from both `test_providers` and `test_reserve_wait` and `test_ruling_107`. Works, but the coupling grows. Nit.

**Checked and clean (no finding):**
- **Deadlock:** the waiter holds nothing while sleeping (lock released, :63-78); the flock is taken fresh per acquisition; a call in flight needs only the lock, briefly. No cycle. ✓
- **Limit integrity:** every save happens inside the lock with the fit-check on the just-read ledger (:63-71); `round(upper, 6)` can only *shrink* the reservation. The spend-alone early-raise (:72) uses the same just-read values. No path saves an over-limit reservation. ✓
- **`waited` flag:** set only after a full pass that didn't return or raise (:77), so the "after waiting" suffix is truthful. ✓
- **Meter `**kw` passthrough:** `settle(key, backend, usage, usd, role, **kw)` — `unreported` reaches the real `_settle`; the TypeError defect is genuinely closed, and the `booked`-in-`best` arithmetic matches the cap's basis (qwen's trace + the author's test at :208-215). ✓
- **Default-router contract:** `reserve_wait_s=0.0` → `t_end = now`, so a non-fitting call raises on the first pass with `waited=False` — byte-identical behavior to the old code except the message no longer... wait, the old message had no suffix either. One behavioral note: the *old* code raised when `spent + held + upper > limit`; the new code, with wait 0, raises when `spent + upper > limit` **or** the deadline passed — for a call kept out only by reservations, the old code's message reported the same numbers. Semantics identical, message identical (no suffix). ✓

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| `_reserve` wait loop correctness | 8.5/10 | 9/10 | Opt-in resolved the P1; loop logic verified clean; residual P3s (oversleep, message) are cosmetic. |
| Caller-contract safety (deadlines, pools) | 7/10 | 9/10 | The opt-in + the author's caller inventory (no budgets in the build) answers GLM's demand; N5's unpinned constant keeps it from 10. |
| Limit integrity / concurrency | 9/10 | 9.5/10 | Flock-atomic reserve verified; F15's leak-wait residual noted, bounded, accepted. |
| Meter / ruling-107-Q1 accounting | 8/10 | 9/10 | `**kw` + `booked`-in-`best` closes the TypeError at the root; test locks the arithmetic to the cap's basis. |
| Tests | 7.5/10 | 8.5/10 | Polls replaced sleeps (GLM F3); one fixed sleep survives (N1) and the helper coupling grows (N6). |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** none.

**P1 HIGH:** none. (Both C1 P1s — wait-before-deadline, and qwen's thread-exhaustion variant — are resolved by the opt-in; the author's caller inventory is credible.)

**P2 MEDIUM:**
- **N1** — tests/package/test_ledger_router.py:241-242: replace the 0.3 s fixed sleep + vacuous-able assert with a poll (or assert the second call's elapsed ≥ 0.3) so the "one WAITING, not refused" property is actually observed, not assumed.
- **N5** — tests/package/proof_ly.py:104-107: add the invariant to the constant's comment — "only a caller with no time budget of its own may raise this" — so the 600 s opt-in survives future callers that gain deadlines.

**P3 (no change required):** N2 (redundant 0.2 s sleep, test_reserve_wait.py:354), N3 (message reports configured, not actual, wait — providers.py:75, compounds the ≤1-poll oversleep), N4 (seed's `calls` inconsistency, test_reserve_wait.py:312), N6 (dead `wait_for` import + growing cross-test coupling, test_ledger_router.py:172-174), GLM-F1-residual (error message's `held` is last-read), GLM-F15 (a same-process leaked reservation blocks a waiter the full 600 s — bounded, swept cross-process).

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Make the "one call waits, one answers" observation in test_ledger_router.py:241-242 a poll rather than a 0.3 s sleep — it is the only test guarding the opt-in's *entire reason for existing*, and right now its central assertion can pass vacuously.

## 7. PRODUCTION READY?

**Yes, with conditions** — both conditions are the P2s above, neither blocks the batch:
1. Convert the test_ledger_router.py:241-242 fixed sleep to a poll (or equivalently strengthen the assertion) before the next build relies on this test as the opt-in's guard.
2. Add the "no time budget of its own" invariant to the `RESERVE_WAIT_S` comment at proof_ly.py:104.

Everything else — the loop's fail-closed semantics, the flock-atomic reserve, the default-router's unchanged refusal contract, the meter's `**kw` passthrough and `booked`-in-`best` accounting — I've verified clean in this pass.

P1_OR_WORSE: 0