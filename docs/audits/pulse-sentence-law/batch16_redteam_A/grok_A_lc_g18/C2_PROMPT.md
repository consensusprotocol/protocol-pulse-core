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
Yes.  
- `tokens` (10-12) and `anchor` (30-48) delegate to `canon.canon_tokens`/`canon_aligned` and enforce first/last-token lock boundaries (46-47).  
- `edge_word_fidelity` (56-106) now requires every frame compared (89), supports `offset_s`+`gain_invariant` for finals, and returns explicit failure when no alignment covers the word.  
- New `span_matches` (115-147) and `_gain_db` (152-174) implement the exact acoustic rules in their docstrings (interior speech, ±2 hops, SPAN_* constants).  
- `edges_on_final` (184-214) runs G17c on the final bytes after gain removal.  
- `norm`/`diff` (480-502) route through canon and preserve repeat-only differences for acoustic adjudication (510-521).  
No off-by-one, unit, or silent-pass paths visible; missing data yields explicit False.

**Q2: LAW COMPLIANCE**  
COMPLIANT on every cited law.  
- SENTENCE LAW / L-e / L-k: punctuation assumed pre-applied; all text paths now use canon (10-12, 30, 487).  
- SELECTION LOCK / SNAP LIMIT: anchor rejects any token outside the locked span (46-47).  
- L-b / L-c: fades stay in gap; proof moved to final bytes (208-210, 184-214).  
- L-g / L-h: symbols, entities, and spoken forms handled identically via canon.  
- No threshold changes, no recomputation of locks, no v2f divergence.

**Q3: TESTS**  
Yes.  
- `TestSpanMatches` (339-381) uses synthetic bursts that must-pass (same span + gain/codec) and must-fail (300 ms repeat).  
- `test_a_repeat_only_difference_is_kept_as_evidence` (301-307) and `test_units_and_signs_are_not_erased` (309-317) assert the exact non-vacuous behaviours required by F04/F05.  
- verdict tests (278-284) now use the exact `passing_rows` inventory and confirm every bad row produces HOLD.

**Q4: VERDICT**  
No defects.  
READY

## GPT4O — CYCLE 1 OUTPUT
### Q1: CORRECTNESS

1. **`tokens` function (lines 8-12):** 
   - The function uses `canon.canon_tokens(text)` to tokenize the text. This aligns with the docstring that states it uses the canonical form from `pipeline/canon.py`. The function appears to correctly replace the previous regex-based tokenization.

2. **`SourceAudio.speech_bed_quiet` function (lines 16-24):**
   - The logic for calculating `speech` has been adjusted to handle cases where `upper` might be empty. The fallback to using `live` ensures no NaN values are produced, which aligns with the comment (GPT-cut F28). This seems correct.

3. **`anchor` function (lines 26-48):**
   - The function now uses `canon.canon_aligned` for token alignment, which should provide a more accurate alignment based on the canonical form. The check for the lock starting and ending on the correct tokens (lines 46-47) ensures that the selection is properly anchored, preventing off-by-one errors.

4. **`edge_word_fidelity` function (lines 55-106):**
   - The function now includes parameters `offset_s` and `gain_invariant`, which are used to adjust the comparison based on the final's gain and offset. The logic for comparing frames ensures that every frame of the edge word is compared, and the gain is removed before comparison, aligning with the docstring and law L-c.

5. **`span_matches` function (lines 115-147):**
   - This function checks if the final's audio segment matches the source span, considering gain and allowing for small timing shifts. The logic appears to follow the described process, and the exclusion of edges (SPAN_EDGE_S) is correctly implemented.

6. **`_gain_db` function (lines 152-174):**
   - The function calculates the constant gain between a source span and its rendered copy. The use of median level difference over interior speech frames seems correct, and it returns None if the conditions for a steady gain are not met.

7. **`edges_on_final` function (lines 184-214):**
   - This function implements the acoustic proof for dissenting edge readings, using the final file's bytes. The logic for handling exceptions and ensuring both sides are checked aligns with the requirements.

8. **`norm` function in `word_diff.py` (lines 480-490):**
   - The function uses canonical forms and applies specific rules for dropping 'dollars' after numbers, aligning with the docstring. The handling of repeats with `collapse` is consistent with the requirements.

9. **`diff` function in `word_diff.py` (lines 498-502):**
   - The function now includes a `collapse` parameter to handle repeat-only differences, which aligns with the updated requirements for G18.

Overall, the functions appear to handle their tasks correctly according to their docstrings and the laws.

### Q2: LAW COMPLIANCE

1. **SENTENCE LAW:** COMPLIANT
   - The `anchor` function (lines 26-48) ensures that the selection lock is respected and does not recompute expected words after selection.

2. **SELECTION LOCK:** COMPLIANT
   - The logic in `anchor` (lines 26-48) and `edges_on_final` (lines 184-214) ensures that the selection lock is respected.

3. **SNAP LIMIT:** COMPLIANT
   - The `edge_word_fidelity` function (lines 55-106) ensures that cuts do not move outside the allowed boundaries.

4. **NEIGHBOUR:** COMPLIANT
   - The checks in `edge_word_fidelity` ensure that no audible part of the neighboring word is included.

5. **ONSET/TAIL:** COMPLIANT
   - The `edge_word_fidelity` function ensures that edge words are heard whole.

6. **CREDITS:** NOT APPLICABLE
   - No changes related to credits in the diff.

7. **L-a SIGN-OFF NAMES ALL:** NOT APPLICABLE
   - No changes related to sign-off names in the diff.

8. **L-b EDGE WORDS WHOLE:** COMPLIANT
   - The `edge_word_fidelity` function ensures compliance by comparing every frame of the edge words.

9. **L-c DISSENT IS RIGHT UNTIL DISPROVED:** COMPLIANT
   - The `edges_on_final` function implements the required checks for dissenting edge readings.

10. **L-d PROTECTED PREVIEW:** NOT APPLICABLE
    - No changes related to the protected preview in the diff.

11. **L-e PUNCTUATED BEFORE READ:** NOT APPLICABLE
    - No changes related to punctuation in the diff.

12. **L-f CHANNELS FIRST:** NOT APPLICABLE
    - No changes related to channel selection in the diff.

13. **L-g WRITTEN FORMS:** COMPLIANT
    - The `norm` function in `word_diff.py` handles written forms as required.

14. **L-h TEXT READ AS SPOKEN:** NOT APPLICABLE
    - No changes related to text reading in the diff.

15. **L-i THE CLAIM IS THE EVENT:** NOT APPLICABLE
    - No changes related to claims in the diff.

16. **L-j RELEASE IS AUTHORISED ON THESE BYTES:** NOT APPLICABLE
    - No changes related to release authorization in the diff.

