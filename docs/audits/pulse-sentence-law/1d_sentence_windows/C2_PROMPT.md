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
The changed functions (`_ends_statement`, `_n_sentences`, `_word_sentences`, `start_is_boundary`, `anchored_window`, `expanded_window`, `repair_window`, and the new fallback path in `select_passages.py`) match their docstrings and the sentence-boundary rules shown in the diff. All terminal checks now route through `sentence_law.is_terminal` (lines 22, 42, 52, 67, 97, 106, 124). No path in the diff produces a PASS or sealed window when data is missing; `_source_for` returns a rejection string and `_fill` skips the segment. No off-by-one in sentence indexing or duration math is visible. Imports inside functions (lines 21, 38, 51, 175) are present but do not alter control flow.

**Q2: LAW COMPLIANCE**  
- SENTENCE LAW / SNAP LIMIT / SELECTION LOCK: COMPLIANT (lines 60, 75, 87, 114, 166-168, 232-239). Windows are built only from whole sentences; selection_lock is written after verification; cuts are never moved.  
- ONSET/TAIL / CREDITS / M12 FAIL CLOSED: no changes in this diff, so unaffected.  
- LAW 20 / M2 (thresholds frozen): PARTIAL — `CLIP_MIN_S`/`CLIP_MAX_S` changed (line 10) and `MAX_WINDOW_SENTENCES` added (line 11). These are budget constants, not gate-acceptance thresholds, but the change alters what the editor will accept.  
- LAW 22 / v2f reference: no renderer changes visible.  
- No path recomputes first/last words after the lock or moves a cut outside the locked sentence's silence.

**Q3: TESTS**  
`test_sentence_windows.py` (new) and the updates to `test_window_review.py` exercise the exact claims: abbreviation/ellipsis handling (lines 271-284), budget enforcement (lines 293-306), next-ranked fallback (lines 336-378), and the three-sentence cap (lines 420-431). Assertions are specific (exact tuples, presence of rejection strings, `n_sentences <= 3`). No vacuous passes; the “must-fail” cases are rejected for the documented reasons (start boundary, sentence count, missing pause). Controls pass only after the legal replacement window is chosen.

**Q4: VERDICT**  
- MINOR | line 10 | CLIP_MIN_S lowered from 13.0 to 12.0 (and MAX_S to 20.0) | Document the change as an explicit, one-time budget adjustment required by sentence alignment; do not treat as precedent for future threshold edits.  
- MINOR | lines 21,38,51 | Repeated `import sentence_law` inside functions | Move to module level to avoid repeated import cost and potential circular-import surprises.  
- MINOR | line 29 | Reliance on `INTERJECTIONS` and `_lc_words` (pre-existing symbols) | Confirm they remain defined and unchanged outside this diff.  

No defects block the stated laws or produce false passes.  
**READY**

## GPT4O — CYCLE 1 OUTPUT
### Q1: CORRECTNESS

1. **Function `_ends_statement`**: This function checks if a word ends a statement by looking for terminal punctuation (lines 19-22). It correctly excludes questions and abbreviations, which aligns with its docstring.

2. **Function `_n_sentences`**: This function counts sentences between two indices, excluding interjections (lines 25-30). It appears to correctly implement the logic described in the docstring.

3. **Function `_word_sentences`**: This function identifies sentence boundaries based on terminal punctuation, excluding abbreviations (lines 33-46). It uses `sentence_law.is_terminal` to determine sentence ends, which should handle punctuation correctly.

4. **Function `start_is_boundary`**: This function checks if a sentence start is a valid boundary (lines 46-55). It uses `sentence_law.is_terminal` to verify terminal punctuation, which should be correct.

5. **Function `anchored_window`**: This function checks if a window is valid based on sentence boundaries and duration constraints (lines 56-70). It uses `_ends_statement` to ensure the window ends on a valid statement end, which aligns with the requirements.

6. **Function `expanded_window`**: This function attempts to expand a window while respecting sentence and duration limits (lines 71-99). It correctly uses `_n_sentences` and `_ends_statement` to enforce constraints.

7. **Function `repair_window`**: This function repairs a window by adjusting its boundaries (lines 101-126). It uses `_ends_statement` to ensure the window ends correctly, which is consistent with its purpose.

8. **Function `_clip_quality`**: This function adds a "kind" attribute to the output dictionary (lines 128-136). This change seems unrelated to sentence law but does not introduce correctness issues.

9. **Function `select_and_build_edl`**: This function selects and builds an EDL, replacing rejected windows with the next-ranked legal candidate (lines 141-242). It uses `_fill` to ensure replacements are legal, which aligns with the requirements.

Overall, the functions appear to correctly implement their intended logic, and there are no obvious issues with time/index handling, units, or state leakage.

### Q2: LAW COMPLIANCE

1. **SENTENCE LAW**: COMPLIANT. The changes ensure that clips start and end on sentence boundaries, using terminal punctuation and acoustic pauses (lines 19-22, 33-46, 56-70, 71-99, 101-126).

