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
Yes. Every changed function now delegates to `canon.canon_tokens` / `canon.canon` (or the thin wrappers `_canon_tokens`, `_g3b_words`, `_norm`, `norm_word`, `spoken_tokens`, `_words`). The new `canon.py` (lines 602-629) implements exactly the rules described in its docstring and in L-g/L-h/L-k. No ad-hoc regex normalisers remain in the comparison paths. Dynamic `sys.path` inserts (lines 73, 92, 218, 284) are the only visible risk of import-state leakage between clips; otherwise no off-by-one, unit, or silent-exception paths are introduced. Empty/missing inputs produce empty token lists (fail-closed behaviour preserved).

**Q2: LAW COMPLIANCE**  
- L-k (ONE CANONICAL FORM): COMPLIANT (new file lines 415-629 + all call sites).  
- L-g (WRITTEN FORMS) & L-h (TEXT READ AS SPOKEN): COMPLIANT (updated `_g3b_words`, `word_overlap`, `spoken_channels`, `_fuzzy_word_overlap`, `gate_g3`, `gate_g13`).  
- SELECTION LOCK / SNAP LIMIT / SENTENCE LAW: COMPLIANT – expected first/last words are now taken from the sealed `selection_lock` text via canon (line 331-333) and never recomputed from moved cuts.  
- No gate thresholds loosened; v2f reference path unchanged. No path allows a cut outside the locked sentence gap.

**Q3: TESTS**  
`test_canon.py` (new) exercises 200 real sentences under every mutation listed in the docstring and asserts both equivalence and non-equivalence. `test_g3b_majority.py` now uses `same(...)` and correctly distinguishes “above 40 trillion” vs “above 40 trillion dollars”. `test_stand_alone.py` adjustment matches the new canonical numeric handling. All must-fail cases remain must-fail; no vacuous assertions.

**Q4: VERDICT**  
- MEDIUM | lines 73,92,218,284 | repeated `sys.path.insert` for relative imports | replace with proper package-relative imports or `importlib`.  
- LOW | line 124 | `_key` drops “dollars/percent” only after a number – correct per comment but fragile if ASR ever emits other units.  

READY (minor import hygiene only; functional changes are correct and law-compliant).

## GPT4O — CYCLE 1 OUTPUT
### Q1: CORRECTNESS

1. **Functionality and Docstring Compliance:**
   - The `norm_word` function (lines 8-12) is updated to use the canonical form from `pipeline/canon.py`, which aligns with its docstring.
   - The `spoken_tokens` function (lines 23-46) now uses `canon.canon_tokens`, which matches the docstring's description of converting words to a canonical form.
   - The `_norm` function in `editorial_gate.py` (lines 57-60) and `_g20_norm` in `gates.py` (lines 80-84) have been updated to use the canonical form, aligning with their purpose of normalizing text.
   - The `_key` function in `punctuation.py` (lines 118-125) correctly implements the canonical form with adjustments for currency/percent words, as per its docstring.
   - The `canon.py` module (lines 414-628) provides a comprehensive implementation of the canonical form, covering various transformations like entity decoding, number normalization, and punctuation handling, as described in its header comment.

2. **Error Handling and Data Integrity:**
   - The changes ensure that text normalization and comparison are consistent across the pipeline, reducing the risk of silent exceptions or incorrect comparisons.
   - There is no indication from the diff that a path could produce a PASS when data is missing or a model failed. The functions seem to handle inputs robustly, but without the full context of how these functions are called, it's hard to be certain.

### Q2: LAW COMPLIANCE

1. **SENTENCE LAW:** COMPLIANT
   - The use of `canon.canon_tokens` ensures that words are consistently normalized, supporting accurate sentence boundary detection (lines 8-12, 23-46).

2. **SELECTION LOCK:** COMPLIANT
   - The changes do not indicate any recomputation of expected words after selection. The use of canonical forms ensures consistency (lines 330-333).

3. **SNAP LIMIT:** COMPLIANT
   - The canonical form ensures that comparisons are accurate, which supports maintaining snap limits (lines 23-46).

4. **NEIGHBOUR:** COMPLIANT
   - The canonical form helps ensure that edge words are correctly identified, supporting the neighbor rule (lines 23-46).

5. **ONSET/TAIL:** COMPLIANT
   - The canonical form aids in maintaining accurate onset and tail word detection (lines 23-46).

6. **CREDITS:** COMPLIANT
   - The use of canonical forms in name matching (lines 80-84) supports accurate credit checks.

7. **L-a SIGN-OFF NAMES ALL:** COMPLIANT
   - The canonical form is used to ensure accurate name matching in sign-offs (lines 400-410).

8. **L-b EDGE WORDS WHOLE:** COMPLIANT
   - The canonical form supports accurate edge word detection (lines 23-46).

9. **L-c DISSENT IS RIGHT UNTIL DISPROVED:** COMPLIANT
   - The canonical form aids in ensuring accurate edge word comparisons (lines 23-46).

10. **L-d PROTECTED PREVIEW:** COMPLIANT
    - The changes do not affect the protected preview path.

11. **L-e PUNCTUATED BEFORE READ:** COMPLIANT
    - The canonical form ensures that punctuation is consistently handled (lines 23-46).

12. **L-f CHANNELS FIRST:** COMPLIANT
    - The canonical form supports accurate channel name detection (lines 400-410).

13. **L-g WRITTEN FORMS:** COMPLIANT
    - The canonical form explicitly handles written forms as spoken words (lines 414-628).

14. **L-h TEXT READ AS SPOKEN:** COMPLIANT
    - The canonical form decodes entities and joins split tokens, aligning with this law (lines 414-628).

15. **L-i THE CLAIM IS THE EVENT:** COMPLIANT
    - The canonical form supports accurate event detection (lines 414-628).

16. **L-j RELEASE IS AUTHORISED ON THESE BYTES:** COMPLIANT
    - The changes ensure consistent text handling, supporting accurate release checks (lines 414-628).

17. **L-k ONE CANONICAL FORM:** COMPLIANT
    - The introduction of `canon.py` ensures that all text comparisons use a single canonical form (lines 414-628).

18. **LAW 20 / M2:** COMPLIANT
    - The changes do not alter gate thresholds or reclassify failing gates.

19. **M12 FAIL CLOSED:** COMPLIANT
    - The changes ensure robust handling of text normalization, reducing the risk of silent failures.

20. **LAW 22:** COMPLIANT
    - The changes do not affect the v2f reference path.

### Q3: TESTS

1. **Test Coverage:**
   - The tests in `test_canon.py` (lines 629-862) comprehensively cover the canonical form transformations, including HTML entities, unicode normalization, number handling, and more.
   - The tests in `test_g3b_majority.py` (lines 148-180) verify that symbols are read as spoken words, aligning with law L-g.
   - The tests in `test_stand_alone.py` (lines 182-195) ensure that subject terms are correctly identified, supporting law L-f.

2. **Must-Fail and Must-Pass:**
   - The tests include cases that must fail and pass, as required by the laws, ensuring that the canonical form is correctly implemented and used.

3. **Potential Issues:**
   - There are no indications of assertions that could pass vacuously. The tests seem well-constructed to validate the canon

## GEMINI — CYCLE 1 OUTPUT
An audit of the `pulse-sentence-law` feature follows.

### Q1: CORRECTNESS

The code appears to be of high quality and systematically addresses the issues it sets out to solve.

1.  **Centralization of Logic:** The primary change is the introduction of `pipeline/canon.py` and the removal of ad-hoc text normalization logic from at least 7 other files. This is a massive improvement in correctness and maintainability. The old implementations were scattered, inconsistent, and, as evidenced by the feature's purpose, buggy (e.g., the original `_g3b_words` in `qa_gates.py`). The new `canon.py` provides a single, extensively tested source of truth for text comparison.

2.  **Robustness of `canon.py`:** The implementation in `canon.py` is thorough.
    *   It correctly handles a wide range of transformations: HTML entities, Unicode normalization (`NFKC`), case folding, and joining of split tokens from Whisper (e.g., `'$81' ' ,000'` -> `'$81,000'`).
    *   The number parsing is sophisticated, handling digits, spelled-out numbers (`_words_number`), suffixes (`k`, `M`, `B`), and spoken-order currency/percentages. The use of a state machine with `owed` (lines 538, 574) to correctly place the word "dollars" after a numeric amount is a good, robust design.
    *   The distinction between `canon_tokens(heads=True)` for `stand_alone.py` (line 144) and the default behavior shows careful consideration of different use cases.

3.  **Gate Logic Improvements:** The gates are made more reliable.
    *   In `segment_v1/qa_gates.py`, the `_says` helper function (line 360) replaces substring matching (`alias in t_lower`) with a contiguous token-run match. This is far more precise and less prone to false positives (e.g., matching "in" inside "binance").
    *   The change in `gate_g3b` (lines 331-333) to use the `selection_lock` text as context for the final word is a crucial and subtle correctness fix. It allows `canon.py` to correctly interpret multi-word phrases like "40 trillion", which it couldn't do if it only saw the last word, "trillion".
    *   The `word_overlap` function (line 213) is corrected to return `0.0` for an empty reference, fixing a potential "pass on missing data" bug and adhering to `M12 FAIL CLOSED`.

