**Q1: CORRECTNESS**  
The diff contains only test files (`tests/oracle/*`) and supporting docs. No `sentence_law.py`, `pipeline/run_fresh.py`, `edl.json` handling, cut logic, or `edge_fades`/`gate_g17_edges` code appears. All functions under test (e.g., `L.parse_oracle`, `L.check`, `X.export_run`, `AB.run_role`) match their docstrings and the inline laws (L-j, L-l, L-o, L-x, etc.) for the oracle/judge path. No off-by-one, unit, or silent-exception issues visible in the test code. No path in these tests can emit a PASS when a model reply is missing/malformed (they raise `OracleFailed`/`JudgeFailed`).

**Q2: LAW COMPLIANCE**  
- SENTENCE LAW / L-e / L-g / L-h: COMPLIANT (lines 324-331, 615-619, 318-321 enforce whole punctuated sentences, spoken-form reading, no markup).  
- SELECTION LOCK / SNAP LIMIT / NEIGHBOUR / ONSET/TAIL: NOT VERIFIABLE (no cut, EDL, or `sentence_law.*` code in diff).  
- L-a / L-b / CREDITS: NOT VERIFIABLE (no render/sign-off/avatar code).  
- L-j / L-l / M12: COMPLIANT (tests explicitly require whole replies and fail-closed on missing/malformed fields; lines 483-523, 535-558).  
- L-d / L-22: NOT VERIFIABLE (no v2f reference path exercised).  
No evidence of loosened thresholds or recomputed first/last words after selection.

**Q3: TESTS**  
Tests use must-fail fixtures (empty/malformed replies, unknown IDs, altcoin smuggling, partial schemas) that correctly raise the documented exceptions. Controls (legal_lineup, consistent verdicts) pass for the stated reasons. No vacuous assertions found; every check has explicit positive/negative cases. Byte-identity, hash-mismatch, and spend-guard tests are concrete.

**Q4: VERDICT**  
No defects in the supplied diff.  
The diff adds only oracle-selection tests; it does not contain or exercise the sentence-boundary/cut/edge-word/credit logic named in the feature.  
**NOT READY** (wrong diff for the stated feature).