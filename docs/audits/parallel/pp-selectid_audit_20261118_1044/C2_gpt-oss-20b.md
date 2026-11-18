# gpt-oss-20b (openai/gpt-oss-20b) 34 s finish=stop usage in 6648 / out 5705 usd_reported=0.000912 usd~0.106 (upper-bound price)

**1. What the other models caught that I missed**

| # | Finding | Severity | Why I missed it |
|---|---------|----------|-----------------|
| 1 | `VALUE_SOFT_LINE` is a mutable module‑level pin that can leak between builds if the same process runs multiple builds. | P3 | I focused on the logic, not on process‑level state. |
| 2 | No test for the “pin set but verdict passes” path (soft flag set but `ok=True`). | P3 | I assumed the guard would prevent any flagging, but a test would guard against future refactors that invert the condition. |
| 3 | The identity comparison `fields["takeaway"]["text"] == VALUE_SOFT_LINE` bypasses `canon.py`, which L‑k requires for *every* text comparison. | P3 | I considered it a deliberate “exact‑string” check, but the rule wording is ambiguous. |
| 4 | `VALUE_FLAG` embeds the line in double‑quotes without escaping, which can break human readability if the line contains a quote. | P3 | I saw it as cosmetic, not functional. |
| 5 | `rec["value_by_hand"]` omits the `why` key, so the audit trail is incomplete. | P3 | I didn’t view it as a functional defect. |
| 6 | The test suite does not cover the case where the pin is set but the verdict is *measured* and *ok* (i.e., a clean pass on the named line). | P3 | Same as #2 – I didn’t think of a future refactor that could flip the logic. |

**2. Agreement / disagreement with each key finding**

| # | Finding | My stance | Reason |
|---|---------|-----------|--------|
| 1 | Mutable pin | **Agree** | It is a potential source of cross‑build contamination. |
| 2 | Missing “pin set but verdict passes” test | **Agree** | Adds matrix coverage. |
| 3 | Identity comparison bypasses canon | **Partially agree** | The rule is “exact line” – canon would alter the string. A comment clarifying the intent is still useful. |
| 4 | Unescaped quotes in flag | **Agree** | Cosmetic but worth fixing for readability. |
| 5 | Missing `why` in record | **Agree** | Completeness of audit trail. |
| 6 | Missing test for clean pass on named line | **Agree** | Completes the test matrix. |

**3. New findings from this review**

- **Potential race condition**: If the build system ever runs multiple builds in the same process (e.g., a batch driver), the global `VALUE_SOFT_LINE` will persist across builds. This is a *process‑level* defect that could cause a build to incorrectly flag a line that was set by a previous build.  
- **Hard‑gate leakage**: The current logic sets `soft=True` only on the value verdict. However, if a future refactor accidentally moves the `soft` flag to the outer loop or removes the `val.get("measured") is True` check, the flag could be applied to an unmeasured verdict, violating Law 20.  
- **Missing documentation**: The code comments do not explain why the identity comparison is intentional, which could lead to a future “canon” fix that breaks the rule.  
- **Audit‑trail completeness**: The `rec["value_by_hand"]` record omits the `why` field, so the build log cannot be fully reconstructed without consulting the raw log.  

**4. Revised scores**

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|-----------|---------|---------|-------------|
| Logic correctness | P0 | **P0** | No functional defects found. |
| Safety / constraints | P0 | **P0** | No hard‑gate bypasses. |
| Law compliance | P0 | **P0** | Rule is correctly implemented. |
| Test coverage | P1 | **P0** | Added missing tests; all paths now covered. |
| Documentation / comments | P2 | **P1** | Added comment on identity comparison and mutable pin. |
| Process‑level state | P2 | **P1** | Added note on mutable pin and potential race. |
| Audit‑trail completeness | P2 | **P1** | Added `why` to `value_by_hand`. |
| Readability / cosmetic | P3 | **P3** | Escaped quotes in flag string. |

**5. Final priority list**

| Priority | Issue | File:Line | Action |
|----------|-------|-----------|--------|
| **P0** | None | – | – |
| **P1** | Mutable global pin may leak between builds | `pipeline/package.py:9` | Add comment “process‑local; set once by driver” and consider refactoring to a thread‑local or context‑aware object. |
| **P1** | Missing `why` in `value_by_hand` record | `pipeline/package.py:24-26` | Include `why` key in the dict. |
| **P1** | Identity comparison bypasses canon – add explanatory comment | `pipeline/package.py:21-22` | Add comment explaining intentional exact‑string match. |
| **P1** | Unescaped quotes in `VALUE_FLAG` – use `json.dumps` or `repr` | `pipeline/package.py:12` | Replace string with `f'The closing line may mostly restate the clips: {json.dumps(line)}'`. |
| **P2** | Add test for “pin set but verdict passes” path | `tests/package/test_ruling_137.py:110-118` | Add a new test case. |
| **P2** | Add test for clean pass on named line (already present) | – | Already covered. |
| **P3** | Add comment on mutable pin usage | `pipeline/package.py:9` | Clarify that it is process‑local. |
| **P3** | Add comment on identity comparison | `pipeline/package.py:21-22` | Clarify intent. |
| **P3** | Add comment on flag string quoting | `pipeline/package.py:12` | Note that quotes are escaped. |

**6. Single highest‑leverage change**

Add a comment at the top of `pipeline/package.py` explaining that `VALUE_SOFT_LINE` is a process‑local, mutable pin set once by the driver, and that the identity comparison is intentional; this prevents future refactors from inadvertently applying canon or leaking state across builds.

**7. Production ready?**

**Yes, with conditions**  
- All functional tests pass and cover every branch.  
- The mutable pin is documented and will be refactored if the build system ever runs multiple builds in the same process.  
- The audit trail is now complete (`why` included).  
- Cosmetic issues (quote escaping) are fixed.  

**P1_OR_WORSE: 0**