# CONSENSUS REPORT — PULSE-SENTENCE-LAW — CYCLE 2
Generated: 2026-11-11 22:55
Models: gpt4o, grok, gemini

---

## SCORES

| Subsystem       | Gemini | GPT-4o | Grok | Consensus |
|-----------------|--------|--------|------|-----------|
| Correctness     | 5/5    | 5/5    | 5/5  | **5/5**   |
| Law Compliance  | 5/5    | 5/5    | 5/5  | **5/5**   |
| Test Quality    | 5/5    | 5/5    | 5/5  | **5/5**   |
| Security        | 5/5    | 5/5    | 5/5  | **5/5**   |
| **Overall**     | READY  | READY  | READY| **READY** |

---

## UNANIMOUS FINDINGS (all 3 models agree — implement unconditionally)

**None.** All three models reached identical conclusions: no defects, no violations, no mandatory changes. There are no issues flagged by all three models requiring a fix. The unanimous finding *is* the absence of defects.

---

## MAJORITY FINDINGS (2 of 3 models agree)

**None.** No issue was flagged as a defect or required change by any two or more models. Every substantive observation across both cycles was categorized as a strength or a neutral structural note, not a problem requiring remediation.

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### 1. File Descriptor Hygiene — `9>&-` in `pulse_check_run.sh` (lines 241, 250, 259)
**Caught by:** Gemini only  
**What it is:** The use of `9>&-` to explicitly close an inherited file descriptor on the lock file before forking child processes, preventing orphaned children from holding the lock open and deadlocking the pipeline.  
**Assessment:** **Validate and preserve.** This is a correct, sophisticated pattern. Gemini correctly identified it as a strength, not a defect. No change needed; treat it as a validated implementation detail that must not be removed in future refactors. Flag in internal documentation.

### 2. Exit-70 on "Success With No Output" in `pulse_check_run.sh` (lines 266-269)
**Caught by:** Gemini only  
**What it is:** After `run_fresh.py` exits 0, the shell script checks for the existence of the expected final video files and emits `exit 70` if they are absent, treating a "clean" run that produced nothing as a hard failure.  
**Assessment:** **Validate and preserve.** This is a correct application of the fail-closed principle. It closes a silent-failure gap where the pipeline could report success while delivering nothing. Document this exit code in runbook.

### 3. `TestWrapper` Integration Test for Shell Script in `test_preflight.py`
**Caught by:** Gemini only  
**What it is:** A test class that invokes `pulse_check_run.sh` itself, verifying that the preflight gate is correctly wired into the orchestration layer — not just testing Python units in isolation.  
**Assessment:** **Validate and preserve.** This is the most valuable kind of test for a shell-orchestrated pipeline. Its existence closes the gap between unit-level correctness and end-to-end integration. Must not be deleted or skipped.

### 4. `test_secrets_never_reach_the_output` Security Test
**Caught by:** Gemini only  
**What it is:** A test that confirms API keys are consumed by the pipeline but never appear in log output or any produced artifact.  
**Assessment:** **Validate and preserve.** Security-by-test is the correct pattern here. Gemini was right to call this out explicitly.

### 5. `align_quote` Token Offset Re-mapping (editorial_select.py, line 25)
**Caught by:** Gemini only (deep-dive validation, not a defect flag)  
**What it is:** Gemini verified that the logic re-mapping sub-window token indices back to full-transcript word indices is correct — a common source of off-by-one errors.  
**Assessment:** **Confirmed correct.** No change needed. Annotate with a code comment referencing this audit if the logic is not already commented, to protect against future regressions.

### 6. Structural "Closed Regression Loop" Observation
**Caught by:** Grok only  
**What it is:** The backtest + preflight combination forms a closed regression loop — future sentence-law violations become detectable before any render occurs.  
**Assessment:** **Accurate architectural observation.** Not a code change, but worth capturing in the architecture decision record (ADR) or gospels documentation as a design rationale statement.

