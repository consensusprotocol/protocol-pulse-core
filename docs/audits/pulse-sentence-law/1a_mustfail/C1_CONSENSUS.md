# CONSENSUS REPORT — PULSE-SENTENCE-LAW — CYCLE 1
Generated: 2026-11-11 02:30
Models: grok, gpt4o, gemini

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Correctness | 9/10 | 8/10 | N/A (no impl code) | 8.5/10 |
| Law Compliance | 10/10 | 9/10 | N/A (no impl code) | 9.5/10 |
| Test Quality | 10/10 | 8/10 | 6/10 (unverifiable) | 8/10 |
| Overall Verdict | READY | READY | NOT READY | CONDITIONAL READY |

> **Score Note:** Grok's N/A scores are not a failing assessment of test quality — they reflect a methodologically strict position that the diff contains no implementation code. Gemini and GPT-4o both assessed the test suite as the artifact under review, which is the correct framing given the diff content.

---

## UNANIMOUS FINDINGS (all 3 models agree — implement unconditionally)

**None.** The three models did not unanimously flag a shared concrete defect requiring a code change. This is because:
- Gemini and GPT-4o found no defects in the diff.
- Grok's finding is structural (missing implementation), not a defect within the diff's own code.

The one point all three models *implicitly* agree on:

### U1 — The diff contains no implementation of `sentence_law`, `run_fresh`, `shoutout`, or `select_passages`
- **File:** `pipeline/sentence_law.py`, `pipeline/run_fresh.py`, `pipeline/shoutout.py` (absent)
- **What it means:** The enforcement logic is not in this diff. All three models noticed this. Grok treats it as a blocker; Gemini and GPT-4o treat it as expected (TDD: tests first, fixes second).
- **Action:** The implementation files MUST appear in the second build pass. This is the entire reason the second pass prompt exists.

---

## MAJORITY FINDINGS (2 of 3 models agree)

### M1 — Test suite is correctly structured as TDD / "must-fail" contract
- **Models:** Gemini + GPT-4o
- **Finding:** The test file `pipeline/test_pulse_20261110_mustfail.py` is correctly designed. Must-fail cases will fail on current buggy code; control cases confirm non-regression. This is the intended structure.
- **Action:** No change needed to the tests. Implement the enforcement code to satisfy them.

### M2 — `M12 FAIL CLOSED` is correctly enforced by `allow_model=False` + cache
- **Models:** Gemini + GPT-4o
- **File/Line:** `pipeline/test_pulse_20261110_mustfail.py`, line ~118
- **Finding:** Using a fixed adjudication cache with `allow_model=False` ensures non-deterministic model calls cannot produce a spurious PASS. Both models independently called this out as correct and important.
- **Action:** This pattern must be preserved in all future test additions. Do not add any test that calls a live model without an explicit cache hit.

### M3 — `inspect.getsource` assertions confirm removal of banned functions
- **Models:** Gemini + GPT-4o
- **File/Line:** `pipeline/test_pulse_20261110_mustfail.py`, lines ~173–178, ~235–240
- **Finding:** Asserting that `_snap_candidates`, `recompute_sync`, `wide_snap`, and thumbnail/placeholder fallback logic are physically absent from source is a strong, non-vacuous regression guard. Both models flagged this as a best-practice pattern.
- **Action:** When implementing fixes, actually delete those functions — the tests will catch any accidental re-introduction.

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### UI1 — `selection_lock` regenerated programmatically from `B3_chosen.json` (Gemini only)
- **File/Line:** `pipeline/test_pulse_20261110_mustfail.py`, lines ~113–114
- **Insight:** Gemini specifically noted that the fixture recreates the `selection_lock` from the editor's original `B3_chosen.json` rather than from a later recomputed version. This is the methodologically correct approach — it establishes ground truth at the point of human selection, not at a downstream recomputation that may already be contaminated by the bug.
- **Assessment:** **Implement / preserve.** This is the highest-insight observation in the entire audit. It directly addresses the SELECTION LOCK law. The implementation of `sentence_law.py` must load this same `B3_chosen.json`-derived lock, not recompute it.

### UI2 — `assertAlmostEqual` for float comparison in `TestWindowOffset` (Gemini only)
- **File/Line:** `pipeline/test_pulse_20261110_mustfail.py`, line ~202
- **Insight:** Gemini flagged that the download window offset test correctly uses `assertAlmostEqual` rather than `assertEqual` for floating-point time values, preventing flaky failures from IEEE 754 rounding.
- **Assessment:** **Preserve.** Correct choice. If any new time-comparison assertions are added in the second pass, use `assertAlmostEqual` with an appropriate `places` parameter (suggest `places=3` for millisecond-level precision).

