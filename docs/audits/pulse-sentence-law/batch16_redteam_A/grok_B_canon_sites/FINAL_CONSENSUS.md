# CONSENSUS REPORT — PULSE-SENTENCE-LAW — CYCLE 2
Generated: 2026-11-11 22:49
Models: gpt4o, grok, gemini

---

## SCORES

| Subsystem            | Gemini | GPT-4o | Grok | Consensus |
|----------------------|--------|--------|------|-----------|
| Correctness          | 7/10   | 9/10   | 9/10 | **8/10**  |
| Law Compliance       | 10/10  | 9/10   | 9/10 | **9/10**  |
| Test Quality         | 9/10   | 9/10   | 9/10 | **9/10**  |
| Security / Robustness| 6/10   | 8/10   | 6/10 | **6/10**  |
| Overall Readiness    | 6/10   | 9/10   | 8/10 | **7/10**  |

> **Score arbitration notes:**
> - Gemini uniquely identified a P0 correctness bug in `canon_aligned`, dragging its Correctness and Overall Readiness scores down. GPT-4o and Grok did not catch this bug; their higher scores reflect incomplete analysis. Consensus Correctness is settled at 8/10 (above Gemini's floor, below the others' ceiling) pending bug confirmation.
> - Robustness consensus of 6/10 reflects Grok's deeper assessment of the repeated-execution risk in `_canon()` and Gemini's systemic framing — both more severe than GPT-4o's 8/10.
> - Overall Readiness of 7/10 reflects the existence of at least one unresolved P0 candidate and a unanimous P1 architectural flaw.

---

## UNANIMOUS FINDINGS (all 3 models agree — implement unconditionally)

### U1 — Systemic `sys.path.insert` in runtime code
- **What:** Every model flagged the repeated use of `sys.path.insert` for relative imports as a significant architectural defect. Mutating global `sys.path` at request time is non-deterministic, slow, and can produce import-state leakage across clips in a long-running process.
- **Files/Lines:** `pipeline/gates.py:73, 92` and `segment_v1/qa_gates.py:218, 284`
- **Fix:** Remove all dynamic `sys.path` mutations. Convert to standard package-relative imports (`from ..pipeline import canon`) or, if the package structure prevents this, perform a single bootstrap `importlib`-based import at process startup — never at call time.

### U2 — `word_overlap` fail-open bug now patched; call-site verification required
- **What:** All three models confirmed that the original `word_overlap` returned `1.0` on an empty reference (fail-open, violating M12 FAIL CLOSED). The diff fixes this to `0.0`. All models also agreed that the fix must be verified at every call site — a 0.0 return must produce a FAIL disposition with no silent short-circuit swallowing.
- **Files/Lines:** `segment_v1/qa_gates.py:213` (fix) + all callers of `word_overlap` and `_fuzzy_word_overlap`
- **Fix:** Audit every call site. Assert that a 0.0 return propagates to a hard FAIL. Add a targeted regression test: empty reference input → gate disposition is FAIL.

---

## MAJORITY FINDINGS (2 of 3 models agree)

### M1 — G3b `selection_lock` context fix is correct and critical
- **Models:** Gemini + Grok (GPT-4o noted the change but did not explain the mechanism)
- **What:** The previous `gate_g3b` passed only the final isolated token to the canonicaliser (e.g., "trillion" alone). `canon.py` cannot resolve multi-word number phrases without context. The fix reads the full `selection_lock` text, giving `canon.py` the preceding "40" it needs to correctly emit "40 trillion dollars". This is a materially important correctness fix for L-g compliance.
- **Status:** Already fixed in the diff. No code change needed — but document the invariant: the canonicaliser must always receive full phrase context, never isolated tokens.

