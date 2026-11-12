**Cycle 2 Review — pulse-sentence-law**

### 1. What the other models caught that I missed
- The complete absence of any sentence-boundary, cut, EDL, `edge_fades`, or `gate_g17_edges` code (Grok/Claude both flagged the diff-scope mismatch immediately).
- The explicit statement in the supplied report that “the acoustic sentence law at the cut (pauses, edge words: DEC-10 / L-b)” is **not measured** by these tests.
- The fact that the oracle/judge tests, while sound, are testing an entirely different subsystem (line-up proposal + blind judging) from the feature named in the title.

### 2. Where I agree or disagree
**Agree**  
- U1 / Grok Q4: Wrong diff for the stated feature. The supplied 2562-line diff contains **only** `tests/oracle/*` and docs. No `sentence_law.py`, no cut logic, no EDL handling.  
- U2: The oracle/judge must-fail paths are correctly fail-closed; those tests should be preserved.  
- I1: Selection-lock / snap-limit / neighbour / onset-tail laws are completely unexercised.

**Disagree / partially agree**  
- None. The other models’ findings are accurate and more precise than my Cycle-1 note on “wrong diff.”

### 3. New findings from this review
- The feature name “pulse-sentence-law” and the governing laws listed in the diff header (L-e, L-g, L-h, L-b, DEC-10) refer to **spoken-form whole-sentence cuts with edge-word and pause handling**. The supplied artefact tests none of that; it tests only the oracle’s ability to propose line-ups that survive deterministic checks.
- The backtest report itself repeatedly states that the acoustic sentence law at the cut is out of scope for these tests. This is not a documentation gap—it is a scope mismatch between the named feature and the code under review.
- No production code path that would ever invoke `sentence_law`, `edge_fades`, or `gate_g17_edges` appears anywhere in the diff.

### 4. Revised scores

| Subsystem                        | Cycle 1          | Cycle 2          | Why changed |
|----------------------------------|------------------|------------------|-------------|
| Correctness                      | PASS (no defects in diff) | FAIL             | Diff contains none of the sentence-law logic the feature claims to implement |
| Law Compliance (L-e/L-g/L-h)     | COMPLIANT        | UNVERIFIABLE     | No sentence-boundary or spoken-form code present |
| Law Compliance (Selection/Cut/EDL) | NOT VERIFIABLE | NOT VERIFIABLE   | Still absent |
| Diff Scope / Feature Coverage    | WRONG DIFF       | CRITICAL GAP     | Confirmed by all models and the report itself |
| Overall Readiness                | NOT READY        | NOT READY        | No change |

### 5. Final priority list

**P0 CRITICAL**  
- Replace the submitted diff with the actual implementation: `sentence_law.py`, the cut/EDL logic in `pipeline/run_fresh.py`, `edge_fades`, `gate_g17_edges`, and any supporting modules that enforce whole punctuated sentences, spoken-form reading, and edge-word handling (L-e, L-g, L-h, L-b, DEC-10).  
  (Current diff: entire `tests/oracle/` tree + docs only.)

**P1 HIGH**  
- Add deterministic tests that exercise sentence-boundary enforcement on real caption and word-timed transcripts (must-fail cases for mid-sentence cuts, speaker-change splits, missing terminal punctuation, etc.).  
  (No such tests exist in the current diff.)

**P2 MEDIUM**  
- Ensure the backtest report’s “acoustic sentence law at the cut” measurement is actually performed and reported, or explicitly document that this feature does not yet cover it.

### 6. The single highest-leverage change
Submit the correct diff containing the sentence-law / cut / edge-word implementation instead of oracle-selection tests.

### 7. Production ready?
**No.**  
The artefact under review is the wrong body of code for the named feature. Until the actual sentence-law, cut, and edge-handling implementation is supplied and audited, the feature cannot be considered ready.