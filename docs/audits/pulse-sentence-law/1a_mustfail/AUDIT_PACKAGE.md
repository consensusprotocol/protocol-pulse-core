# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pulse-sentence-law
# Branch: combo-letterbox-quoteonly-v2
# Generated: 2026-11-11 02:29 UTC
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
 265 | +    "pulse-sentence-law": """## YOUR REVIEW TASK: PULSE CHECK SENTENCE LAW / ONSET / CREDITS (Python pipeline, no UI, no DB)
 266 | +
 267 | +The only file is the exact staged diff of ONE commit. Review that diff, nothing else.
 268 | +Only state what you can verify from the diff shown. If uncertain, say so. Do not guess. Cite diff lines.
 269 | +
 270 | +### Q1: CORRECTNESS
 271 | +Does each changed function do what its docstring and the laws above say? Off-by-one in time/index
 272 | +handling, wrong units (seconds vs ms), wrong comparisons, silent exceptions, state that leaks between
 273 | +clips. Can any path produce a PASS (or a cut, a lock, a window) when data is missing or a model failed?
 274 | +
 275 | +### Q2: LAW COMPLIANCE
 276 | +For each law above: COMPLIANT / VIOLATION / PARTIAL with the diff line. In particular: can a cut move
 277 | +outside the locked sentence's silence, can expected words be recomputed after selection, can a gate
 278 | +threshold have been loosened, can the v2f reference path behave differently?
 279 | +
 280 | +### Q3: TESTS
 281 | +Do the tests prove the claim (must-fail fixtures FAIL for the right reason; controls PASS for the right
 282 | +reason)? Any assertion that could pass vacuously?
 283 | +
 284 | +### Q4: VERDICT
 285 | +List every defect as: SEVERITY | diff line | issue | fix. End with READY or NOT READY.
 286 | +""",
 287 |      "track-a-d1-d3": """## YOUR REVIEW TASK: EDITORIAL DECISIONS D1-D3 (Python pipeline code, no UI, no DB)
 288 |  
 289 |  The first file is the exact diff under review; the full modules and tests follow for context.
 290 | 
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