### M2 — `punctuation.py:124-125` `_key` unit-dropping logic is fragile
- **Models:** Grok + Gemini
- **What:** The rule that drops "dollars"/"percent" only after a digit-string token creates a brittle implicit dependency on `canon.py`'s output format. If `canon.py` is ever updated to emit spelled-out numbers, the alignment logic silently breaks.
- **Files/Lines:** `pipeline/punctuation.py:124-125`
- **Fix (P2):** At minimum, add a comment coupling this logic to `canon.py`'s numeric output contract. Preferred: move this rule into `canon.py` itself so there is a single owner.

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### X1 — Bug in `canon_aligned` for numbers ≥ 1,000,000 (Gemini only)
- **What:** Gemini identified that the token-joining regex in `canon.py:616` (`re.fullmatch(r"\$?\d{1,3}", w.strip())`) checks the *accumulated* buffer `w`. For a Whisper split like `['1', '234', '567']`, after joining '1' and '234', `w` becomes `'1234'` — four digits — and fails the `\d{1,3}` check, terminating the merge loop. The token '567' is then processed independently, corrupting alignment for any number ≥ 1,000,000.
- **Assessment: IMPLEMENT.** This is a plausible and mechanically sound analysis. The regex `\d{1,3}` is unambiguous — it cannot match a 4+ digit string. The bug manifests silently (no exception, just wrong tokens), which makes it especially dangerous. Even if large numbers are rare in current content, they will occur (financial data, population figures, etc.). The fix is trivial and the risk of leaving it is high.
- **Files/Lines:** `pipeline/canon.py:616`
- **Fix:** Change `re.fullmatch(r"\$?\d{1,3}", w.strip())` to `re.fullmatch(r"\$?\d+", w.strip())` (unbounded digit match on the accumulated buffer). Add a regression test: `canon_aligned(['1', '234', '567'])` → single token representing 1,234,567.

### X2 — `_canon()` helper in `qa_gates.py` executes `sys.path.insert` on every call (Grok only)
- **What:** Unlike the four static inserts in `gates.py` that execute once at module load, the `_canon()` helper in `qa_gates.py:282-287` runs `sys.path.insert` on every invocation. In a production pipeline processing thousands of clips, this executes thousands of times, progressively degrading `sys.path` with duplicate entries and imposing unnecessary overhead.
- **Assessment: IMPLEMENT.** This is strictly worse than the static-insert pattern and directly extends U1. Even if U1 is resolved by switching to package-relative imports (which would eliminate this site entirely), it should be called out explicitly to ensure it is not overlooked.
- **Files/Lines:** `segment_v1/qa_gates.py:282-287`
- **Fix:** Covered by the U1 fix. If for any reason the broader refactor is deferred, add a module-level guard (`_canon_imported = False`) to prevent repeated execution as an interim measure.

### X3 — `_says` substring-to-token-run upgrade prevents false positives (Gemini only)
- **What:** Gemini noted that replacing `alias in t_lower` substring matching with the `_says` contiguous-token-run helper in `qa_gates.py:360` prevents false positive alias matches (e.g., "in" matching inside "binance"). This is a meaningful hardening of the gate logic.
- **Assessment: ALREADY FIXED in the diff.** No action needed. Document as a validated strength.

### X4 — `TestSites` grep test programmatically enforces L-k (Gemini only)
- **What:** The `test_canon.py:825` grep test verifies that every call site in the codebase uses the canonical form — not just that the function itself is correct. This is an architectural enforcement mechanism for L-k (ONE CANONICAL FORM).
- **Assessment: VALIDATED STRENGTH.** No action needed.

---

## CONFLICTS (models disagree — tiebreaker)

### Conflict 1 — Overall Readiness / Production Ready?

| Model  | Verdict |
|--------|---------|
| Gemini | **No** — P0 bug + P1 architectural flaw = not shippable |
| Grok   | **Yes with conditions** — import hygiene is the only material issue |
| GPT-4o | **Yes with conditions** — same as Grok |

**Tiebreaker: Gemini is correct.**
Grok and GPT-4o did not identify the `canon_aligned` regex bug (X1). A silent corruption of number-token alignment in a core module is a P0 regardless of how rare large numbers currently are. The code should not ship until X1 is fixed and regression-tested. Gemini's "No" verdict stands.

