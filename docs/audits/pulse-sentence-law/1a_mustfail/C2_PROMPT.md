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
The diff contains no implementation of `sentence_law`, `run_fresh`, `gates`, `shoutout`, or `select_passages`. The only code changes are the addition of a 200-line test file and a 2-line update to `utils/cross_llm_audit.py`. No functions that perform clipping, locking, gating, or avatar validation are present, so correctness of those behaviors cannot be verified from the diff.

**Q2: LAW COMPLIANCE**  
- SENTENCE LAW, SELECTION LOCK, SNAP LIMIT, ONSET/TAIL, CREDITS, LAW 20/M2, M12 FAIL CLOSED, LAW 22: cannot be assessed because the enforcing code (`sentence_law.py`, `run_fresh.py`, `shoutout.py`, etc.) is absent from the diff.  
- The only verifiable change (lines 252, 257) adds the feature name to `FEATURE_MAP` and `EXPLICIT_FILES`; this is a documentation update and does not alter any gate logic or thresholds.  
- No evidence of loosened thresholds, recomputation after selection, or v2f divergence is present because no such code appears.

**Q3: TESTS**  
The test file (`pipeline/test_pulse_20261110_mustfail.py`) is added in full (lines 38–243). It defines multiple `Test*` classes that assert `False` on D1–D4 cases and `True` on controls, plus checks that certain function names are absent from `run_fresh`. Because the supporting modules (`sentence_law`, `run_fresh`, `shoutout`) are not in the diff, it is impossible to confirm that the tests actually exercise the intended paths or that assertions cannot pass vacuously. The `TestWindowOffset` and `TestD4Credits` classes contain mocks and file-based checks, but their coverage of the laws cannot be verified from this diff alone.

**Q4: VERDICT**  
No defects can be listed because the diff contains only a gospel document, a test suite, and a two-line audit-script update; the actual enforcement logic is not present.  
**NOT READY** — the diff does not include the code required to implement or demonstrate compliance with the stated laws.

## GPT4O — CYCLE 1 OUTPUT
### Q1: CORRECTNESS

1. **Functionality and Compliance**: The functions appear to be designed to enforce the laws as described. The test suite is comprehensive, covering various scenarios like missing lead-in pads, incorrect sentence boundaries, and avatar validation. The functions are structured to ensure that any failure in data or model results in a rejection, adhering to the M12 FAIL CLOSED law.

2. **Time/Index Handling**: The code uses `ffprobe` to get the duration of media files, which is a reliable method. The use of floating-point arithmetic for time calculations seems appropriate, and there are no obvious off-by-one errors in the index handling.

3. **Silent Exceptions**: There are no silent exceptions in the test cases. All exceptions are either caught and handled or allowed to propagate as part of the test validation.

4. **State Leakage**: The use of class-level setup and teardown methods in `_G16Fixture` ensures that state does not leak between tests. Temporary directories are created and cleaned up properly.

5. **Pass Conditions**: The tests are designed to fail if any condition is not met, ensuring that no path can produce a PASS when data is missing or a model fails.

### Q2: LAW COMPLIANCE

1. **SENTENCE LAW**: COMPLIANT - The tests ensure that clips start and end at sentence boundaries, with appropriate pauses (lines 138-158).

2. **SELECTION LOCK**: COMPLIANT - The selection locks are created and verified to ensure that no words are added or dropped after selection (lines 116-116).

3. **SNAP LIMIT**: COMPLIANT - The tests ensure that cuts do not move outside the allowed silence (lines 146-148).

4. **ONSET/TAIL**: COMPLIANT - Tests check for genuine sub-speech audio before and after segments (lines 139-142).

5. **CREDITS**: COMPLIANT - The tests ensure that avatars are correctly validated and that no fallbacks to thumbnails or placeholders occur (lines 230-239).

6. **LAW 20 / M2**: COMPLIANT - Gate thresholds are constants, and any failure results in a hard stop (lines 171-171).

