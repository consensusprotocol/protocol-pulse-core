# CONSENSUS REPORT — PULSE-SENTENCE-LAW — CYCLE 2
Generated: 2026-11-11 02:44
Models: grok, gpt4o, gemini

---

## SCORES

| Subsystem      | Gemini | GPT-4o | Grok | Consensus |
|----------------|--------|--------|------|-----------|
| Correctness    | 9.5    | 9.5    | 9.6  | **9.5**   |
| Law Compliance | 9.5    | 9.5    | 10.0 | **9.7**   |
| Test Quality   | 10.0   | 9.3    | 9.4  | **9.6**   |
| **Overall**    | —      | —      | —    | **READY** |

> Score interpretation: Gemini's Law Compliance downgrade to 9.5 reflects epistemic caution (credits compliance inferred, not directly visible in diff), not an actual defect. Grok's 10.0 reflects that all laws are satisfied by what is visible. Consensus splits the difference.

---

## UNANIMOUS FINDINGS (all 3 models agree — implement unconditionally)

### U1 — Redundant In-Function Import of `sentence_law`
**What it is:** `import sentence_law as L` (or equivalent) appears inside a function body (`stage_cut` in `run_fresh.py`) in addition to the module-level import. This is dead weight: it re-runs the import machinery on every call, pollutes the function's local namespace, and signals to future readers that the module-level import is unreliable.

**File/line:** `pipeline/run_fresh.py`, line 221 (inside `stage_cut`); also reported at `pinned.py` lines 39 and 54 (Grok cycle 2).

**What to change:** Delete the in-function import statement(s). Confirm the module-level `import sentence_law` (or `from pipeline import sentence_law`) already exists at the top of each affected file and is sufficient.

---

## MAJORITY FINDINGS (2 of 3 models agree)

### M1 — `TestD4Credits` Temporary Directory Lifecycle
**Models:** GPT-4o + Grok (Gemini noted it was already present in diff but agreed the pattern is correct).

**What it is:** The `TestD4Credits` test class manages temporary directories per-test via `mkdtemp` inside individual test methods. This creates risk of leaked temp directories on test failure and duplicates setup/teardown boilerplate.

**File/line:** `test_pulse_20261110_mustfail.py`, lines 1530–1537.

**What to change:** Promote temp directory creation to `setUpClass` / `tearDownClass` (or use `tempfile.TemporaryDirectory` as a class-level context manager). Ensures cleanup even on assertion failure and removes per-test duplication.

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### UI-1 — Credits Law Compliance Is Inferred, Not Directly Verified (Gemini only)
**What it is:** The diff does not include the implementation of `shoutout.validate_avatar`. Compliance with the CREDITS law is established entirely through the test at `test_pulse_20261110_mustfail.py:1545`, not through direct inspection of the enforcement logic.

**Assessment: Investigate further — do not block ship.**
The test is a genuine integration test that would fail if `validate_avatar` were broken. This is acceptable evidence for a diff-scoped audit. However, the next audit cycle for `shoutout.validate_avatar` itself should explicitly include that function in scope. Add a TODO comment near the test: `# AUDIT NOTE: validate_avatar implementation not in this diff; re-audit at shoutout.py`.

### UI-2 — Defense-in-Depth: Dual `gate_g16` Calls (Grok only)
**What it is:** `stage_sentence_law` runs G16 as a pre-render fast-fail (line 278), and `gate_g16` runs again inside `stage_gates` (lines 417–422), giving two independent enforcement points.

**Assessment: Skip (no action needed — this is a strength, not a gap).**
Document as an intentional design decision in an inline comment if not already present, so future editors do not collapse the two calls thinking they are redundant.

### UI-3 — Old `compute_all_cuts` Path Now Unreachable in Auto Mode (Grok only)
**What it is:** `write_lock_cut_table` + `_accepted_cut_pair` make the old `compute_all_cuts` path dead code in auto mode. `test_pinned.py:1425–1435` asserts this.

**Assessment: Implement a minor hardening.** Add a `raise AssertionError("unreachable: compute_all_cuts called in auto mode")` guard (or equivalent `assert False`) at the entry of the old path so that if the routing logic ever regresses, the failure is loud rather than silent. File/line: wherever the auto-mode branch diverges.

---

## CONFLICTS (models disagree — tiebreaker)

### C1 — Law Compliance Score: 9.5 (Gemini, GPT-4o) vs. 10.0 (Grok)
**Nature of disagreement:** Gemini and GPT-4o penalised compliance because `shoutout.validate_avatar` is out-of-diff. Grok scored 10.0 because all laws are satisfied by the visible code.

