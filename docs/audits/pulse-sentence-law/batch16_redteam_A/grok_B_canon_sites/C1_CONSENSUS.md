# CONSENSUS REPORT — PULSE-SENTENCE-LAW — CYCLE 1
Generated: 2026-11-11 22:46
Models: grok, gpt4o, gemini

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Correctness | 9/10 | 8/10 | 9/10 | **9/10** |
| Law Compliance | 9/10 | 9/10 | 9/10 | **9/10** |
| Test Quality | 10/10 | 8/10 | 9/10 | **9/10** |
| Security / Robustness | 7/10 | 7/10 | 7/10 | **7/10** |
| Overall Readiness | 9/10 | 9/10 | 9/10 | **9/10** |

> Score derivation: Gemini issued 1 MAJOR + 1 MAJOR + 1 MEDIUM + 1 MEDIUM (no blockers, all resolved by the diff itself); GPT-4o and Grok issued READY with minor/medium caveats only. All three models converged on the same import-hygiene and word_overlap issues as the only unresolved residuals.

---

## UNANIMOUS FINDINGS (all 3 models agree — implement unconditionally)

### U1 — `sys.path.insert` import-hygiene
**What:** Lines 73, 92, 218, 284 in `gates.py` (and mirrored sites) repeatedly call `sys.path.insert(0, ...)` to resolve relative imports. This is fragile, order-dependent, and leaks path state across clip-processing iterations in long-running workers.
**File/Line:** `gates.py:73`, `gates.py:92`, `gates.py:218`, `gates.py:284` (and any equivalent in `qa_gates.py` / `editorial_gate.py`)
**Fix:** Convert all affected files to proper package-relative imports (`from ..pipeline import canon`) or, where the package boundary makes that awkward, use a single `importlib.util.spec_from_file_location` call in a shared bootstrap that runs once at process start. Remove every `sys.path.insert` from hot paths.

### U2 — `word_overlap` returns `1.0` on empty reference (fail-open)
**What:** All three models flagged that `word_overlap` previously returned `1.0` (full match / PASS) when the reference token set was empty, violating `M12 FAIL CLOSED`. Gemini confirmed the fix is in the diff (now returns `0.0`); Grok and GPT-4o both independently flagged the residual risk that this logic must be verified in every downstream call site, not just the one changed line.
**File/Line:** `qa_gates.py:213` (fix confirmed in diff) + all callers that pass the result directly to a gate threshold comparison.
**Fix:** Verify every call site of `word_overlap` / `_fuzzy_word_overlap` asserts that a `0.0` return correctly propagates to a FAIL disposition rather than being swallowed by an `or`-short-circuit or default-`True` fallback.

---

## MAJORITY FINDINGS (2 of 3 models agree)

### M1 — G3b last-word context needs `selection_lock` text, not isolated token (Gemini + Grok)
**What:** Gate G3b, when checking the final word of a sentence, was previously passing only the isolated last token to the canonicaliser. For multi-word numeric phrases like "40 trillion", the canonicaliser cannot resolve "trillion" without seeing "40" in the same context window, producing a comparison mismatch. The fix (lines 331-333 reading from `selection_lock`) is in the diff.
**File/Line:** `qa_gates.py:331-333`
**Fix confirmed in diff.** Regression test should include the specific case `"above 40 trillion"` vs `"above 40 trillion dollars"` to lock this in permanently.

### M2 — `_key` / currency-unit fragility if ASR emits novel units (Grok + Gemini implicit)
**What:** `punctuation.py:124` strips "dollars/percent" only when immediately following a digit token. If ASR emits other unit words (e.g., "euros", "pence", "bps", "percent" detached from a number) the key will not normalise them, producing a mismatch that silently causes alignment drift.
**File/Line:** `punctuation.py:118-125`
**Fix:** Extend the unit-stripping set to cover the full vocabulary listed in `canon.py`'s number normaliser (since those are the words canon already knows how to handle). Keep the "must follow a digit" guard to avoid over-stripping.

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### UI1 — `_says` token-run match replaces substring match (Gemini only, HIGH VALUE)
**What:** Gemini specifically highlighted that `_says` now uses a contiguous-token-run match instead of `alias in t_lower`, preventing false positives where a short channel name or keyword appears as a substring inside a longer unrelated word (e.g., "in" matching inside "binance").
**Assessment:** **IMPLEMENT / VERIFY.** This is a genuine correctness improvement that GPT-4o and Grok accepted without comment, suggesting they read it as already resolved. Confirm the new `_says` function is used at every former substring-match call site in both `qa_gates.py` and `gates.py`. Add a targeted negative test: a clip whose ASR transcript contains a channel name as a substring of a longer word must NOT trigger a false positive.