7. **M12 FAIL CLOSED**: COMPLIANT - The code is structured to reject any missing data or model failures (lines 171-171).

8. **LAW 22**: COMPLIANT - The v2f reference is checked to ensure byte-identical re-rendering (lines 224-228).

### Q3: TESTS

1. **Must-Fail Fixtures**: The must-fail tests are well-designed to fail for the right reasons, such as incorrect sentence boundaries or missing lead-in pads (lines 139-158).

2. **Control Tests**: Control tests are included to ensure that correct conditions pass, such as the acoustically clean clip (lines 160-162).

3. **Vacuous Assertions**: There are no vacuous assertions. Each test has a clear purpose and checks specific conditions.

### Q4: VERDICT

1. **SEVERITY: Low | Diff Line: 139 | Issue: Test for lead-in pad could be more descriptive | Fix: Add more context to the assertion message to clarify the failure reason.**

2. **SEVERITY: Low | Diff Line: 230 | Issue: Test for avatar validation could specify the expected exception message | Fix: Include the expected exception message in the `assertRaises` context.**

Overall, the code is well-structured, adheres to the laws, and the tests are comprehensive. The minor issues noted do not affect the overall functionality or compliance.

**VERDICT: READY**

## GEMINI — CYCLE 1 OUTPUT
### Q1: CORRECTNESS
As the provided diff contains no application logic changes, I can only assess the correctness of the new test suite, `pipeline/test_pulse_20261110_mustfail.py`. The suite is well-designed and appears correct in its approach.

-   The test fixture setup in `_G16Fixture.setUpClass` (diff lines 100-124) is correct. It correctly recreates the conditions of the original run by programmatically generating the `selection_lock` (lines 113-114) from the editor's original selection (`B3_chosen.json`). This is crucial for correctly testing for violations against the SELECTION LOCK law, as it establishes the ground truth against which the faulty cuts are measured.
-   The test for the download window offset (`TestWindowOffset`, lines 186-205) correctly uses mocking to intercept the `subprocess.run` call. It then parses the requested download section from the command-line arguments and compares it to the function's returned offset. Using `assertAlmostEqual` (line 202) is the correct way to handle potential floating-point inaccuracies.
-   The tests correctly use a cached, non-live model adjudicator (`allow_model=False`, line 118), which upholds the `M12 FAIL CLOSED` law: if an adjudication is not in the pre-approved cache, the test will fail rather than attempting a new, non-deterministic adjudication.

The test functions do what their names and the file's docstring claim. I can't see how a pass could be produced on missing data; the design seems to ensure failure in such cases.

### Q2: LAW COMPLIANCE
The new test suite is explicitly designed to enforce the Governing Laws by failing on code that violates them. While I cannot see the fixed code, the tests themselves are fully compliant with the spirit and letter of the laws.

-   **SENTENCE LAW:** COMPLIANT. `TestD2Clip01Out` and `TestD3Edges` (lines 146-163) contain assertions that are designed to fail if cuts start or end mid-sentence, directly enforcing this law.
-   **SELECTION LOCK:** COMPLIANT. This law is a primary focus. `TestTautology.test_recomputed_expected_words_fail_the_lock` (line 166) specifically checks that the gate fails if it recomputes expected words instead of using the sealed lock. Furthermore, `TestTautology.test_run_fresh_has_no_recompute_sync_or_wide_snap` (line 173) asserts that the functions which previously performed this re-computation have been physically removed from the codebase.
-   **SNAP LIMIT:** COMPLIANT. The aforementioned test asserting the removal of `_snap_candidates` (line 176) suggests that an overly permissive snapping mechanism has been removed, which is a core part of enforcing this law.
-   **ONSET/TAIL:** COMPLIANT. `TestD1HookOnset.test_g16_in_fails_without_lead_in_pad` (line 137) contains a specific assertion to check that the `genuine_lead_ms` is below the 80ms threshold (line 140), directly testing a requirement of this law.
-   **CREDITS:** COMPLIANT. `TestD4Credits` (lines 207-240) is a robust enforcement of this law. It confirms that the old, warped avatars fail the gates (line 217), a known-good reference passes them (line 224), the system explicitly rejects non-square avatar images (line 232), and that old fallback logic has been removed from the source (lines 238-239).
-   **LAW 20 / M2 (Hard Stop):** COMPLIANT. The entire premise of this "must-fail" test suite is to turn previously silent failures into hard gate failures, which is the essence of this law.
-   **M12 FAIL CLOSED:** COMPLIANT. As noted in Q1, the use of a fixed adjudication cache with `allow_model=False` (line 118) enforces this principle.
-   **LAW 22 (v2f Reference):** COMPLIANT. `test_v2f_finals_pass_g15_and_g12` (line 224) acts as a regression test, ensuring that the new, stricter gates do not accidentally fail the frozen reference render.

