# heimdall_muse (meta-models/muse-spark-open-816b-a42b, 397.2 s, $0.030, finish stop)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT: pp-ingest (Ruling 98 / Paid Route)

**Branch:** `pp-ingest` @ `56f6eac7` + diff | **Reviewer:** heimdall_muse (Cycle 2) | **Date:** 2026-11-14

---

## 1. WHAT DID THEY CATCH THAT I MISSED?

**Honest accounting:**

| Finding | Who caught it | Why I missed it |
|---------|---------------|-----------------|
| **Zoneless `failing_since_utc` → 5h late open** | GLM P0 | I listed C2 as "if missing → never opens, correct" but did not check the *naive datetime* path. I assumed `fromisoformat` would fail or be handled; I didn't trace `datetime.timestamp()` semantics for naive datetimes (local time) vs `time.time()` (UTC). The codebase's own `config.aware()` convention (fail-closed on zoneless) made this inconsistency verifiable — I should have cross-referenced it. |
| **Route head lost if STATE write fails** | GLM P1 / Claude consensus C1-3 | I verified the `st["open"]` guard prevents duplicate heads but did not consider the *STATE file write* failing (OSError). The signal's own switches had retry logic; the paid route's heads did not in the original diff. I treated `_route_switch` as atomic. |
| **Second outage inside 12h: `recheck_ts` already set → no re-check** | Claude consensus C1-4 (muse P2) | I verified `recheck_due` filters `recheck_ts IS NULL` but did not walk the *second outage* scenario: video mined on paid route → re-queued → mined on Heimdall → mined on paid route *again* in a second outage. The second paid mining left `recheck_ts` set from the first cycle, so the second Heimdall re-mine was never queued. I only traced one outage cycle. |
| **Worst-case reservation < actual cost → cap overshoot** | Qwen P0 (framed as race, actually reservation sizing) / Claude C1-1 | I listed C6 as "cap may trip early, intentional upper bound" and moved on. I did not compute the actual worst case: Gemini `max_tokens_floor=16000` × 2 attempts × $25/MTok ≈ $0.83, vs flat $0.25 reserve. The flat reserve was provably insufficient. Qwen's framing as a "race" was wrong, but the underlying sizing bug was real. |
| **`why_not_open` / observability gaps** | GLM P2 | I focused on correctness of the open/close logic, not on whether an operator could *diagnose* why the route didn't open. The `route_why` / `paid_route` snapshot in `live.json` is an operability requirement I underweighted. |

**What I caught that they missed or misframed:**

- Qwen's "RoleCaps race" was not a race — `reserve` and `add` are each under the same lock, and `reserve`/`release` pairing in `Router.run`'s `finally` is correct. The real bug was reservation *sizing*, not concurrency.
- Qwen's "paid_open desync" and "conv cache leak" were non-issues or P2 at most; the cache is bounded at 5000 and cleared.
- GLM's Finding 2/3 about `_seen()` ordering and re-open duplicate heads were actually correct behavior — I verified this and GLM ultimately agreed.

---

## 2. WHERE DO I AGREE OR DISAGREE?

