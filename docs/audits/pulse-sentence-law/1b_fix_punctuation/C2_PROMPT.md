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
- `punctuation.transfer` (lines 39-51) and `ensure` (61-70) only copy trailing punctuation onto aligned verbatim words via `difflib.SequenceMatcher` matching blocks; the assert at line 67 and `_key` normalisation guarantee words and timings are unchanged.  
- `sentence_law.boundary` (318-348) now returns `valid=False` + "unpunctuated" for any stretch lacking terminal marks (342-344); `edge_plan`/`gate_g16`/`write_lock_cut_table` call sites were updated to drop the `adj` argument (351-357, 365, 383). No path can produce a PASS when punctuation is absent or a model call would have been required. No unit, index, or exception-handling defects visible in the diff.

**Q2: LAW COMPLIANCE**  
- SENTENCE LAW: COMPLIANT (lines 342-344, 223-227).  
- SELECTION LOCK / SNAP LIMIT: COMPLIANT — locks are read-only after selection (196-197, 376-378); cuts stay inside the pause of the locked sentence.  
- No gate threshold changed, no v2f path altered, no recomputation of expected words after selection. All other listed laws are untouched by this diff.

**Q3: TESTS**  
Yes.  
- `TestUnpunctuatedTranscript` (483-513) and `TestPunctuationLayer` (528-567) exercise the exact failure modes (unpunctuated gaps, adjudicator false positives, mark transfer only on aligned words).  
- Assertions are specific (e.g., 451-452, 506-507, 539-540) and would fail if the new logic were inverted. No vacuous passes.

**Q4: VERDICT**  
No defects found.  
READY

## GPT4O — CYCLE 1 OUTPUT
### Q1: CORRECTNESS

1. **Functionality of `transfer` (lines 39-51):**
   - The function `transfer` aligns words from a reference decode to a verbatim decode and transfers punctuation marks. It correctly uses `difflib.SequenceMatcher` to find matching blocks and transfers punctuation only when the words match. The function ensures that words themselves do not change, complying with the docstring and laws.

2. **Functionality of `reference_decode` (lines 54-58):**
   - This function performs a reference decode using a model with a specific prompt. It returns words with punctuation. The function appears to perform as expected, with no off-by-one errors or incorrect units.

3. **Functionality of `ensure` (lines 61-70):**
   - This function checks if punctuation needs restoration and applies it using the `transfer` function. It ensures that the words themselves do not change, only punctuation is added. The function handles missing punctuation correctly by returning early if no restoration is needed.

4. **Functionality of `boundary` (lines 318-348):**
   - The function checks for sentence boundaries based on punctuation and pauses. It correctly handles unpunctuated stretches by failing closed, as per the laws. There are no off-by-one errors or incorrect units.

5. **Functionality of `edge_plan` (lines 351-358):**
   - This function calculates boundaries around selected words and checks their validity. It no longer uses an adjudicator and relies solely on punctuation and pauses, aligning with the updated laws.

6. **Handling of missing data or model failures:**
   - The code does not produce a pass when data is missing or a model fails, complying with M12 FAIL CLOSED. Functions like `ensure` and `boundary` handle missing punctuation by failing closed.

### Q2: LAW COMPLIANCE

1. **SENTENCE LAW: COMPLIANT**
   - Lines 318-348: The `boundary` function ensures that sentence boundaries are determined by punctuation and pauses, not by language models.

2. **SELECTION LOCK: COMPLIANT**
   - No evidence in the diff of recomputing expected words after selection.

3. **SNAP LIMIT: COMPLIANT**
   - The `boundary` function (lines 318-348) ensures cuts are within legal boundaries.

4. **ONSET/TAIL: COMPLIANT**
   - The laws regarding onset and tail are not directly modified in this diff, but the functions handling boundaries ensure compliance indirectly.

5. **CREDITS: NOT APPLICABLE**
   - No changes related to credits in this diff.

6. **LAW 20 / M2: COMPLIANT**
   - No gate thresholds are changed in the diff.

7. **M12 FAIL CLOSED: COMPLIANT**
   - Functions handle missing data by failing closed, as seen in `ensure` and `boundary`.

8. **LAW 22: COMPLIANT**
   - No changes to the v2f reference path behavior are evident in the diff.

### Q3: TESTS

1. **Must-fail fixtures:**
   - Lines 463-567: Tests like `TestUnpunctuatedTranscript` and `TestPunctuationLayer` ensure that unpunctuated gaps do not pass as sentence boundaries, complying with the updated laws.

2. **Control tests:**
   - Tests ensure that valid sentence boundaries are recognized correctly, and punctuation is applied as expected.

3. **Assertions:**
   - Assertions are specific and not vacuous, checking for correct reasons for pass/fail conditions.

### Q4: VERDICT

1. **SEVERITY: LOW | Line 318-348 | Issue: None | Fix: None needed.**
   - The `boundary` function correctly implements the updated laws.

2. **SEVERITY: LOW | Line 61-70 | Issue: None | Fix: None needed.**
   - The `ensure` function correctly handles punctuation restoration.

3. **SEVERITY: LOW | Line 39-51 | Issue: None | Fix: None needed.**
   - The `transfer` function correctly aligns and transfers punctuation.

**READY**: The code changes are compliant with the laws, and the tests adequately cover the updated functionality.

## GEMINI — CYCLE 1 OUTPUT
Excellent. I will now review the code for the `pulse-sentence-law` feature.

---

### Q1: CORRECTNESS

The code appears to be of high quality and logically sound. The changed functions do what their docstrings and the feature description imply.

1.  **`pipeline/punctuation.py`:** This new module correctly implements the described strategy.
    *   `_key()` (line 30) correctly normalizes words for comparison, ignoring case and punctuation.
    *   `transfer()` (line 39) is the core of the logic. It correctly uses `difflib.SequenceMatcher` to find blocks of words that are identical (post-normalization) between the verbatim and reference transcripts. It only transfers trailing punctuation to words in these aligned blocks, and only if the verbatim word doesn't already have punctuation. This is a robust way to prevent corruption.
    *   The use of `out = [dict(w) for w in words]` (line 42) ensures the original word list is not mutated, which is good practice.
    *   The assertion `assert [_key(w["word"]) for w in words] == [_key(w["word"]) for w in record["words"]]` (line 67) is a critical correctness check. It programmatically guarantees that the process only adds punctuation and never changes the underlying words, which is essential for `SELECTION LOCK`.
    *   The `ensure()` function (line 61) correctly includes a fast path to skip processing for transcripts that are already punctuated, which is efficient.

