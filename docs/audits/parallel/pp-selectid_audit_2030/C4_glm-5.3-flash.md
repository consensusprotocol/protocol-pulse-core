# glm-5.3-flash (z-ai/glm-5.3-flash) 48 s finish=stop usage in 52204 / out 2749 usd~0.198 (upper-bound price)

# CYCLE 2 AUDIT — pp-selectid, L-y medley (C4_STEP.diff)

## 1. What the others caught that I missed

- **Grok's P0 (runtime_s_estimate)**: I traced `cheap_checks` reading `pk["runtime_s_estimate"]` but did not verify `_package` writes it. It does (line 208 area, via the shared `_package`), and the test at test_medley.py:1738 asserts its value. Grok's P0 was wrong; I should have stated the positive verification in Cycle 1 rather than leaving it implicit.
- **Grok's P2 on the takeaway table** (`proof_ly.py:1331`): `judged = [x for x in takes if x.get("passed") is not None]` — correct, and the ROUND-2 fix (K7, "passed / judged / written" + the summary's "a write stopped first by another gate ... is not judged") addresses it. I missed that the `None`-passed records were silently dropped from the denominator.
- **Qwen's P0-2→P2 downgrade discipline**: his own self-corrections (P0-2, P0-3 both downgraded after tracing) are sound; the `content_s=52` case genuinely fails closed with no landing length, and the ROUND-2 `NoBridgeFits` (package.py:482, 504-508) now refuses before any model call. Agree.

## 2. Agree / disagree

| Finding | Verdict |
|---|---|
| Grok P0 (runtime key) | **Disagree — refuted.** `_package` sets it; test 1738 pins the value; 145 tests pass. |
| Grok P1 (redo "None") | **Partially agree, now fixed.** package.py:856-860 branches on `b` (`if b else " (no takeaway length lands it...")`), and K6's `NoBridgeFits` prevents the no-landing redo. Residual: `b = takeaway_budget(content, written)` at 856 can still be `None` for a *non-bridge* RUNTIME violation; the fallback string is well-formed, so this is cosmetic only. |
| Grok P2 (canon for text comparisons) | **Disagree.** These compare the package's own bytes to themselves (bridge record vs VO line, gated line vs shipped line, package.py:592, package_pin.py:1031). L-k canon is for transcript-vs-locked-text; exact equality is what L-j wants here. |
| Grok P2 (table hides unjudged) | **Agree, fixed in ROUND 2** (proof_ly.py:1310, 1364-1366). |
| Qwen P0-1 (unmeasured verdict skips flagged check) | **Agree with his own downgrade.** Fail-closed; the "not measured" message is accurate. |
| Qwen P0-2/P0-3 (budget edge cases) | **Agree — fail-closed, and K6 now refuses before paying.** `bridge_budget` (package.py:112-125) returns the largest n whose 3..n budgets intersect; `write_takeaway` raises `NoBridgeFits` (504) before `router.call` (524). The test at 1619-1647 exercises 94 clip lengths including the none-fits branch and asserts `prompts == []`. |
| GLM's after-hook/`bridges_after_clip=0` convention note | **Agree it's a P1-adjacent fragility, not a P0.** `assemble_medley` folds `k==0` into `intro` and never writes `0` into `bridges_after_clip` (package.py:235-241); `ly_shape`'s guard `0 < a < n_clips` (577) would drop a literal `0`. Only bites a second producer; the shipped producer is self-consistent, and `ly_shape`'s `sorted(bridged) != sorted(flagged)` would catch the mismatch (fail closed). |

## 3. New findings (this review)

**N1 (P2) — `bridge_budget`'s loop can return a non-maximal n.** package.py:121-124: it iterates n from 12 down and returns the *first* n whose (lo,hi) intersects the 3-word budget. Since `takeaway_budget(content, w(n))` shrinks `hi` as n grows (more bridge seconds), the first hit from the top is indeed the largest n — correct. But the returned `hi` is `min(short[1], long_[1])` where `long_` is the budget *at n*, while the writer may write a bridge of *3..n* words; a shorter bridge gives a *larger* takeaway hi, so the returned (lo,hi) is the tightest — conservative, correct. No bug; noting I verified it.

**N2 (P2) — `write_takeaway` redo path: `written` is a list, `other=()` default.** package.py:825: `written = [fields["bridge"]["text"]] if fields.get("bridge") else ()`. On a redo, `join is not None and not other` is False, so `bridge_budget` is skipped and `takeaway_budget(content, written)` is used — correct per ROUND-2 item 11. But if the *first* write's bridge was declined (`fields["bridge"] is None`), build() re-lines (812-817) rather than redoing, so `written` never goes stale. Verified consistent.

**N3 (P2) — `proof_ly.py` `meter()` monkeypatches `Router._settle` after construction.** proof_ly.py:1252-1267: if the Router itself wraps `_settle` (or another worker shares the instance), the wrapper stacks. Here each process builds its own Router, so it's safe; but the wrapper calls `settle(...)` *then* reads `usage` — if `settle` mutates `usage`, `rep` could change. From the diff, `_settle` only reads. Low risk, unverified beyond the diff.

