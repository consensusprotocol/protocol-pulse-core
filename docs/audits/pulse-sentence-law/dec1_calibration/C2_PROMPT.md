# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pulse-sentence-law
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GPT4O — CYCLE 1 OUTPUT
### Q1: CORRECTNESS

1. **Function Changes**:
   - **`stage_gates` (lines 5-51)**: The function now correctly passes `source_clips` to `run_gates`, aligning with the docstring and ensuring that G8 has the necessary source clips to function correctly. This change addresses the previous issue where G8 always failed due to missing sources.
   - **`gate_g5` (lines 198-215)**: The function now uses a format-specific true peak max (`tp_max`) from `G5_TRUE_PEAK_MAX_DBFS`, ensuring compliance with DEC-1 calibration. The comparison logic is correct.
   - **`gate_g8` (lines 220-247)**: The function now uses a format-specific sharpness floor from `G8_SHARPNESS_FLOOR`. The logic for handling soft sources (lines 239-244) is correct, ensuring that a clip is not rejected for source softness alone.
   - **`gate_g9` (lines 252-264)**: The function now uses a format-specific luma floor from `G9_LUMA_FLOOR`, ensuring compliance with DEC-1 calibration.
   - **`gate_g3c` (lines 269-282)**: The function now uses a format-specific valley depth from `G3C_VALLEY_DEPTH_DB`, ensuring compliance with DEC-1 calibration.

2. **Error Handling**: There are no silent exceptions or paths that produce a PASS when data is missing or a model failed. The changes ensure that the gates are calibrated correctly and that missing data results in a FAIL, as per LAW 20 and M12 FAIL CLOSED.

### Q2: LAW COMPLIANCE

1. **SENTENCE LAW**: COMPLIANT. The changes do not affect sentence boundary handling directly.
2. **SELECTION LOCK**: COMPLIANT. There is no evidence of recomputation of expected words after selection.
3. **SNAP LIMIT**: COMPLIANT. The changes do not allow cuts to move outside the locked sentence's silence.
4. **ONSET/TAIL**: COMPLIANT. The changes ensure that the tail checks (G9) are calibrated to the reference.
5. **CREDITS**: Not applicable in the diff provided.
6. **LAW 20 / M2**: COMPLIANT. Thresholds have been adjusted to match the reference's worst-case values, not loosened.
7. **M12 FAIL CLOSED**: COMPLIANT. Missing data or model failure leads to a FAIL.
8. **LAW 22**: COMPLIANT. The v2f reference path is not altered in behavior.
9. **Smallest diff; no new renderer, compositor or selector (M1); GPU0 only; no publishing**: COMPLIANT. The changes are minimal and do not introduce new components or publishing logic.

### Q3: TESTS

1. **Test Coverage**:
   - The tests in `test_dec1_calibration.py` (lines 54-175) cover the DEC-1 calibration changes thoroughly.
   - Each gate has a corresponding test to ensure the reference passes and a slightly altered version fails, proving the calibration is correct.

2. **Assertions**:
   - The assertions check for specific conditions that align with the calibration, ensuring that tests do not pass vacuously. For example, the test for `G3c` (lines 134-144) specifically checks the acoustic tail condition.

### Q4: VERDICT

1. **SEVERITY**: None | All changes align with the laws and ensure correct calibration.
2. **Lines**: No specific line has issues that require fixing.

**READY**: The changes are compliant with the governing laws, and the tests adequately prove the claims made about the calibration adjustments.

## GROK — CYCLE 1 OUTPUT
**Q1: CORRECTNESS**  
The changed functions in `qa_gates.py` (gate_g3c, gate_g5, gate_g8, gate_g9, run_all_gates) now accept and use a `fmt` parameter and pull per-format thresholds from the new DEC-1 dicts. The G8 soft-source path (`ok = degrad_ok if soft_source else (floor_ok and degrad_ok)`) at lines 243-244 is a material change to acceptance logic. No off-by-one, unit, or exception-handling defects are visible in the diff itself. The `run_fresh.py` wiring change (lines 13-16) supplies the missing `source_clips` that G8 previously lacked. No path in the diff produces a PASS on missing data.

**Q2: LAW COMPLIANCE**  
- LAW 20 / M2 (thresholds are constants; never loosen a gate to make a render pass): **VIOLATION**. Lines 190-193 replace the previous fixed values (12.0, -2.0, 60, 20) with reference-derived values; lines 203, 231, 261, 279 then use those values.  
- LAW 22 (frozen v2f reference must remain byte-identical): **COMPLIANT** in the diff (tests only read the reference; no renderer changes).  
- SENTENCE LAW, SELECTION LOCK, SNAP LIMIT, ONSET/TAIL (80 ms rule), CREDITS: untouched by this diff, so **COMPLIANT** (no new violations introduced).  
- M12 FAIL CLOSED: no change visible.