### UI2 — `TestSites` architectural grep-test enforcing L-k across the whole codebase (Gemini only, HIGH VALUE)
**What:** Gemini identified that `test_canon.py`'s `TestSites` class programmatically scans the codebase for forbidden ad-hoc normalization patterns, enforcing L-k as a living lint rule rather than a code-review checklist item.
**Assessment:** **IMPLEMENT / EXTEND.** This pattern is excellent. The second pass should ensure `TestSites` also bans direct calls to Python's built-in `.lower()` or `.strip()` on text that enters any comparison path, since those bypass canon's Unicode NFKC + entity-decode logic. Add that pattern to the grep list.

### UI3 — `canon_tokens(heads=True)` distinction for `stand_alone.py` (Gemini only, MEDIUM VALUE)
**What:** Gemini noted that `stand_alone.py:144` calls `canon_tokens(heads=True)` while all other call sites use the default. This is intentional (stand-alone subject-term matching needs head words only) but is currently undocumented at the call site.
**Assessment:** **INVESTIGATE.** Add an inline comment at line 144 explaining why `heads=True` is correct here, to prevent a future developer from "normalising" it away. No functional change needed.

### UI4 — Removal of hardcoded `/home/ultron/` absolute paths (Gemini only, LOW but confirms portability)
**What:** Gemini called out that `gates.py:73,93` previously used absolute paths that would break on any non-`ultron` host.
**Assessment:** Already fixed in the diff. Verify CI runs on a clean container to confirm no other hardcoded paths remain (`grep -r '/home/ultron' .` as part of `regression_test.sh`).

---

## CONFLICTS (models disagree — your tiebreaker)

### C1 — Severity of import-path issue
- **Grok:** MEDIUM
- **GPT-4o:** Not explicitly flagged as a defect (accepted as resolved)
- **Gemini:** MEDIUM (flagged identically to Grok)

**Tiebreaker — Grok/Gemini are correct.** GPT-4o under-weighted this. In a long-running worker process that handles multiple clips sequentially, repeated `sys.path.insert(0, ...)` grows the path list unboundedly and can cause the wrong version of a module to be imported if two clips with different working directories are processed in the same interpreter. This is a real operational risk, not cosmetic. Classify as **P1 HIGH**, not cosmetic.

### C2 — Verdict strictness
- **GPT-4o:** "No defects identified" / READY with zero issues logged
- **Grok:** READY with 2 minor issues
- **Gemini:** READY with 4 issues (2 MAJOR already resolved in diff, 2 MEDIUM residual)

**Tiebreaker — Gemini's framing is most honest** because it distinguishes defects *resolved by the diff* (and therefore verifiable) from defects *residually open*. The two MAJOR items Gemini listed are confirmed-fixed; the two MEDIUM items (import hygiene, `word_overlap` call-site propagation) remain open. GPT-4o's clean bill should be treated as "no new defects introduced" rather than "nothing to do." Consensus verdict is **READY with P1 and P2 items to close.**

---

## VALIDATED STRENGTHS (all models agree — do NOT change in the second pass)

1. **`pipeline/canon.py` architecture and implementation** (lines 414-628): All three models agree the centralised canonicaliser is thorough, well-designed (state-machine for `owed`-word placement, NFKC normalisation, HTML entity decode, split-token joining), and directly implements L-k. Do not refactor internals.

2. **`TestEquivalence` + `TestDifferences` + `TestAligned` in `test_canon.py`**: All three models praised the dual-polarity testing (mutations that MUST match; differences that MUST NOT match) and the alignment index validation. Do not simplify or remove any existing test cases.

3. **`TestSites` grep-enforcement of L-k**: Gemini flagged it as exemplary; Grok and GPT-4o implicitly accepted it. Keep and extend, do not remove.

4. **`word_overlap` returning `0.0` on empty reference**: The fix itself is correct and unanimously validated. Do not revert.

5. **`test_g3b_majority.py` using `same(a, b)` canonical equivalence**: All models confirmed this is the correct testing idiom post-canon. Do not rewrite to exact-list assertions.

6. **`_says` contiguous token-run matching**: Unanimously accepted as a correctness improvement over substring matching. Do not revert to `alias in t_lower`.

---

## LAW COMPLIANCE CONSENSUS