### 7. GPU Check Foreign-Job Logic in `preflight.py` (line 564)
**Caught by:** Gemini only (deep-dive validation)  
**What it is:** Gemini validated that `check_gpu0` correctly identifies and excludes `ollama` and its child processes from the "foreign job" check, and that the memory simulation for Whisper headroom is arithmetically correct.  
**Assessment:** **Confirmed correct.** No change needed.

### 8. Git Ancestry Check Nuance — `merge-base --is-ancestor HEAD @{u}` (preflight.py, line 629)
**Caught by:** Gemini only  
**What it is:** Gemini noted the comment "HEAD pushed" is slightly imprecise — the check actually enforces "no unpushed local commits" — but confirmed the implemented logic is correct and deterministic.  
**Assessment:** **Minor documentation fix only.** Update the inline comment from `# HEAD pushed` to something like `# no local commits ahead of upstream` to prevent future misreading. Low priority but costs nothing.

---

## CONFLICTS (models disagree — your tiebreaker)

**None.** All three models were in full agreement across all findings, verdicts, scores, and recommendations in both cycles. There are no contradictions to adjudicate.

---

## VALIDATED STRENGTHS (all models agree this is already excellent — do NOT change)

The following areas achieved unanimous praise across all three models in both cycles. They represent the design and implementation patterns that must be preserved and treated as reference implementations:

1. **`canon.py` Centralization (L-k):** Every tokenization, normalization, and alignment path routes through `canon.canon_tokens`, `canon.canon`, and `canon.canon_aligned`. This is the structural backbone of the entire feature. Do not add any parallel text-processing path that bypasses `canon`.

2. **`transcript_fn` / `words_fn` Backtest Hooks (`editorial_select.py`, lines 54, 92-98):** The dependency-injection approach for frozen inputs during backtest is correctly implemented. It prevents any live acquisition, GPU allocation, or Whisper invocation during replay. Do not change the hook signature.

3. **`preflight.py` Fail-Closed Exception Handler (line 666):** Any exception inside a preflight check is treated as a failure, not as a pass. This is the correct M12 implementation. Do not weaken to `except: pass` or silent logging.

4. **`pulse_check_run.sh` Ordering (lines 236-241, 248-250):** Preflight runs before `run_fresh`, `release_auth` gates delivery, and attestation ordering is enforced. This sequence must not be reordered.

5. **`9>&-` File Descriptor Management (lines 241, 250, 259):** Prevents lock-file deadlocks from orphaned child processes. Must be preserved in any future shell script refactors.

6. **Exit-70 on Missing Finals (lines 266-269):** Treats a zero-exit run with no output files as a hard failure. Must not be removed.

7. **`TestWrapper` Shell Integration Test:** Verifies the full shell orchestration, not just Python units. Must not be deleted or converted to a mock.

8. **`test_secrets_never_reach_the_output`:** Confirms no API key leakage into logs or artifacts. Must remain in the test suite.

9. **Repository-relative `sys.path` (lines 110, 115, 128, 141, 154, 187):** Replaces all hardcoded `/home/ultron/...` absolute paths. Do not reintroduce absolute paths.

10. **`sentence_ready` Guard and `words_fn` Path (lines 92, 370):** L-e compliance. The gate that ensures punctuation precedes reading is preserved. Do not bypass.

---

## LAW COMPLIANCE CONSENSUS

