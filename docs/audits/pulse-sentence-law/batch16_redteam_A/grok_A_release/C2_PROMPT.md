# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pulse-sentence-law
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GROK — CYCLE 1 OUTPUT
**Q1: CORRECTNESS**  
Yes for all changed functions visible in the diff. `stage_gates` (run_fresh.py:87-296) now records exact verdicts + evidence via `put`/`_samples` and delegates blockers to release_auth; `attest_run` (355-382) and `verdict_for` (303-308) enforce terminal state + inventory before any candidate; `release_auth.blockers`/`attest`/`authorise` (580-727) reject missing/zero-sample/non-PASS rows and re-verify bytes on disk. No silent exceptions that produce PASS; every missing or malformed path yields HOLD. No time/index arithmetic or unit conversions appear in this diff.  

**Q2: LAW COMPLIANCE**  
- L-a, L-b, L-c, L-j: COMPLIANT (run_fresh:155-163 G20, 206-249 G17c + final-only proof via `edges_on_final`, 285-382 attestation last, release_auth:555-611 exact REQUIRED rows + evidence).  
- L-d, SELECTION_LOCK, SNAP_LIMIT, SENTENCE_LAW constants: not modified in this diff (PARTIAL).  
- No loosened thresholds, no recomputation of locked words, no v2f divergence.  

**Q3: TESTS**  
`test_release_auth.py` (new) exhaustively mutates every REQUIRED row, evidence field, bound file, pack, and run_state; each case asserts HOLD with the precise reason. `test_story_ledger.py` (448-472) covers the new `authorised`/`status` fields. No vacuous assertions.  

**Q4: VERDICT**  
- LOW | run_fresh:212 | G17_onset_tail evidence written after `put` (minor race if exception) | move inside `put`  
- LOW | replay:18-23 | attestation exception path sets HOLD but does not call `write_report` again | cosmetic only  

READY

## GPT4O — CYCLE 1 OUTPUT
### Q1: CORRECTNESS

1. **Function `make_copy` (lines 5-13):** 
   - The function adds "ATTESTATION.json" to the list of stale files (line 10), which aligns with the purpose of ensuring that attestations are not reused improperly. This matches the docstring's implication of ensuring diagnostic replays are not deliverable.
   - The logic seems correct and consistent with the stated purpose.

2. **Function `replay` (lines 14-26):** 
   - The function calls `attest_run` with `deliverable=False`, ensuring replays are not deliverable (lines 18-20). This aligns with the docstring and the laws.
   - The exception handling (lines 21-23) ensures that any error during attestation results in a HOLD verdict, which is consistent with the fail-closed principle.

3. **Function `stage_gates` (lines 70-296):**
   - The function has been refactored to use a `put` function (lines 87-96) to handle gate results, ensuring consistent handling of verdicts and evidence. This aligns with the requirement for exact verdicts and evidence.
   - The function correctly computes the number of samples (lines 52-57), ensuring that a gate cannot pass without evidence.
   - The function checks for hash identity of files (lines 75-76), ensuring the measured files are the ones being attested, which aligns with the laws.
   - The logic for handling dissenting checks (lines 215-249) ensures that a dissenting check is treated as correct unless proven otherwise, complying with law L-c.

4. **Function `attest_run` (lines 357-382):**
   - This function creates an attestation based on the run's state and evidence, ensuring that any hold results in a HOLD verdict (lines 364-368). This aligns with the laws and the fail-closed principle.
   - The function checks for code cleanliness and revision consistency (lines 369-372), which is consistent with ensuring the integrity of the run.

5. **Function `authorise` (lines 683-727):**
   - This function verifies the attestation and ensures all conditions for a release are met, including file integrity and evidence consistency. This aligns with the laws and ensures no unauthorized releases.

Overall, the functions appear to do what their docstrings and the laws state, with no obvious off-by-one errors, wrong units, or silent exceptions.

### Q2: LAW COMPLIANCE

1. **SENTENCE LAW:** COMPLIANT. The diff ensures that sentence boundaries are respected and verified (lines 197-201).

2. **SELECTION LOCK:** COMPLIANT. The selection lock is respected, and no recomputation of expected words is allowed after selection (lines 251-267).

3. **SNAP LIMIT:** COMPLIANT. The logic ensures that cuts are made within the allowed boundaries and do not add or drop words (lines 215-249).

4. **NEIGHBOUR:** COMPLIANT. The logic ensures no audible part of the neighboring word is included (lines 215-249).

5. **ONSET/TAIL:** COMPLIANT. The function `stage_gates` ensures that edge words are preserved as required (lines 203-213).

6. **CREDITS:** COMPLIANT. The credits are verified against the registered avatars (lines 146-154).

7. **L-a SIGN-OFF NAMES ALL:** COMPLIANT. The function ensures that the sign-off names match the credited channels (lines 155-163).

8. **L-b EDGE WORDS WHOLE:** COMPLIANT. The function ensures that edge words are heard whole (lines 203-213).

9. **L-c DISSENT IS RIGHT UNTIL DISPROVED:** COMPLIANT. The function respects dissenting checks until proven otherwise (lines 215-249).

10. **L-d PROTECTED PREVIEW:** COMPLIANT. The diff does not affect the protected reference.

11. **L-e PUNCTUATED BEFORE READ:** COMPLIANT. The function ensures that transcripts are punctuated before being read (lines 251-267).

12. **L-f CHANNELS FIRST:** COMPLIANT. The function ensures that story candidates are derived from channel clusters first.

13. **L-g WRITTEN FORMS:** COMPLIANT. The function ensures that written forms are read as spoken (lines 251-267).

14. **L-h TEXT READ AS SPOKEN:** COMPLIANT. The function ensures that text is read as spoken before processing (lines 251-267).

15. **L-i THE CLAIM IS THE EVENT:** COMPLIANT. The function ensures that the claim is the event being judged.

16. **L-j RELEASE IS AUTHORISED ON THESE BYTES:** COMPLIANT. The function ensures that releases are authorized based on the exact bytes measured (lines 683-727).

17. **L-k ONE CANONICAL FORM:** COMPLIANT. The function ensures that text comparisons use a canonical form.

18. **LAW 20 / M2:** COMPLIANT. The function ensures that gate thresholds are constants and failures are hard stops.

19. **M12 FAIL CLOSED:** COMPLIANT. The function ensures that missing data or model failures result in a rejection.

20. **LAW 22:** COMPLIANT. The function ensures that the v2f reference keeps re-rendering byte-identically.

### Q3: TESTS

1. **Test Coverage:** The tests cover various scenarios, including missing required rows, non-PASS verdicts, unknown rows, and evidence issues (lines 740-1032).

2. **Must-Fail Fixtures:** The tests ensure that must-fail fixtur

## GEMINI — CYCLE 1 OUTPUT
Excellent. This is a substantial and critical change to the pipeline's quality and release process. I will review it against the provided laws and context.

---

### Q1: CORRECTNESS

The changed functions appear to do what their docstrings and the governing laws state. The design philosophy is clearly "fail-closed," and this is implemented robustly.

*   **`release_auth.py` (new file):** This module is the centerpiece.
    *   `blockers()` (line 580): Correctly implements the inventory check. It fails on missing required rows, non-`PASS` verdicts for required rows, unexpected rows, and invalid verdicts. It also correctly treats `MONITORING` rows as needing to be present but not deciding the outcome (lines 598-600). The check for execution evidence (lines 604-611), requiring `executed: True` and `samples >= 1`, is a strong guard against vacuous passes.
    *   `attest()` (line 638): This function correctly creates a verifiable snapshot. It reads from disk, calculates current hashes, and compares against what the gates measured (lines 662-665). It correctly includes the run state (`run_state.get("ok") is True`, line 668), ensuring that a run with any `holds` cannot be attested as passing. The atomic write via `os.replace` is good practice.
    *   `authorise()` (line 683): This is a correct and paranoid re-verification. It doesn't trust the verdict in `ATTESTATION.json`; instead, it re-runs `blockers()` on the attested rows (line 702). It re-hashes every bound file and compares it to the attested digest (lines 719-727). This function correctly ensures that what is being authorized for delivery is *exactly* what was checked and approved, moment-by-moment.

*   **`run_fresh.py`:**
    *   `stage_gates()` has been refactored for clarity and safety. The new `put()` helper function (line 87) ensures gate results are stored in a structured way, separating the verdict from notes and evidence. This is much safer than parsing string prefixes like `"PASS(L-c: ...)"`.
    *   The implementation of Law L-c (lines 215-249) is updated to use `L.edges_on_final`, directly matching the amended law's text which requires measuring on the final deliverable. This is a crucial correctness fix.
    *   The new `verdict_for()` (line 303) correctly delegates the verdict logic to `release_auth.blockers`, removing the old, fragile string-prefix-based logic. This is a huge improvement.
    *   `record_assets()` (line 311) is now more robust. It correctly checks for modifications against the *launch* revision (`launch`), not `HEAD` (line 343), which prevents race conditions in a busy repository.
    *   `attest_run()` (line 357) is the final checkpoint. It correctly aggregates all potential failure reasons (existing holds, non-candidate verdict, dirty code) and creates a final attestation. Line 377 is critical: `if att["verdict"] != "ALL_PASS" and run.status.get("verdict") == VERDICT_CANDIDATE: run.status["verdict"] = VERDICT_HOLD`. This ensures the run's final saved state can never disagree with the attestation, creating a single source of truth.

No obvious off-by-one errors, unit mismatches, or silent exceptions were found. The entire change is geared towards preventing a `PASS` on missing or failed data, in compliance with M12.

### Q2: LAW COMPLIANCE

The code appears to be compliant with all applicable laws.

*   **SENTENCE LAW, SELECTION LOCK, SNAP LIMIT, NEIGHBOUR, ONSET/TAIL, CREDITS:** The implementation of these laws is not in the diff, but their enforcement is significantly strengthened. Gates like `G16_sentence_boundary`, `G17_onset_tail`, and `G15_credits` are now listed as `REQUIRED` in `release_auth.py` (lines 556-557). Any verdict other than exactly `PASS` will block the release. **COMPLIANT**.
*   **L-a SIGN-OFF NAMES ALL:** `G20_signoff_names_all` is a `REQUIRED` gate (line 557). **COMPLIANT**.
*   **L-b EDGE WORDS WHOLE:** Enforced via the `G17_onset_tail` required gate. **COMPLIANT**.
*   **L-c DISSENT IS RIGHT UNTIL DISPROVED:** The diff contains a direct and correct implementation of the amended law. `run_fresh.py:235` calls `L.edges_on_final` to get proof from the bytes being approved, and this proof is used to adjudicate G3b/G3c disagreements (lines 237-247). **COMPLIANT**.
*   **L-d PROTECTED PREVIEW:** No changes in the diff relate to this law. **CANNOT VERIFY**.
*   **L-e to L-i, L-k:** The code implementing these laws is not in the diff. However, the new framework ensures that if any of these laws are violated in a way that causes a gate to return a non-`PASS` verdict, the release will be blocked. The enforcement mechanism is compliant. **PARTIAL (enforcement mechanism is compliant)**.
*   **L-j RELEASE IS AUTHORISED ON THESE BYTES:** This is the primary focus of the diff. The new `release_auth.py` module, its comprehensive tests, and its integration as the final step in `run_fresh.py` and the first step of delivery (as implied by docstrings) is a robust and complete implementation of this law. The removal of

