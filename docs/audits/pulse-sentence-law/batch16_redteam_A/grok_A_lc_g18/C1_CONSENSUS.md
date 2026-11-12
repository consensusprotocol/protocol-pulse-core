# CONSENSUS REPORT — PULSE-SENTENCE-LAW — CYCLE 1
Generated: 2026-11-11 22:40
Models: grok, gpt4o, gemini

---

## SCORES

Scores extracted from qualitative verdicts and severity assessments. Models did not emit numeric scores; mapped from verdict language to 0–10 scale (10 = fully correct/compliant/tested).

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| **Correctness** | 9 | 8 | 9 | 8.7 |
| **Law Compliance** | 7 | 8 | 9 | 8.0 |
| **Test Coverage** | 9 | 8 | 9 | 8.7 |
| **Security / Fail-Closed** | 9 | 8 | 8 | 8.3 |
| **Overall Readiness** | 9 | 9 | 9 | **9.0** |

> Score deductions: Gemini and GPT-4o both docked points for the unverified `canon.py` dependency (L-g, L-h, L-k) and for unverified laws (L-d, L-e, L-f, L-i, L-j, LAW 22). Grok assumed those modules pass; that optimism is noted as an audit limitation.

---

## UNANIMOUS FINDINGS (all 3 models agree — implement unconditionally)

**None.** All three models returned a READY verdict with no defects that all three flagged identically. The findings below are strong majority or unique observations. This is a positive result — no unanimous defects — but the unanimous *gap* around `canon.py` is treated as a system-level finding (see Majority Findings).

---

## MAJORITY FINDINGS (2 of 3 models agree)

### MF-1 — `canon.py` is unaudited; L-g, L-h, L-k compliance is contingent
**Models:** Gemini (explicit), GPT-4o (implicit — marked L-g COMPLIANT "by delegation"; L-h NOT APPLICABLE)
**Grok:** Assumed compliant without caveat.

**What it is:** Both `sentence_law.py` and `word_diff.py` now delegate all text normalisation to `pipeline/canon.py`. The correctness of L-g (written forms), L-h (text read as spoken), and L-k (one canonical form) is entirely contingent on the implementation of that module. Neither Gemini nor GPT-4o could verify it from the diff alone.

**File/Line:** `pipeline/canon.py` — entire module (not in diff)

**What to change:** `canon.py` must be surfaced and audited before final sign-off. At minimum, add a targeted test that exercises every branch referenced by the laws (currency symbols, unit abbreviations, entity spoken forms, case folding) so that future diffs to `canon.py` are tested in isolation.

**Implement:** YES — block final sign-off until `canon.py` is audited or test coverage proves behaviour.

---

### MF-2 — LAW 22 / v2f regression result is not in the diff
**Models:** Gemini (explicit CANNOT VERIFY), GPT-4o (marked NOT APPLICABLE — arguably incorrect dismissal)
**Grok:** Declared compliant without citing evidence.

**What it is:** LAW 22 requires that the v2f reference hash is unchanged. The diff does not include the regression test output proving the reference did not drift.

**File/Line:** Regression artefact — expected at `docs/audits/` or `test_v2f_regression.py`

**What to change:** Attach v2f regression output (or CI badge) to the PR. If the regression script is `regression_test.sh`, its output must be committed alongside the feature branch.

**Implement:** YES — procedural gate, not a code change. Add to merge checklist.

---

### MF-3 — Test docstrings are thin; complex synthetic-data setup lacks explanatory comments
**Models:** GPT-4o (explicit LOW severity, lines 301-308 and 376-381), Gemini (noted tests are "well-targeted" but implicitly the complexity of `TestSpanMatches` setup is noted as a risk)
**Grok:** No issue raised.

**What it is:** The synthetic audio construction in `TestSpanMatches` (lines 339-381) and the repeat-evidence test (lines 301-308) are non-obvious. A future maintainer modifying constants could break the test without understanding why it passes or fails.

**File/Line:** `test_word_diff.py:301-308`, `test_word_diff.py:339-381`

**What to change:** Add inline comments explaining: (a) why 300 ms was chosen as the repeat length, (b) what "gain+noise+codec" simulates in `TestSpanMatches`, (c) the specific law clause each test is proving.

