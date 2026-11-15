# glm-5.3-flash (z-ai/glm-5.3-flash) 158 s finish=stop usage in 10784 / out 4814 usd_reported=0.000931 usd~0.105 (upper-bound price)

# Code Audit: pp-selectid — Batch 3 Spend-Guard Fixes

**Scope reviewed:** C1_STEP.diff (providers.py `_reserve` wait, proof_ly.py `meter()` wrapper, two new test files) against the governing laws (M12 fail-closed, LAW 20/M2, L-j) and the stated defect narrative.

---

## Findings

### [P1] F1 — `_reserve` wait loop: `waited` flag set outside the lock, and the "spend alone" early-exit can misreport, but more importantly the loop's exit condition ordering can raise SpendLimit *before* one final successful poll

`providers.py`, new `_reserve`:

```python
while True:
    with self._lock():
        ...
        if spent + held + upper <= self.limit_usd:  # reserve & return
        if spent + upper > self.limit_usd or time.time() >= t_end:
            raise SpendLimit(...)
    waited = True
    time.sleep(...)
```

Two issues:

1. **`waited = True` executes after the `with` block, before the sleep — but if the loop body raises, `waited` was already set on the *previous* iteration.** That part is fine. The real issue: on the *first* iteration, if the call doesn't fit, the code checks `time.time() >= t_end`. With `reserve_wait_s = 0.0` (or a very small value), `t_end = now + 0.0`, so `time.time() >= t_end` is true immediately and the call is refused without ever waiting — correct fail-closed, but the error message then lacks the "(still, after waiting...)" suffix even though `waited` is False, which is consistent. However, when `reserve_wait_s > 0` and the deadline expires, the final check happens *inside* the lock *before* one last reservation attempt — no, wait, the fit-check runs first, so the last-iteration fit is still honored. **Downgrade: the ordering is actually correct.** The remaining defect: **`waited` is set to True even when the loop exits via the raise on the *first* pass** — no, it isn't; the raise happens before `waited = True`. After careful trace: the flag logic is correct. **Residual [P2]:** the error message when `waited` is true reports `spent + reserved + upper > limit` using the *last-read* `held`, which may have changed; cosmetic.

2. **Poll interval vs. deadline: `time.sleep(max(0.01, reserve_poll_s))` can oversleep past `t_end`** — the next iteration's `time.time() >= t_end` catches it, so the wait can exceed `reserve_wait_s` by up to one poll interval (600 s default → up to +1.0 s). [P3] (message says "after waiting 600 s" while actual wait is 600–601 s; harmless).

**Verdict: no P0/P1 in the loop logic itself; the wait is fail-closed (M12 ✓).** But see F2 for the real P1.

### [P1] F2 — Starvation: the waiting call re-reads the ledger but never re-checks *its own* reservation against *newly arrived* competitors; under sustained contention a call can wait the full 600 s and be refused despite the limit having room "in principle" — and, critically, **the wait runs *before* the call's deadline (`_within`) starts, so the caller's time budget is silently consumed**

This is the question the author asked (CHECK 3) and it is a real defect. Trace: `Router.call` → `_reserve` (new: can block up to 600 s) → *then* the deadline/`_within` machinery starts. Callers with their own time budgets:

- **prescreen (step A, ruling 101's wait estimate):** computes a wait estimate from... the *pre-wait* state. A worker that would have been refused at once (old behavior, ~0 s) now blocks up to 600 s; ruling 101's estimate and any prescreen timeout computed *before* `Router.call` no longer bound the wall-clock. If prescreen's ThreadPoolExecutor or the ruling-102 "retried next build" logic has its own deadline, a 600 s `_reserve` wait can blow it, producing holds that *look* like gate failures rather than SpendLimit.
- **the shadow's background asks:** background threads now block up to 600 s inside `_reserve`; if the shadow's teardown joins its workers with a shorter timeout, the join times out and the ask is lost — previously it was refused *fast* and the shadow could react.

**Fix:** either (a) start the caller's deadline clock *before* `_reserve` (pass a deadline into `_reserve` and cap `t_end` by it), or (b) document + bound `reserve_wait_s` per call-site. As written, the 600 s default is a silent 10-minute hang for every caller that assumed SpendLimit returns at once. **[P1] — must fix before merge** (or, at minimum, the author must demonstrate no caller has a budget shorter than 600 s; the diff neither demonstrates nor bounds this).

### [P3] F3 — `test_reserve_wait.py` timing assumptions

- `test_six_workers...`: `time.sleep(0.4)` then asserts `track["now"] == 4` exactly. On a loaded 2×4090 box (or CI), thread startup jitter can leave only 3 workers reserved at the 0.4 s mark → flaky. Prefer: poll until `track["now"] == 4` with a deadline, or assert `track["now"] >= 3` / `<= 4` with a later re-check. Also `assertEqual(results, {})` at 0.4 s — if the box is slow, a worker could... no, `release` isn't set, so no answers; that assert is safe. The `track["now"] == 4` assert is the only flake risk. [P3]
- `test_a_call_still_kept_out...`: `time.sleep(0.15)` between launches, then asserts exactly 1 reservation — if the second thread's `_reserve` hasn't reached its first ledger read by then, the assert still passes (it reads 1 either way); but `assertGreaterEqual(secs, 0.4)` depends on `wait_s=0.4` and the poll granularity 0.02 s — fine. `assertEqual(g.calls, 0)` at that point: the first call is held by `release` (10 s), so safe. OK.
- `test_a_call_kept_out_by_spend_alone...`: `assertLess(secs, 1.0)` — the refused call's path takes one lock acquisition; safe unless the ledger flock is contended by the small call's *reservation save*... the small call already reserved (0.2 s sleep), so no contention. Safe. [P3] only on the 0.4 s assert.

### [P2] F4 — `meter()` wrapper: `**kw` passthrough is correct, but the "best" accounting for an abandoned call diverges from the cap when a *late answer* replaces the booking

The wrapper's docstring says "a late answer that replaces the booking (Router._replace_booking) is not followed here." So: the cap (router `_settle`) counts the *revised* booking when a late answer lands; the meter's "best" keeps the original `unreported` booking. If a late answer's true cost exceeds the abandoned-call booking, the meter's "best" *undercounts* relative to what the cap reads — the meter's stated purpose ("THIS process's own spend... as the cap counts it") is violated in exactly the late-answer case the ruling-107-Q1 machinery exists for. The test `test_the_meter_counts_an_abandoned_call_at_the_booking_the_cap_counts` never exercises a late answer, so this divergence is untested. [P2] — either follow `_replace_booking` in the wrapper (wrap it too) or amend the docstring/test to record the divergence as intended.

### [P2] F5 — CHECK 4 (other wrappers with old signatures): the diff fixes `meter()`'s `_settle` wrapper, but the narrative says the router's `abandon()` path calls `self._settle(key, b, {...}, listed, role, unreported=booked)` — any *other* monkey-patch or subclass of `Router._settle` / `Router._reserve` in the repo (e.g., in tests/package/proof_ly.py's other helpers, or the shadow) that wasn't updated in this diff will hit the same TypeError. The diff only greps-clean the two files it touches; no repo-wide check. [P2] — add a cheap guard: a test asserting `inspect.signature(Router._settle)` accepts `unreported` (a signature-compat canary), so the next keyword added to `_settle` fails a test, not a build.

### [P3] F6 — `test_meter.py` imports

`from test_ruling_107 import LIST, TOKENS, seed` — cross-test-module import; if `test_ruling_107.py` gains a module-level side effect (or is renamed), this breaks. Also `REPO` computed as `dirname(dirname(HERE))` — for `tests/package/test_meter.py`, HERE = `tests/package`, so REPO = repo root: correct. Nit: `QWEN_LIST` comment says "Fake's list price" — verify `Fake`'s pricing actually matches (1,000 in / 100 out at 10/100 per 1M); if `Fake`'s usage dict overrides, the constant could drift. [P3]

### [P2] F7 — CHECK 2 (is the limit ever passed?): the reservation save is atomic under `_lock()`, but the *ledger read* inside `_ledger()` (which "drops reservations of processes that are gone") mutates-while-iterating semantics

`_ledger()` (base, unchanged, :814-839) drops reservations of dead processes. Inside the new loop, `_ledger()` is called under `_lock()` — good. But `_ledger()`'s pruning *writes* the pruned ledger (per the narrative "drops reservations of processes that are gone"); if `_ledger()` saves the pruned dict, then the subsequent `self._save(d)` in the reserve branch saves a *second* time — benign. However, if `_ledger()`'s prune-save and this loop's `_save` interleave with another *process's* flock-protected section... no, both are under the same flock. **No defect.** But: the new loop calls `_ledger()` every 1.0 s (default) for up to 600 s → 600 flock+read+prune+write cycles per waiting call; with 6 workers waiting, that's ~3,600 ledger rewrites/10 min, each an flock+JSON round-trip. On the shared `SPEND.json` this is contention noise but not a defect. [P3] — consider: only re-read when the poll interval elapsed AND skip the prune-write when nothing changed (if `_ledger()` writes unconditionally, that's a small write-amplification; if it only reads, disregard).