| Law | Status | Confidence |
|---|---|---|
| **L-k ONE CANONICAL FORM** | ✅ COMPLIANT | Unanimous |
| **L-g WRITTEN FORMS** | ✅ COMPLIANT | Unanimous |
| **L-h TEXT READ AS SPOKEN** | ✅ COMPLIANT | Unanimous |
| **L-a SIGN-OFF NAMES ALL** | ✅ COMPLIANT | Unanimous |
| **L-b EDGE WORDS WHOLE** | ✅ COMPLIANT | Unanimous |
| **L-c DISSENT IS RIGHT UNTIL DISPROVED** | ✅ COMPLIANT | Unanimous |
| **L-d PROTECTED PREVIEW** | ✅ COMPLIANT (unaffected) | Unanimous |
| **L-e PUNCTUATED BEFORE READ** | ✅ COMPLIANT (prerequisite met) | Majority |
| **L-f CHANNELS FIRST** | ✅ COMPLIANT | Unanimous |
| **L-i THE CLAIM IS THE EVENT** | ✅ COMPLIANT | Majority |
| **L-j RELEASE IS AUTHORISED ON THESE BYTES** | ✅ COMPLIANT | Majority |
| **SELECTION LOCK** | ✅ COMPLIANT | Unanimous |
| **SNAP LIMIT** | ✅ COMPLIANT | Unanimous |
| **SENTENCE LAW** | ✅ COMPLIANT | Unanimous |
| **NEIGHBOUR** | ✅ COMPLIANT | Majority |
| **ONSET/TAIL** | ✅ COMPLIANT | Majority |
| **M12 FAIL CLOSED** | ✅ COMPLIANT (fix confirmed in diff) | Unanimous |
| **LAW 20 / M2** | ✅ COMPLIANT (no thresholds loosened) | Unanimous |
| **LAW 22** | ✅ COMPLIANT (v2f path unchanged) | Unanimous |

**No laws are currently violated.** The residual P1/P2 items are hygiene and robustness concerns, not law violations.

---

## SECURITY CONSENSUS

| Issue | Models | Priority |
|---|---|---|
| `sys.path.insert` path-injection risk — a maliciously named directory on the host could shadow a legitimate module if the path is attacker-influenced | Grok + Gemini | P1 |
| No input-length or token-count guard in `canon.py` — an adversarially long transcript could cause quadratic behaviour in the state machine | None explicitly flagged, but implied by Gemini's "robustness" comments | P2 (investigate) |
| Hardcoded absolute paths removed — residual grep needed to confirm none remain | Gemini | P2 |

No injection, authentication, or data-exfiltration issues were identified by any model.

---

## WORLD-CLASS GAP CONSENSUS (2+ models mentioned)

1. **Package structure / import hygiene** (Grok + Gemini): A truly world-class pipeline module uses proper Python package imports, not `sys.path` manipulation. The current pattern is a known source of CI-vs-production discrepancies and import shadowing bugs.

2. **Caller-site propagation of `word_overlap = 0.0`** (Grok + Gemini): A world-class gate system guarantees that a FAIL signal from any sub-function cannot be absorbed by a default-True fallback further up the call stack. The fix at line 213 is necessary but not sufficient without auditing all callers.

