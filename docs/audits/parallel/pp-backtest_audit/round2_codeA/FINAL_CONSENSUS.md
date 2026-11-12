# CONSENSUS REPORT — PULSE-SENTENCE-LAW — CYCLE 2
Generated: 2026-11-12 03:53
Models: gpt4o, grok (+1 failed)

---

## SCORES

| Subsystem            | Gemini | GPT-4o | Grok   | Consensus |
|----------------------|--------|--------|--------|-----------|
| Correctness          | N/A    | 9/10   | 10/10  | **9.5/10** |
| Law Compliance       | N/A    | 9/10   | 10/10  | **9.5/10** |
| Test Coverage        | N/A    | 4/10   | 3/10   | **3.5/10** |
| Security / Atomicity | N/A    | 8/10   | 9/10   | **8.5/10** |
| Overall Readiness    | N/A    | READY* | HOLD   | **HOLD** |

*GPT-4o marked READY-with-conditions; Grok marked explicit HOLD pending P0 test suite. Consensus defers to the stricter verdict: **HOLD**.

---

## UNANIMOUS FINDINGS (all 2 models agree — implement unconditionally)

### U1 — Zero test code present in the diff
**What it is:** The diff contains no executable test files. References to `tests/oracle/test_oracle_export.py` and `test_oracle_*.py` appear only as comments. No must-fail fixtures exist for any of the fail-closed paths the code introduces.

**Affected files/lines:**
- `lineup.py:746–772` (`parse_oracle` → `OracleFailed`)
- `lineup.py:775–796` (`parse_judge` → `JudgeFailed`)
- `lineup.py:810–860` (`check` — all rule branches)
- `llm.py:970–1062` (`Ledger` — over-cap rejection)

**What to change:** Add `tests/oracle/test_oracle_export.py` and companion modules containing:
1. A must-fail fixture proving `parse_oracle` raises `OracleFailed` on malformed, empty, and internally inconsistent oracle replies.
2. A must-fail fixture proving `parse_judge` raises `JudgeFailed` equivalently.
3. At least one pass-fixture and one violation-fixture for every deterministic rule branch in `check` (consecutive IDs, duration windows, altcoin screen, channel counts).
4. A `Ledger` over-cap rejection fixture exercised under simulated concurrent access.

### U2 — External dependencies in `call_backend` are not mockable in confirmed tests
**What it is:** `call_backend` (`providers.py:1550–1591`) invokes live vendor APIs. No test module confirms a registered stub/fake backend path, meaning any CI run reaching `providers.call` is non-deterministic and potentially billable.

**Affected files/lines:** `providers.py:1550–1591`

**What to change:** Document and enforce a mock/fake-backend registration point in every test module that exercises any `call_backend` code path. A fixture-level monkeypatch or a named fake provider registered before each test suite is acceptable; the mechanism must be explicit and checked in.

---

## MAJORITY FINDINGS (2 of 2 models agree)

All unanimous findings above are also majority findings by definition. No additional findings reached majority without also being unanimous given the two-model quorum. See U1 and U2 above.

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### I1 — `replay.py`/`score.py` NotRerun path and silent stage misclassification *(Grok only)*
**What it is:** The `replay` function (`replay.py:1753–1806`) plus `score.py`'s near-carrier logic (`score.py:2860`) interact through `CacheOnlyLLM`, `_Checkpoint` monkey-patching, and `trace`. A missed `NotRerun` path or an incorrect `progress` snapshot could silently convert a `NOT_RERUN` into an incorrect loss stage — a logic error that would not raise an exception and would not be visible in any existing test.

**Assessment: Investigate further → then implement.** This is the most architecturally subtle surface in the entire diff (Grok's observation that it's buried in 3,500 lines is accurate). The failure mode is silent and correctness-breaking, not merely cosmetic. Add a synthetic-record fixture that deliberately hits the `NotRerun` branch and asserts the correct stage label before any further changes touch `replay.py`.

### I2 — `ab.py` swap construction and withdrawn-item merge correctness *(Grok only)*
**What it is:** `_swap` construction and the `merge` logic for withdrawn items in `ab.py` are described as correct on paper, but no exercised test proves that a must-fail swap is counted only when the judge fails on rule 1.

**Assessment: Implement.** The claim "correct on paper" is insufficient for a spend-gated, audit-logged subsystem. Add a must-fail swap fixture to the P0 test suite.

### I3 — Documentation quality positive note *(GPT-4o only)*
**What it is:** GPT-4o noted that docstrings are thorough and well-structured throughout the diff.

