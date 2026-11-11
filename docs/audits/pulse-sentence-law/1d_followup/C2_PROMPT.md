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
The changed functions in `select_passages.py` (lines 16-37, 46, 54-59) correctly implement the new conflict checks and post-build duration validation against the locked words' actual span. No path allows a PASS when data is missing or a model fails (M12 FAIL CLOSED is respected). No off-by-one, unit, or silent-exception issues visible in the diff. The `_conflicts` helper and budget re-check after `_build_segment` are the only material changes.

**Q2: LAW COMPLIANCE**  
- SENTENCE LAW / SNAP LIMIT / SELECTION LOCK: COMPLIANT (lines 54-59 reject when locked words fall outside budget; selection_lock is never recomputed).  
- ONSET/TAIL, CREDITS, G12/G15, LAW 20/M2, M12 FAIL CLOSED, LAW 22: no changes in the diff, so COMPLIANT by absence.  
- No cut can move outside the locked sentence's silence, no gate thresholds are loosened, and v2f reference behavior is untouched.

**Q3: TESTS**  
The new tests in `test_sentence_windows.py` (lines 235-268) and updates in `test_fresh.py` (lines 83-124) prove the must-fail cases fail for the documented reasons (missing pause, budget violation on locked words, double-use of a fallback window) and the control cases pass with the expected first/last words. No vacuous assertions; every check inspects concrete `first_word`/`last_word`, rejection strings, or coordinate invariants.

**Q4: VERDICT**  
No defects found.  

READY

## GPT4O — CYCLE 1 OUTPUT
### Q1: CORRECTNESS

1. **Function `_eligible`**:
   - The function checks if a passage is eligible based on its kind, score, and duration. It uses `_budget` to determine the duration limits and `_conflicts` to check for conflicts. The logic appears correct as per the docstring and laws. The function ensures that a passage is within the specified duration and does not conflict with already used passages (lines 31-37).

2. **Function `_conflicts`**:
   - This function checks for conflicts such as overlap with already used windows, per-video, and per-channel limits. The logic seems correct and aligns with the description in the docstring (lines 19-29).

3. **Function `_fill`**:
   - This function attempts to fill a slot with a segment, checking eligibility and conflicts. It includes a check for segment duration against the budget, rejecting segments that don't fit within the specified limits (lines 42-62). The logic is consistent with the requirements.

4. **Test functions**:
   - The test functions are designed to verify that the selection process adheres to the laws and constraints. They simulate various scenarios to ensure that the selection process behaves as expected. The logic in the test cases appears to be correctly implemented to test the intended scenarios (lines 79-268).

5. **Handling of Missing Data or Model Failures**:
   - The code does not seem to handle missing data or model failures explicitly in the diff. However, the logic in `_eligible` and `_conflicts` ensures that only valid and non-conflicting passages are considered, which indirectly handles some cases of missing or invalid data.

### Q2: LAW COMPLIANCE

1. **SENTENCE LAW**: COMPLIANT
   - The code ensures that clips are selected based on complete sentences and checks for acoustic pauses (lines 31-37, 42-62).

2. **SELECTION LOCK**: COMPLIANT
   - The selection lock is respected, and no recomputation of expected words is done after selection (lines 120-124).

3. **SNAP LIMIT**: COMPLIANT
   - The code ensures that cuts are made within the allowed silence between sentences (lines 42-62).

4. **ONSET/TAIL**: PARTIAL
   - The diff does not explicitly show checks for onset/tail requirements, but the selection logic implies adherence to these constraints.

5. **CREDITS**: NOT APPLICABLE
   - The diff does not involve credits handling.

6. **LAW 20 / M2**: COMPLIANT
   - The code does not change gate thresholds or reclassify failing gates as false positives (lines 42-62).

7. **M12 FAIL CLOSED**: COMPLIANT
   - The logic ensures that missing data or conflicts result in rejection, not acceptance (lines 31-37, 42-62).

8. **LAW 22**: NOT APPLICABLE
   - The diff does not involve the v2f reference path.

### Q3: TESTS

- The tests are designed to verify the selection process under various scenarios. They check for correct handling of sentence boundaries, conflicts, and duration constraints.
- The tests seem to cover the necessary scenarios to ensure compliance with the laws. Assertions are specific and should not pass vacuously (lines 79-268).