### [P3] F8 — Error message arithmetic

The SpendLimit message reports `spent + reserved + upper > the limit` — when raised via the *spend-alone* branch, `held` is included in the message but the deciding condition was `spent + upper > limit`; a reader may be misled (the message shows a sum that may be ≤ limit in the spend-alone case... no: if `spent + upper > limit` then `spent + held + upper > limit` too, since held ≥ 0). Message is always true. [P3] — no defect, noted for completeness.

### [P2] F9 — CHECK 1 (deadlock/starve): the wait holds no lock while sleeping (sleep is outside `with self._lock()`), and a call in flight needs nothing a waiting call holds — *except* the flock

The flock (`_lock()`) is taken through a *new* open file each time (narrative, :806-812) — so no stale-fd deadlock. A waiting call holds no lock during sleep. A call in flight holds only its *reservation* (a ledger entry), not the flock. The one coupling: `_ledger()`'s prune of dead processes — if a process is *slow* (not dead) but its flock... no. **No deadlock.** One subtle starvation: the waiting call's reservation, once it fits, is saved; but between the fit-check and the save, the lock is held continuously — atomic, no TOCTOU. ✓. However: **`_lock()` via flock is *not* thread-parallel-safe on all filesystems** — the narrative asserts "threads of one process exclude each other too" via flock; on some NFS/overlayfs (Ubuntu 24.04, likely overlayfs in containers) flock across... same-process flock on the *same* fd would not exclude, but they open a *new fd* each time, and POSIX flock locks are per-open-file-description, so two fds in one process DO exclude. Correct on ext4/overlayfs. ✓ (Worth a [P3] note: this depends on flock-per-fd semantics; a comment citing SUSv4 §flock would help.)

### [P3] F10 — `RESERVE_WAIT_S`/`RESERVE_POLL_S` as module constants copied into instance attrs

`self.reserve_wait_s, self.reserve_poll_s = RESERVE_WAIT_S, RESERVE_POLL_S` — the test overrides them as instance attrs (`r.reserve_wait_s, r.Router... = wait_s, 0.02`), which is the intended seam. Fine. But the constants' comment spans three lines where the second constant's comment is on the continuation line — cosmetic. [P3]

### [P2] F11 — CHECK 5 (test timing, `test_meter.py`): `wait_for(log, "late_error")` — the late path is asynchronous

`metered_miss` calls `wait_for(log, "late_error")` (from test_providers) — presumably polls the deadline log for the `late_error` kind. If `wait_for`'s default timeout is shorter than the 0.4 s `SlowFail` delay + abandonment booking, the test flakes. The 0.2 s deadline vs 0.4 s delay: the abandonment fires at 0.2 s, the late error at ~0.4 s; `wait_for` must tolerate ≥0.4 s + scheduling. If `wait_for` (base, unchanged) has, say, a 2 s cap, fine; if 0.5 s, marginal. Can't verify from the diff — flag for the author to confirm `wait_for`'s timeout. [P2→P3] depending on `wait_for`'s cap; the author should state it.

### [P2] F12 — `test_reserve_wait.py` `guarded()` writes the ledger *before* the Router reads it — but the Router's `_ledger()` prune may drop the seeded `reserved: {}`... no, empty. However, `guarded()` seeds `"calls": 1 if spent else 0` and `usd_reported: spent` — with `limit_basis="reported"`, `_basis_total` reads `usd_reported` — consistent. But `usd_estimate: spent` too — if any code path reads the estimate basis, the seeded ledger is consistent either way. ✓. One real nit: `guarded()` does not set `r.reserve_wait_s` when `wait_s=10.0` default... it does: `r.reserve_wait_s, r.reserve_poll_s = wait_s, 0.02` — always. ✓. [P3] — no defect.

### [P2] F13 — CHECK 2, the deeper question: **`_save` inside the reserve branch keeps `spent + reserved <= limit` at save time, but `spent` is read from `_basis_total(d)` which, on the "reported" basis, reads `usd_reported` — and a *concurrent* `_settle` in another process updates `usd_reported` under the same flock.** Since both the read and the save happen under one flock acquisition, the invariant holds. ✓ No defect. But: the *abandonment booking* (ruling 107 Q1) writes `usd_reported` (or `usd_unreported_estimate`?) — the narrative says the booking goes to `usd_unreported_estimate` (test asserts `led["usd_unreported_estimate"] == booked`). If the cap's basis is "reported" and the abandonment booking lands in `usd_unreported_estimate` (NOT counted by `_basis_total` on the reported basis), then **an abandoned call's booking does not count against the reported-basis cap until...** — this is base behavior (unchanged, ruling 107 Q1's own design), not introduced by this diff. [P3] — note only.