**Assessment: Skip as an action item** — it is a strength (see Validated Strengths below), not a gap. No change needed.

---

## CONFLICTS (models disagree — your tiebreaker)

### C1 — Overall readiness verdict
**GPT-4o:** READY with conditions (tests are P1, not a blocker).
**Grok:** NOT READY until P0 test suite is present and green.

**Tiebreaker — Grok is correct.** The audit mandate explicitly requires that every fail-closed path be proven by a must-fail fixture. `parse_oracle`, `parse_judge`, `check`, and `Ledger` are all fail-closed by construction, and none have exercised tests. Shipping fail-closed code with zero test proof of the closed paths is equivalent to shipping with unknown behavior on the most critical branches. The stricter verdict stands: **HOLD pending P0 tests.**

### C2 — Severity of test-coverage gap
**GPT-4o:** Low-severity, housekeeping, does not block.
**Grok:** Critical blocker; direct violation of audit mandate.

**Tiebreaker — Grok is correct** for the same reason as C1. The distinction between "housekeeping" and "blocker" is not stylistic here — it determines whether the PR merges. The audit mandate is unambiguous: must-fail fixtures are required, not optional.

---

## VALIDATED STRENGTHS (all models agree — do NOT change in the second pass)

1. **Fail-closed parsing** — `parse_oracle` and `parse_judge` raise typed exceptions on every malformed/empty/inconsistent reply path and never return a partial result. This architecture is correct and must not be relaxed.

2. **Deterministic rule enforcement in `check`** — All rule branches (consecutive IDs, duration windows, altcoin screen, channel counts) are applied exactly as documented with no silent pass-through. Do not alter thresholds or add conditional bypasses.

3. **Atomic ledger operations** — `Ledger` uses file locking for all spend/inflight mutations and enforces the cap before any commit. The mechanism is correct; do not replace it with a non-atomic alternative.

4. **Law-delegation correctness** — `tokens`/`sentences` correctly delegate to `transcript_store.read_text`, `sentence_law.is_terminal`, and `editorial_select._word_sentences` without recomputing cut points or edge-word logic after selection. This is precisely the right boundary. Do not absorb those functions inline.

5. **Schema strictness** — All model-reply schemas are validated with typed fields; missing or mistyped fields propagate as failures, never as defaults. Do not add default-fallback logic.

6. **Docstring quality** — Docstrings throughout the diff are thorough and accurate. Preserve them as new test code is added.

---

## LAW COMPLIANCE CONSENSUS

| Law / Rule               | Status         | Basis |
|--------------------------|----------------|-------|
| SENTENCE LAW             | **COMPLIANT**  | Sentence boundaries via `sentence_law.is_terminal`; no recomputation after selection |
| SELECTION LOCK           | **COMPLIANT**  | Sentence IDs validated against day's export; no post-selection recomputation |
| SNAP LIMIT               | **COMPLIANT**  | `check` enforces duration windows deterministically |
| NEIGHBOUR                | **COMPLIANT**  | Diff does not touch cut-point or edge-word logic |
| ONSET / TAIL             | **COMPLIANT**  | Duration constraints in `check` enforce indirectly; `layout_eligible` read-only |
| CREDITS                  | **COMPLIANT**  | `layout_survives` checks layout eligibility; not modified |
| L-j (schema strictness)  | **COMPLIANT**  | Strict schemas, typed exceptions on any deviation |
| L-l (unmeasured items)   | **COMPLIANT**  | Unmeasured items reported as such, never promoted |
| L-m (reference behaviour)| **COMPLIANT**  | No loosening of gate thresholds; v2f reference untouched |

**No law violations detected.** Compliance is contingent on the existing fail-closed paths remaining untouched, which is enforced by the validated strengths above.

---

## SECURITY CONSENSUS

| Issue | Priority | Models | Detail |
|-------|----------|--------|--------|
| Non-deterministic/billable CI from live API calls in `call_backend` | **P1** | Both | Without a confirmed mock path, any CI run that reaches `providers.call` incurs real spend and produces non-deterministic results. |
| Atomic ledger enforcement | **Strength** | Both | File-lock mechanism is correct; no security gap identified. |
| No writes to transcript store or `/home/ultron/protocol_pulse` by this diff | **Strength** | Both | Export reads only; ledger writes to caller-supplied path outside the store. |

No P0 security vulnerabilities identified. The only security-adjacent risk is the unguarded live API call path in tests, which is a P1.

---

## WORLD-CLASS GAP CONSENSUS

