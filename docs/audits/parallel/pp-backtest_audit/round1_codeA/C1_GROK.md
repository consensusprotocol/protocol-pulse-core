**Q1: CORRECTNESS**  
The functions in the diff match their docstrings. `export.py` (lines 235-429) correctly reads records by sha, applies `transcript_store.read_text` + `canon.canon`, splits via `sentence_law.is_terminal` / `editorial_select._word_sentences`, and produces deterministic sorted output. `lineup.py` (lines 453-782) implements strict `parse_oracle`/`parse_judge` that raise `OracleFailed`/`JudgeFailed` on any malformed/empty/inconsistent reply (never treating them as NONE or LEGAL). `providers.py` (lines 1140-1396) and `llm.py` (lines 783-874) enforce the single-vendor-name rule, GPU0 lease gate, spend cap, and `ContextTooLong` rejection. No off-by-one, unit, or silent-exception paths visible in the shown code; every failure path is explicit and fail-closed.

**Q2: LAW COMPLIANCE**  
- SENTENCE LAW / SELECTION LOCK / SNAP LIMIT / NEIGHBOUR / ONSET/TAIL / L-b / L-c / L-e / L-k: COMPLIANT (no modification to `sentence_law.py`, `punctuation.py`, `editorial_select`, or cut logic; all use the imported modules unchanged).  
- L-l (whole model replies): COMPLIANT (strict schema + `JudgeFailed`/`OracleFailed` on any missing/wrong-type field).  
- L-x (providers only): COMPLIANT (lines 1176-1194, 1195-1200).  
- No path allows a cut to move outside a locked sentence, recomputes first/last words after selection, loosens a gate threshold, or treats a model failure as a pass. v2f reference path is untouched.

**Q3: TESTS**  
No test files appear in the diff. The claim that must-fail fixtures produce the right failure mode and controls pass for the right reason cannot be verified from the supplied diff.

**Q4: VERDICT**  
No defects found in the reviewed diff.  
READY