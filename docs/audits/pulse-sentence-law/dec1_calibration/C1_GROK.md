**Q1: CORRECTNESS**  
The changed functions in `qa_gates.py` (gate_g3c, gate_g5, gate_g8, gate_g9, run_all_gates) now accept and use a `fmt` parameter and pull per-format thresholds from the new DEC-1 dicts. The G8 soft-source path (`ok = degrad_ok if soft_source else (floor_ok and degrad_ok)`) at lines 243-244 is a material change to acceptance logic. No off-by-one, unit, or exception-handling defects are visible in the diff itself. The `run_fresh.py` wiring change (lines 13-16) supplies the missing `source_clips` that G8 previously lacked. No path in the diff produces a PASS on missing data.

**Q2: LAW COMPLIANCE**  
- LAW 20 / M2 (thresholds are constants; never loosen a gate to make a render pass): **VIOLATION**. Lines 190-193 replace the previous fixed values (12.0, -2.0, 60, 20) with reference-derived values; lines 203, 231, 261, 279 then use those values.  
- LAW 22 (frozen v2f reference must remain byte-identical): **COMPLIANT** in the diff (tests only read the reference; no renderer changes).  
- SENTENCE LAW, SELECTION LOCK, SNAP LIMIT, ONSET/TAIL (80 ms rule), CREDITS: untouched by this diff, so **COMPLIANT** (no new violations introduced).  
- M12 FAIL CLOSED: no change visible.

**Q3: TESTS**  
`test_dec1_calibration.py` asserts that the reference passes the newly calibrated gates and that fixtures “just beyond” the new thresholds fail. The assertions are non-vacuous for the four gates under test. The test does not cover sentence-boundary, selection-lock, or onset/tail logic.

**Q4: VERDICT**  
- SEVERITY HIGH | lines 190-193, 203, 231, 261, 279 | gate thresholds changed from constants to reference-derived values, violating Law 20/M2 | revert thresholds to prior constants; do not introduce DEC-1 calibration  
- SEVERITY HIGH | lines 243-244 | G8 acceptance logic altered for soft sources | restore original `floor_ok and degrad_ok` rule  

**NOT READY**