Items mentioned by 2+ models:

### WCG-1 — Must-fail test fixtures for all fail-closed paths
Both models agree this is the single largest gap between the current state and a world-class product. A codebase whose correctness is entirely predicated on fail-closed exception paths — and which has zero exercised proof of those paths — cannot be called world-class regardless of how clean the production code is. The production code is excellent; the test layer is absent.

### WCG-2 — Confirmed mock/fake backend for all LLM call paths
Both models agree that an explicit, documented, enforced mock registration point for `call_backend` is required. World-class LLM pipelines never allow live API calls in CI, both because of cost and because non-determinism makes green tests meaningless.

---

## FINAL ACTION PLAN (sorted by consensus priority)

| Priority | Change | File:Line | Models | Why |
|----------|--------|-----------|--------|-----|
| **P0 CRITICAL** | Add must-fail fixture: `parse_oracle` raises `OracleFailed` on malformed, empty, and inconsistent oracle replies | `tests/oracle/test_oracle_export.py` (new file) / `lineup.py:746–772` | Both | Zero test proof of the most critical fail-closed path; audit mandate requires it |
| **P0 CRITICAL** | Add must-fail fixture: `parse_judge` raises `JudgeFailed` equivalently | `tests/oracle/test_oracle_export.py` / `lineup.py:775–796` | Both | Same rationale; `JudgeFailed` path has identical risk |
| **P0 CRITICAL** | Add pass + violation fixture for every rule branch in `check` (consecutive IDs, duration windows, altcoin screen, channel counts) | `tests/oracle/test_oracle_export.py` / `lineup.py:810–860` | Both | Deterministic rules with no exercised test cannot be trusted in production |
| **P0 CRITICAL** | Add `Ledger` over-cap rejection fixture under simulated concurrent access | `tests/oracle/test_ledger.py` (new) / `llm.py:970–1062` | Both | Atomic ledger is the spend guard; must be proven, not assumed |
| **P0 CRITICAL** | Add must-fail swap fixture for `ab.py` — prove swap counted only on judge-fails-rule-1 | `tests/oracle/test_ab.py` (new) / `ab.py` | Grok (unique but implement) | Silent correctness failure in spend-gated subsystem; too high risk to defer |
| **P1 HIGH** | Register and document explicit mock/fake backend for all `call_backend` paths in every test module that touches it | `providers.py:1550–1591` / test modules | Both | Live API calls in CI are non-deterministic and billable |
| **P1 HIGH** | Add synthetic-record fixture hitting `replay.py:1786` `NotRerun` branch; assert correct stage label | `tests/oracle/test_replay.py` (new) / `replay.py:1753–1806` | Grok (unique but investigate→implement) | Silent stage misclassification; no exception raised on wrong path |
| **P2 MEDIUM** | Add synthetic-record fixture for `score.py:2860` near-carrier logic | `tests/oracle/test_score.py` (new) / `score.py:2860` | Grok | Completes replay/score surface coverage; lower risk than NotRerun path |
| **P2 MEDIUM** | Document mocking strategy in test module docstrings for maintainability | All new test files | GPT-4o | Prevents future contributors from bypassing mock layer |

---

## CYCLE 2 VERDICT

**NOT PRODUCTION READY.**

The production code itself — correctness, law compliance, schema strictness, atomic ledger, fail-closed parsing — is of high quality and contains no defects. Both models confirmed this across two cycles.

**The absolute final blocker is the complete absence of test code.** The diff introduces fail-closed paths in `parse_oracle`, `parse_judge`, `check`, and `Ledger` that are the primary safety guarantees of the entire pipeline. None of them have exercised must-fail fixtures. An audit of a system whose safety relies on exception paths, where none of those exception paths have ever been triggered in a test, cannot issue a READY verdict.

**Condition for READY:** All P0 items above must be implemented, committed, and show zero FAILs in `regression_test.sh`. P1 items (mock registration, `NotRerun` fixture) should accompany the same PR. The code may then be considered production-ready.

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/PULSE_SENTENCE_LAW_GOSPEL.md.
Read ~/protocol_pulse/docs/audits/pulse-sentence-law_CONSENSUS_C2.md.

This is the FINAL PASS for pulse-sentence-law.
The first build was reviewed by 2 independent AI models across 2 cycles.
Implement every P0 and P1 item from the consensus. Use judgment on P2.

PRIORITY ACTION PLAN:

