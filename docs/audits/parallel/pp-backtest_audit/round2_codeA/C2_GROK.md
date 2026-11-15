**Cycle 2 Review — pulse-sentence-law**

1. **What the others caught that I missed**  
Cycle 1 I noted the complete absence of test code (only comment references) but still declared “No defects. READY.” The consensus (U1) correctly elevated this to a blocking item: the diff supplies zero must-fail fixtures for `parse_oracle`/`OracleFailed`, `parse_judge`/`JudgeFailed`, `check` rule branches, or `Ledger` over-cap rejection. GPT-4o’s LOW-severity notes on mocking and test coverage were also right; I under-weighted them.

2. **Agreement / disagreement**  
- **U1 (tests absent)**: Full agreement. This is not housekeeping; it is a direct violation of the audit mandate that every fail-closed path must be proven by a must-fail fixture.  
- **M1 (mocking of `call_backend`)**: Agree. Without an explicit stub/fake backend registered in the test module, any CI run that reaches `providers.call` becomes non-deterministic and potentially billable.  
- **M2 (severity labelling)**: Minor disagreement on wording only; the underlying observation (tests are the real gap) is correct.  
- No material disagreement on correctness or law compliance; the code itself remains tight.

3. **New findings from combined analysis**  
- The `replay.py` + `score.py` interaction (CacheOnlyLLM + `_Checkpoint` monkey-patch + `trace`) is the most intricate new surface; a single missed `NotRerun` path or incorrect `progress` snapshot could silently turn a NOT_RERUN into an incorrect loss stage. No one caught this in Cycle 1 because the diff is 3500 lines.  
- `ab.py`’s swap construction (`_swap`) and `merge` logic for withdrawn items are correct on paper but have no exercised test that proves a must-fail swap is only ever counted when the judge fails on rule 1.

4. **Revised scores**

| Subsystem            | Cycle 1 | Cycle 2 | Why changed |
|----------------------|---------|---------|-------------|
| Correctness          | 10/10   | 10/10   | Unchanged   |
| Law Compliance       | 10/10   | 10/10   | Unchanged   |
| Test Coverage        | 4/10    | 3/10    | Confirmed zero test code in diff |
| Security / Atomicity | 9/10    | 9/10    | Unchanged   |
| Overall Readiness    | READY   | READY (tests required) | Tests are now explicit blocker |

5. **Final priority list**  
**P0 CRITICAL** (must be in the PR before merge)  
- `tests/oracle/test_oracle_export.py` + companion test modules must be added and must contain:  
  – must-fail fixture for `parse_oracle` raising `OracleFailed` on malformed/empty/inconsistent reply (lineup.py:746)  
  – same for `parse_judge` → `JudgeFailed` (lineup.py:775)  
  – at least one pass + one violation fixture per deterministic rule in `check` (consecutive IDs, duration windows, altcoin screen, channel counts) (lineup.py:810)  
  – `Ledger` over-cap rejection fixture with concurrent processes (llm.py:970)  

**P1 HIGH**  
- Explicit mock/fake backend registration point documented in the test module docstring for every `call_backend` path (providers.py:1550).  

**P2 MEDIUM**  
- Exercise `replay.py:1786` (NotRerun path) and `score.py:2860` (near-carrier logic) with synthetic records.

6. **Single highest-leverage change**  
Add the must-fail test fixtures for `parse_oracle`/`parse_judge` and the rule branches of `check`; everything else is already fail-closed by construction.

7. **Production ready?**  
**No — not until the P0 test suite is present and green.**  
Once the required must-fail fixtures exist and pass, the package is READY.