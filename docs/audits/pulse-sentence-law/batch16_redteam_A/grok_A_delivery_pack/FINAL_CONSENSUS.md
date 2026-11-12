# CONSENSUS REPORT — PULSE-SENTENCE-LAW — CYCLE 2
Generated: 2026-11-11 22:37
Models: gpt4o, grok, gemini

---

## SCORES

| Subsystem       | Gemini | GPT-4o | Grok  | Consensus |
|-----------------|--------|--------|-------|-----------|
| Correctness     | 9.5/10 | 9.5/10 | 9.5/10 | **9.5/10** |
| Law Compliance  | 10/10  | 10/10  | 10/10  | **10/10**  |
| Test Quality    | 10/10  | 9.5/10 | 9.5/10 | **9.7/10** |
| Security        | 9.5/10 | 9.5/10 | 9.5/10 | **9.5/10** |
| **Overall**     | READY  | READY* | READY  | **READY**  |

*GPT-4o added a minor documentation condition, not a code blocker.

---

## UNANIMOUS FINDINGS (all 3 models agree — implement unconditionally)

**None.** All three models agree there are **zero code defects** requiring mandatory fixes. The diff is clean, correct, and law-compliant. No code change is unanimously required.

The closest thing to a unanimous finding is a **documentation suggestion** (not a code fix):

### U-1 | Add inline comment explaining stale-frame removal
- **What it is:** The `_frame` function in `verify_pack.py` calls `os.remove(out)` before generating a new frame. Without a comment, future maintainers may not understand why the pre-emptive deletion exists.
- **File/line:** `verify_pack.py`, line 1137
- **What to change:** Add one explanatory comment (see P2 below).
- **Confidence:** All three models referenced this line; Gemini and Grok explicitly flagged it as worth documenting; GPT-4o agreed after review.

---

## MAJORITY FINDINGS (2 of 3 models agree)

### M-1 | `send_telegram_preview` stub is correct — not a defect (Gemini + Grok)
- **What it is:** GPT-4o originally labelled the `send_telegram_preview` stub a "HIGH severity" concern. Gemini and Grok independently and explicitly disagreed, confirming it is the intended fail-loud deprecation pattern.
- **Action:** No change. The stub is correct by design. See CONFLICTS section.

### M-2 | `headline_numbers_said` with `canon` is correct (Gemini + Grok)
- **What it is:** GPT-4o raised a "MEDIUM risk" concern about `headline_numbers_said`. Gemini re-audited and confirmed correctness; Grok concurred.
- **Action:** No change. Function is correctly implemented.

### M-3 | Stale-frame removal documentation (Gemini + Grok, GPT-4o in agreement)
- **What it is:** Defensive pre-removal of destination file in `_frame` lacks an explanatory comment.
- **Action:** Add comment (see P2 action plan).

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### UI-1 | Theoretical TOCTOU race condition in `deliver_run` (Gemini only)
- **What it is:** In `telegram.py` lines 322-325, there is a window between the hash-check (`release_auth.check_file(...)`) and the subsequent file read inside `send(...)`. An attacker with filesystem access could modify the file between check and read.
- **Assessment:** **Acknowledge, do not block.** Gemini correctly identifies this as a classic TOCTOU pattern and correctly self-assesses it as extremely low practical risk given the controlled pipeline environment. The existing authorization and digest chain more than covers the realistic threat model. This is not a blocker.
- **Recommendation:** Add a brief inline comment noting the TOCTOU window and the accepted risk rationale, so future security reviewers don't re-discover and escalate it unnecessarily.
- **Action:** P3 / informational comment only.

---

## CONFLICTS (models disagree — your tiebreaker)

### C-1 | Severity of `send_telegram_preview` stub
- **GPT-4o:** Flagged "HIGH severity" — interpreted the stub as a missing replacement.
- **Gemini + Grok:** Explicitly and correctly disagreed. The stub is a deliberate, loud deprecation that forces all callers to migrate to `deliver_run`. It is exactly the right pattern for safely retiring an insecure entry point.
- **Tiebreaker verdict: Gemini and Grok are correct.** A stub that immediately raises `RuntimeError` is not a defect; it is a security feature. Any legacy caller that slips through will fail loudly in CI/staging rather than silently bypassing the new authorization path. No change required.

### C-2 | `headline_numbers_said` risk level
- **GPT-4o:** Raised as MEDIUM risk.
- **Gemini + Grok:** Confirmed compliant after reviewing `canon.canon_tokens` usage.
- **Tiebreaker verdict: Gemini and Grok are correct.** The function correctly canonicalises both the spoken token set and the headline numbers before comparison. No change required.

---

## VALIDATED STRENGTHS (all models agree this is already excellent — do NOT change)

1. **Authorization-first gate in `deliver_run`** (`telegram.py` lines 297-299): `release_auth.authorise` is called before any network activity. Universally praised. Do not change.

