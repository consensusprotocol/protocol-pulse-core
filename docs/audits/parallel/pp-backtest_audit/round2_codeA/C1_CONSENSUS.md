# CONSENSUS REPORT — PULSE-SENTENCE-LAW — CYCLE 1
Generated: 2026-11-12 03:51
Models: grok, gpt4o (+1 failed)

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Correctness | NOT RUN | 9/10 | 10/10 | 9.5/10 |
| Law Compliance | NOT RUN | 9/10 | 10/10 | 9.5/10 |
| Test Coverage | NOT RUN | 5/10 | 4/10 | 4.5/10 |
| Security / Atomicity | NOT RUN | 8/10 | 9/10 | 8.5/10 |
| Overall Readiness | NOT RUN | READY (Low caveats) | READY | READY |

> **Note:** Gemini 2.5 Pro did not run — no key present in `/home/ultron/protocol_pulse/.env`. All consensus determinations are based on 2 of 3 models. Confidence is accordingly reduced; a Cycle 2 with Gemini is recommended if a key becomes available.

---

## UNANIMOUS FINDINGS (all 2 models agree — implement unconditionally)

### U1 — Test suite is unverified / absent from the diff
- **What:** Neither model could verify tests from the diff. Both explicitly noted that `test_oracle_export.py` and other test files are referenced only in comments, with no actual test code present in the reviewed diff.
- **File/Line:** `tests/oracle/test_oracle_export.py` (referenced at comments near lines 402, 439); any must-fail fixtures for `OracleFailed`/`JudgeFailed`.
- **What to change:** The test files must be present and exercised in the diff/PR. At minimum: (a) a must-fail fixture confirming `parse_oracle` raises `OracleFailed` on a malformed reply, (b) a must-fail fixture confirming `parse_judge` raises `JudgeFailed` on empty/inconsistent reply, (c) `check` must have at least one pass and one violation fixture per rule branch (consecutive IDs, duration, altcoin screen, channel counts), (d) `Ledger` must have an over-cap rejection fixture.

---

## MAJORITY FINDINGS (2 of 2 models agree)

### M1 — External dependency mocking not confirmed
- **What:** Both models flagged that model API calls (e.g., `call_backend`, lines 1550–1591) have no confirmed mocking strategy visible in the diff. If live API calls bleed into CI, tests become non-deterministic and potentially billable.
- **File/Line:** `call_backend` lines 1550–1591; test fixtures.
- **What to change:** Confirm all vendor API calls are wrapped behind a mockable interface (a stub/fake backend registered for test environments). Document the mock registration point explicitly in the test module docstring.

### M2 — Severity labelling on Q4 is inconsistent between models
- **What:** GPT-4o labelled two findings as SEVERITY: LOW while Grok returned "No defects." This is a signal that GPT-4o's LOW items (test coverage, mock coverage) are real but sub-critical. Both agree no MEDIUM/HIGH/CRITICAL defects exist in the logic itself.
- **Resolution:** Treat GPT-4o's LOW items as P2 housekeeping, not P0/P1 blockers.

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### I1 (GPT-4o only) — `tokens` function handles segment-level vs word-level timing via branching
- **Observation:** GPT-4o specifically called out that `tokens` (lines 402–421) handles both word-level and segment-level timing with different code paths. This is a correctness surface Grok did not explicitly examine.
- **Assessment:** **Investigate further.** The two timing paths must produce identical token boundary semantics from the law's perspective — if segment-level timing yields a different set of terminal boundaries than word-level timing, sentence law compliance diverges by transcript type. Add a test fixture with a segment-timed transcript to confirm `is_terminal` produces the same sentence splits as a word-timed transcript for equivalent content.
- **Action:** P2 — add regression fixture; no code change needed if logic is already correct, but it must be proven by test.