### Q4: VERDICT

1. **SEVERITY**: LOW | Line 42-62 | The code does not explicitly handle onset/tail requirements, though it implies compliance. | Add explicit checks for onset/tail requirements.
2. **SEVERITY**: LOW | General | The diff does not show handling of credits, though it's not applicable to this change. | Ensure credits handling is verified elsewhere if applicable.

**READY**: The code changes and tests appear to be correct and compliant with the specified laws, with minor improvements suggested for explicitness in onset/tail handling.

## GEMINI — CYCLE 1 OUTPUT
Excellent. I will now perform the requested code audit.

### Q1: CORRECTNESS

The changed functions appear to do what they're intended to do, and the logic seems correct and robust.

1.  **Refactoring of Eligibility Checks:** In `pipeline/select_passages.py`, the original `_eligible` function (lines 9-16) is refactored into `_budget`, `_conflicts`, and a new `_eligible` (lines 16-37). This is a good change for clarity and maintainability. The `_conflicts` function correctly centralizes all reasons a candidate passage might conflict with already `used` segments, including a new and important check for when a fallback from a previous slot has already claimed the window for a later slot (docstring line 21, implementation line 22).

2.  **Conflict Check for Top-Ranked Choice:** The logic on line 46 `(p is first and _conflicts(p, kind))` is a crucial correctness fix. It ensures that even the editor's primary choice for a slot is checked for conflicts. This correctly handles the edge case where a *previous* slot's fallback selection might have already used the time window of a *later* slot's primary selection.

3.  **Post-Cut Duration Check:** The new block on lines 54-59 introduces a vital check. It verifies that the duration of the *actual segment created from the locked words* (`seg["duration"]`) respects the budget (`lo`, `hi`), not just the pre-selection declared window duration (`p["duration"]`). This prevents a situation where a declared 12s window might only contain 9s of sentence-complete speech, which would then be incorrectly used as a "clip". The rejection is handled correctly by setting `seg = None`, which causes the loop to continue to the next candidate.

4.  **Fail-Closed Behavior (M12):** The code respects the M12 FAIL CLOSED law. When `_build_segment` fails (which it would for a boundary violation, as tested), it returns `None`. The loop correctly `continue`s on line 51. The new duration check also fails closed by nullifying the segment (`seg = None` on line 59) and allowing the `if seg is not None:` on line 60 to prevent its use. No new paths introduce silent exceptions or pass-on-failure behavior.

### Q2: LAW COMPLIANCE

The code appears to be compliant with all applicable laws.

*   **SENTENCE LAW:** **COMPLIANT.** While the diff doesn't show the implementation of the acoustic pause check, the new tests in `pipeline/test_sentence_windows.py` are explicitly designed to prove its existence and enforcement. The test data on line 160 includes a sentence gap of `0.05`s (< 80ms). The test on lines 236-244 verifies that a candidate clip (`bad`) ending at this illegal boundary is rejected for that specific reason (the `assertIn("OUT", rej["result"] ...)` on line 244). This demonstrates compliance.

*   **SELECTION LOCK:** **COMPLIANT.** The new logic on lines 54-59 operates on `seg`, which is the result of `_build_segment`. This is the point where words are locked. The check uses the duration of this locked segment, it does not recompute or change the selected words. The test on line 122 also confirms the `selection_lock` is created and matches the final segment words.

*   **SNAP LIMIT:** **COMPLIANT.** The test `test_rejected_clip_is_replaced_by_the_next_legal_window` proves this. The `bad` candidate window is rejected because there is "No legal boundary" in the gap (the pause is too short). The system then correctly falls back to another candidate rather than trying to move the cut point into the spoken part of the sentence.

*   **ONSET/TAIL:** **UNCERTAIN.** This diff does not touch rendering or audio processing code, only the selection logic. I cannot verify compliance or violation from the provided files.

*   **CREDITS:** **UNCERTAIN.** This diff does not touch any code related to credit generation or avatar handling. I cannot verify compliance or violation.

