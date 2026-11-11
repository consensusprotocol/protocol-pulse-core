# CONSENSUS REPORT — PULSE-SENTENCE-LAW — CYCLE 2
Generated: 2026-11-11 08:49
Models: gpt4o, gemini (+1 failed: grok — budget exceeded)

---

## SCORES

| Subsystem       | Gemini | GPT-4o | Grok        | Consensus |
|-----------------|--------|--------|-------------|-----------|
| Correctness     | 9/10   | 7/10   | N/A (failed)| **8/10**  |
| Law Compliance  | 10/10  | 8/10   | N/A         | **9/10**  |
| Test Quality    | 10/10  | 8/10   | N/A         | **9/10**  |
| Overall Verdict | YES w/ conditions | READY w/ conditions | N/A | **YES, WITH CONDITIONS** |

> **Scoring note:** Gemini scored higher because it assessed only the code present in the diff, which is of high quality. GPT-4o weighted the feature-level incompleteness (D1, D4 unaddressed) more aggressively into the per-subsystem scores. The consensus splits the difference: the implemented code is very good; the feature boundary is the problem. Grok's failure does not alter any finding — both present models converged independently.

---

## UNANIMOUS FINDINGS (both models agree — implement unconditionally)

### U1 — Onset/Tail Defect D1 Not Addressed
- **What:** The stated feature goal included fixing clipped audio onset (D1 — first word of a clip is audibly truncated). `shot_snap.py` explicitly preserves audio with `-c:a copy`, meaning any pre-existing onset clipping passes through untouched. The fix for D1 is entirely absent from this diff.
- **File/line:** `shot_snap.py:362` (`-c:a copy`) and the broader feature specification.
- **Required change:** Either implement D1 onset-padding logic (e.g., extend audio head by a fixed guard interval before the first speech token), or formally descope D1 by adding a `# TODO(D1): onset clipping not addressed in this cycle — see ticket #XXX` comment and creating a tracking ticket. Shipping silently incomplete work breaks QA and product trust.

### U2 — Credits / Avatar Warping Defect D4 Not Addressed
- **What:** The feature description listed fixing warped credit avatars (D4) as an in-scope defect. No changes to any credit, avatar, or image-processing subsystem appear in the diff.
- **File/line:** N/A — absence of changes.
- **Required change:** Same choice as U1: implement D4, or explicitly descope it with a `TODO(D4)` comment, a tracking ticket, and a note in the feature changelog that D4 ships separately. Do not let the feature land claiming to fix D4.

### U3 — Error Messages Are Under-Descriptive
- **What:** Both models flagged that error strings in two locations lack enough context to diagnose failures quickly in production or CI.
- **Locations and required changes:**
  - `replay.py:88` — The `SystemExit` for a pre-existing destination directory should include the actual path: `f"STOP: Replay destination {dst} already exists. Remove it manually or choose a different stamp."`
  - `shot_snap.py:365` — The `RuntimeError` for a frame-count mismatch should include expected vs. actual: `f"shot_snap changed frame count of {clip!r}: expected {n}, got {frame_count(part)}"`

---

## MAJORITY FINDINGS (2 of 2 models agree)

All unanimous findings above are also majority findings (2/2). No additional majority-only tier exists given only two models completed the cycle; every shared finding is already captured in the UNANIMOUS section.

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### I1 — `word_diff.py` Decimal Normalization: Silent Bug in Old Code (Gemini only)
- **What:** Gemini performed the deepest analysis of the `word_diff.py` decimal change. The old code could cause `5.5%` → `5 5 percent` → token-collapsed to `5%` via deduplication, making `5.5%` and `5%` appear identical to the differ. This is a correctness defect in the old code, not merely an enhancement. The new `_decimals` function that maps `5.5` → `5p5` before further processing is a critical bug fix.
- **Assessment: IMPLEMENT (already implemented — confirm in test coverage).** This insight does not require a new code change; the fix is already in the diff. However, it should be explicitly noted in the commit message and a regression test should confirm the `5.5% vs 5%` case is now detected as a difference. If that specific case lacks a test fixture, add one.
- **File/line:** `word_diff.py:832–859`