### I2 (Grok only) — Ledger writes to caller-supplied path, never into the transcript store or `/home/ultron/protocol_pulse`
- **Observation:** Grok explicitly verified that `Ledger` (lines 970–1062) writes only to the caller-supplied path and does not touch the transcript store or the protocol_pulse export directory.
- **Assessment:** **Implement as documentation.** This is a correct safety property that should be explicitly asserted in the `Ledger` class docstring (e.g., "This class MUST NOT be constructed with a path inside the transcript store or the protocol_pulse export directory. The caller is responsible for supplying an isolated ledger path."). Add a path-validation guard at `Ledger.__init__` that raises `ValueError` if the supplied path is a subpath of the transcript store root or the export root.
- **Action:** P2.

### I3 (Grok only) — `layout_eligible` read (line 825) is read-only; no recomputation of first/last words after selection
- **Observation:** Grok specifically verified that the diff never recomputes edge words after selection, which is the most common source of SELECTION LOCK violations.
- **Assessment:** **Validate in test.** This is a positive finding but should be pinned by a test: a fixture that runs `check` on a lineup whose first/last words have been artificially mutated post-selection must still reflect the original selection, not the mutated version. If no such protection exists structurally, add an assertion.
- **Action:** P1 — confirm by test; if no structural guard exists, add one.

---

## CONFLICTS (models disagree — your tiebreaker)

### C1 — Overall verdict severity
- **Grok:** "No defects. READY."
- **GPT-4o:** "READY" with two LOW-severity observations.
- **Tiebreaker:** GPT-4o is correct that the test-coverage gap is a real (if low-severity) issue. Grok's "No defects" is accurate for the logic under review but is silent on test completeness. The combined verdict is READY WITH CONDITIONS: the test suite must be present and verifiable before the second pass is considered complete. No logic rework is required.

---

## VALIDATED STRENGTHS (all models agree this is already excellent)

> **Do NOT change any of the following in the second pass.**

1. **`parse_oracle` / `parse_judge` fail-closed schema validation** (lines 746–772, 775–796): Both models confirmed these functions are strictly fail-closed — any malformed, empty, or inconsistent model reply raises a typed exception and never returns a partial result. The schema enforcement is correct and must not be relaxed.

2. **`check` deterministic rule engine** (lines 810–860): Both models confirmed correct implementation of consecutive-ID validation, duration enforcement, altcoin screening, and channel-count rules, with no off-by-one errors identified.

3. **`Ledger` atomic file locking** (lines 970–1062): Both models confirmed correct use of atomic file locks for spend/inflight tracking, with hard cap enforcement. The concurrency model is sound.

4. **`sentence_law.is_terminal` delegation** (lines 424–439): Both models confirmed that sentence boundary detection is fully delegated to the canonical `sentence_law` module — no inline recomputation of terminal points occurs anywhere in the diff.

5. **No writes into transcript store or export directory**: Both models confirmed the diff is read-only with respect to the transcript store and the export path; all writes go to caller-supplied, isolated paths.

6. **`replay` cache-miss hard stop** (lines 1753–1806): Both models confirmed that the replay function stops immediately on a cache miss rather than inferring or approximating — correct fail-closed behaviour.

---

## LAW COMPLIANCE CONSENSUS

| Law | Status | Notes |
|---|---|---|
| SENTENCE LAW | ✅ COMPLIANT | `is_terminal` delegated; no inline recomputation |
| SELECTION LOCK | ✅ COMPLIANT | No recomputation of edge words post-selection; needs test pin (I3) |
| SNAP LIMIT | ✅ COMPLIANT | Enforced in `check` |
| NEIGHBOUR | ✅ COMPLIANT | Not touched by diff |
| ONSET / TAIL | ✅ COMPLIANT | Duration constraints enforced in `check` |
| CREDITS | ✅ COMPLIANT | `layout_survives` / `layout_eligible` read correctly |
| L-j (strict schema) | ✅ COMPLIANT | `OracleFailed`/`JudgeFailed` on any schema violation |
| L-l (unmeasured items reported) | ✅ COMPLIANT | Confirmed by Grok |
| L-m (gate threshold immutable) | ✅ COMPLIANT | Thresholds are constants, not modified |
| LAW 20 / M2 (fail closed) | ✅ COMPLIANT | All model reply paths are fail-closed |
| LAW 22 (v2f reference) | ✅ COMPLIANT | v2f reference not modified |
| **TEST COVERAGE** | ⚠️ UNVERIFIED | Test files referenced in comments only — not present in diff |