**N4 (P2) — `ly_shape` counts `texts` (intro + bridges[:-1]) against `LY_MAX_BRIDGES` (package.py:581) but the takeaway sits in `bridges[-1]`; a package with `bridges = []` and `intro` set (no takeaway) fails the earlier `not bridges` check — good. However `after[-1] != n_clips` (574) uses the *last* element; a malformed `after = [2, 1]` with `n_clips=2` passes the takeaway check while `bridged` picks up `js[2]`... which is out of range? `js` has `n-1` entries (indices 0..n-2); `js[2]` for n=3 segments → IndexError, not a clean fail.** Concrete: `vo = {"bridges": ["T", "X"], "bridges_after_clip": [2, 1]}` with 3 segments: `after[-1]==1 != 2` → fails cleanly. Try `after = [1, 2]`, n=3: `after[-1]==2==n_clips` ✓; `bridged = [js[1]]` (a=1, 0<1<2 ✓); `texts = bridges[:-1] = ["T"]` → len 1==1 ✓; then `sorted(bridged) != sorted(flagged)` decides. No IndexError. Downgrade: verified safe; the guard `type(a) is int and 0 < a < n_clips` bounds the index. Withdrawn.

**N5 (P1) — `line_problems`'s extra-slot check.** package_pin.py:1032: `any(k not in slots and (k.startswith("bridge_") or k == "takeaway") for k in by)`. For a *medley with a mid-join bridge*, `slots = ["bridge_1", "takeaway"]` — fine. For a medley where the bridge is after the hook, `slots = ["takeaway"]` only (after=[n_clips]); the line's slot is `"intro"` (package.py:235), which is not in `slots` but also doesn't start with `bridge_` and isn't `takeaway` — so it escapes the extra-slot check, and `by.get("intro") != vo.get("intro")` (1025) covers it. But `vo["intro"]` for a *no-bridge* medley is `None` and `by` has no "intro" key → `by.get("intro")` is None == None ✓. Verified consistent; the asymmetry (intro slot invisible to `bridge_slots`) is a readability wart, not a bug.

**N6 (P2) — `Rig.write` (test_medley.py:1826) duplicates the `NoBridgeFits` precondition rather than calling the real `write_takeaway`**, so the loop-control tests would not catch a drift between `bridge_budget` and the stub's check. Test-only; noted.

**N7 (P2) — `proof_ly.py:1340`: `nb = 0 if not pk.get("bridge") else 1`** — a package whose bridge record exists but is falsy-`{}` would count as zero-bridge. `assemble_medley` writes either `None` or a populated dict, so unreachable from this producer.

## 4. Revised scores

| Subsystem | Cycle 1 | Cycle 2 | Why |
|---|---|---|---|
| package.build loop control | 8/10 | 9/10 | ROUND-2 doomed-moments + early CUTTABLE + pre-paid-gate reads verified; test 1920-1948 covers the ordering. |
| ly_shape / package_pin | 8/10 | 9/10 | R11-mirror record checks (item 12) added and must-fail tested (1682-1691). |
| Budgets (K6) | 6/10 | 9/10 | `bridge_budget` + `NoBridgeFits` closes the empty-intersection hole; 94-length test. |
| providers ledger | 8/10 | 9/10 | `_num` guards bool/inf/nan (test 1985-1990); guard still reads the estimate. |
| proof_ly / table | 7/10 | 8/10 | honest judged/written; own-spend meter; residual: N3, N7 warts. |

## 5. Final priority list

- **P0**: none. (Grok's P0 refuted: `_package` writes `runtime_s_estimate`; test 1738.)
- **P1**: 
  - (a) package.py:577 — `ly_shape` silently drops out-of-range `bridges_after_clip` entries instead of failing; a second producer using the documented `after_clip: 0` convention (package.py:227-228) gets a confusing "not at a join" failure. Make the guard `0 <= a <= n_clips` and fail on anything else.
  - (b) package.py:856 — the RUNTIME redo's `takeaway_budget(content, written)` can return `None` when the violation is not the takeaway's length; the message then says "no takeaway length lands it: shorten the bridge" even when there is no bridge. Cosmetic but misleading to the writer.
- **P2**: N3 (meter wrapper), N6 (Rig duplicates the precondition), N7, and the `bridge_slots`/intro-slot asymmetry (package_pin.py:1010-1018) — document that a medley's after-hook bridge lives in the `intro` slot, invisible to `bridge_slots`.

## 6. Single highest-leverage change

Make `ly_shape`'s join-index guard total (fail, don't silently drop, any `bridges_after_clip` entry outside 0..n_clips) — it is the one place where a second producer's legal package can be rejected with a misleading reason, and it costs one line.

## 7. Production ready?

**Yes with conditions**: (1) fix the P1(a) guard; (2) fix or suppress the P1(b) redo message; (3) keep the 145-test suite green including the 94-length budget sweep. Everything else is P2 polish; the ROUND-2 items 11-15 are correctly implemented and tested.

SHIP: yes with conditions