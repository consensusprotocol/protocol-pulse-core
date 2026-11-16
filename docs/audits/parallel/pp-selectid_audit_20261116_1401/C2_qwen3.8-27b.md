# qwen3.8-27b (qwen/qwen3.8-27b) 30 s finish=stop usage in 8928 / out 2110 usd_reported=0.001920 usd~0.058 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261116_1401
# Reviewer: Heimdall (Cycle 2)

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I (and the consensus) correctly identified that the locking was sound, but I missed a subtle **test isolation defect** that `mimo-v2.6-flash-rl` caught in its Check (2) [P3] and which is actually more significant than a nit.

**The Missed Defect:**
In `tests/providers/test_providers.py`, the `TestRuling123Reserve` class uses a shared `Fake` backend instance `g` across the "Day 1" and "Day 2" legs of `test_a_quarter_of_list_until_a_call_bills_above_it_then_list_for_the_day`.
- Line 128: `g._usage` is mutated to `{"in": 1000, "out": 2000, "usd_reported": 0.02}` to trigger the tripwire on Day 1.
- Line 137-139: A new router `day2` is created with a new ledger `day2.json`. The test calls `day2.call(...)`.
- **The Problem:** The `Fake` backend `g` still has `_usage` set to `usd_reported: 0.02`. When `day2.call` settles, it will **also** trip the wire in `day2.json` because `0.02 > 0.25 * 0.055`.
- The test asserts `g.calls == 4` (Line 140), which passes because the call *runs* (the reserve is 25% initially, so it fits). However, the test **fails to assert** that `day2.json` contains a `reserve_tripped` entry.
- **Why this matters:** The test claims to prove "a new day's ledger: 25% again." It proves the call *runs*, but it does not prove the state is clean. If the tripwire logic were broken such that it *didn't* reset on a new day (e.g., if it read from a global cache instead of the ledger), this test might still pass if the reserve calculation was correct, but the *trip state* would be wrong. More critically, if the tripwire logic were broken such that it *persisted* across days (e.g., if `reserve_tripped` was stored in the backend object instead of the ledger), the Day 2 call would be reserved at List ($0.38), and `0.69 + 0.38 > 1.00`, so the call would **fail** with `SpendLimit`. The test would catch that.
- **However**, the current test is ambiguous about the *side effect*. `mimo` correctly noted that the unasserted side effect (the trip in Day 2) is worth checking. If the intent is to show that Day 2 starts fresh at 25%, the test should ideally use a *new* backend instance or reset `_usage` to a low value (e.g., `0.01`) to ensure the Day 2 call does *not* trip the wire, thereby isolating the "fresh start" behavior from the "tripwire still active" behavior. As written, Day 2 *also* trips the wire. This makes the test less precise in verifying the "reset" aspect.

**Other Missed Points:**
- `mimo` correctly identified the race condition window (Check 1, P3) where a call reading the fraction before the trip and reserving after it could still reserve at 25%. The consensus correctly dismissed this as acceptable per the ruling ("one call's overshoot").
- `qwen`'s P1 about locking was correctly dismissed by the consensus.

## 2. WHERE DO YOU AGREE OR DISAGREE?

| Model | Finding | My Stance | Reason |
| :--- | :--- | :--- | :--- |
| **Gemma** | "No defects found." | **Disagree** | Gemma missed the test isolation/precision issue in `TestRuling123Reserve`. The test is not as clean as claimed. |
| **Mimo** | Check 2 [P3]: "Day-2 leg does not assert day-2's ledger state... unasserted side effect is worth a line of assertion." | **Agree** | This is the most valuable finding. The test should be tightened to ensure Day 2 is truly "fresh" (no trip) or explicitly assert the trip if that's the intent. |
| **Mimo** | Check 1 [P3]: Race window. | **Agree** | Correctly identified, but correctly dismissed as acceptable per ruling. |
| **Qwen** | P1: Locking issue. | **Disagree** | The consensus correctly proved this is a false positive. `_settle` holds the lock. |
| **Consensus** | "P1_OR_WORSE: 0" | **Partially Agree** | I agree there are no P0/P1 *code* defects. However, the *test* defect is a P2 (should fix) that impacts confidence in the "reset" behavior. |

## 3. NEW FINDINGS FROM THIS REVIEW

**[P2] Test Precision: `TestRuling123Reserve.test_a_quarter_of_list_until_a_call_bills_above_it_then_list_for_the_day`**
- **File:** `tests/providers/test_providers.py`
- **Lines:** 128-140
- **Issue:** The test reuses the same `Fake` backend `g` for Day 1 and Day 2. After Day 1 trips the wire, `g._usage` is left at `usd_reported: 0.02`. When Day 2 runs, it *also* trips the wire in `day2.json`.
- **Impact:** The test does not cleanly verify that a new day starts *without* a trip. It verifies that a new day *can* run a call, but since the call also trips the wire, it doesn't isolate the "reset" logic from the "trip" logic.
- **Fix:** Either:
    1. Reset `g._usage` to a low value (e.g., `0.01`) before the Day 2 call, and assert that `day2.json` does *not* contain `reserve_tripped`.
    2. Or, create a new `Fake` backend instance for Day 2.
    3. Or, explicitly assert that `day2.json` *does* contain `reserve_tripped` if the intent is to show the tripwire works on Day 2 as well (but then the test name "a new day's ledger: 25% again" is misleading, as it's 25% *until* the trip, then List).

**[P3] Documentation Clarity: `_reserve_fraction` Docstring**
- **File:** `pipeline/providers.py`
- **Lines:** 24-27
- **Issue:** The docstring says "until a call of it bills above that fraction of the list price of what it used". It doesn't explicitly state that the trip is *per ledger day*. The code is correct, but the docstring could be clearer for future maintainers.
- **Fix:** Add "for the rest of the current ledger day" to the docstring.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| **Tripwire Logic** | Pass | Pass | Logic is correct. |
| **Persistence** | Pass | Pass | Ledger is the source of truth. |
| **Isolation** | Pass | Pass | Only xAI backend affected. |
| **Tests** | Pass | **Conditional Pass** | Test has a precision issue (P2) that should be fixed to clearly verify the "reset" behavior. |
| **Locking** | Pass | Pass | Confirmed by consensus. |

## 5. FINAL PRIORITY LIST

1.  **[P2] Fix Test Precision:** In `tests/providers/test_providers.py`, modify `test_a_quarter_of_list_until_a_call_bills_above_it_then_list_for_the_day` to ensure the Day 2 leg clearly verifies the "fresh start" behavior. Reset `g._usage` to a low value before the Day 2 call and assert that `day2.json` does *not* contain `reserve_tripped`. This will prove that the tripwire state is correctly scoped to the ledger day.
2.  **[P3] Clarify Docstring:** In `pipeline/providers.py`, update the `_reserve_fraction` docstring to explicitly mention "for the rest of the current ledger day."

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**Tighten the test to explicitly verify that the tripwire state resets on a new ledger day by ensuring the Day 2 call does *not* trip the wire and asserting the absence of `reserve_tripped` in the new ledger.**

## 7. PRODUCTION READY?

**Yes with conditions.**

**Condition:** The test precision issue (P2) must be fixed. The code is correct, but the test does not fully validate the "reset" behavior as intended. Once the test is updated to clearly show that a new day starts without a trip, this is production-ready.

P1_OR_WORSE: 0