P0 CRITICAL | Add must-fail fixture: parse_oracle raises OracleFailed on malformed/empty/inconsistent oracle reply | tests/oracle/test_oracle_export.py (new) / lineup.py:746–772 | models: both | Zero test proof of primary fail-closed path; audit mandate requires it

P0 CRITICAL | Add must-fail fixture: parse_judge raises JudgeFailed on malformed/empty/inconsistent judge reply | tests/oracle/test_oracle_export.py / lineup.py:775–796 | models: both | Same rationale as above

P0 CRITICAL | Add pass-fixture + violation-fixture for every rule branch in check (consecutive IDs, duration windows, altcoin screen, channel counts) | tests/oracle/test_oracle_export.py / lineup.py:810–860 | models: both | Deterministic rules have no exercised proof; cannot be trusted in production

P0 CRITICAL | Add Ledger over-cap rejection fixture under simulated concurrent access | tests/oracle/test_ledger.py (new) / llm.py:970–1062 | models: both | Atomic ledger is the spend guard; must be proven, not assumed

P0 CRITICAL | Add must-fail swap fixture for ab.py proving swap is only counted when judge fails on rule 1 | tests/oracle/test_ab.py (new) / ab.py | models: grok (implement) | Silent correctness failure in spend-gated subsystem; too high risk to defer

P1 HIGH | Register and document explicit mock/fake backend for all call_backend paths in every test module that exercises providers.call | providers.py:1550–1591 + all new test modules | models: both | Live API calls in CI are non-deterministic and billable

P1 HIGH | Add synthetic-record fixture hitting replay.py:1786 NotRerun branch; assert correct stage label is emitted | tests/oracle/test_replay.py (new) / replay.py:1753–1806 | models: grok (implement) | Silent stage misclassification; no exception raised on wrong path means failures are invisible

P2 MEDIUM | Add synthetic-record fixture for score.py:2860 near-carrier logic | tests/oracle/test_score.py (new) / score.py:2860 | models: grok | Completes replay/score surface coverage

P2 MEDIUM | Document mocking strategy explicitly in docstring of every new test module | all new test files | models: gpt4o | Prevents future contributors bypassing mock layer

VALIDATED (do NOT touch — all models confirmed excellent):
- parse_oracle / parse_judge fail-closed exception architecture (lineup.py:746–796) — do not add defaults or partial returns
- Deterministic rule enforcement in check (lineup.py:810–860) — do not alter thresholds or add bypasses
- Ledger atomic file-lock mechanism (llm.py:970–1062) — do not replace with non-atomic alternative
- tokens/sentences delegation to sentence_law.is_terminal and editorial_select._word_sentences — do not absorb inline or recompute after selection
- Strict model-reply schema validation with typed exceptions — do not add default-fallback logic
- Docstring quality throughout — preserve all existing docstrings as new test files are added