### Q3: TESTS
The quality of the tests in `pipeline/test_pulse_20261110_mustfail.py` is excellent. They convincingly prove the claims of the feature.

-   The tests are structured to fail on the current codebase for exactly the reasons outlined in the file's docstring (lines 53-66). For example, `test_g16_in_fails_without_lead_in_pad` (line 137) not only asserts the gate fails but also asserts *why* it fails (`assertLess(r["genuine_lead_ms"], 80)`).
-   The suite includes critical "control" tests that must pass, such as `test_d3c_clip02_out_control_passes` (line 160) and `test_v2f_finals_pass_g15_and_g12` (line 224). These ensure that the eventual fix is not overly aggressive and does not break previously working cases.
-   The tests do not appear to have any assertions that could pass vacuously. They check specific boolean return values, numeric comparisons, and even the content of error messages.
-   A particularly strong and non-vacuous testing pattern is used in lines 173-178 and 235-240, where `inspect.getsource` is used to assert that specific buggy functions and fallback logic have been completely removed from the source code. This is a powerful way to prevent regression.

### Q4: 

## CLAUDE'S CYCLE 1 CONSENSUS
# CONSENSUS REPORT — PULSE-SENTENCE-LAW — CYCLE 1
Generated: 2026-11-11 02:30
Models: grok, gpt4o, gemini

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Correctness | 9/10 | 8/10 | N/A (no impl code) | 8.5/10 |
| Law Compliance | 10/10 | 9/10 | N/A (no impl code) | 9.5/10 |
| Test Quality | 10/10 | 8/10 | 6/10 (unverifiable) | 8/10 |
| Overall Verdict | READY | READY | NOT READY | CONDITIONAL READY |

> **Score Note:** Grok's N/A scores are not a failing assessment of test quality — they reflect a methodologically strict position that the diff contains no implementation code. Gemini and GPT-4o both assessed the test suite as the artifact under review, which is the correct framing given the diff content.

---

## UNANIMOUS FINDINGS (all 3 models agree — implement unconditionally)

**None.** The three models did not unanimously flag a shared concrete defect requiring a code change. This is because:
- Gemini and GPT-4o found no defects in the diff.
- Grok's finding is structural (missing implementation), not a defect within the diff's own code.

The one point all three models *implicitly* agree on:

### U1 — The diff contains no implementation of `sentence_law`, `run_fresh`, `shoutout`, or `select_passages`
- **File:** `pipeline/sentence_law.py`, `pipeline/run_fresh.py`, `pipeline/shoutout.py` (absent)
- **What it means:** The enforcement logic is not in this diff. All three models noticed this. Grok treats it as a blocker; Gemini and GPT-4o treat it as expected (TDD: tests first, fixes second).
- **Action:** The implementation files MUST appear in the second build pass. This is the entire reason the second pass prompt exists.

---

## MAJORITY FINDINGS (2 of 3 models agree)

### M1 — Test suite is correctly structured as TDD / "must-fail" contract
- **Models:** Gemini + GPT-4o
- **Finding:** The test file `pipeline/test_pulse_20261110_mustfail.py` is correctly designed. Must-fail cases will fail on current buggy code; control cases confirm non-regression. This is the intended structure.
- **Action:** No change needed to the tests. Implement the enforcement code to satisfy them.

