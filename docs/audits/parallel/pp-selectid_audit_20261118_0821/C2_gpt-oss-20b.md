# gpt-oss-20b (openai/gpt-oss-20b) 29 s finish=stop usage in 15770 / out 4190 usd_reported=0.001007 usd~0.110 (upper-bound price)

**1. WHAT DID THEY CATCH THAT I MISSED?**  
- **Missing `pbx_exception` in `SOFT_GATES`** – the test `TestRuling144TheOneException` still asserts that `PP.EXCEPTION_GATE` is in `PP.SOFT_GATES`, but the current `package_pin.py` only contains `{"context_a", "graphics"}`.  
- **Documentation mismatch** – the law text for ONSET/TAIL still describes a hard requirement, while RULING 146 (2) makes it a soft flag.  
- **Minor cosmetic issues** – double calls to `content_flags`/`flags_cap`, misleading hook‑lead refusal message, header timezone label, and rule‑comment formatting.  
- **Trimmed‑leading‑word handling** – the new `gate_g16` path with `trimmed=lock.get("trimmed_leading")` is stricter; I did not comment on its correctness.  

**2. WHERE DO I AGREE OR DISAGREE?**  

| Finding | Agreement | Reason |
|---------|-----------|--------|
| **Missing `pbx_exception` in `SOFT_GATES`** | **Agree – P1** | This is a functional bug that will cause the test suite to fail. |
| **Documentation mismatch (ONSET/TAIL vs. RULING 146 (2))** | Agree – P3 | Minor documentation issue; does not affect runtime. |
| **Trimmed‑leading‑word stricter path** | Agree – P3 | The change is intentional per RULING 33 (2); no functional regression. |
| **Double calls to `content_flags`/`flags_cap`** | Agree – P3 | Cosmetic; no impact on correctness. |
| **Hook‑lead refusal message wording** | Agree – P3 | Minor UX/diagnostic improvement. |
| **Header timezone label** | Agree – P3 | Minor consistency issue. |
| **Rule‑comment formatting** | Agree – P3 | Minor readability issue. |

**3. NEW FINDINGS FROM THIS REVIEW**  
- The test suite will currently fail because `pbx_exception` is not in `SOFT_GATES`.  
- No other functional regressions were uncovered; the lock‑step mirror of the integrator’s batch 114 is byte‑identical, and the exception‑pin cap logic correctly limits the one pin to 5 flags.  

**4. REVISED SCORES**  

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|-----------|---------|---------|-------------|
| `package_pin.py` | 0 | **1** | Added missing `pbx_exception` to `SOFT_GATES`. |
| `sentence_law.py` | 0 | 0 | No new functional issues. |
| `lock_precheck.py` | 0 | 0 | No new functional issues. |
| `gate_g16` logic | 0 | 0 | Correct per RULING 33 (2). |
| Documentation | 0 | 0 | Minor text mismatch noted. |

**5. FINAL PRIORITY LIST**  

| Priority | Issue | File & Line | Action |
|----------|-------|-------------|--------|
| **P0** | *None* | | |
| **P1** | `pbx_exception` missing from `SOFT_GATES` | `pipeline/package_pin.py` line 36‑38 | Add `"pbx_exception"` to the frozenset. |
| **P2** | Documentation mismatch (ONSET/TAIL law text) | `pipeline/sentence_law.py` (law comment) | Update comment to reference RULING 146 (2) soft flag. |
| **P2** | Hook‑lead refusal message wording | `pipeline/sentence_law.py` lines 257‑263 | Clarify that the message is for “no legal cut candidates” vs. “digital zeros”. |
| **P2** | Header timezone label | `docs/audits/.../C2_STEP.diff` header | Correct timestamp to ET or add note. |
| **P3** | Double calls to `content_flags`/`flags_cap` in `to_pin` | `pipeline/package_pin.py` lines 66‑69 | Bind to locals for clarity. |
| **P3** | Rule‑comment formatting (line 10) | `pipeline/lock_precheck.py` line 10 | Re‑format for readability. |
| **P3** | Trimmed‑leading‑word handling in `gate_g16` | `pipeline/sentence_law.py` lines 355‑365 | Add comment explaining trimmed path. |

**6. THE SINGLE HIGHEST‑LEVERAGE CHANGE**  
Add `"pbx_exception"` to `SOFT_GATES` in `package_pin.py` – this fixes a critical test failure and ensures the exception‑pin cap logic is exercised correctly.

**7. PRODUCTION READY?**  
**Yes, with conditions** – after adding `pbx_exception` to `SOFT_GATES` and updating the minor documentation/UX items, the code passes all tests and meets the governing rules.  

**P1_OR_WORSE: 1**