### [P3] F14 — Docstring drift

`_reserve`'s new docstring says "reserves once it fits; still kept out after reserve_wait_s, it is refused (fail closed). Spend alone over the limit is refused at once." — matches the code. ✓. The `meter()` docstring's "Batch 3's builds 1 and 2 (22:05 and 22:20 ET Nov 14) lost three abandoned calls' bookings and held three moments (four holds)" — the narrative says "3 moments (4 holds) by a TypeError"; docstring says "three moments (four holds)". Consistent. ✓

### [P2] F15 — CHECK 1, one more coupling: **a call in flight whose *process* dies** — its reservation is pruned by `_ledger()` (dead-process prune), so waiting calls recover. But a *thread* that dies without releasing (e.g., `Router.call`'s `except BaseException: self._settle(key); raise` — what if `_settle` itself raises? Then the reservation key is never released → the reservation leaks until the process dies and the prune collects it.** With the new 600 s wait, a leaked reservation now blocks waiting calls for up to 600 s (previously: instant refusal, no wait).** The narrative says `_settle(key)` bare-call releases the reservation — if that `_settle` raises (e.g., the very TypeError class of bug F5 guards against), the reservation leaks. Pre-existing, but the 600 s wait *amplifies* leak impact. [P2] — consider a try/finally around the release, or note the amplification.

### [P3] F16 — `test_reserve_wait.py` `Gate.complete`'s `release.wait(10)` — if the test's `release.set()` happens after 10 s (CI stall), the call raises `P.Unavailable` → the router fails over... to nothing (single back-end) → the call errors, the reservation released via the except path. Then `assertEqual(sorted(...), ["answer"]*6)` fails. 10 s is generous; [P3] only.

### [P3] F17 — Missing test: no test that a *free* back-end (`b.free()`) skips the wait entirely (returns None immediately) — the `if not self.spend_path or b.free(): return None` fast path is unchanged and untested in this diff. [P3]

### [P3] F18 — `test_meter.py`'s `metered_miss` asserts `assertAlmostEqual(led["usd_unreported_estimate"], LIST, places=9)` — LIST = 1000·10/1e6 + 100·100/1e6 = 0.01 + 0.01 = 0.02. And `own["est"]` = LIST + QWEN_LIST = 0.02 + 0.011 = 0.031. The arithmetic checks out against the stated Fake pricing. ✓

---

## Summary

| # | Sev | Area |
|---|-----|------|
| F2 | P1 | `_reserve`'s 600 s wait runs before callers' deadlines; prescreen/ruling-101/shadow budgets silently consumed |
| F4 | P2 | meter "best" doesn't follow `_replace_booking` (late answer) — divergence untested |
| F5 | P2 | no signature-compat canary for future `_settle` keyword additions |
| F7 | P2 | 1 s poll × 600 s × 6 workers = ledger write amplification (if `_ledger()` prune-saves) |
| F11 | P2 | `wait_for(log, "late_error")` timeout unstated — confirm ≥0.4 s + margin |
| F15 | P2 | reservation leak (if `_settle(key)` raises in the except path) now blocks waiters 600 s |
| F1,F3,F6,F8,F9,F10,F12,F13,F14,F16,F17,F18 | P3 | timing margins, message wording, flock-semantics note, coverage nits |

**Laws:** M12 fail-closed ✓ (wait→refuse, never a pass); LAW 20/M2 ✓ (thresholds are constants, no gate reclassification); L-j ✓ (no gate/bytes changes); smallest-diff ✓ (M1: no new renderer/selector); GPU0/publishing untouched ✓.

**Bottom line:** The core fix is sound — the wait loop is fail-closed, the flock discipline is correct (new fd per acquisition → same-process exclusion holds), the reservation invariant (spent+reserved ≤ limit at every save) holds under the single-flock critical section, and the meter's `**kw` passthrough fixes the TypeError at its root. The one thing that must be settled before merge is F2: either cap the wait by the caller's deadline or demonstrate that no caller (prescreen, ruling-101 wait estimate, shadow background asks) has a time budget shorter than 600 s.

P1_OR_WORSE: 1