17. **L-k ONE CANONICAL FORM:** COMPLIANT
    - The use of `canon.canon_tokens` ensures compliance with the canonical form requirement.

18. **LAW 20 / M2:** COMPLIANT
    - No evidence of threshold changes in the diff.

19. **M12 FAIL CLOSED:** COMPLIANT
    

## GEMINI — CYCLE 1 OUTPUT
An audit of the `pulse-sentence-law` feature branch.

### Q1: CORRECTNESS
The changes appear to be of high quality, demonstrating a deep understanding of the problems identified in the 2026-11-10 cut. The code correctly implements its documented intentions.

-   **`pipeline/sentence_law.py`:**
    -   The move to a centralized `canon.py` for tokenization (lines 11, 30, 36) is a significant correctness and maintainability improvement, removing ad-hoc text processing.
    -   The fix for potential `NaN` values from `np.median` on flat envelopes (line 22) is robust, preventing a class of silent failures.
    -   The new anchor check (lines 46-47) correctly tightens the `SELECTION LOCK` by ensuring the match begins on the first token of the first word and ends on the last token of the last word, preventing partial-word matches.
    -   `edge_word_fidelity` is substantially improved. The new check `keep[n:].any()` (line 89) correctly implements the "every frame must be compared" rule from GPT-cut F07, preventing an alignment from being accepted if it doesn't cover the entire audible part of the word. The `gain_invariant` logic (lines 73-77, 93) correctly isolates the comparison from loudness changes in the final render.
    -   The new functions `_gain_db` and `span_matches` (lines 115-174) are well-designed. `_gain_db` correctly measures gain on the interior of a clip to avoid fades and uses interquartile range (`spread`) to ensure the gain is constant, which is a robust method. `span_matches` correctly uses a "run of bad frames" (lines 137-141) to detect insertions/deletions, which is more robust than a simple percentage of mismatched frames.
    -   `edges_on_final` correctly orchestrates the new checks, with a solid `try...except` block (line 211) that ensures any failure during measurement results in a failed check, upholding M12 FAIL CLOSED.

-   **`pipeline/word_diff.py`:**
    -   The replacement of complex, local normalization logic (lines 395-479 deleted) with a call to the new `canon.py` (line 487) is a major correctness win.
    -   The new logic in `gate_g18` (lines 510-521) to handle repeat-only differences is sophisticated and correct. It correctly isolates these specific cases, keeps the original difference as evidence, and uses the new `span_matches` for an acoustic tie-breaker. The `try...except` block (line 517) correctly handles measurement failures.

No state appears to leak between clips. Units seem correct (e.g., `HOP_S` is used consistently). The code paths for handling missing data or exceptions correctly result in failures rather than passes.

### Q2: LAW COMPLIANCE

-   **SENTENCE LAW:** COMPLIANT. The core logic is unchanged, but its inputs are now governed by `canon.py` (L-k), improving consistency.
-   **SELECTION LOCK:** COMPLIANT. Strengthened by the new anchor checks at lines 46-47.
-   **SNAP LIMIT:** COMPLIANT. No changes to the relevant logic.
-   **NEIGHBOUR:** COMPLIANT. No changes to the relevant logic.
-   **ONSET/TAIL:** COMPLIANT. No changes to the relevant logic.
-   **CREDITS:** CANNOT VERIFY. No relevant code in diff.
-   **L-a SIGN-OFF NAMES ALL:** CANNOT VERIFY. No relevant code in diff.
-   **L-b EDGE WORDS WHOLE:** COMPLIANT. Directly addressed by the major changes to `edge_word_fidelity` (lines 55-106), which now performs a more rigorous acoustic comparison of the edge words against the source.
-   **L-c DISSENT IS RIGHT UNTIL DISPROVED:** COMPLIANT. This is a primary focus of the commit. It is implemented by:
    1.  The new function `edges_on_final` (lines 184-214), which runs checks on the final render.
    2.  `edge_word_fidelity`'s `gain_invariant` mode (line 57, 210).
    3.  The rule that every word frame must be compared (line 89).
    4.  The acoustic adjudication for G18 repeat-only differences in `word_diff.py` (lines 510-521).
