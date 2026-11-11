# CONSENSUS REPORT — PULSE-SENTENCE-LAW — CYCLE 2
Generated: 2026-11-11 12:09
Models: gpt4o, gemini (+1 failed: grok — budget exceeded)

---

## SCORES

| Subsystem       | Gemini | GPT-4o | Grok        | Consensus |
|-----------------|--------|--------|-------------|-----------|
| Correctness     | 9/10   | 9/10   | N/A (failed)| **9/10**  |
| Law Compliance  | 8/10   | 9/10   | N/A (failed)| **8/10**  |
| Test Quality    | 10/10  | 9/10   | N/A (failed)| **9/10**  |
| Error Handling  | 6/10   | 8/10   | N/A (failed)| **7/10**  |

> **Note on Grok failure**: Budget exceeded before Grok could contribute. Consensus is drawn from 2 of 3 models. Confidence is moderate; findings should be treated as 2-model agreement rather than full 3-model unanimity. No finding is artificially promoted to "unanimous" solely on the basis of 2/2 agreement when 3 were expected.

---

## UNANIMOUS FINDINGS (all 2 available models agree — implement unconditionally)

### U1 — M12 FAIL CLOSED: `check_cut_acoustics` dependency not wrapped in error handling
**What it is**: The call to `check_cut_acoustics` on line 8 of `pipeline/run_fresh.py`, and all subsequent processing of its return value `d` through line 14, is unguarded. If the dependency raises any exception (network error, timeout, internal failure) or returns a malformed/incomplete dictionary (e.g., missing the `"out"` key), the stage crashes with an unhandled `TypeError` or `KeyError`. A crash is not equivalent to a graceful fail-closed: it may leave `rec` in an indeterminate state, corrupt pipeline state for downstream stages, and produce no structured audit trail for the failure.

**File/Line**: `pipeline/run_fresh.py`, lines 8–14

**What to change**: Wrap the entire block — the `check_cut_acoustics` call through the `rec.update(...)` line — in a `try/except Exception` block. Inside the `except` block, set `ok = False`, log the error with the clip identifier, and write a structured failure reason into `rec`. This ensures every failure path produces a deterministic, logged rejection rather than a process crash.

```python
# pipeline/run_fresh.py — recommended replacement for lines 8-14
try:
    ok, d = check_cut_acoustics(src, c["cut_in"], c["cut_out"])
    for s in ("in", "out"):
        if c.get(f"valley_{s}"):
            d[s] = {
                "pass": True,
                "m19": d[s],
                "judged_by": "G16 neighbour_clear (DEC-10 c-ii)",
            }
    ok = d["in"]["pass"] and d["out"]["pass"]
    rec.update(pass_=ok, **d)
except Exception as e:
    log.error(
        "acoustic_check_failed clip=%s err=%s",
        rec.get("clip_id", "unknown"),
        e,
    )
    rec.update(pass_=False, reason="acoustic_check_exception")
    ok = False
```

---

## MAJORITY FINDINGS (2 of 2 models agree)

All findings at this level are identical to the unanimous findings above — with only 2 models available, the unanimous and majority tiers collapse. See U1.

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### UI1 — Gemini only: Structurally incomplete return value is a distinct risk from an exception
**What Gemini caught**: Beyond `check_cut_acoustics` raising an exception, Gemini specifically identified that it could return a *structurally valid but incomplete* dictionary — for example, `{"in": {"pass": True}}` with the `"out"` key absent — causing a `KeyError` on line 13 (`d["out"]["pass"]`). This is a distinct failure mode from a thrown exception and is worth naming explicitly: even a "successful" call with a partial return value will crash the stage.

**Assessment**: **Implement**. This is not a hypothetical edge case. If `check_cut_acoustics` ever short-circuits on the `"in"` edge (e.g., early return on first failure), the `"out"` key may be absent. The `try/except` block from U1 covers this failure mode automatically, but the structural validation point is worth documenting in a code comment so future maintainers understand the assumption being guarded. Consider adding an assertion or explicit key-existence check inside the `try` block as defense-in-depth:

```python
# inside the try block, after the call:
assert "in" in d and "out" in d, f"Malformed acoustic dict: {d.keys()}"
```

### UI2 — Gemini only: `judged_by` annotation and `m19` preservation explicitly praised as auditability strengths
**What Gemini caught**: Gemini foregrounded the `judged_by` annotation and the preservation of original `m19` data as named strengths, framing them as accountability mechanisms, not incidental details.

**Assessment**: **Acknowledge / no change needed**. These are confirmed strengths (see Validated Strengths below). No action required beyond preserving them.

