# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pulse-sentence-law
# Branch: combo-letterbox-quoteonly-v2
# Generated: 2026-11-11 04:03 UTC
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

### File: docs/audits/pulse-sentence-law/CURRENT.diff (272 lines)
```
   1 | diff --git a/pipeline/select_passages.py b/pipeline/select_passages.py
   2 | index af1e33c1..baa80856 100644
   3 | --- a/pipeline/select_passages.py
   4 | +++ b/pipeline/select_passages.py
   5 | @@ -282,18 +282,26 @@ def select_and_build_edl(keyword, niche, run_dir):
   6 |      def _key(p):
   7 |          return (p["video_id"], round(p["start"], 2), round(p["end"], 2))
   8 |  
   9 | -    def _eligible(p, kind):
  10 | -        lo, hi, floor = ((HOOK_MIN_S, HOOK_MAX_S, HOOK_MIN_SCORE) if kind == "hook"
  11 | -                         else (CLIP_MIN_S, CLIP_MAX_S, CLIP_MIN_SCORE))
  12 | -        if p.get("kind") != kind or _key(p) in tried or (p.get("clip_score") or 0) < floor:
  13 | -            return False
  14 | -        if not lo <= p["end"] - p["start"] <= hi:
  15 | -            return False
  16 | +    def _budget(kind):
  17 | +        return (HOOK_MIN_S, HOOK_MAX_S) if kind == "hook" else (CLIP_MIN_S, CLIP_MAX_S)
  18 | +
  19 | +    def _conflicts(p, kind):
  20 | +        """Overlap / per-video / per-channel conflicts with windows already used (also applied to the
  21 | +        editor's own candidate: an earlier fallback may have taken its window, 1d audit)."""
  22 | +        if _key(p) in tried:
  23 | +            return True
  24 |          if any(u["video_id"] == p["video_id"] and not (p["end"] <= u["start"] or p["start"] >= u["end"]) for u in used):
  25 | -            return False
  26 | +            return True
  27 |          if sum(1 for u in used if u["video_id"] == p["video_id"]) >= MAX_VERIFIED_QUOTES_PER_VIDEO:
  28 | +            return True
  29 | +        return kind != "hook" and sum(1 for u in used[1:] if u["channel"] == p["channel"]) >= 2
  30 | +
  31 | +    def _eligible(p, kind):
  32 | +        lo, hi = _budget(kind)
  33 | +        floor = HOOK_MIN_SCORE if kind == "hook" else CLIP_MIN_SCORE
  34 | +        if p.get("kind") != kind or (p.get("clip_score") or 0) < floor:
  35 |              return False
  36 | -        return kind == "hook" or sum(1 for u in used[1:] if u["channel"] == p["channel"]) < 2
  37 | +        return lo <= p["end"] - p["start"] <= hi and not _conflicts(p, kind)
  38 |  
  39 |      def _source_for(p):
  40 |          vid = p["video_id"]
  41 | @@ -314,7 +322,7 @@ def select_and_build_edl(keyword, niche, run_dir):
  42 |      def _fill(first, label, kind, slot):
  43 |          for p in [first] + sorted([q for q in pool if q is not first],
  44 |                                    key=lambda q: (-(q.get("clip_score") or 0), -(q.get("relevance") or 0))):
  45 | -            if p is None or (p is not first and not _eligible(p, kind)):
  46 | +            if p is None or (p is first and _conflicts(p, kind)) or (p is not first and not _eligible(p, kind)):
  47 |                  continue
  48 |              tried.add(_key(p))
  49 |              why = _source_for(p)
  50 | @@ -325,6 +333,12 @@ def select_and_build_edl(keyword, niche, run_dir):
  51 |                  continue
  52 |              seg = _build_segment(p, label)
  53 |              boundary_report[-1].update(fallback=p is not first, slot=slot)
  54 | +            lo, hi = _budget(kind)
  55 | +            if seg is not None and not lo <= seg["duration"] <= hi:
  56 | +                # the budget holds for the clip actually cut (this file's words), not the declared window
  57 | +                boundary_report[-1]["result"] = (f"rejected: locked words span {seg['duration']} s, outside the "
  58 | +                                                 f"{kind} budget {lo}-{hi} s")
  59 | +                seg = None
  60 |              if seg is not None:
  61 |                  used.append(p)
  62 |                  return seg
  63 | diff --git a/pipeline/test_fresh.py b/pipeline/test_fresh.py
  64 | index a3f019c5..d3d7cd2f 100644
  65 | --- a/pipeline/test_fresh.py
  66 | +++ b/pipeline/test_fresh.py
  67 | @@ -45,8 +45,9 @@ def _synth_window(path, words, dur=45.0, sr=16000):
  68 |          f.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
  69 |  
  70 |  
  71 | -def _sentences(tag, t, n_sent=8, per=6):
  72 | -    """Sentence-structured word timestamps: 0.30 s words, 0.05 s word gaps, 0.50 s sentence gaps."""
  73 | +def _sentences(tag, t, n_sent=8, per=12):
  74 | +    """Sentence-structured word timestamps: 0.30 s words, 0.05 s word gaps, 0.50 s sentence gaps.
  75 | +    12 words a sentence, so 2 sentences = 8.8 s (hook budget 8-12) and 3 = 13.45 s (clip budget 12-20)."""
  76 |      ws = []
  77 |      for si in range(n_sent):
  78 |          for wi in range(per):
  79 | @@ -61,23 +62,24 @@ class TestSelectCoords(unittest.TestCase):
  80 |      def test_edl_times_are_source_file_coords(self):
  81 |          import select_passages as sp
  82 |          words = {"AAA": _sentences("a", 2.0), "BBB": _sentences("b", 2.0)}
  83 | +        win_off = {"AAA": 95.0, "BBB": 495.0}   # where each downloaded window starts in the full video
  84 |  
  85 | -        def text(vid, s0, s1):  # sentences s0..s1 as the editor selected them
  86 | -            return " ".join(w["word"] for w in words[vid] if s0 <= int(w["word"][1:].split("s")[1].split("w")[0]) <= s1)
  87 | +        def window(vid, channel, s0, s1, score):  # sentences s0..s1, declared where their text is
  88 | +            ws = [w for w in words[vid] if s0 <= int(w["word"][1:].split("s")[1].split("w")[0]) <= s1]
  89 | +            st, en = round(ws[0]["start"] + win_off[vid], 2), round(ws[-1]["end"] + win_off[vid], 2)
  90 | +            return {"video_id": vid, "channel": channel, "start": st, "end": en, "duration": round(en - st, 2),
  91 | +                    "score": score, "text": " ".join(w["word"] for w in ws)}
  92 |          with tempfile.TemporaryDirectory() as rd:
  93 |              os.makedirs(os.path.join(rd, "sources"))
  94 |              os.makedirs(os.path.join(rd, "transcripts"))
  95 | -            passages = {"chosen": [
  96 | -                {"video_id": "AAA", "channel": "The Bitcoin Layer", "start": 110.0, "end": 121.0,
  97 | -                 "duration": 11.0, "score": 9, "text": text("AAA", 5, 6)},
  98 | -                {"video_id": "BBB", "channel": "BTC Sessions", "start": 510.0, "end": 524.0,
  99 | -                 "duration": 14.0, "score": 5, "text": text("BBB", 5, 7)}]}
 100 | +            passages = {"chosen": [window("AAA", "The Bitcoin Layer", 5, 6, 9),
 101 | +                                   window("BBB", "BTC Sessions", 5, 7, 5)]}
 102 |              json.dump(passages, open(os.path.join(rd, "passages.json"), "w"))
 103 |  
 104 |              def fake_dl(vid, start, end, run_dir, pad=15.0):
 105 |                  path = os.path.join(run_dir, "sources", f"{vid}.wav")
 106 |                  _synth_window(path, words[vid])
 107 | -                return (path, start - pad)
 108 | +                return (path, win_off[vid])
 109 |  
 110 |              def fake_tx(path, vid, run_dir):
 111 |                  rec = {"words": words[vid]}
 112 | @@ -95,13 +97,13 @@ class TestSelectCoords(unittest.TestCase):
 113 |                  self.assertEqual(seg["time_coords"], "source_file")
 114 |                  off = seg["source_window_offset_s"]
 115 |                  self.assertIn(off, (95.0, 495.0))
 116 | -                # source-file coords: well inside the ~40 s downloaded window, never full-video
 117 | +                # source-file coords: inside the ~45 s downloaded window, never full-video
 118 |                  self.assertLess(seg["word_start"], 60.0, seg)
 119 |                  self.assertLess(seg["word_end"], 60.0, seg)
 120 |                  # the editor's sentences, sealed at selection (sentence law)
 121 |                  lock = seg["selection_lock"]
 122 |                  self.assertEqual((lock["first_word"], lock["last_word"]), (seg["first_word"], seg["last_word"]))
 123 | -                self.assertTrue(lock["first_word"].endswith("s5w0") and lock["last_word"].endswith("w5."), lock)
 124 | +                self.assertTrue(lock["first_word"].endswith("s5w0") and lock["last_word"].endswith("w11."), lock)
 125 |  
 126 |  
 127 |  # ── intro-optional renderer support (shared helper) ──
 128 | diff --git a/pipeline/test_sentence_windows.py b/pipeline/test_sentence_windows.py
 129 | index bf913061..93058185 100644
 130 | --- a/pipeline/test_sentence_windows.py
 131 | +++ b/pipeline/test_sentence_windows.py
 132 | @@ -72,12 +72,12 @@ def _synth(path, words, dur=45.0, sr=16000):
 133 |          f.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
 134 |  
 135 |  
 136 | -def _sentences(tag, t, gaps):
 137 | -    """Sentences of 6 words (0.30 s words, 0.05 s word gaps); gaps[i] = silence after sentence i."""
 138 | +def _sentences(tag, t, gaps, per=12):
 139 | +    """Sentences of `per` words (0.30 s words, 0.05 s word gaps); gaps[i] = silence after sentence i."""
 140 |      ws = []
 141 |      for si, gap in enumerate(gaps):
 142 | -        for wi in range(6):
 143 | -            ws.append({"word": f"{tag}s{si}w{wi}" + ("." if wi == 5 else ""), "start": round(t, 2),
 144 | +        for wi in range(per):
 145 | +            ws.append({"word": f"{tag}s{si}w{wi}" + ("." if wi == per - 1 else ""), "start": round(t, 2),
 146 |                         "end": round(t + 0.30, 2)})
 147 |              t += 0.35
 148 |          t += gap - 0.05
 149 | @@ -85,49 +85,80 @@ def _sentences(tag, t, gaps):
 150 |  
 151 |  
 152 |  class TestNextRankedFallback(unittest.TestCase):
 153 | -    def test_rejected_clip_is_replaced_by_the_next_legal_window(self):
 154 | +    """Windows are declared exactly where their text is (12-word sentences: 2 = 8.8 s hook, 3 = 13.45 s
 155 | +    clip). BBB sentence 4 runs straight into sentence 5 (no pause): no window may end or start there."""
 156 | +    OFF = {"AAA": 95.0, "BBB": 495.0}
 157 | +
 158 | +    def setUp(self):
 159 | +        self.words = {"AAA": _sentences("a", 2.0, [0.5] * 8),
 160 | +                      "BBB": _sentences("b", 2.0, [0.5, 0.5, 0.5, 0.5, 0.05, 0.5, 0.5, 0.5, 0.5, 0.5])}
 161 | +
 162 | +    def window(self, vid, s0, s1, kind, score):
 163 | +        ws = [w for w in self.words[vid] if s0 <= int(w["word"][1:].split("s")[1].split("w")[0]) <= s1]
 164 | +        st, en = ws[0]["start"] + self.OFF[vid], ws[-1]["end"] + self.OFF[vid]
 165 | +        return {"kind": kind, "video_id": vid, "channel": {"AAA": "The Bitcoin Layer", "BBB": "BTC Sessions"}[vid],
 166 | +                "start": round(st, 2), "end": round(en, 2), "duration": round(en - st, 2), "score": score * 20,
 167 | +                "clip_score": score, "text": " ".join(w["word"] for w in ws)}
 168 | +
 169 | +    def run_select(self, chosen, pool):
 170 |          import select_passages as sp
 171 | -        # BBB sentence 6 runs straight into sentence 7 (no pause): a clip ending there is not cuttable
 172 | -        words = {"AAA": _sentences("a", 2.0, [0.5] * 8), "BBB": _sentences("b", 2.0, [0.5] * 6 + [0.05, 0.5])}
 173 | -
 174 | -        def text(vid, s0, s1):
 175 | -            return " ".join(w["word"] for w in words[vid]
 176 | -                            if s0 <= int(w["word"][1:].split("s")[1].split("w")[0]) <= s1)
 177 | -
 178 | -        with tempfile.TemporaryDirectory() as rd:
 179 | -            os.makedirs(os.path.join(rd, "sources"))
 180 | -            os.makedirs(os.path.join(rd, "transcripts"))
 181 | -            hook = {"kind": "hook", "video_id": "AAA", "channel": "The Bitcoin Layer", "start": 110.0, "end": 119.0,
 182 | -                    "duration": 9.0, "score": 90, "clip_score": 4.5, "text": text("AAA", 5, 6)}
 183 | -            bad = {"kind": "clip", "video_id": "BBB", "channel": "BTC Sessions", "start": 510.0, "end": 524.0,
 184 | -                   "duration": 14.0, "score": 80, "clip_score": 4.0, "text": text("BBB", 4, 6)}
 185 | -            alt = {"kind": "clip", "video_id": "BBB", "channel": "BTC Sessions", "start": 497.5, "end": 510.0,
 186 | -                   "duration": 12.5, "score": 70, "clip_score": 3.8, "text": text("BBB", 0, 2)}
 187 | -            json.dump({"chosen": [hook, bad], "passages": [hook, bad, alt]},
 188 | -                      open(os.path.join(rd, "passages.json"), "w"))
 189 | -
 190 | -            def fake_dl(vid, start, end, run_dir, pad=15.0):
 191 | -                path = os.path.join(run_dir, "sources", f"{vid}.wav")
 192 | -                _synth(path, words[vid])
 193 | -                return (path, 95.0 if vid == "AAA" else 495.0)
 194 | -
 195 | -            def fake_tx(path, vid, run_dir):
 196 | -                rec = {"words": words[vid]}
 197 | -                json.dump(rec, open(os.path.join(run_dir, "transcripts", f"{vid}.json"), "w"))
 198 | -                return rec
 199 | -            orig = (sp._download_window, sp._whisper_transcribe)
 200 | -            sp._download_window, sp._whisper_transcribe = fake_dl, fake_tx
 201 | -            try:
 202 | -                self.assertTrue(sp.select_and_build_edl("test", "bitcoin", rd))
 203 | -            finally:
 204 | -                sp._download_window, sp._whisper_transcribe = orig
 205 | -            edl = json.load(open(os.path.join(rd, "edl.json")))
 206 | -            report = json.load(open(os.path.join(rd, "SELECT_BOUNDARIES.json")))
 207 | -            clip = edl["clips"][0]
 208 | -            self.assertEqual((clip["first_word"], clip["last_word"]), ("bs0w0", "bs2w5."), clip)
 209 | -            rejected = [r for r in report if r["result"].startswith("rejected")]
 210 | -            self.assertTrue(rejected and "OUT" in rejected[0]["result"], report)
 211 | -            self.assertTrue(any(r.get("fallback") and r["result"] == "accepted" for r in report), report)
 212 | +        rd = tempfile.mkdtemp(prefix="fb_")
 213 | +        os.makedirs(os.path.join(rd, "sources"))
 214 | +        os.makedirs(os.path.join(rd, "transcripts"))
 215 | +        json.dump({"chosen": chosen, "passages": pool}, open(os.path.join(rd, "passages.json"), "w"))
 216 | +
 217 | +        def fake_dl(vid, start, end, run_dir, pad=15.0):
 218 | +            path = os.path.join(run_dir, "sources", f"{vid}.wav")
 219 | +            _synth(path, self.words[vid], dur=self.words[vid][-1]["end"] + 5.0)
 220 | +            return (path, self.OFF[vid])
 221 | +
 222 | +        def fake_tx(path, vid, run_dir):
 223 | +            rec = {"words": self.words[vid]}
 224 | +            json.dump(rec, open(os.path.join(run_dir, "transcripts", f"{vid}.json"), "w"))
 225 | +            return rec
 226 | +        orig = (sp._download_window, sp._whisper_transcribe)
 227 | +        sp._download_window, sp._whisper_transcribe = fake_dl, fake_tx
 228 | +        try:
 229 | +            ok = sp.select_and_build_edl("test", "bitcoin", rd)
 230 | +        finally:
 231 | +            sp._download_window, sp._whisper_transcribe = orig
 232 | +        edl = json.load(open(os.path.join(rd, "edl.json"))) if ok else None
 233 | +        return ok, edl, json.load(open(os.path.join(rd, "SELECT_BOUNDARIES.json")))
 234 | +
 235 | +    def test_rejected_clip_is_replaced_by_the_next_legal_window(self):
 236 | +        hook, bad, short, alt = (self.window("AAA", 5, 6, "hook", 4.5), self.window("BBB", 2, 4, "clip", 4.0),
 237 | +                                 self.window("BBB", 0, 1, "clip", 3.9), self.window("BBB", 6, 8, "clip", 3.8))
 238 | +        ok, edl, report = self.run_select([hook, bad], [hook, bad, short, alt])
 239 | +        self.assertTrue(ok, report)
 240 | +        self.assertEqual((edl["hook"]["first_word"], edl["hook"]["last_word"]), ("as5w0", "as6w11."))
 241 | +        clip = edl["clips"][0]
 242 | +        self.assertEqual((clip["first_word"], clip["last_word"]), ("bs6w0", "bs8w11."), report)
 243 | +        rej = next(r for r in report if r.get("video_id") == "BBB" and r["result"].startswith("rejected"))
 244 | +        self.assertIn("OUT", rej["result"], report)          # rejected for its missing pause, nothing else
 245 | +        self.assertTrue(any(r.get("fallback") and r["result"] == "accepted" for r in report), report)
 246 | +        # the higher-ranked 8.8 s window is below the 12 s clip budget: never tried
 247 | +        self.assertFalse(any(r["window_full_video_s"][0] == short["start"] for r in report), report)
 248 | +
 249 | +    def test_a_window_taken_by_a_fallback_is_never_used_twice(self):
 250 | +        # slot 1 (bad) falls back to 'alt'; slot 2 is the editor's own choice of that same window -> skipped
 251 | +        hook, bad, alt = (self.window("AAA", 5, 6, "hook", 4.5), self.window("BBB", 2, 4, "clip", 4.0),
 252 | +                          self.window("BBB", 6, 8, "clip", 3.8))
 253 | +        ok, edl, report = self.run_select([hook, bad, alt], [hook, bad, alt])
 254 | +        self.assertTrue(ok, report)
 255 | +        keys = [(c["video_id"], c["word_start"]) for c in edl["clips"]]
 256 | +        self.assertEqual(keys, [("BBB", self.words["BBB"][6 * 12]["start"])], report)
 257 | +
 258 | +    def test_budget_holds_for_the_locked_words_not_the_declared_window(self):
 259 | +        # declared as 13.5 s, but its text is two sentences (8.8 s): the cut clip would be under budget
 260 | +        hook, liar, alt = (self.window("AAA", 5, 6, "hook", 4.5), self.window("BBB", 6, 7, "clip", 4.0),
 261 | +                           self.window("BBB", 6, 8, "clip", 3.8))
 262 | +        liar["end"] = round(liar["start"] + 13.5, 2)
 263 | +        liar["duration"] = 13.5
 264 | +        ok, edl, report = self.run_select([hook, liar], [hook, liar, alt])
 265 | +        self.assertTrue(ok, report)
 266 | +        rej = next(r for r in report if r.get("slot") == 1 and r["result"].startswith("rejected"))
 267 | +        self.assertIn("locked words span 8.8 s, outside the clip budget", rej["result"], report)
 268 | +        self.assertEqual(edl["clips"][0]["last_word"], "bs8w11.", report)
 269 |  
 270 |  
 271 |  if __name__ == "__main__":
 272 | 
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