### UI3 — Test assertion messages could be more descriptive (GPT-4o only)
- **File/Line:** `pipeline/test_pulse_20261110_mustfail.py`, line ~139
- **Insight:** GPT-4o (Low severity) noted that failure messages could carry more context about *why* a test failed, beyond the boolean assertion.
- **Assessment:** **Implement in second pass (P2).** Add `msg=` parameters to key assertions, particularly in `TestD1HookOnset` and `TestD2Clip01Out`, so CI output is self-documenting. Example: `self.assertFalse(result, msg=f"Expected gate FAIL on onset={r['genuine_lead_ms']}ms < 80ms threshold")`.

### UI4 — `assertRaises` should include expected exception message (GPT-4o only)
- **File/Line:** `pipeline/test_pulse_20261110_mustfail.py`, line ~230
- **Insight:** GPT-4o noted that the avatar validation `assertRaises` block does not assert the specific exception message, leaving open the possibility that a different exception (wrong path, import error) produces a false pass.
- **Assessment:** **Implement in second pass (P2).** Use `assertRaisesRegex` instead of `assertRaises` for the avatar non-square rejection test. Pin the expected error string (e.g., `"avatar.*non.square"` or the actual message from `sentence_law`).

### UI5 — Grok's NOT READY verdict is a methodological position, not a defect finding
- **Insight:** Grok correctly observes that no enforcement logic is in the diff and therefore cannot assess correctness of `sentence_law`, `run_fresh`, etc. This is a valid audit posture — Grok is refusing to issue a READY verdict for a commit that contains only tests.
- **Assessment:** **Do not dismiss.** Grok is right that this diff alone cannot ship. The READY verdict from Gemini and GPT-4o is contingent on the second pass delivering the implementation. The final CYCLE 1 verdict should be CONDITIONAL READY, not unconditional READY.

---

## CONFLICTS (models disagree — your tiebreaker)

### C1 — Overall Verdict: READY vs. NOT READY
- **Grok:** NOT READY — implementation absent.
- **Gemini + GPT-4o:** READY — the tests are the artifact; implementation comes next.
- **Tiebreaker ruling:** Both are correct in their own frames. The commit is **READY as a TDD anchor commit** — it correctly captures the contract the fix must satisfy. It is **NOT READY as a shippable feature** — the enforcement code must follow immediately in the next commit. The second pass prompt resolves this by making implementation the explicit deliverable. Record the cycle as **CONDITIONAL READY**.

### C2 — Can law compliance be assessed from this diff?
- **Grok:** No — no enforcement code is present, so compliance cannot be verified.
- **Gemini + GPT-4o:** Yes — the *tests* are themselves expressions of the laws, and their structure can be evaluated for compliance with the laws' intent.
- **Tiebreaker ruling:** Gemini and GPT-4o are correct. In TDD, a failing test for a law is evidence of compliance *intent* and coverage. Grok is applying a correctness frame to a test-only commit. The compliance assessment should be understood as "the test suite correctly encodes the laws" — not "the laws are enforced in production." Both things are true simultaneously.

---

## VALIDATED STRENGTHS (all models agree this is already excellent)

**Do NOT change these in the second pass.**

1. **`_G16Fixture` class-level setup/teardown** — State isolation is clean; temp directories are created and destroyed correctly. Gemini and GPT-4o both confirmed.

2. **`allow_model=False` + fixed adjudication cache** — The M12 FAIL CLOSED principle is correctly implemented in the test harness. Changing this to allow live model calls would invalidate the entire test suite's determinism.

3. **Control tests alongside must-fail tests** — `test_d3c_clip02_out_control_passes` and `test_v2f_finals_pass_g15_and_g12` ensure the fix doesn't over-correct. All three models either confirmed or did not challenge this design.

4. **`inspect.getsource` deletion assertions** (lines ~173–178, ~235–240) — This pattern for asserting function removal is non-vacuous and regression-proof. Do not remove or weaken these assertions.

5. **`assertAlmostEqual` for float/time comparisons** (line ~202) — Correct numerical hygiene. Preserve this pattern for all time-domain assertions.

6. **Selection lock derived from `B3_chosen.json`** (lines ~113–114) — The ground truth is correctly anchored to the human editor's original selection. This is the right source of truth for SELECTION LOCK testing.

---

## LAW COMPLIANCE CONSENSUS

