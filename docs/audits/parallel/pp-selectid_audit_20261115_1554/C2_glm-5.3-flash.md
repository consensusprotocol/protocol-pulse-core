# glm-5.3-flash (z-ai/glm-5.3-flash) 164 s finish=stop usage in 24298 / out 4719 usd_reported=0.001338 usd~0.144 (upper-bound price)

# CYCLE 2 AUDIT — pp-selectid-20261115_1554 (RULING 116, calibrated line-up bar)

Reviewer: continuing from my Cycle 1. I now have Grok's and Qwen's Cycle 1 outputs plus the C1 consensus (including the one acted-on fix: the takeaway-rewrite site now reads `pk["segments"][0]["label"]` instead of the literal `"hook"`).

---

## 1. WHAT DID THEY CATCH THAT I MISSED?

Honest accounting against what I would have flagged:

- **The takeaway-rewrite hook-label bug (qwen, acted on).** In the fixed diff, line 565 reads `lb != pk["segments"][0]["label"]` — the package's own first-segment label, consistent with `labs[0]` everywhere else. In the pre-fix code it was the literal `"hook"`. I should have caught that in Cycle 1: it's exactly the class of bug this audit is for (a site that silently compares against the wrong label, so the hook's rating stays inside the `min()` and the rewrite condition mis-fires). Qwen caught it; the fix is correct and the mutation (L8) was re-aimed and killed. **Missed by me.**
- **The ruling-63 reorder site reading `min(cl.values())` with the hook's rating inside.** The diff at lines 534–539 now excludes the hook (`lb != labs[0]`) and adds the explicit `hook_own.passes is True` guard. Grok's framing ("all sites that compute `min(...)` over clip ratings now correctly exclude the hook") is the right invariant; I should have enumerated the sites myself rather than trusting the two obvious ones (`medley`/`coherence`). **Partially missed** — I flagged the general risk but did not trace `build()`'s reorder and the takeaway-rewrite as concrete sites.
- **Grok's duplication observation** (`lineup_bar.bar` re-implementing `hook_bar`'s timestamp/validity checks). I likely noted it as a nit; Grok correctly graded it P2 and the consensus explains why it's *kept* (each file's refusal names its own calibration; both tested). I now agree with "keep, don't refactor."

## 2. WHERE DO I AGREE / DISAGREE?