-   **L-d PROTECTED PREVIEW:** CANNOT VERIFY. The diff does not contain the regression script or its output.
-   **L-e PUNCTUATED BEFORE READ:** CANNOT VERIFY. The diff shows code that consumes transcripts but not the `transcript_store` that implements this law.
-   **L-f CHANNELS FIRST:** CANNOT VERIFY. No relevant code in diff.
-   **L-g WRITTEN FORMS:** PARTIAL. The code is compliant by delegating to `canon.py` (lines 481, 487). Final compliance depends on the (unseen) implementation of `canon.py`. The test at `test_word_diff.py:293-296` suggests it works as specified.
-   **L-h TEXT READ AS SPOKEN:** PARTIAL. Compliance depends on the unseen `canon.py`.
-   **L-i THE CLAIM IS THE EVENT:** CANNOT VERIFY. No relevant code in diff.
-   **L-j RELEASE IS AUTHORISED ON THESE BYTES:** COMPLIANT. The test `test_verdict_rules` (lines 265-284) is rewritten to enforce the "exact inventory" rule, ensuring that old, permissive verdicts now correctly HOLD the run.
-   **L-k ONE CANONICAL FORM:** COMPLIANT. This is a core theme of the change. Ad-hoc normalization is removed from `word_diff.py` (lines 395-479 deleted) and both `sentence_law

## CLAUDE'S CYCLE 1 CONSENSUS
# CONSENSUS REPORT — PULSE-SENTENCE-LAW — CYCLE 1
Generated: 2026-11-11 22:40
Models: grok, gpt4o, gemini

---

## SCORES

Scores extracted from qualitative verdicts and severity assessments. Models did not emit numeric scores; mapped from verdict language to 0–10 scale (10 = fully correct/compliant/tested).

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| **Correctness** | 9 | 8 | 9 | 8.7 |
| **Law Compliance** | 7 | 8 | 9 | 8.0 |
| **Test Coverage** | 9 | 8 | 9 | 8.7 |
| **Security / Fail-Closed** | 9 | 8 | 8 | 8.3 |
| **Overall Readiness** | 9 | 9 | 9 | **9.0** |

> Score deductions: Gemini and GPT-4o both docked points for the unverified `canon.py` dependency (L-g, L-h, L-k) and for unverified laws (L-d, L-e, L-f, L-i, L-j, LAW 22). Grok assumed those modules pass; that optimism is noted as an audit limitation.

---

## UNANIMOUS FINDINGS (all 3 models agree — implement unconditionally)

**None.** All three models returned a READY verdict with no defects that all three flagged identically. The findings below are strong majority or unique observations. This is a positive result — no unanimous defects — but the unanimous *gap* around `canon.py` is treated as a system-level finding (see Majority Findings).

---

## MAJORITY FINDINGS (2 of 3 models agree)

### MF-1 — `canon.py` is unaudited; L-g, L-h, L-k compliance is contingent
**Models:** Gemini (explicit), GPT-4o (implicit — marked L-g COMPLIANT "by delegation"; L-h NOT APPLICABLE)
**Grok:** Assumed compliant without caveat.

**What it is:** Both `sentence_law.py` and `word_diff.py` now delegate all text normalisation to `pipeline/canon.py`. The correctness of L-g (written forms), L-h (text read as spoken), and L-k (one canonical form) is entirely contingent on the implementation of that module. Neither Gemini nor GPT-4o could verify it from the diff alone.

**File/Line:** `pipeline/canon.py` — entire module (not in diff)

**What to change:** `canon.py` must be surfaced and audited before final sign-off. At minimum, add a targeted test that exercises every branch referenced by the laws (currency symbols, unit abbreviations, entity spoken forms, case folding) so that future diffs to `canon.py` are tested in isolation.

**Implement:** YES — block final sign-off until `canon.py` is audited or test coverage proves behaviour.

---

### MF-2 — LAW 22 / v2f regression result is not in the diff
**Models:** Gemini (explicit CANNOT VERIFY), GPT-4o (marked NOT APPLICABLE — arguably incorrect dismissal)
**Grok:** Declared compliant without citing evidence.

**What it is:** LAW 22 requires that the v2f reference hash is unchanged. The diff does not include the regression test output proving the reference did not drift.

**File/Line:** Regression artefact — expected at `docs/audits/` or `test_v2f_regression.py`

**What to change:** Attach v2f regression output (or CI badge) to the PR. If the regression script is `regression_test.sh`, its output must be committed alongside the fea

---

## ORIGINAL CODE (same code as Cycle 1)
## THE CODE (every new and modified file)

### File: docs/audits/pulse-sentence-law/CURRENT.diff (525 lines)
```
   1 | diff --git a/pipeline/sentence_law.py b/pipeline/sentence_law.py
   2 | index 9dd31e3b..15657eff 100644
   3 | --- a/pipeline/sentence_law.py
   4 | +++ b/pipeline/sentence_law.py
   5 | @@ -88,7 +88,9 @@ class LawError(Exception):
   6 |  # ── text ──
   7 |  
   8 |  def tokens(text):
   9 | -    return [t for t in re.split(r"[^a-z0-9]+", (text or "").lower().replace("’", "'").replace("'", "")) if t]
  10 | +    """Words in the pipeline's one canonical form (pipeline/canon.py)."""
  11 | +    import canon
  12 | +    return canon.canon_tokens(text)
  13 |  
  14 |  
  15 |  def is_terminal(word):
  16 | @@ -144,7 +146,8 @@ class SourceAudio:
  17 |          live = d[d > DIGITAL_FLOOR_DBFS]
  18 |          if len(live) < 10:
  19 |              raise LawError(f"no audio in [{t0:.2f}, {t1:.2f}]")
  20 | -        speech = float(np.median(live[live > np.percentile(live, 30)]))
  21 | +        upper = live[live > np.percentile(live, 30)]
  22 | +        speech = float(np.median(upper if len(upper) else live))     # a flat envelope gives no NaN (GPT-cut F28)
  23 |          bed = float(np.percentile(live, 10))
  24 |          quiet = min(speech - VALLEY_BELOW_SPEECH_DB, max(speech - QUIET_BELOW_SPEECH_DB, bed + BED_PLUS_DB))
  25 |          return {"speech_db": round(speech, 1), "bed_db": round(bed, 1), "quiet_db": round(quiet, 1),
  26 | @@ -322,9 +325,11 @@ def anchor(words, text, min_ratio=ANCHOR_MIN_RATIO, t0=None, t1=None):
  27 |      """Locate the editor's selected text in a word-timestamp transcript (text alignment, never time
  28 |      arithmetic; [t0, t1] only narrows the search). The span's first and last tokens must equal the
  29 |      selection's. Returns (i0, i1, ratio) or None."""
  30 | +    import canon                                      # one canonical form; a token keeps the word it starts in
  31 |      qt = tokens(text)
  32 | -    toks = [(t, wi) for wi, w in enumerate(words)
  33 | -            if (t0 is None or w["start"] >= t0) and (t1 is None or w["start"] <= t1) for t in tokens(w["word"])]
  34 | +    idx = [wi for wi, w in enumerate(words)
  35 | +           if (t0 is None or w["start"] >= t0) and (t1 is None or w["start"] <= t1)]
  36 | +    toks = [(t, idx[o]) for t, o in canon.canon_aligned([words[wi]["word"] for wi in idx])]
  37 |      seq = [t for t, _ in toks]
  38 |      if len(qt) < 3 or not seq:
  39 |          return None
  40 | @@ -345,8 +350,8 @@ def anchor(words, text, min_ratio=ANCHOR_MIN_RATIO, t0=None, t1=None):
  41 |          return None
  42 |      r, s, e = best
  43 |      i0, i1 = toks[s][1], toks[e][1]
  44 | -    if tokens(words[i0]["word"])[0] != qt[0] or tokens(words[i1]["word"])[-1] != qt[-1]:
  45 | -        return None
  46 | +    if (s and toks[s - 1][1] == i0) or (e + 1 < len(toks) and toks[e + 1][1] == i1):
  47 | +        return None                    # a lock starts on its first word's first token and ends on its last word's last
  48 |      return i0, i1, round(r, 3)
  49 |  
  50 |  
  51 | @@ -473,14 +478,27 @@ def edge_fades(sa, plan, cut_in, cut_out):
  52 |      return round(fi, 3), round(fo, 3), wb
  53 |  
  54 |  
  55 | -def edge_word_fidelity(src_path, clip_path, plan, cut_in, cut_out, pad_s=0.0, sa=None):
  56 | +def edge_word_fidelity(src_path, clip_path, plan, cut_in, cut_out, pad_s=0.0, sa=None, offset_s=0.0,
  57 | +                       gain_invariant=False):
  58 |      """G17c (law L-b): the first and the last word of a prepared clip, with their natural decay, at full level:
  59 |      every 10 ms frame of the source over [first onset, + 0.3 s] and [last end - 0.3 s, last end] that is above
  60 |      the gap level next to the cut is matched in the clip within EDGE_WORD_MAX_DB (best alignment within +-2
  61 | -    hops absorbs the codec's delay). Returns (ok, detail)."""
  62 | +    hops absorbs the codec's delay). Every word frame must be compared (GPT-cut F07: an alignment that leaves a
  63 | +    word frame outside the clip is no proof; zero compared frames is never 'perfect').
  64 | +    offset_s: where the clip starts inside clip_path (0 for a prepared clip; the segment's start in a FINAL).
  65 | +    gain_invariant: the final's constant gain (amix + loudnorm) is measured on the clip's own interior speech
  66 | +    and removed before the 1 dB comparison (law L-c: the proof is made on the final's bytes). Returns (ok,
  67 | +    detail)."""
  68 |      sa = sa or SourceAudio(src_path)
  69 |      ca = SourceAudio(clip_path)
  70 |      wb = edge_word_bounds(sa, plan, cut_in, cut_out)
  71 | +    base = offset_s - cut_in + pad_s                                # source time -> clip_path time
  72 | +    gain = 0.0
  73 | +    if gain_invariant:
  74 | +        gain = _gain_db(sa, ca, cut_in, cut_out, base)
  75 | +        if gain is None:
  76 | +            return False, {side: {"ok": False, "why": "the final's gain is not measurable on the clip interior"}
  77 | +                           for side in ("in", "out")}
  78 |      det = {}
  79 |      for side, (a, b) in (("in", (wb["onset"], None)), ("out", (None, wb["end"]))):
  80 |          if (a if side == "in" else b) is None:
  81 | @@ -494,22 +512,92 @@ def edge_word_fidelity(src_path, clip_path, plan, cut_in, cut_out, pad_s=0.0, sa
  82 |              continue
  83 |          best = None
  84 |          for k in range(-2, 3):
  85 | -            tc, dc = ca.sl(t0 - cut_in + pad_s + k * HOP_S, t1 - cut_in + pad_s + k * HOP_S)
  86 | +            tc, dc = ca.sl(t0 + base + k * HOP_S, t1 + base + k * HOP_S)
  87 |              n = min(len(dc), len(ds))
  88 | -            if n == 0:
  89 | +            if n == 0 or keep[n:].any():                             # a word frame left uncompared: no proof
  90 |                  continue
  91 | -            diff = np.abs(dc[:n] - ds[:n])[keep[:n]]
  92 | -            worst = float(np.max(diff)) if len(diff) else 0.0
  93 | +            diff = np.abs(dc[:n] - gain - ds[:n])[keep[:n]]
  94 | +            worst = float(np.max(diff))
  95 |              if best is None or worst < best[0]:
  96 |                  best = (worst, k)
  97 |          ok = best is not None and best[0] <= EDGE_WORD_MAX_DB
  98 |          det[side] = {"ok": ok, "span": [round(t0, 3), round(t1, 3)], "worst_db": None if best is None else round(best[0], 2),
  99 | -                     "shift_hops": None if best is None else best[1],
 100 | +                     "shift_hops": None if best is None else best[1], "compared_frames": int(keep.sum()),
 101 | +                     **({"gain_db": round(gain, 2)} if gain_invariant else {}),
 102 |                       "why": "edge word at full level" if ok else
 103 | -                     f"edge word up to {best[0] if best else float('nan'):.1f} dB off the source (max {EDGE_WORD_MAX_DB})"}
 104 | +                     "no alignment compares every frame of the edge word" if best is None else
 105 | +                     f"edge word up to {best[0]:.1f} dB off the source (max {EDGE_WORD_MAX_DB})"}
 106 |      return all(v["ok"] for v in det.values()), det
 107 |  
 108 |  
 109 | +GAIN_INTERIOR_MARGIN_S = 0.5    # law L-c: the final's gain is read away from both edges (fades, dissolves)
 110 | +SPAN_EDGE_S = 0.3               # span_matches: edges excluded (fades, dissolves)
 111 | +SPAN_MISMATCH_DB = 6.0          # a speech frame off the source by more than this is a mismatch
 112 | +SPAN_MISMATCH_RUN_S = 0.15      # this long a run of mismatching speech frames = the audio is not the source span
 113 | +
 114 | +
 115 | +def span_matches(src_path, final_path, cut_in, cut_out, offset_s, pad_s=0.0, sa=None):
 116 | +    """GPT-cut F05: the acoustic adjudication of a repeat-only G18 difference. The final's audio of a segment is
 117 | +    the source span itself: after the constant gain is removed (_gain_db) and the best of +-2 hops, no run of
 118 | +    SPAN_MISMATCH_RUN_S of consecutive speech frames differs from the source by more than SPAN_MISMATCH_DB (an
 119 | +    inserted or dropped word shifts everything after it). Edges (SPAN_EDGE_S) are excluded. (ok, detail)."""
 120 | +    sa = sa or SourceAudio(src_path)
 121 | +    ca = SourceAudio(final_path)
 122 | +    base = offset_s - cut_in + pad_s
 123 | +    gain = _gain_db(sa, ca, cut_in, cut_out, base)
 124 | +    if gain is None:
 125 | +        return False, {"why": "gain not measurable"}
 126 | +    t0, t1 = cut_in + SPAN_EDGE_S, cut_out - SPAN_EDGE_S
 127 | +    _, ds = sa.sl(t0, t1)
 128 | +    if len(ds) < 20:
 129 | +        return False, {"why": "span too short to compare"}
 130 | +    speech = ds > np.percentile(ds, 50)
 131 | +    best = None
 132 | +    for k in range(-2, 3):
 133 | +        _, dc = ca.sl(t0 + base + k * HOP_S, t1 + base + k * HOP_S)
 134 | +        if len(dc) < len(ds):
 135 | +            continue
 136 | +        bad = (np.abs(dc[:len(ds)] - gain - ds) > SPAN_MISMATCH_DB) & speech
 137 | +        run = longest = 0
 138 | +        for b in bad:
 139 | +            run = run + 1 if b else 0
 140 | +            longest = max(longest, run)
 141 | +        if best is None or longest < best[0]:
 142 | +            best = (longest, k, int(bad.sum()))
 143 | +    if best is None:
 144 | +        return False, {"why": "the final is shorter than the source span"}
 145 | +    ok = best[0] * HOP_S < SPAN_MISMATCH_RUN_S
 146 | +    return ok, {"gain_db": round(gain, 2), "shift_hops": best[1], "longest_mismatch_ms": int(round(best[0] * HOP_S * 1000)),
 147 | +                "mismatch_frames": best[2], "speech_frames": int(speech.sum())}
 148 | +
 149 | +
 150 | +
 151 | +
 152 | +def _gain_db(sa, ca, cut_in, cut_out, base):
 153 | +    """The constant gain (dB) between a source span and its rendered copy: the median level difference over the
 154 | +    span's interior speech frames (the louder half of the source), at the best of +-2 hops. None when the
 155 | +    interior has fewer than 20 speech frames or the difference is not steady (spread > 1 dB)."""
 156 | +    t0, t1 = cut_in + GAIN_INTERIOR_MARGIN_S, cut_out - GAIN_INTERIOR_MARGIN_S
 157 | +    if t1 - t0 < 0.5:
 158 | +        return None
 159 | +    _, ds = sa.sl(t0, t1)
 160 | +    if len(ds) < 20:
 161 | +        return None
 162 | +    speech = ds > np.percentile(ds, 50)
 163 | +    best = None
 164 | +    for k in range(-2, 3):
 165 | +        _, dc = ca.sl(t0 + base + k * HOP_S, t1 + base + k * HOP_S)
 166 | +        n = min(len(dc), len(ds))
 167 | +        m = speech[:n]
 168 | +        if n < len(ds) or m.sum() < 20:
 169 | +            continue
 170 | +        d = dc[:n][m] - ds[:n][m]
 171 | +        spread = float(np.percentile(d, 75) - np.percentile(d, 25))
 172 | +        if best is None or spread < best[1]:
 173 | +            best = (float(np.median(d)), spread)
 174 | +    return None if best is None or best[1] > 1.0 else best[0]
 175 | +
 176 | +
 177 |  def accepted_cut(src, plan, step=HOP_S, sa=None):
 178 |      """The cut nearest the plan's targets. Both edges clear of cut_accept: its unchanged acoustics check on the
 179 |      pair (20 / 30 ms fades). An edge only reachable at the envelope minimum (DEC-10 d) gets a 2-frame fade and
 180 | @@ -747,6 +835,39 @@ def gate_g17_edges(run_dir, source_path_fn=None):
 181 |      return ok_all, table
 182 |  
 183 |  
 184 | +def edges_on_final(final_path, segments, run_dir, source_path_fn=None):
 185 | +    """Law L-c as amended by the orchestrator (addendum 2026-11-11 '22:00', GPT-cut F03): the acoustic proof
 186 | +    that overrules a dissenting edge reading is G17c measured on the FINAL file being approved (its bytes, its
 187 | +    gain removed), never on the prepared clip. {label: {"in": detail, "out": detail}} for every talking head of
 188 | +    that final; a segment that cannot be measured has both sides ok False."""
 189 | +    with open(os.path.join(run_dir, "edl.json")) as f:
 190 | +        locks = {label: (seg.get("selection_lock"), seg["video_id"]) for label, seg in _segments(json.load(f))}
 191 | +    with open(os.path.join(run_dir, "cuts_final.json")) as f:
 192 | +        cuts = {c["clip_id"]: c for c in json.load(f)}
 193 | +    out = {}
 194 | +    for seg in segments:
 195 | +        if seg.get("type") != "talking_head":
 196 | +            continue
 197 | +        label = seg["label"]
 198 | +        (lock, vid), cut = locks.get(label, (None, None)), cuts.get(label)
 199 | +        if not lock or not cut:
 200 | +            out[label] = {s: {"ok": False, "why": "no lock / cut"} for s in ("in", "out")}
 201 | +            continue
 202 | +        try:
 203 | +            with open(os.path.join(run_dir, "transcripts", f"{vid}.json")) as f:
 204 | +                words = json.load(f)["words"]
 205 | +            src = (source_path_fn or (lambda v: os.path.join(run_dir, "sources", f"{v}.mp4")))(vid)
 206 | +            sa = SourceAudio(src)
 207 | +            plan = edge_plan(sa, words, lock["i0"], lock["i1"])
 208 | +            _, det = edge_word_fidelity(src, final_path, plan, cut["cut_in"], cut["cut_out"],
 209 | +                                        float(cut.get("lead_in_pad_s") or 0), sa=sa, offset_s=float(seg["start"]),
 210 | +                                        gain_invariant=True)
 211 | +        except (LawError, OSError, ValueError, KeyError, subprocess.SubprocessError) as e:
 212 | +            det = {s: {"ok": False, "why": f"not measurable: {type(e).__name__}: {e}"} for s in ("in", "out")}
 213 | +        out[label] = det
 214 | +    return out
 215 | +
 216 | +
 217 |  # ── G17 ONSET/TAIL INTEGRITY (rendered audio) ──
 218 |  
 219 |  def head_tail(sa):
 220 | diff --git a/pipeline/test_dec1_calibration.py b/pipeline/test_dec1_calibration.py
 221 | index 3c1ed3c3..b09c8982 100644
 222 | --- a/pipeline/test_dec1_calibration.py
 223 | +++ b/pipeline/test_dec1_calibration.py
 224 | @@ -143,17 +143,29 @@ class TestTailRows(unittest.TestCase):
 225 |      """Heimdall DEC-1 audit: G9_tail is the calibrated gate alone; a conform fallback (not the locked
 226 |      outro the floor was measured on) fails its own row, so the run still holds."""
 227 |  
 228 | +    def verdict(self, tail):
 229 | +        """run_fresh's verdict (release_auth's exact inventory) on an otherwise passing 16:9 row set."""
 230 | +        import run_fresh as rf
 231 | +        from test_release_auth import passing_rows
 232 | +        return rf.verdict_for({**passing_rows()["16x9"], **tail}, "16x9")[0]
 233 | +
 234 |      def test_luma_pass_on_a_fallback_outro_fails_outro_locked(self):
 235 | -        import run_fresh as rf          # verdict_for: run_fresh's existing verdict (HOLD on any FAIL row)
 236 | +        import run_fresh as rf
 237 |          self.assertEqual(rf.tail_rows(True, True), {"G9_tail": "PASS", "outro_locked": "FAIL"})
 238 | -        self.assertEqual(rf.verdict_for(rf.tail_rows(True, True))[0], rf.VERDICT_HOLD)
 239 | +        self.assertEqual(self.verdict(rf.tail_rows(True, True)), rf.VERDICT_HOLD)
 240 | +
 241 | +    def test_an_outro_that_is_not_hash_identical_fails_outro_locked(self):
 242 | +        """GPT-cut F09: the identity was computed and then ignored; outro_locked now requires it."""
 243 | +        import run_fresh as rf
 244 | +        self.assertEqual(rf.tail_rows(True, False, identical=False), {"G9_tail": "PASS", "outro_locked": "FAIL"})
 245 | +        self.assertEqual(self.verdict(rf.tail_rows(True, False, identical=False)), rf.VERDICT_HOLD)
 246 |  
 247 |      def test_rows_follow_their_own_inputs(self):
 248 |          import run_fresh as rf
 249 |          self.assertEqual(rf.tail_rows(True, False), {"G9_tail": "PASS", "outro_locked": "PASS"})
 250 |          self.assertEqual(rf.tail_rows(False, False), {"G9_tail": "FAIL", "outro_locked": "PASS"})
 251 | -        self.assertEqual(rf.verdict_for(rf.tail_rows(False, False))[0], rf.VERDICT_HOLD)   # luma fail holds
 252 | -        self.assertEqual(rf.verdict_for(rf.tail_rows(True, False))[0], rf.VERDICT_CANDIDATE)
 253 | +        self.assertEqual(self.verdict(rf.tail_rows(False, False)), rf.VERDICT_HOLD)   # luma fail holds
 254 | +        self.assertEqual(self.verdict(rf.tail_rows(True, False)), rf.VERDICT_CANDIDATE)
 255 |  
 256 |  
 257 |  if __name__ == "__main__":
 258 | diff --git a/pipeline/test_fresh.py b/pipeline/test_fresh.py
 259 | index 199fb605..70b0a657 100644
 260 | --- a/pipeline/test_fresh.py
 261 | +++ b/pipeline/test_fresh.py
 262 | @@ -282,15 +282,17 @@ class TestClipContract(unittest.TestCase):
 263 |  
 264 |  class TestRunFreshRules(unittest.TestCase):
 265 |      def test_verdict_rules(self):
 266 | +        """Red-team 2026-11-11 A: the verdict is release_auth's exact inventory. The old prefix rules ('FLAG...',
 267 | +        'LIMITED...' and the '(run_gates)' placeholder passing) are gone: each of them now HOLDS."""
 268 |          from run_fresh import verdict_for, VERDICT_CANDIDATE, VERDICT_HOLD
 269 | -        ok_rows = {"G1_voice": "PASS", "G8_sharpness": "FLAG/LIMITED (x)",
 270 | -                   "G9_tail": "FLAG (APPROVED KNOWN EXCEPTION ...)",
 271 | -                   "G14_frame_similarity": "LIMITED (not valid)",
 272 | -                   "G11_parity(run_gates)": "NOT RUN BY run_gates (no horiz) — see G11 below"}
 273 | -        self.assertEqual(verdict_for(ok_rows)[0], VERDICT_CANDIDATE)
 274 | -        for bad in ("FAIL", "HOLD(inconclusive)", "SKIPPED (no horiz_mp4)",
 275 | -                    "FAIL (fallback occurred)"):
 276 | -            self.assertEqual(verdict_for({**ok_rows, "Gx": bad})[0], VERDICT_HOLD, bad)
 277 | +        from test_release_auth import passing_rows
 278 | +        for fmt in ("16x9", "9x16"):
 279 | +            self.assertEqual(verdict_for(passing_rows()[fmt], fmt)[0], VERDICT_CANDIDATE, fmt)
 280 | +        for row, bad in (("G8_sharpness", "FLAG/LIMITED (x)"), ("G9_tail", "FLAG (APPROVED KNOWN EXCEPTION ...)"),
 281 | +                         ("G18_word_for_word", "FAIL"), ("G16_sentence_boundary", "HOLD(inconclusive)"),
 282 | +                         ("G20_signoff_names_all", "SKIPPED (no horiz_mp4)"), ("G11_parity(run_gates)", "NOT RUN BY run_gates")):
 283 | +            rows = {**passing_rows()["9x16"], row: bad}
 284 | +            self.assertEqual(verdict_for(rows, "9x16")[0], VERDICT_HOLD, (row, bad))
 285 |  
 286 |      def test_no_publishing_path(self):
 287 |          src = open(os.path.join(PIPELINE, "run_fresh.py")).read()
 288 | diff --git a/pipeline/test_word_diff.py b/pipeline/test_word_diff.py
 289 | index 90c0c055..ffe52663 100644
 290 | --- a/pipeline/test_word_diff.py
 291 | +++ b/pipeline/test_word_diff.py
 292 | @@ -27,10 +27,27 @@ class TestCanonical(unittest.TestCase):
 293 |                       ("U .S. Bitcoin ETFs had about $1 .3 billion", "US Bitcoin ETFs had about one point three billion dollars"),
 294 |                       ("around $74 000, around the 50 weekly MA", "around seventy four thousand dollars around the fifty weekly MA"),
 295 |                       ("241 House winners and 50 senators", "two hundred forty one house winners and fifty senators"),
 296 | -                     ("up still 25 % off the lows", "up still twenty five percent off the lows"),
 297 | -                     ("days. Of course, of course, Bitcoin dropped", "days of course bitcoin dropped")):
 298 | +                     ("up still 25 % off the lows", "up still twenty five percent off the lows")):
 299 |              self.assertEqual(W.diff(a, b), [], (a, b))
 300 |  
 301 | +    def test_a_repeat_only_difference_is_kept_as_evidence(self):
 302 | +        """GPT-cut F05: a disfluent repeat rendered differently is NOT removed from the comparison; it is a
 303 | +        repeat-only difference (gone with collapse=True) that gate_g18 decides by the audio (span_matches)."""
 304 | +        a, b = "days. Of course, of course, Bitcoin dropped", "days of course bitcoin dropped"
 305 | +        self.assertNotEqual(W.diff(a, b), [])
 306 | +        self.assertEqual(W.diff(a, b, collapse=True), [])
 307 | +        self.assertNotEqual(W.diff("bitcoin is falling", "bitcoin is falling bitcoin is falling"), [])
 308 | +
 309 | +    def test_units_and_signs_are_not_erased(self):
 310 | +        """GPT-cut F04: five percent vs five dollars, -5% vs +5%, $5 vs 5% differ; only a '$' formatting
 311 | +        difference (whisper writes '$74,000' for a spoken 'seventy-four thousand') is tolerated."""
 312 | +        for a, b in (("bitcoin fell five percent today", "bitcoin fell five dollars today"),
 313 | +                     ("it moved -5% on the day", "it moved +5% on the day"),
 314 | +                     ("it costs $5", "it costs 5%")):
 315 | +            self.assertNotEqual(W.diff(a, b), [], (a, b))
 316 | +        self.assertEqual(W.diff("around $74,000 today", "around 74 000 today"), [])
 317 | +        self.assertEqual(W.diff("it fell -5%", "it fell minus five percent"), [])
 318 | +
 319 |      def test_a_half_written_or_spoken_is_the_same_number(self):
 320 |          """Recut run 6 G18 clip_02: the final was heard as 'five and a half percent', the source span as
 321 |          '5 .5%' (the same audio). Equal both ways; any real difference in the number still counts."""
 322 | @@ -49,9 +66,10 @@ class TestCanonical(unittest.TestCase):
 323 |          d = W.diff("It went from above $81,000 after the election. That was the week.",
 324 |                     "81,000 after the election. That was the week. All right, you've probably seen")
 325 |          self.assertIn(("delete", "it went from above", ""), d)
 326 | -        self.assertIn(("insert", "", "all right you've probably seen"), d)
 327 | +        self.assertIn(("insert", "", "all right you've probably seen"), d)   # canon keeps apostrophes (M1)
 328 |          self.assertEqual(W.diff("the market fell", "the market rose"), [("replace", "fell", "rose")])
 329 | -        self.assertEqual(W.diff("bitcoin fell", "bitcoin fell fell sharply"), [("insert", "", "sharply")])
 330 | +        self.assertEqual(W.diff("bitcoin fell", "bitcoin fell fell sharply"), [("insert", "", "fell sharply")])
 331 | +        self.assertEqual(W.diff("bitcoin fell", "bitcoin fell fell sharply", collapse=True), [("insert", "", "sharply")])
 332 |  
 333 |      def test_edges_compare_the_first_and_last_two_words(self):
 334 |          self.assertEqual(W.edges("But I don't check it. Many times.", "but i don't check it many times"), [])
 335 | @@ -60,6 +78,51 @@ class TestCanonical(unittest.TestCase):
 336 |                           [("start", "it went", "above 81000"), ("end", "last week", "people celebrating")])
 337 |  
 338 |  
 339 | +class TestSpanMatches(unittest.TestCase):
 340 | +    """span_matches (sentence_law): the final's segment IS the source span when, gain removed, no 150 ms run of
 341 | +    speech frames differs by more than 6 dB. Synthetic speech-like bursts; must-pass: the same span with a gain,
 342 | +    a quiet bed and a codec round trip; must-fail: the same span with 300 ms of it repeated (a concat defect)."""
 343 | +
 344 | +    @classmethod
 345 | +    def setUpClass(cls):
 346 | +        import numpy as np
 347 | +        import subprocess
 348 | +        cls.tmp = tempfile.mkdtemp(prefix="span_")
 349 | +        sr, rng = 16000, np.random.default_rng(7)
 350 | +        t = np.arange(int(sr * 6.0)) / sr
 351 | +        env = np.zeros_like(t)
 352 | +        k = 0.2
 353 | +        while k < 5.8:                                       # syllable-like bursts of varying length and level
 354 | +            d = rng.uniform(0.08, 0.25)
 355 | +            env[(t >= k) & (t < k + d)] = rng.uniform(0.2, 0.9)
 356 | +            k += d + rng.uniform(0.05, 0.2)
 357 | +        src = env * np.sin(2 * np.pi * 220 * t) * (1 + 0.3 * np.sin(2 * np.pi * 3 * t))
 358 | +        bed = 0.003 * rng.standard_normal(len(t))
 359 | +
 360 | +        def wav(name, x):
 361 | +            path = os.path.join(cls.tmp, name)
 362 | +            raw = path + ".f32"
 363 | +            x.astype(np.float32).tofile(raw)
 364 | +            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(sr), "-ac", "1", "-i", raw,
 365 | +                            "-c:a", "aac", "-b:a", "192k", path], check=True)
 366 | +            return path
 367 | +        cls.src = wav("src.m4a", src)
 368 | +        cls.same = wav("same.m4a", 0.5 * src + bed)                              # gain + bed + codec
 369 | +        rep = np.concatenate([src[:int(sr * 3.0)], src[int(sr * 2.7):int(sr * 3.0)], src[int(sr * 3.0):]])[:len(src)]
 370 | +        cls.repeat = wav("repeat.m4a", 0.5 * rep + bed)                          # 300 ms repeated at 3.0 s
 371 | +
 372 | +    @classmethod
 373 | +    def tearDownClass(cls):
 374 | +        shutil.rmtree(cls.tmp, ignore_errors=True)
 375 | +
 376 | +    def test_the_same_span_matches_and_a_repeat_does_not(self):
 377 | +        import sentence_law as L
 378 | +        ok, det = L.span_matches(self.src, self.same, 0.0, 5.9, 0.0)
 379 | +        self.assertTrue(ok, det)
 380 | +        ok, det = L.span_matches(self.src, self.repeat, 0.0, 5.9, 0.0)
 381 | +        self.assertFalse(ok, det)
 382 | +
 383 | +
 384 |  def _clips():
 385 |      """Yesterday's three clips: the editor's sentences locked on today's transcripts (as the G16 fixture),
 386 |      and the source span each was cut from."""
 387 | diff --git a/pipeline/word_diff.py b/pipeline/word_diff.py
 388 | index dad11755..386cb7a0 100644
 389 | --- a/pipeline/word_diff.py
 390 | +++ b/pipeline/word_diff.py
 391 | @@ -23,91 +23,17 @@ import tempfile
 392 |  ASR = {"model": "large-v3", "language": "en", "beam_size": 5, "word_timestamps": True, "vad_filter": False}
 393 |  EDGE_WORDS = 2
 394 |  
 395 | -_UNITS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen "
 396 | -                                     "fourteen fifteen sixteen seventeen eighteen nineteen".split())}
 397 | -_TENS = {w: 10 * i for i, w in enumerate("_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()) if w != "_"}
 398 | -_SCALES = {"hundred": 100, "thousand": 1000}   # whisper writes '74,000' but keeps '1.3 billion' as words
 399 | -_AFTER_NUMBER = {"dollars", "dollar", "percent", "per", "cent"}
 400 | -
 401 | -
 402 | -def _spelled_numbers(tokens):
 403 | -    """'seventy four thousand' -> '74000', 'one hundred and twenty' -> '120'. Only a well-formed phrase is
 404 | -    joined: a unit after a unit or after a teen ('one two', 'eleven three') starts a new number, so a
 405 | -    count like 'one two three' stays three tokens (Heimdall: additive joining hid differences)."""
 406 | -    out, i = [], 0
 407 | -    while i < len(tokens):
 408 | -        if tokens[i] in _UNITS or tokens[i] in _TENS:
 409 | -            total, cur, j, last = 0, 0, i, None
 410 | -            while j < len(tokens):
 411 | -                t = tokens[j]
 412 | -                if t in _UNITS:
 413 | -                    if last in ("unit",) or (last == "tens" and _UNITS[t] >= 10):
 414 | -                        break
 415 | -                    cur += _UNITS[t]
 416 | -                    last = "unit"
 417 | -                elif t in _TENS:
 418 | -                    if last in ("unit", "tens"):
 419 | -                        break
 420 | -                    cur += _TENS[t]
 421 | -                    last = "tens"
 422 | -                elif t == "hundred" and last in ("unit",):
 423 | -                    cur *= 100
 424 | -                    last = "hundred"
 425 | -                elif t in _SCALES and t != "hundred" and last is not None:
 426 | -                    total += max(cur, 1) * _SCALES[t]
 427 | -                    cur, last = 0, "scale"
 428 | -                elif (t == "and" and last in ("hundred", "scale") and j + 1 < len(tokens)
 429 | -                      and (tokens[j + 1] in _UNITS or tokens[j + 1] in _TENS)):
 430 | -                    last = "and"
 431 | -                else:
 432 | -                    break
 433 | -                j += 1
 434 | -            out.append(str(total + cur))
 435 | -            i = j
 436 | -        else:
 437 | -            out.append(tokens[i])
 438 | -            i += 1
 439 | -    return out
 440 | -
 441 | -
 442 | -_NUM = re.compile(r"\d+(p\d+)?")
 443 | -
 444 | -
 445 | -def _decimals(tokens):
 446 | -    """Spoken decimals as the written form's single token: 'one point three' -> '1p3' (like '1.3'), and
 447 | -    'five and a half' -> '5p5' (like '5.5'; recut run 6 G18: '5 .5%' vs 'five and a half percent', the same
 448 | -    audio). Only after a number: 'a year and a half' stays words. Before 2026-11-11 a decimal split into
 449 | -    two digit tokens and the repeat-collapser then merged '5 5' into '5', so 5.5 % and 5 % compared equal."""
 450 | -    out, k = [], 0
 451 | -    while k < len(tokens):
 452 | -        w = tokens[k]
 453 | -        if w.isdigit() and tokens[k + 1:k + 2] == ["point"] and k + 2 < len(tokens) and tokens[k + 2].isdigit():
 454 | -            out.append(f"{w}p{tokens[k + 2]}")
 455 | -            k += 3
 456 | -        elif w.isdigit() and tokens[k + 1:k + 4] == ["and", "a", "half"]:
 457 | -            out.append(f"{w}p5")
 458 | -            k += 4
 459 | -        else:
 460 | -            out.append(w)
 461 | -            k += 1
 462 | -    return out
 463 | -
 464 | -
 465 | -def norm(text):
 466 | -    t = (text or "").lower().replace("’", "'")
 467 | -    t = re.sub(r"(\d)\s+([.,]\d)", r"\1\2", t)            # '88 ,000' -> '88,000', '1 .3' -> '1.3'
 468 | -    t = re.sub(r"(\d)\s+(?=\d{3}\b)", r"\1", t)             # '74 000' -> '74000'
 469 | -    t = re.sub(r"\$\s+(\d)", r"$\1", t)
 470 | -    t = re.sub(r"\b(\w)\s+\.(?=\w)", r"\1.", t)              # 'u .s.' -> 'u.s.'
 471 | -    t = re.sub(r"\b([a-z])\.(?=[a-z]\b)", r"\1", t)            # 'u.s.' -> 'us.' (single-letter abbreviations)
 472 | -    t = re.sub(r"(?<=\d)[,](?=\d{3}\b)", "", t)             # '74,000' -> '74000'
 473 | -    t = re.sub(r"(?<=\d)\.(?=\d)", "p", t)                   # '5.5' -> '5p5': a decimal stays ONE token
 474 | -    t = re.sub(r"[^\w\s']", " ", t)                         # punctuation, '$', '%' (both sides alike)
 475 | -    t = re.sub(r"(?<!\w)'|'(?!\w)", "", t)                  # quote marks, not apostrophes
 476 | -    tokens = _decimals(_spelled_numbers(t.split()))          # 'one point three' / 'five and a half' -> '1p3' / '5p5'
 477 | -    tokens = [w for k, w in enumerate(tokens) if not (w in _AFTER_NUMBER and k and (
 478 | -        _NUM.fullmatch(tokens[k - 1]) or tokens[k - 1] in ("million", "billion", "trillion")))]
 479 | -    return _collapse_repeats(tokens)
 480 | +def norm(text, collapse=False):
 481 | +    """G18's comparison form: the pipeline's one canonical form (pipeline/canon.py: case, punctuation, split number
 482 | +    fragments, spelled numbers, decimals, currency / percent, signs), then G18's one tolerance, both sides alike:
 483 | +    'dollars' right after a number is dropped (whisper writes '$74,000' for a spoken 'seventy-four thousand';
 484 | +    '5 percent' vs '5 dollars' still differ: GPT-cut F04). collapse=True also folds immediate repeats of 1-3
 485 | +    words ('of course of course'); a difference that only that removes is NOT dropped from the evidence: G18
 486 | +    adjudicates it acoustically (GPT-cut F05, gate_g18)."""
 487 | +    import canon
 488 | +    t = canon.canon_tokens(text)
 489 | +    t = [w for k, w in enumerate(t) if not (w == "dollars" and k and re.fullmatch(r"\d+(\.\d+)?", t[k - 1]))]
 490 | +    return _collapse_repeats(t) if collapse else t
 491 |  
 492 |  
 493 |  def _collapse_repeats(tokens):
 494 | @@ -121,9 +47,9 @@ def _collapse_repeats(tokens):
 495 |      return out
 496 |  
 497 |  
 498 | -def diff(expected, heard):
 499 | +def diff(expected, heard, collapse=False):
 500 |      """Word-level differences [(op, expected_words, heard_words)] after canonicalisation; [] if equal."""
 501 | -    e, h = norm(expected), norm(heard)
 502 | +    e, h = norm(expected, collapse), norm(heard, collapse)
 503 |      out = []
 504 |      for op, a0, a1, b0, b1 in difflib.SequenceMatcher(None, e, h, autojunk=False).get_opcodes():
 505 |          if op != "equal":
 506 | @@ -180,6 +106,18 @@ def gate_g18(final_path, segments, clips, transcriber=None):
 507 |          row = {"segment": label, "heard": heard, "source_span_heard": src, "lock_text": c["lock_text"],
 508 |                 "edges": edges(c["lock_text"], heard), "identity": diff(src, heard),
 509 |                 "lock_diff_reported": diff(c["lock_text"], heard)}
 510 | +        if row["identity"] and not diff(src, heard, collapse=True):
 511 | +            # only repeats differ (two whisper passes render a disfluent repeat differently, Nov 10 fixture): the
 512 | +            # difference stays in the row and is decided by the audio: the final's segment must BE the source span
 513 | +            import sentence_law as L
 514 | +            try:
 515 | +                same, det = L.span_matches(c["source"], final_path, c["cut_in"], c["cut_out"], float(seg["start"]),
 516 | +                                           float(c.get("pad_s") or 0.0))
 517 | +            except Exception as e:                   # not measurable: the difference stands
 518 | +                same, det = False, {"why": f"{type(e).__name__}: {e}"}
 519 | +            row["repeat_only_adjudication"] = {"same_audio": same, **det}
 520 | +            if same:
 521 | +                row["identity_repeats_only"], row["identity"] = row["identity"], []
 522 |          row["pass"] = not row["edges"] and not row["identity"]
 523 |          ok_all &= row["pass"]
 524 |          rows.append(row)
 525 | 
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
