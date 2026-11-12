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