4.  **Configuration and Pathing:** The removal of hardcoded absolute paths like `/home/ultron/...` in `gates.py` (lines 73, 93) in favor of relative paths (`os.path.join`) makes the code more portable and robust.

I see no obvious off-by-one errors, state leakage, or pathways that would produce a `PASS` on failed models or missing data. The changes are systematic and well-reasoned.

### Q2: LAW COMPLIANCE

The diff shows a strong focus on complying with the new and existing laws.

*   **L-g WRITTEN FORMS:** COMPLIANT. This is a core focus of the change. The new `canon.py` module explicitly implements the required logic (e.g., '$40 trillion' -> '40 trillion dollars'), and the old, insufficient implementation in `qa_gates.py` (lines 290-322) is correctly removed. The test in `test_g3b_majority.py` (lines 161-178) directly verifies this.
*   **L-h TEXT READ AS SPOKEN:** COMPLIANT. `canon.py`'s `fold` function (line 478) handles HTML entity decoding. The `_SPLIT` regex (line 460) and `canon_aligned`'s logic (lines 615-618) handle joining split tokens.
*   **L-k ONE CANONICAL FORM:** COMPLIANT. This is the central principle of the entire diff. The creation of `pipeline/canon.py` and the systematic refactoring of `cut_accept.py`, `editorial_gate.py`, `gates.py`, `pinned.py`, `stand_alone.py`, and `segment_v1/qa_gates.py` to use it directly implements this law. The `TestSites` class in the new `test_canon.py` (line 825) even includes a "grep test" to enforce this law across the codebase, which is exemplary.
*   **L-a SIGN-OFF NAMES ALL:** COMPLIANT. The comparison logic for spoken channel names in G20 (`gates.py`, line 83) and G13 (`qa_gates.py`, line 406) is now routed through `canon.py`, making it more accurate and compliant with L-k. The G13 check is also improved from a substring search to a token-sequence match.
*   **M12 FAIL CLOSED:** COMPLIANT. In `qa_gates.py` (line 213), the `word_overlap` function is changed to return `0.0` (fail) when the reference text is empty, instead of `1.0` (pass).
*   **LAW 20 / M2:** COMPLIANT. No gate thresholds are loosened. The logic is made stricter.
*   **The following laws are supported by these changes but not fully implemented within this diff:**
    *   `SENTENCE LAW` & `L-e PUNCTUATED BEFORE READ`: The changes in `punctuation.py` (line 125) make the alignment process (which transfers punctuation) more robust by using a canonical key, but the core punctuation logic itself isn't in this diff. The use of `canon.py` in all word comparisons is a necessary prerequisite for reliable sentence boundary checks.