*   **LAW 20 / M2:** **COMPLIANT.** The new duration check on lines 55-59 is a hard gate with a clear rejection. It correctly causes a fallback to the next candidate. No thresholds have been loosened; a new, stricter gate has been added.

*   **M12 FAIL CLOSED:** **COMPLIANT.** As noted in Q1, failures (boundary not found, duration out of budget) lead to rejection of the candidate segment, not a pass.

*   **LAW 22:** **UNCERTAIN.** This diff does not touch code related to the `v2f` reference render. I cannot verify compliance or violation.

### Q3: TESTS

The new and modified tests are excellent and directly prove the claims.

1.  **`test_fresh.py`:** The update to generate more realistic test data (12 words per sentence, line 73) and the correct handling of source window offsets (`win_off`, line 83) makes the test suite more robust and less likely to have false positives related to coordinate systems.

2.  **`test_sentence_windows.py`:** This file contains the most critical new tests, which are very well-designed.
    *   **`test_rejected_clip_is_replaced...`:** This test (line 235) successfully proves the primary fix. It creates a "m

## CLAUDE'S CYCLE 1 CONSENSUS
# CONSENSUS REPORT — PULSE-SENTENCE-LAW — CYCLE 1
Generated: 2026-11-11 04:04
Models: grok, gpt4o, gemini

---

## SCORES

Scores are synthesized from each model's explicit verdict and severity language. No model used a numeric rubric, so scores are derived from qualitative signal (PASS / flag count / severity labels) mapped to a 1–10 scale where 10 = no defects, fully compliant.

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Correctness (`select_passages.py`) | 10 | 9 | 10 | **10** |
| Law Compliance — SENTENCE LAW | 10 | 10 | 10 | **10** |
| Law Compliance — SELECTION LOCK | 10 | 10 | 10 | **10** |
| Law Compliance — SNAP LIMIT | 10 | 10 | 10 | **10** |
| Law Compliance — ONSET/TAIL | Uncertain | 7 | 10 | **Uncertain** |
| Law Compliance — CREDITS | Uncertain | N/A | 10 | **Uncertain** |
| Law Compliance — LAW 20 / M2 | 10 | 10 | 10 | **10** |
| Law Compliance — M12 FAIL CLOSED | 10 | 10 | 10 | **10** |
| Law Compliance — LAW 22 / v2f | Uncertain | N/A | 10 | **Uncertain** |
| Test Quality | 10 | 9 | 10 | **10** |
| Overall | **9.5** | **9.0** | **10** | **9.5** |

> **Score note:** The 0.5-point haircut on consensus overall reflects three "Uncertain" ratings on laws that the diff does not touch. These are not defects in the changed code — they are audit visibility gaps. The changed code itself is clean.

---

## UNANIMOUS FINDINGS (all 3 models agree — implement unconditionally)

**None.** All three models converged on the same high-level conclusion: the changed code and new tests are correct, the laws they touch are compliant, and no concrete defects were found in the diff. There is no issue that all three models simultaneously flagged as requiring a fix.

---

## MAJORITY FINDINGS (2 of 3 models agree)

### M1 — ONSET/TAIL compliance is unverifiable from the diff (Gemini + GPT-4o)

- **What it is:** The diff covers selection logic only. Neither the diff nor the test files provide evidence that ONSET/TAIL guard requirements are enforced at the selection layer or verified in these tests.
- **File/line:** `pipeline/select_passages.py` — no specific line; absence of check.
- **GPT-4o rating:** LOW severity, suggested adding explicit checks.
- **Gemini rating:** UNCERTAIN — cannot confirm or deny from provided files.
- **Grok position:** Declared COMPLIANT by absence (no changes to onset/tail code, therefore no regression). This is a technically defensible but weaker claim.
- **Consensus action:** **Investigate further.** This is not a regression introduced by this diff. However, the audit surface is incomplete. Before closing the feature, confirm in a separate audit pass that onset/tail enforcement lives somewhere in the pipeline (rendering layer, pre-filter, or a dedicated gate) and is covered by at least one test. If it does not exist, add it.

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### U1 — Conflict check on line 46 is a correctness fix for a subtle ordering hazard (Gemini only)



---

## ORIGINAL CODE (same code as Cycle 1)
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