After implementing: regression_test.sh must show zero FAILs.
git add -A && git commit -m "feat(pulse-sentence-law): post-audit pass — consensus improvements"
git push origin combo-letterbox-quoteonly-v2
```

---

# WINNER DETERMINATION

# WINNER: **Grok** — Grok delivered the most rigorous analysis across all four criteria, correctly identifying zero-test coverage as a **blocking HOLD** rather than a housekeeping note, and uniquely surfaced the `replay.py`/`score.py` CacheOnlyLLM interaction as an unexamined failure surface that neither GPT-4o nor any other model caught. Its Cycle 2 self-correction was substantive rather than cosmetic, and its stricter HOLD verdict proved correct as the consensus deferred to it.

---

# FINAL SECOND-PASS PRIORITY LIST

Ordered by severity (P0 = release blocker → P3 = housekeeping). Implement top-to-bottom before any merge.

---

## P0 — RELEASE BLOCKERS (do not ship without these)

### P0-A: Must-fail test fixtures for every fail-closed path (U1)
**Files to create/modify:**
- `tests/oracle/test_oracle_export.py`
- `tests/oracle/test_lineup.py`
- `tests/ledger/test_ledger.py`

**Exact fixtures required:**
1. `test_parse_oracle_raises_on_malformed()` — empty dict, missing required fields, type mismatches → asserts `OracleFailed` raised, never returns partial result
2. `test_parse_oracle_raises_on_inconsistent()` — internally contradictory reply → asserts `OracleFailed`
3. `test_parse_judge_raises_on_malformed()` — same pattern → asserts `JudgeFailed`
4. `test_check_consecutive_ids_violation()` — non-consecutive sentence IDs → asserts violation returned
5. `test_check_duration_window_violation()` — duration outside spec → asserts violation
6. `test_check_altcoin_screen_violation()` — altcoin term present → asserts violation
7. `test_check_channel_count_violation()` — wrong channel count → asserts violation
8. `test_check_pass_fixture()` — one fully compliant lineup → asserts no violations
9. `test_ledger_overcap_rejection()` — spend attempt past cap → asserts refused, balance unchanged
10. `test_ledger_concurrent_rejection()` — simulated concurrent access via threading → asserts atomic enforcement

---

### P0-B: Mockable external dependencies in `call_backend` (U2)
**File:** `llm.py:1550–1591`

**What to implement:**
1. Extract provider dispatch into an injectable `_backend_caller` function parameter (default: live provider) so tests can substitute a deterministic stub
2. Register a `FakeBackend` class in `tests/conftest.py` that returns canned responses without network calls
3. Confirm in CI that no test touching `call_backend` reaches `providers.call` — enforce with a monkeypatch fixture that raises `RuntimeError("live call in test")` if the real provider is invoked

---

## P1 — HIGH PRIORITY (implement before next release cycle)

### P1-A: `replay.py` / `score.py` CacheOnlyLLM interaction (Grok-unique finding)
**Files:** `replay.py`, `score.py`

**Risk:** A missed `NotRerun` path or incorrect `progress` snapshot can silently convert a NOT_RERUN verdict into a wrong loss stage — no current test exercises this path.

**What to implement:**
1. `test_replay_cache_miss_stops_cleanly()` — cache miss mid-replay → asserts replay halts, no partial score emitted
2. `test_replay_not_rerun_path()` — explicit NOT_RERUN trigger → asserts correct loss stage recorded, not silently skipped
3. `test_checkpoint_snapshot_integrity()` — verify `_Checkpoint` state after each step matches expected `progress` value

---

### P1-B: `ab.py` swap/merge correctness under must-fail conditions (Grok-unique finding)
**File:** `ab.py`

**Risk:** `_swap` construction and `merge` logic for withdrawn items are unexercised; a must-fail swap counted outside judge-rule-1-failure is undetected.

**What to implement:**
1. `test_swap_only_counts_on_judge_rule1_failure()` — judge passes on rule 1 → asserts swap NOT counted
2. `test_swap_counts_on_judge_rule1_failure()` — judge fails rule 1 → asserts swap counted exactly once
3. `test_merge_withdrawn_items_idempotent()` — merge called twice on same withdrawn item → asserts no duplicate

---

## P2 — MEDIUM PRIORITY (address within 2 sprints)

### P2-A: Severity labelling consistency in audit tooling
**What to implement:** Standardise all audit outputs to use explicit `[P0]/[P1]/[P2]/[P3]` tags rather than `LOW/MEDIUM/HIGH` — the mixed vocabulary caused the GPT-4o cycle-2 output to underweight U1 as "low severity housekeeping" when it was a release blocker.

### P2-B: `tokens`/`sentences` edge-case coverage
**Files:** `export.py:402–439`

**What to implement:**
1. Test with transcript containing zero tokens → asserts empty list returned, no exception
2. Test with segment-level-only timing (no word-level timestamps) → asserts fallback path taken correctly
3. Test hash mismatch in `load_record` → asserts integrity error raised, not silently ignored

---

## P3 — HOUSEKEEPING (address before next audit cycle)

### P3-A: Comment-only test file references
Remove or replace all `# see tests/oracle/test_oracle_export.py` comments in source files until the actual test files exist — phantom references create false confidence in reviewers.

### P3-B: CI enforcement gate
Add a CI step that fails the build if `tests/` contains no file matching `test_oracle_*.py` — prevents the Cycle 1 error (comment references accepted as evidence of test existence) from recurring.

---

## IMPLEMENTATION ORDER SUMMARY

| Priority | Item | Owner Signal | Blocking? |
|---|---|---|---|
| P0-A | Must-fail fixtures for all fail-closed paths | Test eng | **YES** |
| P0-B | Mock injection for `call_backend` | Backend eng | **YES** |
| P1-A | `replay`/`score` CacheOnlyLLM tests | Backend eng | Next cycle |
| P1-B | `ab.py` swap/merge must-fail tests | Backend eng | Next cycle |
| P2-A | Audit severity label standardisation | Process | 2 sprints |
| P2-B | `tokens`/`sentences` edge cases | Test eng | 2 sprints |
| P3-A | Remove phantom comment references | Any | Before next audit |
| P3-B | CI test-existence gate | DevOps | Before next audit |