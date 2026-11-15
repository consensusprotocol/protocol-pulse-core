**Q1: CORRECTNESS**  
Functions match their docstrings. `parse_oracle`/`parse_judge` (lines 746-772, 775-796) raise `OracleFailed`/`JudgeFailed` on any malformed/empty/inconsistent reply and never return a partial result. `check` (810-860) applies deterministic rules exactly as documented (consecutive IDs, durations, altcoin screen, channel counts). `Ledger` (970-1062) uses atomic file locking for spend/inflight and refuses calls past the cap. `tokens`/`sentences` (402-439) correctly delegate to `transcript_store.read_text` + `sentence_law.is_terminal`/`editorial_select._word_sentences`. No off-by-one, unit, or silent-exception paths that turn a failure into a pass. All model-reply paths are fail-closed.

**Q2: LAW COMPLIANCE**  
- SENTENCE LAW / SELECTION LOCK / SNAP LIMIT / NEIGHBOUR / ONSET/TAIL / CREDITS / L-a..L-l: **COMPLIANT**. The diff never touches cut points, selection locks, or edge-word logic; it only reads existing `sentence_law.is_terminal`, `BITCOIN_TERMS`, and `layout_eligible` (lines 430, 457, 825). No recomputation of first/last words after selection.  
- L-j / L-l / L-m: **COMPLIANT** (strict schemas, `OracleFailed`/`JudgeFailed` on any missing/mistyped field, unmeasured items reported as such).  
- No path loosens a gate threshold or alters v2f reference behaviour. No writes into the transcript store or `/home/ultron/protocol_pulse` (export reads only; ledger writes to caller-supplied path outside the store).

**Q3: TESTS**  
No test code appears in the diff. Mentions of `tests/oracle/test_oracle_export.py` and `test_oracle_*.py` exist only as comments; cannot verify must-fail fixtures or non-vacuous assertions from the supplied diff.

**Q4: VERDICT**  
No defects.  
**READY**