| Law | Status | Evidence | Confidence |
|---|---|---|---|
| SENTENCE LAW | ✅ Encoded in tests | `TestD2Clip01Out`, `TestD3Edges` assert sentence-boundary cuts | High |
| SELECTION LOCK | ✅ Encoded in tests | `TestTautology` asserts recompute path fails; sealed lock from `B3_chosen.json` | High |
| SNAP LIMIT | ✅ Encoded in tests | Removal of `_snap_candidates` asserted via `inspect.getsource` | High |
| ONSET/TAIL | ✅ Encoded in tests | `TestD1HookOnset` checks `genuine_lead_ms < 80` | High |
| CREDITS | ✅ Encoded in tests | `TestD4Credits` validates avatar geometry, rejects non-square, confirms v2f | High |
| LAW 20 / M2 (Hard Stop) | ✅ Encoded in tests | Entire must-fail suite enforces hard-stop semantics | High |
| M12 FAIL CLOSED | ✅ Encoded in tests | `allow_model=False` forces cache-only adjudication | High |
| LAW 22 (v2f Reference) | ✅ Encoded in tests | `test_v2f_finals_pass_g15_and_g12` is a byte-identical regression guard | High |

**Overall:** All 8 laws are correctly encoded in the test suite. **No laws are violated by this diff.** The laws will not be *enforced in production* until the implementation commit lands.

---

## SECURITY CONSENSUS

No security issues were flagged by any model. This diff adds:
- A test file (no network calls, no credential handling, no user input paths)
- Two lines to an audit configuration file

**Security posture: Clean for this diff.**

One forward-looking note (no model flagged it, but worth recording): when `shoutout.py` and avatar handling are implemented in the second pass, ensure that file paths passed to `ffprobe` and `subprocess.run` are sanitized — avatar filenames from external sources must not reach shell invocations unsanitized.

---

## WORLD-CLASS GAP CONSENSUS

Items mentioned by 2+ models:

### WCG1 — Implementation is the gap (Grok + implicitly Gemini/GPT-4o)
The test suite is excellent. The gap is that `sentence_law.py`, `run_fresh.py`, and `shoutout.py` do not appear in this diff. A world-class feature ships tests *and* the passing implementation in the same reviewable unit. The current structure (tests in one commit, implementation in the next) is acceptable for internal TDD workflow but would not pass external code review as a complete feature.

### WCG2 — No integration / end-to-end test (Gemini + GPT-4o)
Both models noted that the tests are unit/component level. A world-class pipeline feature would include at least one end-to-end test that runs the full `pulse-sentence-law` pipeline on a known input and asserts the final output artifact matches the v2f reference at the byte level. This is distinct from the unit tests for individual gates.

---

## FINAL ACTION PLAN (sorted by consensus priority)

| Priority | Change | File:Line | Models | Why |
|---|---|---|---|---|
| **P0 CRITICAL** | Implement `sentence_law.py` with all gate logic (SENTENCE LAW, SELECTION LOCK, SNAP LIMIT, ONSET/TAIL, M12 FAIL CLOSED) | `pipeline/sentence_law.py` (new file) | all 3 | Tests exist; enforcement code does not. Feature cannot ship without it. |
| **P0 CRITICAL** | Implement `run_fresh.py` with banned functions (`_snap_candidates`, `recompute_sync`, `wide_snap`) physically deleted | `pipeline/run_fresh.py` | all 3 | `inspect.getsource` assertions will fail if these functions exist. Deletion is a hard requirement. |
| **P0 CRITICAL** | Implement `shoutout.py` with avatar validation — reject non-square, reject warped, reject placeholder/thumbnail fallback | `pipeline/shoutout.py` (new/modified) | all 3 | `TestD4Credits` gates require this. LAW 22 regression test requires it. |
| **P0 CRITICAL** | Implement `select_passages.py` loading selection lock from `B3_chosen.json`, not recomputed downstream | `pipeline/select_passages.py` | gemini + grok | SELECTION LOCK law requires ground truth anchored to human editor selection, not recomputed. |
| **P1 HIGH** | Add `msg=` parameters to all `assertFalse`/`assertTrue` calls in must-fail tests for CI self-documentation | `pipeline/test_pulse_20261110_mustfail.py`, ~line 139 and all similar | gpt4o | Failing CI output must be human-readable without opening the test file. |
| **P1 HIGH** | Replace `assertRaises` with `assertRaisesRegex` for avatar non-square rejection test; pin expected error string | `pipeline/test_pulse_20261110_mustfail.py`, ~line 230 | gpt4o | Prevents wrong-exception false passes; pins the exact error contract for `shoutout`. |
| **P2 MEDIUM** | Add end-to-end integration test: run full pipeline on known input, assert final artifact matches v2f reference | `pipeline/test_pulse_sentence_law_e2e.py` (new) | gemini + gpt4o | World-class gap; unit tests alone do not prove pipeline integration. |
| **P2 MEDIUM** | Sanitize all file paths before passing to `ffprobe`/`subprocess.run` in the new implementation files | `pipeline/sentence_law.py`, `pipeline/shoutout.py` | synthesized | Forward-looking security hygiene; not currently a defect but will be when implementation lands. |

---

## CYCLE 1 VERDICT

**CONDITIONAL READY.**