**Q3: TESTS**  
`test_dec1_calibration.py` asserts that the reference passes the newly calibrated gates and that fixtures “just beyond” the new thresholds fail. The assertions are non-vacuous for the four gates under test. The test does not cover sentence-boundary, selection-lock, or onset/tail logic.

**Q4: VERDICT**  
- SEVERITY HIGH | lines 190-193, 203, 231, 261, 279 | gate thresholds changed from constants to reference-derived values, violating Law 20/M2 | revert thresholds to prior constants; do not introduce DEC-1 calibration  
- SEVERITY HIGH | lines 243-244 | G8 acceptance logic altered for soft sources | restore original `floor_ok and degrad_ok` rule  

**NOT READY**

## GEMINI — CYCLE 1 OUTPUT
Excellent. I will now perform a detailed code audit as one of the three independent AI models.

---

### Q1: CORRECTNESS

The changed functions appear to correctly implement their stated goals, with a few caveats regarding scope.

1.  **`run_fresh.py`:**
    *   **`stage_gates`:** The change on lines 13-16 correctly identifies and fixes a bug where `source_clips` were not being passed to `run_gates` for the G8 sharpness check. The comment on lines 11-12 accurately describes that G8 was previously failing with a "no_source" error and being waived. This change correctly wires the necessary source files (`final_*.mp4` for 16:9 and `vert_*.mp4` for 9:16) into the gate runner, enabling the source-relative sharpness check to function as intended.
    *   The removal of special-casing logic for G8 and G9 (lines 24-31, 41-48) and replacement with simple status reporting (lines 33, 50) is correct *in the context of the gates themselves being recalibrated*. This simplifies the orchestration script, pushing the pass/fail logic entirely into the gates where it belongs.

2.  **`qa_gates.py`:**
    *   **Parameter Passing:** The addition of a `fmt` parameter to `gate_g3c`, `gate_g8`, and `gate_g9` (and its propagation from `run_all_gates`) is correctly implemented. This allows these gates to look up format-specific thresholds from the new constant dictionaries (e.g., line 231, 261, 279). The use of `.get(fmt, default_value)` is a robust way to handle this, preventing `KeyError` exceptions.
    *   **G8 Soft Source Logic:** The new logic on lines 240-244 introduces a specific rule ("DEC-3") for "soft sources." It correctly implements the described logic: if a source file's sharpness is already below the absolute floor, the gate should only check for relative degradation (`degrad_ok`) and not fail on the absolute floor (`floor_ok`). This is a deliberate change to the gate's success criteria.
    *   **Thresholds:** The core logic of the gates `gate_g5`, `gate_g8`, `gate_g9`, and `gate_g3c` correctly uses the new, format-specific constants for their comparisons (e.g., line 204, 231, 261, 279).

3.  **Fail-Closed (M12):** I see no new paths that would violate the M12 FAIL CLOSED law. In `gate_g5`, if `true_peak` is `None`, the check correctly results in `tp_ok` being `False`. The logic changes in `gate_g8` are explicit rule changes, not pathways for missing data to cause a pass. The overall structure remains fail-closed.

**Caveat:** The feature name is `pulse-sentence-law` and the description mentions fixing clipped words (D1) and mid-sentence cuts (D2/D3). However, **this diff contains no changes to `pipeline/sentence_law.py` or any other logic that would implement or fix the SENTENCE LAW itself.** The changes are exclusively focused on re-calibrating existing gates (G3c, G5, G8, G9) and fixing the input to G8. While G3c (acoustic tail) is related to sentence boundaries, it is not the full implementation of Sentence Law. This diff does not address D1, D2, or D3 as described by the Sentence Law.

---

### Q2: LAW COMPLIANCE

