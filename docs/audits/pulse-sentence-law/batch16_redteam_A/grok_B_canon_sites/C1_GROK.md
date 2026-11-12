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