| Their finding | My verdict | Why |
|---|---|---|
| Grok: timestamp/validity logic duplicated from `hook_bar` [P2] | **Agree, keep as-is** | The consensus's reason is sound: the refusal strings name their own calibration ("the line-up calibration's…"), and both are tested. A shared helper would couple the two files' error contracts. Not worth the churn. |
| Grok: the calibration file carries full through-lines/story IDs/pins — a content dependency [P2] | **Agree, but weaker than Grok thinks** | The `TestTheLiveCalibration` test (diff lines 795–807) derives the floors from `proof/clips116/` on every run, so a stale or hand-edited copy fails. A new prompt version forces re-measurement *by design* (floors are only valid for the question they were measured under — the consensus says this and it's correct). The "minimal rating vectors" suggestion would actually *weaken* the provenance. **Disagree with the suggested remedy; agree the coupling exists.** |
| Grok: 12× repeated parenthetical, inconsistent patching styles, namedtuple for `floors_for` [P3] | **Agree, all nits** | The two patching styles in `TestRuling116LineupBar` (lines 951, 966: `mock.patch.object(PK, "_live_lineup_bar", ...)` vs `mock.patch.object(PK, "COHERENCE_MIN", PK.COHERENCE_MIN)`) — note the second is a *no-op* patch (patching a value with itself), which is a readability trick, not a defect. Still P3. |
| Qwen: `floors_from`'s `vals` comprehension + `len(vals) != len(rs)` | **Agree it's correct, one subtlety** | `vals = [min(r["clips"].values()) if p == "clip" else r.get(p) for r in rs if r.get("clips")]` — the `if r.get("clips")` filter means a run with `clips` present but *empty* (`{}`) yields `min({})` → ValueError, which is caught by the `len(vals) != len(rs)`... no wait: a run with `clips={}` passes the filter, `min({})` raises, so it's caught by the try/except? No — there's no try/except in `floors_from`; `min({})` raises `ValueError` naturally, which is the documented failure. Actually `min({})` raises `ValueError: min() arg is an empty sequence` — that *is* the intended "a run without its ratings measures nothing" path, and the test at diff line 715 (`clips_alone=[{"clips": {}}]`) exercises it. Correct. |
| Qwen: `floors_for` strictly gates on `backend == live["rater"]` | **Agree — this is the heart of check (1)** | Line 94: `if live is not None and backend == live["rater"]`. Exact-string match on the rater. The rig's `RIG_RATER = "xai:grok"` vs production's `"xai:grok-4.20-0309-reasoning"` — the conftest fixture patches `_live_lineup_bar` wholesale, so the rig's shorter name is compared against the rig's own backends, which answer as `"xai:grok"`. Consistent. No gap. |
| C1: the acted-on fix (hook label in the takeaway-rewrite) | **Agree, correctly fixed** | Line 565 now matches every other site's `labs[0]` convention, and the mutation was re-aimed and killed. |

**Disagreement worth noting:** nobody flagged that `lineup_bar_mark` (diff lines 472–480) reads `med.get("calibration_sha256")` but *not* `coh.get("calibration_sha256")` — it takes the sha only from the medley verdict. If the two verdicts were judged under *different* calibration files (possible: the file's mtime changes between the medley call and the coherence call within one build, since `_live_lineup_bar` caches per-minute), the mark could record a sha that doesn't match the coherence verdict's floors. See new findings.

## 3. NEW FINDINGS (Cycle 2)

**[P2] `lineup_bar_mark` records only the medley verdict's calibration sha — the two verdicts can disagree.**
`package.py` lines 472–480:
```python
return {"note": LB.NOTE, "floors": {"clips_alone": med.get("floors"), "coherence": coh.get("floors")},
        "calibration_sha256": med.get("calibration_sha256"), "ruling": "116"}
```
The floors of *both* verdicts are recorded, but the sha comes only from `med`. Within one `build()`, `medley()` and `coherence()` each call `lineup_floors` → `_live_lineup_bar()`, whose cache key is `(st_mtime_ns, int(time.time() // 60))`. If the calibration file is rewritten (or the minute rolls) between the two verdicts, `med` and `coh` can carry floors+sha from *different* calibration generations. The mark then asserts "line-up passed on the calibrated bar" with a sha that doesn't correspond to the coherence floors it also publishes. Not wrong-result (each verdict's own floors are what gated it, and both are recorded), but the mark's provenance is incomplete. Fix: either record both shas, or assert `med["calibration_sha256"] == coh["calibration_sha256"]` (and return None / the standard-bar path when they differ). Severity: P2 — the window is one minute, and a re-sealed calibration mid-build is rare, but the mark is meant to be a provenance record.

**[P2] `_live_lineup_bar`'s cache key uses `st_mtime_ns` but the failure path caches `(None, minute)` — a file created *within the same minute* as a failed stat is invisible until the next minute.**
`package.py` lines 449–460:
```python
try:
    k = (os.stat(LB.PATH).st_mtime_ns, int(time.time() // 60))
except OSError:
    k = (None, int(time.time() // 60))
```
If the calibration file doesn't exist at t=0 (stat fails → key `(None, m)`) and is written at t=0+30s (same minute), the next call in that same minute computes the *same* key `(None, m)` — wait, no: the second call's `os.stat` now *succeeds*, so its key is `(mtime_ns, m) ≠ (None, m)`. The cache is keyed on the *current* stat, not a stored one, so this is actually correct. Retracted — the key is computed fresh each call. **No finding.** (I note it because it's the kind of thing that looks like a bug and isn't; the per-minute granularity means a mid-minute re-seal is picked up on the next call, not the next minute, since the key includes the new mtime.)

**[P3] `floors_from`'s `low` list is built but the "stopped at" floors are applied before the caller sees the un-clamped values — the `floors_below_3` field in the shipped calibration is `[]`, so this path is untested against the live file.**
Diff line 404: `"floors_below_3": []`. The unit test (line 710) exercises the clamping path with synthetic runs, but the live calibration's floors are all exactly 3, so the shipped file never demonstrates the clamp. Fine — the test proves the *function*; the live file proves the *data*. No action.

**[P3] `TestRuling116LineupBar.test_ruling_63_...`'s "standard" branch patches `PK.COHERENCE_MIN` with itself.**
Line 952: `mock.patch.object(PK, "COHERENCE_MIN", PK.COHERENCE_MIN)` is a no-op. It reads as if it's doing something. Grok called the *inconsistency*; I'd add that the second operand of the patch is literally dead. Harmless.

**[P3] `proof_ledger.py` line 653 calls the private `PK._live_lineup_bar()`** while everything else in that function goes through public names (`PK.hook_live_bar()`). Consistency nit; the underscore is load-bearing only by convention.

**[P2, verification] Check (2) — "no site still judges a line-up on COHERENCE_MIN with the hook's rating inside" — I traced every `COHERENCE_MIN` reference reachable from the line-up path.** In the diff:
- `medley` (line 512): `min(x for lb, x in v["clips"].items() if lb != labs[0]) >= fl["clip"]` ✓
- `coherence` (line 495): same exclusion, plus `v["vo_point"] >= fl["vo_point"]` ✓
- `last_clip_only` (line 526): `x < floor` with `floor` from `med["floors"]`, hook excluded ✓
- ruling-63 reorder (lines 534–539): hook excluded, `hook_own.passes is True` added ✓
- weak-clip set (line 548): `x < floor`, hook discarded at line 553 (`weak.discard(segs[0]["moment_id"])`) ✓
- takeaway-rewrite (lines 564–566): hook excluded via `pk["segments"][0]["label"]`, `hook_own.passes is True` required ✓
- weak clips there (line 576): `.get(sg["label"], cfl["clip"]) < cfl["clip"]` — note the *default* is now `cfl["clip"]`, not `COHERENCE_MIN`. Correct: a segment whose label is missing from the verdict's clips is treated as *passing* its floor, which is the fail-open direction for a missing rating... actually it's the conservative direction (a missing clip counts as at-floor, so it's never "weak", so it's never dropped). Since `coherence()` always writes every segment's label into `v["clips"]` (the rig at line 849 and the real function both do), the default only fires for a malformed verdict. Acceptable; the standard bar's behavior is preserved because `cfl` falls back to `STANDARD_LINEUP["coherence"]` when `floors` is absent (line 560). ✓
- `STANDARD_LINEUP` (lines 436–437) is the only remaining literal-`COHERENCE_MIN` line-up judge, and it's the intended fallback. ✓

Check (2) passes. The only remaining question: **is there a site that reads `med["floors"]`/`coh["floors"]` when `bar` says "standard" but the verdict dict lacks `floors`?** `last_clip_only` line 525 and the takeaway-rewrite line 560 both do `med.get("floors") or STANDARD_LINEUP[...]` — correct fail-closed-to-strict. ✓

**[P3] Check (3) — the floors in the shipped file.** I recomputed by hand from the embedded runs:
- `clips_alone` clips across all four packages, excluding the hook slot: 0c68b589 → {4,4,4,4,4,4}; 13949b7c → {3,4,4,3,4,4}; 37c5b5f5 → {4,4,4,4,4,5,4,4,5,4,4,5}... wait, each package has 3 runs × 2 clips = 6 values. 37c5b5f5: (4,5),(4,5),(4,5) → min 4. 41f29b1f: (4,3),(4,4),(4,3) → min 3. Global min = 3. ✓
- `coherence` clips: 0c68b589 → (5,3),(4,3),(4,3) → 3; 13949b7c → (5,4)×3 → 4; 37c5b5f5 → (5,4)×3 → 4; 41f29b1f → (4,3),(4,4),(5,4) → 3. Global min = 3. ✓
- `vo_point`: 0c68b589 → 3,3,4 → 3; others 4,4,4. Global min = 3. ✓
- `floors_below_3` = [] ✓ (no rating below 3 in the source).
- Joins: 0c68b589 flagged=[]×3; 13949b7c flagged=["hook -> clip_01"]×2, []×1 → max 1 = LY_MAX_BRIDGES (the test at line 807 asserts `max(len(flagged)) == PK.LY_MAX_BRIDGES`, which also *verifies the law's constant* — nice). ✓

Check (3) passes.

**[P3] Check (4) — the mark.** `lineup_bar_mark` requires `bar == "calibrated"` on *both* verdicts (line 477), returns None otherwise; the pin test (lines 781–786) proves `package_sha256` is unchanged with the mark present — outside the seal. `package_pin.py` lines 598–599 add it conditionally, same pattern as `hook_bar`. ✓ (modulo the sha-provenance P2 above).

**[P3] Check (5) — the tests.** 7+7 as claimed; the mutation count (13/13) is asserted, not shown, but the control-run discipline is described. The one test I'd strengthen: `test_the_mark_...`'s standard-bar case (lines 990–994) patches `_live_lineup_bar` to `(None, ...)` *after* the rig was constructed — the rig's `medley`/`coherence` stubs call `PK.lineup_floors`, which calls the patched function, so the verdicts record `bar="standard"` and the mark is absent. Correct, but it relies on the stub calling `lineup_floors` *lazily at call time*; if the stub ever captured the floors at construction, the test would silently pass for the wrong reason. It doesn't. Fine.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| `lineup_bar.floors_from` | 9.5 | 9.5 | Unchanged; the empty-`clips` ValueError path is the documented failure and is tested. |
| `lineup_bar.bar` (validation) | 9 | 9 | Unchanged; duplication from `hook_bar` is deliberate and tested. |
| `floors_for` / rater gating | 9.5 | 9.5 | Exact-string rater match; no gap found. |
| `package.medley`/`coherence` integration | 9 | 9.5 | The takeaway-rewrite label fix (acted on in C1) closes the last inconsistent site; my full trace of check (2) found no remaining `COHERENCE_MIN`+hook site. |
| `build()` sites (r62/r63/weak/rewrite) | 8.5 | 9 | Both previously-missed sites now read the verdict's own floors and exclude the hook; the added `hook_own.passes is True` guards are correct. |
| The mark + pin | 9 | 8.5 | New: the sha-provenance gap (medley's sha only, verdicts can straddle a calibration re-seal). Downgraded. |
| Tests | 9 | 9 | Comprehensive; the no-op `COHERENCE_MIN` patch and the private-`_live_lineup_bar` call in proof_ledger are nits. |
| Calibration data | 9.5 | 9.5 | Hand-recomputed: floors are the source minimums; joins = the law's one; `floors_below_3` consistent. |

## 5. FINAL PRIORITY LIST

- **[P2] `package.py:479` — `lineup_bar_mark` takes `calibration_sha256` from the medley verdict only.** If the two verdicts straddle a calibration re-seal (the `_live_lineup_bar` cache key includes the minute and the file mtime), the mark publishes coherence floors with a medley-generation sha. Record both shas or require they match. (The shipped `valid_h: null` + one-fixed-source makes this near-impossible today; it's a provenance defect, not a wrong result.)
- **[P3] `package.py:472-480`** — consider asserting `med["bar"] == coh["bar"] == "calibrated"` *and* equal shas inside `lineup_bar_mark` rather than at the call site's `if lm:` (line 584-586); the current split means a future caller could set a half-mark.
- **[P3] `test_medley.py:952, 967`** — `mock.patch.object(PK, "COHERENCE_MIN", PK.COHERENCE_MIN)` is a no-op; replace with a comment or drop.
- **[P3] `proof_ledger.py:653`** — `PK._live_lineup_bar()` is private; expose a `PK.lineup_live_bar()` alias or accept the convention.
- **[P3] `lineup_bar.py:44`** — the `if r.get("clips")` filter means a run with `clips: null` is silently skipped, then caught by `len(vals) != len(rs)`; a run with `clips: {}` raises from `min()` directly. Both are "measures nothing" failures, but they fail through two different mechanisms; one explicit `if not r.get("clips"): raise` would be clearer.

No P0. No P1.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Make `lineup_bar_mark` record (or require equality of) *both* verdicts' `calibration_sha256` — it's the only place where the mark's provenance can diverge from what actually gated the package.

## 7. PRODUCTION READY?

**Yes, with one condition.** Ship it once `lineup_bar_mark` (package.py:472–480) records both verdicts' calibration shas — or, minimally, asserts they're equal, so the "line-up passed on the calibrated bar" mark can never publish floors from one calibration generation under another's sha. Everything else (the P3s) can follow.

P1_OR_WORSE: 0