**Tiebreaker ruling: Both are correct within their scope.**
Grok is correct that the code *in the diff* is fully compliant. Gemini/GPT-4o are correct that a full-system compliance claim requires verifying code outside the diff. Consensus score 9.7 is appropriate. This is not a conflict requiring a code change — it is a documentation scope issue (see UI-1 above).

### C2 — Priority Classification of Redundant Import
**Nature of disagreement:** GPT-4o labelled it P1 HIGH. Grok and Gemini labelled it P2 MEDIUM.

**Tiebreaker ruling: P2 MEDIUM is correct.**
The redundant import causes no runtime failure, no incorrect behavior, and no law violation. It is a code hygiene issue. Calling it P1 overstates the risk and creates priority inflation. P2 is the right label.

---

## VALIDATED STRENGTHS (all models agree — do NOT touch in second pass)

1. **`_accepted_cut_pair` constrained search** (sentence_law.py:1050–1067): Searches only within the locked window; makes SNAP LIMIT violation structurally impossible. Do not expand the search window or add fallback paths.

2. **`selection_lock` immutability** (select_passages.py:559–567, run_fresh.py:220–226): Lock is written at selection time and never recomputed. Do not add any code path that re-derives `expected_words` or `cut_lo`/`cut_hi` after selection.

3. **Fail-closed `edge_plan` / `write_lock_cut_table`** (sentence_law.py:951–978, 1070–1109): Returns descriptive `valid: False` records rather than raising exceptions for expected failures. Do not convert these to exception-based flows.

4. **`Adjudicator` deterministic replay via `allow_model=False`** (sentence_law.py:871): Cache-miss in gate mode raises `LawError` immediately; gates cannot pass on stale or absent adjudication. Do not add a fallback that calls the model when cache is missing during gate execution.

5. **Complete deletion of `_snap_candidates` + `_recompute_edge_words`** (run_fresh.py, formerly lines 106–202, 238–259, 329–368): The root-cause elimination of D1/D2/D3. Do not reintroduce any snapping or word-recomputation logic.

6. **`SourceAudio` with `check=True` and empty-data guard** (sentence_law.py:759, 764): `ffmpeg` failures are not silent; zero-length audio is rejected. Do not relax either check.

7. **Must-fail test suite with exact reason assertions** (test_pulse_20261110_mustfail.py:1443–1523): Tests assert specific failure reasons (D1/D2/D3), not just failure presence. Do not weaken assertions to `assertFalse(result.ok)` without reason checking.

---

## LAW COMPLIANCE CONSENSUS

| Law | Status | Evidence |
|-----|--------|----------|
| SENTENCE LAW | ✅ COMPLIANT | `boundary()` + 80 ms acoustic check; constants at lines 694–697 |
| SELECTION LOCK | ✅ COMPLIANT | `make_lock`/`verify_lock`; lock sealed at selection, never recomputed |
| SNAP LIMIT | ✅ COMPLIANT | `_accepted_cut_pair` searches only inside `cut_lo`/`cut_hi`; old snap path deleted |
| ONSET/TAIL | ✅ COMPLIANT | `edge_plan` lead/tail rules; G17a/b gates enforce at render time |
| CREDITS | ✅ COMPLIANT (inferred) | Test at line 1545 passes; `validate_avatar` implementation outside diff scope |
| LAW 20 / M2 | ✅ COMPLIANT | Gate thresholds are constants; failures produce hard stops |
| M12 FAIL CLOSED | ✅ COMPLIANT | Missing transcript / failed adjudication / no valid pause → rejection, never pass |
| LAW 22 | ✅ COMPLIANT | v2f reference path unchanged; no evidence of drift |

**No law violations found.**

---

## SECURITY CONSENSUS

No security issues were flagged by any model. For completeness, the following properties were confirmed safe:

- **`subprocess.run` with `check=True`** (SourceAudio): Does not expose shell injection because arguments are passed as a list, not a shell string.
- **`os.replace` for cache writes** (Adjudicator:890): Atomic write prevents partial-cache reads by concurrent processes.
- **No external user input flows** into gate logic: All inputs are pipeline-internal EDL/lock structures, not user-supplied strings.

**Security verdict: No issues.**

---

## WORLD-CLASS GAP CONSENSUS
*(Items mentioned by 2+ models)*

### WCG-1 — Out-of-Diff Verification Boundary (Gemini + GPT-4o)
The audit's scope is limited to the diff. `shoutout.validate_avatar` and any other enforcement modules called by the new pipeline but not shown in the diff are unverified. A truly world-class audit process would either expand the diff scope to include all transitively called enforcement functions, or maintain a living "verified module registry" with explicit scope declarations per audit cycle.

