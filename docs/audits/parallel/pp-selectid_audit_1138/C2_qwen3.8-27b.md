# qwen3.8-27b (qwen/qwen3.8-27b) 54 s finish=stop usage in 32626 / out 2466 usd~0.135 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-1138
# Reviewer: Claude (Cycle 2)

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

**Grok-4.20** was the most decisive: it found **no P0, no P1, no P2** and said "SHIP: yes." Its reasoning was correct on the key point I under-weighted in Cycle 1: the pin-stage `affirmed_verdict` is a *pre-filter*, not the release gate. The render's `validate` re-runs `check_edl` with its own `clip_scorer` on GPU0 at render time, on its current code. A stale `scorer_sha` in a pin can therefore at worst waste one pin (refused at validate), never authorize a release on a stale verdict. This directly refutes Qwen's P0-2.

**Qwen3.8-27B** raised four "P0" items, all rooted in the same misconception (that `package_pin.affirmed_verdict` is the final gate). It retracted every P1 it raised. Its P0-2 (stale `scorer_sha` at pin stage) is the most substantive claim, and it is **refuted** by the architecture: `scorer_verdicts()` in `package.py` enforces `scorer_sha == render_scorer_sha()` at build time; the pin's `affirmed_verdict` is a weaker, independent check that the integrator's `check_pin_only` uses for seal recomputation, not for scorer validation. The render's validate is the true gate.

**GLM-5.3-FLASH** raised P1-1 (diagnostic loss on exception path) and P1-2 (coupling between `verdict_of` and `scorer_verdicts`). Both are valid observability/robustness notes, not correctness bugs. I missed P1-1's specific point: when `d["scorer"]` is not a dict, the `AttributeError` is caught but the record's `why` becomes the exception string, losing the structured diagnostic fields (`kind`, `event`, `scorer_sha`, `threshold`). This is a real gap in the sealed/ledgered record for exactly the malformed-file cases where diagnostics matter most.

## 2. WHERE DO YOU AGREE OR DISAGREE?

| Finding | My position | Reasoning |
|---|---|---|
| **Qwen P0-2** (stale `scorer_sha` at pin) | **Disagree — refuted** | The pin is not the release gate. `scorer_verdicts()` enforces sha equality at build time. The render's validate re-runs the scorer on current code. A stale pin is refused at validate, never released. |
| **Qwen P0-1** (missing `affirmed` key) | **Disagree — refuted** | `v.get("affirmed")` returns `None`; `(None is True)` is `False`. If `rule` is `True`, they disagree → dropped. If `rule` is `False`, they agree → accepted with `affirmed: False`. Fail-closed in both cases. |
| **GLM P1-1** (diagnostic loss on exception) | **Agree — P1** | When `d["scorer"]` is a list or other non-dict, `AttributeError` is caught but the record loses structured fields. Fail-closed, but the sealed record is less useful in the exact cases where you want it. |
| **GLM P1-2** (`verdict_of` trusts producer) | **Agree — P1 (by design)** | `verdict_of` checks only `text_sha256`. The only producer is `scorer_verdicts()`, which pre-filters. `build()` strips any carried verdict and attaches only the index's. A hand-made verdict cannot reach a build. The pin's `affirmed_verdict` is the strict, independent check. This is a documented coupling, not a bug. |
| **Grok: no P0/P1** | **Agree** | All fail-closed paths hold. The architecture is sound. |

## 3. NEW FINDINGS FROM THIS REVIEW

**P1-NEW-1. `package.py:141-142` — Exception path loses structured diagnostics.**
When `d["scorer"]` is not a dict (e.g., a list), `sc.get("kind")` raises `AttributeError`, caught at line 141. The record becomes `{"read": False, "why": "AttributeError: ..."}`. The structured fields (`kind`, `event`, `scorer_sha`, `threshold`) are absent. This is fail-closed (nothing is used), but the sealed/ledgered record loses its diagnostic evidence in exactly the malformed-file cases where you most want it. The `why` chain at lines 135-140 is only reached when `d["scorer"]` is a dict; the exception path bypasses it entirely.