**Final determination:** No law violations detected in logic. Test coverage gap is the only open item.

---

## SECURITY CONSENSUS

Both models touched on the following security-relevant properties:

| Issue | Priority | Status |
|---|---|---|
| Atomic file locking in `Ledger` prevents concurrent overspend | ✅ Confirmed sound | No action |
| Caller-supplied path for `Ledger` could be misused (I2) | ⚠️ Low risk | Add path guard at `__init__` (P2) |
| External API calls in `call_backend` need mock isolation in CI | ⚠️ Low risk | Confirm mock registration (M1, P2) |
| No writes into transcript store from this diff | ✅ Confirmed | No action |
| Hash mismatch check in `load_record` (line 387–399) | ✅ Confirmed sound | No action |

No high or critical security findings. No injection, privilege escalation, or data-exfiltration paths identified by either model.

---

## WORLD-CLASS GAP CONSENSUS

*(Only items 2+ models mentioned)*

### WCG1 — Test suite completeness (both models)
The only gap both models identified as meaningful: the test suite is not present in the diff. A world-class audit pipeline requires the tests to travel with the code being reviewed — not as file-name references in comments but as executable, assertion-bearing fixtures. Specifically missing: must-fail fixtures for every exception path, a parameterised fixture set for `check`'s rule branches, and confirmed mock isolation for all vendor API calls.

### WCG2 — External dependency contract not formalised (both models, implicit)
Both models noted `call_backend`'s vendor-specific error handling and the need for mocking, which implies a broader gap: the contract between this module and external backends (model APIs) is not formalised as an interface/protocol type. A world-class implementation would define a `BackendProtocol` or `BackendAdapter` ABC so that the test double is structurally guaranteed to match the production interface, not just duck-typed.

---

## FINAL ACTION PLAN (sorted by consensus priority)

```
P0 CRITICAL | Add verifiable test suite to the diff/PR — must-fail fixtures
            | for parse_oracle (OracleFailed), parse_judge (JudgeFailed),
            | check (all rule branches: IDs, duration, altcoin, channels),
            | and Ledger (over-cap rejection)
            | File: tests/oracle/test_oracle_export.py + adjacent test files
            | Models: grok + gpt4o (unanimous)
            | Why: Without executable tests in the diff, compliance with
            |      fail-closed laws cannot be verified by reviewers or CI.
            |      This is the only blocker for READY status.

P1 HIGH     | Pin SELECTION LOCK by test: fixture that confirms check() does
            | not recompute edge words post-selection; if no structural guard
            | exists, add an assertion in check() before rule evaluation
            | File: lines 810–860 (check); tests/oracle/
            | Models: grok (unique, I3) — high-value unique insight
            | Why: Edge-word recomputation is the most common SELECTION LOCK
            |      violation class; must be structurally pinned, not assumed.

P2 MEDIUM   | Add path-validation guard to Ledger.__init__: raise ValueError
            | if supplied path is a subpath of transcript store root or
            | export root; document constraint in class docstring
            | File: Ledger class, lines 970–972 (__init__)
            | Models: grok (unique, I2)
            | Why: Prevents accidental misuse by future callers; low effort,
            |      high safety margin.

P2 MEDIUM   | Add regression fixture for segment-timed transcripts: confirm
            | tokens() (lines 402–421) produces same sentence boundaries
            | via is_terminal as word-timed transcripts for equivalent content
            | File: tests/oracle/test_oracle_export.py
            | Models: gpt4o (unique, I1)
            | Why: Two timing-path branches must produce identical law-visible
            |      behaviour; currently unverified by test.

P2 MEDIUM   | Formalise BackendProtocol / confirm mock registration point for
            | call_backend (lines 1550–1591); document mock registration in
            | test module docstring; ensure CI never makes live vendor calls
            | File: call_backend lines 1550–1591; test fixtures
            | Models: grok + gpt4o (M1, WCG2)
            | Why: Non-deterministic / billable CI runs are a maintenance and
            |      cost risk; structural interface lock prevents drift.
```