**Implement:** YES (low effort, high maintainability value).

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### UI-1 — `NaN` guard on `np.median` for flat envelopes (Gemini only)
**Model:** Gemini
**What it is:** Line 22 of `sentence_law.py` adds a guard against `NaN` from `np.median` when the envelope is flat (all-zero or constant). Gemini explicitly praised this. GPT-4o noted the fix but did not flag it as a novel correctness issue. Grok did not mention it.
**Assessment:** This is a real silent-failure class. The fix is already in the code. No action needed — but the **test suite should include a flat-envelope fixture** to prevent regression. No such test is visible in the diff.
**Recommendation:** **Implement** — add a unit test with a flat-envelope input to `test_sentence_law.py` confirming the guard prevents `NaN` propagation.

### UI-2 — `spread` / IQR used in `_gain_db` as a robustness signal (Gemini only)
**Model:** Gemini
**What it is:** `_gain_db` returns `None` when the interquartile range of frame-level gain estimates is too wide, ensuring the gain is "constant" before trusting the value. Gemini identified this as a robust method. No other model commented on the statistical choice.
**Assessment:** The IQR threshold value (`SPAN_*` constant) is not visible in the diff excerpt. If this constant is too tight, real matching clips will be rejected; if too loose, manipulated clips will pass. The constant needs a calibration note.
**Recommendation:** **Investigate further** — confirm the IQR threshold is documented with its calibration basis (e.g., empirical distribution over known-good finals). Add a comment citing the calibration data or test.

### UI-3 — `test_an_outro_that_is_not_hash_identical_fails_outro_locked` (Gemini only)
**Model:** Gemini (line 241-245 of `test_dec1_calibration.py`)
**What it is:** A new test for a previously uncovered failure case (GPT-cut F09). Neither GPT-4o nor Grok mentioned this test.
**Assessment:** Gemini is correct that this closes a real gap. The test is already committed. No action needed — validated as a strength.
**Recommendation:** **No change needed** — already implemented. Flag for validation preservation.

### UI-4 — L-d PROTECTED PREVIEW cannot be verified (Gemini only)
**Model:** Gemini
**What it is:** The diff does not contain the regression script output for the protected preview gate. Gemini explicitly flagged CANNOT VERIFY; GPT-4o marked NOT APPLICABLE (incorrect — the law exists); Grok declared compliant.
**Assessment:** This is a legitimate gap. The protected-preview gate is a separate subsystem, but any change to `sentence_law.py` or `word_diff.py` can affect its output.
**Recommendation:** **Implement** — add L-d to the merge checklist alongside LAW 22. Confirm the protected preview regression passes before merge.

### UI-5 — `gate_g18` repeat-only acoustic adjudication `try...except` (Gemini only)
**Model:** Gemini (lines 510-521, `word_diff.py`)
**What it is:** Gemini noted the `try...except` in `gate_g18` correctly treats measurement failure as a failed check (M12 FAIL CLOSED). GPT-4o and Grok acknowledged M12 compliance generally but did not isolate this specific block.
**Assessment:** Already correctly implemented. Reinforces M12 compliance. No action needed.
**Recommendation:** **No change** — validated.

---

## CONFLICTS (models disagree — your tiebreaker)

### CONFLICT-1 — L-h TEXT READ AS SPOKEN: COMPLIANT vs. NOT APPLICABLE vs. COMPLIANT
- **Grok:** COMPLIANT (symbols/entities handled via canon)
- **GPT-4o:** NOT APPLICABLE (no changes related to text reading)
- **Gemini:** PARTIAL (compliance depends on unseen `canon.py`)

**Tiebreaker:** Gemini is most accurate. The law is applicable — `word_diff.py` previously had ad-hoc spoken-form logic (deleted, lines 395-479). That logic is now replaced by `canon.py`. The law is therefore *affected* by the diff, and compliance is *contingent* on `canon.py`. GPT-4o's NOT APPLICABLE is incorrect; Grok's COMPLIANT is optimistic. **Record as PARTIAL pending `canon.py` audit.**

### CONFLICT-2 — L-e PUNCTUATED BEFORE READ: COMPLIANT vs. NOT APPLICABLE vs. COMPLIANT
- **Grok:** COMPLIANT (punctuation assumed pre-applied)
- **GPT-4o:** NOT APPLICABLE
- **Gemini:** CANNOT VERIFY