### UI3 — GPT-4o only: `check_cut_acoustics` is mocked in tests, so its failure behavior is not exercised
**What GPT-4o caught**: Because the dependency is fully mocked in the test suite, there is no test that exercises the error-handling path for a dependency failure.

**Assessment**: **Implement** (add test). After adding the `try/except` block from U1, add at least one test case where the mock raises an exception and assert that: (a) `rec["pass"]` is `False`, (b) `rec["reason"]` contains `"acoustic_check_exception"`, and (c) no exception propagates to the caller.

```python
# pipeline/test_dec10_edges.py — add this test case
def test_stage_cut_acoustic_check_raises_fails_closed(monkeypatch):
    monkeypatch.setattr(
        "pipeline.run_fresh.check_cut_acoustics",
        Mock(side_effect=RuntimeError("simulated failure")),
    )
    hold, rec = _stage_cut(clip_id="test-clip", valley_in=False, valley_out=False)
    assert rec["pass"] is False
    assert "acoustic_check_exception" in rec.get("reason", "")
    assert hold is True  # pipeline should hold on fail-closed
```

---

## CONFLICTS (models disagree — tiebreaker)

### C1 — Law Compliance score: Gemini 8/10 vs. GPT-4o 9/10
**Disagreement**: Gemini downgraded Law Compliance from 10 to 8, arguing that the absence of error handling constitutes a meaningful M12 FAIL CLOSED violation. GPT-4o kept Law Compliance at 9/10, treating error handling as a robustness concern rather than a compliance failure.

**Tiebreaker — Gemini is more correct here**: M12 FAIL CLOSED is an explicit governing law, not a best-practice guideline. A dependency failure that crashes the stage rather than producing a structured rejection is not compliant with the law's intent, even if it technically prevents a false pass. The process may not cleanly record `pass=False` in the audit record if it crashes mid-write. The law requires the system to *actively* fail closed, not merely avoid accidentally passing. **Consensus Law Compliance score: 8/10.**

### C2 — Error Handling score: Gemini 6/10 vs. GPT-4o 8/10
**Disagreement**: Gemini scored more harshly (6/10), GPT-4o more leniently (8/10).

**Tiebreaker — Gemini's lower score is more appropriate**: The gap is specifically the lack of any `try/except` around a dependency call in a pipeline stage that governs cut acceptance. In a system where false passes have editorial and legal-weight consequences, unguarded dependency calls should be treated as a meaningful deficiency. **Consensus Error Handling score: 7/10** (splitting for practical use, but the fix is mandatory).

---

## VALIDATED STRENGTHS (all models agree — do NOT change)

1. **`c.get(f"valley_{s}")` defensive access** — Safe key lookup that correctly returns `None` (falsy) when the flag is absent, preventing crashes on inputs that lack valley metadata.

2. **`m19` preservation under new key** — The original acoustic check result is not discarded when overridden; it is nested under `d[s]["m19"]`. This maintains full audit accountability and prevents silent data loss.

3. **`judged_by` annotation** — The string `"G16 neighbour_clear (DEC-10 c-ii)"` embedded in the record makes the override reason self-documenting in the data layer itself, not just in source comments.

4. **Test isolation via mocks** — Tests correctly isolate `stage_cut` using mocks for `check_cut_acoustics`, making test failures attributable to logic under test rather than dependency behavior.

5. **Valley flag logic is correctly scoped per-edge** — The `for s in ("in", "out")` loop applies the valley override independently to each edge, preventing a valley on one side from silently masking a failure on the other.

---

## LAW COMPLIANCE CONSENSUS

| Law              | Status                | Notes |
|------------------|-----------------------|-------|
| SENTENCE LAW     | ✅ COMPLIANT          | No sentence boundary logic is touched. |
| SELECTION LOCK   | ✅ COMPLIANT          | Expected words are not recomputed. |
| SNAP LIMIT       | ✅ COMPLIANT          | The diff is a direct implementation of this law's envelope-minimum clause. |
| NEIGHBOUR (G16)  | ✅ COMPLIANT          | Deferral to `neighbour_clear` is correctly documented and implemented. |
| ONSET/TAIL       | ✅ COMPLIANT          | Not touched. |
| CREDITS          | ✅ N/A                | Not applicable to this diff. |
| LAW 20 / M2      | ✅ COMPLIANT          | Gate thresholds not altered. |
| **M12 FAIL CLOSED** | ⚠️ **PARTIAL**    | The new logic block correctly avoids false passes for the valley case. However, an unhandled dependency exception or malformed return from `check_cut_acoustics` could crash the stage rather than producing a structured `pass=False` record. The law requires *active* fail-closed behavior, not crash-as-fallback. **Fix required before this is fully compliant.** |
| LAW 22           | ✅ COMPLIANT          | v2f reference path behavior unchanged. |