### I2 — Delivery Script Policy Change: `HOLD` Verdicts Silently Dropped (Gemini only)
- **What:** The change in `scripts/pulse_check_run.sh:891–896` stops delivering `HOLD` verdicts to the Telegram review channel. The comment states this is per-orchestrator instruction. While technically correct by instruction, this is a major operational policy change that alters the review workflow for the entire team.
- **Assessment: INVESTIGATE FURTHER.** This is not a code defect but a workflow governance gap. Before shipping, confirm in writing (Slack/ticket) that the product owner and QA lead have signed off on `HOLD` verdicts being silently suppressed rather than surfaced to reviewers. If that sign-off exists, add a comment citing the decision: `# Policy: HOLD is not surfaced to review channel per orchestrator decision YYYY-MM-DD`. If sign-off does not exist, escalate before merging.
- **File/line:** `scripts/pulse_check_run.sh:891–896`

---

## CONFLICTS (models disagree — tiebreaker)

### C1 — Severity of Feature Incompleteness vs. Code Correctness Scores
- **Gemini** held Correctness at 9/10 and Law Compliance at 10/10, reasoning that the code *present* is excellent and the incompleteness is a scope/project issue, not a code defect.
- **GPT-4o** dropped Correctness to 7/10 and Law Compliance to 8/10, absorbing feature-level omissions into per-subsystem scores.
- **Tiebreaker ruling:** Gemini's framing is more precise for a code audit: score the code on the page, flag scope gaps separately. However, GPT-4o's more conservative overall verdict is the correct operational posture — the feature **cannot ship as-is** regardless of which model's scoring rubric you prefer. The consensus scores (8/10, 9/10) reflect the high quality of implemented code while the conditional verdict reflects the real-world ship gate. Neither model is wrong; they are using different rubric scopes.

### C2 — Test Quality Score (10/10 vs. 8/10)
- **Gemini** raised Test Quality to 10/10, noting that must-fail fixtures derived from real production incidents represent a mature testing philosophy.
- **GPT-4o** dropped it to 8/10, penalizing the absence of tests covering D1 and D4.
- **Tiebreaker ruling:** Both are correct in their domain. Gemini is right that the existing tests are exceptional. GPT-4o is right that the gaps around D1/D4 are real. Consensus 9/10 is accurate: the tests for what was built are outstanding; tests for what was not built are, by definition, missing.

---

## VALIDATED STRENGTHS (all models agree — do NOT touch)

1. **`stand_alone.py` — Fail-Closed Logic (M12 Compliance):** The `opener` and `topical` functions correctly fail to `False` when a scorer verdict is required but unavailable. This is the correct editorial safety posture and is robustly implemented.

2. **`shot_snap.py` — Frame-Count Integrity Check:** The post-encode assertion that the frame count is unchanged (`line 363`) is an excellent, non-obvious guard against A/V desync. This should be preserved exactly as written.

3. **`shot_snap.py` — `plan()` Safety Guard:** The `if head >= tail: return` guard prevents zero-duration or negative-duration clip creation. Do not remove this.

4. **`word_diff.py` — `_decimals` Token Normalization:** The new function and its integration into `norm()` are a correct, elegant fix for a subtle silent-failure mode in the old code. Leave this as implemented.

5. **`stand_alone.py` — `check_edl` Scorer Exception Handling:** Catching scorer unavailability and flagging an error (rather than silently passing) is exactly correct per M12. Leave this pattern in place.

6. **`replay.py` — `make_copy` with `os.link`:** Using hard links for large source files is the right performance choice. The logic to remove stale outputs before re-running is correct. Do not change the structural approach.