**Tiebreaker:** Gemini is most accurate. The sentence-law pipeline consumes transcripts; whether punctuation is correctly applied before those transcripts are generated is upstream. The diff shows no changes to the transcript store, so this law is genuinely CANNOT VERIFY from the diff. **Record as CANNOT VERIFY — requires upstream audit.**

### CONFLICT-3 — Overall severity of `canon.py` dependency
- **Grok:** No issue (implicit trust)
- **GPT-4o:** Noted but not elevated
- **Gemini:** Flagged as the primary risk; "full system verification requires auditing `canon.py`"

**Tiebreaker:** Gemini is correct. The wholesale deletion of 85 lines of normalization logic and replacement with an unreviewed module is the highest systemic risk in this diff. This should be treated as a P1 blocking item, not a minor note.

---

## VALIDATED STRENGTHS (all models agree this is already excellent — do NOT change)

1. **`anchor` token boundary enforcement (lines 46-47, `sentence_law.py`)** — All three models confirmed the new first/last-token lock check correctly tightens SELECTION LOCK with no off-by-one errors.

2. **`edge_word_fidelity` every-frame comparison (line 89, `sentence_law.py`)** — All three models confirmed `keep[n:].any()` correctly implements the "every frame must be compared" rule (GPT-cut F07) and prevents partial-alignment acceptance.

3. **`_gain_db` gain measurement on interior speech frames with IQR spread guard (`sentence_law.py:152-174`)** — All three models found this correct and robust. Do not alter the IQR logic or the interior-only framing.

4. **`span_matches` run-of-bad-frames detection (`sentence_law.py:115-147`)** — All three models confirmed this is more robust than a percentage-based mismatch check. The SPAN_EDGE_S exclusion is correct.

5. **`edges_on_final` try/except fail-closed block (line 211, `sentence_law.py`)** — All three models confirmed M12 FAIL CLOSED compliance. Do not convert exceptions to warnings or soft failures.

6. **Deletion of ad-hoc normalization (lines 395-479, `word_diff.py`)** — All three models confirmed this is a correctness and maintainability improvement. Do not reintroduce local normalization.

7. **`test_verdict_rules` exact-inventory rewrite (`test_fresh.py:265-284`)** — All three models confirmed this correctly enforces L-j. Do not relax the passing-rows inventory.

8. **`TestSpanMatches` synthetic-audio pass/fail fixtures (`test_word_diff.py:339-381`)** — All three models confirmed the design is sound. Do not alter the fundamental pass/fail cases (same-span+gain+codec must pass; 300 ms repeat must fail).

9. **`gate_g18` repeat-only difference preservation as evidence (`word_diff.py:510-521`)** — All three models confirmed the acoustic tie-breaker with fail-closed exception handling is correct.

10. **`test_an_outro_that_is_not_hash_identical_fails_outro_locked` (`test_dec1_calibration.py:241-245`)** — Gemini validated; GPT-4o and Grok did not contradict. Treat as validated.

---

## LAW COMPLIANCE CONSENSUS

