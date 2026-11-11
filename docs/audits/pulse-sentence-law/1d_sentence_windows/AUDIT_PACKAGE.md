# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pulse-sentence-law
# Branch: combo-letterbox-quoteonly-v2
# Generated: 2026-11-11 03:20 UTC
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

### File: docs/audits/pulse-sentence-law/CURRENT.diff (451 lines)
```
   1 | diff --git a/pipeline/editorial_select.py b/pipeline/editorial_select.py
   2 | index 0be1f722..e791acf5 100644
   3 | --- a/pipeline/editorial_select.py
   4 | +++ b/pipeline/editorial_select.py
   5 | @@ -46,7 +46,8 @@ MAX_ADJUDICATE_PER_STORY = 14
   6 |  MIN_COVERAGE_CHANNELS = 2
   7 |  MIN_LAYOUT_CHANNELS = 2            # R5: clips from >= 2 distinct channels
   8 |  HOOK_MIN_S, HOOK_MAX_S = 8.0, 12.0
   9 | -CLIP_MIN_S, CLIP_MAX_S = 13.0, 25.0
  10 | +CLIP_MIN_S, CLIP_MAX_S = 12.0, 20.0     # 1d (2026-11-11): whole sentences within the 12-20 s clip budget
  11 | +MAX_WINDOW_SENTENCES = 3                 # 1d: a window is one to three whole sentences
  12 |  HOOK_MIN_SCORE, CLIP_MIN_SCORE = 4.0, 3.5
  13 |  N_CLIPS = 3                        # v2f format: hook + 3 clips
  14 |  MAX_VERIFIED_QUOTES_PER_VIDEO = 2  # D2 (PBX 2026-11-09): up to two verified windows per source video
  15 | @@ -123,12 +124,27 @@ def _tok(w):
  16 |      return [t for t in re.split(r"[^a-z0-9]+", (w or "").lower().replace("’", "'").replace("'", "")) if t]
  17 |  
  18 |  
  19 | +def _ends_statement(word):
  20 | +    """A window may end only on a statement end: '.' or '!' that is not an abbreviation (U.S.)."""
  21 | +    import sentence_law
  22 | +    return sentence_law.is_terminal(word) and not word.rstrip().rstrip("\"')]”’").endswith("?")
  23 | +
  24 | +
  25 | +def _n_sentences(words, sents, a, b):
  26 | +    """Sentences a..b counted toward MAX_WINDOW_SENTENCES; an interjection-only sentence ('Oh.',
  27 | +    'Yeah.') is transparent, as in PBX's D4a ruling (2026-11-09) for the per-direction cap."""
  28 | +    return sum(1 for i in range(a, b + 1)
  29 | +               if not (set(_lc_words(" ".join(w["word"] for w in words[sents[i][0]:sents[i][1] + 1])))
  30 | +                       <= INTERJECTIONS))
  31 | +
  32 | +
  33 |  def _word_sentences(words):
  34 | -    """Sentences as word-index ranges, split after terminal punctuation (same rule as
  35 | -    transcript_store.sentences_from_words)."""
  36 | +    """Sentences as word-index ranges, split after terminal punctuation; abbreviations such as
  37 | +    'U.S.' and trailing '...' never end a sentence (sentence_law.is_terminal, the one rule)."""
  38 | +    import sentence_law
  39 |      out, s0 = [], 0
  40 |      for i, w in enumerate(words):
  41 | -        if w["word"].rstrip().endswith(_TERMINAL):
  42 | +        if sentence_law.is_terminal(w["word"]):
  43 |              out.append((s0, i))
  44 |              s0 = i + 1
  45 |      if s0 < len(words):
  46 | @@ -167,7 +183,8 @@ def start_is_boundary(words, sents, si):
  47 |      """A window start is a boundary only if the previous sentence ended with terminal punctuation,
  48 |      the first word opens a sentence (capital or digit) and is not a continuation conjunction."""
  49 |      w0 = sents[si][0]
  50 | -    if si > 0 and not words[w0 - 1]["word"].rstrip().endswith(_TERMINAL):
  51 | +    import sentence_law
  52 | +    if si > 0 and not sentence_law.is_terminal(words[w0 - 1]["word"]):
  53 |          return False, "previous word has no terminal punctuation"
  54 |      first = re.sub(r"^[\"'(\[“‘$]+", "", words[w0]["word"].strip())
  55 |      if not first or not (first[0].isupper() or first[0].isdigit()):
  56 | @@ -194,11 +211,13 @@ def anchored_window(words, sents, anchor, lo, hi):
  57 |      ok, why = start_is_boundary(words, sents, sa)
  58 |      if not ok:
  59 |          return None, f"start rejected: {why}", span
  60 | +    if _n_sentences(words, sents, sa, se) > MAX_WINDOW_SENTENCES:
  61 | +        return None, f"quote spans {_n_sentences(words, sents, sa, se)} sentences > {MAX_WINDOW_SENTENCES}", span
  62 |      if d < lo:
  63 |          return None, f"quote sentence(s) {d} s < minimum {lo} s (no padding)", span
  64 |      if d > hi:
  65 |          return None, f"quote sentence(s) {d} s > maximum {hi} s", span
  66 | -    if not words[sents[se][1]]["word"].rstrip().endswith((".", "!")):
  67 | +    if not _ends_statement(words[sents[se][1]]["word"]):
  68 |          return None, "does not end on '.' or '!'", span
  69 |      text = " ".join(w["word"].strip() for w in words[sents[sa][0]:sents[se][1] + 1])
  70 |      return {**span, "text": text, "anchor_start": anchor["start"], "anchor_end": anchor["end"]}, None, span
  71 | @@ -244,6 +263,11 @@ def expanded_window(words, sents, anchor, lo, hi, on_event):
  72 |                  checks.append({"direction": d, "sentence": stext(i), "on_event": None,
  73 |                                 "detail": f"would exceed {hi} s; direction closed"})
  74 |                  continue
  75 | +            if _n_sentences(words, sents, na, nb) > MAX_WINDOW_SENTENCES:
  76 | +                open_dirs.remove(d)
  77 | +                checks.append({"direction": d, "sentence": stext(i), "on_event": None,
  78 | +                               "detail": f"would exceed {MAX_WINDOW_SENTENCES} sentences; direction closed"})
  79 | +                continue
  80 |              # D4a (PBX 2026-11-09 ~02:05): content-free interjections are transparent — included in
  81 |              # the window but skipped for the (a) check, not counted toward the two-sentence cap, and
  82 |              # they do not close the direction.  The 8 s bound (b) still applies to them.
  83 | @@ -282,6 +306,8 @@ def expanded_window(words, sents, anchor, lo, hi, on_event):
  84 |              "expansion": checks}
  85 |      if d > hi:
  86 |          return None, f"quote sentence(s) {d} s > maximum {hi} s", span
  87 | +    if _n_sentences(words, sents, a, b) > MAX_WINDOW_SENTENCES:
  88 | +        return None, f"window spans {_n_sentences(words, sents, a, b)} sentences > {MAX_WINDOW_SENTENCES}", span
  89 |      if d < lo:
  90 |          return None, (f"{d} s < minimum {lo} s after verified expansion"
  91 |                        + (f"; expansion stopped: {'; '.join(stops)}" if stops
  92 | @@ -289,7 +315,7 @@ def expanded_window(words, sents, anchor, lo, hi, on_event):
  93 |      ok, why = start_is_boundary(words, sents, a)
  94 |      if not ok:
  95 |          return None, f"start rejected: {why}", span
  96 | -    if not words[sents[b][1]]["word"].rstrip().endswith((".", "!")):
  97 | +    if not _ends_statement(words[sents[b][1]]["word"]):
  98 |          return None, "does not end on '.' or '!'", span
  99 |      text = " ".join(w["word"].strip() for w in words[sents[a][0]:sents[b][1] + 1])
 100 |      return {**span, "text": text, "anchor_start": anchor["start"], "anchor_end": anchor["end"]}, None, span
 101 | @@ -454,7 +480,7 @@ def repair_window(words, sents, win, fault, lo, hi, on_event):
 102 |  
 103 |      def edge_ok(a, b):
 104 |          return start_is_boundary(words, sents, a)[0] if d == "prev" else \
 105 | -            words[sents[b][1]]["word"].rstrip().endswith((".", "!"))
 106 | +            _ends_statement(words[sents[b][1]]["word"])
 107 |  
 108 |      added = 0
 109 |      while added == 0 or not edge_ok(a, b):
 110 | @@ -462,6 +488,8 @@ def repair_window(words, sents, win, fault, lo, hi, on_event):
 111 |          if i < 0 or i >= len(sents):
 112 |              return None, f"boundary repair: no {d} sentence", span
 113 |          na, nb = (i, b) if d == "prev" else (a, i)
 114 | +        if _n_sentences(words, sents, na, nb) > MAX_WINDOW_SENTENCES:
 115 | +            return None, f"boundary repair: would exceed {MAX_WINDOW_SENTENCES} sentences", span
 116 |          if words[sents[nb][1]]["end"] - words[sents[na][0]]["start"] > hi:
 117 |              span["expansion"].append({"direction": d, "sentence": stext(i), "on_event": None,
 118 |                                        "detail": f"would exceed {hi} s; direction closed"})
 119 | @@ -496,7 +524,7 @@ def repair_window(words, sents, win, fault, lo, hi, on_event):
 120 |      ok, why = start_is_boundary(words, sents, a)
 121 |      if not ok:
 122 |          return None, f"repaired start rejected: {why}", span
 123 | -    if not words[sents[b][1]]["word"].rstrip().endswith((".", "!")):
 124 | +    if not _ends_statement(words[sents[b][1]]["word"]):
 125 |          return None, "repaired window does not end on '.' or '!'", span
 126 |      return {"start": st, "end": en, "duration": dd, "first_sentence": stext(a), "last_sentence": stext(b),
 127 |              "n_sentences": b - a + 1, "text": " ".join(w["word"].strip() for w in words[sents[a][0]:sents[b][1] + 1]),
 128 | @@ -1030,7 +1058,7 @@ def _clip_quality(c, same, E, L, by_cid, words, log, today=""):
 129 |                            (f"; infrastructure-blocked videos {[v for v, _ in infra]}" if infra else "")}
 130 |      out = []
 131 |      for p in chosen:   # select_passages input contract (full-video seconds)
 132 | -        out.append({"video_id": p["video_id"], "channel": p["channel"], "handle": p["handle"],
 133 | +        out.append({"kind": p["kind"], "video_id": p["video_id"], "channel": p["channel"], "handle": p["handle"],
 134 |                      "title": p["title"], "tier": p["tier"], "start": round(p["start"], 2),
 135 |                      "end": round(p["end"], 2), "text": p["text"], "duration": p["duration"],
 136 |                      "score": round(p["clip_score"] * 20 + p["relevance"], 2),
 137 | diff --git a/pipeline/select_passages.py b/pipeline/select_passages.py
 138 | index 752a8032..91bdf81f 100644
 139 | --- a/pipeline/select_passages.py
 140 | +++ b/pipeline/select_passages.py
 141 | @@ -205,14 +205,18 @@ def select_and_build_edl(keyword, niche, run_dir):
 142 |          print("  Not enough valid passages — STOP")
 143 |          return False
 144 |  
 145 | -    # Pick hook: shortest passage with highest score, must be a statement
 146 | -    hook_candidates = [p for p in valid if p["duration"] <= 12.0 and
 147 | -                       not p["text"].rstrip().endswith("?")]
 148 | -    if not hook_candidates:
 149 | -        hook_candidates = sorted(valid, key=lambda p: p["duration"])[:1]
 150 | -
 151 | -    hook = max(hook_candidates, key=lambda p: p["score"]) if hook_candidates else valid[0]
 152 | -    clips = [p for p in valid if p is not hook][:5]  # Max 5 clips
 153 | +    if all(p.get("kind") in ("hook", "clip") for p in valid):
 154 | +        # 1d (2026-11-11): the editor's slots are kept; a rejected slot is refilled from the ranking
 155 | +        hook = next((p for p in valid if p["kind"] == "hook"), None)
 156 | +        clips = [p for p in valid if p["kind"] == "clip"]
 157 | +    else:
 158 | +        # legacy passages.json without slot kinds: shortest statement with the highest score
 159 | +        hook_candidates = [p for p in valid if p["duration"] <= 12.0 and
 160 | +                           not p["text"].rstrip().endswith("?")]
 161 | +        if not hook_candidates:
 162 | +            hook_candidates = sorted(valid, key=lambda p: p["duration"])[:1]
 163 | +        hook = max(hook_candidates, key=lambda p: p["score"]) if hook_candidates else valid[0]
 164 | +        clips = [p for p in valid if p is not hook][:5]  # Max 5 clips
 165 |  
 166 |      # SENTENCE LAW (sentence_law.py): the editor's chosen sentences are located in the downloaded
 167 |      # file's own transcript by TEXT, sealed in a selection lock, and both edges must be legal,
 168 | @@ -267,12 +271,71 @@ def select_and_build_edl(keyword, niche, run_dir):
 169 |              "selection_lock": lock,
 170 |          }
 171 |  
 172 | +    # Next-ranked fallback (mission 1b/1d): a window the sentence law rejects is replaced by the
 173 | +    # best-ranked legal candidate of the same kind from the editor's shortlist (score floor, duration
 174 | +    # budget, no overlap, <= 2 clips per channel, <= 2 windows per video), never by moving a cut.
 175 | +    from editorial_select import (HOOK_MIN_S, HOOK_MAX_S, CLIP_MIN_S, CLIP_MAX_S, HOOK_MIN_SCORE,
 176 | +                                  CLIP_MIN_SCORE, MAX_VERIFIED_QUOTES_PER_VIDEO)
 177 | +    pool = [p for p in data.get("passages", []) if p.get("kind") in ("hook", "clip")]
 178 | +    used, tried = [], set()
 179 | +
 180 | +    def _key(p):
 181 | +        return (p["video_id"], round(p["start"], 2), round(p["end"], 2))
 182 | +
 183 | +    def _eligible(p, kind):
 184 | +        lo, hi, floor = ((HOOK_MIN_S, HOOK_MAX_S, HOOK_MIN_SCORE) if kind == "hook"
 185 | +                         else (CLIP_MIN_S, CLIP_MAX_S, CLIP_MIN_SCORE))
 186 | +        if p.get("kind") != kind or _key(p) in tried or (p.get("clip_score") or 0) < floor:
 187 | +            return False
 188 | +        if not lo <= p["end"] - p["start"] <= hi:
 189 | +            return False
 190 | +        if any(u["video_id"] == p["video_id"] and not (p["end"] <= u["start"] or p["start"] >= u["end"]) for u in used):
 191 | +            return False
 192 | +        if sum(1 for u in used if u["video_id"] == p["video_id"]) >= MAX_VERIFIED_QUOTES_PER_VIDEO:
 193 | +            return False
 194 | +        return kind == "hook" or sum(1 for u in used[1:] if u["channel"] == p["channel"]) < 2
 195 | +
 196 | +    def _source_for(p):
 197 | +        vid = p["video_id"]
 198 | +        if vid not in sources:
 199 | +            res = _download_window(vid, p["start"], p["end"], run_dir)
 200 | +            if not res or not res[0]:
 201 | +                return "download failed"
 202 | +            sources[vid], offsets[vid] = res
 203 | +            tr = _whisper_transcribe(sources[vid], vid, run_dir)
 204 | +            if not tr:
 205 | +                return "transcription failed"
 206 | +            transcripts[vid] = tr
 207 | +        span = transcripts[vid].get("duration") or 0
 208 | +        if span and not (offsets[vid] + 1.0 <= p["start"] and p["end"] <= offsets[vid] + span - 1.0):
 209 | +            return "outside the downloaded window"
 210 | +        return None
 211 | +
 212 | +    def _fill(first, label, kind):
 213 | +        for p in [first] + sorted([q for q in pool if q is not first],
 214 | +                                  key=lambda q: (-(q.get("clip_score") or 0), -(q.get("relevance") or 0))):
 215 | +            if p is None or (p is not first and not _eligible(p, kind)):
 216 | +                continue
 217 | +            tried.add(_key(p))
 218 | +            why = _source_for(p)
 219 | +            if why:
 220 | +                boundary_report.append({"segment": label, "video_id": p["video_id"], "channel": p["channel"],
 221 | +                                        "window_full_video_s": [p["start"], p["end"]],
 222 | +                                        "result": f"rejected: {why}", "fallback": p is not first})
 223 | +                continue
 224 | +            seg = _build_segment(p, label)
 225 | +            boundary_report[-1]["fallback"] = p is not first
 226 | +            if seg is not None:
 227 | +                used.append(p)
 228 | +                return seg
 229 | +        return None
 230 | +
 231 |      try:
 232 | -        hook_seg = _build_segment(hook, "hook")
 233 | +        hook_seg = _fill(hook, "hook", "hook")
 234 |          clip_segs = []
 235 |          if hook_seg is not None:
 236 | -            for i, clip in enumerate(clips):
 237 | -                seg = _build_segment(clip, f"clip_{i+1:02d}")
 238 | +            for clip in clips:
 239 | +                seg = _fill(clip, f"clip_{len(clip_segs) + 1:02d}", "clip")
 240 |                  if seg:
 241 |                      seg["index"] = len(clip_segs) + 1
 242 |                      clip_segs.append(seg)
 243 | diff --git a/pipeline/test_sentence_windows.py b/pipeline/test_sentence_windows.py
 244 | new file mode 100644
 245 | index 00000000..bf913061
 246 | --- /dev/null
 247 | +++ b/pipeline/test_sentence_windows.py
 248 | @@ -0,0 +1,134 @@
 249 | +#!/usr/bin/env python3
 250 | +"""1d (PBX review 2026-11-11): selection proposes SENTENCE-ALIGNED windows of one to three whole
 251 | +sentences within the 8-12 s hook / 12-20 s clip budgets, and a window the sentence law rejects is
 252 | +replaced by the next-ranked legal window, never by moving a cut.
 253 | +Run: cd ~/protocol_pulse && python3 -m pytest -q pipeline/test_sentence_windows.py"""
 254 | +import json
 255 | +import os
 256 | +import sys
 257 | +import tempfile
 258 | +import unittest
 259 | +
 260 | +PIPELINE = os.path.dirname(os.path.abspath(__file__))
 261 | +sys.path.insert(0, PIPELINE)
 262 | +
 263 | +import editorial_select as es  # noqa: E402
 264 | +
 265 | +
 266 | +def _w(word, t, d=0.3):
 267 | +    return {"word": word, "start": round(t, 2), "end": round(t + d, 2)}
 268 | +
 269 | +
 270 | +class TestSentenceSplitting(unittest.TestCase):
 271 | +    def test_abbreviation_is_not_a_sentence_end(self):
 272 | +        # whisper writes "U .S." as two tokens; the Nov 10 Natalie window was counted as 4 sentences
 273 | +        ws = [_w(x, i * 0.4) for i, x in enumerate(
 274 | +            ["By", "the", "weekend.", "U", ".S.", "Bitcoin", "ETFs", "had", "outflows.", "And", "then."])]
 275 | +        self.assertEqual(es._word_sentences(ws), [(0, 2), (3, 8), (9, 10)])
 276 | +
 277 | +    def test_trailing_ellipsis_is_not_a_sentence_end(self):
 278 | +        ws = [_w(x, i * 0.4) for i, x in enumerate(["So", "anyway...", "it", "fell."])]
 279 | +        self.assertEqual(es._word_sentences(ws), [(0, 3)])
 280 | +
 281 | +    def test_question_never_ends_a_window(self):
 282 | +        self.assertFalse(es._ends_statement("really?"))
 283 | +        self.assertTrue(es._ends_statement("week."))
 284 | +        self.assertFalse(es._ends_statement("U.S."))
 285 | +
 286 | +
 287 | +class TestBudgets(unittest.TestCase):
 288 | +    def test_budget_constants(self):
 289 | +        self.assertEqual((es.HOOK_MIN_S, es.HOOK_MAX_S), (8.0, 12.0))
 290 | +        self.assertEqual((es.CLIP_MIN_S, es.CLIP_MAX_S), (12.0, 20.0))
 291 | +        self.assertEqual(es.MAX_WINDOW_SENTENCES, 3)
 292 | +
 293 | +    def test_expansion_stops_at_three_sentences(self):
 294 | +        # five short sentences (2.0 s each); anchor = sentence 2; a 9-12 s window would need 5 sentences
 295 | +        ws, t = [], 0.0
 296 | +        for s in range(5):
 297 | +            for k in range(4):
 298 | +                ws.append(_w(f"S{s}w{k}" if k == 0 else f"s{s}w{k}" + ("." if k == 3 else ""), t))
 299 | +                t += 0.5
 300 | +            t += 0.3
 301 | +        sents = es._word_sentences(ws)
 302 | +        anchor = {"w0": 8, "w1": 11, "start": ws[8]["start"], "end": ws[11]["end"]}
 303 | +        win, why, span = es.expanded_window(ws, sents, anchor, 9.0, 12.0, lambda txt: (True, "ok"))
 304 | +        self.assertIsNone(win)
 305 | +        self.assertLessEqual(span["n_sentences"], 3, span)
 306 | +        self.assertTrue(any("sentences; direction closed" in c["detail"] for c in span["expansion"]), span)
 307 | +
 308 | +
 309 | +def _synth(path, words, dur=45.0, sr=16000):
 310 | +    import numpy as np
 311 | +    import wave
 312 | +    x = np.random.default_rng(3).normal(0, 0.0005, int(dur * sr))
 313 | +    for w in words:
 314 | +        a, b = int(w["start"] * sr), int(w["end"] * sr)
 315 | +        x[a:b] += 0.1 * np.sin(2 * np.pi * 300 * np.arange(b - a) / sr)
 316 | +    with wave.open(path, "wb") as f:
 317 | +        f.setnchannels(1)
 318 | +        f.setsampwidth(2)
 319 | +        f.setframerate(sr)
 320 | +        f.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
 321 | +
 322 | +
 323 | +def _sentences(tag, t, gaps):
 324 | +    """Sentences of 6 words (0.30 s words, 0.05 s word gaps); gaps[i] = silence after sentence i."""
 325 | +    ws = []
 326 | +    for si, gap in enumerate(gaps):
 327 | +        for wi in range(6):
 328 | +            ws.append({"word": f"{tag}s{si}w{wi}" + ("." if wi == 5 else ""), "start": round(t, 2),
 329 | +                       "end": round(t + 0.30, 2)})
 330 | +            t += 0.35
 331 | +        t += gap - 0.05
 332 | +    return ws
 333 | +
 334 | +
 335 | +class TestNextRankedFallback(unittest.TestCase):
 336 | +    def test_rejected_clip_is_replaced_by_the_next_legal_window(self):
 337 | +        import select_passages as sp
 338 | +        # BBB sentence 6 runs straight into sentence 7 (no pause): a clip ending there is not cuttable
 339 | +        words = {"AAA": _sentences("a", 2.0, [0.5] * 8), "BBB": _sentences("b", 2.0, [0.5] * 6 + [0.05, 0.5])}
 340 | +
 341 | +        def text(vid, s0, s1):
 342 | +            return " ".join(w["word"] for w in words[vid]
 343 | +                            if s0 <= int(w["word"][1:].split("s")[1].split("w")[0]) <= s1)
 344 | +
 345 | +        with tempfile.TemporaryDirectory() as rd:
 346 | +            os.makedirs(os.path.join(rd, "sources"))
 347 | +            os.makedirs(os.path.join(rd, "transcripts"))
 348 | +            hook = {"kind": "hook", "video_id": "AAA", "channel": "The Bitcoin Layer", "start": 110.0, "end": 119.0,
 349 | +                    "duration": 9.0, "score": 90, "clip_score": 4.5, "text": text("AAA", 5, 6)}
 350 | +            bad = {"kind": "clip", "video_id": "BBB", "channel": "BTC Sessions", "start": 510.0, "end": 524.0,
 351 | +                   "duration": 14.0, "score": 80, "clip_score": 4.0, "text": text("BBB", 4, 6)}
 352 | +            alt = {"kind": "clip", "video_id": "BBB", "channel": "BTC Sessions", "start": 497.5, "end": 510.0,
 353 | +                   "duration": 12.5, "score": 70, "clip_score": 3.8, "text": text("BBB", 0, 2)}
 354 | +            json.dump({"chosen": [hook, bad], "passages": [hook, bad, alt]},
 355 | +                      open(os.path.join(rd, "passages.json"), "w"))
 356 | +
 357 | +            def fake_dl(vid, start, end, run_dir, pad=15.0):
 358 | +                path = os.path.join(run_dir, "sources", f"{vid}.wav")
 359 | +                _synth(path, words[vid])
 360 | +                return (path, 95.0 if vid == "AAA" else 495.0)
 361 | +
 362 | +            def fake_tx(path, vid, run_dir):
 363 | +                rec = {"words": words[vid]}
 364 | +                json.dump(rec, open(os.path.join(run_dir, "transcripts", f"{vid}.json"), "w"))
 365 | +                return rec
 366 | +            orig = (sp._download_window, sp._whisper_transcribe)
 367 | +            sp._download_window, sp._whisper_transcribe = fake_dl, fake_tx
 368 | +            try:
 369 | +                self.assertTrue(sp.select_and_build_edl("test", "bitcoin", rd))
 370 | +            finally:
 371 | +                sp._download_window, sp._whisper_transcribe = orig
 372 | +            edl = json.load(open(os.path.join(rd, "edl.json")))
 373 | +            report = json.load(open(os.path.join(rd, "SELECT_BOUNDARIES.json")))
 374 | +            clip = edl["clips"][0]
 375 | +            self.assertEqual((clip["first_word"], clip["last_word"]), ("bs0w0", "bs2w5."), clip)
 376 | +            rejected = [r for r in report if r["result"].startswith("rejected")]
 377 | +            self.assertTrue(rejected and "OUT" in rejected[0]["result"], report)
 378 | +            self.assertTrue(any(r.get("fallback") and r["result"] == "accepted" for r in report), report)
 379 | +
 380 | +
 381 | +if __name__ == "__main__":
 382 | +    unittest.main()
 383 | diff --git a/pipeline/test_window_review.py b/pipeline/test_window_review.py
 384 | index af2be03e..31996e55 100644
 385 | --- a/pipeline/test_window_review.py
 386 | +++ b/pipeline/test_window_review.py
 387 | @@ -116,7 +116,8 @@ class TestVerifiedAdjacentExpansion(unittest.TestCase):
 388 |          ws = words_for(sents_txt)
 389 |          sents = es._word_sentences(ws)
 390 |          a = es.align_quote("The exchange lost six billion dollars to hackers overnight", ws, 0, 1000)
 391 | -        w, why, span = es.expanded_window(ws, sents, a, 18.0, 25.0, lambda t: (True, "SUPPORTS"))
 392 | +        # 1d: three sentences reach 12 s; the lower-case 'and' start is still rejected
 393 | +        w, why, span = es.expanded_window(ws, sents, a, 12.0, 25.0, lambda t: (True, "SUPPORTS"))
 394 |          self.assertIsNone(w)
 395 |          self.assertIn("start rejected", why)
 396 |  
 397 | @@ -397,7 +398,7 @@ class TestD2TwoVerifiedWindowsPerVideo(unittest.TestCase):
 398 |                  self.assertFalse(p["video_id"] == o["video_id"] and not (p["end"] <= o["start"] or p["start"] >= o["end"]))
 399 |  
 400 |  
 401 | -C = ["Binance confirmed the hack this morning in a short statement posted on its own website.",            # 0
 402 | +C = ["Binance confirmed the hack this morning.",                                                       # 0 (1d: fits 20 s)
 403 |       "It means six billion dollars of customer money left the exchange in one night and nobody stopped it.",  # 1 quote
 404 |       "Withdrawals stayed frozen for hours while the exchange tried to find the hole.",                       # 2
 405 |       "Thanks for watching and see you all tomorrow on the stream."]                                          # 3
 406 | @@ -422,7 +423,7 @@ class TestD3BoundaryRepair(unittest.TestCase):
 407 |  
 408 |      def test_mid_thought_window_passes_after_verified_repair(self):
 409 |          """Positive: the clip 'It means ... hole.' is rated 3 for starting mid-thought; the previous
 410 | -        sentence is verified on-event, so it is added (24.5 s <= 25) and the re-rated window (4.5)
 411 | +        sentence is verified on-event, so it is added (19.2 s <= 20, 1d budget) and the re-rated window (4.5)
 412 |          clears the unchanged 3.5 floor. The hook version cannot grow past 12 s and stays rejected."""
 413 |          llm = RoutedLLM([C[0], C[1], C[2]], rate=self.rate("starts_mid_thought"))
 414 |          cq = self.cq(llm)
 415 | @@ -509,14 +510,16 @@ class TestD4AdjacentReaction(unittest.TestCase):
 416 |          self.assertIn(sm.REACTION_QUESTION, llm.prompts[-1])
 417 |          self.assertIn('<excerpt id="sentence">Some sentence here.</excerpt>', llm.prompts[-1])
 418 |  
 419 | -    def test_at_most_two_admitted_sentences_per_direction(self):
 420 | +    def test_window_never_exceeds_three_sentences(self):
 421 | +        # 1d (2026-11-11): one to three whole sentences; the total binds before the D4 per-direction cap
 422 |          txt = ["It hurt.", "It hurt more.", "It hurt again.", SENTS[1], "This is bad.", "This is worse.", "This is the worst."]
 423 |          ws = words_for(txt)
 424 |          a = es.align_quote(SENTS[1].rstrip("."), ws, 0, 1000)
 425 |          calls = []
 426 |          w, why, span = es.expanded_window(ws, es._word_sentences(ws), a, 60.0, 80.0, lambda t: (calls.append(t) or True, "ok"))
 427 | -        self.assertEqual(sorted(c["direction"] for c in span["expansion"] if c["on_event"]), ["next", "next", "prev", "prev"])
 428 | -        self.assertEqual(sum(c["detail"].startswith("cap:") for c in span["expansion"]), 2)
 429 | +        self.assertEqual(sorted(c["direction"] for c in span["expansion"] if c["on_event"]), ["next", "prev"])
 430 | +        self.assertEqual(sum("sentences; direction closed" in c["detail"] for c in span["expansion"]), 2)
 431 | +        self.assertLessEqual(span["n_sentences"], 3)
 432 |          self.assertNotIn(txt[0], calls)
 433 |          self.assertNotIn(txt[6], calls)
 434 |  
 435 | @@ -635,11 +638,12 @@ class TestD4aInterjectionTransparency(unittest.TestCase):
 436 |          # Both real reactions were checked
 437 |          self.assertIn(txt[2], calls)
 438 |          self.assertIn(txt[3], calls)
 439 | -        # The cap stops at 2 real sentences per direction: txt[4] hits the cap
 440 | +        # 1d: anchor + 2 real reactions = 3 counted sentences (the interjection is transparent);
 441 | +        # txt[4] would be a 4th counted sentence and closes the direction
 442 |          real_next = [c for c in span["expansion"] if c["direction"] == "next" and c["on_event"] is True]
 443 |          self.assertEqual(len(real_next), 2)
 444 | -        cap_entries = [c for c in span["expansion"] if c["detail"].startswith("cap:")]
 445 | -        self.assertTrue(cap_entries, "a cap entry must appear for the 3rd real sentence")
 446 | +        cap_entries = [c for c in span["expansion"] if "sentences; direction closed" in c["detail"]]
 447 | +        self.assertTrue(cap_entries, "a closing entry must appear for the 4th counted sentence")
 448 |  
 449 |      def test_interjection_alone_does_not_make_a_window_legal(self):
 450 |          """An interjection next to a short anchor does not, by itself, make the window long enough."""
 451 | 
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