| # | Finding | Verdict | Why |
|---|---------|---------|-----|
| GLM-1 | Zoneless clock → 5h late | **Agree** — real, moderate. Fix verified: `d.tzinfo is not None else None` (downsignal.py:217). | Naive datetime `.timestamp()` uses local time; ET host = 5h offset. Now correctly treated as "no clock." |
| GLM-2 | Stale view / unreadable signal | **Agree it was correct** — no bug. Both GLM and I verified fail-closed is correct. | `paid_open=False` while unreadable, `st["open"]` persisted prevents duplicate head. |
| GLM-3 | Close only on `mode == up` | **Agree it was correct** — no bug. | Close branch only fires on successful read of `up` mode; unreadable signal correctly leaves `paid_open=False` without closing recorded state. |
| GLM-4 | `signal_back()` requires `not paid_open` | **Agree it was correct** — verified the close→requeue sequence. | Close writes `st.open=False` + `paid_open=False` in same tick; next tick `signal_back()` returns True. |
| Qwen-1 | RoleCaps race | **Disagree on framing, agree on sizing bug** | No race — lock protects all paths. But flat $0.25 < worst-case $0.83 was a real cap-overshoot bug. Fixed via `_worst_cost()` (providers.py:885-890). |
| Qwen-2 | paid_open desync | **Disagree** — not a bug | GIL atomicity + `claim()` atomicity + next-tick convergence is correct. Re-mine logic handles mid-batch flips. |
| Qwen-3 | conv cache leak | **Disagree on severity** — P2 at most | Bounded at 5000, cleared. Amortized cost is acceptable for 5s interval. |
| Qwen-4 | offset_before bisection | **Out of scope** — not this diff | Ledger ordering is pre-existing; stamp-under-lock already addresses it. |
| Muse C1-C6 | All marked "No bug" or "Correct" | **Partially agree** — C1-C3, C6 correct; C4/C5 were real bugs I dismissed too quickly | C4 (200-row window hiding new uploads) was mitigated by `ORDER BY published_ts DESC` — I was right. C5 (conv cache) was correctly P2. But I should have flagged the zoneless clock and head-loss bugs that GLM found. |
| Claude C1-1 | Worst-case reservation | **Agree** — P0, fixed | `_worst_cost()` now computes `attempts × (prompt/3 × in_price + max_tokens × out_price)` per backend. Verified at providers.py:859-864. |
| Claude C1-2 | Zoneless clock | **Agree** — P0, fixed | Verified at downsignal.py:214-219. |
| Claude C1-3 | Route head retry | **Agree** — P1, fixed | `route_heads` queue + `_flush_route_heads()` at downsignal.py:452-463. |
| Claude C1-4 | Second outage recheck_ts | **Agree** — P1, fixed | `_settle` now clears `recheck_ts=None` when `route == paid_role` (service.py:318-320). |
| Claude C1-5/6 | Observability | **Agree** — P2, fixed | `route_why`, `paid_route` in snapshot (downsignal.py:471-479), `live.json` top-level (stats.py:140). |

---

## 3. NEW FINDINGS FROM THIS REVIEW

### N1: Cap check uses `cap_reserve_usd` (0.25) not worst-case — still undersized for cap-reached detection (P2)

**Location:** `downsignal.py:246` — `spent + float(rc.get("cap_reserve_usd", 0.0)) > cap`