---

## SECURITY CONSENSUS

No security-specific findings were raised by either model. The code operates on internal pipeline data (timings, acoustic results) with no external input surfaces visible in the diff. No injection vectors, authentication gaps, or secrets-handling issues were identified.

**Security posture: No action required from this audit.**

---

## WORLD-CLASS GAP CONSENSUS
*(Items mentioned by 2+ models)*

### Gap 1 — Dependency failure path is untested (both models)
The test suite exercises the happy path and the valley-flag override path, but has no coverage for `check_cut_acoustics` raising an exception or returning malformed data. A world-class pipeline stage has tests for every exit path, including dependency failures. Without this, the `try/except` fix from U1 would itself be untested and could regress silently.

### Gap 2 — M12 FAIL CLOSED not fully operationalized (both models)
Both models converged on this: a world-class implementation of M12 does not rely on "crash prevents false pass" as the safety mechanism. It explicitly handles every failure mode, produces a structured rejection record with a reason code, and logs at an appropriate level with enough context (clip ID, error type) to triage production incidents without log-diving. The current code is one `try/except` block away from meeting this standard.

---

## FINAL ACTION PLAN (sorted by consensus priority)

| Priority | Change | File:Line | Models | Why |
|----------|--------|-----------|--------|-----|
| **P1 HIGH** | Wrap `check_cut_acoustics` call and all `d`-processing in `try/except Exception`; on exception set `ok=False`, log with clip ID, write `reason="acoustic_check_exception"` to `rec` | `pipeline/run_fresh.py:8–14` | both (gpt4o, gemini) | M12 FAIL CLOSED requires structured fail-closed on dependency failures, not crash-as-fallback. Without this, the law is only partially satisfied. |
| **P1 HIGH** | Add test: mock raises `RuntimeError`, assert `rec["pass"] is False`, `reason` contains exception marker, no exception propagates | `pipeline/test_dec10_edges.py` | gpt4o (dependency gap); gemini (structural risk) | The P1 fix above is itself unvalidated without a test. M12 compliance cannot be claimed if the fail-closed path has zero coverage. |
| **P2 MEDIUM** | Inside `try` block, add assertion or explicit check that both `"in"` and `"out"` keys exist in `d` before accessing them; log and reject if either is absent | `pipeline/run_fresh.py:10–13` | gemini (unique) | Defense-in-depth against structurally incomplete returns. Covered by the P1 `try/except` but worth making explicit for future maintainers. |

---

## CYCLE 2 VERDICT

**The core logic is correct and the law implementation is sound.** The valley-edge override, `m19` preservation, `judged_by` annotation, and per-edge scoping are all well-implemented. The test suite is strong for the primary logic paths.

**The code is NOT yet production-ready as written.** The single blocker is:

> **The `check_cut_acoustics` call and its result-processing are unguarded.** A dependency exception or malformed return will crash the stage rather than producing a structured `pass=False` record, leaving `rec` in an indeterminate state and violating M12 FAIL CLOSED in its operational meaning.

This is a small, low-risk, high-confidence fix. Resolve the P1 items (error handling + test coverage for the error path), then this code is production-ready.

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/PULSE_SENTENCE_LAW_GOSPEL.md.
Read ~/protocol_pulse/docs/audits/pulse-sentence-law_CONSENSUS_C2.md.

This is the FINAL PASS for pulse-sentence-law.
The first build was reviewed by 2 independent AI models (gpt4o, gemini)
across 2 cycles. Grok failed due to budget limits (not a code issue).
Implement every P0 and P1 item from the consensus. Use judgment on P2.

PRIORITY ACTION PLAN:

P1 HIGH | Wrap the check_cut_acoustics call and all d-processing (lines 8–14)
        | in try/except Exception. On exception: set ok=False, call
        | log.error() with clip_id and error, write
        | rec.update(pass_=False, reason="acoustic_check_exception").
        | File: pipeline/run_fresh.py lines 8–14

P1 HIGH | Add test where check_cut_acoustics mock raises RuntimeError.
        | Assert: rec["pass"] is False, rec["reason"] contains
        | "acoustic_check_exception", no exception propagates to caller,
        | pipeline hold is True.
        | File: pipeline/test_dec10_edges.py

P2 MEDIUM | Inside the try block, after the check_cut_acoustics call,
          | add an explicit assertion or guard that both "in" and "out"
          | keys exist in d. If either is missing: log, set ok=False,
          | write reason="acoustic_check_malformed_response".
          | File: pipeline/run_fresh.py (inside try block)

VALIDATED (do NOT touch — all models confirmed excellent):
- c.get(f"valley_{s}") defensive key access — do not change
- m19 preservation under nested key — do not change
- judged_by annotation string — do not change
- for s in ("in", "out") per-edge loop — do not change
- Existing test structure and mock isolation — do not change, only add

