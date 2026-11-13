# qwen3.8-27b (qwen/qwen3.8-27b) 47 s finish=stop usage in 12199 / out 1521 usd~0.059 (upper-bound price)

# Audit: pp-selectid-0310 (C1_STEP.diff)

## P0 Findings
None.

## P1 Findings

**1. `pipeline/package.py:10-20` — `stand_alone_check` hardcodes the subject, violating the "reproduce the render's call exactly" requirement.**
The function calls `SA.subject_terms("", "bitcoin")` with a hardcoded `"bitcoin"`. The render's `run_fresh.stage_validate` derives the subject from the package's label (e.g., `run_fresh.stand_alone_subject`). If a future package is labeled with a different subject (e.g., `"etf"`, `"macro"`), the pin-stage check will test against `{bitcoin, btc}` while the render tests against the actual subject. This creates a divergence where:
- A line-up that passes the render's topic check (names the actual subject) but fails the pin's topic check (doesn't name "bitcoin") will be **refused at pin** even though the render would accept it. This is a false negative (overly strict), which is safe but breaks the "reproduce exactly" contract.
- Conversely, if the render's subject logic changes, the pin won't track it.

**Mitigation:** The current codebase appears to only produce "bitcoin"-labeled packages, so this is latent. However, the docstring claims it reproduces the render's call "exally," which is false for non-bitcoin subjects. Either parameterize the subject or document the limitation explicitly.

**2. `pipeline/package.py:23-30` — `no_role_on_screen` may over-drop moments due to asymmetric hook/clip opener rules.**
The function drops a moment if it fails **both** `SA.opener("clip", text)` and `SA.opener("hook", text)`. The test at line 205-206 confirms that pronoun openers (e.g., "It is Bitcoin.") pass as clips but fail as hooks, so they are **not** dropped. This is correct. However, the logic assumes that `SA.opener` with `rate=None` is deterministic and that the clip/hook rules are the only factors. If `SA.opener` has other failure modes (e.g., length, punctuation) that differ between clip and hook roles, a moment could be dropped even though it would pass in one role under the render's scorer. The render's scorer (`rate` parameter) can affirm a clip that fails the no-scorer check, so `no_role_on_screen` is **stricter** than the render. This is safe (fail-closed) but may reduce available moments unnecessarily.

**3. `pipeline/package.py:52-53` — `lineup_for` with `need_stand_alone=True` may skip valid line-ups due to the stricter no-scorer check.**
When `need_stand_alone=True`, a candidate line-up is skipped if `stand_alone_check` fails. Since `stand_alone_check` uses `rate=None`, it is stricter than the render (which may use a scorer to affirm a conjunction opener). This means the pin stage may refuse a line-up that the render would accept. This is safe (fail-closed) but may reduce the number of valid line-ups. The test at line 213-214 confirms this: the old pick `["h", "b", "x"]` (where "b" opens with "But") is replaced by `["h", "x", "y"]` when `need_stand_alone=True`. This is the intended behavior, but it means the pin stage is **more restrictive** than the render, which is a divergence from "reproduce exactly."

## P2 Findings

**4. `pipeline/package.py:133-137` — The `stand_alone` gate row's evidence format is verbose and may be hard to parse.**
The `rows` field is a list of strings like `"clip_01: FAIL opener: clip opens on 'but' | topic: names the subject (bitcoin)"`. This is human-readable but not machine-parseable. If downstream tools need to extract per-segment pass/fail status, they must parse the string. Consider using a structured format (e.g., a list of dicts) for the evidence.

**5. `pipeline/package_pin.py:153` — `MEDLEY_GATES` now includes `"stand_alone"`, but `REQUIRED_GATES` does not.**
This is correct: `stand_alone` is only required for medleys, not for all packages. However, the comment at line 150-152 is dense and may be hard to maintain. Consider splitting the comment into separate lines for each gate.

**6. `tests/package/test_medley.py:194-200` — The test hardcodes the render's `run_log.txt` lines 47-49.**
The test asserts that `stand_alone_check` produces the same verdicts as the render's log. This is a good regression test, but it couples the test to the specific log file. If the render's log format changes, the test will break. Consider extracting the expected verdicts into a fixture or constant.

**7. `tests/package/test_medley.py:226-236` — The test `test_build_leaves_no_role_moments_out_before_the_angle_and_seals_the_row` uses a `Rig` class that is not defined in the diff.**
The test references `Rig(ms, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None])` and `rig.run()`, but the `Rig` class is not shown in the diff. This is likely defined elsewhere in the test file, but it is not clear from the diff alone. If `Rig` is a new helper, it should be included in the diff for auditability.

## SHIP: yes with conditions

**Conditions:**
1. **Parameterize the subject in `stand_alone_check`** (P1-1) or document that it only works for "bitcoin"-labeled packages. If the pipeline will only ever produce "bitcoin" packages, add a comment stating this assumption.
2. **Clarify the stricter-than-render behavior** (P1-2, P1-3) in the docstring of `stand_alone_check` and `no_role_on_screen`. State explicitly that the pin-stage check is stricter than the render because it does not use a clip scorer, and that this is intentional (fail-closed).
3. **Include the `Rig` class definition** in the diff (P2-7) or reference the file where it is defined.
4. **Consider structuring the `stand_alone` gate row's evidence** (P2-4) for machine-parseability, if downstream tools will consume it.

The change is safe (fail-closed) and addresses the integrator's hold. The main risk is the hardcoded subject and the stricter-than-render behavior, which should be documented or parameterized.