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