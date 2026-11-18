# gpt-oss-20b (openai/gpt-oss-20b) 47 s finish=stop usage in 9172 / out 7688 usd_reported=0.001237 usd~0.143 (upper-bound price)

**1. What the other models caught that I missed**

| Issue | Source | Severity | Why it matters |
|-------|--------|----------|----------------|
| **ONSET_QUIET regex tightly coupled to a prose string** | Qwen3.8‑27B | P2 | If the wording of the `why` field changes (e.g., “70 ms of genuine quiet before the hook’s first onset < 90 ms” → “70 ms of genuine quiet before the hook’s first onset is below 90 ms”), the regex will silently fail, the hook will stay hard, and the never‑empty pass will never produce a package. No safety risk, but the feature silently stops working. |
| **`soft_graphics` mutates `m["visual"]` inside a filter predicate** | Qwen3.8‑27B | P2 | The mutation is hidden from the caller and can lead to subtle bugs if the same moment is processed more than once or if other code later expects the original visual record. It also makes reasoning about the code harder. |
| **Missing explicit guard for `soft` in `_build` when iterating over `cleared`** | Qwen3.8‑27B | P2 | The loop `for m in (cleared.values() if soft else ())` is correct, but the comment “RULING 146 (2): G17a's quiet before the hook's first word” is misleading – it applies only when `soft` is true. The code is fine, but the comment could mislead future maintainers. |
| **Potential double‑assignment of `m["visual"]` formats** | Qwen3.8‑27B | P3 | `soft_graphics` sets `formats=["16x9"]`; later `_build` sets `m["visual"] = dict(m["visual"], formats=["16x9"])`. The second assignment is redundant but harmless. It could be cleaned up. |

**2. Agreement / disagreement with their key findings**

| Finding | Agree / Disagree | Reason |
|---------|------------------|--------|
| ONSET_QUIET regex coupling | **Agree** | It is a maintenance risk; the feature will silently break if the wording changes. |
| `soft_graphics` side‑effect | **Agree** | The mutation is hidden and could cause subtle bugs. |
| Comment mis‑labeling | **Agree** | The comment could mislead; it should be clarified. |
| Redundant format assignment | **Agree** | Minor, but worth cleaning. |
| No hard‑pass regressions | **Agree** | Tests confirm the clean pass still rejects the ticker and quiet‑shortfall cases. |
| Flagging logic correctness | **Agree** | The flag rows are added only when `soft` is true and the relevant condition holds. |

**3. New findings from this review**

1. **`soft_graphics` mutates the moment’s visual record** – this side‑effect is not obvious and could be problematic if the same moment is reused elsewhere.  
2. **The ONSET_QUIET regex is brittle** – a change in the wording of the `why` field will silently disable the soft pass.  
3. **Redundant format reassignment** – `m["visual"]` is set to `formats=["16x9"]` twice.  
4. **Comment clarity** – the comment in `_build` about RULING 146 (2) is misleading; it only applies when `soft` is true.  
5. **Potential missing guard** – the `soft` variable is used in several places; if it is ever `None` or not defined, the code would crash. The current code assumes it is always a boolean, which is true in the current context but should be documented.  

**4. Revised scores**

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|-----------|---------|---------|-------------|
| `package.py` (soft pass logic) | P0 | **P2** | Side‑effect of `soft_graphics` and regex brittleness. |
| `visual_pin.py` (`graphics_only`) | P0 | P0 | No new issues. |
| `package_pin.py` (`SOFT_GATES`) | P0 | P0 | No new issues. |
| `tests/package/test_ruling_137.py` | P0 | P0 | Tests cover the new behavior but do not test the regex brittleness or side‑effect. |
| **Overall** | P1_OR_WORSE: 0 | **P1_OR_WORSE: 0** | No P0/P1 findings; only P2 issues identified. |

**5. Final priority list**

| Priority | Issue | File & Line | Action |
|----------|-------|-------------|--------|
| **P2** | `ONSET_QUIET` regex coupling to prose | `pipeline/package.py` L10 | Replace regex with a structured flag (e.g., `h["failure_kind"] == "quiet_shortfall"`) or add a unit test that asserts the exact `why` string. |
| **P2** | Hidden mutation in `soft_graphics` | `pipeline/package.py` L13‑L24 | Extract the mutation into a separate helper (`mark_soft_graphics(m)`) and document that it mutates `m["visual"]`. Add a test that verifies the mutation is idempotent and does not affect other logic. |
| **P2** | Redundant format reassignment | `pipeline/package.py` L53‑L56 | Remove the second `m["visual"] = dict(m["visual"], formats=["16x9"])` or merge it into `soft_graphics`. |
| **P3** | Misleading comment in `_build` | `pipeline/package.py` L44‑L47 | Clarify that the loop runs only when `soft` is true. |
| **P3** | Potential missing guard for `soft` | `pipeline/package.py` | Add a defensive check or documentation that `soft` is always a boolean. |

**6. The single highest‑leverage change**

Replace the brittle `ONSET_QUIET` regex with a structured flag (e.g., `h["failure_kind"] == "quiet_shortfall"`) so that the soft pass for G17a is robust to wording changes and does not silently fail.

**7. Production ready?**

**Yes, with conditions.**  
- Implement the two P2 fixes (regex → structured flag, extract mutation).  
- Add unit tests for the new logic and for the side‑effect.  
- Clean up the redundant format assignment and clarify comments.  
Once those changes are merged, the code will be safe, maintainable, and fully covered by tests.