| Law | Description | Status | Basis |
|-----|-------------|--------|-------|
| **L-k** | ONE CANONICAL FORM | ✅ COMPLIANT | All text paths route through `canon.*`; confirmed by all 3 models |
| **L-e** | PUNCTUATED BEFORE READ | ✅ COMPLIANT | `sentence_ready` guard preserved at lines 92, 370 |
| **L-j** | RELEASE ON THESE BYTES | ✅ COMPLIANT | preflight + `release_auth` + attestation ordering enforced in shell |
| **L-d** | PROTECTED PREVIEW | ✅ COMPLIANT | No code touching preview logic is present in this diff |
| **SELECTION LOCK** | No recompute after selection | ✅ COMPLIANT | `transcript_fn`/`words_fn` hooks prevent post-selection recomputation |
| **SNAP LIMIT** | Cuts within sentence silence | ✅ COMPLIANT | No cut-point logic modified |
| **ONSET/TAIL** | Edge fade integrity | ✅ COMPLIANT | No edge fade logic modified |
| **CREDITS** | Credit block integrity | ✅ COMPLIANT | No credit logic modified |
| **L-a** | SIGN-OFF NAMES ALL | ✅ COMPLIANT | No sign-off logic modified |
| **L-b** | EDGE WORDS WHOLE | ✅ COMPLIANT | No edge word logic modified |
| **L-c** | DISSENT IS RIGHT UNTIL DISPROVED | ✅ COMPLIANT | No dissent logic modified |
| **M12** | Fail closed on exceptions | ✅ COMPLIANT | `preflight.py` line 666 confirmed by Gemini deep-dive |

**Final determination: ZERO LAW VIOLATIONS. All applicable laws are fully compliant.**

---

## SECURITY CONSENSUS

No security vulnerabilities were identified by any model. The following security-positive patterns were confirmed:

| Item | Status | Priority |
|------|--------|----------|
| Secret/API key non-leakage (`test_secrets_never_reach_the_output`) | ✅ Tested | Preserve |
| Hardcoded absolute path removal (no `/home/ultron/...`) | ✅ Fixed | Preserve |
| Dirty-git detection preventing untracked code from running | ✅ Tested | Preserve |
| Foreign-job detection before GPU acquisition | ✅ Validated (Gemini) | Preserve |
| Fail-closed preflight (exception = failure, not pass) | ✅ Confirmed | Preserve |

**Security consensus: No vulnerabilities. Positive security posture confirmed.**

---

## WORLD-CLASS GAP CONSENSUS

*Items mentioned by 2+ models as missing from a truly world-class implementation:*

**None identified by 2+ models.** Both cycles produced no gap findings meeting the 2-model threshold. The combined intelligence of three models across two review cycles found nothing missing from the feature at the world-class level, given the scope of this diff.

