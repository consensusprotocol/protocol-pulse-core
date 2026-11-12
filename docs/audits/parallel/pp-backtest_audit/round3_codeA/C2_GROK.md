**CYCLE 2 REVIEW — pulse-sentence-law**

### 1. What Grok/Claude caught that I missed in Cycle 1
- **Test coverage gap** (Claude U-1): Explicitly flagged that no test files were in the diff. I accepted Grok’s “READY” without sufficient weight on the absence of must-fail fixtures for `parse_oracle`/`parse_judge`, `Ledger` cap enforcement, `ContextTooLong`, SHA re-verification, and the write-guard.
- **Single-reviewer confidence discount**: Claude correctly noted that only one model completed Cycle 1, materially lowering trust in the “no defects” claim.

### 2. Agreement / Disagreement
- **Agree** with Grok on core correctness and law compliance (L-j/L-l/L-m/L-x, spend guard, fail-closed parsing, vendor separation, `sentence_law.is_terminal` delegation). The strict schema enforcement, `OracleFailed`/`JudgeFailed`, exclusive locks + pid checks, and `ContextTooLong` pre-send rejection are implemented as described.
- **Partially agree** on replay guard: the `no_writes_under` monkey-patching is present and aggressive, but its completeness (pathlib, all os builtins, edge cases with symlinks/tmp files) is not trivial to verify without tests.
- **Disagree** with Grok’s final “No defects found.” The missing test package and the complexity of the AB harness + witness state machine introduce unverified paths that could still allow a silent PASS on malformed data or stale artefacts.

### 3. New findings from combined analysis
- The `ab.py` swap construction and `_agree` logic for must-fail items is intricate; a single off-by-one in overlap calculation or `WITHDRAWN` filtering could silently drop required negative cases.
- `replay.py:1824-1893` write guard is the single most security-critical piece of new code; any gap (e.g., `tempfile`, `shutil`, or third-party libs that open files) would violate the “never write under main tree” rule.
- Stale-file protection (`run.py:fresh` + `oracle_sha256`) is good but depends on every downstream consumer (score, report, witness) calling it correctly; one missed call creates a silent data-integrity hole.

### 4. Revised Scores

| Subsystem                              | Cycle 1 | Cycle 2 | Why changed |
|----------------------------------------|---------|---------|-------------|
| Correctness — parse_oracle / parse_judge | PASS    | PASS    | Still solid |
| Correctness — Ledger / spend guard     | PASS    | PASS    | Still solid |
| Correctness — call_backend / ContextTooLong | PASS | PASS | Still solid |
| Correctness — export / SHA / sentence_law | PASS | PASS | Still solid |
| Correctness — replay write guard       | PASS    | PASS    | Implementation present |
| Law Compliance (L-j/l/m/x/h/k)         | PASS    | PASS    | Still solid |
| Tests — must-fail fixtures             | NOT VERIFIED | FAIL | Confirmed absent from diff |
| Overall Verdict                        | READY   | READY WITH CONDITIONS | Test gap + single-reviewer risk |

### 5. Final Priority List
**P0 CRITICAL (must fix before any production use)**
- Verify or create must-fail test suite covering: schema violations → `OracleFailed`/`JudgeFailed`, `SpendStop` before any remote call, `ContextTooLong` rejection, SHA mismatch → `ExportError`, write attempts under `MAIN_TREE` → `PermissionError`.

**P1 HIGH**
- Audit `replay.py:no_writes_under` against `tempfile`, `shutil`, `pathlib.Path` edge cases, and any library that may open files for writing.
- Add explicit `fresh()` check in every consumer of `GROUPS.json`, `WITNESS.json`, `SCORE.json`.

**P2 MEDIUM**
- Add a lightweight property test that the three independent exports are byte-identical on the same input.

### 6. The single highest-leverage change
Add the missing test package (especially the must-fail fixtures for the strict parsers and the write guard) and run it under the same CI that will gate merges. Everything else is defensive code that already fails closed; untested defensive code is the only remaining systemic risk.

### 7. Production Ready?
**Yes with conditions.**

Conditions:
- The test package (Package B) must be reviewed and pass before any run that touches real spend or the live transcript store.
- The `no_writes_under` guard must be stress-tested against common file-system operations.
- All derived artefacts must be proven to carry a matching `oracle_sha256` or be rejected.

Once those three items are closed, the implementation meets the stated laws and the fail-closed contract.