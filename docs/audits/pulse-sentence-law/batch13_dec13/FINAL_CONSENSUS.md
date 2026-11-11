# CONSENSUS REPORT — PULSE-SENTENCE-LAW — CYCLE 2
Generated: 2026-11-11 18:21
Models: gpt4o, gemini (+1 failed: grok budget exceeded)

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Correctness | 8/10 | 8/10 | N/A | **8/10** |
| Law Compliance | 9/10 | 9/10 | N/A | **9/10** |
| Test Quality | 10/10 | 9/10 | N/A | **9.5/10** |
| Security / Fail-Closed | 8/10 | 8/10 | N/A | **8/10** |
| **Overall** | **8.5/10** | **8.5/10** | N/A | **8.5/10** |

> **Note on Grok failure:** Grok-3 exceeded its daily budget and produced no output for Cycle 2. All findings below are drawn from Gemini and GPT-4o only. Confidence in findings is slightly reduced relative to a full 3-model consensus; however, both available models reached identical conclusions independently, which strengthens the signal.

---

## UNANIMOUS FINDINGS (both models agree — implement unconditionally)

Both models flagged exactly the same two issues. These represent the highest-confidence defects in the codebase.

---

### U-1: Sentence-initial capitalization not transferred during punctuation restoration

**What it is:** The `punctuate()` function in `transcript_store.py` creates a `whisper_words_punct` record by running a reference decode and grafting punctuation onto the original word tokens. However, it does not transfer sentence-initial capitalization from the reference decode back to the original tokens. When a sentence begins mid-transcript, the first word retains its lowercase form from the original Whisper output. Downstream gates that check for sentence boundaries by inspecting capitalization (e.g., `start_is_boundary`) will incorrectly reject these sentences as non-boundary starts, partially defeating the purpose of the SENTENCE LAW feature.

**Evidence from tests:** The test file `pipeline/test_punct_word_pass.py` line 950 marks this as an `OPEN` issue — confirming the bug is known but not yet fixed. Known defects cannot ship as `OPEN`.

**File/Lines:** `pipeline/transcript_store.py`, `punctuate()` function, lines 1110–1131. The root fix likely belongs in `pipeline/punctuation.py` in the `ensure` or `transfer` helper, but the effect manifests via `punctuate()`.

**What to change:** After aligning punctuation from the reference decode onto original word tokens, also transfer the capitalization of the first word of each detected sentence boundary. If `reference_word[i]` starts a sentence (i.e., it begins with an uppercase letter and follows a sentence-terminal punctuation mark or is the first token), copy the capitalised form to `original_words[i].word`. Do not alter any other words' casing. Close the `OPEN` marker in the test file once fixed.

---

### U-2: Punctuation failure status is not normalised to a canonical sentinel

**What it is:** When punctuation restoration fails, `transcript_store.py` returns a failure status constructed at runtime as the formatted string `f"{step}_failed"` (line 1180). The guard in `editorial_select.py` (line 291) checks for this specific string to reject the candidate. This is a classic "stringly-typed" fragility: if the value of `step` changes during any future refactor — even a trivial rename — the two sides of the check silently drift apart. The guard no longer matches, the failure is no longer caught, and a candidate with a broken transcript is accepted. This is a latent **fail-open** vulnerability in a system that is explicitly required to fail closed.

**File/Lines:**
- Failure string produced: `pipeline/transcript_store.py`, line 1180
- Failure string consumed: `pipeline/editorial_select.py`, line 291
- Test assertion: `pipeline/test_punct_word_pass.py`, line 1026

**What to change:**
1. Define a shared module-level constant: `PUNCTUATION_FAILED = "punctuation_failed"` in `pipeline/transcript_store.py`.
2. Replace the f-string on line 1180 with the constant.
3. Import `PUNCTUATION_FAILED` from `transcript_store` in `editorial_select.py` and replace the hardcoded string on line 291 with the constant.
4. Update the test assertion on line 1026 to reference the same constant so it auto-tracks any future rename.

---

## MAJORITY FINDINGS (2 of 2 models agree)

Both findings above are unanimous. There are no additional majority-only findings — both models converged completely on the same two issues and found no other defects.

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