After implementing: regression_test.sh must show zero FAILs.
Verify the new exception-path test appears in test output and passes.
git add -A && git commit -m "feat(pulse-sentence-law): post-audit pass — M12 fail-closed hardening + exception path test coverage"
git push origin combo-letterbox-quoteonly-v2
```

---

# WINNER DETERMINATION

WINNER: **Gemini** — Gemini delivered the most precise, technically grounded Cycle 1 analysis by independently identifying the defensive `c.get()` pattern, the data-preservation strength of the `m19` key, and the traceability value of the `judged_by` annotation before any cross-model review surfaced them, demonstrating genuine depth rather than reactive agreement. In Cycle 2, Gemini produced the clearest structured self-correction, explicitly acknowledging its own blind spot on dependency failure modes with specific exception types (`TypeError`, `KeyError`) and articulating *why* a crash fails M12 more rigorously than any other model's response.

---

## FINAL SECOND-PASS PRIORITY LIST

Ordered by: risk severity × consensus confidence × actionability. Implement in this sequence.

---

### P1 — CRITICAL · IMPLEMENT IMMEDIATELY
**M12 FAIL CLOSED: Wrap `check_cut_acoustics` call and all downstream dict access in guarded error handling**

- **File/Lines**: `pipeline/run_fresh.py`, lines 8–14
- **Action**: Wrap the full block in `try/except Exception as e`. In the `except` block: set `ok = False`, write `rec["error"] = {"stage": "check_cut_acoustics", "reason": str(e), "clip": clip_id}`, log at ERROR level with clip identifier. Do not re-raise. This covers: exceptions from the dependency, `None` return, missing `"in"`/`"out"` keys, and malformed sub-dicts.
- **Why first**: Unhandled crash leaves pipeline state indeterminate. No audit trail is written. Downstream stages may operate on corrupt `rec`. This is the only finding rated below 8/10 by both available models (consensus 7/10 on Error Handling).

---

### P2 — HIGH · IMPLEMENT BEFORE MERGE
**Validate return structure of `check_cut_acoustics` before accessing keys**

- **File/Lines**: `pipeline/run_fresh.py`, immediately after the guarded call in P1
- **Action**: After the `try` block succeeds, assert or explicitly check that `d` is a `dict` containing both `"in"` and `"out"` keys, each with a `"pass"` sub-key. If the shape is wrong, treat as a P1-style fail-closed: set `ok = False`, write a structured `rec["error"]` entry with `reason: "malformed_response"`. Do not proceed to the valley-override logic on a structurally invalid `d`.
- **Why second**: Defensive `c.get()` on line 10 handles missing `valley_` flags correctly, but provides no protection if the outer `d` dict itself is missing expected keys. This is a distinct failure mode from P1 and must be handled separately even if P1's exception wrapper is in place.

---

### P3 — MEDIUM · IMPLEMENT IN SAME PR IF POSSIBLE
**Add integration-level test covering `check_cut_acoustics` failure modes**

- **File/Lines**: `pipeline/test_dec10_edges.py`
- **Action**: Add three new test cases to the existing suite: (1) `check_cut_acoustics` raises `Exception` → assert `ok == False`, assert `rec` contains structured `error` key, assert no unhandled exception propagates; (2) `check_cut_acoustics` returns `None` → same assertions; (3) `check_cut_acoustics` returns `{"in": {}}` with missing `"out"` key → same assertions. Current tests mock the function to return well-formed data only, leaving all failure paths untested.
- **Why third**: Tests are currently rated 9–10/10 for the happy path but provide zero coverage of the failure modes identified in P1 and P2. Without these tests, regressions in error handling will not be caught.

---

### P4 — LOW · IMPLEMENT AS FOLLOW-UP TICKET
**Confirm `judged_by` annotation is consumed and surfaced in audit output**

- **File/Lines**: Wherever `rec` is serialized/written downstream of `stage_cut`
- **Action**: Verify that the `judged_by` field written at line 12 is included in the final audit report output and not silently dropped during `rec` serialization. If it is dropped, add it to the serialization schema. This is a traceability concern, not a correctness defect.
- **Why last**: Gemini correctly identified this as a strength of the implementation. The risk is low (data is written; it may simply not be surfaced), but the value of the annotation is nullified if it never reaches the audit trail.

---

**Grok note**: Grok failed due to budget exhaustion before contributing any Cycle 1 or Cycle 2 findings. P1–P4 above reflect 2-model consensus only. If Grok is re-run, its output should be compared against P1 specifically — that finding is the most likely to have additional nuance from a third perspective.