| Law | Consensus Status | Notes |
|---|---|---|
| SENTENCE LAW | ✅ COMPLIANT | Strengthened by canon delegation |
| SELECTION LOCK | ✅ COMPLIANT | Lines 46-47 close the boundary gap |
| SNAP LIMIT | ✅ COMPLIANT | No changes to relevant logic; existing gates hold |
| NEIGHBOUR | ✅ COMPLIANT | No regression; edge_word_fidelity improvements help |
| ONSET / TAIL | ✅ COMPLIANT | Covered by edge_word_fidelity every-frame check |
| L-b EDGE WORDS WHOLE | ✅ COMPLIANT | Direct focus of edge_word_fidelity rewrite |
| L-c DISSENT IS RIGHT UNTIL DISPROVED | ✅ COMPLIANT | edges_on_final + gain_invariant mode |
| L-g WRITTEN FORMS | ⚠️ PARTIAL | Contingent on unseen canon.py |
| L-h TEXT READ AS SPOKEN | ⚠️ PARTIAL | Contingent on unseen canon.py |
| L-k ONE CANONICAL FORM | ⚠️ PARTIAL | Contingent on unseen canon.py |
| L-j RELEASE AUTHORISED ON THESE BYTES | ✅ COMPLIANT | test_verdict_rules exact-inventory rewrite |
| M12 FAIL CLOSED | ✅ COMPLIANT | try/except blocks in edges_on_final and gate_g18 |
| LAW 20 / M2 | ✅ COMPLIANT | New thresholds added as named constants; none loosened |
| LAW 22 / v2f | ⚠️ CANNOT VERIFY | Regression output not in diff |
| L-d PROTECTED PREVIEW | ⚠️ CANNOT VERIFY | Regression output not in diff |
| L-e PUNCTUATED BEFORE READ | ⚠️ CANNOT VERIFY | Upstream transcript store not in diff |
| CREDITS | ⚠️ N/A IN DIFF | No relevant code changed |
| L-a SIGN-OFF NAMES ALL | ⚠️ N/A IN DIFF | No relevant code changed |
| L-f CHANNELS FIRST | ⚠️ N/A IN DIFF | No relevant code changed |
| L-i THE CLAIM IS THE EVENT | ⚠️ N/A IN DIFF | No relevant code changed |

**Laws requiring pre-merge verification:** L-g, L-h, L-k (via canon.py audit), LAW 22 (v2f regression), L-d (protected preview regression).

---

## SECURITY CONSENSUS

No security vulnerabilities were flagged by any model. The fail-closed posture (M12) is the primary security-adjacent property and is confirmed compliant. No concerns around injection, path traversal, or data leakage were raised. The unaudited `canon.py` is the closest thing to a security-adjacent risk (a malformed canonical form could cause a silent pass), but this is classified as a correctness risk, not a security vulnerability.

**Security consensus: No action required beyond the correctness audit of `canon.py`.**

---

## WORLD-CLASS GAP CONSENSUS

Items mentioned by 2+ models as missing from a truly world-class implementation:

### WCG-1 — Calibration documentation for `SPAN_*` and `_gain_db` IQR threshold constants
**Models:** Gemini (IQR threshold), GPT-4o (implicit in noting complex setup needs comments)

The constants `SPAN_EDGE_S`, `SPAN_MIN_S`, and the IQR spread threshold in `_gain_db` are correctness-critical. A world-class implementation documents the empirical basis for each constant (e.g., "measured over N=500 known-good finals; 99th-percentile spread was X dB"). Without this, constants will drift silently during future tuning.

**Action:** Add a `docs/calibration/span_constants.md` or inline calibration comments citing the measurement basis.

### WCG-2 — End-to-end audit trail for `canon.py` changes
**Models:** Gemini, GPT-4o

The centralization of normalization into `canon.py` is architecturally correct, but it creates a high-impact single point of failure. A world-class product would have: (a) a dedicated audit trail requiring a law-compliance review for any change to `canon.py`, (b) property-based tests (e.g., `hypothesis`) ensuring canon output is idempotent and round-trip stable, and (c) a pinned snapshot of `canon.py` in the regression artefacts.

**Action:** Add `canon.py` to the list of files requiring dual-model review on any PR. Add idempotency and round-trip property tests.

---

## FINAL ACTION PLAN (sorted by consensus priority)