2.  **`pipeline/sentence_law.py`:** The changes here are primarily removals and simplifications, which improve correctness by eliminating a faulty component.
    *   The `Adjudicator` class, identified as the source of errors, has been completely removed (lines 252-313).
    *   The `boundary()` function (line 318) is now simpler and more robust. The logic `if not is_punctuated(words, k): return {..., "valid": False, ...}` (lines 342-344) correctly implements the "fail closed" principle for unpunctuated sections. This removes the dependency on the unreliable LLM and replaces it with a deterministic, safer rule.

3.  **Error Handling & State:**
    *   The system upholds the **M12 FAIL CLOSED** law. If the ASR model in `punctuation.py` fails, it will raise an exception, halting the pipeline instead of producing a corrupt transcript and a false pass. Likewise, the new `boundary()` logic explicitly fails on missing data (i.e., missing punctuation).
    *   There is no apparent state leakage between clips. The removal of the `Adjudicator` instance, which was passed around, actually reduces the potential for such issues.

I find no issues with correctness in this diff. The logic is sound, well-tested, and includes strong internal assertions.

### Q2: LAW COMPLIANCE

The code appears to be fully compliant with all specified laws.

*   **SENTENCE LAW:** **COMPLIANT.** The diff directly implements a stricter and more reliable version of this law. The removal of the LLM adjudicator (diff lines 252-313) and the introduction of the "fail closed" rule for unpunctuated stretches (lines 222-225, 342-344) directly address the reported failures. Punctuation is now derived deterministically from a second ASR pass.
*   **SELECTION LOCK:** **COMPLIANT.** The lock is respected. Words are not recomputed. The new `punctuation.py` module is explicitly designed to preserve the original words, as proven by the assertion on line 67. This ensures that timings and word sequences from the original verbatim transcript remain unchanged.
*   **SNAP LIMIT:** **COMPLIANT.** The logic for placing cuts within a valid pause is unchanged. By making the definition of a "legal boundary" stricter, this law is now enforced more rigorously, as cuts can no longer be planned around the erroneous boundaries previously approved by the adjudicator.
*   **ONSET/TAIL:** **COMPLIANT.** The laws themselves are not modified, but the tests now correctly fail clips that violate them (e.g., test `TestD1HookOnset` on lines 439-449), demonstrating that the improved boundary detection allows these gates to function as intended.
*   **CREDITS:** **COMPLIANT.** This law is not relevant to the changes in this diff. The code does not touch avatar or credit generation.
*   **LAW 20 / M2:** **COMPLIANT.** No gate thresholds have been loosened. The criteria for a valid sentence boundary have been significantly tightened by removing the adjudicator and requiring explicit punctuation. This is the opposite of loosening a threshold.
*   **M12 FAIL CLOSED:** **COMPLIANT.** This is a core design principle of the change. Missing punctuation in a transcript stretch now results in a "fail" for any boundary check within it (line 343). An ASR or other model failure during punctuation restoration will raise an exception, which constitutes a rejection.
*   **LAW 22:** **COMPLIANT.** No rendering code is changed. The `v2f` reference path should re-render identically. This change affects clip selection and boundary validation, which happen *before* rendering. The reference asset, as

## CLAUDE'S CYCLE 1 CONSENSUS
# CONSENSUS REPORT — PULSE-SENTENCE-LAW — CYCLE 1
Generated: 2026-11-11 05:16
Models: grok, gpt4o, gemini

---

## SCORES

All three models evaluated Q1–Q4 qualitatively rather than numerically. Scores are inferred from language confidence and finding severity.

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Q1 Correctness | 10/10 | 9/10 | 10/10 | **10/10** |
| Q2 Law Compliance | 10/10 | 10/10 | 10/10 | **10/10** |
| Q3 Test Quality | 10/10 | 9/10 | 10/10 | **10/10** |
| Q4 Overall Verdict | READY | READY | READY | **READY** |
| **Composite** | **10/10** | **9.5/10** | **10/10** | **9.8/10** |

> **Score basis:** Gemini provided the most granular analysis with explicit line-level reasoning. GPT-4o produced a structurally complete review but was lighter on deep reasoning for individual functions. Grok was terse but precise. No model found a defect; GPT-4o added one additional LOW severity note (non-actionable) relative to the others.

---

## UNANIMOUS FINDINGS (all 3 models agree — implement unconditionally)

**None.**

All three models independently found zero defects, zero correctness issues, zero law violations, and zero test gaps. There is nothing all three models agree *needs to change*.

This is an unusual but valid outcome for a cycle audit: unanimous "no defects found."

---

## MAJORITY FINDINGS (2 of 3 models agree)

**None.**

No issue was raised by even two models. Every observation across all three outputs was positive confirmation of correct behavior.

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### U1 — Gemini only: `_key()` normalization is a critical correctness dependency
**File:** `pipeline/punctuation.py`, line 30
**Observation:** Gemini specifically called out that `_key()` normalizes for case and punctuation before comparison, which is what makes `SequenceMatcher` alignment reliable across verbatim vs. reference decodes. If `_key()` is ever changed (e.g., to strip additional characters or change Unicode normalization), alignment could silently degrade without any test catching it.
**Assessment:** **Investigate further / add regression guard.** This is not a defect today, but `_key()` is a load-bearing function with no dedicated unit test isolating its normalization contract. A future maintainer could break it accidentally. Recommend adding an explicit unit test asserting that `_key("Hello,") == _key("hello")` and similar edge cases (apostrophes, em-dashes, Unicode punctuation).
**Priority: P2**

### U2 — Gemini only: State leakage risk reduction from Adjudicator removal
**File:** `pipeline/sentence_law.py`, removed lines 252–313
**Observation:** Gemini noted that removing the `Adjudicator` instance (which was passed between functions) also eliminates a category of potential state-leakage bugs between clips. This is a maintenance-class observation, not a current defect.
**Assessment:** **Skip** — no action needed. The removal already happened; this is confirmatory anal

---

## ORIGINAL CODE (same code as Cycle 1)
## THE CODE (every new and modified file)