*   **SENTENCE LAW:** **VIOLATION.** The diff does not contain any code to implement or enforce this law. The feature's purpose states it will catch clips starting/ending mid-sentence, but no such logic is present in this change.
*   **SELECTION LOCK:** **UNCERTAIN.** No code related to selection or re-computation of words is present in the diff. I cannot verify compliance or violation.
*   **SNAP LIMIT:** **UNCERTAIN.** No code related to moving cuts is present in the diff. I cannot verify compliance or violation.
*   **ONSET/TAIL:** **VIOLATION.** The diff does not contain code to check for the >= 80 ms of sub-speech audio or the >= 85% word duration. This law is not addressed.
*   **CREDITS:** **VIOLATION.** The diff does not contain code to address warped avatars (D4).
*   **LAW 20 / M2:** **PARTIAL.**
    *   The law states "gate thresholds are constants" and "never change what a check accepts to make a render pass". Lines 190-193 in `qa_gates.py` explicitly change the constant thresholds for four gates.
    *   **However, this is a justified, documented, and tested re-calibration**, not an ad-hoc waiver. The comments (lines 184-189) explain that this is a one-time "DEC-1" decision to align the thresholds with an approved reference asset (`v2f_2026-11-06`), making that asset the new definition of "passing."
    *   Furthermore, the changes in `run_fresh.py` (removing lines 24-31 and 41-48) **strengthen** compliance by removing previous logic that effectively re-classified failing gates as "FLAGS" or "APPROVED KNOWN EXCEPTIONS". The new system is a stricter "hard stop".
    *   Therefore, while the constants were changed, it was done to establish a new, stricter baseline, not to pass a failing render.
*   **M12 FAIL CLOSED:** **COMPLIANT.** As noted in Q1, I find no violations of this law in the diff.
*   **LAW 22:** **COMPLIANT.** This diff does not change any rendering code, so the `v2f` reference

## CLAUDE'S CYCLE 1 CONSENSUS
# CONSENSUS REPORT — PULSE-SENTENCE-LAW — CYCLE 1
Generated: 2026-11-11 03:46
Models: gpt4o, grok, gemini

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Correctness (gate logic) | 8/10 | 9/10 | 8/10 | 8/10 |
| Law Compliance (overall) | 4/10 | 9/10 | 5/10 | 5/10 |
| Sentence Law implementation | 0/10 | 7/10 | 6/10 | 3/10 |
| Test Coverage (gate calibration) | 9/10 | 9/10 | 8/10 | 9/10 |
| Test Coverage (sentence/onset/tail) | 0/10 | 6/10 | 5/10 | 3/10 |
| G8 soft-source logic | 7/10 | 9/10 | 4/10 | 6/10 |
| Threshold calibration (DEC-1) | 7/10 | 9/10 | 3/10 | 6/10 |
| Feature completeness | 1/10 | 7/10 | 6/10 | 4/10 |
| Overall Readiness | 3/10 | 8/10 | 4/10 | 4/10 |

> **Score methodology:** Gemini and Grok penalized heavily for missing sentence-law implementation and threshold-law tension. GPT-4o was more lenient on both. Consensus scores weight the two dissenting models more heavily on contested items and average on uncontested items.

---

## UNANIMOUS FINDINGS (all 3 models agree — implement unconditionally)

### U1 — `run_fresh.py` G8 source-clip wiring fix is correct and necessary
- **File/Lines:** `run_fresh.py` lines 13-16
- **What:** All three models agree that passing `source_clips` to `run_gates` correctly fixes the previously broken G8 path where sources were missing, causing perpetual "no_source" failures that were silently waived.
- **Action:** Keep the fix exactly as written. No change needed; flagged here as a confirmed correct repair.

### U2 — DEC-1 calibration tests in `test_dec1_calibration.py` are high quality and non-vacuous
- **File/Lines:** `pipeline/test_dec1_calibration.py` lines 54-175
- **What:** All three models independently verified that the four boundary-condition tests (`test_g*_just_beyond_fails`) are specific, correctly structured, and cannot pass vacuously. The control test (`test_reference_passes_every_calibrated_gate`) is correctly positioned as the central invariant.
- **Action:** Preserve these tests exactly. Do not alter thresholds, fixture construction, or assertion style.

### U3 — Zero test coverage for Sentence Law, Onset/Tail, and Credits
- **File/Lines:** N/A — missing files
- **What:** All three models noted the absence of any tests covering sentence-boundary detection, mid-sentence cut prevention, the ≥80 ms sub-speech onset/tail rule, or the credits warp defect (D4).
- **Action:** New test files must be created. See Final Action Plan P0-C and P1-B.

---

## MAJORITY FINDINGS (2 of 3 models agree)

### M1 — Sentence Law implementation is entirely absent (Gemini + Grok; GPT-4o partially dissented)
- **File/Lines:** N/A — `pipeline/sentence_law.py` missing or unmodified
- **What:** Gemini flagged this as CRITICAL. Grok treated it as implicit in the Law 20 violation finding. GPT-4o assessed SENTENCE LAW as COMPLIANT, but its reasoning was that "the changes do not affect sentence boundary handling directly" — which is precisely the problem. The feature is n

