**Cycle 2 Audit — pulse-sentence-law**

### 1. WHAT DID THEY CATCH THAT YOU MISSED?
- The explicit dependency on the unaudited `pipeline/canon.py` module (L-g / L-h / L-k compliance is now contingent). My Cycle 1 review treated the delegation as sufficient; the other models correctly flagged that the diff removes the old normalisation logic but does not show the replacement.
- The missing v2f / LAW 22 regression artefact. I did not call out the absence of the regression output that proves the reference hash is unchanged.

### 2. WHERE DO YOU AGREE OR DISAGREE?
**Agree**  
- MF-1 (`canon.py`): full agreement. Compliance on written/spoken forms and canonical tokenisation cannot be asserted from this diff alone.  
- MF-2 (LAW 22): full agreement. The regression proof must be attached.  
- All three models’ positive findings on the new `span_matches`, `_gain_db`, `edges_on_final`, `edge_word_fidelity` (every-frame rule, gain-invariant path), and the tightened anchor check (lines 46-47) are correct.  
- The test updates (`test_verdict_rules`, `TestSpanMatches`, repeat-only handling) are strong.

**Disagree / partially agree**  
- None on the technical defects; the only divergence was my earlier optimism about the unseen `canon.py`.

### 3. NEW FINDINGS FROM THIS REVIEW
No new defects in the changed code itself. The combined view simply makes the two systemic gaps (canon.py + regression artefact) unavoidable.

### 4. REVISED SCORES

| Subsystem              | Cycle 1 | Cycle 2 | Why changed |
|------------------------|---------|---------|-------------|
| Correctness            | 9       | 9       | No change |
| Law Compliance         | 8       | 7       | Downgraded for contingent L-g/L-h/L-k and missing LAW 22 proof |
| Test Coverage          | 9       | 9       | No change |
| Security / Fail-Closed | 9       | 9       | No change |
| Overall Readiness      | 9       | 8       | Blocked on two external items |

### 5. FINAL PRIORITY LIST
**P0 CRITICAL** (must be resolved before merge)  
- `pipeline/canon.py` — entire module must be audited or a targeted test suite exercising every branch referenced by L-g, L-h, L-k must be added and passed.  
- Attach v2f regression output (or CI badge) proving the reference hash is unchanged (LAW 22).

**P1 HIGH**  
- None in the diff itself.

**P2 MEDIUM**  
- None.

### 6. THE SINGLE HIGHEST-LEVERAGE CHANGE
Surface and audit `pipeline/canon.py` (or its test coverage) so that the canonical-form guarantees the rest of the change depends on are actually verified.

### 7. PRODUCTION READY?
**Yes with conditions.**  
Conditions: (1) `pipeline/canon.py` is audited or its relevant behaviour is covered by an isolated test that passes, and (2) the v2f/LAW 22 regression artefact is committed alongside the PR. Once those two items are closed, the feature is ready.