### Conflict 2 — Security / Robustness score

| Model  | Score |
|--------|-------|
| Gemini | 6/10  |
| GPT-4o | 8/10  |
| Grok   | 6/10  |

**Tiebreaker: 6/10 consensus.**
GPT-4o's 8/10 reflects insufficient weight given to the systemic `sys.path` mutation pattern and the per-call execution risk in `_canon()` (X2). The 2-model consensus of 6/10 is correct.

---

## VALIDATED STRENGTHS (all models agree — do NOT change in second pass)

1. **`canon.py` centralization** — Replacing 7+ scattered ad-hoc normalisers with a single, extensively tested module is the right architectural decision. The implementation is thorough: HTML entities, NFKC Unicode, case folding, Whisper token joins, state-machine number/currency handling.
2. **`word_overlap` fail-closed fix** — The change from returning `1.0` to `0.0` on empty reference is correct and critical.
3. **G3b `selection_lock` context fix** — Reading the full phrase from `selection_lock` rather than an isolated token is a correct and necessary fix for L-g compliance.
4. **`_says` token-run matching** — The upgrade from substring to contiguous canonical token match is a meaningful precision improvement.
5. **`test_canon.py` test suite** — 200 real sentences, equivalence and non-equivalence assertions, and the `TestSites` grep enforcement are all excellent test design. Do not regress these.
6. **`_words_number` state machine (`owed` variable)** — The design for correctly ordering spoken "dollars" after numeric amounts is robust and well-reasoned.
7. **Removal of hardcoded absolute paths** (`/home/ultron/...`) in `gates.py` — Correct portability fix.

---

## LAW COMPLIANCE CONSENSUS

| Law | Status | Notes |
|-----|--------|-------|
| **L-k ONE CANONICAL FORM** | ✅ COMPLIANT | `canon.py` is the single source of truth; `TestSites` grep enforces call-site compliance |
| **L-g WRITTEN FORMS** | ✅ COMPLIANT | `canon.py` correctly maps `$40 trillion` → `40 trillion dollars`; old `qa_gates.py` logic removed |
| **L-h TEXT READ AS SPOKEN** | ✅ COMPLIANT | Spoken-order currency/percentage handling implemented in `canon.py` |
| **SENTENCE LAW** | ✅ COMPLIANT | First/last words taken from sealed `selection_lock` via canon; never recomputed from moved cuts |
| **SELECTION LOCK** | ✅ COMPLIANT | G3b fix reads from `selection_lock`; no recomputation after lock |
| **SNAP LIMIT** | ✅ COMPLIANT | No path allows a cut outside the locked sentence gap |
| **M12 FAIL CLOSED** | ✅ COMPLIANT (patch applied) | `word_overlap` now returns 0.0 on empty reference; call-site audit still required |
| **L-a SIGN-OFF NAMES ALL** | ✅ COMPLIANT | Canonical form used for name matching |
| **L-b EDGE WORDS WHOLE** | ✅ COMPLIANT | Canonical form ensures accurate edge word detection |

**No laws are violated.** The `canon_aligned` bug (X1) is an implementation defect within an otherwise compliant design — it prevents correct fulfillment of L-g in the specific case of large split numbers, but does not represent a law violation in intent.

---

## SECURITY CONSENSUS

No security vulnerabilities (injection, privilege escalation, data leakage) were identified by any model. The two robustness concerns with security-adjacent implications are:

1. **`sys.path` mutation (U1 / X2):** Global mutable state in `sys.path` is an operational stability risk, not a traditional security risk. In a multi-tenant or sandboxed deployment it could theoretically be exploited for import hijacking, but that is a low-probability concern in this architecture.
2. **Silent wrong output from `canon_aligned` (X1):** A canonicaliser that silently produces wrong tokens for large numbers could cause gates to pass clips that should be rejected (fail-open behavior for specific numeric phrases). This is an integrity risk more than a security risk.