---

## ORIGINAL CODE (same code as Cycle 1)
## THE CODE (every new and modified file)

### File: docs/audits/pulse-sentence-law/CURRENT.diff (308 lines)
```
   1 | diff --git a/pipeline/run_fresh.py b/pipeline/run_fresh.py
   2 | index ba081a07..12a50b7d 100644
   3 | --- a/pipeline/run_fresh.py
   4 | +++ b/pipeline/run_fresh.py
   5 | @@ -585,8 +585,12 @@ def stage_gates(run, final16, man16, final9, man9):
   6 |          segs9 = json.load(f)["segments"]
   7 |  
   8 |      # Production gate runner — invoked exactly as in the v2f run.
   9 | -    ok16, r16 = run_gates(run.dir, final16, man16)
  10 | -    ok9, r9 = run_gates(run.dir, final9, man9)
  11 | +    # G8 needs its sources (2026-11-11: it was never given any, so it always failed "no_source" and was
  12 | +    # waived): 16:9 = the prepared clips (source camera, 1920x1080), 9:16 = the reframed vertical clips.
  13 | +    src16 = {c["clip_id"]: os.path.join(qa, f"final_{c['clip_id']}.mp4") for c in cuts}
  14 | +    src9 = {c["clip_id"]: os.path.join(qa, f"vert_{c['clip_id']}.mp4") for c in cuts}
  15 | +    ok16, r16 = run_gates(run.dir, final16, man16, source_clips=src16)
  16 | +    ok9, r9 = run_gates(run.dir, final9, man9, source_clips=src9)
  17 |      import qa_gates  # patched by run_gates (BASE/VO_DIR) — same module instance
  18 |  
  19 |      rows = {"16x9": {}, "9x16": {}}
  20 | @@ -664,14 +668,8 @@ def stage_gates(run, final16, man16, final9, man9):
  21 |                                         "same relative offset",
  22 |                   "relative_16x9": g8rel, "degraded_below_0.85": degraded}
  23 |      for fmt, res in (("16x9", r16), ("9x16", r9)):
  24 | -        if res["G8_sharpness"]["pass"]:
  25 | -            rows[fmt]["G8_sharpness"] = "PASS"
  26 | -        elif fmt == "16x9" and degraded:
  27 | -            rows[fmt]["G8_sharpness"] = f"FAIL (pipeline degradation ratio < 0.85: {degraded})"
  28 | -        else:
  29 | -            rows[fmt]["G8_sharpness"] = "FLAG/LIMITED (absolute floor vs soft source; " \
  30 | -                                        "source-relative G8 rule not yet approved)"
  31 | -            flags[fmt].append("G8")
  32 | +        # DEC-1 floor + DEC-3 soft-source rule live in the gate itself; no waiver (DEC-8)
  33 | +        rows[fmt]["G8_sharpness"] = _status(res["G8_sharpness"]["pass"])
  34 |  
  35 |      # G9 — approved known exception only if the outro is hash-identical to the locked outro
  36 |      g9_report = {}
  37 | @@ -687,14 +685,8 @@ def stage_gates(run, final16, man16, final9, man9):
  38 |          g9_report[fmt] = {"gate": d, "outro_master_sha256": msha, "outro_conformed_sha256": csha,
  39 |                            "hash_identical_to_locked_outro": identical,
  40 |                            "last_segment": last.get("label"), "conform_fallback": fallback}
  41 | -        if res["G9_tail"]["pass"]:
  42 | -            rows[fmt]["G9_tail"] = "PASS"
  43 | -        elif identical and last.get("label") == "outro" and d.get("audio_ok") and not d.get("luma_ok"):
  44 | -            rows[fmt]["G9_tail"] = ("FLAG (APPROVED KNOWN EXCEPTION: locked outro ends on black; "
  45 | -                                    f"tail luma {d.get('mean_luma')})")
  46 | -            flags[fmt].append("G9")
  47 | -        else:
  48 | -            rows[fmt]["G9_tail"] = "FAIL"
  49 | +        # DEC-1 calibrated the luma floor to the approved reference's locked outro; no exception path
  50 | +        rows[fmt]["G9_tail"] = _status(res["G9_tail"]["pass"] and (identical or not fallback))
  51 |  
  52 |      # G16 SENTENCE_BOUNDARY: re-run on the final cut state (format-independent; same row in both)
  53 |      adj = L.Adjudicator()
  54 | diff --git a/pipeline/test_dec1_calibration.py b/pipeline/test_dec1_calibration.py
  55 | new file mode 100644
  56 | index 00000000..89bb6816
  57 | --- /dev/null
  58 | +++ b/pipeline/test_dec1_calibration.py
  59 | @@ -0,0 +1,116 @@
  60 | +#!/usr/bin/env python3
  61 | +"""DEC-1 (orchestrator, delegated by PBX, 2026-11-11): the gates PBX's approved v2f reference failed
  62 | +(G3c, G5, G8, G9) are calibrated to the reference's own measured worst value per format, no margin.
  63 | +Each test: the frozen reference PASSES, and a fixture just beyond it FAILS. The reference is read only;
  64 | +modified copies are written to a temp dir. Run: python3 -m pytest -q pipeline/test_dec1_calibration.py"""
  65 | +import contextlib
  66 | +import io
  67 | +import json
  68 | +import os
  69 | +import shutil
  70 | +import subprocess
  71 | +import sys
  72 | +import tempfile
  73 | +import unittest
  74 | +
  75 | +PIPELINE = os.path.dirname(os.path.abspath(__file__))
  76 | +REPO = os.path.dirname(PIPELINE)
  77 | +sys.path.insert(0, os.path.join(REPO, "segment_v1"))
  78 | +REF = os.path.join(REPO, "references", "v2f_2026-11-06", "run")
  79 | +OUT = {"16x9": os.path.join(REF, "out", "segment.mp4"), "9x16": os.path.join(REF, "out", "segment_vertical.mp4")}
  80 | +MAN = {f: os.path.join(REF, "qa", f"concat_manifest_{f}.json") for f in OUT}
  81 | +HAVE_REF = all(os.path.exists(p) for p in list(OUT.values()) + list(MAN.values()))
  82 | +
  83 | +
  84 | +def Q():
  85 | +    import qa_gates
  86 | +    return qa_gates
  87 | +
  88 | +
  89 | +def quiet(fn, *a, **k):
  90 | +    with contextlib.redirect_stdout(io.StringIO()):
  91 | +        return fn(*a, **k)
  92 | +
  93 | +
  94 | +def segs(fmt):
  95 | +    return json.load(open(MAN[fmt]))["segments"]
  96 | +
  97 | +
  98 | +def g8_sources(fmt):
  99 | +    """Production wiring (run_fresh.stage_gates): 16:9 -> prepared clips, 9:16 -> vertical clips."""
 100 | +    pre = "final" if fmt == "16x9" else "vert"
 101 | +    return {c: os.path.join(REF, "qa", f"{pre}_{c}.mp4") for c in ("hook", "clip_01", "clip_02", "clip_03")}
 102 | +
 103 | +
 104 | +def ffmpeg(*args):
 105 | +    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True, timeout=600)
 106 | +
 107 | +
 108 | +@unittest.skipUnless(HAVE_REF, "frozen v2f reference not present")
 109 | +class TestDec1(unittest.TestCase):
 110 | +    @classmethod
 111 | +    def setUpClass(cls):
 112 | +        cls.tmp = tempfile.mkdtemp(prefix="dec1_")
 113 | +
 114 | +    @classmethod
 115 | +    def tearDownClass(cls):
 116 | +        shutil.rmtree(cls.tmp, ignore_errors=True)
 117 | +
 118 | +    def test_constants_are_the_reference_measurements(self):
 119 | +        q = Q()
 120 | +        self.assertEqual(q.G3C_VALLEY_DEPTH_DB, {"16x9": 11.63, "9x16": 11.65})
 121 | +        self.assertEqual(q.G5_TRUE_PEAK_MAX_DBFS, {"16x9": -2.0, "9x16": -1.3})
 122 | +        self.assertEqual(q.G8_SHARPNESS_FLOOR, {"16x9": 27.56, "9x16": 10.84})
 123 | +        self.assertEqual(q.G9_LUMA_FLOOR, {"16x9": 14.33, "9x16": 14.77})
 124 | +
 125 | +    def test_reference_passes_every_calibrated_gate(self):
 126 | +        q = Q()
 127 | +        for fmt in OUT:
 128 | +            self.assertTrue(quiet(q.gate_g3c, OUT[fmt], segs(fmt), self.tmp, fmt=fmt)[0], f"G3c {fmt}")
 129 | +            self.assertTrue(quiet(q.gate_g5, OUT[fmt], fmt)[0], f"G5 {fmt}")
 130 | +            self.assertTrue(quiet(q.gate_g8, OUT[fmt], segs(fmt), self.tmp, source_clips=g8_sources(fmt),
 131 | +                                  fmt=fmt)[0], f"G8 {fmt}")
 132 | +            self.assertTrue(quiet(q.gate_g9, OUT[fmt], self.tmp, fmt=fmt)[0], f"G9 {fmt}")
 133 | +
 134 | +    def test_g3c_just_beyond_fails(self):
 135 | +        # the hook's last 150 ms 1 dB louder: the tail rise crosses speech - 11.63 dB
 136 | +        q = Q()
 137 | +        hook = next(s for s in segs("16x9") if s["label"] == "hook")
 138 | +        t0 = hook["end"] - 0.15
 139 | +        p = os.path.join(self.tmp, "g3c.mp4")
 140 | +        ffmpeg("-i", OUT["16x9"], "-c:v", "copy", "-af",
 141 | +               f"volume=enable='between(t,{t0:.3f},{hook['end']:.3f})':volume=1.122", "-c:a", "aac", "-b:a", "192k", p)
 142 | +        ok, table = quiet(q.gate_g3c, p, segs("16x9"), self.tmp, fmt="16x9")
 143 | +        self.assertFalse(next(r for r in table if r["segment"] == "hook")["pass"])
 144 | +
 145 | +    def test_g5_just_beyond_fails(self):
 146 | +        q = Q()
 147 | +        p = os.path.join(self.tmp, "g5.mp4")
 148 | +        # +1.5 dB (an AAC re-encode moves inter-sample peaks; loudness stays within -14 +/- 1)
 149 | +        ffmpeg("-i", OUT["9x16"], "-c:v", "copy", "-af", "volume=1.5dB", "-c:a", "aac", "-b:a", "192k", p)
 150 | +        ok, d = quiet(q.gate_g5, p, "9x16")
 151 | +        self.assertFalse(d["tp_ok"], d)
 152 | +
 153 | +    def test_g8_just_beyond_fails(self):
 154 | +        # 16:9 hook: reference out median 27.56 == floor, source (prepared hook) above it, so the floor
 155 | +        # applies (DEC-3 does not); a light blur puts the output just below the calibrated floor
 156 | +        q = Q()
 157 | +        p = os.path.join(self.tmp, "g8.mp4")
 158 | +        ffmpeg("-i", OUT["16x9"], "-vf", "gblur=sigma=0.4", "-c:v", "libx264", "-crf", "12", "-preset", "veryfast",
 159 | +               "-c:a", "copy", p)
 160 | +        ok, table = quiet(q.gate_g8, p, segs("16x9"), self.tmp, source_clips=g8_sources("16x9"), fmt="16x9")
 161 | +        hook = next(r for r in table if r["segment"] == "hook")
 162 | +        self.assertFalse(hook["pass"], hook)
 163 | +        self.assertLess(hook["out_median"], q.G8_SHARPNESS_FLOOR["16x9"], hook)
 164 | +
 165 | +    def test_g9_just_beyond_fails(self):
 166 | +        q = Q()
 167 | +        p = os.path.join(self.tmp, "g9.mp4")
 168 | +        ffmpeg("-sseof", "-3", "-i", OUT["16x9"], "-vf", "eq=brightness=-0.006", "-c:v", "libx264", "-crf", "12",
 169 | +               "-preset", "veryfast", "-c:a", "copy", p)
 170 | +        ok, d = quiet(q.gate_g9, p, self.tmp, fmt="16x9")
 171 | +        self.assertFalse(d["luma_ok"] in (True, "True"), d)
 172 | +
 173 | +
 174 | +if __name__ == "__main__":
 175 | +    unittest.main()
 176 | diff --git a/segment_v1/qa_gates.py b/segment_v1/qa_gates.py
 177 | index 293936f5..a6a666da 100644
 178 | --- a/segment_v1/qa_gates.py
 179 | +++ b/segment_v1/qa_gates.py
 180 | @@ -28,6 +28,17 @@ VOICE_SIM_THRESHOLD = 0.75  # Law 20 — do not change
 181 |  TRANSCRIPT_OVERLAP_THRESHOLD = 0.80
 182 |  FPS = 24
 183 |  
 184 | +# ── DEC-1 REFERENCE CALIBRATION (orchestrator, delegated by PBX, 2026-11-11) ──
 185 | +# PBX's approved v2f outputs (references/v2f_2026-11-06/run/out/segment.mp4 sha256 47293813...,
 186 | +# segment_vertical.mp4 sha256 5545a261...) are by definition passing (Law 22). For the four gates they
 187 | +# failed on 2026-11-11 the threshold is the reference's own measured worst value, per format, with no
 188 | +# extra margin (floats truncated to 2 decimals so the reference passes at its own measurement). Every
 189 | +# other threshold is unchanged. Measurements: docs/audits/DEFINITION_OF_DONE_PULSE_CHECK.md (1f).
 190 | +G3C_VALLEY_DEPTH_DB = {"16x9": 11.63, "9x16": 11.65}    # was 12.0: strictest depth at which the v2f hook tail passes (11.6301 / 11.6543)
 191 | +G5_TRUE_PEAK_MAX_DBFS = {"16x9": -2.0, "9x16": -1.3}    # 9x16 was -2.0: v2f segment_vertical.mp4 true peak -1.3 dBFS (16x9 -2.2 passed)
 192 | +G8_SHARPNESS_FLOOR = {"16x9": 27.56, "9x16": 10.84}     # was 60: v2f worst segment medians (16x9 hook 27.56, 9x16 clip_03 10.84)
 193 | +G9_LUMA_FLOOR = {"16x9": 14.33, "9x16": 14.77}          # was 20: v2f tail luma 14.3357 / 14.7715 (locked outro ends on black)
 194 | +
 195 |  # ── Faster-Whisper singleton (medium, float16, cuda, vad OFF, word timestamps) ──
 196 |  _FW_MODEL = None
 197 |  
 198 | @@ -716,7 +727,8 @@ def gate_g5(final_mp4, fmt):
 199 |                              pass
 200 |  
 201 |      lufs_ok = integrated is not None and abs(integrated - (-14)) <= 1.0
 202 | -    tp_ok = true_peak is not None and true_peak <= -2.0
 203 | +    tp_max = G5_TRUE_PEAK_MAX_DBFS.get(fmt, G5_TRUE_PEAK_MAX_DBFS["16x9"])   # DEC-1
 204 | +    tp_ok = true_peak is not None and true_peak <= tp_max
 205 |  
 206 |      results["integrated_lufs"] = integrated
 207 |      results["true_peak"] = true_peak
 208 | @@ -727,7 +739,7 @@ def gate_g5(final_mp4, fmt):
 209 |          all_pass = False
 210 |  
 211 |      print(f"  Integrated: {integrated} LUFS (target -14+/-1) [{'PASS' if lufs_ok else 'FAIL'}]")
 212 | -    print(f"  True Peak: {true_peak} dBFS (target <=-2.0) [{'PASS' if tp_ok else 'FAIL'}]")
 213 | +    print(f"  True Peak: {true_peak} dBFS (target <={tp_max}) [{'PASS' if tp_ok else 'FAIL'}]")
 214 |  
 215 |      return all_pass, results
 216 |  
 217 | @@ -839,7 +851,7 @@ def _laplacian_centre(img_gray):
 218 |  
 219 |  
 220 |  def gate_g8(final_mp4, segments, qa_dir, upscaled_labels=None, crop_widths=None,
 221 | -            source_clips=None):
 222 | +            source_clips=None, fmt="16x9"):
 223 |      """Sharpness gate: absolute floor + source-relative degradation check (R2/A9).
 224 |  
 225 |      Two independent checks per talking-head segment:
 226 | @@ -855,7 +867,7 @@ def gate_g8(final_mp4, segments, qa_dir, upscaled_labels=None, crop_widths=None,
 227 |  
 228 |      print("\n=== G8: SHARPNESS ===")
 229 |  
 230 | -    SHARPNESS_FLOOR = 60          # Law 20 — do not change (for native-res content)
 231 | +    SHARPNESS_FLOOR = G8_SHARPNESS_FLOOR.get(fmt, G8_SHARPNESS_FLOOR["16x9"])  # DEC-1 (was 60)
 232 |      DEGRADATION_RATIO = 0.85      # output must be >= 85% of source sharpness
 233 |  
 234 |      if upscaled_labels is None:
 235 | @@ -940,7 +952,11 @@ def gate_g8(final_mp4, segments, qa_dir, upscaled_labels=None, crop_widths=None,
 236 |              degrad_ok = out_median >= DEGRADATION_RATIO * src_median
 237 |              degrad_reason = None
 238 |  
 239 | -        ok = floor_ok and degrad_ok
 240 | +        # DEC-3 (orchestrator, delegated by PBX, 2026-11-11): a clip is never rejected for SOURCE
 241 | +        # softness alone - when the source itself is below the floor, the render only has to keep
 242 | +        # >= DEGRADATION_RATIO of it. Otherwise floor and ratio both apply.
 243 | +        soft_source = bool(has_source and src_variances and src_median < floor)
 244 | +        ok = degrad_ok if soft_source else (floor_ok and degrad_ok)
 245 |          if not ok:
 246 |              all_pass = False
 247 |  
 248 | @@ -974,14 +990,14 @@ def gate_g8(final_mp4, segments, qa_dir, upscaled_labels=None, crop_widths=None,
 249 |  # G9: TAIL (last 1.0s not black/silent)
 250 |  # ==============================================================
 251 |  
 252 | -def gate_g9(final_mp4, qa_dir):
 253 | +def gate_g9(final_mp4, qa_dir, fmt="16x9"):
 254 |      """Last 1.0s of final file: mean luma > 20 AND audio not silent.
 255 |      Law 20 — do not change thresholds."""
 256 |      import cv2
 257 |  
 258 |      print("\n=== G9: TAIL ===")
 259 |  
 260 | -    LUMA_FLOOR = 20  # Law 20 — do not change
 261 | +    LUMA_FLOOR = G9_LUMA_FLOOR.get(fmt, G9_LUMA_FLOOR["16x9"])  # DEC-1 (was 20)
 262 |      AUDIO_FLOOR_DB = -50  # dBFS; below this = silent
 263 |  
 264 |      dur = get_duration(final_mp4)
 265 | @@ -1506,7 +1522,7 @@ def gate_g13(final_mp4, segments, qa_dir, edl_path=None, channels_json_path=None
 266 |  # G3c: ACOUSTIC_TAIL (M19 — last 120ms of each clip < -35 dBFS)
 267 |  # ==============================================================
 268 |  
 269 | -def gate_g3c(final_mp4, segments, qa_dir):
 270 | +def gate_g3c(final_mp4, segments, qa_dir, fmt="16x9"):
 271 |      """M19a: Acoustic tail check on each talking-head clip in the OUTPUT.
 272 |  
 273 |      Two checks per clip:
 274 | @@ -1522,7 +1538,7 @@ def gate_g3c(final_mp4, segments, qa_dir):
 275 |  
 276 |      import tempfile
 277 |  
 278 | -    VALLEY_DEPTH_DB = 12.0  # M19a: valley zone must be >= 12 dB below speech median
 279 | +    VALLEY_DEPTH_DB = G3C_VALLEY_DEPTH_DB.get(fmt, G3C_VALLEY_DEPTH_DB["16x9"])  # M19a 12 dB; DEC-1
 280 |  
 281 |      all_pass = True
 282 |      table = []
 283 | @@ -1707,7 +1723,7 @@ def run_all_gates(final_mp4, manifest_path, qa_dir=None, source_clips=None,
 284 |          any_fail = True
 285 |  
 286 |      # G3c: Acoustic tail (M19 — last 120ms of each clip < -35 dBFS, no onset)
 287 | -    g3c_pass, g3c_table = gate_g3c(final_mp4, segments, qa_dir)
 288 | +    g3c_pass, g3c_table = gate_g3c(final_mp4, segments, qa_dir, fmt=fmt)
 289 |      results["G3c_acoustic_tail"] = {"pass": g3c_pass, "table": g3c_table}
 290 |      if not g3c_pass:
 291 |          any_fail = True
 292 | @@ -1734,13 +1750,13 @@ def run_all_gates(final_mp4, manifest_path, qa_dir=None, source_clips=None,
 293 |  
 294 |      # G8: Sharpness (source-relative, R2/A9)
 295 |      g8_pass, g8_table = gate_g8(final_mp4, segments, qa_dir,
 296 | -                                 source_clips=source_clips)
 297 | +                                 source_clips=source_clips, fmt=fmt)
 298 |      results["G8_sharpness"] = {"pass": g8_pass, "table": g8_table}
 299 |      if not g8_pass:
 300 |          any_fail = True
 301 |  
 302 |      # G9: Tail (last 1.0s not black/silent)
 303 | -    g9_pass, g9_data = gate_g9(final_mp4, qa_dir)
 304 | +    g9_pass, g9_data = gate_g9(final_mp4, qa_dir, fmt=fmt)
 305 |      results["G9_tail"] = {"pass": g9_pass, "data": g9_data}
 306 |      if not g9_pass:
 307 |          any_fail = True
 308 | 
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