7. **Test fixtures from production incidents:** The must-fail approach using real incident data is world-class. Do not rationalize these away; they are the most valuable tests in the suite.

---

## LAW COMPLIANCE CONSENSUS

| Law | Status | Notes |
|-----|--------|-------|
| SENTENCE LAW | ✅ COMPLIANT | `shot_snap.py` enforces shot boundaries; `stand_alone.py` enforces opener/topical rules. Both correct. |
| SELECTION LOCK | ✅ COMPLIANT | No recomputation of expected words post-selection. Confirmed by both models. |
| SNAP LIMIT | ✅ COMPLIANT | Cuts only moved within silence between sentences. |
| ONSET/TAIL | ⚠️ PARTIALLY COMPLIANT | Tail is handled. Onset (D1) is not addressed. Feature is incomplete against this law. |
| M12 FAIL CLOSED | ✅ COMPLIANT | Fail-closed is correctly implemented throughout `stand_alone.py`. |
| CREDIT/AVATAR | ❌ NOT ADDRESSED | D4 is not implemented. If this is a law-level requirement, the feature is non-compliant. |

---

## SECURITY CONSENSUS

Neither model flagged security vulnerabilities in this diff. The code handles:
- File system operations (`os.link`, `shutil`, path manipulation) — no path traversal risks identified.
- External process calls (`ffmpeg`) — arguments are constructed from internal data structures, not user input.
- No network calls, authentication, or secrets handling in the changed code.

**Security verdict: No security issues identified by either model. No action required.**

---

## WORLD-CLASS GAP CONSENSUS

Items mentioned by 2+ models as missing from a truly world-class implementation:

1. **Feature scope completeness (D1 + D4):** Both models agree that shipping a feature that claims to fix four defects while silently fixing only two is a trust and process gap. World-class delivery requires explicit scope tracking — either implement all stated goals or formally document deferrals with tickets.

2. **Diagnostic error messages:** Both models agree that the two under-descriptive error messages (`replay.py:88`, `shot_snap.py:365`) would slow down production incident response. World-class tooling tells you exactly what failed and what was expected — not just that something went wrong.

3. **Test coverage for unimplemented defects:** Both models noted the absence of tests for D1 and D4. Even if D1/D4 are descoped, adding `pytest.mark.xfail` or `pytest.skip` test stubs with ticket references would document the gap and prevent it from being forgotten.

---

## FINAL ACTION PLAN (sorted by consensus priority)

```
P0 CRITICAL | Resolve D1 (onset clipping) scope: implement fix OR add TODO(D1) comment +
              tracking ticket + changelog note                                          |
              shot_snap.py:362, feature changelog                                      |
              models: both (unanimous)                                                  |
              Shipping a feature that silently omits a stated defect fix breaks QA
              trust and may cause editorial law violations at runtime.

P0 CRITICAL | Resolve D4 (avatar warping) scope: implement fix OR add TODO(D4) comment +
              tracking ticket + changelog note                                          |
              scripts/*, credit processing subsystem (absent from diff)                |
              models: both (unanimous)                                                  |
              Same rationale as D1. Both omissions together undermine the feature's
              stated value.

P1 HIGH     | Improve SystemExit error message in replay.py to include the destination
              path                                                                      |
              replay.py:88                                                              |
              models: both (unanimous)                                                  |
              Low-effort change with high debugging ROI in production incident response.

P1 HIGH     | Improve RuntimeError message in shot_snap.py to include expected vs.
              actual frame counts                                                       |
              shot_snap.py:365                                                          |
              models: both (unanimous)                                                  |
              A/V desync incidents are hard to diagnose; this message is the first
              signal an operator will see.

P1 HIGH     | Confirm or obtain product-owner sign-off on HOLD-verdict suppression in
              delivery script; add explanatory comment if approved                     |
              scripts/pulse_check_run.sh:891–896                                       |
              models: gemini (unique — but high governance risk)                       |
              Silent suppression of HOLD verdicts is a major workflow change that
              must be a deliberate, documented decision.

P2 MEDIUM   | Add regression test for decimal false-equality bug:
              assert word_diff("5.5%", "5%") != []                                    |
              word_diff.py test suite                                                   |
              models: gemini (unique insight — existing fix confirmed correct)         |
              The fix is already in; the test closes the loop and prevents regression.

P2 MEDIUM   | Add xfail or skip stubs for D1 and D4 test cases with ticket references |
              test suite (new file or existing test_stand_alone.py)                   |
              models: gpt4o                                                             |
              Documents the gap, prevents silent forgetting, and makes CI status
              honest about what is and is not covered.
```

