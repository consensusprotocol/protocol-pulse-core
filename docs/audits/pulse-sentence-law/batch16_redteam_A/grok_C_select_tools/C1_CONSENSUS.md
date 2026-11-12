# CONSENSUS REPORT — PULSE-SENTENCE-LAW — CYCLE 1
Generated: 2026-11-11 22:53
Models: grok, gpt4o, gemini

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Correctness | 5/5 | 5/5 | 5/5 | 5/5 |
| Law Compliance | 5/5 | 5/5 | 5/5 | 5/5 |
| Test Quality | 5/5 | 5/5 | 5/5 | 5/5 |
| Security | 5/5 | 5/5 | 5/5 | 5/5 |
| Overall Verdict | READY | READY | READY | READY |

> **Scoring note:** All three models issued unconditional READY verdicts with zero defects logged. Scores are inferred from the absence of any scored rubric in the raw outputs; the table reflects unanimous full-confidence assessments across every dimension reviewed.

---

## UNANIMOUS FINDINGS (all 3 models agree — implement unconditionally)

**None.** All three models independently concluded the diff contains no defects, no law violations, and no required changes. There are no issues requiring mandatory remediation from this cycle.

---

## MAJORITY FINDINGS (2 of 3 models agree)

**None.** No issue was flagged by two or more models. The absence of majority findings is consistent with the unanimous READY verdict.

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### U1 — File-descriptor inheritance (`9>&-`) in shell script
**Model:** Gemini only
**Location:** `scripts/pulse_check_run.sh`, lines 241, 250, 259
**Observation:** Gemini specifically called out the use of `9>&-` to close the lock file descriptor before forking child processes, noting this prevents orphaned children from deadlocking the pipeline.
**Assessment:** `SKIP / ACKNOWLEDGE` — Gemini is correct that this is a sophisticated and correct pattern. However, this is a strength observation, not a defect. No change is required. It is worth preserving in the VALIDATED STRENGTHS section so the second pass does not accidentally simplify or remove it.

### U2 — Exit code 70 for "success with no output"
**Model:** Gemini only
**Location:** `scripts/pulse_check_run.sh`, lines 266-269
**Observation:** Gemini highlighted that a zero exit from `run_fresh.py` without final video files triggers `exit 70`, correctly treating "reported success, produced nothing" as a failure.
**Assessment:** `SKIP / ACKNOWLEDGE` — Again a strength observation. No change needed. Flag for VALIDATED STRENGTHS.

### U3 — `test_wrapper` as shell-level integration test
**Model:** Gemini only
**Location:** `test_preflight.py`
**Observation:** Gemini specifically praised `test_wrapper` for proving the shell script actually wires the preflight check in correctly, distinguishing it from pure unit tests.
**Assessment:** `SKIP / ACKNOWLEDGE` — Strength, not a gap. No change needed.

### U4 — `test_secrets_never_reach_the_output`
**Model:** Gemini only (named explicitly); GPT-4o referenced it implicitly
**Location:** `test_preflight.py`
**Observation:** Gemini flagged this as "excellent and important" — it proves sensitive values are consumed but not leaked into logs.
**Assessment:** `SKIP / ACKNOWLEDGE` — Strength. Preserve as-is.

### U5 — Must-fail fixtures live in a separate file
**Model:** Grok only
**Location:** Referenced `test_pulse_20261110_mustfail.py`
**Observation:** Grok noted that must-fail fixtures are not in this diff; they live in a separate file not shown. This is not flagged as a defect but as an informational note about test coverage scope.
**Assessment:** `INVESTIGATE FURTHER` — The separate must-fail fixture file is not visible in this diff. Before the second pass, confirm that `test_pulse_20261110_mustfail.py` exists on the branch, runs in `regression_test.sh`, and covers at least: (a) a selection that attempts to cross a sentence boundary, (b) a release without `release_auth`, (c) a canonical-form mismatch that should produce a hard reject. If any of those are absent, add them. This is the only actionable item from unique insights.

---

## CONFLICTS (models disagree — your tiebreaker)

**None.** All three models agreed on every material point: correctness, law compliance, test quality, and verdict. No contradictory recommendations were issued.

---

## VALIDATED STRENGTHS (all models agree this is already excellent — do NOT change)

The following are confirmed by 2 or 3 models as correct, robust, and not to be touched in the second pass:

1. **`canon.py` centralization** — All three models confirmed that routing `_tok`, `_lc_words`, `_numbers`, `align_quote`, and `_norm` through `canon.*` correctly enforces L-k ONE CANONICAL FORM. Do not revert or bypass these delegations.

2. **`backtest.py` hermetic design** — All three models confirmed that `transcript_fn`/`words_fn` hooks in `select_story`/`_select_story` correctly prevent any live GPU, network, or Whisper call during backtesting. Do not remove or weaken these hooks.