## CLAUDE'S CYCLE 1 CONSENSUS
# CONSENSUS REPORT — PULSE-SENTENCE-LAW — CYCLE 1
Generated: 2026-11-11 22:29
Models: grok, gpt4o, gemini

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Correctness | 9/10 | 8/10 | 9/10 | **9/10** |
| Law Compliance | 9/10 | 9/10 | 8/10 | **9/10** |
| Test Quality | 10/10 | 9/10 | 10/10 | **10/10** |
| Security / Fail-Closed | 10/10 | 9/10 | 9/10 | **9/10** |
| Overall Readiness | 9/10 | 8/10 | 8/10 | **READY** |

> Score derivation: Gemini and Grok explicitly flagged only LOW items; GPT-4o mislabeled correct behavior as HIGH/MEDIUM issues. Consensus deflates GPT-4o's overall score accordingly.

---

## UNANIMOUS FINDINGS (all 3 models agree — implement unconditionally)

**None.** No single defect was identified by all three models as an actionable bug requiring a code change. All three converged on the same architectural observation — the fail-closed design is correct — but each flagged *different* minor issues. The absence of unanimous defects is itself a strong signal of code quality.

---

## MAJORITY FINDINGS (2 of 3 models agree)

### M1 — G17_onset_tail evidence write ordering (Grok + Gemini)
- **What:** `run_fresh.py:212` — The G17 onset/tail evidence is written to the ledger *after* the `put()` call rather than being bundled atomically inside it. If an exception fires between `put()` and the evidence write, the gate record lands with a `PASS` verdict but no evidence. `release_auth.blockers()` would then correctly reject it (evidence check at line 604–611), but the inconsistency creates a confusing diagnostic state.
- **File/Line:** `run_fresh.py:212`
- **Fix:** Move the `_samples` / evidence population into the `put()` call site, or inside `put()` itself, so verdict and evidence are written atomically. If `put()` accepts an `evidence=` kwarg, pass it there.

### M2 — Stale comment referencing G11 (Gemini + implicit in Grok's structural review)
- **What:** `run_fresh.py:104` — Comment `G11_parity(run_gates) ... see G11 below` predates the refactor and no longer accurately describes the surrounding logic.
- **File/Line:** `run_fresh.py:104`
- **Fix:** Update or remove the stale comment so future readers are not misled.

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### U1 — `replay` exception path does not call `write_report` (Grok only)
- **What:** `replay.py:21-23` — When `attest_run` raises, the except block sets the verdict to HOLD but never calls `write_report` a second time. The on-disk report therefore still carries whatever partial state existed before the exception.
- **Assessment:** **Investigate further.** If `replay` is ever called in a context where the report file is consumed downstream before the caller inspects the return value, the stale file is a real (if unlikely) hazard. If `replay` is always a diagnostic-only path where the caller exclusively trusts the return value, this is cosmetic. Recommend adding a defensive `write_report` call in the except b

---

## ORIGINAL CODE (same code as Cycle 1)
## THE CODE (every new and modified file)

