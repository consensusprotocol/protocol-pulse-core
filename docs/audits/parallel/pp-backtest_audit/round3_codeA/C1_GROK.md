**Q1: CORRECTNESS**  
All new functions match their docstrings and the listed laws (L-j, L-l, L-m, L-x, spend guard).  
- `parse_oracle` / `parse_judge` (lineup.py:777-827) raise `OracleFailed`/`JudgeFailed` on any missing/mistyped field or inconsistent verdict; never return a partial answer.  
- `Ledger.reserve`/`settle` (llm.py:1064-1095) use an exclusive lock + pid check; a call past the cap raises `SpendStop` before any remote request.  
- `call_backend` (providers.py:1615-1664) rejects `ContextTooLong` before send, treats any vendor-side error as retryable, and never prints keys.  
- `export_run` / `tokens` / `sentences` (export.py:505-467) re-verify transcript SHA, use `read_text` + `canon`, and delegate sentence boundaries exclusively to `sentence_law.is_terminal`. No recomputation of first/last words after selection.  
- `replay` (replay.py:1909-1962) never writes under the main tree (guard at 1824-1893) and stops on the first `NotRerun`.  
No off-by-one, unit, or silent-exception paths that could turn a missing input into a PASS.

**Q2: LAW COMPLIANCE**  
- L-j / L-l / L-m: COMPLIANT (lineup.py:740-746, 806-827; providers.py:1680-1693; ab.py:258-262).  
- L-x: COMPLIANT (providers.py:1439-1444, 1521-1546, 1670-1693). Only `providers.py` names vendors; local GPU0 only under lease; judge chain never includes writer vendor.  
- L-h / L-k: COMPLIANT (export.py:394, 456, 484; canon imported flat).  
- Sentence law / SELECTION LOCK / SNAP LIMIT: COMPLIANT by construction; the backtest never edits cuts or re-derives boundaries (export.py:375, lineup.py:841-894).  
- No gate threshold is loosened; every failure is hard (no reclassification). v2f reference path is untouched.

**Q3: TESTS**  
No test files appear in this diff (explicitly stated as Package A). Cannot verify must-fail fixtures or vacuous assertions.

**Q4: VERDICT**  
No defects found that would allow a PASS on missing data, model failure, or law violation.  

READY