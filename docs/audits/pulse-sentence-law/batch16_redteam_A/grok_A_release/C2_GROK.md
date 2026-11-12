**CYCLE 2 REVIEW — pulse-sentence-law**

**1. WHAT DID THEY CATCH THAT YOU MISSED?**  
The stale comment at `run_fresh.py:104` ("G11_parity(run_gates) ... see G11 below") was a clear documentation debt that I overlooked. GPT-4o and Gemini also reinforced the robustness of the `release_auth.blockers` + `attest` + `authorise` chain more explicitly than my Cycle 1 note.

**2. WHERE DO YOU AGREE OR DISAGREE?**  
- **M1 (G17_onset_tail evidence ordering, run_fresh.py:212)**: Agree. The race between `put()` and the later `evidence[...]["samples"] = ...` line is real; an exception leaves a PASS row with zero evidence.  
- **M2 (stale comment)**: Agree. Cosmetic but worth fixing for future readers.  
- **U1 (replay exception path)**: Partially agree. It is low-risk in practice (replay is diagnostic), but still a latent inconsistency.  
- Overall correctness and law compliance: Full agreement with the other models. The fail-closed design is correctly implemented.

**3. NEW FINDINGS FROM THIS REVIEW**  
None that rise above LOW. The combined view confirms the architecture is sound; the only remaining issues are the two already-flagged LOW items plus the stale comment.

**4. REVISED SCORES**

| Subsystem              | Cycle 1 | Cycle 2 | Why changed                  |
|------------------------|---------|---------|------------------------------|
| Correctness            | 9/10    | 9/10    | No change                    |
| Law Compliance         | 9/10    | 9/10    | No change                    |
| Test Quality           | 10/10   | 10/10   | No change                    |
| Security / Fail-Closed | 9/10    | 9/10    | No change                    |
| Overall Readiness      | READY   | READY   | Confirmed after cross-review |

**5. FINAL PRIORITY LIST**

- **P1 HIGH** — `run_fresh.py:212`: Move G17 evidence population inside/adjacent to the `put()` call so verdict and samples are written atomically.  
- **P2 MEDIUM** — `run_fresh.py:104`: Remove or update the stale G11 comment.  
- **P2 MEDIUM** — `replay.py:21-23`: Add a defensive `write_report` (or equivalent) in the attestation exception path for consistency.

**6. THE SINGLE HIGHEST-LEVERAGE CHANGE**  
Make the G17_onset_tail evidence write atomic with its verdict so a passing gate row can never exist without the required `samples >= 1` evidence.

**7. PRODUCTION READY?**  
**Yes with conditions.** Ship after the P1 item (evidence ordering) is fixed. The rest of the change is already robust, fail-closed, and law-compliant.