# CONSENSUS REPORT — PULSE-SENTENCE-LAW — CYCLE 2
Generated: 2026-11-11 19:06
Models: gpt4o, grok, gemini

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Correctness (`_g3b_words` logic) | PASS | PASS | PASS | **PASS** |
| Correctness (gate integration — `last_word`) | PASS | PASS | PASS | **PASS** |
| Correctness (gate integration — `next_source_word`) | **FAIL** | PASS | PASS | **FAIL** |
| Fail-closed / no silent exceptions | COMPLIANT | COMPLIANT | COMPLIANT | **COMPLIANT** |
| L-g WRITTEN FORMS | PARTIAL | COMPLIANT | COMPLIANT | **PARTIAL** |
| SENTENCE LAW | COMPLIANT | COMPLIANT | COMPLIANT | **COMPLIANT** |
| SELECTION LOCK | COMPLIANT | COMPLIANT | COMPLIANT | **COMPLIANT** |
| SNAP LIMIT | COMPLIANT | COMPLIANT | COMPLIANT | **COMPLIANT** |
| LAW 22 (v2f protected render) | COMPLIANT | COMPLIANT | COMPLIANT | **COMPLIANT** |
| M12 FAIL CLOSED | COMPLIANT | COMPLIANT | COMPLIANT | **COMPLIANT** |
| Unit test (`test_symbols_are_read_as_the_spoken_words`) | PASS | PASS | PASS | **PASS** |
| Integration test (`test_v2f_vertical_dollars_tail_passes`) | PASS | PASS | PASS | **PASS** |
| Must-fail fixture preserved | PASS | PASS | PASS | **PASS** |
| Test coverage — `next_source_word` symbol leak | **FAIL** | PASS | PASS | **FAIL** |
| Overall Verdict | **NOT READY** | READY (w/ conditions) | READY | **NOT READY** |

---

## UNANIMOUS FINDINGS (all 3 models agree — implement unconditionally)

**None.** There are no defects that all three models flagged simultaneously. The two models that reached a READY verdict (GPT-4o, Grok) missed the `next_source_word` bug that Gemini alone caught. The lack of unanimous findings does not mean the code is clean — see Unique Insights below.

---

## MAJORITY FINDINGS (2 of 3 models agree)

### MAJ-1: Dollar-scale word sequencing is correctly implemented
- **Models:** GPT-4o, Grok, Gemini (unanimous on this point)
- **Finding:** The deferred-`dollars` flag logic for phrases like `"$40 trillion"` → `['40', 'trillion', 'dollars']` is correct. All three models validated this independently.
- **Action:** No change needed. Confirmed correct.

### MAJ-2: Existing test suite already covers the `$40 trillion` case
- **Models:** Grok and Gemini agree; GPT-4o incorrectly recommended adding a test
- **Finding:** `test_symbols_are_read_as_the_spoken_words` line 28 already asserts `_g3b_words("above $40 trillion") == ["above", "40", "trillion", "dollars"]`. GPT-4o's P2 recommendation to add this test is redundant.
- **Action:** No test addition needed. GPT-4o was wrong here.

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### UNIQUE-1 (Gemini): Incomplete Leak Detection for `next_source_word` — IMPLEMENT
- **File:** `segment_v1/qa_gates.py`
- **Lines:** 97–101
- **Finding:** When `next_source_word` contains a symbol that expands to multiple tokens (e.g., `"50%"` → `['50', 'percent']`), the gate discards all tokens after the first. The leak check then only searches for `'50'` in the tail audio, completely ignoring `'percent'`. A clip where only `"percent"` leaked into the tail would receive a false PASS.
- **Why this matters:** This is a silent quality gate failure — the most dangerous failure mode in a QA system. The gate's entire purpose is to catch leaked words. Making it structurally blind to half the leaked tokens from any symbol-expanded `next_source_word` directly contradicts L-g and M12's spirit.
- **Assessment:** **IMPLEMENT.** This is a real, traceable, logical bug with a clear and narrow fix. It is not speculative. The fix does not require modifying the helper function — only how its output is consumed in `gate_g3b`. Gemini's recommended fix (rename to `next_words`, check for any match against the list) is correct.
- **Required companion:** A new must-fail test where `next_source_word` is `"50%"`, the tail audio contains `"percent"` but not `"50"`, and the gate must return FAIL.