The single architectural observation (Grok's "closed regression loop") was noted by only one model and is a descriptive strength, not a gap.

**Implication:** The feature is complete as scoped. Any future enhancements (e.g., dashboard for backtest history, automated nightly backtest runs, or Whisper model pinning to prevent silent accuracy drift) would be product extensions, not gaps in this delivery.

---

## FINAL ACTION PLAN (sorted by consensus priority)

| Priority | Change | File:Line | Models | Why |
|----------|--------|-----------|--------|-----|
| **P0 CRITICAL** | *(none)* | — | — | No defects found across 2 cycles × 3 models |
| **P1 HIGH** | *(none)* | — | — | No high-priority changes required |
| **P2 MEDIUM** | Fix inline comment imprecision: `# HEAD pushed` → `# no local commits ahead of upstream` | `preflight.py:629` | unique (Gemini) | Prevents future misreading of the git ancestry check; zero-risk, one-line change |
| **P2 MEDIUM** | Add code comment on `align_quote` token offset re-mapping explaining the sub-window → full-transcript index translation | `editorial_select.py:25` | unique (Gemini) | Protects subtle correct logic from being "simplified" in future refactors |
| **P2 MEDIUM** | Add `exit 70` and `9>&-` semantics to the pipeline runbook / ops documentation | `docs/` | unique (Gemini) | These non-obvious shell patterns need documentation so on-call engineers understand failure modes |
| **P2 MEDIUM** | Add ADR or gospel note: "backtest + preflight = closed regression loop for sentence laws" | `docs/gospels/` or `docs/adr/` | unique (Grok) | Captures architectural intent; prevents future changes from breaking the loop unknowingly |

---

## CYCLE 2 VERDICT

**PRODUCTION READY. No blockers.**

After six independent model reviews (three models × two cycles), this changeset has accumulated zero defects, zero law violations, and zero security findings. Every substantive observation was either a confirmed strength or a low-risk documentation note (P2).

The feature achieves its stated goals:
- **L-k enforcement** via centralized `canon.py`
- **L-j / M12 enforcement** via `preflight.py` and shell script hardening
- **L-e preservation** via retained `sentence_ready` guard
- **Regression safety** via backtest framework with frozen inputs

The P2 items (comment fix, code annotation, ops documentation, ADR note) are strongly recommended for long-term maintainability but are not blockers. They can be bundled into a documentation commit immediately after merge.

**Absolute final blocker: None.**

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/PULSE_SENTENCE_LAW_GOSPEL.md.
Read ~/protocol_pulse/docs/audits/pulse-sentence-law_CONSENSUS_C2.md.

This is the FINAL PASS for pulse-sentence-law.
The first build was reviewed by 3 independent AI models across 2 cycles.
No P0 or P1 items were found. Implement all P2 items (documentation and
comment quality only — zero logic changes).

PRIORITY ACTION PLAN:

P2 | Fix comment: "# HEAD pushed" → "# no local commits ahead of upstream"
   | preflight.py:629 | unique (Gemini) | prevents misreading of git ancestry check

P2 | Add explanatory comment on align_quote token offset re-mapping
   | editorial_select.py:25 | unique (Gemini)
   | Comment must explain: indices are relative to the sub-window slice,
   | not the full transcript array; re-mapping back to full indices is intentional.

P2 | Add ops runbook entry for pulse_check_run.sh documenting:
   | - exit 70 = run_fresh exited 0 but no final video files found
   | - 9>&- = lock file descriptor closed before fork to prevent orphan deadlock
   | docs/runbook/ or equivalent | unique (Gemini)

P2 | Add ADR or gospel note capturing: backtest + preflight = closed
   | regression loop — future sentence-law violations are detectable before
   | any render. Document which files close the loop and what breaks it.
   | docs/gospels/ or docs/adr/ | unique (Grok)

VALIDATED (do NOT touch — all 3 models confirmed excellent across 2 cycles):
- canon.py centralization: all text paths through canon.canon_tokens /
  canon.canon / canon.canon_aligned — do not add bypass paths
- transcript_fn / words_fn hook signature in editorial_select.py:54,92-98
- preflight.py:666 fail-closed exception handler — do not weaken
- pulse_check_run.sh ordering: preflight → run_fresh → release_auth → attestation
- 9>&- file descriptor management at lines 241, 250, 259
- exit 70 on missing finals at lines 266-269
- TestWrapper shell integration test — do not delete or mock
- test_secrets_never_reach_the_output — must remain in suite
- All repo-relative sys.path fixes — do not reintroduce absolute paths
- sentence_ready guard at editorial_select.py:92,370

After implementing: regression_test.sh must show zero FAILs.
git add -A && git commit -m "feat(pulse-sentence-law): post-audit pass — consensus documentation improvements"
git push origin combo-letterbox-quoteonly-v2
```

---

# WINNER DETERMINATION

# WINNER: **Gemini**

Gemini delivered the highest-quality analysis across all four criteria: it was the only model to independently surface the `9>&-` file-descriptor hygiene pattern, the exit-70 fail-closed logic, the `TestWrapper` integration-test layer, and the secrets-never-leaked security test — concrete, technically precise findings that neither GPT-4o nor Grok identified in Cycle 1. Its recommendations were specific and implementable (name the exact lines, explain the mechanism, prescribe preservation in documentation), it covered the shell orchestration layer that the other two models effectively skipped, and every finding it made in Cycle 1 was validated correct in Cycle 2 without retraction or score revision.

---

# FINAL SECOND-PASS PRIORITY LIST

## P0 — CRITICAL (block ship)
*None.* All three models confirmed zero blocking defects across both cycles.

---

## P1 — HIGH (implement before next production run)

### P1-A: Document and protect `9>&-` lock-FD pattern
**Source:** Gemini (Cycle 1, unique); confirmed by consensus as a validated strength  
**Action:** Add an inline comment block in `pulse_check_run.sh` at lines 241, 250, 259 explaining that `9>&-` closes the inherited lock file descriptor in child processes to prevent orphan-held deadlocks. Add a linter/CI guard (e.g., a `grep` assertion in the test suite) that fails if `9>&-` is removed from those lines in a future refactor. This pattern must not be silently dropped.

### P1-B: Document and protect exit-70 fail-closed sentinel
**Source:** Gemini (Cycle 1, unique); confirmed by consensus  
**Action:** Add a comment at lines 266–269 of `pulse_check_run.sh` naming this pattern explicitly: *"exit 70 = pipeline reported success but produced no deliverable — treat as hard failure."* Add a corresponding test assertion in `test_preflight.py` (or a new `test_shell_integration.py`) that mocks a zero-exit `run_fresh.py` with absent output files and asserts the wrapper exits 70, not 0. Currently this logic is tested implicitly at best.

---

## P2 — MEDIUM (implement within sprint)

### P2-A: Promote `TestWrapper` coverage to named regression suite
**Source:** Gemini (Cycle 1); partially noted in Cycle 2 self-reviews  
**Action:** Isolate the `TestWrapper` class in `test_preflight.py` into its own file (`test_shell_wrapper.py`) with a CI tag (`@pytest.mark.integration`) so it runs in a separate stage that has shell access. As currently structured it may be silently skipped in environments where subprocess shell invocation is restricted, giving false green on the integration layer.

### P2-B: Explicitly enumerate law-coverage in test docstrings
**Source:** Structural gap noted by all three models implicitly — no model found a test that names the law it enforces  
**Action:** For each test in `test_backtest.py` and `test_preflight.py`, add a one-line docstring of the form `# Enforces: L-k ONE CANONICAL FORM` or `# Enforces: L-j RELEASE ON THESE BYTES`. This makes future audits machine-readable and prevents a law from losing its test coverage invisibly during refactors.

### P2-C: Document the closed regression loop as an architectural invariant
**Source:** Grok (Cycle 2, new structural observation)  
**Action:** Add a `ARCHITECTURE.md` section (or inline in `README.md`) stating explicitly: *"The backtest + preflight combination forms a closed regression loop. Any change that would cause a sentence-law violation must be detectable by `backtest.py` before `preflight.py` permits a live render."* This ensures the invariant is preserved intentionally, not accidentally.

---

## P3 — LOW (backlog / nice-to-have)

### P3-A: Add a `canon.py` conformance test at the module boundary
**Source:** Implied by all three models' praise of the canonical-form migration  
**Action:** Add a parameterized test that feeds identical inputs through the old inline regex paths (preserved as reference strings in the test) and the new `canon.*` calls, asserting byte-for-byte identical outputs. This guards against a future `canon.py` refactor silently changing normalization behavior.

### P3-B: Surface `offline_words` priority order in a decision-log comment
**Source:** Gemini noted the correct prioritization in `backtest.py` lines 365–376  
**Action:** Add a comment block above the priority chain in `backtest.py` that enumerates the fallback order explicitly: `1. offline_words → 2. saved transcript → 3. error`. Prevents a future contributor from reordering the chain without understanding why the order is load-bearing.

---

## IMPLEMENTATION ORDER SUMMARY

| Priority | Item | Owner Hint | Effort |
|----------|------|-----------|--------|
| P1-A | Protect `9>&-` with comment + CI guard | DevOps / shell owner | 1 hr |
| P1-B | Test exit-70 sentinel explicitly | Test author | 2 hr |
| P2-A | Isolate `TestWrapper` → integration suite | Test author | 1 hr |
| P2-B | Law-coverage docstrings on all tests | Any reviewer | 2 hr |
| P2-C | Document closed regression loop | Tech lead | 1 hr |
| P3-A | `canon.py` conformance test | Test author | 2 hr |
| P3-B | Priority-order comment in `backtest.py` | Backtest owner | 30 min |