2. **SELECTION LOCK**: COMPLIANT. The selection lock is respected, and expected words are not recomputed after selection (lines 141-242).

3. **SNAP LIMIT**: COMPLIANT. The changes ensure that cuts do not move outside the locked sentence's silence (lines 56-70, 71-99, 101-126).

4. **ONSET/TAIL**: COMPLIANT. The changes do not affect onset/tail requirements, which are presumably handled elsewhere.

5. **CREDITS**: NOT APPLICABLE. The diff does not involve credits.

6. **LAW 20 / M2**: COMPLIANT. Gate thresholds are constants, and there is no evidence of threshold loosening (lines 141-242).

7. **M12 FAIL CLOSED**: COMPLIANT. Missing data or model failures result in rejection, not a pass (lines 141-242).

8. **LAW 22**: COMPLIANT. There is no indication that the v2f reference path would behave differently.

### Q3: TESTS

1. **Must-fail fixtures**: The tests include scenarios where windows are rejected for exceeding sentence limits or ending incorrectly (lines 287-307, 335-379). These tests should fail for the right reasons.

2. **Controls**: Tests for valid scenarios, such as correct sentence counting and boundary detection, should pass for the right reasons (lines 270-285, 287-307).

3. **Assertions**: The assertions appear to be meaningful and not vacuous. They check specific conditions related to sentence boundaries and window validity.

### Q4: VERDICT

- **SEVERITY: LOW** | No specific line | The change to `_clip_quality` (lines 128-136) seems unrelated to sentence law but does not introduce correctness issues. No fix needed.
- **SEVERITY: LOW** | No specific line | The diff does not address credits, but this is not required for the current scope.

Overall, the changes are READY for integration, as they comply with the laws and are supported by appropriate tests.

## GEMINI — CYCLE 1 OUTPUT
Excellent, this is a comprehensive quality gate package. I will perform the requested code audit as an independent AI model.

---

### Q1: CORRECTNESS

The changed functions appear to do what their docstrings and surrounding comments claim. The logic seems sound and consistently applied.

1.  **`editorial_select.py`**:
    *   The new functions `_ends_statement` (l. 19) and `_n_sentences` (l. 25) correctly implement the new editorial rules: ending on a statement (not a question) and capping the total number of sentences (while ignoring interjections).
    *   The use of a centralized `sentence_law.is_terminal` function (l. 42, 52) is a good practice, replacing scattered `endswith()` checks and correctly handling cases like "U.S." as per the new tests.
    *   The `MAX_WINDOW_SENTENCES` constraint is correctly checked in all functions that create or modify a window: `anchored_window` (l. 60), `expanded_window` (l. 75, 87), and `repair_window` (l. 114).
    *   The change to clip duration budget (`CLIP_MAX_S` from 25.0 to 20.0, l. 10) is consistently reflected in the updated tests (e.g., l. 411).
    *   Adding `"kind"` to the output of `_clip_quality` (l. 133) is a necessary and correct change to support the new fallback logic in `select_passages.py`.

2.  **`select_passages.py`**:
    *   The new "Next-ranked fallback" logic (l. 172-229) is the core of this feature and appears correct. The `_fill` function (l. 212) correctly attempts the primary candidate first, then iterates through a sorted list of alternatives.
    *   The `_eligible` function (l. 183) correctly checks all documented constraints for a fallback candidate (kind, score, duration, non-overlap, per-video/per-channel limits).
    *   **M12 FAIL CLOSED Compliance:** The logic correctly handles failures. If `_source_for` fails to download or transcribe (l. 201, 205), it returns an error string, and the candidate is skipped. If `_build_segment` returns `None` (indicating a Sentence Law violation or other problem), the `if seg is not None:` check (l. 226) prevents the invalid segment from being used, and `_fill` moves to the next candidate. This correctly prevents a pass on missing data or model failure.

There are no obvious off-by-one errors, unit mix-ups, or state leakage between clips. The logic appears robust. A minor uncertainty is the implementation of `sentence_law.py`, as it is not included in the diff. However, its behavior is well-defined by the new tests (`test_abbreviation_is_not_a_sentence_end`, `test_trailing_ellipsis_is_not_a_sentence_end`), which provides high confidence in its correct usage here.

### Q2: LAW COMPLIANCE

The code is largely compliant, with one point of uncertainty.