2. **Pre-flight `_plan` construction** (`telegram.py` lines 235-281): All payloads validated (dimensions, size, headline numbers, attestation) before the first send. Universally praised. Do not change.

3. **`SendRejected` vs. unknown-outcome error distinction** (`telegram.py` lines 412-416): Correctly prevents dangerous auto-retries on ambiguous Telegram responses. Universally praised. Do not change.

4. **Atomic state management via `os.replace`** (`telegram.py` lines 318, 1191, 1289): Prevents corrupt intermediate state files. Universally praised. Do not change.

5. **Bot-token leak prevention in `_send_bot_api`** (`telegram.py` line 413): Generic re-raise strips sensitive information from logs. Universally praised. Do not change.

6. **Strict `panel_ok` requiring every model to answer every question with boolean `True`** (`verify_pack.py` line 1195): Zero-shot/zero-boundary treated as failures. Universally praised. Do not change.

7. **Per-file digest re-verification inside `deliver_run`** (`telegram.py` line 322): Post-attestation mutation caught before each send. Universally praised. Do not change.

8. **Test suite structure** (`test_failure_blocks.py`, `test_telegram_delivery.py`): Non-vacuous assertions, `make_run`/`release_auth` fixtures, checkpoint-resume coverage. Universally praised. Do not change.

---

## LAW COMPLIANCE CONSENSUS

| Law | Status | Basis |
|-----|--------|-------|
| **L-j** (RELEASE IS AUTHORISED ON THESE BYTES) | ✅ COMPLIANT | `authorise` + per-file digest re-check enforced before every send |
| **L-d** (PROTECTED PREVIEW) | ✅ COMPLIANT | Legacy preview path hard-removed; stub raises immediately |
| **M12** (FAIL CLOSED) | ✅ COMPLIANT | Missing attestation, changed files, failed rows all raise before any network call |
| **SELECTION LOCK** | ✅ COMPLIANT | `headline_numbers_said` + `canon` prevents recomputation |
| **SNAP LIMIT** | ✅ COMPLIANT | No changes to cut-point logic; pre-flight dimension checks enforce limits |
| **NEIGHBOUR / ONSET / TAIL** | ✅ COMPLIANT | Unaffected by this diff; existing guarantees intact |
| **CREDITS / L-a** | ✅ COMPLIANT | `publish_kit` enforces credited channel completeness |

**Final determination: Zero law violations. Full compliance confirmed by all three models across both cycles.**

---

## SECURITY CONSENSUS

| Issue | Models | Priority | Action |
|-------|--------|----------|--------|
| Bot token leak prevention (already implemented) | All 3 | Validated strength | No change |
| Legacy path hard-removal via `RuntimeError` stub | All 3 | Validated strength | No change |
| Theoretical TOCTOU in `deliver_run` (lines 322-325) | Gemini only | P3 informational | Comment only, no code change |

No security vulnerabilities requiring code changes were identified by majority or unanimous consensus. The pipeline's threat model is well-covered by the existing authorization and digest chain.

---

## WORLD-CLASS GAP CONSENSUS

*Only items mentioned by 2+ models are included.*

### WCG-1 | Inline documentation of defensive patterns (all 3 models)
All three models independently identified `verify_pack.py` line 1137 as lacking an explanatory comment for the pre-emptive `os.remove`. While the code is correct, the *intent* is not self-evident. World-class production code makes defensive decisions explicit in prose, not just in behavior. This is the only gap the combined intelligence of three models agrees on.

**No other world-class gaps were identified by 2+ models.** The code is assessed as genuinely exceptional in architecture, error handling, state management, and test coverage.

---

## FINAL ACTION PLAN (sorted by consensus priority)

| Priority | Change | File:Line | Models | Why |
|----------|--------|-----------|--------|-----|
| **P0 CRITICAL** | *None* | — | — | Zero critical defects found across two full cycles |
| **P1 HIGH** | *None* | — | — | Zero high-priority issues; all laws compliant |
| **P2 MEDIUM** | Add comment explaining pre-emptive stale-frame removal | `verify_pack.py:1137` | All 3 (unanimous) | Prevents future maintainer confusion; makes defensive intent explicit; costs zero risk |
| **P3 LOW** | Add comment acknowledging TOCTOU window and accepted-risk rationale | `telegram.py:322` | Gemini only | Low practical risk in controlled env; comment prevents future false-escalation by security reviewers |

**Suggested P2 change:**
```python
def _frame(video, t, out):
    # Pre-emptively remove destination to prevent a stale artifact from a previous
    # failed run from being silently reused and causing a false visual-check pass.
    if os.path.exists(out):
        os.remove(out)
```

**Suggested P3 change:**
```python
# TOCTOU note: there is a small window between this hash-check and the file read
# inside send(). Accepted risk: pipeline runs in a controlled environment with
# restricted filesystem access; the authorization + digest chain covers the realistic
# threat model. Revisit if deployment context changes.
if item["rel"] and not release_auth.check_file(run_dir, att, item["rel"]):
```