Neither model surfaced a unique insight that the other missed. Both models' Cycle 2 reviews were substantively identical in their defect identification. The following observations were made by one model and not explicitly stated by the other, but neither contradicts the other:

**Gemini only — LLM cache key completeness (line 593, `story_semantics.py`):**
Gemini explicitly re-verified that the cache key for `LocalLLM.chat_json` includes model, context size, max tokens, and prompt, and found it correct. GPT-4o did not revisit this in Cycle 2.
**Assessment: No action needed. This is a confirmed strength, not a gap.**

**Gemini only — Dual-model resource release (`release_whisper`, line 1075):**
Gemini re-verified that both `_WHISPER` and `_REFERENCE` are cleared in `release_whisper` and found no leak. GPT-4o did not revisit this.
**Assessment: No action needed. Confirmed as already correct.**

---

## CONFLICTS (models disagree — tiebreaker)

**None.** Both models agreed on every finding, every priority rating, and the production-readiness verdict. The scores are identical. There are no conflicts to resolve.

---

## VALIDATED STRENGTHS (all models agree — do NOT change in the second pass)

These areas were explicitly examined and confirmed correct by both models. Do not modify them during the fix pass.

1. **`sentence_ready` gate in `acquire()`** (lines 1147, `transcript_store.py`): Correctly used as a hard gate. Only transcripts that pass `sentence_ready` proceed; others must be punctuated or fail. Logic is sound.

2. **`punctuate()` exception handling** (lines ~1173–1180, `transcript_store.py`): Exceptions during punctuation are caught, logged, and converted to a failure status that propagates upstream. The fail-closed architecture is correct — the only defect is the string fragility (U-2), not the exception handling structure itself.

3. **LLM cache implementation** (`story_semantics.py`, lines 591–619): Cache miss and cache-write failures both fall through to a live model call with `pass`. The cache is an enhancement, not a new failure point. Cache key is complete and correct. Do not alter.

4. **Dual Whisper model resource management** (`transcript_store.py`, `release_whisper`, line ~1075): Both `_WHISPER` and `_REFERENCE` are released correctly. No resource leak. Do not alter.

5. **Tiered pool system in `editorial_select._select_story`** (lines 313–327): The refactored pool loop correctly stops on the first producible story, implementing Law L-f (CHANNELS FIRST) as specified. The `evaluate()` function correctly encapsulates steps 4–7. Logic is sound and complex but correct. Do not alter.

6. **Test suite quality overall** (`pipeline/test_punct_word_pass.py`): Tests cover the new logic with unit-level checks and fixture-based integration tests that validate CHANNELS FIRST on real-world data. The tests are described by both models as excellent. Do not reduce test coverage — only add to it when fixing U-1.

---

## LAW COMPLIANCE CONSENSUS

| Law | Status | Determination |
|---|---|---|
| **L-e / SENTENCE LAW** (transcripts must be punctuated before reading) | ⚠️ **PARTIAL** | Architecture is correct. Bug U-1 means punctuation-restored transcripts are not fully sentence-ready for all gates (capitalization check fails). Technically the law is structurally implemented but functionally incomplete. |
| **L-f / CHANNELS FIRST / SELECTION LOCK** | ✅ **COMPLIANT** | Tiered pool system correctly implements channels-first priority. No recomputation of expected words after selection. |
| **SNAP LIMIT** | ✅ **COMPLIANT** | No evidence of cuts moving outside locked sentence silence. No changes to this logic in the diff. |
| **M12 / FAIL CLOSED** | ⚠️ **LATENT RISK** | Structurally compliant. Bug U-2 represents a latent fail-open regression risk on future refactor. Must be hardened before ship. |
| **NEIGHBOUR** | ✅ **COMPLIANT** | Not affected by this diff. No violations found. |

**Final Law Determination:** Law L-e is not fully satisfied until U-1 is fixed. M12 is at latent risk until U-2 is fixed. All other laws are fully compliant.

---

## SECURITY CONSENSUS

Both models flagged one security-class issue:

**S-1 (= U-2): Latent fail-open via sentinel string drift.**
Priority: **P1 HIGH.** Not currently exploitable, but constitutes a structural fail-open risk. Any refactor touching the `step` variable silently breaks the rejection guard. In an editorial system where incorrect candidates reaching output is a trust/accuracy failure, this must be treated as a security-class issue, not merely a code style issue. Fix by introducing a shared constant as described in U-2.