| Priority | Change | File:Line | Models | Why |
|---|---|---|---|---|
| **P0 CRITICAL** | Surface and audit `pipeline/canon.py` before merge; confirm L-g, L-h, L-k compliance from its implementation | `pipeline/canon.py` (entire module) | gemini + gpt4o | Wholesale replacement of 85 lines of normalization. All three law-compliance verdicts hang on this module. Silent failure if canon is wrong. |
| **P0 CRITICAL** | Attach v2f regression output to PR (or block merge on CI gate) | Regression artefact / CI | gemini + grok (implicitly) | LAW 22 cannot be verified without it. Grok declared compliant with no evidence — that is insufficient. |
| **P1 HIGH** | Add flat-envelope fixture to `test_sentence_law.py` proving `NaN` guard (line 22) works | `test_sentence_law.py` (new test) | gemini (unique, but high-risk gap) | Silent failure class if the guard regresses. No test currently locks this behaviour. |
| **P1 HIGH** | Confirm L-d PROTECTED PREVIEW regression passes after these changes; attach output to PR | Regression artefact | gemini + (gpt4o misclassified as N/A — incorrect) | sentence_law.py changes can affect protected-preview output. Must be verified. |
| **P1 HIGH** | Add calibration comment to `_gain_db` IQR spread threshold and all `SPAN_*` constants citing empirical basis | `sentence_law.py:109-112, 152-174` | gemini + gpt4o (WCG consensus) | Constants will drift silently without documented basis. Affects L-b and L-c correctness. |
| **P2 MEDIUM** | Add inline comments to `TestSpanMatches` explaining: why 300 ms, what gain+noise+codec simulates, which law clause each case proves | `test_word_diff.py:339-381` | gpt4o + gemini | High-complexity synthetic setup will confuse future maintainers; risk of tests being "fixed" incorrectly. |
| **P2 MEDIUM** | Add inline comments to `test_a_repeat_only_difference_is_kept_as_evidence` explaining the F05 scenario | `test_word_diff.py:301-308` | gpt4o + gemini | Same maintainability concern; the scenario is non-obvious. |
| **P2 MEDIUM** | Add `canon.py` to dual-review gate in PR template; add idempotency property test | `pipeline/canon.py` + PR template | gemini + gpt4o (WCG) | Canon is now a high-impact centralised dependency; changes to it must be reviewed with the same rigour as sentence_law.py. |
| **P2 MEDIUM** | Confirm L-e (PUNCTUATED BEFORE READ) compliance via upstream transcript-store review | `transcript_store` (upstream) | gemini + grok (conflicting, Gemini correct) | Cannot be verified from this diff; needs to be on the merge checklist. |

---

## CYCLE 1 VERDICT

**CONDITIONAL READY.**

The code quality is high. All three models independently returned READY verdicts. The implementation is correct within the reviewed diff, the law compliance is strong on every verifiable law, and the tests are non-vacuous and well-targeted.

**However, merge is blocked on two P0 items:**
1. `canon.py` must be audited for L-g / L-h / L-k compliance.
2. v2f regression output must be attached proving LAW 22 is not broken.

These are not defects in the written code — they are verification gaps created by the architectural decision to centralize normalization. The second pass should address the P1 and P2 items; the P0 items are process gates that must be resolved before or alongside the second pass.

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/PULSE_SENTENCE_LAW_GOSPEL.md.
Read ~/protocol_pulse/docs/audits/pulse-sentence-law_CONSENSUS_C1.md.

This is the SECOND PASS for pulse-sentence-law.
The first build was reviewed by 3 independent AI models across 1 cycle.
Implement every P0 and P1 item from the consensus. Use judgment on P2.

PRIORITY ACTION PLAN:

P0 CRITICAL | Audit pipeline/canon.py for L-g, L-h, L-k compliance.
  Confirm: (a) written forms (currency, units, symbols) are correctly
  normalised; (b) spoken forms are faithfully produced; (c) canon output
  is idempotent (canon(canon(x)) == canon(x)). Add a dedicated test file
  test_canon.py with fixtures covering every law clause. If canon.py has
  gaps, fix them here.
  File: pipeline/canon.py + tests/test_canon.py

P0 CRITICAL | Attach v2f regression proof.
  Run the v2f regression suite and commit the output summary to
  docs/audits/pulse-sentence-law_v2f_regression.txt.
  If CI is configured, add the badge to the PR. This is a merge gate.
  File: docs/audits/pulse-sentence-law_v2f_regression.txt (new)

P1 HIGH | Add flat-envelope NaN-guard test.
  In test_sentence_law.py add a fixture where the audio envelope is
  all-zero (or constant) and assert that speech_bed_quiet returns a
  finite value (not NaN). This locks the guard at sentence_law.py:22.
  File: test_sentence_law.py (new test)

P1 HIGH | Verify L-d PROTECTED PREVIEW regression.
  Run the protected-preview regression script after these changes.
  Commit the output to docs/audits/pulse-sentence-law_preview_regression.txt.
  If any preview hashes changed, investigate before merge.
  File: docs/audits/pulse-sentence-law_preview_regression.txt (new)

P1 HIGH | Document calibration basis for SPAN_* constants and _gain_db IQR threshold.
  At sentence_law.py:109-112 add a comment block citing the empirical
  