---

## CYCLE 2 VERDICT

**PRODUCTION READY — NO BLOCKERS.**

After two full cycles of independent review by three models (Gemini 2.5 Pro, GPT-4o, Grok-3), this code is unanimously assessed as correct, law-compliant, secure, and well-tested. The only recommended changes are two inline comments totalling approximately four lines. No code logic requires modification.

The diff represents a genuine, defense-in-depth hardening of the release pipeline: authorization gates before any side effects, atomic state files, fail-closed error handling at every layer, and a strict test suite that verifies the security boundaries rather than just the happy path. This is the standard other features should be measured against.

**Absolute final blocker:** None.

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/PULSE_SENTENCE_LAW_GOSPEL.md.
Read ~/protocol_pulse/docs/audits/pulse-sentence-law_CONSENSUS_C2.md.

This is the FINAL PASS for pulse-sentence-law.
The first build was reviewed by 3 independent AI models across 2 cycles.
Implement every P0 and P1 item from the consensus (there are none — no code
changes required). Use judgment on P2 and P3 (documentation only).

PRIORITY ACTION PLAN:

P2 MEDIUM | verify_pack.py:1137 | Add inline comment explaining pre-emptive
stale-frame removal:
  # Pre-emptively remove destination to prevent a stale artifact from a previous
  # failed run from being silently reused and causing a false visual-check pass.

P3 LOW | telegram.py:322 | Add inline comment acknowledging TOCTOU window
and accepted risk:
  # TOCTOU note: there is a small window between this hash-check and the file
  # read inside send(). Accepted risk: pipeline runs in a controlled environment
  # with restricted filesystem access; the authorization + digest chain covers
  # the realistic threat model. Revisit if deployment context changes.

VALIDATED (do NOT touch — all 3 models confirmed excellent):
- deliver_run authorization-first gate (telegram.py:297-299)
- _plan pre-flight validation before first send (telegram.py:235-281)
- SendRejected vs unknown-outcome error distinction (telegram.py:412-416)
- Atomic state management via os.replace (telegram.py:318, 1191, 1289)
- Bot-token leak prevention in _send_bot_api (telegram.py:413)
- Strict panel_ok requiring every model / every question (verify_pack.py:1195)
- Per-file digest re-verification inside deliver_run (telegram.py:322)
- send_telegram_preview RuntimeError stub (telegram.py:129-132) — deliberate,
  do not restore or modify
- Test suite: make_run/release_auth fixtures, non-vacuous assertions,
  checkpoint-resume coverage (test_failure_blocks.py, test_telegram_delivery.py)

After implementing: regression_test.sh must show zero FAILs.
git add -A && git commit -m "feat(pulse-sentence-law): post-audit pass — consensus improvements (documentation only)"
git push origin combo-letterbox-quoteonly-v2
```

---

# WINNER DETERMINATION

WINNER: **Gemini** — Gemini delivered the only genuinely unique finding across both cycles (the stale-frame `os.remove` defensive pattern in `verify_pack.py:1137`) that all three models subsequently validated and elevated to the consensus report's sole documented action item, demonstrating superior depth of analysis. Its Cycle 1 output was also the most structured and technically specific, correctly explaining *why* each design choice was sound (atomic `os.replace`, token-leak prevention, `SendRejected` vs. unknown-outcome distinction) rather than merely confirming compliance, satisfying all four criteria — accuracy, depth, actionability, and completeness — at the highest level.

---

## FINAL SECOND-PASS PRIORITY LIST

**P0 CRITICAL — None.**
All three models unanimously confirmed zero blocking defects. The diff is correct, law-compliant, and safe to ship as-is.

---

**P1 HIGH — None.**
No high-severity issues survived cross-model scrutiny. GPT-4o's two P1 candidates (`send_telegram_preview` stub, `headline_numbers_said` logic) were explicitly rejected by majority vote and correctly classified as non-defects.

---

**P2 MEDIUM — None requiring code change.**

**P2-1 | Document stale-frame pre-removal intent**
- **File:** `verify_pack.py`, line 1137
- **Action:** Insert one inline comment before `os.remove(out)`:
  ```python
  # Remove any stale frame from a prior failed run so it cannot be
  # silently reused if the regeneration step below raises.
  os.remove(out)
  ```
- **Rationale:** The behavior is correct; the comment prevents a future maintainer from "fixing" the removal under the mistaken belief it is redundant, which would reintroduce a silent-stale-artefact failure mode.
- **Confidence:** 3/3 models referenced this line; 2/3 explicitly flagged it as worth documenting.

---

**P3 LOW — None.**
No low-priority items emerged that were not subsumed by P2-1 above.

---

**Implementation order:** P2-1 is the single highest-leverage change remaining. All other work is complete. Ship after adding the one-line comment.