---

## CYCLE 2 VERDICT

**NOT PRODUCTION-READY AS SUBMITTED — YES WITH CONDITIONS.**

The code that is present is of high quality: robust fail-closed logic, excellent frame-integrity assertions, a genuine silent-bug fix in decimal normalization, and world-class test fixtures from real production incidents. Neither model found defects in what was implemented.

**The absolute final blockers are:**

1. **P0-A:** The team must make an explicit, documented decision about D1 (onset clipping) — implement it or formally defer it. The code may not ship claiming to address D1 when it does not.
2. **P0-B:** Same for D4 (avatar warping). Both omissions together represent a feature that delivers roughly half its stated value while appearing complete.

Once both P0 items are resolved (by either implementation or formal documented deferral with tickets), and the two P1 error message improvements are applied, this code is ready to ship. The P2 items are strongly recommended but not gate items.

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/PULSE_SENTENCE_LAW_GOSPEL.md.
Read ~/protocol_pulse/docs/audits/pulse-sentence-law_CONSENSUS_C2.md.

This is the FINAL PASS for pulse-sentence-law.
The first build was reviewed by 2 independent AI models across 2 cycles.
Implement every P0 and P1 item from the consensus. Use judgment on P2.

PRIORITY ACTION PLAN:

P0 CRITICAL | Resolve D1 scope: implement onset-clipping fix in shot_snap.py, OR add
              # TODO(D1): onset clipping not addressed this cycle — ticket #XXX
              at shot_snap.py:362 and update the feature changelog to list D1 as deferred.

P0 CRITICAL | Resolve D4 scope: implement avatar-warp fix, OR add
              # TODO(D4): credit avatar warping not addressed this cycle — ticket #XXX
              in the nearest relevant file and update the feature changelog.

P1 HIGH     | replay.py:88 — Change SystemExit message to:
              f"STOP: Replay destination {dst} already exists. Remove it manually or
              choose a different stamp."

P1 HIGH     | shot_snap.py:365 — Change RuntimeError message to:
              f"shot_snap changed frame count of {clip!r}: expected {n},
              got {frame_count(part)}"

P1 HIGH     | scripts/pulse_check_run.sh:891–896 — Confirm product-owner sign-off on
              HOLD-verdict suppression exists. If yes, add comment:
              # Policy: HOLD not surfaced to review channel — approved by [name] [date]
              If no sign-off exists, escalate before merging.

P2 MEDIUM   | word_diff.py test suite — Add regression test:
              assert word_diff("5.5%", "5%") != [], "decimal false-equality must be detected"

P2 MEDIUM   | Test suite — Add xfail stubs for D1 and D4 with ticket references so CI
              honestly reflects coverage gaps.

VALIDATED — do NOT touch (all models confirmed excellent):
- stand_alone.py: fail-closed logic in opener(), topical(), check_edl() — M12 compliant
- shot_snap.py:363: frame-count integrity assertion — keep exactly as written
- shot_snap.py plan(): if head >= tail: return guard — do not remove
- word_diff.py: _decimals() function and its integration into norm() — correct, leave as-is
- stand_alone.py: scorer exception handling pattern — correct per M12
- replay.py: make_copy() os.link approach and stale-output cleanup — correct, leave structure
- All test fixtures derived from production incidents — do not remove or weaken