*   **SENTENCE LAW**: **COMPLIANT**. The entire change is designed to enforce this law. `editorial_select.py` now defines windows in terms of whole sentences (l. 60, 75, 87, 114) and uses a dedicated function `_ends_statement` (l. 19) for boundary checks. The acoustic pause requirement is implicitly enforced: `select_passages.py` calls `_build_segment`, which will fail if no legal cut point (with the required pause) is found, triggering the fallback mechanism.
*   **SELECTION LOCK**: **COMPLIANT**. The new fallback logic in `select_passages.py` (l. 172-229) replaces an *entire proposed window* with another *entire proposed window* from the selection pool. It does not move the cut points of a selected window or recompute its expected words. The selection lock is created on the final, validated window inside `_build_segment`.
*   **SNAP LIMIT**: **COMPLIANT**. The logic adheres to this law by rejecting invalid windows instead of moving their cuts. A window that fails boundary checks is discarded, and a fallback is sought (l. 212-229).
*   **ONSET/TAIL**: **COMPLIANT**. This law applies to the rendering stage. These changes are in the selection stage, but they support this law by ensuring that selected boundaries have a required acoustic pause, making it possible for the renderer to include the required sub-speech audio.
*   **CREDITS**: **COMPLIANT**. No code in the diff relates to avatars or credits.
*   **LAW 20 / M2**: **COMPLIANT**. New gate thresholds (`MAX_WINDOW_SENTENCES`, l. 11) are introduced as constants. Existing thresholds are tightened (`CLIP_MAX_S`, l. 10). No logic loosens a check to make a render pass.
*   **M12 FAIL CLOSED**: **COMPLIANT**. As noted in Q1, download, transcription, or boundary check failures lead to candidate rejection, not a pass (l. 218-228).
*   **LAW 22**: **UNCERTAIN / PARTIAL**. The law requires the v2f reference to re-render byte-identically. The changes in `select_passages.py` (l. 153-164) include a legacy path for `passages.json` files that do not have the `kind` field. If the v2f reference data uses this legacy format, it will be processed by the old selection logic which is preserved inside the `else` block. While this logic is preserved, the functions it calls (`_build_segment`, etc.) now contain the new, st

## CLAUDE'S CYCLE 1 CONSENSUS
# CONSENSUS REPORT — PULSE-SENTENCE-LAW — CYCLE 1
Generated: 2026-11-11 03:21
Models: grok, gpt4o, gemini

---

## SCORES

No model produced a numeric score table. Scores are inferred from verdict language and severity of issues raised.

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Correctness | 9/10 | 9/10 | 9/10 | 9/10 |
| Law Compliance | 7/10 | 9/10 | 8/10 | 8/10 |
| Test Quality | 10/10 | 9/10 | 9/10 | 9/10 |
| Overall Readiness | 7/10 | 9/10 | 8/10 | 8/10 |

*Gemini's score is dragged down by the unresolved LAW 22 concern. GPT-4o did not raise it; Grok did not raise it. See CONFLICTS.*

---

## UNANIMOUS FINDINGS (all 3 models agree — implement unconditionally)

### U1 — Module-level imports for `sentence_law`
**What:** `import sentence_law` is repeated inside function bodies (lines 21, 38, 51, 175 of `editorial_select.py`). All three models either flagged it directly (Grok: MINOR, lines 21/38/51) or implicitly endorsed the centralization of `sentence_law` calls as good practice (Gemini, GPT-4o). The concern is repeated import overhead and latent circular-import risk.
**File/Line:** `editorial_select.py`, lines 21, 38, 51, 175
**Change:** Hoist all `import sentence_law` to the module-level import block at the top of `editorial_select.py`. Remove the per-function occurrences.

---

### U2 — All window-building paths enforce `MAX_WINDOW_SENTENCES`
**What:** All three models confirmed that `MAX_WINDOW_SENTENCES` is correctly checked in `anchored_window`, `expanded_window`, and `repair_window`. This is a **validated strength** (see that section), but the unanimous agreement also constitutes a finding: no additional enforcement sites are needed. No action required beyond the confirmation itself.

---

## MAJORITY FINDINGS (2 of 3 models agree)

### M1 — `CLIP_MIN_S`/`CLIP_MAX_S` budget change requires explicit documentation
**Models:** Grok (MINOR, line 10), Gemini (noted in correctness, line 10)
**What:** `CLIP_MIN_S` was lowered from 13.0 → 12.0 and `CLIP_MAX_S` from 25.0 → 20.0. Grok notes these are budget constants, not gate-acceptance thresholds, but the change still alters accepted clip range. Gemini confirms the tests reflect the new values. GPT-4o did not flag this.
**File/Line:** `editorial_select.py`, line 10
**Change:** Add an inline comment at line 10 clearly stating this is a deliberate, one-time adjustment required by sentence-alignment geometry (shorter legal windows mean the old 25 s ceiling produced near-empty expansions). Include the previous values in the comment so git blame is self-documenting. Example:

```python
# Budget narrowed 2026-11-11 for sentence-law alignment (was 13.0–25.0).
# Sentence-boundary geometry makes >20 s windows rare; raising the floor
# to 12 s prevents sub-sentence slivers. Do not adjust without a law review.
CLIP_MIN_S = 12.0
CLIP_MAX_S = 20.0
```

Do **not** treat as precedent for ad-hoc threshold edits. This change is already in the diff; the action is purely documenta

---

## ORIGINAL CODE (same code as Cycle 1)
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