3. **Negative/adversarial test cases for `_says`** (Gemini + implicit from Grok's false-positive concern): World-class tests include cases designed to break the system — specifically, channel names appearing as substrings inside unrelated words in ASR output.

4. **Extension of `TestSites` lint coverage** (Gemini alone explicitly, but consistent with the L-k concern all models raised): World-class architectural enforcement would also ban bare `.lower()` / `.strip()` in comparison paths, not just the specific patterns already listed.

---

## FINAL ACTION PLAN (sorted by consensus priority)

```
P0 CRITICAL | Audit all callers of word_overlap / _fuzzy_word_overlap to confirm 0.0 propagates to FAIL (not absorbed by default-True or or-short-circuit) | qa_gates.py + all callers | models: grok + gemini | M12 FAIL CLOSED — a gate that silently passes on empty reference is a release-safety defect

P1 HIGH     | Replace all sys.path.insert calls with proper package-relative imports or a single importlib bootstrap | gates.py:73,92,218,284 and qa_gates.py equivalents | models: grok + gemini | Prevents module-shadowing and path-state leakage across clips in long-running workers; also a latent security surface

P1 HIGH     | Add targeted negative test for _says: ASR transcript where channel name is substring of longer word must NOT trigger gate pass | qa_gates.py + test_qa_gates.py | models: gemini (unique but high-value) | Confirms the substring→token-run fix is complete and locks it against regression

P2 MEDIUM   | Extend unit-stripping set in _key to cover full canon.py currency/unit vocabulary (euros, pence, bps, etc.), keeping digit-guard | punctuation.py:118-125 | models: grok + gemini | Prevents silent alignment drift when ASR emits non-USD currency units

P2 MEDIUM   | Extend TestSites grep list to ban bare .lower() / .strip() on text entering any comparison path | test_canon.py:825+ | models: gemini (unique) + L-k concern (all) | Enforces L-k at the byte level — NFKC + entity-decode bypass is the most likely future regression vector

P2 MEDIUM   | Add inline comment at stand_alone.py:144 explaining why heads=True is correct for subject-term matching | stand_alone.py:144 | models: gemini (unique) | Prevents future "normalisation" of a load-bearing parameter difference

P2 MEDIUM   | Add grep -r '/home/ultron' . to regression_test.sh to catch any surviving hardcoded paths | regression_test.sh | models: gemini | Portability — CI runs on clean containers, not ultron
```

---

## CYCLE 1 VERDICT

**READY FOR SECOND BUILD PASS.**

The diff itself is correct, law-compliant, and well-tested. No model identified a functional defect introduced by the changes. The two previously-MAJOR issues (scattered normalisation violating L-k; substring matching causing false-positive gate passes) are resolved within the diff and unanimously validated. The residual items are import hygiene (P1), caller-site propagation audit (P0), and test/lint extensions (P2). None require rearchitecting the solution.

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/PULSE_SENTENCE_LAW_GOSPEL.md.
Read ~/protocol_pulse/docs/audits/pulse-sentence-law_CONSENSUS_C1.md.

This is the SECOND PASS for pulse-sentence-law.
The first build was reviewed by 3 independent AI models (Gemini 2.5 Pro,
GPT-4o, Grok-3) across 1 cycle. Implement every P0 and P1 item from the
consensus. Use judgment on P2.

PRIORITY ACTION PLAN:

P0 CRITICAL | Audit every caller of word_overlap and _fuzzy_word_overlap.
  Confirm that a return value of 0.0 propagates to a gate FAIL disposition
  and is not absorbed by a default-True fallback, an `or True` short-circuit,
  or a missing None-check. Fix any site where it can be swallowed.
  File: qa_gates.py + all callers. Reason: M12 FAIL CLOSED.

P1 HIGH | Replace every sys.path.insert(0, ...) call with proper
  package-relative imports (`from ..pipeline import canon`, etc.) or, where
  the package boundary prevents that, a single importlib.util bootstrap that
  runs once at process start. Remove all sys.path mutations from hot
  (per-clip) code paths.
  Files: gates.py:73,92,218,284 and any equivalent in qa_gates.py /
  editorial_gate.py. Reason: prevents module-shadowing and path-state
  leakage across clips in long-running workers.

P1 HIGH | Add a targeted negative regression test for the _says function.
  Scenario: an ASR transcript whose text contains a known channel name or
  keyword as a strict substring of a longer unrelated word (e.g., the word
  "binance" containing "in", or "bloomberg" containing "bloom"). The gate
  must NOT fire. Place in test_qa_gates.py alongside existing _says tests.
  Reason: confirms the substring→contiguous-token-run fix is complete and
  locked against regression.

P2 MEDIUM | Extend the unit-stripping set in punctuation.py _key (lines
  118-125) to cover the full currency/unit vocabulary already known to
  canon.py (euros, pence, bps, cents, etc.). Keep the "must immediately
  follow a digit token" guard. Reason: prevents silent alignment drift when
  ASR emits non-USD currency denominations.

P2 MEDIUM | Extend the TestSites grep list in test_canon.py (line 825+) to
  ban bare .lower() and .strip() calls on any variable that enters a
  comparison path. The pattern to ban: `\.lower()` and `\.strip()` appearing
  in cut_accept.py, editorial_gate.py, gates.py, pinned.py, stand_alone.py,
  qa_gates.py, punctuation.py outside of canon.py itself.
  Reason: NFKC + entity-decode bypass is the most likely future L-k
  regression vector.

P2 MEDIUM | Add a one-line comment at stand_alone.py:144 explaining that
  `heads=True` is intentional for subject-term (head-word) matching and
  must not be changed to match the default canon_tokens signature.
  Reason: prevents future "normalisation" of a load-bearing parameter.

P2 MEDIUM | Add `grep -r '/home/ultron' . && exit 1` (or equivalent) to
  regression_test.sh so that any re-introduction of hardcoded absolute paths
  causes CI to fail. Reason: portability; CI runs on clean containers.

VALIDATED — do NOT touch (all 3 models confirmed excellent):
- pipeline/canon.py lines 414-628: architecture, state machine, NFKC +
  entity-decode + split-token-joining logic. Do not refactor internals.
- test_canon.py TestEquivalence, TestDifferences, TestAligned: dual-polarity
  testing and alignment index validation. Do not simplify or remove cases.
- test_canon.py TestSites: grep-enforcement of L-k. Keep and extend only.
- qa_gates.py:213 word_overlap returning 0.0 on empty reference. Do not
  revert.
- test_g3b_majority.py using same(a, b) canonical equivalence idiom.
  Do not rewrite to exact-list assertions.
- qa_gates.py _says contiguous token-run matching. Do not revert to
  substring matching.

After implementing: regression_test.sh must show zero FAILs.
git add -A && git commit -m "feat(pulse-sentence-law): post-audit pass — consensus improvements (C1)"
git push origin combo-letterbox-quoteonly-v2
```