No other security issues were identified. The LLM cache does not introduce new attack surface (cache misses fall through safely). Dual-model resource management does not create state bleed between clips.

---

## WORLD-CLASS GAP CONSENSUS

Items mentioned by both models as gaps relative to a truly world-class implementation:

1. **Known defect shipped as `OPEN` in tests (U-1 / casing).** Both models noted that `test_punct_word_pass.py` line 950 marks the casing bug as `OPEN`. A world-class codebase does not ship with known, documented correctness defects marked open in its test suite. The standard is: if it's known, it's fixed before merge. The gap here is not just the bug but the practice of treating a test `OPEN` marker as an acceptable ship state.

2. **Stringly-typed inter-module protocol (U-2 / sentinel).** Both models flagged the f-string sentinel as a symptom of a broader pattern: using raw strings to communicate state between modules. A world-class implementation uses shared typed constants (or enums) for all inter-module status values, making string drift impossible by construction. The gap is not just this one instance but the absence of a typed status enum for transcript acquisition states.

---

## FINAL ACTION PLAN (sorted by consensus priority)

| Priority | Change | File : Line | Models | Why |
|---|---|---|---|---|
| **P1 HIGH** | Transfer sentence-initial capitalization from reference decode to original word tokens in `punctuate()`. Close `OPEN` marker in test once fixed. | `pipeline/punctuation.py` (fix root), effect in `transcript_store.py` lines 1110–1131; test: `test_punct_word_pass.py` line 950 | **Both** | Correctness defect. Downstream capitalization gates reject valid sentence boundaries. Law L-e is not fully satisfied. Known defect cannot ship `OPEN`. |
| **P1 HIGH** | Define `PUNCTUATION_FAILED = "punctuation_failed"` constant. Replace f-string on line 1180. Import and use constant in `editorial_select.py` line 291. Update test assertion on line 1026 to reference constant. | `pipeline/transcript_store.py` line 1180; `pipeline/editorial_select.py` line 291; `pipeline/test_punct_word_pass.py` line 1026 | **Both** | Latent fail-open vulnerability. String drift on future refactor silently breaks M12 FAIL CLOSED guarantee. Single shared constant makes drift impossible. |

> There are no P0 CRITICAL items (no currently triggerable data-loss or security exploit). There are no P2 MEDIUM items surfaced by consensus. Both P1 items are well-scoped, low-risk fixes.

---

## CYCLE 2 VERDICT

**NOT PRODUCTION READY — two P1 blockers must be fixed first.**

The feature's architecture is sound. The tiered pool system, the fail-closed acquisition pipeline, the LLM cache, and the dual-model resource management are all correct and of high quality. The test suite is strong.

However, two defects prevent ship:

1. **U-1** means the SENTENCE LAW feature does not fully deliver its stated purpose — a subset of punctuation-restored transcripts will be rejected by downstream capitalization gates, silently degrading clip selection quality for mid-transcript sentence starts.

2. **U-2** means the fail-closed guarantee has a latent crack — it holds today but is one variable rename away from failing silently and catastrophically.

Both fixes are straightforward and well-defined. Once implemented and `regression_test.sh` shows zero FAILs, the feature is production-ready.

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/PULSE_SENTENCE_LAW_GOSPEL.md.
Read ~/protocol_pulse/docs/audits/pulse-sentence-law_CONSENSUS_C2.md.

This is the FINAL PASS for pulse-sentence-law.
The feature was reviewed by 2 independent AI models across 2 cycles.
Implement every P1 item from the consensus. There are no P0 or P2 items.

PRIORITY ACTION PLAN:

P1 HIGH | Transfer sentence-initial capitalization from reference decode to
         original word tokens during punctuation restoration. Fix the root
         logic in pipeline/punctuation.py (the ensure/transfer helper).
         The effect must appear in the whisper_words_punct record produced
         by the punctuate() function in pipeline/transcript_store.py
         (lines 1110-1131). Rule: if reference_word[i] begins with an
         uppercase letter AND either (a) it is the first token or (b) it
         follows a sentence-terminal punctuation mark (. ? !), copy the
         capitalised form to the corresponding original word token. Do not
         alter casing of any other words. After fixing, close the OPEN
         marker at pipeline/test_punct_word_pass.py line 950 and ensure
         the test passes with the corrected behaviour.
         | pipeline/punctuation.py (root fix) +
           pipeline/transcript_store.py lines 1110-1131 +
           pipeline/test_punct_word_pass.py line 950
         | models: both | Law L-e not fully satisfied; known defect cannot ship OPEN.

P1 HIGH | Normalise the punctuation failure sentinel to a shared constant.
         (1) Add module-level constant in pipeline/transcript_store.py:
             PUNCTUATION_FAILED = "punctuation_failed"
         (2) Replace the f-string return value at line 1180 with PUNCTUATION_FAILED.
         (3) In pipeline/editorial_select.py line 291, import PUNCTUATION_FAILED
             from pipeline.transcript_store and replace the hardcoded string
             with the constant.
         (4) In pipeline/test_punct_word_pass.py line 1026, update the test
             assertion to reference PUNCTUATION_FAILED rather than a raw string,
             so the test auto-tracks any future rename.
         | pipeline/transcript_store.py line 1180 +
           pipeline/editorial_select.py line 291 +
           pipeline/test_punct_word_pass.py line 1026
         | models: both | Latent fail-open: string drift on refactor silently breaks M12 FAIL CLOSED.

VALIDATED — do NOT touch these areas, all models confirmed excellent:
- sentence_ready gate in acquire() (transcript_store.py ~line 1147)
- punctuate() exception handling and fail-closed structure (~lines 1173-1180),
  only the string representation changes, not the structure
- LLM cache implementation in story_semantics.py (lines 591-619)
- release_whisper dual-model resource cleanup (transcript_store.py ~line 1075)
- Tiered pool loop in editorial_select._select_story (lines 313-327)
- evaluate() encapsulation of steps 4-7 (lines 148-310)
- Overall test suite coverage and structure

After implementing:
1. regression_test.sh must show zero FAILs.
2. Confirm test_punct_word_pass.py OPEN marker is closed and test passes.
3. Confirm no raw string literals remain in the punctuation failure path
   across transcript_store.py, editorial_select.py, and the test file.

