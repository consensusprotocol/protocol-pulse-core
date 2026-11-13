# glm-5.3-flash (z-ai/glm-5.3-flash) 166 s finish=stop usage in 8528 / out 3128 usd~0.073 (upper-bound price)

# CYCLE 2 — FINAL REVIEW (pp-selectid-0352)

## 1. WHAT DID THEY CATCH THAT I MISSED?

Honest accounting against the consensus table and the three Cycle 1 outputs:

- **The differential test (K1).** The consensus records that glm's condition 1 — "prove, not assert, that ad_read_out refuses exactly what the package stage refuses" — was answered with a differential test calling `PK.exclusion_for` with a router that throws if called (`test_medley.py:145-153`). I did not weight this enough in Cycle 1: it is the strongest evidence in the diff, because it runs the package stage's *own* screen on the same moment and the same stubbed context, and asserts verdict/why/backend equality. It converts the "same rule, earlier" claim from an assertion into a checked property.
- **The contract verification (K2).** The consensus states, with file:line, that (a) `exclusion_for` passes `CI.context_around`'s raw before-string to `exclusion_verdict`, (b) `src_of` is `context_integrity.source_for` which raises KeyError on a missing Source — the same lookup `exclusion_for` uses — and (c) a moment's `sentences` is always `[k0, k1]` per `moments.record`, the same fields both paths index. I flagged the unseen contracts as residual risk; the consensus resolved them in code. That was the right disposition and I under-credited it.
- **glm's P1-1 self-downgrade.** glm correctly traced that a marker in the moment text with an empty before-context is refused identically by both stages, so its "empty vs None context" concern collapses to a coverage note, not a divergence. I should have reached that conclusion myself in Cycle 1 rather than leaving it hedged.

What nobody missed, and I confirm: grok's and qwen's "no P0, no P1" verdicts were, on the evidence available, correct.

## 2. WHERE DO I AGREE OR DISAGREE?

**K1 (differential test) — AGREE, IMPLEMENTED.** `test_medley.py:145-153` runs `PK.exclusion_for(never, m, ...)` where `never`'s `call` raises if invoked, so the verdict returned is provably the deterministic part only, and asserts `("exclude", got["a"], "deterministic")` — the same why-string `ad_read_out` produced. This is exactly the "refuses exactly what the package stage refuses, nothing more" proof the task asks for, on the one moment the stub gives a marker for. One scope note (not a disagreement): the differential runs only for moment "a" (marker in the sentence before); the negative case (moment "b", no marker → not in `got`, and `exclusion_for` would return the model path) is covered only implicitly by `got == {"a": ...}`. Acceptable, since the shared function `ad_read_marker` is what both call.

**K2 (contracts outside the diff) — AGREE, VERIFIED.** Given the consensus's cited lines, the equivalence argument holds: `ad_read_out` (package.py:57) makes the identical `CI.context_around(src_of(m, sources), m["sentences"][0], m["sentences"][1], *m["words"])` call that `exclusion_for` makes, then applies the identical `ad_read_marker` that `exclusion_verdict`'s deterministic part now delegates to (moments.py:32-35). Same inputs, same function, same verdict. The refactor of `exclusion_verdict` itself (moments.py:27-31 → 32-35) is behavior-preserving: the why-string, risks, backend, measured, replayed fields are byte-identical, and the model verdict after it is untouched.

**K3 (why_none "angle N: None" + 900-char truncation) — AGREE, IMPLEMENTED.** package.py:96-99: each angle's reason is `t.get('why') or t.get('result') or 'no reason recorded'`, truncated at 250 chars per angle — this fixes both glm's None-why cosmetic and its mid-escape clipping concern, and the guard `if out["package"] is None and not out.get("why_none")` correctly defers to any earlier-set reason (the `<3 channels` early return at :89-91 returns before this code, so no overwrite; any other path that set why_none with package still None is respected by `not out.get("why_none")`). glm's own re-derivation (P1-2 → P2-1) matches; I adopt it.

**K4 (KeyError breadth; census semantics) — AGREE, DOCUMENTED.** package.py:48-52: the docstring states both that any unreadable field (KeyError) is skipped and that `out` is a census of moments that survived `no_role_on_screen`. Both skips fail closed: a skipped moment still meets the package stage's screen, because the package stage's `exclusion_for` performs the same lookup and refuses no-context moments. Nothing new passes.

**K5 (double AD_MARKERS search) — AGREE, IMPLEMENTED.** moments.py:14: one `hit = AD_MARKERS.search(txt)`, the captured group reused in the reason. glm's P2-2 resolved.

**glm P1-12 (step A's "screened" count changes) — AGREE, DOCUMENTED.** package.py:73-74, 82, 87-88: the log line now names the ad-read count separately, and `out["ad_read"]` is recorded. Step A sees fewer moments by design; the count is accounted, not silently lost. This is the intended "only earlier, never more" behavior.

**qwen's P2-1 (src_of returning a key context_around doesn't raise on) — PARTIALLY AGREE.** Qwen's analysis concludes the behavior is correct (skip → package stage refuses, fail closed), and I agree with the conclusion. But its premise — that `context_around` might return None *without* raising for a bad key — is unverifiable from the diff; the consensus's K2(b) (src_of raises KeyError, same lookup as exclusion_for) is the stronger, code-cited resolution. Either way the skip path is safe, so the residual is a documentation question, not a defect.

**grok's blanket "none" — AGREE.** Its one-line justification enumerates precisely the properties that matter (identical marker function, identical context source, skip-and-defer, why_none guarded, acceptance surface unchanged) and each is checkable in the diff. No over-claim.

## 3. NEW FINDINGS FROM THIS REVIEW