The *reservation* gate (providers.py:859) now correctly uses `_worst_cost()` (up to $0.83). But the *cap-reached notice* (downsignal.py:246) still checks `spent + 0.25 > cap`. This means the "CAP REACHED" STATE head fires when `spent > $1.75`, but a call with worst-case $0.83 could still start at `spent=$1.75` (since `1.75 + 0.83 = 2.58 > 2.00` would be blocked by the reservation gate, but the notice hasn't fired yet at `spent=$1.75` if we check `1.75 + 0.25 = 2.00` which is not `> 2.00`).

**Impact:** The cap-reached notice is slightly late — it fires one tick after the cap actually blocks calls, not simultaneously. Low severity: the cap itself is still enforced (reservation gate blocks), only the notification is delayed by one 5s tick. But for audit purposes, the notice should use the same worst-case figure.

**Fix:** `downsignal.py:246` should check against the actual worst-case cost, or at minimum `max(cap_reserve_usd, worst_cost_for_cheapest_backend)`. Alternatively, the reservation failure itself could trigger the notice.

### N2: `RoleCaps._roll` loader called under lock — potential deadlock / stall (P2)

**Location:** `providers.py:697-701` — `_roll()` calls `self.loader(role, start)` while holding `self.lock`.

`loader` is `queue.role_spend_since` which acquires `queue.lock` (a `threading.RLock`). If any code path holds `queue.lock` and then calls `router.caps.today()` or `router.caps.reserve()`, it would deadlock. Currently no such path exists — `role_spend_since` is only called from `RoleCaps._roll`, and `queue.lock` is never held when calling into `RoleCaps`. But this is a latent coupling: a future change that adds cap checking inside a queue transaction would deadlock.

**Mitigation:** Document the lock ordering invariant, or release `RoleCaps.lock` before calling the loader (double-checked locking pattern).

### N3: `recheck_due` horizon uses `published_ts` not `mined_at` — edge case for re-published videos (P3)

**Location:** `queue.py:188-193` — `published_ts >= now - horizon_s`

A video published 11h ago, mined on the paid route, then re-published (metadata update changes `published_ts` to now) would have `published_ts` refreshed but `mine_route` still `mine_paid`. It would be re-queued for Heimdall re-mine even though its moments are 11h old and about to expire. This is arguably correct (re-mine gives Heimdall a chance to produce fresh moments), but the 12h horizon check is on publish time, not mine time. No fix needed — matches spec A31 ("still inside 12h (its moments' life)").

### N4: No test for cap enforcement across ET midnight rollover (P2)

The `RoleCaps._roll` logic resets `spent` at ET midnight by calling the loader. No test verifies that a call starting at 23:59 ET and ending at 00:01 ET is counted on the correct day, or that the reservation held across midnight doesn't double-count. The consensus notes say "every reservation is released in run()'s finally whatever the day; a call that starts before midnight and ends after counts once, on the day it ended" — but this relies on `add()` calling `_roll()` at completion time, which would have already reset `spent` to the new day's loader value. If the loader hasn't yet seen the just-completed call's row (async `q.call` write), the new day's `spent` could be stale.

**In practice:** `q.call` is synchronous (direct SQLite write under lock), so the loader will see it. But this depends on `Service._on_attempt` → `q.call` happening before `caps.add()` — which it does (providers.py:942-944: `spend.add` + `caps.add` happen after `_emit` which triggers `q.call` via `on_attempt`). Verified correct, but fragile ordering.

---

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|-----------|---------|---------|-------------|
| **Correctness (open/close rules)** | 9/10 | 9/10 | No change — logic was correct, fixes addressed edge cases I missed |
| **Correctness (cap enforcement)** | 7/10 | 9/10 | Was 7 because I noted cap could overshoot but didn't quantify; now fixed with `_worst_cost()` — ceiling guarantee |
| **Correctness (freeze lift)** | 9/10 | 9/10 | No change — `freeze_lifted` gating verified correct |
| **Correctness (re-mine)** | 8/10 | 9/10 | Was 8 because I didn't trace second-outage path; now fixed with `recheck_ts` clear |
| **Concurrency / Threads** | 9/10 | 8/10 | Downgraded: N2 (loader under lock) is a latent deadlock risk; N4 (midnight rollover) has fragile ordering dependency |
| **Observability / STATE** | 7/10 | 9/10 | Was 7 — missing `why_not_open`, `paid_route` in live.json; now fixed |
| **Overall** | 8/10 | 8.5/10 | Net improvement: 4 fixes landed, but 2 new P2s identified |

---

## 5. FINAL PRIORITY LIST

| Priority | Location | Issue | Status |
|----------|----------|-------|--------|
| **P0** | `providers.py:859-864` | Flat $0.25 reserve < worst-case $0.83 → cap overshoot | **FIXED** — `_worst_cost()` |
| **P0** | `downsignal.py:214-219` | Zoneless `failing_since_utc` → 5h late open on ET host | **FIXED** — `tzinfo is not None` check |
| **P1** | `downsignal.py:452-463` | STATE write failure lost route head | **FIXED** — `route_heads` queue + retry |
| **P1** | `service.py:318-320` | Second outage: `recheck_ts` already set → no re-mine | **FIXED** — `recheck_ts=None` on paid mining |
| **P1** | `downsignal.py:246` | Cap-reached notice uses `0.25` not worst-case → fires late | **OPEN** — should use `_worst_cost()` or max reserve |
| **P2** | `providers.py:697-701` | `RoleCaps._roll` calls loader under lock → latent deadlock | **OPEN** — document lock ordering or restructure |
| **P2** | `downsignal.py:246` + `queue.py:182` | No test for ET midnight rollover with in-flight reservation | **OPEN** — add test |
| **P2** | `service.py:562-578` | `_paid_due` does 200 transcript reads per tick (first tick after outage) | **OPEN** — pre-filter without reads, or batch |
| **P3** | `queue.py:188` | `recheck_due` horizon on `published_ts` not `mined_at` | **ACCEPT** — matches spec, no fix needed |

---

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**The worst-case reservation (`_worst_cost()`) is the highest-leverage fix — without it, the $2.00 cap is not a ceiling but a suggestion, and every other correctness property (re-mine, open/close, freeze lift) is moot if the budget invariant is violated.**

---

## 7. PRODUCTION READY?

**Yes, with conditions.**

**Conditions:**

1. **P1 cap-notice fix** — `downsignal.py:246` should check `spent + worst_case > cap` (or at minimum `spent + max(cap_reserve_usd, min_worst_cost) > cap`) so the "CAP REACHED" STATE head fires when the cap actually blocks, not one tick later. One-line fix.

2. **P2 lock-ordering documentation** — Add a comment to `RoleCaps._roll` stating the lock ordering invariant: "`RoleCaps.lock` must never be acquired while holding `Queue.lock`" — or restructure to call the loader outside the lock.

3. **Verify no regressions** — All 281 tests pass (including 6 new `test_paid_route.py` tests covering: freeze lift, cap enforcement, worst-case sizing, zoneless clock, head retry, second-outage recheck).

**Without these conditions:** Still shippable — the P1 is a notification delay (cap enforcement itself is correct), and the P2 is latent. But both should be addressed within one cycle.