### File: docs/audits/pulse-sentence-law/CURRENT.diff (571 lines)
```
   1 | diff --git a/pipeline/punctuation.py b/pipeline/punctuation.py
   2 | new file mode 100644
   3 | index 00000000..6166ef14
   4 | --- /dev/null
   5 | +++ b/pipeline/punctuation.py
   6 | @@ -0,0 +1,64 @@
   7 | +#!/usr/bin/env python3
   8 | +"""pipeline/punctuation.py — sentence punctuation for VERBATIM transcripts (sentence law, 2026-11-11).
   9 | +
  10 | +Whisper sometimes decodes a whole window without punctuation (Yahoo Finance, Nov 10: 140 lowercase words,
  11 | +no mark). The sentence law needs to know where sentences end. The verbatim decode's WORDS stay exactly
  12 | +as they are (selection locks, edge-word timings and G18 need every spoken word; a prompted decode drops
  13 | +disfluent repetitions such as Yahoo's "of course of course"). Only punctuation is taken from a second
  14 | +decode of the same audio steered by a neutral punctuated prompt, and only onto words both decodes agree
  15 | +on (difflib alignment of normalised word keys). Words the decodes disagree on get no punctuation, so no
  16 | +sentence boundary can come from them (fail closed: the window is rejected, the next-ranked one is tried).
  17 | +
  18 | +Replaces the per-gap language-model adjudicator, which called 19 of 19 Yahoo gaps sentence ends,
  19 | +'the | Wolf' and 'of | all' included (E-FAIL-013).
  20 | +"""
  21 | +import difflib
  22 | +import re
  23 | +
  24 | +import sentence_law as L
  25 | +
  26 | +PROMPT = "Hello, and welcome. Here is the next part of the conversation."
  27 | +TRAIL = re.compile(r"[.,!?;:]+$")
  28 | +
  29 | +
  30 | +def _key(word):
  31 | +    return re.sub(r"[^a-z0-9']", "", (word or "").lower().replace("’", "'"))
  32 | +
  33 | +
  34 | +def needs_restoration(words):
  35 | +    """True when any word sits in a stretch the sentence law reads as unpunctuated."""
  36 | +    return any(not L.is_punctuated(words, k) for k in range(len(words)))
  37 | +
  38 | +
  39 | +def transfer(words, ref):
  40 | +    """Copy each reference word's trailing punctuation onto the aligned verbatim word (equal blocks
  41 | +    only; a verbatim word keeps its own punctuation). Returns (new words, marks moved)."""
  42 | +    a, b = [_key(w["word"]) for w in words], [_key(w["word"]) for w in ref]
  43 | +    out, moved = [dict(w) for w in words], 0
  44 | +    for blk in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
  45 | +        for j in range(blk.size):
  46 | +            w, r = out[blk.a + j], ref[blk.b + j]
  47 | +            m = TRAIL.search(r["word"].strip())
  48 | +            if a[blk.a + j] and m and not TRAIL.search(w["word"].strip()):
  49 | +                w["word"] = w["word"].strip() + m.group(0)
  50 | +                moved += 1
  51 | +    return out, moved
  52 | +
  53 | +
  54 | +def reference_decode(source_path, model):
  55 | +    """The punctuation reference: the same ASR settings as the verbatim decode, plus PROMPT."""
  56 | +    segs, _ = model.transcribe(source_path, language="en", beam_size=5, word_timestamps=True,
  57 | +                               vad_filter=False, initial_prompt=PROMPT)
  58 | +    return [{"word": w.word.strip()} for s in segs for w in (s.words or [])]
  59 | +
  60 | +
  61 | +def ensure(record, source_path, model):
  62 | +    """The transcript record with sentence punctuation. Verbatim word keys never change."""
  63 | +    if record.get("punctuation") or not needs_restoration(record["words"]):
  64 | +        return record
  65 | +    ref = reference_decode(source_path, model)
  66 | +    words, moved = transfer(record["words"], ref)
  67 | +    assert [_key(w["word"]) for w in words] == [_key(w["word"]) for w in record["words"]]
  68 | +    return dict(record, words=words, punctuation={
  69 | +        "source": "asr_reference", "model": "large-v3", "prompt": PROMPT, "marks_transferred": moved,
  70 | +        "still_unpunctuated": needs_restoration(words), "reference_text": " ".join(w["word"] for w in ref)})
  71 | diff --git a/pipeline/run_fresh.py b/pipeline/run_fresh.py
  72 | index 179e56a7..5265476b 100644
  73 | --- a/pipeline/run_fresh.py
  74 | +++ b/pipeline/run_fresh.py
  75 | @@ -379,11 +379,7 @@ def stage_cut(run):
  76 |          from pinned import write_pinned_cut_table
  77 |          write_pinned_cut_table(run.dir)
  78 |      else:
  79 | -        adj = L.Adjudicator()
  80 | -        try:
  81 | -            L.write_lock_cut_table(run.dir, adj)
  82 | -        finally:
  83 | -            adj.close()
  84 | +        L.write_lock_cut_table(run.dir)
  85 |      with open(os.path.join(run.dir, "cuts_final.json")) as f:
  86 |          cuts = json.load(f)
  87 |      report, fails = [], []
  88 | @@ -419,11 +415,7 @@ def stage_cut(run):
  89 |  def stage_sentence_law(run):
  90 |      """G16 SENTENCE_BOUNDARY before anything is rendered: every cut holds exactly its locked
  91 |      sentence(s), both edges are legal sentence boundaries and the cuts sit inside those pauses."""
  92 | -    adj = L.Adjudicator()
  93 | -    try:
  94 | -        ok, table = L.gate_g16(run.dir, adj)
  95 | -    finally:
  96 | -        adj.close()
  97 | +    ok, table = L.gate_g16(run.dir)
  98 |      run.prov["G16_pre_render"] = table
  99 |      jdump(os.path.join(run.dir, "SENTENCE_LAW.json"), {"pass": ok, "segments": table})
 100 |      for r in table:
 101 | @@ -695,11 +687,7 @@ def stage_gates(run, final16, man16, final9, man9):
 102 |          rows[fmt].update(tail_rows(res["G9_tail"]["pass"], fallback))
 103 |  
 104 |      # G16 SENTENCE_BOUNDARY: re-run on the final cut state (format-independent; same row in both)
 105 | -    adj = L.Adjudicator()
 106 | -    try:
 107 | -        g16_ok, g16 = L.gate_g16(run.dir, adj)
 108 | -    finally:
 109 | -        adj.close()
 110 | +    g16_ok, g16 = L.gate_g16(run.dir)
 111 |      for fmt in ("16x9", "9x16"):
 112 |          rows[fmt]["G16_sentence_boundary"] = _status(g16_ok)
 113 |  
 114 | diff --git a/pipeline/select_passages.py b/pipeline/select_passages.py
 115 | index a9f5a1c4..a11d0f9b 100644
 116 | --- a/pipeline/select_passages.py
 117 | +++ b/pipeline/select_passages.py
 118 | @@ -69,38 +69,44 @@ def _download_window(video_id, start_s, end_s, run_dir, pad=15.0):
 119 |  
 120 |  
 121 |  def _whisper_transcribe(source_path, video_id, run_dir):
 122 | -    """Run faster-whisper on a source file for word-level timestamps.
 123 | +    """Run faster-whisper on a source file for word-level timestamps (verbatim decode). Where that
 124 | +    decode has no punctuation, sentence punctuation is added from a prompted reference decode of the
 125 | +    same audio, onto aligned words only (pipeline/punctuation.py; the words never change).
 126 |  
 127 |      Returns dict with 'words' list or None on failure.
 128 |      """
 129 | +    import punctuation
 130 |      transcript_path = os.path.join(run_dir, "transcripts", f"{video_id}.json")
 131 | -    if os.path.exists(transcript_path):
 132 | -        with open(transcript_path) as f:
 133 | -            return json.load(f)
 134 | -
 135 |      os.makedirs(os.path.join(run_dir, "transcripts"), exist_ok=True)
 136 |  
 137 |      try:
 138 | +        result = None
 139 | +        if os.path.exists(transcript_path):
 140 | +            with open(transcript_path) as f:
 141 | +                result = json.load(f)
 142 | +            if result.get("punctuation") or not punctuation.needs_restoration(result.get("words", [])):
 143 | +                return result
 144 | +
 145 |          from faster_whisper import WhisperModel
 146 |          model = WhisperModel("large-v3", device="cuda", compute_type="float16")
 147 | -        segments, info = model.transcribe(
 148 | -            source_path, language="en", beam_size=5,
 149 | -            word_timestamps=True, vad_filter=False,
 150 | -        )
 151 | -
 152 | -        words = []
 153 | -        for seg in segments:
 154 | -            if seg.words:
 155 | -                for w in seg.words:
 156 | -                    words.append({
 157 | -                        "word": w.word.strip(),
 158 | -                        "start": round(w.start, 3),
 159 | -                        "end": round(w.end, 3),
 160 | -                        "probability": round(w.probability, 3),
 161 | -                    })
 162 | -
 163 | -        result = {"words": words, "language": info.language,
 164 | -                  "duration": info.duration}
 165 | +        if result is None:
 166 | +            segments, info = model.transcribe(
 167 | +                source_path, language="en", beam_size=5,
 168 | +                word_timestamps=True, vad_filter=False,
 169 | +            )
 170 | +            words = []
 171 | +            for seg in segments:
 172 | +                if seg.words:
 173 | +                    for w in seg.words:
 174 | +                        words.append({
 175 | +                            "word": w.word.strip(),
 176 | +                            "start": round(w.start, 3),
 177 | +                            "end": round(w.end, 3),
 178 | +                            "probability": round(w.probability, 3),
 179 | +                        })
 180 | +            result = {"words": words, "language": info.language,
 181 | +                      "duration": info.duration}
 182 | +        result = punctuation.ensure(result, source_path, model)
 183 |          with open(transcript_path, "w") as f:
 184 |              json.dump(result, f, indent=2)
 185 |          return result
 186 | @@ -224,7 +230,6 @@ def select_and_build_edl(keyword, niche, run_dir):
 187 |      # cuttable sentence boundaries in this file's audio. Nothing is ever picked by nearest word.
 188 |      channels_used = set()
 189 |      boundary_report = []
 190 | -    adj = L.Adjudicator()
 191 |  
 192 |      def _build_segment(passage, label):
 193 |          vid = passage["video_id"]
 194 | @@ -242,7 +247,7 @@ def select_and_build_edl(keyword, niche, run_dir):
 195 |          i0, i1, ratio = a
 196 |          lock = L.make_lock(vid, words, i0, i1, L.sha256_file(tpath), passage["text"],
 197 |                             [passage["start"], passage["end"]], ratio, "select_passages")
 198 | -        plan = L.edge_plan(L.SourceAudio(sources[vid]), words, i0, i1, adj, context=f"select {label}")
 199 | +        plan = L.edge_plan(L.SourceAudio(sources[vid]), words, i0, i1)
 200 |          rec.update(locked=f"'{lock['first_word']}' ... '{lock['last_word']}'", align_ratio=ratio,
 201 |                     **{f"{s}_edge": {k: plan[s].get(k) for k in ("valid", "cuttable", "pause", "lexical", "reason",
 202 |                                                                   "cut_lo", "cut_hi", "lead_in_pad_s")}
 203 | @@ -356,7 +361,6 @@ def select_and_build_edl(keyword, niche, run_dir):
 204 |                      seg["index"] = len(clip_segs) + 1
 205 |                      clip_segs.append(seg)
 206 |      finally:
 207 | -        adj.close()
 208 |          with open(os.path.join(run_dir, "SELECT_BOUNDARIES.json"), "w") as f:
 209 |              json.dump(boundary_report, f, indent=2)
 210 |      for r in boundary_report:
 211 | diff --git a/pipeline/sentence_law.py b/pipeline/sentence_law.py
 212 | index 9ebf28d8..dee8881f 100644
 213 | --- a/pipeline/sentence_law.py
 214 | +++ b/pipeline/sentence_law.py
 215 | @@ -10,9 +10,12 @@ BOUNDARY RULE (law constants, stated once, used by selection, cutting and gate G
 216 |    A sentence boundary exists between transcript word k and word k+1 iff BOTH
 217 |    (L) LEXICAL   punctuated transcript: word k ends in '.', '!' or '?' and is not an abbreviation
 218 |                  (U.S., Mr., a.m., ...) or a trailing '...';
 219 | -                unpunctuated transcript (fewer than 1 terminal mark per 60 words within +-60 words):
 220 | -                a local-model adjudication says the sentence ends after word k (content-addressed
 221 | -                cache data/editorial/sentence_adjudication.json, every decision logged).
 222 | +                a transcript stretch with fewer than 1 terminal mark per 60 words (within +-60 words) is
 223 | +                UNPUNCTUATED: no gap in it is a sentence boundary (fail closed). Transcripts get their
 224 | +                punctuation at transcription time (pipeline/punctuation.py: marks from a second,
 225 | +                prompted decode of the same audio, onto aligned verbatim words only). The per-gap
 226 | +                local-model adjudicator was removed 2026-11-11: it called 19 of 19 Yahoo Finance gaps
 227 | +                sentence ends, 'the | Wolf' included (E-FAIL-013).
 228 |    (A) ACOUSTIC  the source audio holds a PAUSE between them: a run of >= PAUSE_MIN_S (80 ms, Law
 229 |                  14c) of 10 ms RMS frames below the QUIET LINE, inside [start(k), end(k+1)] (whisper
 230 |                  word edges are estimates and collapse at sentence boundaries, Law 14/14c, so the
 231 | @@ -34,7 +37,6 @@ import json
 232 |  import os
 233 |  import re
 234 |  import subprocess
 235 | -import time
 236 |  from difflib import SequenceMatcher
 237 |  
 238 |  import numpy as np
 239 | @@ -63,8 +65,6 @@ PUNCT_WINDOW_WORDS = 60
 240 |  WORD_DURATION_RATIO_MIN = 0.85  # G17: rendered edge word keeps >= 85 % of its duration
 241 |  _TERMINAL = (".", "!", "?")
 242 |  _ABBREV = {"mr", "mrs", "ms", "dr", "st", "vs", "etc", "jr", "sr", "inc", "ltd", "corp", "prof", "approx"}
 243 | -ADJ_CACHE = os.path.join(REPO, "data", "editorial", "sentence_adjudication.json")
 244 | -ADJ_LOG = os.path.join(REPO, "data", "editorial", "sentence_adjudication_log.jsonl")
 245 |  
 246 |  
 247 |  class LawError(Exception):
 248 | @@ -188,72 +188,9 @@ def find_pause(sa, a, b):
 249 |  
 250 |  # ── lexical adjudication for unpunctuated transcripts ──
 251 |  
 252 | -class Adjudicator:
 253 | -    """'Does a sentence end after word k?' for unpunctuated transcripts. Content-addressed cache,
 254 | -    every decision (cached or fresh) logged. allow_model=False = cache only (tests, gates replay)."""
 255 | -
 256 | -    def __init__(self, cache_path=ADJ_CACHE, log_path=ADJ_LOG, allow_model=True, model=None):
 257 | -        self.cache_path, self.log_path, self.allow_model = cache_path, log_path, allow_model
 258 | -        self.model = model
 259 | -        self._llm = None
 260 | -        try:
 261 | -            with open(cache_path) as f:
 262 | -                self.cache = json.load(f)
 263 | -        except (FileNotFoundError, json.JSONDecodeError):
 264 | -            self.cache = {}
 265 | -
 266 | -    def _llm_start(self):
 267 | -        if self._llm is None:
 268 | -            import story_semantics as sm
 269 | -            self._llm = sm.LocalLLM(model=self.model or sm.LLM_MODEL).start()
 270 | -        return self._llm
 271 | -
 272 | -    def close(self):
 273 | -        if self._llm is not None:
 274 | -            self._llm.stop()
 275 | -            self._llm = None
 276 | -
 277 | -    def decide(self, words, k, context=""):
 278 | -        left = " ".join(w["word"].strip() for w in words[max(0, k - 39):k + 1])
 279 | -        right = " ".join(w["word"].strip() for w in words[k + 1:k + 21])
 280 | -        model = self.model or "gemma3:27b"
 281 | -        key = hashlib.sha256(f"{model}|{left}|<GAP>|{right}".encode()).hexdigest()[:24]
 282 | -        rec = self.cache.get(key)
 283 | -        fresh = False
 284 | -        if rec is None:
 285 | -            if not self.allow_model:
 286 | -                raise LawError(f"sentence adjudication not cached for gap after '{words[k]['word']}' "
 287 | -                               f"(cache-only mode)")
 288 | -            prompt = (
 289 | -                "A speech transcript has no punctuation. Decide whether a sentence ENDS exactly at the "
 290 | -                "marker <GAP> (the next word begins a new sentence), judging grammar and meaning only.\n"
 291 | -                f"TEXT: ...{left} <GAP> {right}...\n"
 292 | -                'Answer JSON only: {"sentence_end": true or false, "reason": "<= 20 words"}')
 293 | -            out = self._llm_start().chat_json(
 294 | -                prompt, max_tokens=120,
 295 | -                validate=lambda o: isinstance(o, dict) and isinstance(o.get("sentence_end"), bool))
 296 | -            rec = {"sentence_end": bool(out["sentence_end"]), "reason": str(out.get("reason", ""))[:160],
 297 | -                   "left_tail": left[-80:], "right_head": right[:60], "model": model,
 298 | -                   "decided_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
 299 | -            self.cache[key] = rec
 300 | -            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
 301 | -            tmp = self.cache_path + ".tmp"
 302 | -            with open(tmp, "w") as f:
 303 | -                json.dump(self.cache, f, indent=1, sort_keys=True)
 304 | -            os.replace(tmp, self.cache_path)
 305 | -            fresh = True
 306 | -        if self.log_path:
 307 | -            os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
 308 | -            with open(self.log_path, "a") as f:
 309 | -                f.write(json.dumps({"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "key": key,
 310 | -                                    "fresh": fresh, "context": context, "after_word": words[k]["word"],
 311 | -                                    "sentence_end": rec["sentence_end"], "reason": rec["reason"]}) + "\n")
 312 | -        return rec["sentence_end"], f"model:{rec['model']} ({'fresh' if fresh else 'cached'} {key}): {rec['reason']}"
 313 | -
 314 | -
 315 |  # ── boundaries ──
 316 |  
 317 | -def boundary(sa, words, k, adj=None, context=""):
 318 | +def boundary(sa, words, k):
 319 |      """Sentence boundary between word k and k+1 (k = -1: file head; k = len-1: file end)."""
 320 |      n = len(words)
 321 |      rec = {"after_word": words[k]["word"] if k >= 0 else "<file head>",
 322 | @@ -282,29 +219,19 @@ def boundary(sa, words, k, adj=None, context=""):
 323 |      rec.update(levels=lv, pause=pause)
 324 |      if pause is None:
 325 |          return {**rec, "valid": False, "reason": f"no pause >= {int(PAUSE_MIN_S * 1000)} ms between the words"}
 326 | -    if is_punctuated(words, k):
 327 | -        lex = is_terminal(words[k]["word"])
 328 | -        rec["lexical"] = "punctuation"
 329 | -        if not lex:
 330 | -            return {**rec, "valid": False, "reason": f"'{words[k]['word']}' does not end a sentence"}
 331 | -    else:
 332 | -        if adj is None:
 333 | -            return {**rec, "valid": False, "lexical": "unpunctuated",
 334 | -                    "reason": "unpunctuated transcript and no adjudicator"}
 335 | -        try:
 336 | -            lex, why = adj.decide(words, k, context=context)
 337 | -        except LawError as e:
 338 | -            return {**rec, "valid": False, "lexical": "unpunctuated", "reason": str(e)}
 339 | -        rec["lexical"] = why
 340 | -        if not lex:
 341 | -            return {**rec, "valid": False, "reason": f"adjudicated: no sentence end after '{words[k]['word']}'"}
 342 | +    if not is_punctuated(words, k):
 343 | +        return {**rec, "valid": False, "lexical": "unpunctuated",
 344 | +                "reason": "unpunctuated transcript stretch: no sentence evidence (fail closed)"}
 345 | +    rec["lexical"] = "punctuation"
 346 | +    if not is_terminal(words[k]["word"]):
 347 | +        return {**rec, "valid": False, "reason": f"'{words[k]['word']}' does not end a sentence"}
 348 |      return {**rec, "valid": True}
 349 |  
 350 |  
 351 | -def edge_plan(sa, words, i0, i1, adj=None, context=""):
 352 | +def edge_plan(sa, words, i0, i1):
 353 |      """Boundaries around words[i0..i1] and the legal cut ranges they allow."""
 354 | -    bin_ = boundary(sa, words, i0 - 1, adj, context=f"{context} in")
 355 | -    bout = boundary(sa, words, i1, adj, context=f"{context} out")
 356 | +    bin_ = boundary(sa, words, i0 - 1)
 357 | +    bout = boundary(sa, words, i1)
 358 |      plan = {"in": bin_, "out": bout}
 359 |      if bin_["valid"]:
 360 |          p = bin_["pause"]
 361 | @@ -420,7 +347,7 @@ def _accepted_cut_pair(src, plan, step=HOP_S):
 362 |      return (in_ok, out_ok) if check_cut_acoustics(src, in_ok, out_ok)[0] else None
 363 |  
 364 |  
 365 | -def write_lock_cut_table(run_dir, adj=None):
 366 | +def write_lock_cut_table(run_dir):
 367 |      """cuts_final.json with every cut placed inside the pause that bounds its LOCKED sentence(s):
 368 |      the cut can never add or drop a word. A segment whose locked edges are not cuttable is written
 369 |      verified=false with the reason (acceptance then HOLDs; no search outside the pause)."""
 370 | @@ -439,7 +366,7 @@ def write_lock_cut_table(run_dir, adj=None):
 371 |          with open(tpath) as f:
 372 |              words = json.load(f)["words"]
 373 |          plan = edge_plan(SourceAudio(os.path.join(run_dir, "sources", f"{seg['video_id']}.mp4")), words,
 374 | -                         lock["i0"], lock["i1"], adj, context=f"cut {label}")
 375 | +                         lock["i0"], lock["i1"])
 376 |          entry.update(first_word_expected=lock["first_word"], last_word_expected=lock["last_word"],
 377 |                       selection_lock_sha256=lock["sha256"],
 378 |                       pause_in=plan["in"].get("pause"), pause_out=plan["out"].get("pause"))
 379 | @@ -465,7 +392,7 @@ def write_lock_cut_table(run_dir, adj=None):
 380 |  # ── G16 SENTENCE_BOUNDARY (pre-render and final gate) ──
 381 |  
 382 |  
 383 | -def gate_g16(run_dir, adj=None, source_path_fn=None):
 384 | +def gate_g16(run_dir, source_path_fn=None):
 385 |      """Every clip's cut must hold exactly its locked sentence(s): lock intact, expected words equal the
 386 |      lock (never recomputed), both edges legal sentence boundaries, cut points inside those pauses
 387 |      (or a declared room-tone pad at a file head without lead-in). Returns (ok, table)."""
 388 | @@ -493,7 +420,7 @@ def gate_g16(run_dir, adj=None, source_path_fn=None):
 389 |                  words = json.load(f)["words"]
 390 |              src = (source_path_fn or (lambda v: os.path.join(run_dir, "sources", f"{v}.mp4")))(seg["video_id"])
 391 |              sa = SourceAudio(src)
 392 | -            plan = edge_plan(sa, words, lock["i0"], lock["i1"], adj, context=f"G16 {label}")
 393 | +            plan = edge_plan(sa, words, lock["i0"], lock["i1"])
 394 |              row["in"] = _edge_row(plan["in"], cut["cut_in"], "in", cut)
 395 |              row["out"] = _edge_row(plan["out"], cut["cut_out"], "out", cut)
 396 |              row["errors"] += [f"IN: {row['in']['why']}"] if not row["in"]["pass"] else []
 397 | diff --git a/pipeline/test_pulse_20261110_mustfail.py b/pipeline/test_pulse_20261110_mustfail.py
 398 | index a5073319..ff399269 100644
 399 | --- a/pipeline/test_pulse_20261110_mustfail.py
 400 | +++ b/pipeline/test_pulse_20261110_mustfail.py
 401 | @@ -5,7 +5,8 @@ EXPECTED ON HEAD 7a76a5c5 (before the checks land): every DEFECT test FAILS, bec
 402 |  that catches the defect or the existing path accepts it; the CONTROL tests (v2f card passes G12/G15,
 403 |  clip_02 out edge is clean) document what must keep passing. A green run means the checks landed.
 404 |  Never invert an assertion to make it pass. Fixture: tests/fixtures/pulse_20261110 (copies; the run dir
 405 | -is never modified). No GPU, no model calls: the unpunctuated-transcript adjudications are cached.
 406 | +is never modified). No GPU, no model calls: Yahoo Finance's unpunctuated window transcript is read the
 407 | +way today's pipeline produces it (selection/transcripts_punctuated, pipeline/punctuation.py).
 408 |  
 409 |  D1  hook opens on "Bitcoin" at source 0.000 with 60 ms of genuine room tone before the onset (30 ms of
 410 |      codec zero first) and no lead-in pad              -> G16 IN and G17a head FAIL
 411 | @@ -58,6 +59,8 @@ class _G16Fixture(unittest.TestCase):
 412 |          L = _law()
 413 |          cls.tmp = tempfile.mkdtemp(prefix="pulse_20261110_")
 414 |          shutil.copytree(os.path.join(FIX, "run", "transcripts"), os.path.join(cls.tmp, "transcripts"))
 415 | +        for f in os.listdir(os.path.join(FIX, "selection", "transcripts_punctuated")):   # today's punctuation layer
 416 | +            shutil.copy(os.path.join(FIX, "selection", "transcripts_punctuated", f), os.path.join(cls.tmp, "transcripts"))
 417 |          shutil.copy(os.path.join(FIX, "run", "cuts_final.json"), cls.tmp)
 418 |          edl = json.load(open(os.path.join(FIX, "run", "edl.json")))
 419 |          sel = {p["video_id"]: p for p in json.load(open(os.path.join(FIX, "selection", "B3_chosen.json")))["chosen"]}
 420 | @@ -71,9 +74,7 @@ class _G16Fixture(unittest.TestCase):
 421 |                                                  [p["start"], p["end"]], r, "B3 (fixture)")
 422 |              cls.locks[label] = seg["selection_lock"]
 423 |          json.dump(edl, open(os.path.join(cls.tmp, "edl.json"), "w"), indent=1)
 424 | -        adj = L.Adjudicator(cache_path=os.path.join(FIX, "selection", "sentence_adjudication.json"),
 425 | -                            log_path=None, allow_model=False)
 426 | -        cls.ok, table = L.gate_g16(cls.tmp, adj, source_path_fn=lambda v: os.path.join(FIX, "audio", f"src_{v}.flac"))
 427 | +        cls.ok, table = L.gate_g16(cls.tmp, source_path_fn=lambda v: os.path.join(FIX, "audio", f"src_{v}.flac"))
 428 |          cls.rows = {r["segment"]: r for r in table}
 429 |          cls.g17_ok, t17 = L.gate_g17_prepared(
 430 |              {c: os.path.join(FIX, "audio", f"prepared_{c}.flac") for c in ("hook", "clip_01", "clip_02")})
 431 | @@ -87,7 +88,7 @@ class _G16Fixture(unittest.TestCase):
 432 |  class TestSelectionLockEdges(_G16Fixture):
 433 |      def test_locks_hold_the_editors_sentences(self):
 434 |          got = {k: (v["first_word"], v["last_word"]) for k, v in self.locks.items()}
 435 | -        self.assertEqual(got, {"hook": ("Bitcoin", "take."), "clip_01": ("It", "week."), "clip_02": ("of", "times")})
 436 | +        self.assertEqual(got, {"hook": ("Bitcoin", "take."), "clip_01": ("It", "week."), "clip_02": ("of", "times.")})
 437 |  
 438 |  
 439 |  class TestD1HookOnset(_G16Fixture):
 440 | @@ -118,9 +119,14 @@ class TestD3Edges(_G16Fixture):
 441 |          self.assertFalse(self.g17["clip_01"]["lead_ok"], f"D3a: G17a lead-in: {self.g17['clip_01']}")
 442 |  
 443 |      def test_d3b_clip02_in_fails(self):
 444 | +        # The speaker says "...past few days. Of course, of course, Bitcoin dropped ..."; the editor's text
 445 | +        # (one "Of course") anchors on the REPEATED "of course", so the locked start is not a sentence start
 446 | +        # ('course' | 'of'). The removed model adjudicator had called that gap a sentence end; with the
 447 | +        # punctuation layer it is not one. Yesterday's cut at 14.93 lands inside "days" on top of that.
 448 |          r = self.rows["clip_02"]["in"]
 449 |          self.assertFalse(r["pass"], f"D3b: clip_02 in 14.93 lands inside 'days': {r}")
 450 | -        self.assertIn("outside the legal range", r["why"], r)
 451 | +        self.assertEqual((r["after_word"], r["before_word"]), ("course", "of"), r)
 452 | +        self.assertIn("does not end a sentence", r["why"], r)
 453 |          self.assertFalse(self.g17["clip_02"]["lead_ok"], f"D3b: G17a lead-in: {self.g17['clip_02']}")
 454 |  
 455 |      def test_d3c_clip02_out_control_passes(self):
 456 | @@ -182,24 +188,97 @@ class TestTautology(_G16Fixture):
 457 |          self.assertIn("G17_onset_tail", src)
 458 |  
 459 |  
 460 | -class TestAdjudicatorReplay(unittest.TestCase):
 461 | -    """M12: in cache-only (gate) mode a missing adjudication is a LawError, and the unpunctuated
 462 | -    boundary it guards comes back invalid -- never a pass, never a silent model call."""
 463 | +class TestUnpunctuatedTranscript(unittest.TestCase):
 464 | +    """E-FAIL-013: the per-gap model adjudicator called 19 of 19 Yahoo Finance gaps sentence ends ('the |
 465 | +    Wolf', 'of | all', 'pretty | massively'; docs/audits/pulse-sentence-law/1b_fix_punctuation/
 466 | +    ADJUDICATOR_EVIDENCE_yahoo_sweep.jsonl). No model opinion decides a boundary any more: an unpunctuated
 467 | +    stretch has none (fail closed); punctuation comes from pipeline/punctuation.py at transcription time."""
 468 |  
 469 | -    def test_cache_miss_fails_closed(self):
 470 | -        L = _law()
 471 | -        tmp = tempfile.mkdtemp(prefix="adj_")
 472 | -        try:
 473 | -            adj = L.Adjudicator(cache_path=os.path.join(tmp, "empty.json"), log_path=None, allow_model=False)
 474 | -            words = json.load(open(os.path.join(FIX, "run", "transcripts", "36HPi9UZPOc.json")))["words"]
 475 | -            k = next(i for i, w in enumerate(words) if w["word"] == "times")
 476 | -            with self.assertRaises(L.LawError):
 477 | -                adj.decide(words, k)
 478 | -            b = L.boundary(L.SourceAudio(os.path.join(FIX, "audio", "src_36HPi9UZPOc.flac")), words, k, adj)
 479 | -            self.assertFalse(b["valid"], b)
 480 | -            self.assertIn("not cached", b["reason"], b)
 481 | -        finally:
 482 | -            shutil.rmtree(tmp, ignore_errors=True)
 483 | +    @classmethod
 484 | +    def setUpClass(cls):
 485 | +        cls.L = _law()
 486 | +        cls.sa = cls.L.SourceAudio(os.path.join(FIX, "audio", "src_36HPi9UZPOc.flac"))
 487 | +        cls.raw = json.load(open(os.path.join(FIX, "run", "transcripts", "36HPi9UZPOc.json")))["words"]
 488 | +        cls.punct = json.load(open(os.path.join(FIX, "selection", "transcripts_punctuated",
 489 | +                                                "36HPi9UZPOc.json")))["words"]
 490 | +
 491 | +    def gap(self, words, a, b):
 492 | +        key = lambda w: w["word"].rstrip(".,?!").lower()
 493 | +        return next(i for i in range(len(words) - 1) if key(words[i]) == a and key(words[i + 1]) == b)
 494 | +
 495 | +    def test_unpunctuated_gap_is_never_a_boundary(self):
 496 | +        b = self.L.boundary(self.sa, self.raw, self.gap(self.raw, "times", "i"))
 497 | +        self.assertFalse(b["valid"], b)
 498 | +        self.assertIn("unpunctuated", b["reason"], b)
 499 | +        self.assertFalse(hasattr(self.L, "Adjudicator"))
 500 | +
 501 | +    def test_the_adjudicators_false_sentence_ends_are_rejected(self):
 502 | +        for a, b_ in (("the", "wolf"), ("wolf", "of"), ("of", "all"), ("i", "am"), ("is", "up"), ("but", "i"),
 503 | +                      ("pretty", "massively")):
 504 | +            b = self.L.boundary(self.sa, self.punct, self.gap(self.punct, a, b_))
 505 | +            self.assertIsNotNone(b.get("pause"), (a, b_, b))          # the speaker does pause there ...
 506 | +            self.assertFalse(b["valid"], (a, b_, b))                  # ... but no sentence ends
 507 | +            self.assertIn("does not end a sentence", b["reason"], (a, b_, b))
 508 | +
 509 | +    def test_true_sentence_ends_with_a_pause_are_boundaries(self):
 510 | +        for a, b_ in (("hack", "but"), ("times", "i")):
 511 | +            b = self.L.boundary(self.sa, self.punct, self.gap(self.punct, a, b_))
 512 | +            self.assertTrue(b["valid"], (a, b_, b))
 513 | +
 514 | +
 515 | +class _Fake:
 516 | +    """faster-whisper stand-in for the punctuation reference decode."""
 517 | +
 518 | +    def __init__(self, text):
 519 | +        self.text, self.calls, self.kw = text, 0, {}
 520 | +
 521 | +    def transcribe(self, path, **kw):
 522 | +        from types import SimpleNamespace as NS
 523 | +        self.calls += 1
 524 | +        self.kw = kw
 525 | +        return [NS(words=[NS(word=" " + t) for t in self.text.split()])], None
 526 | +
 527 | +
 528 | +class TestPunctuationLayer(unittest.TestCase):
 529 | +    def words(self, text):
 530 | +        return [{"word": t, "start": i * 0.4, "end": i * 0.4 + 0.3} for i, t in enumerate(text.split())]
 531 | +
 532 | +    def test_marks_move_only_onto_aligned_words_and_words_never_change(self):
 533 | +        import punctuation as P
 534 | +        w = self.words("a lot has happened over the past few days of course of course bitcoin dropped hard")
 535 | +        ref = [{"word": t} for t in "A lot has happened over the past few days. Of course, Bitcoin dropped hard.".split()]
 536 | +        out, moved = P.transfer(w, ref)
 537 | +        self.assertEqual([P._key(x["word"]) for x in out], [P._key(x["word"]) for x in w])
 538 | +        self.assertEqual([(x["start"], x["end"]) for x in out], [(x["start"], x["end"]) for x in w])
 539 | +        ends = [x["word"] for x in out if _law().is_terminal(x["word"])]
 540 | +        self.assertEqual(ends, ["days.", "hard."])               # no boundary inside the dropped repetition
 541 | +
 542 | +    def test_ensure_leaves_a_punctuated_transcript_alone(self):
 543 | +        import punctuation as P
 544 | +        rec = {"words": self.words("It fell. " * 40)}
 545 | +        fake = _Fake("unused")
 546 | +        self.assertIs(P.ensure(rec, "x.wav", fake), rec)
 547 | +        self.assertEqual(fake.calls, 0)
 548 | +
 549 | +    def test_ensure_records_provenance_and_uses_the_neutral_prompt(self):
 550 | +        import punctuation as P
 551 | +        rec = {"words": self.words("so it fell over the weekend and then it bounced")}
 552 | +        fake = _Fake("So it fell over the weekend. And then it bounced.")
 553 | +        out = P.ensure(rec, "x.wav", fake)
 554 | +        self.assertEqual(fake.kw.get("initial_prompt"), P.PROMPT)
 555 | +        self.assertEqual([x["word"] for x in out["words"]][5:7], ["weekend.", "and"])
 556 | +        self.assertEqual(out["punctuation"]["source"], "asr_reference")
 557 | +        self.assertFalse(out["punctuation"]["still_unpunctuated"])
 558 | +
 559 | +    @unittest.skipUnless(os.environ.get("CUDA_VISIBLE_DEVICES") == "0", "whisper large-v3 needs GPU0")
 560 | +    def test_yahoo_fixture_is_reproduced_from_the_audio(self):
 561 | +        import punctuation as P
 562 | +        from faster_whisper import WhisperModel
 563 | +        raw = json.load(open(os.path.join(FIX, "run", "transcripts", "36HPi9UZPOc.json")))
 564 | +        want = json.load(open(os.path.join(FIX, "selection", "transcripts_punctuated", "36HPi9UZPOc.json")))
 565 | +        got = P.ensure(raw, os.path.join(FIX, "audio", "src_36HPi9UZPOc.flac"),
 566 | +                       WhisperModel("large-v3", device="cuda", compute_type="float16"))
 567 | +        self.assertEqual([w["word"] for w in got["words"]], [w["word"] for w in want["words"]])
 568 |  
 569 |  
 570 |  class TestWindowOffset(unittest.TestCase):
 571 | 
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