After implementing: regression_test.sh must show zero FAILs.
git add -A && git commit -m "feat(pulse-sentence-law): post-audit pass — consensus improvements (C2)"
git push origin combo-letterbox-quoteonly-v2
```

---

# WINNER DETERMINATION

WINNER: Gemini — It delivered the highest-quality Cycle 1 analysis by correctly auditing code correctness at a granular level (including the subtle `word_diff.py` decimal-collapse failure mode that neither other model caught), and its Cycle 2 self-correction was intellectually honest and structurally complete, explicitly acknowledging what it missed and why, rather than simply echoing the consensus. Its scores were also better calibrated to the actual quality of the implemented code versus the feature-boundary problem, which the consensus report validated as the more precise framing.

---

## FINAL SECOND-PASS PRIORITY LIST

Ordered by severity × implementation cost (highest urgency first):

---

### P1 — BLOCKING: Formally resolve D1 (Onset/Tail Clipping) — unanimous U1
- **Why first:** Silent feature incompleteness erodes QA and product trust. This is a contract violation between the spec and the diff.
- **Action:** Either implement audio-head guard-interval padding before the first speech token, OR add an explicit `# TODO(D1): onset clipping descoped — ticket #XXX` and create the tracking ticket. No silent omissions.
- **File:** `shot_snap.py:362`

---

### P2 — BLOCKING: Formally resolve D4 (Credit Avatar Warping) — unanimous U2
- **Why second:** Same class of problem as P1 — stated goal, zero implementation, no acknowledgment.
- **Action:** Implement avatar aspect-ratio preservation in credit rendering, OR descope with an explicit comment and ticket. Same standard as P1.
- **File:** Credit/avatar rendering pipeline (not present in diff — that is itself the finding)

---

### P3 — HIGH: Improve error messages in `replay.py` and `shot_snap.py` — unanimous U3
- **Why third:** A/V desync bugs are the hardest class of defect to diagnose in post-processing pipelines. Opaque `SystemExit` calls waste engineer hours.
- **Action:** In `shot_snap.py`, include expected vs. actual frame count in the exception message. In `replay.py`, include the failing stage name and exit code. Format: `f"shot_snap: frame count changed: expected {expected}, got {actual} — clip={clip_id}"`.
- **Files:** `shot_snap.py` (frame-count guard), `replay.py` (SystemExit call sites)

---

### P4 — HIGH: Add test coverage for D1 and D4 omissions — GPT-4o finding, Gemini confirmed
- **Why fourth:** Even if D1/D4 are descoped, regression tests must gate against silent regressions of the *existing* behavior. If they are implemented, tests are obviously required.
- **Action:** Add test cases that assert onset-clipping does not worsen after `shot_snap.apply()` runs. Add test cases asserting credit avatar aspect ratio is preserved (or is unchanged from pre-patch baseline, if descoped).
- **Files:** Test suite for `shot_snap.py`, credit rendering module

---

### P5 — MEDIUM: Verify `opener` fail-closed behavior under scorer timeout — Gemini finding
- **Why fifth:** `stand_alone.py:433` correctly fails closed when `score is None`, but there is no test that simulates scorer unavailability mid-batch. A scorer timeout in production would silently block clips without an alert.
- **Action:** Add a unit test that injects `score=None` and asserts the clip is rejected. Add a monitoring alert or log line when fail-closed is triggered in production.
- **File:** `stand_alone.py:433`, test suite

---

### P6 — LOW: Confirm `plan` safety check handles zero-duration edge case — Gemini finding
- **Why last:** The `if head >= tail:` guard in `shot_snap.py:338` is correct but has no dedicated test. Low risk given the guard exists, but worth a regression test.
- **Action:** Add a test with a scene-change boundary exactly at the speech-on and speech-off timestamps, asserting the clip is dropped rather than producing a zero-frame output.
- **File:** `shot_snap.py:338`, test suite