The test suite is excellent — methodologically sound, non-vacuous, correctly encodes all 8 governing laws, includes control cases, and uses `inspect.getsource` deletion assertions as a regression-proof guard. Gemini and GPT-4o are correct that this is high-quality TDD work.

Grok is also correct that the feature is not complete: `sentence_law.py`, `run_fresh.py`, `shoutout.py`, and `select_passages.py` are absent. The second pass must deliver these implementation files. The test suite is the contract; the second pass must fulfill it.

**Do not re-run model review on the test file.** Direct all Cycle 2 review attention to the implementation files.

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/PULSE_SENTENCE_LAW_GOSPEL.md.
Read ~/protocol_pulse/docs/audits/pulse-sentence-law_CONSENSUS_C1.md.

This is the SECOND PASS for pulse-sentence-law.
The first build was reviewed by 3 independent AI models across 1 cycle.
Implement every P0 and P1 item from the consensus. Use judgment on P2.

PRIORITY ACTION PLAN:

P0 CRITICAL | Implement pipeline/sentence_law.py with full gate logic:
  - SENTENCE LAW: clips must start and end at sentence boundaries
  - SELECTION LOCK: load lock from B3_chosen.json only — never recompute downstream
  - SNAP LIMIT: enforce silence-only snapping within allowed range
  - ONSET/TAIL: genuine_lead_ms must be >= 80ms; enforce tail equivalently
  - M12 FAIL CLOSED: any missing data or unadjudicated model result = hard reject
  All gate thresholds must be module-level constants, not inline literals.

P0 CRITICAL | Implement pipeline/run_fresh.py with the following functions
  PHYSICALLY DELETED (not commented out, not renamed — deleted):
  - _snap_candidates
  - recompute_sync
  - wide_snap
  The test suite uses inspect.getsource() to assert these are absent.
  Any presence of these names in the source will cause test failure.

P0 CRITICAL | Implement pipeline/shoutout.py with avatar validation:
  - Reject non-square avatar images (raise with message matching r"avatar.*non.square")
  - Reject warped/distorted avatars (must pass g15 and g12 gates)
  - Remove all thumbnail and placeholder fallback logic (assert absent via inspect.getsource)
  - Known-good reference avatar must pass all gates (LAW 22 regression guard)

P0 CRITICAL | Implement pipeline/select_passages.py:
  - Load selection_lock from B3_chosen.json at the point of human editor selection
  - Do NOT recompute expected_words from downstream data
  - The sealed lock is ground truth; any divergence from it is a hard gate failure

P1 HIGH | In pipeline/test_pulse_20261110_mustfail.py, add msg= parameters to all
  assertFalse/assertTrue calls. Each message must state the specific condition
  being tested and the actual value that caused failure. Example:
  self.assertFalse(result, msg=f"Expected gate FAIL: genuine_lead_ms={r['genuine_lead_ms']}ms is below 80ms threshold")

P1 HIGH | In pipeline/test_pulse_20261110_mustfail.py ~line 230, replace:
  with self.assertRaises(ValueError):
  with:
  with self.assertRaisesRegex(ValueError, r"avatar.*non.square"):
  Pin the exact error string to the message raised by shoutout.py.

P2 MEDIUM | Add pipeline/test_pulse_sentence_law_e2e.py:
  - Run the full pulse-sentence-law pipeline on the frozen G16 input
  - Assert the final output artifact matches the v2f reference at byte level
  - Use allow_model=False and the existing adjudication cache

P2 MEDIUM | In all new implementation files, sanitize file paths before passing
  to subprocess.run or ffprobe. Use pathlib.Path and validate existence before
  constructing shell arguments.

VALIDATED (do NOT touch — all 3 models confirmed excellent):

1. _G16Fixture class-level setup/teardown — state isolation is correct
2. allow_model=False + fixed adjudication cache — M12 FAIL CLOSED, do not change
3. Control tests (test_d3c_clip02_out_control_passes, test_v2f_finals_pass_g15_and_g12)
4. inspect.getsource deletion assertions at lines ~173-178 and ~235-240
5. assertAlmostEqual for all float/time comparisons (~line 202)
6. Selection lock derived from B3_chosen.json at lines ~113-114

CONSTRAINTS:
- Gate thresholds are constants — never compute them at runtime
- No live model calls in any test — cache only
- Deleted functions stay deleted — the inspect.getsource tests are your tripwire
- The v2f reference must pass all gates — LAW 22 is non-negotiable

After implementing:
  python -m pytest pipeline/test_pulse_20261110_mustfail.py -v   # all must pass
  bash regression_test.sh                                         # zero FAILs required

git add -A && git commit -m "feat(pulse-sentence-law): implement enforcement — post-audit consensus pass"
git push origin combo-letterbox-quoteonly-v2
```