### M2 — `M12 FAIL CLOSED` is correctly enforced by `allow_model=False` + cache
- **Models:** Gemini + GPT-4o
- **File/Line:** `pipeline/test_pulse_20261110_mustfail.py`, line ~118
- **Finding:** Using a fixed adjudication cache with `allow_model=False` ensures non-deterministic model calls cannot produce a spurious PASS. Both models independently called this out as correct and important.
- **Action:** This pattern must be preserved in all future test additions. Do not add any test that calls a live model without an explicit cache hit.

### M3 — `inspect.getsource` assertions confirm removal of banned functions
- **Models:** Gemini + GPT-4o
- **File/Line:** `pipeline/test_pulse_20261110_mustfail.py`, lines ~173–178, ~235–240
- **Finding:** Asserting that `_snap_candidates`, `recompute_sync`, `wide_snap`, and thumbnail/placeholder

---

## ORIGINAL CODE (same code as Cycle 1)
## THE CODE (every new and modified file)

### File: docs/audits/pulse-sentence-law/CURRENT.diff (290 lines)
```
   1 | diff --git a/docs/gospels/PULSE_SENTENCE_LAW_GOSPEL.md b/docs/gospels/PULSE_SENTENCE_LAW_GOSPEL.md
   2 | new file mode 100644
   3 | index 00000000..665fd49d
   4 | --- /dev/null
   5 | +++ b/docs/gospels/PULSE_SENTENCE_LAW_GOSPEL.md
   6 | @@ -0,0 +1,31 @@
   7 | +# PULSE CHECK SENTENCE LAW GOSPEL (PBX review of run pinned_20261110_150345, 2026-11-11)
   8 | +
   9 | +## WHAT THIS FEATURE IS
  10 | +The automated Protocol Pulse "Pulse Check" medley (pipeline/run_fresh.py) cuts hooks and clips from
  11 | +partner YouTube videos, renders 16:9 and 9:16, and runs QA gates. PBX watched the 2026-11-10 cut and
  12 | +found editorial errors every gate had passed: the opening word sounded clipped (D1), clips started or
  13 | +ended mid-sentence (D2/D3), credit avatars were warped (D4), the vertical was letterboxed (D5) and
  14 | +channel changes were abrupt (D6). This work makes the gates catch what a human caught, proves it on
  15 | +yesterday's files (tests/fixtures/pulse_20261110, pipeline/test_pulse_20261110_mustfail.py), fixes the
  16 | +causes, then requires three clean fresh videos in a row with no code edits between them.
  17 | +
  18 | +## THE LAWS
  19 | +- SENTENCE LAW: a clip's first word is the first word of a sentence and its last word the last word of
  20 | +  a sentence. Boundary = transcript punctuation (or a cached, logged local-model adjudication when the
  21 | +  transcript has no punctuation) AND an acoustic pause >= 80 ms between the two words
  22 | +  (pipeline/sentence_law.py states every constant).
  23 | +- SELECTION LOCK: the words a clip must contain are fixed at selection time (selection_lock in edl.json,
  24 | +  sha256-sealed). No later stage may recompute expected first/last words from a moved cut.
  25 | +- SNAP LIMIT: a cut may move only inside the silence between the chosen sentence and its neighbour; it
  26 | +  may never add or drop a word. No legal boundary in that gap = the window is rejected.
  27 | +- ONSET/TAIL: every rendered segment keeps >= 80 ms of genuine sub-speech audio before its first onset
  28 | +  and after its last offset; codec zero/padding is not room tone; a source that starts speaking at its
  29 | +  file head without lead-in needs a declared room-tone lead-in pad. Edge words keep >= 85 % of their
  30 | +  duration in the render.
  31 | +- CREDITS: round avatars of the channels actually used; the avatar is the channel's real square avatar,
  32 | +  never a video thumbnail, never a generated placeholder; G12/G15 unchanged.
  33 | +- LAW 20 / M2: gate thresholds are constants; a failed gate is a hard stop; never change what a check
  34 | +  accepts to make a render pass; never reclassify a failing gate as a false positive.
  35 | +- M12 FAIL CLOSED: missing data, model failure or an exception rejects; it never produces a pass.
  36 | +- LAW 22: the frozen v2f reference (references/v2f_2026-11-06) must keep re-rendering byte-identically.
  37 | +- Smallest diff; no new renderer, compositor or selector (M1); GPU0 only; no publishing.
  38 | diff --git a/pipeline/test_pulse_20261110_mustfail.py b/pipeline/test_pulse_20261110_mustfail.py
  39 | new file mode 100644
  40 | index 00000000..38f64690
  41 | --- /dev/null
  42 | +++ b/pipeline/test_pulse_20261110_mustfail.py
  43 | @@ -0,0 +1,200 @@
  44 | +#!/usr/bin/env python3
  45 | +"""MUST-FAIL fixture: PBX's review of runs/pinned_20261110_150345 (Telegram 67444/67445, 2026-11-11).
  46 | +
  47 | +EXPECTED ON HEAD 7a76a5c5 (before the checks land): every DEFECT test FAILS, because no check exists
  48 | +that catches the defect or the existing path accepts it; the CONTROL tests (v2f card passes G12/G15,
  49 | +clip_02 out edge is clean) document what must keep passing. A green run means the checks landed.
  50 | +Never invert an assertion to make it pass. Fixture: tests/fixtures/pulse_20261110 (copies; the run dir
  51 | +is never modified). No GPU, no model calls: the unpunctuated-transcript adjudications are cached.
  52 | +
  53 | +D1  hook opens on "Bitcoin" at source 0.000 with 60 ms of genuine room tone before the onset (30 ms of
  54 | +    codec zero first) and no lead-in pad              -> G16 IN and G17a head FAIL
  55 | +D2  clip_01 out 33.71 runs 2.4 s into the next sentence ("All right, you've probably seen people
  56 | +    celebrating"); the sentence ends at 'week.'       -> G16 OUT FAIL
  57 | +D3a clip_01 in 15.13 starts on "81" (sentence: "It went from above $81,000 ...") -> G16 IN + G17a FAIL
  58 | +D3b clip_02 in 14.93 lands inside "days" (sentence: "Of course, Bitcoin dropped ...") -> G16 IN + G17a FAIL
  59 | +D3c clip_02 out 34.36 is a CONTROL and must PASS: acoustically clean (pause 34.08-34.43, the 'I' onset
  60 | +    is 34.44; whisper on the prepared clip ends "...many times."). The transcript word 'i' 33.92-34.46
  61 | +    is a whisper timestamp error, not a defect.
  62 | +T   ad7295ea/4cf5a31a tautology: expected words recomputed from the moved cut -> G16 lock FAIL
  63 | +OFF window offset: yt-dlp is asked for '*54-100' but the offset recorded is 53.57 (source of D3)
  64 | +D4  credits: the 'avatars' are 1280x720 video thumbnails squashed into circles -> G15 and G12 FAIL on
  65 | +    yesterday's card and PASS on the frozen v2f finals; the shout-out builder must refuse a non-square
  66 | +    avatar and must not fall back to a video thumbnail or a generated placeholder.
  67 | +"""
  68 | +import inspect
  69 | +import json
  70 | +import os
  71 | +import shutil
  72 | +import subprocess
  73 | +import sys
  74 | +import tempfile
  75 | +import unittest
  76 | +from unittest import mock
  77 | +
  78 | +PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
  79 | +REPO = os.path.dirname(PIPELINE_DIR)
  80 | +sys.path.insert(0, PIPELINE_DIR)
  81 | +sys.path.insert(0, os.path.join(REPO, "segment_v1"))
  82 | +FIX = os.path.join(REPO, "tests", "fixtures", "pulse_20261110")
  83 | +V2F = os.path.join(REPO, "references", "v2f_2026-11-06", "run")
  84 | +
  85 | +
  86 | +def _law():
  87 | +    import sentence_law
  88 | +    return sentence_law
  89 | +
  90 | +
  91 | +def _dur(p):
  92 | +    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
  93 | +                                capture_output=True, text=True, check=True).stdout)
  94 | +
  95 | +
  96 | +class _G16Fixture(unittest.TestCase):
  97 | +    """Yesterday's cuts against selection locks built from the editor's B3 decision."""
  98 | +
  99 | +    @classmethod
 100 | +    def setUpClass(cls):
 101 | +        L = _law()
 102 | +        cls.tmp = tempfile.mkdtemp(prefix="pulse_20261110_")
 103 | +        shutil.copytree(os.path.join(FIX, "run", "transcripts"), os.path.join(cls.tmp, "transcripts"))
 104 | +        shutil.copy(os.path.join(FIX, "run", "cuts_final.json"), cls.tmp)
 105 | +        edl = json.load(open(os.path.join(FIX, "run", "edl.json")))
 106 | +        sel = {p["video_id"]: p for p in json.load(open(os.path.join(FIX, "selection", "B3_chosen.json")))["chosen"]}
 107 | +        cls.locks = {}
 108 | +        for label, seg in [("hook", edl["hook"])] + [(f"clip_{c['index']:02d}", c) for c in edl["clips"]]:
 109 | +            tpath = os.path.join(cls.tmp, "transcripts", f"{seg['video_id']}.json")
 110 | +            words = json.load(open(tpath))["words"]
 111 | +            p = sel[seg["video_id"]]
 112 | +            i0, i1, r = L.anchor(words, p["text"])
 113 | +            seg["selection_lock"] = L.make_lock(seg["video_id"], words, i0, i1, L.sha256_file(tpath), p["text"],
 114 | +                                                [p["start"], p["end"]], r, "B3 (fixture)")
 115 | +            cls.locks[label] = seg["selection_lock"]
 116 | +        json.dump(edl, open(os.path.join(cls.tmp, "edl.json"), "w"), indent=1)
 117 | +        adj = L.Adjudicator(cache_path=os.path.join(FIX, "selection", "sentence_adjudication.json"),
 118 | +                            log_path=None, allow_model=False)
 119 | +        cls.ok, table = L.gate_g16(cls.tmp, adj, source_path_fn=lambda v: os.path.join(FIX, "audio", f"src_{v}.flac"))
 120 | +        cls.rows = {r["segment"]: r for r in table}
 121 | +        cls.g17_ok, t17 = L.gate_g17_prepared(
 122 | +            {c: os.path.join(FIX, "audio", f"prepared_{c}.flac") for c in ("hook", "clip_01", "clip_02")})
 123 | +        cls.g17 = {r["segment"]: r for r in t17}
 124 | +
 125 | +    @classmethod
 126 | +    def tearDownClass(cls):
 127 | +        shutil.rmtree(cls.tmp, ignore_errors=True)
 128 | +
 129 | +
 130 | +class TestSelectionLockEdges(_G16Fixture):
 131 | +    def test_locks_hold_the_editors_sentences(self):
 132 | +        got = {k: (v["first_word"], v["last_word"]) for k, v in self.locks.items()}
 133 | +        self.assertEqual(got, {"hook": ("Bitcoin", "take."), "clip_01": ("It", "week."), "clip_02": ("of", "times")})
 134 | +
 135 | +
 136 | +class TestD1HookOnset(_G16Fixture):
 137 | +    def test_g16_in_fails_without_lead_in_pad(self):
 138 | +        r = self.rows["hook"]["in"]
 139 | +        self.assertFalse(r["pass"], r)
 140 | +        self.assertLess(r["genuine_lead_ms"], 80)
 141 | +
 142 | +    def test_g17a_head_fails(self):
 143 | +        self.assertFalse(self.g17["hook"]["lead_ok"], self.g17["hook"])
 144 | +
 145 | +
 146 | +class TestD2Clip01Out(_G16Fixture):
 147 | +    def test_g16_out_fails(self):
 148 | +        self.assertFalse(self.rows["clip_01"]["out"]["pass"], self.rows["clip_01"]["out"])
 149 | +
 150 | +
 151 | +class TestD3Edges(_G16Fixture):
 152 | +    def test_d3a_clip01_in_fails(self):
 153 | +        self.assertFalse(self.rows["clip_01"]["in"]["pass"], self.rows["clip_01"]["in"])
 154 | +        self.assertFalse(self.g17["clip_01"]["lead_ok"], self.g17["clip_01"])
 155 | +
 156 | +    def test_d3b_clip02_in_fails(self):
 157 | +        self.assertFalse(self.rows["clip_02"]["in"]["pass"], self.rows["clip_02"]["in"])
 158 | +        self.assertFalse(self.g17["clip_02"]["lead_ok"], self.g17["clip_02"])
 159 | +
 160 | +    def test_d3c_clip02_out_control_passes(self):
 161 | +        self.assertTrue(self.rows["clip_02"]["out"]["pass"], self.rows["clip_02"]["out"])
 162 | +        self.assertTrue(self.g17["clip_02"]["tail_ok"], self.g17["clip_02"])
 163 | +
 164 | +
 165 | +class TestTautology(_G16Fixture):
 166 | +    def test_recomputed_expected_words_fail_the_lock(self):
 167 | +        for c in ("clip_01", "clip_02"):
 168 | +            self.assertTrue(any("recomputed" in e for e in self.rows[c]["errors"]), self.rows[c]["errors"])
 169 | +
 170 | +    def test_gate_fails_overall(self):
 171 | +        self.assertFalse(self.ok)
 172 | +
 173 | +    def test_run_fresh_has_no_recompute_sync_or_wide_snap(self):
 174 | +        import run_fresh
 175 | +        src = inspect.getsource(run_fresh)
 176 | +        for name in ("_recompute_edge_words", "_sync_edl_edge_words", "_snap_candidates"):
 177 | +            self.assertNotIn(f"def {name}", src, f"{name} still present")
 178 | +
 179 | +    def test_gates_stage_runs_g16_and_g17(self):
 180 | +        import run_fresh
 181 | +        src = inspect.getsource(run_fresh.stage_gates)
 182 | +        self.assertIn("G16_sentence_boundary", src)
 183 | +        self.assertIn("G17_onset_tail", src)
 184 | +
 185 | +
 186 | +class TestWindowOffset(unittest.TestCase):
 187 | +    def test_recorded_offset_equals_requested_section_start(self):
 188 | +        import select_passages as sp
 189 | +        tmp = tempfile.mkdtemp(prefix="dlwin_")
 190 | +        seen = {}
 191 | +
 192 | +        def fake_run(cmd, **kw):
 193 | +            seen["section"] = cmd[cmd.index("--download-sections") + 1]
 194 | +            out = cmd[cmd.index("-o") + 1]
 195 | +            with open(out, "wb") as f:
 196 | +                f.write(b"\0" * 200_000)
 197 | +            return subprocess.CompletedProcess(cmd, 0, "", "")
 198 | +        try:
 199 | +            with mock.patch.object(sp.subprocess, "run", side_effect=fake_run):
 200 | +                path, off = sp._download_window("lusJ1m-J0Mc", 68.57, 85.41, tmp)
 201 | +            start = float(seen["section"].lstrip("*").split("-")[0])
 202 | +            self.assertAlmostEqual(off, start, places=3, msg=f"requested {seen['section']} recorded {off}")
 203 | +        finally:
 204 | +            shutil.rmtree(tmp, ignore_errors=True)
 205 | +
 206 | +
 207 | +class TestD4Credits(unittest.TestCase):
 208 | +    S = tempfile.mkdtemp(prefix="g15_")
 209 | +
 210 | +    def _gates(self, mp4, segs):
 211 | +        import gates as G
 212 | +        import qa_gates as Q
 213 | +        ok15, _ = G.gate_g15(mp4, segs, self.S)
 214 | +        ok12, _ = Q.gate_g12(mp4, segs, 3, self.S)
 215 | +        return ok15, ok12
 216 | +
 217 | +    def test_yesterdays_card_fails_g15_and_g12(self):
 218 | +        for fmt in ("16x9", "9x16"):
 219 | +            p = os.path.join(FIX, "video", f"shoutout_{fmt}.mp4")
 220 | +            ok15, ok12 = self._gates(p, [{"label": "shoutout", "type": "shoutout", "start": 0.0, "end": _dur(p)}])
 221 | +            self.assertFalse(ok15, f"G15 passed yesterday's {fmt} card")
 222 | +            self.assertFalse(ok12, f"G12 passed yesterday's {fmt} card")
 223 | +
 224 | +    def test_v2f_finals_pass_g15_and_g12(self):
 225 | +        for out, man in (("segment.mp4", "concat_manifest_16x9.json"), ("segment_vertical.mp4", "concat_manifest_9x16.json")):
 226 | +            segs = json.load(open(os.path.join(V2F, "qa", man)))["segments"]
 227 | +            ok15, ok12 = self._gates(os.path.join(V2F, "out", out), segs)
 228 | +            self.assertTrue(ok15 and ok12, f"v2f {out}: G15 {ok15} G12 {ok12}")
 229 | +
 230 | +    def test_shoutout_refuses_a_thumbnail_avatar(self):
 231 | +        import shoutout
 232 | +        with self.assertRaises(ValueError):
 233 | +            shoutout.validate_avatar(os.path.join(FIX, "video", "natalie_brunell.jpg"))
 234 | +
 235 | +    def test_no_thumbnail_or_placeholder_fallback(self):
 236 | +        import shoutout
 237 | +        src = inspect.getsource(shoutout)
 238 | +        self.assertFalse('meta.get("thumbnail")' in src, "video-thumbnail fallback still in shoutout.py")
 239 | +        self.assertFalse("placeholder" in src.lower(), "generated placeholder avatar still in shoutout.py")
 240 | +
 241 | +
 242 | +if __name__ == "__main__":
 243 | +    unittest.main()
 244 | diff --git a/utils/cross_llm_audit.py b/utils/cross_llm_audit.py
 245 | index 562fdf3a..3f4be510 100755
 246 | --- a/utils/cross_llm_audit.py
 247 | +++ b/utils/cross_llm_audit.py
 248 | @@ -90,10 +90,12 @@ FEATURE_MAP = {
 249 |      "value-stream-mvp": ("VISUAL_DESIGN_SYSTEM.md", "main"),
 250 |      "value-stream-post-audit": ("VISUAL_DESIGN_SYSTEM.md", "main"),
 251 |      "track-a-d1-d3": ("TRACK_A_EDITORIAL_GOSPEL.md", "combo-letterbox-quoteonly-v2"),
 252 | +    "pulse-sentence-law": ("PULSE_SENTENCE_LAW_GOSPEL.md", "combo-letterbox-quoteonly-v2"),
 253 |  }
 254 |  
 255 |  # Explicit file lists for features already merged to main (no branch diff available)
 256 |  EXPLICIT_FILES = {
 257 | +    "pulse-sentence-law": ["docs/audits/pulse-sentence-law/CURRENT.diff"],
 258 |      "track-a-d1-d3": ["docs/audits/track-a-d1-d3/D1_D3.diff", "pipeline/editorial_select.py",
 259 |                        "pipeline/story_semantics.py", "pipeline/test_window_review.py",
 260 |                        "pipeline/test_editorial_robust.py", "pipeline/test_editorial.py"],
 261 | @@ -304,6 +306,28 @@ ROUTE_EXTRACTS = {
 262 |  }
 263 |  
 264 |  CUSTOM_REVIEW_TASKS = {
 265 | +    "pulse-sentence-law": """

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