**Recommendation:** Add a machine-readable `AUDIT_SCOPE.toml` to the repo root listing which modules were in-scope for each audit. Flag out-of-scope calls with `# AUDIT: out-of-scope — verify in [module] audit` comments at call sites.

### WCG-2 — Deterministic Replay Coverage (Grok + Gemini)
The `allow_model=False` mode in `Adjudicator` is excellent, but no test explicitly exercises the cache-miss-during-gate path to confirm it raises `LawError` rather than silently passing. A world-class test suite would include a fixture that deliberately presents an empty cache directory to a gate call and asserts `LawError` is raised.

**Recommendation:** Add `test_adjudicator_gate_cache_miss_raises_law_error` to `test_pinned.py`.

---

## FINAL ACTION PLAN (sorted by consensus priority)

| Priority | Change | File:Line | Models | Why |
|----------|--------|-----------|--------|-----|
| **P2 MEDIUM** | Remove redundant in-function `import sentence_law as L` statements | `pipeline/run_fresh.py:221`; `pipeline/pinned.py:39,54` | All 3 | Module-level import is sufficient; in-function imports re-run import machinery on every call and mislead future readers |
| **P2 MEDIUM** | Promote `TestD4Credits` temp dir to `setUpClass`/`tearDownClass` | `test_pulse_20261110_mustfail.py:1530–1537` | GPT-4o + Grok | Prevents leaked temp dirs on assertion failure; removes per-test duplication |
| **P2 MEDIUM** | Add unreachable-path guard (`assert False` or `raise AssertionError`) at old `compute_all_cuts` auto-mode entry point | `pipeline/run_fresh.py` (auto-mode branch) | Grok (unique; high value) | Makes routing regression loud instead of silent |
| **P2 MEDIUM** | Add `# AUDIT: out-of-scope` comment at `shoutout.validate_avatar` call site | `pipeline/run_fresh.py` or `select_passages.py` (call site) | Gemini (unique; process value) | Documents verification boundary for future auditors |
| **P3 LOW** | Add `test_adjudicator_gate_cache_miss_raises_law_error` test | `test_pinned.py` (new test) | Gemini + Grok (WCG-2) | Closes the one untested `allow_model=False` failure path |
| **P3 LOW** | Add inline comment at dual `gate_g16` call sites explaining intentional defense-in-depth | `pipeline/run_fresh.py:278`, `417–422` | Grok (unique) | Prevents future editors from collapsing the two calls |

**P0 CRITICAL: None.**
**P1 HIGH: None.**

---

## CYCLE 2 VERDICT

**PRODUCTION READY — with P2 conditions.**

After two full cycles of independent review by three models examining correctness, law compliance, test quality, and security, **no functional defects, no law violations, and no security issues were found.** The code represents a structurally superior replacement for the D1/D2/D3-causing logic it removes.

The absolute final blockers before ship are:
1. Remove the redundant in-function imports (P2 — 5 minutes of work, zero risk).
2. Fix `TestD4Credits` temp dir lifecycle (P2 — 10 minutes of work, zero risk).

All other items are non-blocking improvements. The core architectural decisions — immutable selection lock, constrained cut search, fail-closed adjudication, deterministic replay, deletion of snap/recompute logic — are validated by unanimous consensus and must not be altered in the second pass.

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/PULSE_SENTENCE_LAW_GOSPEL.md.
Read ~/protocol_pulse/docs/audits/pulse-sentence-law_CONSENSUS_C2.md.

This is the FINAL PASS for pulse-sentence-law.
The first build was reviewed by 3 independent AI models across 2 cycles.
Implement every P0 and P1 item from the consensus (there are none — 
all blockers are P2). Implement all P2 items. Use judgment on P3.

PRIORITY ACTION PLAN:

P2 MEDIUM | Remove redundant in-function `import sentence_law as L` statements
          | pipeline/run_fresh.py:221 and pipeline/pinned.py:39,54
          | models: all 3
          | Module-level import is sufficient; in-function imports re-run
          | import machinery on every call and mislead future readers.

P2 MEDIUM | Promote TestD4Credits temp dir to setUpClass/tearDownClass
          | test_pulse_20261110_mustfail.py:1530–1537
          | models: GPT-4o + Grok
          | Prevents leaked temp dirs on assertion failure; removes
          | per-test duplication.

