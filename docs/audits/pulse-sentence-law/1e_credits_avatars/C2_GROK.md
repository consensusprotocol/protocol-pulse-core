**CYCLE 2 REVIEW — pulse-sentence-law (avatar/D4 scope only)**

### 1. What the others caught that I missed
- Explicit requirement for `test_pulse_20261110_mustfail.py` (Gemini + consensus). I noted the absence of tests but did not treat the missing file as a blocking defect because the diff header referenced it.
- Full feature scope vs. delivered scope mismatch (Gemini). The feature is named `pulse-sentence-law` and claims D1–D6 coverage; the diff contains only the D4 avatar fix. I evaluated the avatar sub-scope in isolation.
- LAW 22 risk from output change (Gemini). A correct avatar fix necessarily alters the credits render, which may violate the frozen-reference requirement.

### 2. Agreement / disagreement
- **Missing test file** — Agree (U1). This is a critical gap; the must-fail fixtures are the only machine-verifiable proof that the new gates actually catch the original D4 failures.
- **Brittle regex JSON editing in `cmd_register`** — Agree (U2). The approach is fragile and should be replaced with proper `json.load`/`json.dump`.
- **Sentence-law code absent** — Agree. The diff contains zero sentence-boundary, onset, or transcript logic.
- **LAW 22 uncertainty** — Partially agree. The avatar change will alter rendered output; whether that is permitted under the bug-fix exception to LAW 22 is not documented in the diff.
- **Avatar pipeline correctness & CREDITS/M12 compliance** — Agree. The new `_find_avatar` + `validate_avatar` + onboarding flow is a textbook fail-closed implementation.

### 3. New findings from combined review
- Duplicate SHA-256 prefixes already exist in the updated `channels.json` (e.g., `guy_swann` and `bitcoin_audible` both carry `09e2ad1369cea88c`). The deduplication logic in `cmd_fetch` only checks the current run; it does not prevent or warn about pre-existing collisions.
- Saylor channel is disabled with no comment or ticket reference (line 575 of channels.json). This is intentional per the other models but undocumented.
- The `avatar_onboard.py` duplicate-SHA check (lines 105–111) runs after the fetch loop and can silently mark a row as failed without updating the report file that was already written.

### 4. Revised scores

| Subsystem                    | Cycle 1 | Cycle 2 | Why changed |
|-----------------------------|---------|---------|-------------|
| Correctness — Avatar Pipeline | 8/10    | 8/10    | No change |
| Correctness — Sentence Law   | N/A     | N/A     | Confirmed absent |
| Law: CREDITS                 | Compliant | Compliant | — |
| Law: M12 FAIL CLOSED         | Compliant | Compliant | — |
| Law: SENTENCE LAW            | Not addressed | Not addressed | — |
| Law: LAW 22                  | Not addressed | Uncertain | Output change risk now visible |
| Tests                        | Missing | Missing | Elevated to blocking |
| Overall Verdict              | READY   | NOT READY | Scope + test gaps now decisive |

### 5. Final priority list
**P0 CRITICAL**
- Create `pipeline/test_pulse_20261110_mustfail.py` with the four required must-fail cases listed in the consensus (U1).
- Replace regex-based in-place edit in `cmd_register` (avatar_onboard.py:126–134) with proper JSON load/modify/dump.

**P1 HIGH**
- Document the Saylor `enabled:false` change (channels.json:575) or revert it.
- Add a post-write duplicate-SHA warning in `cmd_fetch` and ensure the ONBOARD_REPORT reflects any late failures.
- Clarify LAW 22 handling for bug-fix output changes (either a waiver or a new reference render).

**P2 MEDIUM**
- Add a comment explaining why duplicate SHA prefixes are tolerated or prevented going forward.

### 6. Single highest-leverage change
Create the must-fail test suite (`test_pulse_20261110_mustfail.py`) — it is the only artifact that turns the claim “the new gates catch D4” into verifiable fact.

### 7. Production ready?
**No.**  
Conditions for Yes: (1) the must-fail test file exists and passes, (2) `cmd_register` uses safe JSON editing, (3) the scope mismatch between feature name and delivered code is either resolved or explicitly accepted by the maintainers.