**P1-NEW-2. `package_pin.py:360-371` — `affirmed_verdict` does not check `scorer_sha` against current render code.**
This is **by design** (the pin is a pre-filter, not the release gate), but it is worth stating explicitly: `affirmed_verdict` checks `bool(v.get("scorer_sha"))` (non-empty string), not equality with `render_scorer_sha()`. A pin sealed under an older scorer code will pass `affirmed_verdict` after the render code changes. The render's validate will then refuse it (its own `clip_scorer` runs on current code). This is correct fail-closed behavior, but the pin-stage check is weaker than the build-stage check. A comment or a shared predicate would make the coupling explicit.

**P2-NEW-1. `package.py:289` — `admitted` list computed before `no_role` is finalized.**
`admitted` is computed at line 289 as `verdict_of(m) and m["moment_id"] not in no_role`. But `no_role` is computed at lines 286-287, *after* verdicts are attached (line 285). This is correct: a moment admitted as a clip by its verdict is excluded from `no_role` (because `no_role_on_screen` now reads the verdict). The ordering is intentional and tested. No change needed, but the dependency is subtle.

**P2-NEW-2. `stand_alone.py:452-461` — `affirmed()` with `moments=True` ignores `fault`.**
This is ruling 60's explicit design: "the score alone." The fault is recorded but does not rule. The story path (`moments=False`) still checks `fault != "starts_mid_thought"`. This is correct and tested (line 955-958). No change needed.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| `scorer_verdicts` (reader) | P1 (diagnostic gap) | P1 (confirmed) | GLM's P1-1 is valid: exception path loses structured fields. Fail-closed, but observability gap. |
| `verdict_of` / `with_verdict` | P1 (coupling) | P1 (by design) | The coupling is documented and enforced by `build()` stripping carried verdicts. Not a bug. |
| `affirmed_verdict` (pin) | P0 (stale sha) | P2 (by design) | The pin is a pre-filter, not the release gate. The render's validate is the true gate. Qwen's P0-2 is refuted. |
| `no_role_on_screen` | Clean | Clean | Correctly reads the attached verdict with `moments=True`. Hook role never does. |
| `stand_alone_check` | Clean | Clean | `rate()` answers from attached verdicts. Trimmed segments carry the lock marker. `scorer_pending` removed. |
| `build()` | Clean | Clean | Verdicts attached before STAND_ALONE rules. `trim_refused` before step A. Candidates written atomically. |
| `package_pin` (seal) | Clean | Clean | `scorer_verdict` in `SEALED_LATER`. `scorer_pending` refused. `scorer_problems` and `trim_problems` correct. |
| `stand_alone.py` (copied) | Clean | Clean | `affirmed()`, `clip_scorer()`, `moments` flag. Story path unchanged. |
| Tests | Clean | Clean | 8 new `TestRuling56Scorer` cases. Ruling-49 tests rewritten. All pass. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None.

**P1 HIGH:**
1. `package.py:141-142` — Exception path in `scorer_verdicts` loses structured diagnostics. When `d["scorer"]` is not a dict, the record's `why` is the exception string, and the `kind`/`event`/`scorer_sha`/`threshold` fields are absent. Fix: catch the exception, then attempt to extract whatever structured fields are available before returning.

**P2 MEDIUM:**
1. `package_pin.py:360-371` — `affirmed_verdict` does not check `scorer_sha` against current render code. This is by design (the pin is a pre-filter), but a comment or a shared predicate would make the coupling explicit.
2. `package.py:289` — The dependency between `admitted` and `no_role` is subtle. A comment would help future readers.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The exception path in `scorer_verdicts` (line 141-142) should preserve structured diagnostics even when `d["scorer"]` is malformed, because that is exactly the case where the sealed record needs to explain *why* nothing was used.

## 7. PRODUCTION READY?

**Yes with conditions.**

**Condition:** Fix the P1 diagnostic gap in `scorer_verdicts` (line 141-142) so that the exception path preserves whatever structured fields are available. This is an observability fix, not a correctness fix; the code is fail-closed as-is. The condition is low-risk and can be addressed in a follow-up commit if the current diff is otherwise approved.

**Rationale:** All fail-closed paths hold. The sha matching is correct at the build stage. The pin-stage check is a pre-filter, not the release gate. The render's validate is the true gate. The atomic write is correct. The copied `stand_alone.py` changes nothing on the story path. No check accepts more than before except through an affirmation, by the render's own scorer, of exactly the text that is sealed. The P1 is a diagnostic gap, not an admission leak.