P2 MEDIUM | Add unreachable-path guard at old compute_all_cuts auto-mode
          | entry point (raise AssertionError or assert False)
          | pipeline/run_fresh.py (auto-mode branch)
          | models: Grok (unique, high value)
          | Makes routing regression loud rather than silent.

P2 MEDIUM | Add "# AUDIT: out-of-scope — verify in shoutout audit" comment
          | at shoutout.validate_avatar call site
          | pipeline/run_fresh.py or select_passages.py (call site)
          | models: Gemini (unique, process value)
          | Documents verification boundary for future auditors.

P3 LOW    | Add test_adjudicator_gate_cache_miss_raises_law_error test
          | test_pinned.py (new test)
          | models: Gemini + Grok
          | Closes the one untested allow_model=False cache-miss path.

P3 LOW    | Add inline comment at dual gate_g16 call sites explaining
          | intentional defense-in-depth (not redundancy)
          | pipeline/run_fresh.py:278 and :417–422
          | models: Grok
          | Prevents future editors from collapsing the two calls.

VALIDATED — do NOT touch these; all 3 models confirmed excellent:

1. _accepted_cut_pair constrained search (sentence_law.py:1050–1067):
   Do NOT expand the search window or add fallback paths.

2. selection_lock immutability (select_passages.py:559–567,
   run_fresh.py:220–226): Do NOT add any code path that re-derives
   expected_words or cut_lo/cut_hi after selection.

3. Fail-closed edge_plan / write_lock_cut_table (sentence_law.py:951–978,
   1070–1109): Do NOT convert to exception-based flows.

4. Adjudicator allow_model=False deterministic replay (sentence_law.py:871):
   Do NOT add a model-fallback when cache is missing during gate execution.

5. Complete deletion of _snap_candidates + _recompute_edge_words: Do NOT
   reintroduce any snapping or word-recomputation logic.

6. SourceAudio check=True and empty-data guard (sentence_law.py:759, 764):
   Do NOT relax either check.

7. Must-fail test assertions with exact reason strings
   (test_pulse_20261110_mustfail.py:1443–1523): Do NOT weaken to bare
   assertFalse without reason checking.

After implementing: regression_test.sh must show zero FAILs.
git add -A && git commit -m "feat(pulse-sentence-law): post-audit pass — consensus improvements"
git push origin combo-letterbox-quoteonly-v2
```

---

# WINNER DETERMINATION

**WINNER: Gemini** — Gemini delivered the deepest and most rigorous first-cycle analysis, correctly identifying the atomic cache write (`os.replace`), the descriptive failure propagation pattern across `boundary()`/`edge_plan()`/`write_lock_cut_table()`/`gate_g16()`, and the epistemological distinction between inferred and directly verified compliance (UI-3) — a nuance neither Grok nor GPT-4o raised independently. In Cycle 2, Gemini's self-correction was the most substantive: it named its own blind spots precisely, elevated GPT-4o's import finding, and produced the sharpest methodological observation of the entire audit ("the epistemology of code auditing"), demonstrating both depth and intellectual honesty that the other models did not match.

---

## FINAL SECOND-PASS PRIORITY LIST

| # | Priority | Finding | File / Lines | Action |
|---|----------|---------|--------------|--------|
| 1 | **P1 — HIGH** | **U1: Redundant in-function `import sentence_law`** | `pipeline/run_fresh.py:221`; `pinned.py:39,54` | Delete all in-function import statements; confirm module-level import is present and sufficient in each file |
| 2 | **P2 — MEDIUM** | **M1: `TestD4Credits` temp-dir lifecycle** | `test_pulse_20261110_mustfail.py:1530–1537` | Migrate `mkdtemp` creation and `shutil.rmtree` cleanup to `setUpClass`/`tearDownClass`; prevents leaked directories on test failure |
| 3 | **P3 — LOW** | **UI-3: Credits-law compliance inferred, not directly verified** | `shoutout.validate_avatar` (outside diff) | Add a direct unit test or inline assertion against `validate_avatar`'s source; do not rely solely on the integration test assertion as proof of compliance |
| 4 | **P4 — LOW** | **Defense-in-depth double gate not documented** | `run_fresh.py:278–294` (`stage_sentence_law`) + `run_fresh.py:417–422` (`stage_gates → gate_g16`) | Add a comment at each call site naming the other gate and explaining the layered intent; prevents future engineers from collapsing them into one |
| 5 | **P5 — INFORMATIONAL** | **`compute_all_cuts` auto-mode path now unreachable** | `test_pinned.py:1425–1435` | Confirm with a `pytest.mark.xfail` or deletion that the old path is intentionally dead; prevents confusion if someone attempts to revive it |