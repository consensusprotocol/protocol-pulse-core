# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pulse-sentence-law
# Branch: combo-letterbox-quoteonly-v2
# Generated: 2026-11-11 04:35 UTC
# Purpose: Pre-merge quality gate. 3 independent AI models will review this.
# You are one of: Gemini 2.5 Pro / GPT-4o / Grok-3
# Other top AI models will also review this same code. Put your best work forward.

---

## WHAT THIS FEATURE DOES
The automated Protocol Pulse "Pulse Check" medley (pipeline/run_fresh.py) cuts hooks and clips from
partner YouTube videos, renders 16:9 and 9:16, and runs QA gates. PBX watched the 2026-11-10 cut and
found editorial errors every gate had passed: the opening word sounded clipped (D1), clips started or
ended mid-sentence (D2/D3), credit avatars were warped (D4), the vertical was letterboxed (D5) and
channel changes were abrupt (D6). This work makes the gates catch what a human caught, proves it on
yesterday's files (tests/fixtures/pulse_20261110, pipeline/test_pulse_20261110_mustfail.py), fixes the
causes, then requires three clean fresh videos in a row with no code edits between them.

---

## GOVERNING LAWS (this code MUST comply with every law below — flag any violation)
## THE LAWS
- SENTENCE LAW: a clip's first word is the first word of a sentence and its last word the last word of
  a sentence. Boundary = transcript punctuation (or a cached, logged local-model adjudication when the
  transcript has no punctuation) AND an acoustic pause >= 80 ms between the two words
  (pipeline/sentence_law.py states every constant).
- SELECTION LOCK: the words a clip must contain are fixed at selection time (selection_lock in edl.json,
  sha256-sealed). No later stage may recompute expected first/last words from a moved cut.
- SNAP LIMIT: a cut may move only inside the silence between the chosen sentence and its neighbour; it
  may never add or drop a word. No legal boundary in that gap = the window is rejected.
- ONSET/TAIL: every rendered segment keeps >= 80 ms of genuine sub-speech audio before its first onset
  and after its last offset; codec zero/padding is not room tone; a source that starts speaking at its
  file head without lead-in needs a declared room-tone lead-in pad. Edge words keep >= 85 % of their
  duration in the render.
- CREDITS: round avatars of the channels actually used; the avatar is the channel's real square avatar,
  never a video thumbnail, never a generated placeholder; G12/G15 unchanged.
- LAW 20 / M2: gate thresholds are constants; a failed gate is a hard stop; never change what a check
  accepts to make a render pass; never reclassify a failing gate as a false positive.
- M12 FAIL CLOSED: missing data, model failure or an exception rejects; it never produces a pass.
- LAW 22: the frozen v2f reference (references/v2f_2026-11-06) must keep re-rendering byte-identically.
- Smallest diff; no new renderer, compositor or selector (M1); GPU0 only; no publishing.



---

## TECHNOLOGY STACK
- Python 3.12, Flask 3.x, SQLite via SQLAlchemy ORM
- Ubuntu 24.04 on Ultron server (2x RTX 4090, 93GB RAM)
- All UI animations: CSS/SVG only — NO Three.js, no WebGL, no Canvas
- External services: ElevenLabs TTS, HeyGen avatars, Wav2Lip GPU lip-sync
- ~1000 concurrent users at peak — every route must handle load
- Every DB query on a sort/filter column MUST have an index

---

## THE CODE (every new and modified file)