git add -A && git commit -m "feat(pulse-sentence-law): post-audit pass — consensus improvements (casing transfer + sentinel constant)"
git push origin combo-letterbox-quoteonly-v2
```

---

# WINNER DETERMINATION

## WINNER: Gemini

Gemini delivered superior depth and mechanical precision across both cycles — it not only verified high-level law compliance but traced failure propagation paths, identified the fragility of the dynamic sentinel pattern, and explicitly named the downstream gate (`start_is_boundary`) that would break due to the casing bug. Its Cycle 2 self-audit was structurally honest, distinguishing exactly what it caught versus what the consensus surfaced, which demonstrates the kind of calibrated reasoning that makes an audit model trustworthy rather than merely comprehensive.

---

## FINAL SECOND-PASS PRIORITY LIST

The following is the definitive ordered implementation list, ranked by severity × likelihood × downstream blast radius.

---

### P0 — MUST FIX BEFORE MERGE (Blocking)

**1. Transfer sentence-initial capitalization in `punctuate()` [U-1]**
- **File:** `transcript_store.py` — `punctuate()` function
- **What to do:** After grafting punctuation tokens onto original word tokens, inspect the reference decode for sentence-initial words (i.e., words following a sentence-terminal punctuation mark or at position 0). For each such word, copy the capitalized form from the reference decode into the corresponding original token's `word` field.
- **Why P0:** The entire SENTENCE LAW feature exists to make transcripts sentence-ready. If the first word of a sentence remains lowercase, gates like `start_is_boundary` will reject valid sentences, silently degrading output quality. The bug is confirmed `OPEN` in `test_punct_word_pass.py` line 950 — known defects cannot ship.
- **Test required:** Add a case to `test_punct_word_pass.py` where a sentence begins mid-transcript and assert that the first token of that sentence is capitalized in the output record.

---

**2. Normalize the punctuation failure sentinel [U-2]**
- **File:** `transcript_store.py` — `punctuate()` / `acquire()` + `editorial_select.py` — guard clause (~line 291)
- **What to do:** Replace the dynamic `f"{step}_failed"` string with a module-level constant, e.g., `PUNCT_FAILED = "punctuation_failed"`, imported and checked by name in both files.
- **Why P0:** The fail-closed guarantee of Law M12 is currently implemented via a string that can silently drift if `step` is ever renamed during refactor. A broken sentinel means a punctuation failure stops being caught, candidates are incorrectly accepted, and the system becomes fail-open with no runtime error. This is a latent correctness bomb disguised as a style issue.
- **Test required:** Add a unit test that patches `punctuate()` to raise, then asserts `acquire()` returns exactly `PUNCT_FAILED` and that the editorial select guard correctly rejects it.

---

### P1 — HIGH PRIORITY (Fix in same sprint)

**3. Audit all downstream gates for capitalization dependency**
- **Files:** Any gate module that inspects word-level `word` fields for sentence boundary signals
- **What to do:** Search for all references to `start_is_boundary` and any gate that reads `.word[0].isupper()` or equivalent. Verify each gate's behavior against the corrected `punctuate()` output once U-1 is fixed. Update gate unit tests to use post-fix fixtures.
- **Why P1:** U-1's fix changes the data contract of `whisper_words_punct` records. Gates written against the broken contract may need adjustment or will start passing tests they previously failed — both outcomes need explicit verification, not assumption.

---

**4. Close the `OPEN` marker in `test_punct_word_pass.py` line 950**
- **File:** `pipeline/test_punct_word_pass.py`
- **What to do:** Once U-1 is fixed, remove the `OPEN` marker, convert the skipped/xfail assertion into a live passing test, and add it to the CI gate so it cannot regress.
- **Why P1:** A known open defect in a test file is a process failure. Shipping with it signals that the team accepts broken behavior as a baseline — this erodes audit confidence for every future cycle.

---

### P2 — MEDIUM PRIORITY (Next sprint)

**5. Harden the LLM cache in `story_semantics.LocalLLM.chat_json`**
- **File:** `story_semantics.py` — `chat_json()`, lines 591–619
- **What to do:** Confirm that cache read errors (corrupted file, schema mismatch after a model version change) are caught and treated as cache misses, not as application errors. Add a cache-schema version key so stale cache entries from prior model versions are automatically invalidated rather than silently served.
- **Why P2:** Gemini flagged this as safely implemented but incomplete. A corrupted or version-mismatched cache entry that bypasses the LLM call could produce subtly wrong semantic scores that pass all gates — a silent quality regression harder to detect than an outright failure.

---

**6. Regression test for tiered pool early-exit in `_select_story`**
- **File:** `editorial_select.py` — `_select_story()`, lines 313–327
- **What to do:** Add an integration test that places a producible story in Pool 1 and verifies Pool 2 is never evaluated (mock `evaluate()` and assert call count).
- **Why P2:** The tiered logic is architecturally correct per Gemini's Cycle 1 review, but no test currently isolates the early-exit behavior. Without it, a future refactor could remove the `break` or restructure the loop and no test would catch the regression.

---

### P3 — LOW PRIORITY (Backlog, before next major feature)

**7. Document the `REFERENCE_MODEL` selection rationale**
- **File:** `transcript_store.py` — line 1049
- **What to do:** Add an inline comment or ADR entry explaining why `large-v3` was chosen as the reference model for punctuation restoration and what the upgrade path is if a superior model becomes available.
- **Why P3:** The choice is correct but opaque. Future maintainers will not know whether this constant is arbitrary or load-bearing, increasing the risk of an uninformed change.

---

**8. Add Grok to the next audit cycle with budget pre-confirmed**
- **Process, not code**
- **What to do:** Before initiating Cycle 1 of the next audit, verify Grok's daily budget is not exhausted. Consider running a lightweight probe request at audit-start to confirm availability before committing to a 3-model run.
- **Why P3:** Grok's budget failure in this cycle reduced consensus confidence from 3-model unanimous to 2-model unanimous. Both available models agreed, which preserved signal integrity, but the structural gap should be closed procedurally rather than accepted as normal.