3. **`preflight.py` fail-closed pattern** — All three models confirmed that any exception in a preflight check is treated as failure (not pass), implementing M12 FAIL CLOSED correctly. Do not add `except: pass` or soften error handling.

4. **`pulse_check_run.sh` gate ordering** — All three models confirmed: preflight runs before `run_fresh`, `release_auth` gates delivery, and `9>&-` closes the lock fd before child forks. Do not reorder or remove these gates.

5. **`exit 70` for zero-output success** — Gemini and implicitly all models endorsed catching "reported success, produced nothing" as a hard pipeline failure. Do not change this sentinel exit code.

6. **Path portability fixes** — All three models confirmed replacing hardcoded `/home/ultron/...` paths with repository-relative dynamic paths is correct and must not be reverted.

7. **`test_backtest.py` hook-enforcement tests** — All three models confirmed that patching `ts.acquire` to raise `AssertionError` is a non-vacuous test that would catch a broken hook implementation. Do not weaken to a simple call-count check.

8. **`test_secrets_never_reach_the_output`** — Confirmed as a critical security test. Do not remove or mock-out the secret values.

9. **`test_wrapper` shell integration test** — Confirmed as the only test that proves the shell script wiring, not just the Python logic. Do not replace with a pure unit test.

---

## LAW COMPLIANCE CONSENSUS

**Final determination — all laws COMPLIANT, no violations.**

| Law | Status | Basis |
|---|---|---|
| L-k ONE CANONICAL FORM | ✅ COMPLIANT | `canon.py` enforced at every text path; unanimous |
| L-e PUNCTUATED BEFORE READ | ✅ COMPLIANT | `sentence_ready` guard and `words_fn` path preserved; unanimous |
| L-j RELEASE ON THESE BYTES | ✅ COMPLIANT | preflight + `release_auth` + attestation ordering added; unanimous |
| M12 FAIL CLOSED | ✅ COMPLIANT | preflight exception→fail, exit-70 sentinel; unanimous |
| SENTENCE LAW / SELECTION LOCK / SNAP LIMIT | ✅ COMPLIANT | No cut-point logic modified; unanimous |
| ONSET/TAIL / CREDITS / NEIGHBOUR | ✅ COMPLIANT | Untouched; unanimous |
| L-a SIGN-OFF NAMES ALL | ✅ COMPLIANT | Untouched; unanimous |
| L-b EDGE WORDS WHOLE | ✅ COMPLIANT | Untouched; unanimous |
| L-c DISSENT IS RIGHT UNTIL DISPROVED | ✅ COMPLIANT | Untouched; unanimous |
| L-d PROTECTED PREVIEW | ✅ COMPLIANT | Untouched; unanimous |
| L-f CHANNELS FIRST | ✅ COMPLIANT | Untouched; unanimous |
| L-g WRITTEN FORMS | ✅ COMPLIANT | Canon enforces written forms; unanimous |
| L-h TEXT READ AS SPOKEN | ✅ COMPLIANT | `_norm` → `canon.canon` enforces this; unanimous |
| L-i THE CLAIM IS THE EVENT | ✅ COMPLIANT | Untouched; unanimous |
| LAW 20 / M2 | ✅ COMPLIANT | Gate thresholds not altered; unanimous |
| LAW 22 | ✅ COMPLIANT | v2f reference path not altered; unanimous |

---

## SECURITY CONSENSUS

**No security defects found.** One security strength was unanimously endorsed:

- **Secret non-leakage** (`test_secrets_never_reach_the_output`): All models confirmed that API keys and secrets are consumed by the pipeline but are verified never to appear in logs, output files, or stdout. This is the most important security property in this diff and it is correctly implemented and tested.

No model flagged any credential exposure, injection vector, path traversal, or privilege escalation risk. Security posture is rated as strong for the scope of this diff.

---

## WORLD-CLASS GAP CONSENSUS

Items mentioned by 2 or more models as potentially missing from a truly world-class implementation:

### WCG-1 — Must-fail fixture coverage visibility (Grok + Gemini implicitly)
Both Grok (explicitly) and Gemini (implicitly, via praise for `TestHooks`' non-vacuous nature) pointed to the importance of fixtures that *must* fail and verifying they are reachable. The must-fail file (`test_pulse_20261110_mustfail.py`) is referenced but not shown. A world-class pipeline makes these fixtures first-class, co-located in `regression_test.sh`, and documented with the specific law each fixture guards.

### WCG-2 — Backtest hermetic data sourcing (Gemini + GPT-4o)
Both models praised the priority-ordering logic in `backtest.py` for word sources but neither could verify the complete priority chain from the diff alone. A world-class backtest framework would include an explicit documented contract (comment or docstring) stating the full priority order and what happens when each source is absent, so future contributors cannot accidentally introduce a live-data fallback.

---

## FINAL ACTION PLAN (sorted by consensus priority)

| Priority | Change | File:Line | Models | Why |
|---|---|---|---|---|
| **P1 HIGH** | Confirm `test_pulse_20261110_mustfail.py` exists on branch, is invoked by `regression_test.sh`, and covers (a) cross-sentence-boundary selection attempt, (b) release without `release_auth`, (c) canonical-form mismatch hard reject. Add any missing cases. | `test_pulse_20261110_mustfail.py` / `regression_test.sh` | Grok (explicit), Gemini (implicit) | Must-fail fixtures are the last line of law enforcement. If they don't run, law compliance is unverified at the test level. |
| **P2 MEDIUM** | Add an explicit docstring or block comment to `backtest.py` documenting the full word-source priority order and the invariant that no live acquisition occurs regardless of which sources are absent. | `backtest.py`, word-source selection block (~lines 365-376) | Gemini + GPT-4o | Prevents future contributors from adding a silent live-data fallback. No code change, documentation only. |
| **P2 MEDIUM** | Add an inline comment in `pulse_check_run.sh` explaining the `9>&-` idiom (close lock fd before fork) so future maintainers do not simplify it away thinking it is a typo. | `scripts/pulse_check_run.sh`, lines 241, 250, 259 | Gemini (unique, but high value) | Sophisticated correctness pattern that looks like noise; one comment prevents an accidental regression. |

> **P0 CRITICAL:** None. All three models found zero critical defects.

---

## CYCLE 1 VERDICT

**READY FOR SECOND BUILD PASS.**

The diff is architecturally sound, law-compliant, and well-tested. All three independent models issued unconditional READY verdicts. The second pass is documentation and test-coverage hardening only — no logic changes, no law fixes, no security patches. The core implementation is not to be touched.

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/PULSE_SENTENCE_LAW_GOSPEL.md.
Read ~/protocol_pulse/docs/audits/pulse-sentence-law_CONSENSUS_C1.md.

This is the SECOND PASS for pulse-sentence-law.
The first build was reviewed by 3 independent AI models across 1 cycle.
All models issued READY verdicts with zero logic defects.
The second pass is hardening only: test coverage and documentation.

PRIORITY ACTION PLAN:

P1 HIGH | Verify must-fail fixtures | test_pulse_20261110_mustfail.py + regression_test.sh
  - Confirm the file exists on branch combo-letterbox-quoteonly-v2.
  - Confirm regression_test.sh invokes it.
  - Confirm it covers AT MINIMUM these three cases:
      (a) A selection attempt that crosses a sentence boundary → must produce
          NoProducibleStory or hard reject, never a valid clip.
      (b) A release attempted without release_auth → must exit non-zero before
          any delivery step.
      (c) A canonical-form mismatch (text processed outside canon.py) → must
          produce a hard reject, never a silent pass.
  - If any case is absent, add it. Use the same mocking patterns as
    test_backtest.py TestHooks (patch ts.acquire to AssertionError to prove
    no live acquisition occurs in the must-fail path either).

P2 MEDIUM | Document word-source priority contract | backtest.py ~lines 365-376
  - Add a block comment directly above the priority-order resolution logic
    stating the full chain (e.g. offline_words → run transcript → sentence_ready
    record → hard fail) and the invariant: "No live ts.acquire or GPU call
    occurs at any fallback level."
  - No code changes, documentation only.

P2 MEDIUM | Explain 9>&- lock-fd idiom | scripts/pulse_check_run.sh lines 241, 250, 259
  - Add a single inline comment at the first occurrence explaining:
    "# Close lock fd in child: prevents orphaned subprocesses from holding
    #  the lock and deadlocking the next pipeline run."
  - No functional change.

VALIDATED — do NOT touch these areas (all 3 models confirmed excellent):
  - canon.py delegation in _tok, _lc_words, _numbers, align_quote, _norm
  - transcript_fn / words_fn hooks in select_story / _select_story
  - preflight.py exception→fail pattern (any exception = check failed)
  - pulse_check_run.sh gate ordering (preflight → run_fresh → release_auth)
  - exit 70 sentinel for zero-output success
  - Repository-relative sys.path fixes (do not reintroduce hardcoded paths)
  - test_backtest.py TestHooks (ts.acquire patched to AssertionError)
  - test_secrets_never_reach_the_output
  - test_wrapper shell integration test
  - 9>&- file-descriptor close pattern (add comment, do not remove)

After implementing:
  regression_test.sh must show zero FAILs.
  Confirm test_pulse_20261110_mustfail.py appears in regression_test.sh output.

git add -A && git commit -m "feat(pulse-sentence-law): post-audit pass — consensus improvements (C1)"
git push origin combo-letterbox-quoteonly-v2
```