### File: docs/audits/pulse-sentence-law/CURRENT.diff (68 lines)
```
   1 | diff --git a/pipeline/run_fresh.py b/pipeline/run_fresh.py
   2 | index 12a50b7d..179e56a7 100644
   3 | --- a/pipeline/run_fresh.py
   4 | +++ b/pipeline/run_fresh.py
   5 | @@ -568,6 +568,13 @@ def _status(ok):
   6 |      return "PASS" if ok else "FAIL"
   7 |  
   8 |  
   9 | +def tail_rows(g9_pass, conform_fallback):
  10 | +    """G9_tail is the DEC-1 calibrated gate alone (no exception path). outro_locked: the luma floor is
  11 | +    the approved reference's LOCKED outro tail, so a conform fallback (some other outro) fails closed
  12 | +    on its own row even when its tail clears the floor (Heimdall DEC-1 audit: keep the two apart)."""
  13 | +    return {"G9_tail": _status(g9_pass), "outro_locked": _status(not conform_fallback)}
  14 | +
  15 | +
  16 |  def stage_gates(run, final16, man16, final9, man9):
  17 |      # Keep the source-relative sharpness threshold local to this stage so QA does not
  18 |      # depend on module-global lookup state during long production runs. Threshold unchanged.
  19 | @@ -685,8 +692,7 @@ def stage_gates(run, final16, man16, final9, man9):
  20 |          g9_report[fmt] = {"gate": d, "outro_master_sha256": msha, "outro_conformed_sha256": csha,
  21 |                            "hash_identical_to_locked_outro": identical,
  22 |                            "last_segment": last.get("label"), "conform_fallback": fallback}
  23 | -        # DEC-1 calibrated the luma floor to the approved reference's locked outro; no exception path
  24 | -        rows[fmt]["G9_tail"] = _status(res["G9_tail"]["pass"] and (identical or not fallback))
  25 | +        rows[fmt].update(tail_rows(res["G9_tail"]["pass"], fallback))
  26 |  
  27 |      # G16 SENTENCE_BOUNDARY: re-run on the final cut state (format-independent; same row in both)
  28 |      adj = L.Adjudicator()
  29 | diff --git a/pipeline/test_dec1_calibration.py b/pipeline/test_dec1_calibration.py
  30 | index e20b4bd5..2b6ed47a 100644
  31 | --- a/pipeline/test_dec1_calibration.py
  32 | +++ b/pipeline/test_dec1_calibration.py
  33 | @@ -16,6 +16,7 @@ import unittest
  34 |  PIPELINE = os.path.dirname(os.path.abspath(__file__))
  35 |  REPO = os.path.dirname(PIPELINE)
  36 |  sys.path.insert(0, os.path.join(REPO, "segment_v1"))
  37 | +sys.path.insert(0, PIPELINE)                      # run_fresh (no module name is shared with segment_v1)
  38 |  REF = os.path.join(REPO, "references", "v2f_2026-11-06", "run")
  39 |  OUT = {"16x9": os.path.join(REF, "out", "segment.mp4"), "9x16": os.path.join(REF, "out", "segment_vertical.mp4")}
  40 |  MAN = {f: os.path.join(REF, "qa", f"concat_manifest_{f}.json") for f in OUT}
  41 | @@ -131,7 +132,25 @@ class TestDec1(unittest.TestCase):
  42 |          ffmpeg("-sseof", "-3", "-i", OUT["16x9"], "-vf", "eq=brightness=-0.006", "-c:v", "libx264", "-crf", "12",
  43 |                 "-preset", "veryfast", "-c:a", "copy", p)
  44 |          ok, d = quiet(q.gate_g9, p, self.tmp, fmt="16x9")
  45 | -        self.assertFalse(d["luma_ok"] in (True, "True"), d)
  46 | +        self.assertFalse(ok, d)
  47 | +        self.assertEqual(str(d["luma_ok"]), "False", d)          # numpy bool or bool; None/0 fail
  48 | +        self.assertLess(d["mean_luma"], q.G9_LUMA_FLOOR["16x9"], d)
  49 | +
  50 | +
  51 | +class TestTailRows(unittest.TestCase):
  52 | +    """Heimdall DEC-1 audit: G9_tail is the calibrated gate alone; a conform fallback (not the locked
  53 | +    outro the floor was measured on) fails its own row, so the run still holds."""
  54 | +
  55 | +    def test_luma_pass_on_a_fallback_outro_fails_outro_locked(self):
  56 | +        import run_fresh as rf
  57 | +        self.assertEqual(rf.tail_rows(True, True), {"G9_tail": "PASS", "outro_locked": "FAIL"})
  58 | +        self.assertEqual(rf.verdict_for(rf.tail_rows(True, True))[0], rf.VERDICT_HOLD)
  59 | +
  60 | +    def test_rows_follow_their_own_inputs(self):
  61 | +        import run_fresh as rf
  62 | +        self.assertEqual(rf.tail_rows(True, False), {"G9_tail": "PASS", "outro_locked": "PASS"})
  63 | +        self.assertEqual(rf.tail_rows(False, False), {"G9_tail": "FAIL", "outro_locked": "PASS"})
  64 | +        self.assertEqual(rf.verdict_for(rf.tail_rows(True, False))[0], rf.VERDICT_CANDIDATE)
  65 |  
  66 |  
  67 |  if __name__ == "__main__":
  68 | 
```

---

## YOUR REVIEW TASK: PULSE CHECK SENTENCE LAW / ONSET / CREDITS (Python pipeline, no UI, no DB)

The only file is the exact staged diff of ONE commit. Review that diff, nothing else.
Only state what you can verify from the diff shown. If uncertain, say so. Do not guess. Cite diff lines.

### Q1: CORRECTNESS
Does each changed function do what its docstring and the laws above say? Off-by-one in time/index
handling, wrong units (seconds vs ms), wrong comparisons, silent exceptions, state that leaks between
clips. Can any path produce a PASS (or a cut, a lock, a window) when data is missing or a model failed?

### Q2: LAW COMPLIANCE
For each law above: COMPLIANT / VIOLATION / PARTIAL with the diff line. In particular: can a cut move
outside the locked sentence's silence, can expected words be recomputed after selection, can a gate
threshold have been loosened, can the v2f reference path behave differently?

### Q3: TESTS
Do the tests prove the claim (must-fail fixtures FAIL for the right reason; controls PASS for the right
reason)? Any assertion that could pass vacuously?

### Q4: VERDICT
List every defect as: SEVERITY | diff line | issue | fix. End with READY or NOT READY.