### UNIQUE-2 (Gemini): Decimal number robustness (`$1.66`)
- **Finding:** The shift from `replace(".", " ")` to `.rstrip(".")` fixes a latent bug where `$1.66` would tokenize to `['1', '66']` instead of the correct `['1.66']`.
- **Assessment:** **ALREADY FIXED** in the diff. This is a validation of an existing improvement, not an action item.

---

## CONFLICTS (models disagree — tiebreaker)

### CONFLICT-1: Is the code production-ready?
- **GPT-4o:** Yes, with a P2 condition (add a redundant test)
- **Grok:** Yes, unconditionally
- **Gemini:** No — P1 blocker in `next_source_word` leak detection
- **Tiebreaker verdict: Gemini is correct.** GPT-4o and Grok accepted the gate integration as correct without tracing how `nw[0]` discards subsequent tokens. Gemini's trace is mechanically verifiable: `_g3b_words("50%")` returns `['50', 'percent']`; `nw[0]` is `'50'`; `'percent'` is never checked. This is a falsifiable bug, not an opinion.

### CONFLICT-2: Should a test be added for `$40 trillion`?
- **GPT-4o:** Yes (P2 recommendation)
- **Grok:** No — already covered on line 28
- **Gemini:** No — already covered on line 28
- **Tiebreaker verdict: Grok and Gemini are correct.** GPT-4o failed to verify the existing test suite before recommending the addition. The test exists. No action needed.

---

## VALIDATED STRENGTHS (all models agree — do NOT change)

1. **`_g3b_words` helper function logic** — The tokenizer correctly handles `$`, `%`, commas, trailing periods, deferred `dollars` flag for scale words, and decimal numbers. All three models validated this.
2. **Symmetric application to `last_word`** — `_g3b_words` is correctly applied to both the EDL's expected `last_word` and the heard audio words, ensuring a fair comparison for tail detection.
3. **Fail-closed behavior on missing data** — `ew[-1] if ew else ""` correctly produces an empty string (skipping the check) when a segment has no `last_word`. No crash, no false pass.
4. **`test_symbols_are_read_as_the_spoken_words`** — Correct, non-vacuous, directly tests all symbol expansions required by L-g including the `$40 trillion` edge case.
5. **`test_v2f_vertical_dollars_tail_passes`** — Correctly runs the real v2f reference through `gate_g3b` and validates both the gate result and `edl_last` extraction.
6. **Must-fail fixture (Natalie tail)** — Untouched and confirmed preserved by all three models.

---

## LAW COMPLIANCE CONSENSUS

| Law | Status | Notes |
|---|---|---|
| L-g WRITTEN FORMS | **PARTIAL** | Correctly applied to `last_word`; incompletely applied to `next_source_word` (only first token used) |
| SENTENCE LAW | COMPLIANT | No sentence boundary logic altered |
| SELECTION LOCK | COMPLIANT | No lock-bypass paths introduced |
| SNAP LIMIT | COMPLIANT | No cut movement logic altered |
| NEIGHBOUR | COMPLIANT | No neighbour-word handling altered |
| ONSET/TAIL | COMPLIANT | Tail detection logic structurally intact; symbol expansion bug is in next-word leak only |
| CREDITS | COMPLIANT | Unaffected |
| L-a SIGN-OFF NAMES ALL | COMPLIANT | Unaffected |
| L-b EDGE WORDS WHOLE | COMPLIANT | Unaffected |
| L-c DISSENT IS RIGHT UNTIL DISPROVED | COMPLIANT | Unaffected |
| L-d PROTECTED PREVIEW | COMPLIANT | v2f reference path unaltered |
| L-e PUNCTUATED BEFORE READ | COMPLIANT | Punctuation stripping is correctly applied before tokenizing |
| L-f CHANNELS FIRST | COMPLIANT | Unaffected |
| LAW 20 / M2 | COMPLIANT | Gate thresholds unaltered |
| M12 FAIL CLOSED | COMPLIANT (formal) | The bug produces a false pass, not a crash on missing data; M12 is technically met but its spirit is violated |
| LAW 22 | COMPLIANT | v2f protected render path unaltered |