### File: docs/audits/pulse-sentence-law/CURRENT.diff (1033 lines)
```
   1 | diff --git a/pipeline/replay.py b/pipeline/replay.py
   2 | index 275f1d9c..b7522fab 100644
   3 | --- a/pipeline/replay.py
   4 | +++ b/pipeline/replay.py
   5 | @@ -42,7 +42,7 @@ def make_copy(run_dir, start, stamp=None):
   6 |          else:
   7 |              shutil.copytree(a, b)
   8 |      k = rf.TAIL_STAGES.index(start)
   9 | -    stale = ["GATE_REPORT.json", "VERDICT.txt"]
  10 | +    stale = ["GATE_REPORT.json", "VERDICT.txt", "ATTESTATION.json"]
  11 |      if k <= 2:
  12 |          stale += ["out/segment.mp4", "out/segment_vertical.mp4"]
  13 |      for p in stale:
  14 | @@ -86,6 +86,12 @@ def replay(run_dir, start="prepare", vision=True, stamp=None):
  15 |      finally:
  16 |          run.status["elapsed_s"] = round(time.time() - t0, 1)
  17 |          run.status["ended"] = rf.now_iso()
  18 | +        try:                                            # attested for its verdict, never deliverable
  19 | +            rf.attest_run(run, deliverable=False, why_not="replay: diagnostic, deliver only a full run",
  20 | +                          code_checked=False)
  21 | +        except Exception as e:
  22 | +            run.status["verdict"] = rf.VERDICT_HOLD
  23 | +            run.status["holds"].append(f"attestation: {type(e).__name__}: {e}")
  24 |          run.save()
  25 |          rf.write_report(run)
  26 |          with open(os.path.join(dst, "VERDICT.txt"), "w") as f:
  27 | diff --git a/pipeline/run.py b/pipeline/run.py
  28 | index bbd42573..a6157957 100644
  29 | --- a/pipeline/run.py
  30 | +++ b/pipeline/run.py
  31 | @@ -180,8 +180,9 @@ def stage_gates9(segment_dir, args):
  32 |  
  33 |  
  34 |  def stage_telegram(segment_dir, args):
  35 | -    from telegram_drop import send_telegram_preview
  36 | -    send_telegram_preview(segment_dir, args.qa_version)
  37 | +    """Removed (red-team A): this legacy path imported a module that does not exist (telegram_drop) and trusted
  38 | +    VERIFIED_BY_ORCHESTRATOR. The only send path is telegram.deliver_run on an authorised run_fresh run."""
  39 | +    raise RuntimeError("STOP: run.py telegram stage removed; deliver with telegram.deliver_run (release_auth)")
  40 |  
  41 |  
  42 |  # ── Legacy stage_all (fail-closed fix: check return values) ──
  43 | diff --git a/pipeline/run_fresh.py b/pipeline/run_fresh.py
  44 | index ae5f149a..81b81061 100644
  45 | --- a/pipeline/run_fresh.py
  46 | +++ b/pipeline/run_fresh.py
  47 | @@ -776,11 +776,20 @@ def _status(ok):
  48 |      return "PASS" if ok else "FAIL"
  49 |  
  50 |  
  51 | -def tail_rows(g9_pass, conform_fallback):
  52 | +def _samples(x):
  53 | +    """How many things a gate measured (list / dict entries); a skipped or empty result measured nothing
  54 | +    (release_auth requires >= 1 for every required row: red-team A, 'the gates ran')."""
  55 | +    if isinstance(x, dict) and x.get("skip"):
  56 | +        return 0
  57 | +    return len(x) if isinstance(x, (list, dict)) else 0
  58 | +
  59 | +
  60 | +def tail_rows(g9_pass, conform_fallback, identical=True):
  61 |      """G9_tail is the DEC-1 calibrated gate alone (no exception path). outro_locked: the luma floor is
  62 |      the approved reference's LOCKED outro tail, so a conform fallback (some other outro) fails closed
  63 | -    on its own row even when its tail clears the floor (Heimdall DEC-1 audit: keep the two apart)."""
  64 | -    return {"G9_tail": _status(g9_pass), "outro_locked": _status(not conform_fallback)}
  65 | +    on its own row even when its tail clears the floor (Heimdall DEC-1 audit: keep the two apart), and so
  66 | +    does an outro whose master or conformed file is not hash-identical to the locked one (GPT-cut F09)."""
  67 | +    return {"G9_tail": _status(g9_pass), "outro_locked": _status(identical and not conform_fallback)}
  68 |  
  69 |  
  70 |  def stage_gates(run, final16, man16, final9, man9):
  71 | @@ -799,6 +808,8 @@ def stage_gates(run, final16, man16, final9, man9):
  72 |          segs16 = json.load(f)["segments"]
  73 |      with open(man9) as f:
  74 |          segs9 = json.load(f)["segments"]
  75 | +    # the bytes every gate below measures (release_auth: the attested files must be these files)
  76 | +    measured = {os.path.relpath(p, run.dir): sha256(p) for p in (final16, final9, man16, man9)}
  77 |  
  78 |      # Production gate runner — invoked exactly as in the v2f run.
  79 |      # G8 needs its sources (2026-11-11: it was never given any, so it always failed "no_source" and was
  80 | @@ -812,18 +823,33 @@ def stage_gates(run, final16, man16, final9, man9):
  81 |      rows = {"16x9": {}, "9x16": {}}
  82 |      flags = {"16x9": [], "9x16": []}
  83 |      limits = {"16x9": [], "9x16": []}
  84 | +    notes = {"16x9": {}, "9x16": {}}          # why a row reads what it reads (rows hold exact verdicts only)
  85 | +    evidence = {"16x9": {}, "9x16": {}}       # that the gate ran, and on how many samples
  86 | +
  87 | +    def put(fmt, row, verdict, data, note=None):
  88 | +        """One gate row: an exact verdict (release_auth.VERDICTS, no prefixes, no waiver text), what it measured,
  89 | +        and the reason in notes."""
  90 | +        rows[fmt][row] = verdict
  91 | +        evidence[fmt][row] = {"executed": verdict != "SKIPPED", "samples": _samples(data)}
  92 | +        if note:
  93 | +            notes[fmt][row] = note
  94 | +        elif row in notes[fmt]:
  95 | +            del notes[fmt][row]
  96 | +
  97 |      for fmt, res in (("16x9", r16), ("9x16", r9)):
  98 |          for k, v in res.items():
  99 |              if isinstance(v, dict) and "pass" in v and k not in ("G8_sharpness", "G9_tail",
 100 |                                                                     "G11_parity"):
 101 |                  # a skipped gate is never reported as a PASS (fail-closed)
 102 | -                rows[fmt][k] = (f"SKIPPED ({v.get('reason', 'skip')})" if v.get("skip")
 103 | -                                else _status(v["pass"]))
 104 | -        rows[fmt]["G11_parity(run_gates)"] = "NOT RUN BY run_gates (no horiz) — see G11 below"
 105 | +                if v.get("skip"):
 106 | +                    put(fmt, k, "SKIPPED", None, v.get("reason", "skip"))
 107 | +                else:
 108 | +                    put(fmt, k, _status(v["pass"] is True), v.get("table", v.get("data")))
 109 | +        # G11 inside run_gates has no horizontal final (it skips); the real G11 is the 9x16 row below
 110 |  
 111 |      # G11 for real (vertical vs horizontal)
 112 |      g11_ok, g11 = qa_gates.gate_g11(final9, final16, segs9, segs16)
 113 | -    rows["9x16"]["G11_parity"] = _status(g11_ok)
 114 | +    put("9x16", "G11_parity", _status(g11_ok), g11)
 115 |  
 116 |      # G14 / G14c / G15
 117 |      def _words(vid):                                  # DEC-12e: G14 samples where the transcript has speech
 118 | @@ -851,8 +877,8 @@ def stage_gates(run, final16, man16, final9, man9):
 119 |      man16_g14, man9_g14 = _g14_manifest(man16, "16x9"), _g14_manifest(man9, "9x16")
 120 |      g14_16_ok, g14_16 = G.gate_g14(final16, man16_g14, source_clips=src_clips, qa_dir=g14dir16)
 121 |      fails16 = [d for d in g14_16 if d.get("status") == "FAIL"]
 122 | -    rows["16x9"]["G14_av_alignment"] = ("PASS" if g14_16_ok else
 123 | -                                        "FAIL" if fails16 else "HOLD(inconclusive)")
 124 | +    put("16x9", "G14_av_alignment", "PASS" if g14_16_ok else "FAIL" if fails16 else "HOLD", g14_16,
 125 | +        None if g14_16_ok or fails16 else "inconclusive")
 126 |      limits["16x9"].append("G14: static talking-head temporal slips can pass frame_sim "
 127 |                            "(v2e 18.0-24.0 s precedent); VO sections are auto-PASS (pre-roll "
 128 |                            "declared), plate correctness not verified")
 129 | @@ -860,13 +886,14 @@ def stage_gates(run, final16, man16, final9, man9):
 130 |      # the gate's own per-segment verdict (DEC-12e): >= 3 conclusive matching samples, zero mismatches
 131 |      g14_9_ok, g14_9 = G.gate_g14(final9, man9_g14, source_clips=src_clips, qa_dir=g14dir9, frames=False)
 132 |      fails9 = [d for d in g14_9 if d.get("status") == "FAIL"]
 133 | -    rows["9x16"]["G14_audio_offset"] = ("PASS" if g14_9_ok else "FAIL" if fails9 else "HOLD(inconclusive)")
 134 | -    rows["9x16"]["G14_frame_similarity"] = "LIMITED (not valid for 9:16 crop vs 16:9 source)"
 135 | +    put("9x16", "G14_audio_offset", "PASS" if g14_9_ok else "FAIL" if fails9 else "HOLD", g14_9,
 136 | +        None if g14_9_ok or fails9 else "inconclusive")
 137 | +    put("9x16", "G14_frame_similarity", "LIMITED", None, "not valid for 9:16 crop vs 16:9 source")
 138 |      limits["9x16"].append("G14 frame_sim compares a 9:16 crop with the 16:9 source (v2e positive "
 139 |                            "control: 0.24-0.54 on correct frames); only the audio-offset part is "
 140 |                            "scored; VO sections auto-PASS")
 141 |      g14c_ok, g14c = G.gate_g14c(final16, final9, tolerance_ms=42)
 142 | -    rows["9x16"]["G14c_duration_parity"] = _status(g14c_ok)
 143 | +    put("9x16", "G14c_duration_parity", _status(g14c_ok), g14c)
 144 |      for sub in ("g15_16x9", "g15_9x16"):
 145 |          os.makedirs(os.path.join(qa, sub), exist_ok=True)
 146 |      import credit_rings                             # DEC-11: G15 also checks each disc is the credited avatar
 147 | @@ -874,15 +901,15 @@ def stage_gates(run, final16, man16, final9, man9):
 148 |          credited = credit_rings.credit_channels(json.load(f))
 149 |      g15_16_ok, g15_16 = G.gate_g15(final16, segs16, os.path.join(qa, "g15_16x9"), channels=credited)
 150 |      g15_9_ok, g15_9 = G.gate_g15(final9, segs9, os.path.join(qa, "g15_9x16"), channels=credited)
 151 | -    rows["16x9"]["G15_credits"] = _status(g15_16_ok)
 152 | -    rows["9x16"]["G15_credits"] = _status(g15_9_ok)
 153 | +    put("16x9", "G15_credits", _status(g15_16_ok), g15_16)
 154 | +    put("9x16", "G15_credits", _status(g15_9_ok), g15_9)
 155 |      # G20 SIGNOFF_NAMES_ALL (law L-a): the rendered sign-off names exactly the credited channels
 156 |      for sub in ("g20_16x9", "g20_9x16"):
 157 |          os.makedirs(os.path.join(qa, sub), exist_ok=True)
 158 |      g20_16_ok, g20_16 = G.gate_g20(final16, segs16, credited, os.path.join(qa, "g20_16x9"))
 159 |      g20_9_ok, g20_9 = G.gate_g20(final9, segs9, credited, os.path.join(qa, "g20_9x16"))
 160 | -    rows["16x9"]["G20_signoff_names_all"] = _status(g20_16_ok)
 161 | -    rows["9x16"]["G20_signoff_names_all"] = _status(g20_9_ok)
 162 | +    put("16x9", "G20_signoff_names_all", _status(g20_16_ok), g20_16)
 163 | +    put("9x16", "G20_signoff_names_all", _status(g20_9_ok), g20_9)
 164 |  
 165 |      # G8 — production result + source-relative report (threshold untouched)
 166 |      g8dir = os.path.join(qa, "g8_relative")
 167 | @@ -898,7 +925,7 @@ def stage_gates(run, final16, man16, final9, man9):
 168 |                   "relative_16x9": g8rel, "degraded_below_0.85": degraded}
 169 |      for fmt, res in (("16x9", r16), ("9x16", r9)):
 170 |          # DEC-1 floor + DEC-3 soft-source rule live in the gate itself; no waiver (DEC-8)
 171 | -        rows[fmt]["G8_sharpness"] = _status(res["G8_sharpness"]["pass"])
 172 | +        put(fmt, "G8_sharpness", _status(res["G8_sharpness"]["pass"] is True), res["G8_sharpness"].get("table"))
 173 |  
 174 |      # G9 — approved known exception only if the outro is hash-identical to the locked outro
 175 |      g9_report = {}
 176 | @@ -914,7 +941,8 @@ def stage_gates(run, final16, man16, final9, man9):
 177 |          g9_report[fmt] = {"gate": d, "outro_master_sha256": msha, "outro_conformed_sha256": csha,
 178 |                            "hash_identical_to_locked_outro": identical,
 179 |                            "last_segment": last.get("label"), "conform_fallback": fallback}
 180 | -        rows[fmt].update(tail_rows(res["G9_tail"]["pass"], fallback))
 181 | +        for row, verdict in tail_rows(res["G9_tail"]["pass"] is True, fallback, identical).items():
 182 | +            put(fmt, row, verdict, d if row == "G9_tail" else g9_report[fmt])
 183 |  
 184 |      # G4 per shot + G4s layout truth (DEC-2 / DEC-5)
 185 |      import vertical_layout as V
 186 | @@ -928,15 +956,15 @@ def stage_gates(run, final16, man16, final9, man9):
 187 |          with open(man) as f:
 188 |              shout = json.load(f).get("shoutout_start", 0)
 189 |          ok, g4_shots[fmt] = qa_gates.gate_g4(final, V.per_shot_manifest(sgs, plans), fmt, shout, g4dir)
 190 | -        rows[fmt]["G4_faces_per_shot"] = _status(ok)
 191 | +        put(fmt, "G4_faces_per_shot", _status(ok), g4_shots[fmt])
 192 |          ok, g4s[fmt] = V.gate_g4s(plans, prepared, vert_final=final9 if fmt == "9x16" else None,
 193 |                                    vert_segments=segs9 if fmt == "9x16" else None)
 194 | -        rows[fmt]["G4s_layout_truth"] = _status(ok)
 195 | +        put(fmt, "G4s_layout_truth", _status(ok), g4s[fmt])
 196 |  
 197 |      # G16 SENTENCE_BOUNDARY: re-run on the final cut state (format-independent; same row in both)
 198 |      g16_ok, g16 = L.gate_g16(run.dir)
 199 |      for fmt in ("16x9", "9x16"):
 200 | -        rows[fmt]["G16_sentence_boundary"] = _status(g16_ok)
 201 | +        put(fmt, "G16_sentence_boundary", _status(g16_ok), g16)
 202 |  
 203 |      # G17 ONSET/TAIL: prepared clips (>= 80 ms genuine lead-in/tail) + each final (edge words >= 85 %)
 204 |      g17a_ok, g17a = L.gate_g17_prepared({c["clip_id"]: os.path.join(qa, f"final_{c['clip_id']}.mp4")
 205 | @@ -946,29 +974,36 @@ def stage_gates(run, final16, man16, final9, man9):
 206 |      # G17c (law L-b): the first and last word of every prepared clip, with their decay, at full level
 207 |      # (within 1 dB of the unfaded source); format-independent, part of the G17 row in both formats
 208 |      g17c_ok, g17c = L.gate_g17_edges(run.dir)
 209 | -    rows["16x9"]["G17_onset_tail"] = _status(g17a_ok and g17b16_ok and g17c_ok)
 210 | -    rows["9x16"]["G17_onset_tail"] = _status(g17a_ok and g17b9_ok and g17c_ok)
 211 | +    for fmt, b_ok, b in (("16x9", g17b16_ok, g17b16), ("9x16", g17b9_ok, g17b9)):
 212 | +        put(fmt, "G17_onset_tail", _status(g17a_ok and b_ok and g17c_ok), None)
 213 | +        evidence[fmt]["G17_onset_tail"]["samples"] = min(_samples(g17a), _samples(b), _samples(g17c))
 214 |  
 215 |      # law L-c: a check that disagrees with the others on an EDGE WORD is right until an acoustic comparison
 216 |      # with the source proves otherwise: G17c (the kept word and decay equal the unfaded source) and G16 (no
 217 |      # audible part of the neighbour word, neighbour_clear). A dissenting G3b reading needs that proof, else
 218 |      # HOLD; a G3c head / tail failure on an edge is overruled only by it, else it stands.
 219 | -    def _edge_proved(seg, side):
 220 | -        return g16_ok and bool((g17c.get(seg) or {}).get(side, {}).get("ok"))
 221 | +    # Amended (orchestrator addendum 2026-11-11 '22:00', GPT-cut F03): the G17c comparison that proves an edge
 222 | +    # is measured on the FINAL of that format (the bytes being approved, sentence_law.edges_on_final), never on
 223 | +    # the prepared clip; when it cannot prove the edge, the dissent / the failure stands and the run HOLDS.
 224 |      lc = {}
 225 | -    for fmt, res in (("16x9", r16), ("9x16", r9)):
 226 | +    for fmt, res, final, sgs in (("16x9", r16, final16, segs16), ("9x16", r9, final9, segs9)):
 227 |          g3b = (res.get("G3b_cut_out_clean") or {}).get("table") or []
 228 |          dissent = [e["segment"] for e in g3b if isinstance(e, dict) and e.get("dissent") and e.get("last_found")]
 229 | -        unproved = [sg for sg in dissent if not _edge_proved(sg, "out")]
 230 | -        if rows[fmt].get("G3b_cut_out_clean") == "PASS" and unproved:
 231 | -            rows[fmt]["G3b_cut_out_clean"] = f"HOLD(dissent unproved: {', '.join(unproved)})"
 232 |          g3c = (res.get("G3c_acoustic_tail") or {}).get("table") or []
 233 |          failed = [(e["segment"], side) for e in g3c if isinstance(e, dict)
 234 |                    for side, key in (("out", "tail_ok"), ("in", "head_ok")) if e.get(key) is False]
 235 | +        proof = L.edges_on_final(final, sgs, run.dir) if (dissent or failed) else {}
 236 | +
 237 | +        def _edge_proved(seg, side, proof=proof):
 238 | +            return g16_ok and ((proof.get(seg) or {}).get(side) or {}).get("ok") is True
 239 | +        unproved = [sg for sg in dissent if not _edge_proved(sg, "out")]
 240 | +        if rows[fmt].get("G3b_cut_out_clean") == "PASS" and unproved:
 241 | +            put(fmt, "G3b_cut_out_clean", "HOLD", g3b, f"dissent unproved on the final: {', '.join(unproved)}")
 242 |          if rows[fmt].get("G3c_acoustic_tail") == "FAIL" and failed and all(_edge_proved(sg, sd) for sg, sd in failed):
 243 | -            rows[fmt]["G3c_acoustic_tail"] = "PASS(L-c: " + ", ".join(f"{sg} {sd}" for sg, sd in failed) + \
 244 | -                " proved by the source comparison)"
 245 | -        lc[fmt] = {"g3b_dissent": dissent, "g3b_unproved": unproved, "g3c_failed_edges": failed}
 246 | +            put(fmt, "G3c_acoustic_tail", "PASS", g3c, "L-c: " + ", ".join(f"{sg} {sd}" for sg, sd in failed) +
 247 | +                " proved by the comparison of the final's audio with the source")
 248 | +        lc[fmt] = {"g3b_dissent": dissent, "g3b_unproved": unproved, "g3c_failed_edges": failed,
 249 | +                   "final_proof": proof}
 250 |  
 251 |      # G18 WORD-FOR-WORD (mission 4a): every clip's first/last words are its locked sentences' and its
 252 |      # words are exactly those of the source span it was cut from (both finals; whisper on GPU0)
 253 | @@ -979,13 +1014,15 @@ def stage_gates(run, final16, man16, final9, man9):
 254 |               **{f"clip_{c['index']:02d}": c.get("selection_lock") for c in edl_now.get("clips", [])}}
 255 |      g18_clips = {c["clip_id"]: {"lock_text": (locks.get(c["clip_id"]) or {}).get("text", ""),
 256 |                                  "source": os.path.join(run.dir, "sources", f"{c['video_id']}.mp4"),
 257 | -                                "cut_in": c["cut_in"], "cut_out": c["cut_out"]} for c in cuts}
 258 | +                                "cut_in": c["cut_in"], "cut_out": c["cut_out"],
 259 | +                                "pad_s": float(c.get("lead_in_pad_s") or 0.0)} for c in cuts}
 260 |      missing = [cid for cid, c in g18_clips.items() if not c["lock_text"]]
 261 |      tr = WD.Transcriber()
 262 |      g18 = {}
 263 |      for fmt, final, sgs in (("16x9", final16, segs16), ("9x16", final9, segs9)):
 264 |          ok, g18[fmt] = WD.gate_g18(final, sgs, g18_clips, transcriber=tr)
 265 | -        rows[fmt]["G18_word_for_word"] = _status(ok and not missing)
 266 | +        put(fmt, "G18_word_for_word", _status(ok and not missing), g18[fmt],
 267 | +            f"no selection lock: {missing}" if missing else None)
 268 |      del tr
 269 |      if missing:
 270 |          g18["missing_selection_lock"] = missing
 271 | @@ -999,27 +1036,30 @@ def stage_gates(run, final16, man16, final9, man9):
 272 |      g19 = {}
 273 |      for fmt, final, sgs in (("16x9", final16, segs16), ("9x16", final9, segs9)):
 274 |          ok, g19[fmt] = edge_shots.gate_g19(final, sgs, snap_rec, FPS)
 275 | -        rows[fmt]["G19_edge_shots"] = _status(ok)
 276 | +        put(fmt, "G19_edge_shots", _status(ok), g19[fmt])
 277 |  
 278 |      fb = run.prov["vertical_fallback_check"]
 279 | -    rows["9x16"]["vertical_silent_fallback"] = "FAIL (fallback occurred)" if fb["fallback_occurred"] \
 280 | -        else "PASS (no fallback)"
 281 | +    put("9x16", "vertical_silent_fallback", _status(fb["fallback_occurred"] is False), fb,
 282 | +        "fallback occurred" if fb["fallback_occurred"] else "no fallback")
 283 |  
 284 | -    gates_out = {"rows": rows, "flags": flags, "limitations": limits,
 285 | +    import release_auth
 286 | +    gates_out = {"inventory_version": release_auth.INVENTORY_VERSION, "rows": rows, "notes": notes,
 287 | +                 "evidence": evidence, "measured_files": measured, "flags": flags, "limitations": limits,
 288 |                   "G11": g11, "G14_16x9": g14_16, "G14_9x16": g14_9, "G14c": g14c,
 289 |                   "G15_16x9": g15_16, "G15_9x16": g15_9, "G20_16x9": g20_16, "G20_9x16": g20_9, "G17c": g17c, "L-c": lc, "G8": g8_report, "G9": g9_report, "G16": g16,
 290 |                   "G17": {"prepared": g17a, "16x9": g17b16, "9x16": g17b9}, "G18": g18, "G19": g19,
 291 |                   "G4_per_shot": g4_shots, "G4s": g4s,
 292 |                   "run_gates_overall": {"16x9": ok16, "9x16": ok9}}
 293 |      jdump(os.path.join(run.dir, "GATE_REPORT.json"), gates_out)
 294 | -    run.prov["gates"] = {"rows": rows, "flags": flags, "limitations": limits}
 295 | +    run.prov["gates"] = {"rows": rows, "notes": notes, "flags": flags, "limitations": limits}
 296 |      return rows, flags, limits
 297 |  
 298 |  
 299 | -def verdict_for(rows):
 300 | -    bad = {k: v for k, v in rows.items()
 301 | -           if not (v.startswith("PASS") or v.startswith("FLAG") or v.startswith("LIMITED")
 302 | -                   or v.startswith("NOT RUN BY run_gates"))}
 303 | +def verdict_for(rows, fmt, evidence=None):
 304 | +    """(verdict, {row: why}) by release_auth's exact inventory for that format: a missing, unknown, skipped,
 305 | +    inconclusive or unexecuted row is a blocker (red-team A; no prefix rules)."""
 306 | +    import release_auth
 307 | +    bad = release_auth.blockers(fmt, rows, evidence)
 308 |      return (VERDICT_HOLD if bad else VERDICT_CANDIDATE), bad
 309 |  
 310 |  
 311 | @@ -1074,21 +1114,33 @@ def record_assets(run):
 312 |      run.prov["v2f_reuse_check"] = {"links_into_v2f_material": leaks,
 313 |                                     "source_ids_overlap": sorted(
 314 |                                         {s["video_id"] for s in srcs} & V2F_VIDEO_IDS)}
 315 | -    # executed code hashes
 316 | -    mods = {}
 317 | +    # executed code hashes: every loaded module of THIS checkout, compared with the LAUNCH revision (not
 318 | +    # whatever HEAD is now: GPT-cut F24); a module loaded from another checkout of the pipeline (a hard-coded
 319 | +    # path, a worktree run importing the main tree) is code that did not come from this run's revision
 320 | +    # (Claude-gates C4)
 321 | +    launch = (run.prov.get("code") or {}).get("git_head") or "HEAD"
 322 | +    mods, foreign = {}, []
 323 |      for name, m in list(sys.modules.items()):
 324 |          f = getattr(m, "__file__", None)
 325 | -        if f and f.startswith(REPO) and "/venv/" not in f and os.path.exists(f):
 326 | +        if not f or not os.path.exists(f) or "/venv/" in f or "site-packages" in f or "dist-packages" in f:
 327 | +            continue
 328 | +        f = os.path.realpath(f)
 329 | +        if f.startswith(REPO + os.sep):
 330 |              mods[os.path.relpath(f, REPO)] = sha256(f)
 331 | +        elif re.search(r"/(protocol_pulse|worktrees)/", f):
 332 | +            foreign.append(f)
 333 |      run.prov["executed_code_sha256"] = dict(sorted(mods.items()))
 334 | -    not_clean = []
 335 | +    not_clean = [f"{f} (outside this checkout {REPO})" for f in sorted(foreign)]
 336 | +    head_now = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip()
 337 | +    if launch != "HEAD" and head_now != launch:
 338 | +        not_clean.append(f"HEAD moved during the run: {launch} -> {head_now}")
 339 |      for rel in mods:
 340 |          tracked = subprocess.run(["git", "ls-files", "--error-unmatch", rel], cwd=REPO,
 341 |                                   capture_output=True).returncode == 0
 342 | -        modified = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", rel], cwd=REPO,
 343 | +        modified = subprocess.run(["git", "diff", "--quiet", launch, "--", rel], cwd=REPO,
 344 |                                    capture_output=True).returncode != 0
 345 |          if not tracked or modified:
 346 | -            not_clean.append(f"{rel} ({'untracked' if not tracked else 'modified vs HEAD'})")
 347 | +            not_clean.append(f"{rel} ({'untracked' if not tracked else 'modified vs the launch revision'})")
 348 |      run.prov["executed_code_not_at_revision"] = not_clean
 349 |      if not_clean:
 350 |          run.status["holds"].append(f"executed code not at the recorded revision: {not_clean}")
 351 | @@ -1162,6 +1214,36 @@ def write_report(run):
 352 |          f.write("\n".join(L) + "\n")
 353 |  
 354 |  
 355 | +# ── release attestation ──
 356 | +
 357 | +def attest_run(run, deliverable=True, why_not=None, code_checked=True):
 358 | +    """ATTESTATION.json (release_auth.attest), written last: holds anywhere => HOLD (GPT-cut F10), and the run is
 359 | +    ok only when it ended a candidate with no hold, its tree was clean at launch and every executed module is at
 360 | +    the launch revision (GPT-cut F24, Claude-gates C4). A replay (code_checked=False) has no provenance pass of its
 361 | +    own: it is attested for its verdict and is never deliverable."""
 362 | +    import release_auth
 363 | +    if run.status.get("holds"):
 364 | +        run.status["verdict"] = VERDICT_HOLD
 365 | +    code = run.prov.get("code") or {}
 366 | +    why = list(run.status.get("holds") or [])
 367 | +    if run.status.get("verdict") != VERDICT_CANDIDATE:
 368 | +        why.append(f"verdict {run.status.get('verdict')}")
 369 | +    if code_checked and code.get("pipeline_tree_clean_at_launch") is not True:
 370 | +        why.append("tree not recorded clean at launch")
 371 | +    if code_checked and run.prov.get("executed_code_not_at_revision") != []:
 372 | +        why.append(f"executed code not at the launch revision: {run.prov.get('executed_code_not_at_revision')}")
 373 | +    state = {"ok": not why, "why": why, "verdict": run.status.get("verdict"), "mode": run.mode,
 374 | +             "git_head": code.get("git_head"), "ended": run.status.get("ended")}
 375 | +    att = release_auth.attest(run.dir, state, deliverable=deliverable, why_not=why_not)
 376 | +    run.status["attestation"] = {"verdict": att["verdict"], "deliverable": att["deliverable"]}
 377 | +    if att["verdict"] != "ALL_PASS" and run.status.get("verdict") == VERDICT_CANDIDATE:
 378 | +        run.status["verdict"] = VERDICT_HOLD          # the attestation is the release truth; never two answers
 379 | +        run.status["holds"].append("attestation: " + "; ".join(
 380 | +            [f"{fmt} {k}: {v}" for fmt, b in att["blockers"].items() for k, v in b.items()]
 381 | +            + att["verification"]["why"] + att["other_blockers"] + [f"missing {m}" for m in att["missing_files"]]))
 382 | +    return att
 383 | +
 384 | +
 385 |  # ── main ──
 386 |  
 387 |  TAIL_STAGES = ("prepare", "layout", "render", "gates")
 388 | @@ -1185,16 +1267,17 @@ def run_tail(run, cuts, start="prepare", vision=True):
 389 |      # mission 4a / DEC-8: the automated verification pack (words, joins, credits) for the drop
 390 |      import verify_pack
 391 |      pack = run.stage("verify", lambda: verify_pack.build(run.dir, vision=vision))
 392 | -    with open(os.path.join(run.dir, "GATE_REPORT.json")) as f:     # V1 (visual checklist) joins the rows
 393 | -        for fmt, frows in json.load(f).get("rows", {}).items():
 394 | -            if "V1_visual_checklist" in frows:
 395 | -                rows[fmt]["V1_visual_checklist"] = frows["V1_visual_checklist"]
 396 | +    # the verdict is computed from the report ON DISK (the file the attestation binds); the pack wrote the V1 rows
 397 | +    # into it, and a pack that wrote none (or no evidence) leaves V1 missing = a blocker (GPT-cut F02)
 398 | +    with open(os.path.join(run.dir, "GATE_REPORT.json")) as f:
 399 | +        rep = json.load(f)
 400 | +    rows, evidence = rep.get("rows") or {}, rep.get("evidence") or {}
 401 |      run.prov["visual_checklist"] = {fmt: {"ok": v.get("ok"), "error": v.get("error"),
 402 |                                            "answers": {m: d["rows"] for m, d in (v.get("per_model") or {}).items()}}
 403 |                                      for fmt, v in (pack.get("visual") or {}).items()}
 404 |      run.prov["contact_sheets"] = pack.get("contact_sheets")
 405 | -    v16, bad16 = verdict_for(rows["16x9"])
 406 | -    v9, bad9 = verdict_for(rows["9x16"])
 407 | +    v16, bad16 = verdict_for(rows.get("16x9"), "16x9", evidence)
 408 | +    v9, bad9 = verdict_for(rows.get("9x16"), "9x16", evidence)
 409 |      run.prov["verdicts"] = {"16x9": v16, "9x16": v9}
 410 |      run.prov["verdict_blockers"] = {"16x9": bad16, "9x16": bad9}
 411 |      run.status["verdict"] = VERDICT_CANDIDATE if v16 == v9 == VERDICT_CANDIDATE else VERDICT_HOLD
 412 | @@ -1255,6 +1338,11 @@ def main():
 413 |              run.status["holds"].append(f"provenance: {type(e).__name__}: {e}")
 414 |          run.status["ended"] = now_iso()
 415 |          run.status["elapsed_s"] = round(time.time() - t0, 1)
 416 | +        try:                                   # LAST: the terminal state, any hold included (release_auth)
 417 | +            attest_run(run)
 418 | +        except Exception as e:
 419 | +            run.status["verdict"] = VERDICT_HOLD
 420 | +            run.status["holds"].append(f"attestation: {type(e).__name__}: {e}")
 421 |          run.save()
 422 |          write_report(run)
 423 |          with open(os.path.join(run_dir, "VERDICT.txt"), "w") as f:
 424 | diff --git a/pipeline/story_ledger.py b/pipeline/story_ledger.py
 425 | index 0f888278..8f910a95 100644
 426 | --- a/pipeline/story_ledger.py
 427 | +++ b/pipeline/story_ledger.py
 428 | @@ -52,13 +52,14 @@ def record(run_dir, path=None):
 429 |  
 430 |  
 431 |  def record_if_approved(run_dir, delivery, mode, path=None):
 432 | -    """Called by scripts/pulse_check_run.sh after a delivery: an AUTO run whose BOTH finals went out as
 433 | -    "HOLD FOR APPROVAL - all gates passed, no waivers" is recorded; anything else (pinned, review-only, an
 434 | -    option) is not, so a story held for a defect is free to be produced again once the defect is fixed."""
 435 | +    """Called by scripts/pulse_check_run.sh after a delivery: an AUTO run whose drop was authorised
 436 | +    (release_auth) and completed, with BOTH finals captioned telegram.HOLD_OK, is recorded; anything else
 437 | +    (pinned, an option, a partial drop) is not, so a story held for a defect is free to be produced again once
 438 | +    the defect is fixed."""
 439 |      import telegram
 440 |      finals = [m for m in delivery["messages"] if "format" in m]
 441 | -    if mode != "auto" or delivery.get("option") or len(finals) != 2 or \
 442 | -            not all(m["caption"].startswith(telegram.HOLD_OK) for m in finals):
 443 | +    if mode != "auto" or delivery.get("option") or len(finals) != 2 or delivery.get("authorised") is not True or \
 444 | +            delivery.get("status") != "complete" or not all(m["caption"].startswith(telegram.HOLD_OK) for m in finals):
 445 |          return None
 446 |      return record(run_dir, path)
 447 |  
 448 | diff --git a/pipeline/test_story_ledger.py b/pipeline/test_story_ledger.py
 449 | index 228357e0..8b9ec579 100644
 450 | --- a/pipeline/test_story_ledger.py
 451 | +++ b/pipeline/test_story_ledger.py
 452 | @@ -69,13 +69,16 @@ class TestRecordIfApproved(unittest.TestCase):
 453 |          json.dump({"selected": {"headline": "H", "evidence": ev}}, open(os.path.join(run, "TOPIC_SELECTION.json"), "w"))
 454 |          path = os.path.join(tmp, "ledger.jsonl")
 455 |  
 456 | -        def dlv(c16, c9, option=None):
 457 | -            return {"option": option, "messages": [{"format": "16x9", "caption": c16}, {"format": "9x16", "caption": c9},
 458 | -                                                   {"sheet": "contact_sheet_16x9.jpg"}]}
 459 | +        def dlv(c16, c9, option=None, authorised=True, status="complete"):
 460 | +            return {"option": option, "authorised": authorised, "status": status,
 461 | +                    "messages": [{"format": "16x9", "caption": c16}, {"format": "9x16", "caption": c9},
 462 | +                                 {"sheet": "contact_sheet_16x9.jpg"}]}
 463 |          ok = telegram.HOLD_OK + " | details"
 464 |          self.assertIsNone(story_ledger.record_if_approved(run, dlv(ok, ok), "pinned", path))
 465 | -        self.assertIsNone(story_ledger.record_if_approved(run, dlv(ok, telegram.REVIEW + " - 1 failing"), "auto", path))
 466 | +        self.assertIsNone(story_ledger.record_if_approved(run, dlv(ok, "REVIEW ONLY - 1 failing"), "auto", path))
 467 |          self.assertIsNone(story_ledger.record_if_approved(run, dlv(ok, ok, option="A"), "auto", path))
 468 | +        self.assertIsNone(story_ledger.record_if_approved(run, dlv(ok, ok, authorised=False), "auto", path))
 469 | +        self.assertIsNone(story_ledger.record_if_approved(run, dlv(ok, ok, status="in_progress"), "auto", path))
 470 |          self.assertEqual(story_ledger.entries(path), [])
 471 |          self.assertEqual(story_ledger.record_if_approved(run, dlv(ok, ok), "auto", path)["run"], "fresh_20261111_130000")
 472 |  
 473 | diff --git a/pipeline/transition_options.py b/pipeline/transition_options.py
 474 | index 20d0ee5c..550c2e1f 100644
 475 | --- a/pipeline/transition_options.py
 476 | +++ b/pipeline/transition_options.py
 477 | @@ -28,7 +28,7 @@ def render_option(run_dir, style):
 478 |      dst = f"{run_dir.rstrip('/')}_option{style}"
 479 |      if os.path.exists(dst):
 480 |          raise SystemExit(f"STOP: {dst} exists")
 481 | -    shutil.copytree(run_dir, dst, ignore=shutil.ignore_patterns("TELEGRAM_DELIVERY*.json", "VERIFY"))
 482 | +    shutil.copytree(run_dir, dst, ignore=shutil.ignore_patterns("TELEGRAM_DELIVERY*.json", "VERIFY", "ATTESTATION.json"))
 483 |      for p in ("out/segment.mp4", "out/segment_vertical.mp4", "GATE_REPORT.json"):
 484 |          if os.path.exists(os.path.join(dst, p)):
 485 |              os.remove(os.path.join(dst, p))
 486 | @@ -43,9 +43,18 @@ def render_option(run_dir, style):
 487 |          cuts = json.load(f)
 488 |      rf.TRANSITION_STYLE = style                     # the option, on the same cut
 489 |      try:
 490 | +        rf.stage_env(run)                           # clean tree, launch revision recorded (an option is deliverable)
 491 |          final16, man16, final9, man9 = rf.stage_render(run)
 492 | -        rows, flags, limits = rf.stage_gates(run, final16, man16, final9, man9)
 493 | +        rf.stage_gates(run, final16, man16, final9, man9)
 494 |          verify_pack.build(dst)
 495 | +        with open(os.path.join(dst, "GATE_REPORT.json")) as f:      # the verdict from the report on disk
 496 | +            rep = json.load(f)
 497 | +        verdicts = {fmt: rf.verdict_for((rep.get("rows") or {}).get(fmt), fmt, rep.get("evidence"))
 498 | +                    for fmt in ("16x9", "9x16")}
 499 | +        run.status["verdict"] = rf.VERDICT_CANDIDATE if all(v == rf.VERDICT_CANDIDATE for v, _ in verdicts.values()) \
 500 | +            else rf.VERDICT_HOLD
 501 | +        rf.record_assets(run)                       # executed code at the launch revision (release_auth)
 502 | +        rf.attest_run(run)
 503 |      except Exception:
 504 |          try:
 505 |              os.rename(dst, f"{dst}_failed_{time.strftime('%H%M%S')}")    # kept for diagnosis; a retry can run
 506 | @@ -53,7 +62,7 @@ def render_option(run_dir, style):
 507 |              print(f"  could not set {dst} aside: {e}")                   # never masks the real failure
 508 |          raise
 509 |      run.save()
 510 | -    print(f"option {style}: {dst} | " + ", ".join(f"{fmt}: {rf.verdict_for(rows[fmt])[0]}" for fmt in rows))
 511 | +    print(f"option {style}: {dst} | " + ", ".join(f"{fmt}: {v}" for fmt, (v, _) in verdicts.items()))
 512 |      return dst, cuts
 513 |  
 514 |  
 515 | diff --git a/pipeline/release_auth.py b/pipeline/release_auth.py
 516 | new file mode 100644
 517 | index 00000000..012af843
 518 | --- /dev/null
 519 | +++ b/pipeline/release_auth.py
 520 | @@ -0,0 +1,213 @@
 521 | +#!/usr/bin/env python3
 522 | +"""pipeline/release_auth.py — the ONE answer to "may this exact file be sent as passing" (red-team 2026-11-11, A).
 523 | +
 524 | +FAIL CLOSED: absent, empty, malformed, mistyped or unexpected evidence is never a pass.
 525 | +  inventory   a versioned, exact set of gate rows per format: REQUIRED rows (INVENTORY) decide release and pass only
 526 | +              when their verdict is exactly "PASS" (no prefixes, no waiver strings); MONITORING rows (gates without
 527 | +              a passing fixture, a failing fixture and a missing-evidence answer: addendum '22:15' item 4) must be
 528 | +              present with an exact verdict and are reported, not deciding; the few known non-blocking rows are
 529 | +              enumerated with their allowed verdicts (NONBLOCKING); any other row, a missing row, or a verdict
 530 | +              outside VERDICTS is a failure
 531 | +  evidence    every row records that it executed and on how many samples (>= 1)
 532 | +  attestation run_fresh writes ATTESTATION.json LAST (after the verification pack and provenance) from what is on
 533 | +              disk: the rows, the evidence, the pack's strict result, the run's terminal state (any hold, code
 534 | +              not at the launch revision = not ok), and the sha256 of both finals, the EDL, both manifests,
 535 | +              GATE_REPORT.json, VERIFICATION.json and both contact sheets; the finals and manifests must be the
 536 | +              bytes the gates measured (GATE_REPORT measured_files). A replay is attested but never deliverable.
 537 | +  authorise   re-derives the verdict from the attested rows, re-reads GATE_REPORT.json and VERIFICATION.json, and
 538 | +              recomputes every digest NOW; delivery calls it before the first send and checks each file's digest
 539 | +              again immediately before sending it (telegram.deliver_run). Every send path goes through here; a run
 540 | +              without an attestation (killed, crashed, older code) is never authorised.
 541 | +"""
 542 | +import hashlib
 543 | +import json
 544 | +import os
 545 | +from datetime import datetime, timezone
 546 | +
 547 | +SCHEMA = "pulse.attestation.v1"
 548 | +INVENTORY_VERSION = 1
 549 | +VERDICTS = ("PASS", "FAIL", "HOLD", "SKIPPED", "LIMITED")
 550 | +# Orchestrator addendum '22:15' item 4: a gate DECIDES release (REQUIRED) only with a real passing fixture, a
 551 | +# realistic failing fixture and a defined answer to missing evidence (here: no executed sample = blocker). Every
 552 | +# other gate is MONITORING: it must be present with an exact verdict (it is reported), but its verdict does not
 553 | +# decide release until it has all three. The per-gate fixture table is in docs/audits/DEFINITION_OF_DONE_PULSE_CHECK.md
 554 | +# ("REQUIRED / MONITORING"). No gate is deleted.
 555 | +_REQUIRED = ("G3b_cut_out_clean", "G3c_acoustic_tail", "G4s_layout_truth", "G5_tech", "G8_sharpness", "G9_tail",
 556 | +             "outro_locked", "G12_credits", "G15_credits", "G16_sentence_boundary", "G17_onset_tail",
 557 | +             "G18_word_for_word", "G19_edge_shots", "G20_signoff_names_all")
 558 | +_MONITORING = ("G1_voice", "G2_watermark", "G3_cuts", "G4_faces", "G4_faces_per_shot", "G6_preroll", "G10_chyron",
 559 | +               "G13_vo_audible", "V1_visual_checklist")
 560 | +INVENTORY = {"16x9": frozenset(_REQUIRED + ("G14_av_alignment",)),
 561 | +             "9x16": frozenset(_REQUIRED)}
 562 | +MONITORING = {"16x9": frozenset(_MONITORING),
 563 | +              "9x16": frozenset(_MONITORING + ("G11_parity", "G14_audio_offset", "G14c_duration_parity",
 564 | +                                               "vertical_silent_fallback"))}
 565 | +NONBLOCKING = {"16x9": {}, "9x16": {"G14_frame_similarity": frozenset({"LIMITED"})}}   # known limitation, not a pass
 566 | +FORMATS = ("16x9", "9x16")
 567 | +BOUND = ("out/segment.mp4", "out/segment_vertical.mp4", "edl.json", "qa/concat_manifest_16x9.json",
 568 | +         "qa/concat_manifest_9x16.json", "GATE_REPORT.json", "VERIFY/VERIFICATION.json",
 569 | +         "qa/contact_sheet_16x9.jpg", "qa/contact_sheet_9x16.jpg")
 570 | +
 571 | +
 572 | +def sha256(path):
 573 | +    h = hashlib.sha256()
 574 | +    with open(path, "rb") as f:
 575 | +        for b in iter(lambda: f.read(1 << 20), b""):
 576 | +            h.update(b)
 577 | +    return h.hexdigest()
 578 | +
 579 | +
 580 | +def blockers(fmt, rows, evidence=None):
 581 | +    """{row: why} for one format; empty only when the rows satisfy the inventory exactly: every REQUIRED row is
 582 | +    exactly "PASS" with execution evidence, every MONITORING row is present with an exact verdict (reported, not
 583 | +    deciding), the enumerated non-blocking rows carry their allowed verdict, and no other row exists."""
 584 | +    if fmt not in INVENTORY or not isinstance(rows, dict):
 585 | +        return {"format": f"unknown format {fmt!r} or rows not a mapping"}
 586 | +    bad = {}
 587 | +    allowed = INVENTORY[fmt] | MONITORING[fmt] | set(NONBLOCKING[fmt])
 588 | +    for k in sorted(set(rows) - allowed):
 589 | +        bad[k] = f"unexpected gate row (not in inventory v{INVENTORY_VERSION})"
 590 | +    for k in sorted(INVENTORY[fmt]):
 591 | +        v = rows.get(k)
 592 | +        if v is None:
 593 | +            bad[k] = "required gate row missing"
 594 | +        elif v not in VERDICTS:
 595 | +            bad[k] = f"verdict {v!r} is not one of {VERDICTS}"
 596 | +        elif v != "PASS":
 597 | +            bad[k] = v
 598 | +    for k in sorted(MONITORING[fmt]):
 599 | +        if rows.get(k) not in VERDICTS:
 600 | +            bad[k] = f"monitoring row must be reported with one of {VERDICTS}, got {rows.get(k)!r}"
 601 | +    for k, ok in NONBLOCKING[fmt].items():
 602 | +        if rows.get(k) not in ok:
 603 | +            bad[k] = f"non-blocking row must be one of {sorted(ok)}, got {rows.get(k)!r}"
 604 | +    if evidence is not None:
 605 | +        ev = evidence.get(fmt) if isinstance(evidence, dict) else None
 606 | +        for k in sorted(INVENTORY[fmt]):
 607 | +            e = (ev or {}).get(k)
 608 | +            if not (isinstance(e, dict) and e.get("executed") is True and type(e.get("samples")) is int
 609 | +                    and e["samples"] >= 1):
 610 | +                bad.setdefault(k, f"no execution evidence (executed True, samples >= 1): {e!r}")
 611 | +    return bad
 612 | +
 613 | +
 614 | +def monitoring_report(rows):
 615 | +    """{fmt: {row: verdict}} of the MONITORING rows that did not pass (shown with a delivery, never deciding)."""
 616 | +    return {fmt: {k: (rows.get(fmt) or {}).get(k) for k in sorted(MONITORING[fmt])
 617 | +                  if (rows.get(fmt) or {}).get(k) != "PASS"} for fmt in FORMATS}
 618 | +
 619 | +
 620 | +def verification_ok(pack):
 621 | +    """The verification pack is complete (every frame, sheet, credits row and both G18 tables) and was built WITH
 622 | +    the vision check (a pack without it is a waiver switch: GPT-gates F08, Claude-gates V9). The visual verdict
 623 | +    itself is the V1 row, which decides release only when V1 is in the REQUIRED inventory."""
 624 | +    if not isinstance(pack, dict):
 625 | +        return False, ["verification pack missing or not a mapping"]
 626 | +    why = []
 627 | +    if pack.get("vision") is not True:
 628 | +        why.append("pack built without the vision check")
 629 | +    if pack.get("complete") is not True:
 630 | +        why.append("pack incomplete")
 631 | +    return not why, why
 632 | +
 633 | +
 634 | +def _gate_report(run_dir):
 635 | +    return json.load(open(os.path.join(run_dir, "GATE_REPORT.json")))
 636 | +
 637 | +
 638 | +def attest(run_dir, run_state, deliverable=True, why_not=None):
 639 | +    """Write ATTESTATION.json (atomically) from what is ON DISK: GATE_REPORT.json (rows, evidence, the digests
 640 | +    the gates measured), VERIFY/VERIFICATION.json and the digests of every bound file now. verdict ALL_PASS
 641 | +    only when both formats satisfy the inventory, the pack passed, the files the gates measured are unchanged,
 642 | +    every bound file exists and the run itself ended clean (run_state["ok"] is True: no hold anywhere, code at
 643 | +    the launch revision). A run that is not deliverable (a replay is diagnostic) is recorded with why_not and is
 644 | +    never authorised, whatever its verdict."""
 645 | +    why = []
 646 | +    try:
 647 | +        rep = _gate_report(run_dir)
 648 | +    except (OSError, ValueError) as e:
 649 | +        rep = {}
 650 | +        why.append(f"GATE_REPORT.json unreadable: {type(e).__name__}")
 651 | +    rows, evidence = rep.get("rows") or {}, rep.get("evidence")
 652 | +    bad = {fmt: blockers(fmt, rows.get(fmt), evidence) for fmt in FORMATS}
 653 | +    try:
 654 | +        pack = json.load(open(os.path.join(run_dir, "VERIFY", "VERIFICATION.json")))
 655 | +    except (OSError, ValueError):
 656 | +        pack = None
 657 | +    v_ok, v_why = verification_ok(pack)
 658 | +    files = {rel: (sha256(os.path.join(run_dir, rel)) if os.path.isfile(os.path.join(run_dir, rel)) else None)
 659 | +             for rel in BOUND}
 660 | +    missing = [rel for rel, d in files.items() if d is None]
 661 | +    measured = rep.get("measured_files") or {}
 662 | +    for rel in ("out/segment.mp4", "out/segment_vertical.mp4", "qa/concat_manifest_16x9.json",
 663 | +                "qa/concat_manifest_9x16.json"):
 664 | +        if measured.get(rel) is None or measured.get(rel) != files.get(rel):
 665 | +            why.append(f"{rel}: not the bytes the gates measured")
 666 | +    if rep.get("inventory_version") != INVENTORY_VERSION:
 667 | +        why.append(f"gate report inventory version {rep.get('inventory_version')!r} != {INVENTORY_VERSION}")
 668 | +    if not (isinstance(run_state, dict) and run_state.get("ok") is True):
 669 | +        why.append("run did not end clean: " + "; ".join(map(str, (run_state or {}).get("why") or ["no state"])))
 670 | +    ok = not any(bad.values()) and v_ok and not missing and not why
 671 | +    att = {"schema": SCHEMA, "inventory_version": INVENTORY_VERSION, "verdict": "ALL_PASS" if ok else "HOLD",
 672 | +           "deliverable": bool(deliverable), "why_not_deliverable": why_not, "run_state": run_state,
 673 | +           "rows": rows, "evidence": evidence, "notes": rep.get("notes") or {}, "blockers": bad,
 674 | +           "verification": {"ok": v_ok, "why": v_why}, "other_blockers": why, "missing_files": missing,
 675 | +           "files": files, "created_at": datetime.now(timezone.utc).isoformat()}
 676 | +    tmp = os.path.join(run_dir, "ATTESTATION.json.tmp")
 677 | +    with open(tmp, "w") as f:
 678 | +        json.dump(att, f, indent=2, default=str)
 679 | +    os.replace(tmp, os.path.join(run_dir, "ATTESTATION.json"))
 680 | +    return att
 681 | +
 682 | +
 683 | +def authorise(run_dir):
 684 | +    """(ok, reasons, attestation). ok only when ATTESTATION.json is ALL_PASS and deliverable, its rows re-check
 685 | +    clean here, GATE_REPORT.json still carries exactly those rows and evidence, the verification pack still
 686 | +    passes, the run ended clean, and every bound file's sha256 equals the attested digest NOW."""
 687 | +    p = os.path.join(run_dir, "ATTESTATION.json")
 688 | +    try:
 689 | +        att = json.load(open(p))
 690 | +    except (OSError, ValueError) as e:
 691 | +        return False, [f"no readable attestation: {type(e).__name__}"], None
 692 | +    if not isinstance(att, dict) or att.get("schema") != SCHEMA or att.get("inventory_version") != INVENTORY_VERSION:
 693 | +        return False, ["attestation schema / inventory version mismatch"], att
 694 | +    why = []
 695 | +    if att.get("verdict") != "ALL_PASS":
 696 | +        why.append(f"attestation verdict {att.get('verdict')!r}")
 697 | +    if att.get("deliverable") is not True:
 698 | +        why.append(f"not deliverable: {att.get('why_not_deliverable')}")
 699 | +    if not (isinstance(att.get("run_state"), dict) and att["run_state"].get("ok") is True):
 700 | +        why.append("the run did not end clean")
 701 | +    rows, evidence = att.get("rows") or {}, att.get("evidence")
 702 | +    for fmt in FORMATS:
 703 | +        for k, v in blockers(fmt, rows.get(fmt), evidence).items():
 704 | +            why.append(f"{fmt} {k}: {v}")
 705 | +    try:
 706 | +        rep = _gate_report(run_dir)
 707 | +        if rep.get("rows") != rows or rep.get("evidence") != evidence:
 708 | +            why.append("GATE_REPORT.json rows / evidence differ from the attested ones")
 709 | +    except (OSError, ValueError):
 710 | +        why.append("GATE_REPORT.json unreadable")
 711 | +    try:
 712 | +        v_ok, v_why = verification_ok(json.load(open(os.path.join(run_dir, "VERIFY", "VERIFICATION.json"))))
 713 | +        why += [] if v_ok else v_why
 714 | +    except (OSError, ValueError):
 715 | +        why.append("VERIFICATION.json unreadable")
 716 | +    files = att.get("files") or {}
 717 | +    if set(files) != set(BOUND):
 718 | +        why.append("attested file set differs from the bound set")
 719 | +    for rel in BOUND:
 720 | +        path = os.path.join(run_dir, rel)
 721 | +        if not files.get(rel):
 722 | +            why.append(f"{rel}: no attested digest")
 723 | +        elif not os.path.isfile(path):
 724 | +            why.append(f"{rel}: missing")
 725 | +        elif sha256(path) != files[rel]:
 726 | +            why.append(f"{rel}: changed since it was attested")
 727 | +    return not why, why, att
 728 | +
 729 | +
 730 | +def check_file(run_dir, att, rel):
 731 | +    """True when `rel` still has its attested digest (delivery checks this immediately before each send)."""
 732 | +    path = os.path.join(run_dir, rel)
 733 | +    return bool(att and att.get("files", {}).get(rel)) and os.path.isfile(path) and sha256(path) == att["files"][rel]
 734 | diff --git a/pipeline/test_release_auth.py b/pipeline/test_release_auth.py
 735 | new file mode 100644
 736 | index 00000000..b0dcdb67
 737 | --- /dev/null
 738 | +++ b/pipeline/test_release_auth.py
 739 | @@ -0,0 +1,293 @@
 740 | +#!/usr/bin/env python3
 741 | +"""pipeline/release_auth.py: the fail-closed release contract (red-team 2026-11-11 A; GPT 'five cheapest tests' #2,
 742 | +Claude 'five cheapest tests' #3). One complete passing run directory is built; every mutation of it must HOLD:
 743 | +  inventory   a REQUIRED row deleted, any non-PASS verdict, a prefixed 'PASS (...)', an unknown row, a MONITORING
 744 | +              row missing (it must be reported) -- while a MONITORING row that FAILS does not decide (addendum
 745 | +              '22:15' item 4)
 746 | +  evidence    missing, executed False, zero samples, a sample count that is not an int
 747 | +  bytes       a final / manifest that is not what the gates measured; a bound file changed after the attestation;
 748 | +              GATE_REPORT rows edited after the attestation
 749 | +  pack        built without vision, incomplete, missing
 750 | +  run         holds present (the run did not end clean), not deliverable (a replay), no / corrupt attestation
 751 | +Run: cd ~/protocol_pulse && python3 -m pytest -q pipeline/test_release_auth.py"""
 752 | +import json
 753 | +import os
 754 | +import shutil
 755 | +import subprocess
 756 | +import sys
 757 | +import tempfile
 758 | +import unittest
 759 | +
 760 | +PIPELINE = os.path.dirname(os.path.abspath(__file__))
 761 | +sys.path.insert(0, PIPELINE)
 762 | +import release_auth as RA  # noqa: E402
 763 | +
 764 | +_MEDIA = {}
 765 | +
 766 | +
 767 | +def _media():
 768 | +    """Two one-second black finals at the release dimensions (made once per process)."""
 769 | +    if not _MEDIA:
 770 | +        d = tempfile.mkdtemp(prefix="ra_media_")
 771 | +        for name, (w, h) in (("segment.mp4", (1920, 1080)), ("segment_vertical.mp4", (1080, 1920))):
 772 | +            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=black:s={w}x{h}:r=24:d=1",
 773 | +                            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", os.path.join(d, name)],
 774 | +                           check=True)
 775 | +        _MEDIA["dir"] = d
 776 | +    return _MEDIA["dir"]
 777 | +
 778 | +
 779 | +def passing_rows():
 780 | +    rows = {fmt: {k: "PASS" for k in RA.INVENTORY[fmt] | RA.MONITORING[fmt]} for fmt in RA.FORMATS}
 781 | +    rows["9x16"]["G14_frame_similarity"] = "LIMITED"
 782 | +    return rows
 783 | +
 784 | +
 785 | +def make_run(parent, rows=None, attest=True, run_state=None, edl=None):
 786 | +    """A complete run directory that release_auth authorises (unless the caller mutates it)."""
 787 | +    from PIL import Image
 788 | +    rd = tempfile.mkdtemp(prefix="fresh_", dir=parent)
 789 | +    for sub in ("out", "qa", "VERIFY"):
 790 | +        os.makedirs(os.path.join(rd, sub))
 791 | +    for name in ("segment.mp4", "segment_vertical.mp4"):
 792 | +        shutil.copy(os.path.join(_media(), name), os.path.join(rd, "out", name))
 793 | +    shot = {"start": 0.0, "end": 9.4, "class": "single", "flagged": False}
 794 | +    json.dump(edl or {"topic": "Bitcoin price dip", "headline": "Bitcoin price dip",
 795 | +                      "hook": {"channel": "Yahoo Finance", "video_id": "YAH0000000a",
 796 | +                               "selection_lock": {"text": "Bitcoin fell to 74,000 dollars today."},
 797 | +                               "vertical_layout": {"shots": [shot], "flagged": False}},
 798 | +                      "clips": [{"index": 1, "channel": "Natalie Brunell", "video_id": "NAT0000000b",
 799 | +                                 "selection_lock": {"text": "It is a bear market rally."},
 800 | +                                 "vertical_layout": {"shots": [shot], "flagged": False}}]},
 801 | +              open(os.path.join(rd, "edl.json"), "w"))
 802 | +    for fmt in RA.FORMATS:
 803 | +        json.dump({"format": fmt, "segments": [{"label": "hook", "type": "talking_head", "start": 0.0, "end": 0.5},
 804 | +                                               {"label": "outro", "type": "outro", "start": 0.5, "end": 1.0}]},
 805 | +                  open(os.path.join(rd, "qa", f"concat_manifest_{fmt}.json"), "w"))
 806 | +        Image.new("RGB", (120, 80)).save(os.path.join(rd, "qa", f"contact_sheet_{fmt}.jpg"))
 807 | +    rows = rows or passing_rows()
 808 | +    measured = {rel: RA.sha256(os.path.join(rd, rel)) for rel in
 809 | +                ("out/segment.mp4", "out/segment_vertical.mp4", "qa/concat_manifest_16x9.json",
 810 | +                 "qa/concat_manifest_9x16.json")}
 811 | +    json.dump({"inventory_version": RA.INVENTORY_VERSION, "rows": rows,
 812 | +               "evidence": {fmt: {k: {"executed": True, "samples": 3} for k in r} for fmt, r in rows.items()},
 813 | +               "notes": {}, "measured_files": measured}, open(os.path.join(rd, "GATE_REPORT.json"), "w"))
 814 | +    json.dump({"complete": True, "vision": True, "passed": True,
 815 | +               "visual": {f: {"ok": True} for f in RA.FORMATS}}, open(os.path.join(rd, "VERIFY", "VERIFICATION.json"), "w"))
 816 | +    if attest:
 817 | +        RA.attest(rd, run_state or {"ok": True, "why": []})
 818 | +    return rd
 819 | +
 820 | +
 821 | +def edit_json(path, fn):
 822 | +    d = json.load(open(path))
 823 | +    fn(d)
 824 | +    json.dump(d, open(path, "w"))
 825 | +
 826 | +
 827 | +class Base(unittest.TestCase):
 828 | +    def setUp(self):
 829 | +        self.tmp = tempfile.mkdtemp(prefix="ra_")
 830 | +        self.addCleanup(shutil.rmtree, self.tmp, True)
 831 | +
 832 | +    def holds(self, rd, label):
 833 | +        """attest from the (mutated) disk state, then authorise: both must refuse."""
 834 | +        att = RA.attest(rd, {"ok": True, "why": []})
 835 | +        ok, why, _ = RA.authorise(rd)
 836 | +        self.assertEqual(att["verdict"], "HOLD", label)
 837 | +        self.assertFalse(ok, label)
 838 | +        return att
 839 | +
 840 | +
 841 | +class TestPassingRun(Base):
 842 | +    def test_the_complete_run_is_authorised(self):
 843 | +        rd = make_run(self.tmp)
 844 | +        ok, why, att = RA.authorise(rd)
 845 | +        self.assertTrue(ok, why)
 846 | +        self.assertEqual(att["verdict"], "ALL_PASS")
 847 | +        self.assertEqual(set(att["files"]), set(RA.BOUND))
 848 | +
 849 | +
 850 | +class TestInventory(Base):
 851 | +    def mutate_rows(self, fn, label):
 852 | +        rd = make_run(self.tmp, attest=False)
 853 | +        edit_json(os.path.join(rd, "GATE_REPORT.json"), lambda d: fn(d["rows"]))
 854 | +        return self.holds(rd, label)
 855 | +
 856 | +    def test_every_required_row_deleted_holds(self):
 857 | +        for fmt in RA.FORMATS:
 858 | +            for k in sorted(RA.INVENTORY[fmt]):
 859 | +                self.mutate_rows(lambda r, f=fmt, k=k: r[f].pop(k), f"{fmt} {k} deleted")
 860 | +
 861 | +    def test_every_non_pass_verdict_and_a_prefixed_pass_hold(self):
 862 | +        for v in ("FAIL", "HOLD", "SKIPPED", "LIMITED", "PASS (no fallback)", "PASS(L-c: x)", "pass", True, None, ""):
 863 | +            self.mutate_rows(lambda r, v=v: r["16x9"].__setitem__("G18_word_for_word", v), f"G18 = {v!r}")
 864 | +
 865 | +    def test_an_unknown_row_holds(self):
 866 | +        self.mutate_rows(lambda r: r["9x16"].__setitem__("G11_parity(run_gates)", "NOT RUN BY run_gates"),
 867 | +                         "legacy placeholder row")
 868 | +        self.mutate_rows(lambda r: r["16x9"].__setitem__("G99_new", "PASS"), "unlisted row")
 869 | +
 870 | +    def test_a_monitoring_row_must_be_reported_but_does_not_decide(self):
 871 | +        for fmt in RA.FORMATS:
 872 | +            for k in sorted(RA.MONITORING[fmt]):
 873 | +                self.mutate_rows(lambda r, f=fmt, k=k: r[f].pop(k), f"{fmt} monitoring {k} missing")
 874 | +        rows = passing_rows()
 875 | +        rows["16x9"]["G1_voice"] = "FAIL"
 876 | +        rows["9x16"]["G13_vo_audible"] = "SKIPPED"
 877 | +        rd = make_run(self.tmp, rows=rows)
 878 | +        ok, why, _ = RA.authorise(rd)
 879 | +        self.assertTrue(ok, why)
 880 | +        self.assertEqual(RA.monitoring_report(rows), {"16x9": {"G1_voice": "FAIL"}, "9x16": {"G13_vo_audible": "SKIPPED"}})
 881 | +
 882 | +    def test_the_known_limitation_row_carries_only_its_verdict(self):
 883 | +        self.mutate_rows(lambda r: r["9x16"].__setitem__("G14_frame_similarity", "PASS"), "LIMITED row reads PASS")
 884 | +        self.mutate_rows(lambda r: r["9x16"].pop("G14_frame_similarity"), "LIMITED row missing")
 885 | +
 886 | +    def test_a_format_missing_holds(self):
 887 | +        self.mutate_rows(lambda r: r.pop("9x16"), "9x16 rows missing")
 888 | +
 889 | +
 890 | +class TestEvidence(Base):
 891 | +    def test_a_required_row_without_execution_evidence_holds(self):
 892 | +        for bad in (None, {}, {"executed": False, "samples": 3}, {"executed": True, "samples": 0},
 893 | +                    {"executed": True, "samples": "3"}, {"executed": True, "samples": True},
 894 | +                    {"executed": "true", "samples": 3}):
 895 | +            rd = make_run(self.tmp, attest=False)
 896 | +
 897 | +            def fn(d, bad=bad):
 898 | +                if bad is None:
 899 | +                    d["evidence"]["16x9"].pop("G16_sentence_boundary")
 900 | +                else:
 901 | +                    d["evidence"]["16x9"]["G16_sentence_boundary"] = bad
 902 | +            edit_json(os.path.join(rd, "GATE_REPORT.json"), fn)
 903 | +            self.holds(rd, f"evidence {bad!r}")
 904 | +
 905 | +    def test_a_report_of_another_inventory_version_holds(self):
 906 | +        rd = make_run(self.tmp, attest=False)
 907 | +        edit_json(os.path.join(rd, "GATE_REPORT.json"), lambda d: d.__setitem__("inventory_version", 0))
 908 | +        self.holds(rd, "old report")
 909 | +
 910 | +
 911 | +class TestBytes(Base):
 912 | +    def test_a_final_that_is_not_what_the_gates_measured_holds(self):
 913 | +        rd = make_run(self.tmp, attest=False)
 914 | +        with open(os.path.join(rd, "out", "segment.mp4"), "ab") as f:
 915 | +            f.write(b"\0")                                # re-rendered after the gates ran
 916 | +        att = self.holds(rd, "final changed between gates and attestation")
 917 | +        self.assertIn("out/segment.mp4: not the bytes the gates measured", att["other_blockers"])
 918 | +
 919 | +    def test_a_bound_file_changed_after_the_attestation_is_refused(self):
 920 | +        for rel in RA.BOUND:
 921 | +            rd = make_run(self.tmp)
 922 | +            with open(os.path.join(rd, rel), "ab") as f:
 923 | +                f.write(b" ")
 924 | +            ok, why, _ = RA.authorise(rd)
 925 | +            self.assertFalse(ok, rel)
 926 | +            self.assertTrue(any(rel in w for w in why), (rel, why))
 927 | +
 928 | +    def test_a_bound_file_deleted_after_the_attestation_is_refused(self):
 929 | +        rd = make_run(self.tmp)
 930 | +        os.remove(os.path.join(rd, "out", "segment_vertical.mp4"))
 931 | +        self.assertFalse(RA.authorise(rd)[0])
 932 | +
 933 | +    def test_check_file_before_each_send(self):
 934 | +        rd = make_run(self.tmp)
 935 | +        ok, _, att = RA.authorise(rd)
 936 | +        self.assertTrue(ok)
 937 | +        self.assertTrue(RA.check_file(rd, att, "out/segment.mp4"))
 938 | +        with open(os.path.join(rd, "out", "segment.mp4"), "ab") as f:
 939 | +            f.write(b"\0")
 940 | +        self.assertFalse(RA.check_file(rd, att, "out/segment.mp4"))
 941 | +        self.assertFalse(RA.check_file(rd, att, "out/not_bound.mp4"))
 942 | +
 943 | +
 944 | +class TestPackAndRun(Base):
 945 | +    def test_a_pack_without_vision_or_incomplete_or_missing_holds(self):
 946 | +        for fn, label in ((lambda d: d.__setitem__("vision", False), "vision off"),
 947 | +                          (lambda d: d.__setitem__("complete", "true"), "complete is a string"),
 948 | +                          (lambda d: d.pop("complete"), "complete missing")):
 949 | +            rd = make_run(self.tmp, attest=False)
 950 | +            edit_json(os.path.join(rd, "VERIFY", "VERIFICATION.json"), fn)
 951 | +            self.holds(rd, label)
 952 | +        rd = make_run(self.tmp, attest=False)
 953 | +        os.remove(os.path.join(rd, "VERIFY", "VERIFICATION.json"))
 954 | +        self.holds(rd, "pack missing")
 955 | +
 956 | +    def test_a_run_that_did_not_end_clean_is_never_authorised(self):
 957 | +        rd = make_run(self.tmp, run_state={"ok": False, "why": ["provenance: FileNotFoundError"]})
 958 | +        ok, why, att = RA.authorise(rd)
 959 | +        self.assertEqual(att["verdict"], "HOLD")
 960 | +        self.assertFalse(ok)
 961 | +        rd = make_run(self.tmp, attest=False)
 962 | +        RA.attest(rd, {"ok": "yes"})                     # a truthy non-bool is not ok
 963 | +        self.assertFalse(RA.authorise(rd)[0])
 964 | +
 965 | +    def test_a_replay_is_attested_but_never_deliverable(self):
 966 | +        rd = make_run(self.tmp, attest=False)
 967 | +        att = RA.attest(rd, {"ok": True, "why": []}, deliverable=False, why_not="replay")
 968 | +        self.assertEqual(att["verdict"], "ALL_PASS")
 969 | +        ok, why, _ = RA.authorise(rd)
 970 | +        self.assertFalse(ok)
 971 | +        self.assertTrue(any("not deliverable" in w for w in why), why)
 972 | +
 973 | +    def test_no_or_corrupt_attestation_is_refused(self):
 974 | +        rd = make_run(self.tmp, attest=False)
 975 | +        self.assertFalse(RA.authorise(rd)[0])
 976 | +        open(os.path.join(rd, "ATTESTATION.json"), "w").write("{not json")
 977 | +        self.assertFalse(RA.authorise(rd)[0])
 978 | +        rd = make_run(self.tmp)
 979 | +        edit_json(os.path.join(rd, "ATTESTATION.json"), lambda d: d.__setitem__("schema", "pulse.attestation.v0"))
 980 | +        self.assertFalse(RA.authorise(rd)[0])
 981 | +
 982 | +    def test_an_attestation_edited_to_all_pass_is_refused(self):
 983 | +        rows = passing_rows()
 984 | +        rows["16x9"]["G3c_acoustic_tail"] = "FAIL"
 985 | +        rd = make_run(self.tmp, rows=rows)
 986 | +        edit_json(os.path.join(rd, "ATTESTATION.json"), lambda d: d.__setitem__("verdict", "ALL_PASS"))
 987 | +        ok, why, _ = RA.authorise(rd)                   # the rows are re-checked, not the verdict trusted
 988 | +        self.assertFalse(ok)
 989 | +        self.assertTrue(any("G3c_acoustic_tail" in w for w in why), why)
 990 | +
 991 | +
 992 | +class TestRunFreshWiring(Base):
 993 | +    """run_fresh writes the attestation LAST and never gives two answers: holds anywhere => HOLD (GPT-cut F10)."""
 994 | +
 995 | +    def run_obj(self, rd, holds=(), verdict=None, not_at_rev=()):
 996 | +        import run_fresh as rf
 997 | +        run = rf.Run(rd)
 998 | +        run.status["verdict"] = verdict or rf.VERDICT_CANDIDATE
 999 | +        run.status["holds"] = list(holds)
1000 | +        run.prov["code"] = {"git_head": "abc", "pipeline_tree_clean_at_launch": True}
1001 | +        run.prov["executed_code_not_at_revision"] = list(not_at_rev)
1002 | +        return run
1003 | +
1004 | +    def test_a_clean_candidate_is_attested_all_pass(self):
1005 | +        import run_fresh as rf
1006 | +        rd = make_run(self.tmp, attest=False)
1007 | +        att = rf.attest_run(self.run_obj(rd))
1008 | +        self.assertEqual(att["verdict"], "ALL_PASS", att["other_blockers"])
1009 | +        self.assertTrue(RA.authorise(rd)[0])
1010 | +
1011 | +    def test_a_hold_reason_makes_the_run_hold(self):
1012 | +        import run_fresh as rf
1013 | +        for kw in ({"holds": ["provenance: OSError: disk full"]}, {"not_at_rev": ["pipeline/gates.py (modified)"]}):
1014 | +            rd = make_run(self.tmp, attest=False)
1015 | +            run = self.run_obj(rd, **kw)
1016 | +            att = rf.attest_run(run)
1017 | +            self.assertEqual(att["verdict"], "HOLD", kw)
1018 | +            self.assertEqual(run.status["verdict"], rf.VERDICT_HOLD, kw)
1019 | +            self.assertFalse(RA.authorise(rd)[0], kw)
1020 | +
1021 | +    def test_the_verdict_follows_the_inventory_not_prefixes(self):
1022 | +        import run_fresh as rf
1023 | +        rows = passing_rows()
1024 | +        self.assertEqual(rf.verdict_for(rows["16x9"], "16x9")[0], rf.VERDICT_CANDIDATE)
1025 | +        rows["16x9"]["G17_onset_tail"] = "PASS (looks fine)"
1026 | +        v, bad = rf.verdict_for(rows["16x9"], "16x9")
1027 | +        self.assertEqual(v, rf.VERDICT_HOLD)
1028 | +        self.assertIn("G17_onset_tail", bad)
1029 | +
1030 | +
1031 | +if __name__ == "__main__":
1032 | +    unittest.main()
1033 | 
```

---



---

## CYCLE 2 INSTRUCTIONS

You've now seen what the other models said. This is your final review.

1. WHAT DID THEY CATCH THAT YOU MISSED?
   Review their findings. Be honest about what you overlooked.

2. WHERE DO YOU AGREE OR DISAGREE?
   For each of their key findings: agree / disagree / partially agree + why.

3. NEW FINDINGS FROM THIS REVIEW
   Anything the combined analysis revealed that nobody caught in Cycle 1?

4. REVISED SCORES
   Update your scores from Cycle 1. Did anything change your assessment?
   | Subsystem | Cycle 1 | Cycle 2 | Why changed |

5. FINAL PRIORITY LIST
   Your definitive list of what must change before this ships.
   P0 CRITICAL | P1 HIGH | P2 MEDIUM — cite file and line numbers.

6. THE SINGLE HIGHEST-LEVERAGE CHANGE
   After seeing everything — one sentence. What matters most?

7. PRODUCTION READY?
   Yes / No / Yes with conditions. State your conditions precisely.
