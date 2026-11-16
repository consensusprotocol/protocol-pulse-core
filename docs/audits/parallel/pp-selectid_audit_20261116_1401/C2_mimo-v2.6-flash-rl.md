# mimo-v2.6-flash-rl (xiaomi/mimo-v2.6-flash-rl) 120 s finish=stop usage in 8706 / out 6961 usd_reported=0.000982 usd~0.131 (upper-bound price)

# CYCLE 2 — pp-selectid Audit (RULING 123 (1): Grok reserve at 25% with tripwire)

---

## 1. WHAT DID THEY CATCH THAT I MISSED?

**Mimo's unreported-call gap [P3]:** I did not flag that an abandoned call with no numeric `usd_reported` — which may in fact bill above 25% of list — never trips the wire. The failure direction is unsafe (reserve stays at 25% when it should revert to 100%). The evidence base (127/127 reported calls) makes likelihood low, but the gap is real and worth noting.

**Mimo's `backend=None` skip [P3]:** I did not explicitly call out that `_settle(key, backend=None, ...)` bypasses the entire tripwire block. If any settle path for an xAI call passes `backend=None`, the trip is silently missed. This is pre-existing structure (the `by_backend` accounting has the same gate), but the ruling's "after every outside call" makes it worth confirming.

**Mimo's day-2 test side-effect [P3]:** I missed that the day-2 leg of the test runs with mutated `g._usage` (`usd_reported=0.02`), which is above 25% of list ($0.01375), so day-2's ledger actually gets tripped during settle — but the test neither expects nor asserts this. The claim under test ("a new day's ledger: 25% again") is still proven by the call running, but the unasserted trip is a clarity issue.

**Qwen's locking concern:** Qwen raised a P1 about `_settle` writing `reserve_tripped` without holding `self._lock()`. The consensus correctly rejected this — the diff hunk simply didn't show the `with self._lock():` line, but `_settle` does all its ledger work under that lock (dev46 providers.py:1020, unchanged). I agree with the consensus: **not a defect**.

---

## 2. WHERE DO I AGREE OR DISAGREE?

| Finding | Model | Verdict | Reasoning |
|---------|-------|---------|-----------|
| No P0/P1 defects | Gemma | **Agree** | The tripwire comparison, persistence, specificity, and fail-closed defaults are all correct. |
| Unreported calls don't trip [P3] | Mimo | **Agree** | Real gap, unsafe direction, but evidence base makes it unlikely. The ruling says "compare what was billed" — if billing is unknown, comparison is impossible. Arguably by design. |
| `backend=None` skips tripwire [P3] | Mimo | **Agree** | Pre-existing gate, but worth confirming all xAI settle paths pass the backend. |
| TOCTOU race [P3] | Mimo | **Agree** | A call that read the fraction an instant before another call's trip still reserves at 25%. The ruling explicitly accepts "one call's overshoot." With parallel step-A batches it's at most the calls in flight then. No change needed. |
| Ledger persistence failure loses trip [P3] | Mimo | **Agree** | Inherits existing write-failure behavior (raises, fail-closed per M12). The trip specifically is a fail-open artifact, but this is consistent with how the ledger already works. |
| Day-2 test doesn't assert day-2 ledger [P3] | Mimo | **Agree** | Clarity nit. The test's claim is still proven; the unasserted side effect deserves a line. |
| Locking race in `_settle` [P1] | Qwen | **Disagree** | The consensus is correct: `_settle` does all work inside `with self._lock():`. The diff hunk didn't show the `with` line. Not a defect. |
| Tripwire comparison is correct | Gemma, Mimo | **Agree** | `float(usage["usd_reported"]) > float(f) * usd` where `usd` is the list price of actual usage. Matches "bills above 25% of list." Test confirms `trip["list"] == 0.055` (true list cost, not reserved amount). |
| Trip holds for the day | Gemma, Mimo | **Agree** | `_reserve_fraction` reads under lock; trip persisted in ledger file; new day = new ledger = no trip. Test's day-2 leg proves reset. |
| Only named backend changes | Gemma, Mimo | **Agree** | One key in `model_providers.json`; `_reserve_fraction` returns None for backends without it; test `test_only_a_back_end_that_names_the_fraction_is_reserved_below_list` verifies. |

---

## 3. NEW FINDINGS FROM THIS REVIEW

**[P3] Notice message redundancy:** The `why` field already contains "billed above 25% of list: reserved at list for the rest of the day (ruling 123 (1))", and the notice appends "billed $X, list $Y" after it. The resulting message reads: *"RESERVE BACK TO LIST: xai:g billed above 25% of list: reserved at list for the rest of the day (ruling 123 (1)): billed $0.0200, list $0.0550"* — the "billed above" and "billed $..." are redundant. Cosmetic only.

**[P3] Tripwire threshold when `usd` (list of usage) is 0:** If `usd` is 0 (no tokens used) but `billed > 0`, the condition `billed > f * 0 = 0` is true for any positive billing, tripping the wire. This is arguably correct (anomalous data should trip), but worth noting as an edge case. Not reachable in practice with real usage.

**No new P0/P1/P2 findings.** The combined analysis confirms the implementation is correct.

---

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|-----------|---------|---------|-------------|
| Tripwire comparison | 0 defects | 0 defects | Confirmed correct by all three models |
| Trip persistence / day-hold | 0 defects | 0 defects | Confirmed correct; day-2 test nit is P3 |
| Backend isolation | 0 defects | 0 defects | Confirmed correct |
| Tests | 0 defects | 0 defects | Day-2 side-effect nit is P3; coverage is adequate |
| Locking / concurrency | 0 defects | 0 defects | Qwen's P1 correctly rejected by consensus |
| **Overall P1_OR_WORSE** | **0** | **0** | No change |

---

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None.

**P1 HIGH:** None.

**P2 MEDIUM:** None.

**P3 (nit, fix if convenient):**
1. **Unreported-call gap** — `pipeline/providers.py` `_settle` (~line 1030): an abandoned call with no `usd_reported` never trips the wire. Consider tripping on `usd_unreported_estimate` if it exceeds the threshold, or document the gap.
2. **`backend=None` skip** — `pipeline/providers.py` `_settle` (~line 1026): confirm all xAI settle paths pass `backend`. Pre-existing gate.
3. **Day-2 test side-effect** — `tests/providers/test_providers.py` (~line 139): the day-2 call with mutated usage trips day-2's ledger; add an assertion or reset `g._usage` before the day-2 leg.
4. **Notice redundancy** — `pipeline/providers.py` `_settle` (~line 1055): the `why` field and the appended "billed $X, list $Y" overlap. Cosmetic.

---

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**Add one assertion to the day-2 test leg confirming day-2's ledger state (tripped or not) so the test's claim about day-boundary reset is fully proven rather than inferred from the call succeeding.**

---

## 7. PRODUCTION READY?

**Yes.** The implementation correctly implements RULING 123 (1): the tripwire comparison is right, the trip persists for the day, only the named backend is affected, and the tests cover the critical paths. All findings are P3 (nits). No conditions — the P3 items are polish, not blockers.

---

P1_OR_WORSE: 0