**N1 (P2) — the differential test's coverage is one-sided, and the test's own structure makes the negative case easy to lose.** test_medley.py:148-151: the loop `for m in ms[:2]` computes `v` for "a" only (`... if m["moment_id"] == "a" else None`), so the assertion exercises the marker-in-the-sentence-before case but never asserts that a marker-free moment ("b") yields the *same* non-refusal both sides — it is only implied by `got == {"a": ...}` at :144. Additionally, the `try/finally` at :145-153 restores `CI.context_around` correctly, but the second stub assignment at :146 is inside the `try` whose `finally` restores — fine — yet the whole differential block would silently pass if `exclusion_for`'s signature changed and the call raised, because the `AssertionError` from `never.call` is only thrown if the model path is reached; a `TypeError` from a signature drift would propagate (good, actually — it fails the test). Net: a P2 robustness note, not a defect. Suggested (non-blocking): also assert `PK.exclusion_for(never, ms[1], ...)` returns a verdict whose deterministic part is None, i.e. that the model path is reached for "b" — which the `never` router's throw would then exercise.

**N2 (P2) — `ad_read_out`'s skip-on-`before is None` vs `ad_read_marker`'s None-tolerance is a deliberate, documented asymmetry — but the docstring's "no context" wording could be read as covering only the (None, ·) case.** package.py:60: `why = M.ad_read_marker(m["text"], before) if before is not None else None`. Since `ad_read_marker` handles `before_text=None` (moments.py:12, `(before_text or "")`), the `before is not None` guard at :60 is redundant *for the marker function* — but it is load-bearing for the *contract*: it makes "no context → skip here, package stage refuses" explicit rather than incidental. glm's Cycle 1 P1-1 worried the sentinel might be `""` rather than `None`; the consensus's K2(a) (exclusion_for passes the raw before-string) plus the differential test's `("c": (None, None))` case at :136 pins the None case. If `context_around` ever returned `""` for no-context, `ad_read_out` would screen on an empty before-string — which, as glm itself showed, produces the same verdict as the package stage (marker search on `""` finds nothing; a marker in the moment text is refused by both). So: no divergence either way. Keep the guard; add one docstring clause if you touch this file again. P2, documentation only.

**N3 (P2) — `out["ad_read"]` is a census of survivors of no_role, but the log line's arithmetic is not self-checking.** package.py:85-88: the log prints `n_usable`, `len(no_role)`, `len(ad_read)`, `len(cleared)`; a reader cannot tell from the line alone that these are sequential filters (usable − no_role − ad_read = the step-A population). The `out` dict carries all four numbers, so this is reconstructible; P2, cosmetic.

**N4 (verification note, not a finding) — the why_none fallback's interaction with `budget_stop`.** package.py:93-96: the angle loop breaks when `out["packages"] or out.get("budget_stop") or over_budget(ai)`; if it breaks on `budget_stop` with no package, the new fallback at :96-99 sets why_none from `out["tried"]` — which is correct and more informative than the previous `None`. If `out["tried"]` is empty (no angle ever recorded, e.g. the prescreen cleared nothing but ≥3 channels — actually that's caught by the `<3 channels` early return only on channel count, so a 3-channel/0-cleared... no, `<3` channels of *cleared* moments returns early; if ≥3 cleared but the angle call itself failed, `tried` may be empty) → the `"no angle gave a line-up to try"` branch at :99 covers it. Both branches of the conditional expression are reachable and correct. No defect.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| moments.py (ad_read_marker + exclusion_verdict refactor) | pass, minor hedge on unseen contracts | pass | K2's code-cited contract verification + the differential test close the hedge; the refactor is byte-identical in its return record |
| package.py (ad_read_out, build() filter, why_none) | pass, residual risk on skip semantics | pass | The skip paths are documented (K4), fail closed, and the differential test pins the equivalence; why_none guard verified correct (glm's own re-derivation) |
| test_medley.py (new tests) | pass | pass, with N1 (P2) | The differential test is the strongest evidence in the diff; its one-sided loop is a robustness note, not a gap |
| Overall | no P0/P1, ship | no P0/P1, ship | Nothing in the other models' findings or my re-derivation changed the severity; the residuals are documentation/coverage P2s |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL** — none.

**P1 HIGH** — none.

**P2 MEDIUM**
1. **test_medley.py:148-151 (N1)** — the differential loop exercises only the positive case (moment "a"); add the negative case (moment "b": no marker → `ad_read_marker` returns None → the model path is reached, which the `never` router's throw would confirm). Non-blocking; the shared-function argument covers correctness today.
2. **package.py:60 + 48-52 (N2)** — the `before is not None` guard is redundant to `ad_read_marker`'s own None-tolerance but load-bearing for the documented "skip here, refuse there" contract; if the file is touched again, add one clause noting the `""`-vs-None sentinel equivalence (both produce the same verdict, per glm's Cycle 1 derivation).
3. **package.py:85-88 (N3)** — the log line's four counts are sequential filters; consider naming the surviving population explicitly so the arithmetic is self-checking. Cosmetic.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The differential test (test_medley.py:145-153) is what actually proves the standing law — "refuse exactly what the package stage refuses, only earlier, nothing new" — so the highest-leverage remaining change is extending it to the negative case (moment "b") so the equivalence is pinned on both sides of the marker, not just one.

## 7. PRODUCTION READY?

**Yes.** No conditions required to ship. If the branch is touched again before merge, take the three P2s in order (N1's negative differential case first — it is a five-line test addition that converts the last inferred property into a checked one).

Verification note: the consensus records test_medley 54 OK and test_moments OK, with the other suites run before the commit; I cannot re-run them here, so my "yes" rests on the diff's internal consistency, the consensus's cited contract lines, and the differential test's logic — all of which check out.