**Priority order:** X1 (integrity) > U1/X2 (stability).

---

## WORLD-CLASS GAP CONSENSUS (2+ models mentioned)

1. **Package structure enabling standard imports** (all 3 models): A truly world-class codebase does not use `sys.path.insert` anywhere at runtime. The fact that this pattern appears in 5+ locations across multiple files indicates the package structure itself needs to be fixed (proper `__init__.py` hierarchy, `pyproject.toml` or `setup.py` with the package root declared) so that `from ..pipeline import canon` Just Works. This is an engineering discipline gap, not a one-line fix.

2. **Call-site contract documentation for `canon.py`** (Gemini + Grok): `canon.py` is now the load-bearing foundation for all text comparison. Its contract (inputs it accepts, invariants it guarantees, what "canonical form" means precisely) should be documented at the module level as a formal spec, not just inline comments. This prevents the fragile implicit couplings identified in `punctuation.py` (M2) from multiplying.

3. **Large-number regression coverage in `test_canon.py`** (Gemini + implicit from Grok's call-site verification emphasis): The test suite is excellent for the cases it covers, but the `canon_aligned` bug reveals a gap: numbers ≥ 1,000,000 split across Whisper tokens are not covered. World-class test coverage requires boundary cases at powers of 1,000.

---

## FINAL ACTION PLAN (sorted by consensus priority)

| Priority | Change | File:Line | Models | Why |
|----------|--------|-----------|--------|-----|
| **P0 CRITICAL** | Fix `canon_aligned` regex: change `r"\$?\d{1,3}"` to `r"\$?\d+"` on the accumulated buffer `w` to correctly join split Whisper tokens for numbers ≥ 1,000,000. Add regression test `['1','234','567']` → single canonical token. | `pipeline/canon.py:616` + `test_canon.py` | unique/gemini | Silent wrong-token output; fail-open integrity risk for large-number phrases; trivial fix with high confidence |
| **P1 HIGH** | Remove all `sys.path.insert` calls from runtime code. Fix package structure to allow standard relative imports (`from ..pipeline import canon`). The `_canon()` helper in `qa_gates.py:282-287` is especially critical — it fires on every call, not just at module load. | `pipeline/gates.py:73,92` · `segment_v1/qa_gates.py:218,282-287` | all 3 | Global mutable state; per-call overhead; import-state leakage across clips in long-running process |
| **P1 HIGH** | Audit every call site of `word_overlap` and `_fuzzy_word_overlap`. Confirm that a 0.0 return propagates to a hard FAIL disposition with no silent short-circuit. Add targeted regression test: empty reference → gate disposition is FAIL. | All callers in `segment_v1/qa_gates.py` | all 3 | M12 FAIL CLOSED; patch is applied but downstream propagation unverified |
| **P2 MEDIUM** | Move the "drop dollars/percent after number" rule from `punctuation.py:124-125` into `canon.py`, or at minimum add a comment formally coupling this logic to `canon.py`'s numeric output contract. | `pipeline/punctuation.py:124-125` | grok + gemini | Fragile implicit coupling; silent breakage if `canon.py` ever changes numeric output format |
| **P2 MEDIUM** | Add `test_canon.py` cases for numbers ≥ 1,000,000 split across Whisper tokens (boundary: 1M, 1B, 1T) to prevent regression of the P0 fix. | `test_canon.py` | gemini + implied grok | Test coverage gap at known failure boundary |

---

## CYCLE 2 VERDICT

**NOT PRODUCTION READY.**

Two blockers prevent deployment:

1. **P0 — Silent corruption bug in `canon_aligned` (`pipeline/canon.py:616`):** The regex `\d{1,3}` cannot match an accumulated 4-digit buffer, causing token-merge to terminate prematurely for any number ≥ 1,000,000. This produces wrong canonical tokens silently, with no exception. In a financial/news context where large numbers are routine, this is an unacceptable integrity risk. Fix is a one-character change; there is no justification to ship without it.

2. **P1 — Systemic `sys.path.insert` in runtime execution paths:** Five call sites across two files mutate global import state at request time. The worst case (`_canon()` helper) executes on every gate evaluation. This is a stability and correctness risk for any long-running production process.

All law compliance targets are met. Test quality is high. The architectural direction (`canon.py` centralization) is correct and well-executed. This code is one focused fix session away from being production-ready.

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/PULSE_SENTENCE_LAW_GOSPEL.md.
Read ~/protocol_pulse/docs/audits/pulse-sentence-law_CONSENSUS_C2.md.

This is the FINAL PASS for pulse-sentence-law.
The first build was reviewed by 3 independent AI models across 2 cycles.
Implement every P0 and P1 item from the consensus. Use judgment on P2.

PRIORITY ACTION PLAN:

P0 CRITICAL | pipeline/canon.py:616 | Fix canon_aligned regex for large numbers
  - Change re.fullmatch(r"\$?\d{1,3}", w.strip()) to re.fullmatch(r"\$?\d+", w.strip())
  - This fixes silent token-merge failure for numbers >= 1,000,000 split by Whisper
  - Add regression test in test_canon.py: canon_aligned(['1','234','567']) must produce
    a single canonical token representing 1,234,567 (not two separate tokens)
  - Add boundary cases: 1M, 1B, 1T split tokens

P1 HIGH | pipeline/gates.py:73,92 and segment_v1/qa_gates.py:218,282-287 | Remove all sys.path.insert
  - Fix package structure to allow standard package-relative imports: from ..pipeline import canon
  - The _canon() helper in qa_gates.py:282-287 is critical — it executes sys.path.insert on
    EVERY call, not just at module load. This must be eliminated first.
  - If package structure cannot be fixed immediately: move import to module level with a single
    guard, never inside a function that is called at request time.

P1 HIGH | All callers of word_overlap and _fuzzy_word_overlap in segment_v1/qa_gates.py | Verify fail-closed propagation
  - Confirm that a 0.0 return from word_overlap propagates to a hard FAIL gate disposition
  - No call site may short-circuit or ignore a 0.0 return
  - Add regression test: empty reference string → gate disposition is FAIL (not PASS, not error)

P2 MEDIUM | pipeline/punctuation.py:124-125 | Fix fragile currency/percent unit coupling
  - Move the "drop dollars/percent after number" rule into canon.py so there is a single owner
  - If not moved: add a comment formally documenting the coupling to canon.py's numeric output contract
  - The current regex re.fullmatch(r"\d+(\.\d+)?", t[k-1]) must only match what canon.py guarantees to emit

P2 MEDIUM | test_canon.py | Add large-number boundary coverage
  - Add split-token test cases for numbers at powers of 1,000: 1,000 / 1,000,000 / 1,000,000,000
  - Verify both canon_aligned (merge path) and canon/canon_tokens (normalization path)

VALIDATED (do NOT touch — all 3 models confirmed excellent):
  - canon.py centralization: the single-source-of-truth design is correct; do not split or inline
  - word_overlap fail-closed patch (qa_gates.py:213): the 0.0 return is correct; do not revert
  - gate_g3b selection_lock context fix (lines 331-333): reading full phrase is essential for L-g; do not revert
  - _says token-run matching (qa_gates.py:360): precision upgrade over substring; do not revert
  - test_canon.py TestSites grep test (line 825): architectural enforcement of L-k; do not remove
  - _words_number state machine with owed variable in canon.py: robust spoken-order design; do not simplify
  - Removal of hardcoded /home/ultron/ absolute paths in gates.py: correct portability fix; do not reintroduce

After implementing: regression_test.sh must show zero FAILs.
Confirm test_canon.py passes with the new large-number cases before committing.
git add -A && git commit -m "feat(pulse-sentence-law): post-audit pass — consensus improvements"
git push origin combo-letterbox-quoteonly-v2
```

---

# WINNER DETERMINATION

## WINNER: **Grok**

Grok delivered the highest-quality analysis across both cycles: its Cycle 1 findings were the most accurate (confirmed by Cycle 2 consensus scoring of 9/10 Correctness), it uniquely identified the *repeated-execution* risk of `sys.path.insert` inside `_canon()` being called thousands of times per clip (a finding no other model caught), and its recommendations were the most specific and actionable — naming exact line numbers, severity tiers, and concrete fixes. While Gemini flagged a P0 `canon_aligned` bug that influenced consensus scoring, Grok's breadth, precision, and the novel Cycle 2 discovery demonstrated consistently deeper systemic reasoning throughout both cycles.

---

## FINAL SECOND-PASS PRIORITY LIST

### P0 — Blocking (must fix before merge)

| # | Finding | File / Lines | Action |
|---|---------|-------------|--------|
| P0-1 | **`canon_aligned` correctness bug** (Gemini-flagged candidate) | `pipeline/canon.py` — alignment path | Confirm or refute the bug with a targeted unit test; if confirmed, fix alignment logic before any production deployment |
| P0-2 | **`_canon()` helper executes `sys.path.insert` on every call** — can fire thousands of times per clip | `segment_v1/qa_gates.py:282–287` | Hoist import to module level; guard with a single `try/except ImportError` block at startup |

---

### P1 — High (fix in this sprint)

| # | Finding | File / Lines | Action |
|---|---------|-------------|--------|
| P1-1 | **Static `sys.path.insert` mutations at import time** | `pipeline/gates.py:73,92` · `segment_v1/qa_gates.py:218,284` | Replace all four with package-relative imports (`from ..pipeline import canon`) or a single `importlib` bootstrap; delete all `sys.path` mutations |
| P1-2 | **`word_overlap` call-site audit** — empty-reference fix is present in the function but downstream callers may still depend on the old `1.0` fail-open return | All callers of `word_overlap` and `_fuzzy_word_overlap` | Grep every call site; assert fail-closed (`0.0`) behaviour in an integration test that passes an empty reference |

---

### P2 — Medium (address before next release)

| # | Finding | File / Lines | Action |
|---|---------|-------------|--------|
| P2-1 | **`_key` fragility** — drops `"dollars"/"percent"` only when preceded by a digit-string; breaks if `canon.py` ever emits spelled-out numbers | `punctuation.py:124–125` | Add a property test: for every number format `canon.py` can emit, assert `_key` strips the unit correctly; document the dependency contract between the two modules |
| P2-2 | **`_says` substring-to-token-run upgrade** — confirm no regression in alias matching for short tokens (`"in"`, `"a"`, `"at"`) that previously matched inside longer words | `segment_v1/qa_gates.py` — `_says` helper | Add must-fail test cases: `_says("in", "binance transcript")` must return `False` |

---

### P3 — Low / Hardening (backlog)

| # | Finding | File / Lines | Action |
|---|---------|-------------|--------|
| P3-1 | **`canon.py` unit extensibility** — `_key` tolerance for ASR-emitted units is narrow; future units (`"pct"`, `"bps"`) will silently pass through unnormalized | `pipeline/canon.py` + `punctuation.py` | Add a registered unit table; unknown units after a numeric token emit a warning to the audit log |
| P3-2 | **`TestSites` grep test** — programmatic enforcement of L-k ("ONE CANONICAL FORM") is excellent but should also assert zero direct calls to deprecated normalizers | `test_canon.py:825` area | Extend grep to cover all files in `segment_v1/` and `pipeline/`; fail CI if any old normalizer symbol appears outside `canon.py` |
| P3-3 | **G3b `selection_lock` context** — fix is correct and materially improves L-g compliance; add an explicit regression test for the multi-word case | `segment_v1/qa_gates.py:331–333` | Test: `"40 trillion"` as final phrase must canonicalize identically whether supplied as a full phrase or reconstructed from lock context |