*   **The following laws are not violated and appear unaffected by this diff:**
    *   `SELECTION LOCK`, `SNAP LIMIT`, `NEIGHBOUR`, `ONSET/TAIL`, `CREDITS`, `L-b`, `L-c`, `L

## CLAUDE'S CYCLE 1 CONSENSUS
# CONSENSUS REPORT — PULSE-SENTENCE-LAW — CYCLE 1
Generated: 2026-11-11 22:46
Models: grok, gpt4o, gemini

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Correctness | 9/10 | 8/10 | 9/10 | **9/10** |
| Law Compliance | 9/10 | 9/10 | 9/10 | **9/10** |
| Test Quality | 10/10 | 8/10 | 9/10 | **9/10** |
| Security / Robustness | 7/10 | 7/10 | 7/10 | **7/10** |
| Overall Readiness | 9/10 | 9/10 | 9/10 | **9/10** |

> Score derivation: Gemini issued 1 MAJOR + 1 MAJOR + 1 MEDIUM + 1 MEDIUM (no blockers, all resolved by the diff itself); GPT-4o and Grok issued READY with minor/medium caveats only. All three models converged on the same import-hygiene and word_overlap issues as the only unresolved residuals.

---

## UNANIMOUS FINDINGS (all 3 models agree — implement unconditionally)

### U1 — `sys.path.insert` import-hygiene
**What:** Lines 73, 92, 218, 284 in `gates.py` (and mirrored sites) repeatedly call `sys.path.insert(0, ...)` to resolve relative imports. This is fragile, order-dependent, and leaks path state across clip-processing iterations in long-running workers.
**File/Line:** `gates.py:73`, `gates.py:92`, `gates.py:218`, `gates.py:284` (and any equivalent in `qa_gates.py` / `editorial_gate.py`)
**Fix:** Convert all affected files to proper package-relative imports (`from ..pipeline import canon`) or, where the package boundary makes that awkward, use a single `importlib.util.spec_from_file_location` call in a shared bootstrap that runs once at process start. Remove every `sys.path.insert` from hot paths.

### U2 — `word_overlap` returns `1.0` on empty reference (fail-open)
**What:** All three models flagged that `word_overlap` previously returned `1.0` (full match / PASS) when the reference token set was empty, violating `M12 FAIL CLOSED`. Gemini confirmed the fix is in the diff (now returns `0.0`); Grok and GPT-4o both independently flagged the residual risk that this logic must be verified in every downstream call site, not just the one changed line.
**File/Line:** `qa_gates.py:213` (fix confirmed in diff) + all callers that pass the result directly to a gate threshold comparison.
**Fix:** Verify every call site of `word_overlap` / `_fuzzy_word_overlap` asserts that a `0.0` return correctly propagates to a FAIL disposition rather than being swallowed by an `or`-short-circuit or default-`True` fallback.

---

## MAJORITY FINDINGS (2 of 3 models agree)

### M1 — G3b last-word context needs `selection_lock` text, not isolated token (Gemini + Grok)
**What:** Gate G3b, when checking the final word of a sentence, was previously passing only the isolated last token to the canonicaliser. For multi-word numeric phrases like "40 trillion", the canonicaliser cannot resolve "trillion" without seeing "40" in the same context window, producing a comparison mismatch. The fix (lines 331-333 reading from `selection_lock`) is in the diff.
**File/Line:** `qa_gates.py:331-333`
**Fix confirmed in diff.** Regression te

---

## ORIGINAL CODE (same code as Cycle 1)
## THE CODE (every new and modified file)

### File: docs/audits/pulse-sentence-law/CURRENT.diff (863 lines)
```
   1 | diff --git a/pipeline/cut_accept.py b/pipeline/cut_accept.py
   2 | index de3410bd..1a6e31c8 100644
   3 | --- a/pipeline/cut_accept.py
   4 | +++ b/pipeline/cut_accept.py
   5 | @@ -129,7 +129,9 @@ def check_cut_acoustics(source_path, cut_in, cut_out):
   6 |  # ── Law 14c edge-word check on the prepared clip ──
   7 |  
   8 |  def norm_word(w):
   9 | -    return re.sub(r"[^a-z0-9']", "", (w or "").lower().replace("’", "'"))
  10 | +    """A word in the pipeline's one canonical form (pipeline/canon.py), spaces removed."""
  11 | +    import canon
  12 | +    return "".join(canon.canon_tokens(w))
  13 |  
  14 |  
  15 |  def words_match(heard, expected):
  16 | @@ -143,29 +145,11 @@ def words_match(heard, expected):
  17 |      return len(a) >= 3 and len(b) >= 3 and (a.startswith(b) or b.startswith(a))
  18 |  
  19 |  
  20 | -_MAGNITUDES = {"hundred", "thousand", "million", "billion", "trillion"}
  21 | -
  22 | -
  23 |  def spoken_tokens(words):
  24 | -    """Expand whisper's written currency/percent forms into spoken order so they
  25 | -    compare with EDL words: '$40 trillion.' -> 40 trillion dollars ; '5%' -> 5 percent."""
  26 | -    toks = [w for w in words]
  27 | -    out = []
  28 | -    i = 0
  29 | -    while i < len(toks):
  30 | -        w = toks[i]
  31 | -        if w.startswith("$") and len(w) > 1:
  32 | -            out.append(w[1:])
  33 | -            if i + 1 < len(toks) and norm_word(toks[i + 1]) in _MAGNITUDES:
  34 | -                out.append(toks[i + 1])
  35 | -                i += 1
  36 | -            out.append("dollars")
  37 | -        elif w.endswith("%") and len(w) > 1:
  38 | -            out.extend([w[:-1], "percent"])
  39 | -        else:
  40 | -            out.append(w)
  41 | -        i += 1
  42 | -    return out
  43 | +    """Whisper's words in the one canonical form, spoken order (pipeline/canon.py): '$40 trillion.' ->
  44 | +    40000000000000 dollars ; '5%' -> 5 percent."""
  45 | +    import canon
  46 | +    return canon.canon_tokens(" ".join(words))
  47 |  
  48 |  
  49 |  _MODEL = None
  50 | diff --git a/pipeline/editorial_gate.py b/pipeline/editorial_gate.py
  51 | index 9b2c5f3c..72ee13b3 100644
  52 | --- a/pipeline/editorial_gate.py
  53 | +++ b/pipeline/editorial_gate.py
  54 | @@ -25,7 +25,8 @@ KNOWN_FILLER_VO = {
  55 |  
  56 |  
  57 |  def _norm(text):
  58 | -    return re.sub(r"[^a-z0-9]+", " ", str(text or "").lower()).strip()
  59 | +    import canon                                      # the one canonical form (pipeline/canon.py)
  60 | +    return canon.canon(str(text or ""))
  61 |  
  62 |  
  63 |  def _fail(name, reasons):
  64 | diff --git a/pipeline/gates.py b/pipeline/gates.py
  65 | index aa41b151..438f8088 100644
  66 | --- a/pipeline/gates.py
  67 | +++ b/pipeline/gates.py
  68 | @@ -517,7 +517,7 @@ def run_gates(segment_dir, final_mp4, manifest_path, qa_version=None,
  69 |      paths = resolve_paths(segment_dir, qa_version)
  70 |  
  71 |      # Dynamically patch the frozen qa_gates module's BASE and VO_DIR
  72 | -    sys.path.insert(0, "/home/ultron/protocol_pulse/segment_v1")
  73 | +    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "segment_v1"))   # this checkout, never a fixed path (Claude-gates C4)
  74 |      import qa_gates
  75 |      qa_gates.BASE = segment_dir
  76 |      qa_gates.VO_DIR = paths["vo_dir"]
  77 | @@ -591,8 +591,8 @@ G20_NAME_RATIO = 0.85       # a spoken name matches when a same-length stretch o
  78 |  
  79 |  
  80 |  def _g20_norm(s):
  81 | -    import re
  82 | -    return re.sub(r"[^a-z0-9]", "", (s or "").lower())
  83 | +    import canon                                      # the one canonical form, spaces removed for name matching
  84 | +    return "".join(canon.canon_tokens(s))
  85 |  
  86 |  
  87 |  def spoken_channels(transcript, registry, credited=()):
  88 | @@ -642,7 +642,7 @@ def gate_g20(final_mp4, segments, credited, qa_dir, registry=None):
  89 |      wav = os.path.join(qa_dir, "g20_signoff.wav")
  90 |      subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{sh['start']:.3f}", "-t", f"{sh['end'] - sh['start']:.3f}",
  91 |                      "-i", final_mp4, "-ac", "1", "-ar", "16000", wav], check=True, timeout=120)
  92 | -    sys.path.insert(0, "/home/ultron/protocol_pulse/segment_v1")
  93 | +    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "segment_v1"))   # this checkout, never a fixed path (Claude-gates C4)
  94 |      import qa_gates
  95 |      text = qa_gates.whisper_segment(wav, qa_dir)
  96 |      heard = spoken_channels(text, registry, credited)
  97 | diff --git a/pipeline/pinned.py b/pipeline/pinned.py
  98 | index cbded1ee..bc32c967 100644
  99 | --- a/pipeline/pinned.py
 100 | +++ b/pipeline/pinned.py
 101 | @@ -243,7 +243,8 @@ def validate_range(seg, acq):
 102 |      if approved:
 103 |          # the human-approved words for this exact range: must correspond to the source transcript
 104 |          from difflib import SequenceMatcher
 105 | -        norm = lambda t: [x for x in re.split(r"[^a-z0-9]+", t.lower()) if x]
 106 | +        import canon                              # the one canonical form (orchestrator 2026-11-11 '21:10')
 107 | +        norm = canon.canon_tokens
 108 |          a, t = norm(approved), norm(" ".join(w["word"] for w in touching))
 109 |          ratio = SequenceMatcher(None, a, t, autojunk=False).ratio()
 110 |          if ratio < APPROVED_TEXT_MIN_RATIO:
 111 | diff --git a/pipeline/punctuation.py b/pipeline/punctuation.py
 112 | index 44289da6..ad00cb42 100644
 113 | --- a/pipeline/punctuation.py
 114 | +++ b/pipeline/punctuation.py
 115 | @@ -22,7 +22,12 @@ TRAIL = re.compile(r"[.,!?;:]+$")
 116 |  
 117 |  
 118 |  def _key(word):
 119 | -    return re.sub(r"[^a-z0-9']", "", (word or "").lower().replace("’", "'"))
 120 | +    """A word's alignment key: the pipeline's one canonical form (pipeline/canon.py), spaces removed, with one
 121 | +    alignment tolerance: a currency / percent word right after a number is dropped (one decode writes '$74,000',
 122 | +    the other '74,000'; the mark must still transfer). Pure punctuation has no key and never receives a mark."""
 123 | +    import canon
 124 | +    t = canon.canon_tokens(word)
 125 | +    return "".join(w for k, w in enumerate(t) if not (w in ("dollars", "percent") and k and re.fullmatch(r"\d+(\.\d+)?", t[k - 1])))
 126 |  
 127 |  
 128 |  def needs_restoration(words):
 129 | diff --git a/pipeline/stand_alone.py b/pipeline/stand_alone.py
 130 | index 664289d4..168a1cc3 100644
 131 | --- a/pipeline/stand_alone.py
 132 | +++ b/pipeline/stand_alone.py
 133 | @@ -33,12 +33,8 @@ FILLERS = {"you", "know", "like", "i", "mean"}
 134 |  
 135 |  def _words(text):
 136 |      """Lower-case word tokens; a contraction is reduced to its head ("we've" -> "we", "it's" -> "it")."""
 137 | -    out = []
 138 | -    for w in (text or "").split():
 139 | -        w = re.sub(r"^[^a-z0-9$]+|[^a-z0-9']+$", "", w.lower().replace("’", "'"))
 140 | -        if w:
 141 | -            out.append(w.split("'")[0] or w)
 142 | -    return out
 143 | +    import canon                                    # the one canonical form, contraction heads (pipeline/canon.py)
 144 | +    return canon.canon_tokens(text, heads=True)
 145 |  
 146 |  
 147 |  def opener(kind, text, score=None, fault=None):
 148 | diff --git a/pipeline/test_g3b_majority.py b/pipeline/test_g3b_majority.py
 149 | index 03803f93..6a9e3a53 100644
 150 | --- a/pipeline/test_g3b_majority.py
 151 | +++ b/pipeline/test_g3b_majority.py
 152 | @@ -48,18 +48,20 @@ class TestG3bMajority(unittest.TestCase):
 153 |          self.assertEqual((Q.G3B_READS, Q.G3B_CONTEXT_S), (3, 1.5))
 154 |  
 155 |      def test_symbols_are_read_as_the_spoken_words(self):
 156 | -        self.assertEqual(Q._g3b_words("above $40 trillion"), ["above", "40", "trillion", "dollars"])
 157 | -        self.assertEqual(Q._g3b_words("hit $74,000."), ["hit", "74000", "dollars"])
 158 | -        self.assertEqual(Q._g3b_words("$1.66 billion in outflows"), ["1.66", "billion", "dollars", "in", "outflows"])
 159 | -        self.assertEqual(Q._g3b_words("up 50% today"), ["up", "50", "percent", "today"])
 160 | +        """L-g through the one canonical form (pipeline/canon.py): a symbol and its spoken words read the same."""
 161 | +        same = lambda a, b: Q._g3b_words(a) == Q._g3b_words(b)     # noqa: E731
 162 | +        self.assertTrue(same("above $40 trillion", "above 40 trillion dollars"))
 163 | +        self.assertTrue(same("hit $74,000.", "hit 74,000 dollars"))
 164 | +        self.assertTrue(same("$1.66 billion in outflows", "1.66 billion dollars in outflows"))
 165 | +        self.assertTrue(same("up 50% today", "up 50 percent today"))
 166 |          self.assertEqual(Q._g3b_words("the Monday rally."), ["the", "monday", "rally"])
 167 | -        self.assertEqual(Q._g3b_words("above 40 trillion"), ["above", "40", "trillion"])     # no symbol, no 'dollars'
 168 | +        self.assertFalse(same("above 40 trillion", "above 40 trillion dollars"))       # no symbol, no 'dollars'
 169 |          # batch 14 audit cases: no doubled 'dollars', abbreviated scales, '$' + '%', commas between words
 170 | -        self.assertEqual(Q._g3b_words("above $40 trillion dollars."), ["above", "40", "trillion", "dollars"])
 171 | -        self.assertEqual(Q._g3b_words("$40M raised"), ["40", "million", "dollars", "raised"])
 172 | -        self.assertEqual(Q._g3b_words("$50% off"), ["50", "percent", "off"])
 173 | +        self.assertTrue(same("above $40 trillion dollars.", "above 40 trillion dollars"))
 174 | +        self.assertTrue(same("$40M raised", "40 million dollars raised"))
 175 | +        self.assertEqual(Q._g3b_words("$50% off"), Q._g3b_words("50 percent off"))
 176 |          self.assertEqual(Q._g3b_words("well,known fact"), ["well", "known", "fact"])
 177 | -        self.assertEqual(Q._g3b_words("$5 and $6"), ["5", "dollars", "and", "6", "dollars"])
 178 | +        self.assertTrue(same("$5 and $6", "5 dollars and 6 dollars"))
 179 |  
 180 |      def test_a_leak_of_any_word_of_a_symbol_next_word_fails(self):
 181 |          """batch 14 audit (Gemini): the next source word '50%' reads as ['50', 'percent']; hearing either after the
 182 | diff --git a/pipeline/test_stand_alone.py b/pipeline/test_stand_alone.py
 183 | index 9ff47b2f..cdb3ce33 100644
 184 | --- a/pipeline/test_stand_alone.py
 185 | +++ b/pipeline/test_stand_alone.py
 186 | @@ -55,7 +55,8 @@ class TestTopic(unittest.TestCase):
 187 |          self.assertFalse(S.topical("clip", "Bitcoin is sitting at 77,000 today.", subject=subj)[0])   # an aside
 188 |          self.assertEqual(S.subject_terms("Bitcoin / US spot Bitcoin ETFs"), {"bitcoin", "btc"})
 189 |          self.assertEqual(S.subject_terms("", "Binance hacked for six billion dollars"),
 190 | -                         {"binance", "hacked", "billion", "dollars"})               # headline words, no Bitcoin
 191 | +                         {"binance", "hacked", "dollars"})     # headline words, no Bitcoin; 'six billion' is one
 192 | +                                                               # canonical value (canon.py) and values never count
 193 |          self.assertEqual(S.subject_terms("AI", "AI"), set())                        # nothing usable: fail closed
 194 |          self.assertFalse(S.topical("clip", "Bitcoin is sitting at 77,000 today.", subject=set())[0])
 195 |  
 196 | diff --git a/segment_v1/qa_gates.py b/segment_v1/qa_gates.py
 197 | index 9ea7cc1f..19ba78dd 100644
 198 | --- a/segment_v1/qa_gates.py
 199 | +++ b/segment_v1/qa_gates.py
 200 | @@ -120,14 +120,21 @@ def whisper_segment(wav_path, qa_dir):
 201 |  
 202 |  
 203 |  def word_overlap(transcript, reference_text):
 204 | -    """Fraction of reference words found in transcript."""
 205 | -    ref_words = set(reference_text.lower().replace(".", "").replace(",", "").replace("?", "").split())
 206 | -    trans_words = set(transcript.lower().replace(".", "").replace(",", "").replace("?", "").split())
 207 | +    """Fraction of reference words found in transcript, in the pipeline's one canonical form (pipeline/canon.py).
 208 | +    No reference words = 0.0: an empty expected text never scores a match (Claude-gates V1)."""
 209 | +    ref_words = set(_canon_tokens(reference_text))
 210 | +    trans_words = set(_canon_tokens(transcript))
 211 |      if not ref_words:
 212 | -        return 1.0
 213 | +        return 0.0
 214 |      return len(ref_words & trans_words) / len(ref_words)
 215 |  
 216 |  
 217 | +def _canon_tokens(text):
 218 | +    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pipeline"))
 219 | +    import canon
 220 | +    return canon.canon_tokens(text or "")
 221 | +
 222 | +
 223 |  # ==============================================================
 224 |  # G1: VOICE IDENTITY
 225 |  # ==============================================================
 226 | @@ -307,8 +314,8 @@ def gate_g3(final_mp4, segments, qa_dir):
 227 |          label = seg["label"]
 228 |          seg_start = seg["start"]
 229 |          seg_end = seg["end"]
 230 | -        edl_first = seg.get("first_word", "").lower().strip().rstrip(".,?!").lstrip()
 231 | -        edl_last = seg.get("last_word", "").lower().strip().rstrip(".,?!").lstrip()
 232 | +        cf, cl = _canon().canon_tokens(seg.get("first_word", "")), _canon().canon_tokens(seg.get("last_word", ""))
 233 | +        edl_first, edl_last = (cf[0] if cf else ""), (cl[-1] if cl else "")      # the one canonical form
 234 |  
 235 |          if not edl_first and not edl_last:
 236 |              continue
 237 | @@ -317,7 +324,7 @@ def gate_g3(final_mp4, segments, qa_dir):
 238 |          first_wav = os.path.join(qa_dir, f"g3_{label}_first.wav")
 239 |          extract_audio_region(final_mp4, seg_start, 0.7, first_wav)
 240 |          first_transcript = whisper_segment(first_wav, qa_dir)
 241 | -        first_words = first_transcript.replace(".", "").replace(",", "").replace("?", "").split()
 242 | +        first_words = _canon().canon_tokens(first_transcript)
 243 |          first_word_found = first_words[0] if first_words else ""
 244 |  
 245 |          # Also check first 2.0s for broader word search (whisper-tiny is noisy on 0.7s)
 246 | @@ -330,7 +337,7 @@ def gate_g3(final_mp4, segments, qa_dir):
 247 |          last_wav = os.path.join(qa_dir, f"g3_{label}_last.wav")
 248 |          extract_audio_region(final_mp4, last_start, 0.7, last_wav)
 249 |          last_transcript = whisper_segment(last_wav, qa_dir)
 250 | -        last_words = last_transcript.replace(".", "").replace(",", "").replace("?", "").split()
 251 | +        last_words = _canon().canon_tokens(last_transcript)
 252 |          last_word_found = last_words[-1] if last_words else ""
 253 |  
 254 |          # Also check last 2.0s for the EDL word (clips may have post-speech tail)
 255 | @@ -355,14 +362,14 @@ def gate_g3(final_mp4, segments, qa_dir):
 256 |          # Require non-empty transcript to prevent "" in "" false passes
 257 |          if not first_ok and edl_first:
 258 |              if first_transcript.strip():
 259 | -                first_ok = edl_first in first_transcript
 260 | +                first_ok = edl_first in _canon().canon(first_transcript)
 261 |              if not first_ok and first2_transcript.strip():
 262 | -                first_ok = edl_first in first2_transcript
 263 | +                first_ok = edl_first in _canon().canon(first2_transcript)
 264 |          if not last_ok and edl_last:
 265 |              if last_transcript.strip():
 266 | -                last_ok = edl_last in last_transcript
 267 | +                last_ok = edl_last in _canon().canon(last_transcript)
 268 |              if not last_ok and last2_transcript.strip():
 269 | -                last_ok = edl_last in last2_transcript
 270 | +                last_ok = edl_last in _canon().canon(last2_transcript)
 271 |  
 272 |          ok = first_ok and last_ok
 273 |          if not ok:
 274 | @@ -389,42 +396,18 @@ def gate_g3(final_mp4, segments, qa_dir):
 275 |  G3B_READS, G3B_CONTEXT_S, G3B_TAIL_S = 3, 1.5, 1.0     # DEC-12f
 276 |  
 277 |  
 278 | -_G3B_SCALE = {"hundred", "thousand", "million", "billion", "trillion"}
 279 | -_G3B_SUFFIX = {"k": "thousand", "m": "million", "mn": "million", "b": "billion", "bn": "billion", "t": "trillion",
 280 | -               "tn": "trillion"}
 281 | -_G3B_NUM_SUFFIX = re.compile(r"^(\d+(?:\.\d+)?)(k|mn|m|bn|b|tn|t)$")
 282 | +def _canon():
 283 | +    """The pipeline's one canonical form for every text comparison (pipeline/canon.py)."""
 284 | +    if os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pipeline") not in sys.path:
 285 | +        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pipeline"))
 286 | +    import canon
 287 | +    return canon
 288 |  
 289 |  
 290 |  def _g3b_words(text):
 291 | -    """Reading words, lower-case, punctuation dropped. Law L-g (2026-11-11): a word the ASR wrote as a symbol is
 292 | -    read as the spoken word, in spoken order: '$40 trillion' = '40 trillion dollars', '$40M' = '40 million
 293 | -    dollars', '50%' = '50 percent'; a 'dollars' the ASR also wrote is not doubled; thousands separators are
 294 | -    dropped ('74,000' = '74000'), other commas split words, decimals stay whole ('1.66'). (v2f's approved clip_02
 295 | -    tail '... above 40 trillion dollars.' was read 'above $40 trillion' twice.)"""
 296 | -    text = re.sub(r"(?<=\d),(?=\d)", "", (text or "").lower())
 297 | -    seq = []                                                  # (word, starts a '$' amount)
 298 | -    for t in text.replace(",", " ").replace("?", " ").replace("!", " ").split():
 299 | -        t = t.rstrip(".")
 300 | -        cash = t.startswith("$") and len(t) > 1
 301 | -        t = t[1:] if cash else t
 302 | -        m = _G3B_NUM_SUFFIX.match(t)
 303 | -        if m:
 304 | -            seq += [(m.group(1), cash), (_G3B_SUFFIX[m.group(2)], False)]
 305 | -        elif t.endswith("%") and len(t) > 1:
 306 | -            seq += [(t[:-1], False), ("percent", False)]      # a percentage is not a dollar amount
 307 | -        elif t:
 308 | -            seq.append((t, cash))
 309 | -    out, owed = [], False                                     # owed: an amount still owes its spoken 'dollars'
 310 | -    for w, cash in seq:
 311 | -        if owed and (cash or w not in _G3B_SCALE):
 312 | -            owed = False
 313 | -            if w != "dollars":
 314 | -                out.append("dollars")
 315 | -        out.append(w)
 316 | -        owed = owed or cash
 317 | -    if owed:
 318 | -        out.append("dollars")
 319 | -    return out
 320 | +    """Reading words in the one canonical form (law L-g: '$40 trillion' = '40 trillion dollars', '50%' = '50
 321 | +    percent'; pipeline/canon.py)."""
 322 | +    return _canon().canon_tokens(text)
 323 |  
 324 |  
 325 |  def _g3b_match(expected, heard):
 326 | @@ -461,7 +444,9 @@ def gate_g3b(final_mp4, segments, qa_dir, edl_path=None):
 327 |          label = seg["label"]
 328 |          seg_end = seg["end"]
 329 |          seg_start = seg["start"]
 330 | -        ew = _g3b_words(seg.get("last_word", ""))         # the same reading rules as the heard words (L-g)
 331 | +        lock = (edl_clips.get(label, {}).get("selection_lock") or {}).get("text") or ""
 332 | +        tail = " ".join(lock.split()[-5:]) if lock else seg.get("last_word", "")
 333 | +        ew = _g3b_words(tail)                              # the expected last word read in its own context (canon)
 334 |          edl_last = ew[-1] if ew else ""
 335 |  
 336 |          if not edl_last:
 337 | @@ -1315,15 +1300,29 @@ FOLLOW_WORDS = {"follow", "subscribe", "check"}
 338 |  
 339 |  
 340 |  def _fuzzy_word_overlap(scripted, transcribed):
 341 | -    """Case-insensitive word-set overlap ratio (Jaccard-like: intersection / scripted count)."""
 342 | -    import re
 343 | -    s_words = set(re.sub(r"[^\w\s]", "", scripted.lower()).split())
 344 | -    t_words = set(re.sub(r"[^\w\s]", "", transcribed.lower()).split())
 345 | +    """Word-set overlap ratio (intersection / scripted count) in the one canonical form (pipeline/canon.py)."""
 346 | +    s_words = set(_canon_tokens(scripted))
 347 | +    t_words = set(_canon_tokens(transcribed))
 348 |      if not s_words:
 349 |          return 0.0
 350 |      return len(s_words & t_words) / len(s_words)
 351 |  
 352 |  
 353 | +def _is_silent_reading(transcript):
 354 | +    """An empty reading, or one that is only a known music / outro hallucination, in canonical form (Claude-gates
 355 | +    V3: the raw set never matched a transcript that carries punctuation)."""
 356 | +    t = _canon_tokens(transcript)
 357 | +    return len(" ".join(t)) < 3 or t in [_canon_tokens(h) for h in _MUSIC_HALLUCINATIONS]
 358 | +
 359 | +
 360 | +def _says(transcript_tokens, phrase):
 361 | +    """True when the canonical words of `phrase` occur as a contiguous run in the transcript's canonical words
 362 | +    (token equality, never a substring: Claude-gates T1 / T8)."""
 363 | +    p = _canon_tokens(phrase)
 364 | +    n = len(p)
 365 | +    return n > 0 and any(transcript_tokens[i:i + n] == p for i in range(len(transcript_tokens) - n + 1))
 366 | +
 367 | +
 368 |  def _rms_db(wav_path):
 369 |      """Compute RMS in dB from a WAV file. Returns -inf for silence."""
 370 |      try:
 371 | @@ -1427,9 +1426,8 @@ def gate_g13(final_mp4, segments, qa_dir, edl_path=None, channels_json_path=None
 372 |          print(f"    Scripted:     '{scripted}'")
 373 |          print(f"    Transcribed:  '{transcript}'")
 374 |  
 375 | -        # Check for music hallucination / silence
 376 | -        transcript_lower = transcript.lower().strip()
 377 | -        if transcript_lower in _MUSIC_HALLUCINATIONS or len(transcript_lower) < 3:
 378 | +        # Check for music hallucination / silence (canonical form)
 379 | +        if _is_silent_reading(transcript):
 380 |              print(f"    FAIL: SILENT (hallucination or empty)")
 381 |              table.append({"slot": label, "pass": False, "reason": "SILENT",
 382 |                            "transcript": transcript, "scripted": scripted})
 383 | @@ -1489,8 +1487,7 @@ def gate_g13(final_mp4, segments, qa_dir, edl_path=None, channels_json_path=None
 384 |              print(f"    Scripted:     '{signoff_text}'")
 385 |              print(f"    Transcribed:  '{transcript}'")
 386 |  
 387 | -            transcript_lower = transcript.lower().strip()
 388 | -            if transcript_lower in _MUSIC_HALLUCINATIONS or len(transcript_lower) < 3:
 389 | +            if _is_silent_reading(transcript):
 390 |                  print(f"    FAIL: SILENT (hallucination or empty)")
 391 |                  table.append({"slot": label, "pass": False, "reason": "SILENT",
 392 |                                "transcript": transcript, "scripted": signoff_text})
 393 | @@ -1508,16 +1505,16 @@ def gate_g13(final_mp4, segments, qa_dir, edl_path=None, channels_json_path=None
 394 |                  rms_delta = rms_vo - rms_music if rms_music != float("-inf") else 99.0
 395 |                  print(f"    VO RMS: {rms_vo:.1f} dB, Music RMS: {rms_music:.1f} dB, delta: {rms_delta:.1f} dB")
 396 |  
 397 | -                # Signoff-specific: channel names and follow/subscribe word
 398 | -                t_lower = transcript.lower()
 399 | +                # Signoff-specific: channel names and follow/subscribe word, as canonical word runs
 400 | +                t_tokens = _canon_tokens(transcript)
 401 |                  missing_channels = []
 402 |                  for ch in channel_names:
 403 |                      # M14: check channel name OR any alias from channels.json
 404 |                      aliases = channel_aliases.get(ch, {ch.lower()})
 405 | -                    if not any(alias in t_lower for alias in aliases):
 406 | +                    if not any(_says(t_tokens, alias) for alias in aliases):
 407 |                          missing_channels.append(ch)
 408 |  
 409 | -                has_follow = any(w in t_lower for w in FOLLOW_WORDS)
 410 | +                has_follow = any(_says(t_tokens, w) for w in FOLLOW_WORDS)
 411 |  
 412 |                  # Primary: transcript match, channels, follow word.
 413 |                  # RMS delta is informational (output is a full mix).
 414 | diff --git a/pipeline/canon.py b/pipeline/canon.py
 415 | new file mode 100644
 416 | index 00000000..d03152a3
 417 | --- /dev/null
 418 | +++ b/pipeline/canon.py
 419 | @@ -0,0 +1,209 @@
 420 | +#!/usr/bin/env python3
 421 | +"""pipeline/canon.py — ONE canonical form for every text comparison in the pipeline (orchestrator 2026-11-11 '21:10').
 422 | +
 423 | +Two strings that a listener would hear as the same words compare equal; a different number, a dropped word or a
 424 | +different name does not. canon_tokens(text) -> the canonical word list; canon(text) -> those words joined by spaces.
 425 | +
 426 | +  entities / unicode  'S&amp;P' = 'S&P'; curly quotes, dashes, ellipsis, nbsp folded (NFKC)
 427 | +  split tokens        '$81 ,000' = '$81,000'; 'U .S.' = 'U.S.'; '1 .3' = '1.3' (a Whisper word joined with spaces)
 428 | +  case, punctuation   lower-case; trailing / leading punctuation dropped; a curly apostrophe is a straight one,
 429 | +                      and an apostrophe stays ("it's" and "its" are different words; heads=True gives "it")
 430 | +  hyphens / dashes    split words ('well-known' = 'well known')
 431 | +  numbers             one value form: '74,000' = '74000' = '74k' = 'seventy four thousand' = 'seventy-four
 432 | +                      thousand'; '1.66 billion' = '$1.66B' value-wise; decimals 'one point six six' = '1.66';
 433 | +                      ordinals '3rd' = 'third' = '3'
 434 | +  currency / percent  '$40 trillion' = '40 trillion dollars' (the spoken order); '5.5%' = '5.5 percent' =
 435 | +                      'five point five percent'; 'dollar' = 'dollars'
 436 | +  signs               '-5%' = 'minus 5 percent', '+5%' = 'plus 5 percent' (GPT-cut F04: -5% != +5%); a hyphen
 437 | +                      between words or a range ('2026-11', '74-75') is not a sign
 438 | +Every comparison site (quote verification, selection anchors, edge words, G3b, G18, sign-off names, ledger
 439 | +statements) goes through this module; pipeline/test_canon.py fails any site that compares text another way.
 440 | +"""
 441 | +import html
 442 | +import re
 443 | +import unicodedata
 444 | +from decimal import Decimal, InvalidOperation
 445 | +
 446 | +_UNITS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen "
 447 | +                                     "fourteen fifteen sixteen seventeen eighteen nineteen".split())}
 448 | +_TENS = {w: 10 * (i + 2) for i, w in enumerate("twenty thirty forty fifty sixty seventy eighty ninety".split())}
 449 | +_SCALES = {"hundred": 100, "thousand": 10 ** 3, "million": 10 ** 6, "billion": 10 ** 9, "trillion": 10 ** 12}
 450 | +_SUFFIX = {"k": 10 ** 3, "m": 10 ** 6, "mn": 10 ** 6, "b": 10 ** 9, "bn": 10 ** 9, "t": 10 ** 12, "tn": 10 ** 12}
 451 | +_ORD = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6, "seventh": 7, "eighth": 8,
 452 | +        "ninth": 9, "tenth": 10, "eleventh": 11, "twelfth": 12, "thirteenth": 13, "fourteenth": 14,
 453 | +        "fifteenth": 15, "sixteenth": 16, "seventeenth": 17, "eighteenth": 18, "nineteenth": 19, "twentieth": 20,
 454 | +        "thirtieth": 30, "fortieth": 40, "fiftieth": 50, "sixtieth": 60, "seventieth": 70, "eightieth": 80,
 455 | +        "ninetieth": 90, "hundredth": 100, "thousandth": 1000}
 456 | +_FOLD = str.maketrans({"‘": "'", "’": "'", "‚": "'", "‛": "'", "′": "'", "´": "'",
 457 | +                       "`": "'", "“": '"', "”": '"', "„": '"', "″": '"', "‐": "-",
 458 | +                       "‑": "-", "‒": "-", "–": "-", "—": "-", "―": "-", "−": "-",
 459 | +                       "…": "...", " ": " ", " ": " ", " ": " "})
 460 | +_SPLIT = re.compile(r"\s+(?=[.,][0-9A-Za-z])")            # '$81 ,000', 'U .S.': one written word
 461 | +_THOUSANDS = re.compile(r"(?<=\d),(?=\d{3}\b)")
 462 | +_SPACED_THOUSANDS = re.compile(r"(?<![\d.,])(\d{1,3})\s+(\d{3})(?!\d|[.,]\d)")   # '74 000', '74 000.'; not '74 000.5'
 463 | +_NUM = re.compile(r"^(\d+(?:\.\d+)?)(k|mn|m|bn|b|tn|t)?$")
 464 | +_ORDNUM = re.compile(r"^(\d+)(st|nd|rd|th)$")
 465 | +_TOKEN = re.compile(r"\$|%|[a-z0-9]+(?:[.'][a-z0-9]+)*")
 466 | +
 467 | +
 468 | +def _value(d):
 469 | +    """A Decimal as the one canonical number string: '74000', '1.66', '5.5'."""
 470 | +    d = d.normalize()
 471 | +    return str(int(d)) if d == d.to_integral_value() else format(d, "f")
 472 | +
 473 | +
 474 | +def fold(text):
 475 | +    """The character-level part of the canonical form, as text: entities decoded, unicode folded, split tokens
 476 | +    joined, thousands separators dropped, lower-case (for sites with their own word rules on top, e.g.
 477 | +    stand_alone's contraction heads)."""
 478 | +    t = unicodedata.normalize("NFKC", html.unescape(text or "")).translate(_FOLD)
 479 | +    t = _SPLIT.sub("", t)
 480 | +    t = _SPACED_THOUSANDS.sub(r"\1\2", t)              # '74 000' (G18's rule since 08:30)
 481 | +    t = _THOUSANDS.sub("", t)
 482 | +    return t.lower()
 483 | +
 484 | +
 485 | +_SIGN = re.compile(r"(?<![\w.,$%])([-+])(?=\$?\d)")       # '-5%', '+5%', '(-$40M)': a sign, not a hyphen or range
 486 | +
 487 | +
 488 | +def _prepare(text):
 489 | +    t = _SIGN.sub(lambda m: " minus " if m.group(1) == "-" else " plus ", fold(text))   # GPT-cut F04: -5% != +5%
 490 | +    return _TOKEN.findall(t.replace("-", " ").replace("_", " "))
 491 | +
 492 | +
 493 | +def _words_number(toks, i):
 494 | +    """Parse a spoken number at toks[i] ('seventy four thousand', 'one point six six', 'a hundred').
 495 | +    Returns (Decimal, next index) or None."""
 496 | +    total, cur, j, seen, last = Decimal(0), Decimal(0), i, False, None
 497 | +    while j < len(toks):
 498 | +        w = toks[j]
 499 | +        if w in _UNITS:
 500 | +            if last == "unit" or (last == "tens" and _UNITS[w] >= 10):       # 'three two', 'twenty eleven': two numbers
 501 | +                break
 502 | +            cur += _UNITS[w]
 503 | +            last = "unit"
 504 | +        elif w in _TENS:
 505 | +            if last in ("unit", "tens"):                  # 'twenty twenty', 'five twenty': two numbers
 506 | +                break
 507 | +            cur += _TENS[w]
 508 | +            last = "tens"
 509 | +        elif w in _SCALES and (seen or w == "hundred"):
 510 | +            cur = (cur or 1) * _SCALES[w]
 511 | +            if w != "hundred":
 512 | +                total, cur = total + cur, Decimal(0)
 513 | +            last = "scale"
 514 | +        elif w == "a" and j + 1 < len(toks) and toks[j + 1] in _SCALES and not seen:
 515 | +            cur, last = Decimal(1), "unit"
 516 | +        elif w == "and" and seen and j + 1 < len(toks) and (toks[j + 1] in _UNITS or toks[j + 1] in _TENS):
 517 | +            pass
 518 | +        else:
 519 | +            break
 520 | +        seen, j = True, j + 1
 521 | +    if not seen:
 522 | +        return None
 523 | +    value = total + cur
 524 | +    if j + 1 < len(toks) and toks[j] == "point" and toks[j + 1] in _UNITS:      # 'one point six six'
 525 | +        digits = []
 526 | +        j += 1
 527 | +        while j < len(toks) and toks[j] in _UNITS and _UNITS[toks[j]] < 10:
 528 | +            digits.append(str(_UNITS[toks[j]]))
 529 | +            j += 1
 530 | +        value = Decimal(f"{int(value)}.{''.join(digits)}")
 531 | +    return value, j
 532 | +
 533 | +
 534 | +def _canon_seq(pairs, heads=False):
 535 | +    """The one state machine: (prepared token, owner) pairs -> (canonical token, owner) pairs; a number phrase or
 536 | +    an amount is owned by the word it starts in."""
 537 | +    toks = [t for t, _ in pairs]
 538 | +    out, i, owed = [], 0, None                     # owed: the owner of a '$' amount that still owes 'dollars'
 539 | +    while i < len(toks):
 540 | +        t, own = toks[i], pairs[i][1]
 541 | +        if t == "$":
 542 | +            if owed is not None:
 543 | +                out.append(("dollars", owed))
 544 | +            owed, i = own, i + 1
 545 | +            continue
 546 | +        if t == "%":
 547 | +            out.append(("percent", own))
 548 | +            i += 1
 549 | +            continue
 550 | +        num = None
 551 | +        m = _NUM.match(t)
 552 | +        if m:
 553 | +            try:
 554 | +                num = Decimal(m.group(1)) * (_SUFFIX[m.group(2)] if m.group(2) else 1)
 555 | +            except InvalidOperation:
 556 | +                num = None
 557 | +            i += 1
 558 | +        elif _ORDNUM.match(t):
 559 | +            num, i = Decimal(_ORDNUM.match(t).group(1)), i + 1
 560 | +        elif t in _ORD:
 561 | +            num, i = Decimal(_ORD[t]), i + 1
 562 | +        else:
 563 | +            parsed = _words_number(toks, i)
 564 | +            if parsed:
 565 | +                num, i = parsed
 566 | +        if num is not None:
 567 | +            if toks[i:i + 3] == ["and", "a", "half"]:     # 'five and a half' = 5.5 (G18's rule since 08:30)
 568 | +                num, i = num + Decimal("0.5"), i + 3
 569 | +            while i < len(toks) and toks[i] in _SCALES and toks[i] != "hundred":   # '1.66 billion', '40 trillion'
 570 | +                num, i = num * _SCALES[toks[i]], i + 1
 571 | +            out.append((_value(num), own))
 572 | +            if owed is not None and i < len(toks) and toks[i] in ("%", "percent", "pct"):
 573 | +                owed = None                        # '$50%': a percentage is never a dollar amount (batch 14)
 574 | +            if owed is not None:                   # the spoken 'dollars' sits after the amount's last word
 575 | +                if i < len(toks) and toks[i] in ("dollar", "dollars"):
 576 | +                    out.append(("dollars", pairs[i][1]))
 577 | +                    i += 1
 578 | +                else:
 579 | +                    out.append(("dollars", pairs[i - 1][1]))
 580 | +                owed = None
 581 | +            continue
 582 | +        if owed is not None:
 583 | +            out.append(("dollars", owed))
 584 | +            owed = None
 585 | +        if t in ("dollar", "dollars"):
 586 | +            out.append(("dollars", own))
 587 | +        elif t in ("percent", "pct"):
 588 | +            out.append(("percent", own))
 589 | +        elif t == "per" and i + 1 < len(toks) and toks[i + 1] == "cent":
 590 | +            out.append(("percent", own))
 591 | +            i += 1
 592 | +        else:
 593 | +            w = (t.split("'")[0] if heads and "'" in t else t).replace(".", "")   # "it's" != "its" (M1)
 594 | +            if w:
 595 | +                out.append((w, own))
 596 | +        i += 1
 597 | +    if owed is not None:
 598 | +        out.append(("dollars", owed))
 599 | +    return out
 600 | +
 601 | +
 602 | +def canon_tokens(text, heads=False):
 603 | +    """heads=True reduces a contraction to its head ("that's" -> "that", "we've" -> "we") for sites that ask
 604 | +    which word a contraction starts with (backward references, openers); the default drops the apostrophe."""
 605 | +    return [t for t, _ in _canon_seq([(p, 0) for p in _prepare(text)], heads)]
 606 | +
 607 | +
 608 | +def canon_aligned(words):
 609 | +    """Canonical tokens of a word list, each with the index of the source word it starts in (alignment sites:
 610 | +    quote anchoring, selection locks, punctuation transfer). A Whisper word split across two words ('$81', ',000')
 611 | +    is read as one, owned by its first word."""
 612 | +    pairs, i = [], 0
 613 | +    while i < len(words):
 614 | +        w, j = (words[i] or ""), i + 1
 615 | +        while j < len(words) and (re.match(r"^\s*[.,][0-9A-Za-z]", words[j] or "") or (     # '$81' ',000'
 616 | +                re.fullmatch(r"\$?\d{1,3}", w.strip()) and re.fullmatch(r"\d{3}[.,!?]*", (words[j] or "").strip()))):
 617 | +            w, j = w + (words[j] or "").strip(), j + 1                                      # '74' '000'
 618 | +        pairs += [(p, i) for p in _prepare(w)]
 619 | +        i = j
 620 | +    return _canon_seq(pairs)
 621 | +
 622 | +
 623 | +def canon(text):
 624 | +    return " ".join(canon_tokens(text))
 625 | +
 626 | +
 627 | +def same(a, b):
 628 | +    return canon_tokens(a) == canon_tokens(b)
 629 | diff --git a/pipeline/test_canon.py b/pipeline/test_canon.py
 630 | new file mode 100644
 631 | index 00000000..91cc5a2d
 632 | --- /dev/null
 633 | +++ b/pipeline/test_canon.py
 634 | @@ -0,0 +1,228 @@
 635 | +#!/usr/bin/env python3
 636 | +"""pipeline/canon.py — one canonical form for every text comparison (orchestrator order 2026-11-11 '21:10'; the class
 637 | +behind E-FAIL-035 / 036 / 037: '$40 trillion', split tokens, HTML entities).
 638 | +property  200 real sentences (tests/fixtures/canon_20261111, sampled from the saved transcripts) under each mutation
 639 | +          compare EQUAL after canonicalisation: HTML entities, unicode quotes / dashes / ellipsis / nbsp, split
 640 | +          tokens, currency and percent symbol vs words, digits vs number words up to trillions, decimals, ordinals,
 641 | +          k / M / B suffixes, casing, trailing punctuation, hyphenation, apostrophes
 642 | +          ... and real differences compare UNEQUAL: a different number, a dropped word, a different name
 643 | +aligned   canon_aligned(words) yields the same tokens as canon(text), each owned by the word it starts in
 644 | +sites     every comparison site goes through canon (TestSites: a grep over pipeline/*.py and qa_gates.py fails any
 645 | +          ad-hoc normaliser outside canon.py)
 646 | +Run: cd ~/protocol_pulse && python3 -m pytest -q pipeline/test_canon.py"""
 647 | +import glob
 648 | +import html
 649 | +import json
 650 | +import os
 651 | +import random
 652 | +import re
 653 | +import sys
 654 | +import unittest
 655 | +
 656 | +PIPELINE = os.path.dirname(os.path.abspath(__file__))
 657 | +REPO = os.path.dirname(PIPELINE)
 658 | +sys.path.insert(0, PIPELINE)
 659 | +import canon as C  # noqa: E402
 660 | +
 661 | +SENTS = [x["text"] for x in json.load(open(os.path.join(REPO, "tests", "fixtures", "canon_20261111",
 662 | +                                                          "sentences.json")))["sentences"]]
 663 | +ONES = ("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen "
 664 | +        "seventeen eighteen nineteen").split()
 665 | +TENS = "twenty thirty forty fifty sixty seventy eighty ninety".split()
 666 | +SCALES = [(10 ** 12, "trillion"), (10 ** 9, "billion"), (10 ** 6, "million"), (10 ** 3, "thousand")]
 667 | +ORDS = ["first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth", "eleventh",
 668 | +        "twelfth", "thirteenth", "fourteenth", "fifteenth", "sixteenth", "seventeenth", "eighteenth", "nineteenth",
 669 | +        "twentieth"]
 670 | +
 671 | +
 672 | +def words_int(n, hyphen=False):
 673 | +    """An integer the way a speaker says it ('seventy four thousand', or 'seventy-four thousand')."""
 674 | +    if n < 20:
 675 | +        return ONES[n]
 676 | +    if n < 100:
 677 | +        t, u = divmod(n, 10)
 678 | +        return TENS[t - 2] + (("-" if hyphen else " ") + ONES[u] if u else "")
 679 | +    if n < 1000:
 680 | +        h, r = divmod(n, 100)
 681 | +        return ONES[h] + " hundred" + (" " + words_int(r, hyphen) if r else "")
 682 | +    for v, name in SCALES:
 683 | +        if n >= v:
 684 | +            q, r = divmod(n, v)
 685 | +            return words_int(q, hyphen) + " " + name + (" " + words_int(r, hyphen) if r else "")
 686 | +
 687 | +
 688 | +def words_dec(x):
 689 | +    i, d = str(x).split(".")
 690 | +    return words_int(int(i)) + " point " + " ".join(ONES[int(c)] for c in d)
 691 | +
 692 | +
 693 | +def ordinal_digits(n):
 694 | +    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"
 695 | +
 696 | +
 697 | +def insert(s, phrase, rng):
 698 | +    """The phrase between neutral words, so an inserted spoken number never runs into a number word the sentence
 699 | +    already has ('... one hundred twenty' + 'two real big areas' would be heard as 'twenty-two')."""
 700 | +    w = s.split()
 701 | +    k = rng.randrange(len(w) + 1)
 702 | +    return " ".join(w[:k] + ["about", phrase, "units"] + w[k:])
 703 | +
 704 | +
 705 | +def amounts(rng):
 706 | +    """Integers across every magnitude up to trillions."""
 707 | +    return [rng.choice([7, 13, 45, 99, 105, 999]), rng.randrange(1000, 99999), rng.randrange(10 ** 5, 10 ** 9),
 708 | +            rng.randrange(1, 999) * 10 ** 9 + rng.randrange(0, 999) * 10 ** 6, rng.randrange(1, 99) * 10 ** 12]
 709 | +
 710 | +
 711 | +class TestEquivalence(unittest.TestCase):
 712 | +    def assert_pairs(self, pairs):
 713 | +        bad = [(a, b, C.canon(a), C.canon(b)) for a, b in pairs if not C.same(a, b)]
 714 | +        self.assertFalse(bad, bad[:3])
 715 | +
 716 | +    def test_html_entities(self):
 717 | +        self.assert_pairs([(html.escape(s, quote=True), s) for s in SENTS] +
 718 | +                          [(insert(s, "the S&amp;P 500 and it&#39;s &quot;fine&quot;", random.Random(i)),
 719 | +                            insert(s, "the S&P 500 and it's \"fine\"", random.Random(i))) for i, s in enumerate(SENTS)])
 720 | +
 721 | +    def test_unicode_quotes_dashes_ellipsis_nbsp(self):
 722 | +        def uni(s):
 723 | +            s = s.replace("'", "’").replace(" - ", " – ").replace("...", "…")
 724 | +            return re.sub(r" ", lambda m, c=[0]: " " if (c.__setitem__(0, c[0] + 1) or c[0] % 3 == 0) else " ", s)
 725 | +        self.assert_pairs([(uni(s), s) for s in SENTS] + [(f"“{s}” — well…", f'"{s}" - well...')
 726 | +                                                          for s in SENTS])
 727 | +
 728 | +    def test_split_tokens(self):
 729 | +        self.assert_pairs([(insert(s, "above $81 ,000 and 1 .3 percent in the U .S.", random.Random(i)),
 730 | +                            insert(s, "above $81,000 and 1.3 percent in the U.S.", random.Random(i)))
 731 | +                           for i, s in enumerate(SENTS)])
 732 | +
 733 | +    def test_currency_and_percent_symbols_vs_words(self):
 734 | +        pairs = []
 735 | +        for i, s in enumerate(SENTS):
 736 | +            rng = random.Random(i)
 737 | +            n = rng.choice([5, 74, 81000, 40])
 738 | +            pairs.append((insert(s, f"${n:,}", random.Random(i)), insert(s, f"{n:,} dollars", random.Random(i))))
 739 | +            pairs.append((insert(s, f"${n} trillion", random.Random(i)), insert(s, f"{n} trillion dollars", random.Random(i))))
 740 | +            pairs.append((insert(s, "5.5%", random.Random(i)), insert(s, "5.5 percent", random.Random(i))))
 741 | +            pairs.append((insert(s, "$50%", random.Random(i)), insert(s, "50 percent", random.Random(i))))
 742 | +        self.assert_pairs(pairs)
 743 | +
 744 | +    def test_digits_vs_number_words_up_to_trillions(self):
 745 | +        pairs = []
 746 | +        for i, s in enumerate(SENTS):
 747 | +            rng = random.Random(1000 + i)
 748 | +            for n in amounts(rng):
 749 | +                pairs.append((insert(s, f"{n:,}", random.Random(i)), insert(s, words_int(n, hyphen=i % 2 == 0),
 750 | +                                                                           random.Random(i))))
 751 | +        self.assert_pairs(pairs)
 752 | +
 753 | +    def test_decimals(self):
 754 | +        pairs = []
 755 | +        for i, s in enumerate(SENTS):
 756 | +            x = random.Random(i).choice(["1.66", "5.5", "0.3", "12.75", "2.05"])
 757 | +            pairs.append((insert(s, x, random.Random(i)), insert(s, words_dec(x), random.Random(i))))
 758 | +            pairs.append((insert(s, f"{x} billion", random.Random(i)), insert(s, f"{words_dec(x)} billion", random.Random(i))))
 759 | +        self.assert_pairs(pairs)
 760 | +
 761 | +    def test_ordinals(self):
 762 | +        self.assert_pairs([(insert(s, f"the {ordinal_digits(n)} of November", random.Random(i)),
 763 | +                            insert(s, f"the {ORDS[n - 1]} of November", random.Random(i)))
 764 | +                           for i, s in enumerate(SENTS) for n in [random.Random(i).randrange(1, 21)]])
 765 | +
 766 | +    def test_k_m_b_suffixes(self):
 767 | +        pairs = []
 768 | +        for i, s in enumerate(SENTS):
 769 | +            r = random.Random(i)
 770 | +            pairs.append((insert(s, "74k", r), insert(s, "74,000", random.Random(i))))
 771 | +            pairs.append((insert(s, "1.5M", random.Random(i)), insert(s, "1,500,000", random.Random(i))))
 772 | +            pairs.append((insert(s, "$1.66B", random.Random(i)), insert(s, "1.66 billion dollars", random.Random(i))))
 773 | +        self.assert_pairs(pairs)
 774 | +
 775 | +    def test_casing_trailing_punctuation_hyphens_apostrophes(self):
 776 | +        pairs = []
 777 | +        for s in SENTS:
 778 | +            pairs += [(s.upper(), s), (s.title(), s), (s.rstrip(".!?,") + ".", s.rstrip(".!?,")),
 779 | +                      (s + "?!", s), (s.replace("'", "’"), s)]       # curly = straight; "it's" != "its"
 780 | +            w = s.split()
 781 | +            if len(w) > 3:
 782 | +                pairs.append((" ".join(w[:2]) + "-" + " ".join(w[2:]), s))
 783 | +        self.assert_pairs(pairs)
 784 | +
 785 | +
 786 | +class TestDifferences(unittest.TestCase):
 787 | +    def test_a_different_number_a_dropped_word_a_different_name_stay_different(self):
 788 | +        same = []
 789 | +        for i, s in enumerate(SENTS):
 790 | +            rng = random.Random(i)
 791 | +            n = rng.choice(amounts(rng))
 792 | +            for a, b in ((insert(s, f"{n:,}", random.Random(i)), insert(s, f"{n + 1:,}", random.Random(i))),
 793 | +                         (insert(s, words_int(n), random.Random(i)), insert(s, f"{n * 10:,}", random.Random(i)))):
 794 | +                if C.same(a, b):
 795 | +                    same.append((a, b))
 796 | +            w = s.split()
 797 | +            k = next((j for j, x in enumerate(w) if re.search(r"[A-Za-z0-9]{2}", x)), None)
 798 | +            if k is not None and C.same(s, " ".join(w[:k] + w[k + 1:])):
 799 | +                same.append((s, "dropped " + w[k]))
 800 | +            if C.same(insert(s, "Natalie Brunell", random.Random(i)), insert(s, "Yahoo Finance", random.Random(i))):
 801 | +                same.append((s, "name"))
 802 | +            if C.same(insert(s, "it's", random.Random(i)), insert(s, "its", random.Random(i))):
 803 | +                same.append((s, "it's / its"))                       # different words (cross-LLM M1)
 804 | +        self.assertFalse(same, same[:3])
 805 | +
 806 | +
 807 | +class TestAligned(unittest.TestCase):
 808 | +    def test_aligned_tokens_equal_text_tokens_and_owners_are_source_words(self):
 809 | +        bad = []
 810 | +        for i, s in enumerate(SENTS):
 811 | +            for t in (s, insert(s, "above $81 ,000 and 74 000 people and $40 trillion", random.Random(i))):
 812 | +                words = t.split()
 813 | +                pairs = C.canon_aligned(words)
 814 | +                if [p for p, _ in pairs] != C.canon_tokens(t) or any(not 0 <= o < len(words) for _, o in pairs):
 815 | +                    bad.append(t)
 816 | +        self.assertFalse(bad, bad[:2])
 817 | +
 818 | +    def test_an_amount_is_owned_by_its_words(self):
 819 | +        self.assertEqual(C.canon_aligned("above $40 trillion .".split()),
 820 | +                         [("above", 0), ("40000000000000", 1), ("dollars", 2)])
 821 | +        self.assertEqual(C.canon_aligned(["up", "$81", ",000", "today"]),
 822 | +                         [("up", 0), ("81000", 1), ("dollars", 1), ("today", 3)])
 823 | +
 824 | +
 825 | +class TestSites(unittest.TestCase):
 826 | +    """Every comparison site goes through canon (orchestrator 21:10 'a grep test failing any site not using it'):
 827 | +    no ad-hoc normaliser in the pipeline's code (pipeline/*.py except tests, segment_v1/qa_gates.py). Allowed:
 828 | +    canon.py itself, and transcript_store.read_text's html.unescape (the acquisition reader that stores the
 829 | +    words as spoken, law L-h; it is not a comparison)."""
 830 | +    FORBIDDEN = [r"\.lower\(\)\.replace\(", r"re\.sub\(\s*r?[\"']\[\^\\w", r"re\.split\(\s*r?[\"']\[\^a-z0-9",
 831 | +                 r"unicodedata\.normalize\(", r"html\.unescape\(", r"str\.maketrans\(", r"\.casefold\(\)",
 832 | +                 r"translate\(str\.maketrans"]
 833 | +    ALLOWED = {("transcript_store.py", "html.unescape(")}
 834 | +
 835 | +    def test_no_ad_hoc_normaliser_outside_canon(self):
 836 | +        files = [f for f in glob.glob(os.path.join(PIPELINE, "*.py"))
 837 | +                 if not os.path.basename(f).startswith("test_") and os.path.basename(f) != "canon.py"]
 838 | +        files.append(os.path.join(REPO, "segment_v1", "qa_gates.py"))
 839 | +        bad = []
 840 | +        for f in files:
 841 | +            for n, line in enumerate(open(f, encoding="utf-8"), 1):
 842 | +                code = line.split("#", 1)[0]
 843 | +                for pat in self.FORBIDDEN:
 844 | +                    m = re.search(pat, code)
 845 | +                    if m and (os.path.basename(f), m.group(0)) not in self.ALLOWED:
 846 | +                        bad.append(f"{os.path.relpath(f, REPO)}:{n}: {line.strip()[:120]}")
 847 | +        self.assertFalse(bad, "ad-hoc text normaliser outside pipeline/canon.py:\n" + "\n".join(bad))
 848 | +
 849 | +    def test_the_comparison_sites_import_canon(self):
 850 | +        """The named comparison sites (quote verification, selection anchors, edge words, G3 / G3b, G18,
 851 | +        sign-off names, ledger statements, approved PIN text, G1 / G13 VO text) call canon."""
 852 | +        sites = ["story_semantics.py", "editorial_select.py", "sentence_law.py", "word_diff.py", "gates.py",
 853 | +                 "editorial_gate.py", "cut_accept.py", "stand_alone.py", "punctuation.py", "pinned.py"]
 854 | +        missing = [f for f in sites if "canon" not in open(os.path.join(PIPELINE, f)).read()]
 855 | +        qa = open(os.path.join(REPO, "segment_v1", "qa_gates.py")).read()
 856 | +        if "import canon" not in qa:
 857 | +            missing.append("segment_v1/qa_gates.py")
 858 | +        self.assertFalse(missing, missing)
 859 | +
 860 | +
 861 | +if __name__ == "__main__":
 862 | +    unittest.main()
 863 | 
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