**Final determination:** One law is incompletely implemented — L-g is correctly enforced for `last_word` matching but only partially enforced for `next_source_word` leak detection.

---

## SECURITY CONSENSUS

No security issues were identified by any model. The changes are entirely within a text-tokenization and string-matching domain with no I/O, no network calls, no authentication logic, and no dynamic code execution paths. No action needed.

---

## WORLD-CLASS GAP CONSENSUS

Items mentioned by 2+ models:

1. **Symbol-expanded `next_source_word` coverage in leak detection (Gemini + implicit in GPT-4o's concern about edge cases):** A world-class quality gate checks every spoken token of every word boundary, not just the first. The current implementation is structurally incomplete for any symbol that expands to multiple spoken words at a clip's tail boundary.

2. **Test coverage for the false-pass failure mode (Gemini + GPT-4o both raised test coverage concerns, though for different cases):** A world-class test suite includes at least one must-fail fixture for each gate check path. The `next_source_word` symbol-expansion path currently has no must-fail test. Any refactor could silently introduce a regression with no red test to catch it.

---

## FINAL ACTION PLAN (sorted by consensus priority)

| Priority | Change | File:Line | Models | Why |
|---|---|---|---|---|
| **P1 HIGH** | Fix `next_source_word` leak detection to consume all tokens from `_g3b_words`, not just `nw[0]`. Rename to `next_words = nw`. Update the conditional and downstream check to match against any word in the list. | `segment_v1/qa_gates.py:97–101` | Gemini (unique, confirmed correct) | Silent false-pass bug: a clip where only the second spoken token of a symbol-expanded next word leaks into the tail will incorrectly pass the gate |
| **P1 HIGH** | Add a must-fail test: `next_source_word = "50%"`, tail audio contains `"percent"` but not `"50"` — gate must return FAIL | `pipeline/test_g3b_majority.py` | Gemini (unique, confirmed correct) | No test currently catches a regression in the `next_source_word` multi-token path; without this, the P1 fix above has no red-green verification |
| ~~P2 MEDIUM~~ | ~~Add test for `$40 trillion`~~ | — | GPT-4o only | **SKIP** — test already exists on line 28; GPT-4o did not verify before recommending |

---

## CYCLE 2 VERDICT

**NOT PRODUCTION READY.**

The single blocker is a silent false-pass bug in `gate_g3b`'s `next_source_word` leak detection. When the first word of the next sentence is a symbol that expands to multiple spoken tokens (e.g., `"50%"` → `['50', 'percent']`), only the first token is checked against the tail audio. If only the second token leaked, the gate returns PASS incorrectly. This violates the gate's core function and partially violates L-g. The fix is narrow, well-defined, and requires a companion must-fail test. Everything else in this diff is correct and should not be touched.

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/PULSE_SENTENCE_LAW_GOSPEL.md.
Read ~/protocol_pulse/docs/audits/pulse-sentence-law_CONSENSUS_C2.md.

This is the FINAL PASS for pulse-sentence-law.
The first build was reviewed by 3 independent AI models across 2 cycles.
Implement every P0 and P1 item from the consensus. Skip all P2 items.

PRIORITY ACTION PLAN:

P1 HIGH | Fix next_source_word leak detection in gate_g3b to consume ALL
        | tokens produced by _g3b_words, not just nw[0].
        | Replace:
        |   nw = _g3b_words(edl_entry.get("next_source_word", "") or "")
        |   next_word = nw[0] if nw else ""
        | With:
        |   next_words = _g3b_words(edl_entry.get("next_source_word", "") or "")
        | Update the downstream conditional and leak check to test whether
        | ANY word in next_words appears in the tail audio (not just a
        | single next_word string).
        | File: segment_v1/qa_gates.py lines 97-101

P1 HIGH | Add a must-fail test to the existing test file.
        | Scenario: next_source_word = "50%", tail audio transcription
        | contains "percent" but NOT "50". Assert gate_g3b returns FAIL.
        | This test must be RED before the fix and GREEN after.
        | File: pipeline/test_g3b_majority.py

VALIDATED (do NOT touch — all 3 models confirmed excellent):
- _g3b_words helper function logic (dollar, percent, comma, period, decimal handling)
- Symmetric application of _g3b_words to last_word in gate_g3b
- Fail-closed behavior: ew[-1] if ew else "" on missing last_word
- test_symbols_are_read_as_the_spoken_words (all assertions including $40 trillion)
- test_v2f_vertical_dollars_tail_passes
- Must-fail fixture for Natalie tail (do not modify)

Do NOT add a test for "$40 trillion" — it already exists on line 28.

After implementing: regression_test.sh must show zero FAILs.
The new must-fail test must be RED before your fix and GREEN after —
confirm this in your implementation notes.
git add -A && git commit -m "feat(pulse-sentence-law): post-audit pass — fix next_source_word multi-token leak detection"
git push origin combo-letterbox-quoteonly-v2
```

---

# WINNER DETERMINATION

WINNER: **Gemini**

Gemini delivered the only analysis that caught a genuine defect (the `next_source_word` symbol-leak bug and the corresponding missing test coverage) that neither GPT-4o nor Grok identified, directly driving the consensus NOT READY verdict. It also provided the deepest mechanical trace of the dollar-scale state machine and the decimal-handling regression fix — insights the other models either borrowed from Gemini in Cycle 2 or missed entirely.

---

## FINAL SECOND-PASS PRIORITY LIST

**P0 — Blocking (must fix before merge)**

1. **Fix `next_source_word` symbol leak in `gate_g3b`.**
   The `_g3b_words` normalisation is applied to `edl_last` (last-word path) but the consensus FAIL on `next_source_word` gate integration means the next-word comparison path is either not calling `_g3b_words` symmetrically or is calling it on the wrong field. Confirm line 97 reads `nw = _g3b_words(edl_entry.get("next_source_word", "") or "")` and that the heard-audio side of the same comparison is also passed through `_g3b_words` before the equality check.

2. **Add a must-pass test for `next_source_word` symbol expansion.**
   Write a fixture where `next_source_word` contains a `$` or `%` symbol, run it through `gate_g3b`, and assert the gate returns PASS (not FAIL due to a raw-symbol vs spoken-word mismatch). Without this, the coverage gap that produced the consensus FAIL remains undetected by the test suite.

**P1 — High priority (fix in same PR if possible)**

3. **Add a test for the `$40 trillion` deferred-dollars pattern.**
   The state-machine path that defers appending "dollars" until after a scale word is the most complex branch in `_g3b_words`. Although Grok argued line 28 of the existing test covers it, the consensus PARTIAL on L-g compliance suggests the fixture should be explicit and self-documenting: assert `_g3b_words("$40 trillion") == ["40", "trillion", "dollars"]` as a named case.

4. **Add a test for decimal preservation (`$1.66` → `["1.66", "dollars"]`).**
   The switch from `replace(".", " ")` to `.rstrip(".")` fixed a latent tokenisation bug. That fix has no dedicated regression test. Add one so the bug cannot silently re-emerge.

**P2 — Low priority (track but do not block merge)**

5. **Harden L-g compliance documentation.**
   The consensus returned PARTIAL on L-g. Add a comment in `_g3b_words` that explicitly cross-references L-g and lists every symbol class the function is contractually required to handle, so future contributors know the expansion table is law-defined, not discretionary.

6. **Confirm no other gate functions call a raw-string comparison on EDL word fields.**
   The `next_source_word` leak pattern could exist in analogous gates (`gate_g3a`, `gate_g3c` if present). A one-pass grep for `.get("next_source_word"` and `.get("last_word"` outside of `gate_g3b` should confirm no other site bypasses `_g3b_words`.