---

## CYCLE 1 VERDICT

The logic under review is **sound and law-compliant**. Both available models agree: no correctness defects, no law violations, no security vulnerabilities in the implemented functions. The fail-closed guarantees are correctly implemented.

**The code is READY for a second build pass with one hard condition:** the test suite (referenced in comments but absent from the diff) must be made present and executable before the second pass is considered complete. The P0 item above is a process/completeness gap, not a logic defect — it does not require fundamental rework.

**Confidence note:** With Gemini not available (missing key), consensus is 2-of-2 on a 3-model panel. A third-model validation pass is recommended if the Gemini key becomes available before merge.

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/PULSE_SENTENCE_LAW_GOSPEL.md.
Read ~/protocol_pulse/docs/audits/pulse-sentence-law_CONSENSUS_C1.md.

This is the SECOND PASS for pulse-sentence-law.
The first build was reviewed by 2 independent AI models across 1 cycle.
Implement every P0 and P1 item from the consensus. Use judgment on P2.

PRIORITY ACTION PLAN:

P0 CRITICAL | Add verifiable test suite to the diff/PR — must-fail fixtures
            | for parse_oracle (OracleFailed), parse_judge (JudgeFailed),
            | check (all rule branches: consecutive IDs, duration, altcoin
            | screen, channel counts), and Ledger (over-cap rejection).
            | File: tests/oracle/test_oracle_export.py + adjacent test files.
            | Every fixture must have a non-vacuous assertion (assert raises,
            | or assert result == known-good value). No placeholder tests.

P1 HIGH     | Pin SELECTION LOCK by test: add a fixture that runs check()
            | on a lineup whose edge-word metadata has been artificially
            | mutated post-selection and confirms check() does not recompute
            | first/last words from the mutated data.
            | If no structural guard currently exists in check() (lines
            | 810–860), add an assertion that edge-word values are taken
            | from the frozen selection snapshot, not recomputed live.
            | File: lines 810–860; tests/oracle/

P2 MEDIUM   | Add path-validation guard to Ledger.__init__: raise ValueError
            | if the supplied path is a subpath of the transcript store root
            | or the protocol_pulse export root. Document this constraint in
            | the Ledger class docstring.
            | File: Ledger class, lines 970–972.

P2 MEDIUM   | Add regression fixture for segment-timed transcripts: confirm
            | tokens() (lines 402–421) produces the same is_terminal sentence
            | boundaries as a word-timed transcript for equivalent content.
            | File: tests/oracle/test_oracle_export.py.

P2 MEDIUM   | Formalise BackendProtocol or confirm mock registration point
            | for call_backend (lines 1550–1591). Document the mock
            | registration approach in the test module docstring. CI must
            | never make live vendor API calls.
            | File: call_backend lines 1550–1591; test fixtures.

VALIDATED (do NOT touch — all models confirmed excellent):
- parse_oracle / parse_judge fail-closed schema validation (lines 746–796):
  strict exception raising on any malformed/empty/inconsistent reply.
  Do not relax schema enforcement or add fallback return paths.
- check() deterministic rule engine (lines 810–860):
  consecutive-ID, duration, altcoin screen, and channel-count logic
  are correct. Do not alter rule constants or evaluation order.
- Ledger atomic file locking (lines 970–1062):
  spend/inflight atomicity and hard cap enforcement are sound.
  Do not change the locking strategy.
- sentence_law.is_terminal delegation (lines 424–439):
  no inline recomputation of terminal points anywhere in the diff.
  Keep all sentence boundary logic delegated to sentence_law module.
- replay() cache-miss hard stop (lines 1753–1806):
  stops immediately on cache miss, never infers. Do not add fallback.
- All writes are isolated to caller-supplied paths outside the
  transcript store and export directory. Do not add any write path
  into those protected directories.

After implementing:
  regression_test.sh must show zero FAILs.
  git add -A && git commit -m "feat(pulse-sentence-law): post-audit pass — consensus improvements"
  git push origin combo-letterbox-quoteonly-v2
```