# glm-5.3-flash (z-ai/glm-5.3-flash) 34 s finish=stop usage in 14828 / out 1794 usd~0.071 (upper-bound price)

# CYCLE 2 AUDIT — pp-selectid-0510 (Ruling 41: the line-up search)

## 1. What they caught that I missed

- **glm P1-3 / K3 (SWAP_TOP vs the place's own rule):** the ordering — the place's rule (a short clip only last) applied *before* the SWAP_TOP cap — is the subtle one. The diff (package.py:72–75) does it right, and the test at test_medley.py:329–335 (12 short clips ranked above a full clip; the full clip fills a middle place) proves it. I would have flagged the cap-ordering question; they answered it.
- **glm P1-2 (docstring vs clock):** the ruling-5 clock now starts at `line = (time.time(), _spent(spend))` (package.py:193), *before* the clips-alone `medley` call, while the docstring says "from its clips-alone verdict." glm caught the wording mismatch; the consensus (K4) resolved it as aligned — the verdict is *asked* at that point. I agree: stricter, not looser, and the ruling's own wording ("from the moment its own line-up's clips-alone verdict is asked") supports the code.
- **qwen's "P0" (infinite loop on swap failure):** qwen listed it as P0 then resolved it in its own text. The consensus (K1) verification is correct: `weak` joins `dropped` (package.py:208) *before* the swap, both `lineup_for` calls pass `frozenset(dropped | doomed)`, and `total` increments before every verdict (package.py:192), so the loop is bounded by 8. Not a P0. I agree with the downgrade.

## 2. Agree / disagree

| Finding | Verdict |
|---|---|
| K1 — no loop / no re-judge of dropped moments | **Agree.** Verified: `dropped |= weak` precedes `swap_lineup`, whose `free` excludes `used | avoid` (package.py:64); the swapped line-up is judged exactly once (`swapped = None` after consumption, package.py:174–176). `total < lineups` bounds everything. |
| K2 — hook in the ratings, label map correct | **Agree.** The diff changes the weak-set filter from `lb != "hook"` to include the hook (package.py:200–202), and `by_lab = dict(zip(labs, segs))` maps the same labels medley() rates. The test at :351–358 swaps a hook rated 3. |
| K3 — place's rule before the cap | **Agree, implemented correctly** (package.py:73: `i == len(segs) - 1 or m["duration_s"] >= SHORT_CLIP_S` inside the candidate filter, before `c[:SWAP_TOP]`). |
| K4 — package_over clock wording | **Agree, aligned.** |
| glm P1-2 residual (a line-up that never writes never checks package_over) | **Agree it's intended.** Its verdict spend counts toward the search budget; the package budget binds only a line-up that could deliver. |
| grok's "no P0, no P1, SHIP: yes" | **Agree in substance**, though it's a thin review — it verifies rather than stresses. |

## 3. New findings (this cycle)

**P2-1 — `swap_lineup`'s repeat_ok pass can return a line-up whose `supply_exception` differs from what `lineup_for` would record — no, verified consistent:** the swapped path calls `supply_exception(segs, ctx)` (package.py:176), the same factored function. Not a finding; recorded as verified.

**P2-2 — `swap_lineup`'s `avoid` does not include the *weak* moments' own ids beyond `used`:** actually `used` covers them (they're in `segs`). Verified.

**P2-3 (new, minor) — `swap_lineup`'s hook candidate sort key requires `m["scores"]["hook_first_2s"]` (package.py:70) but the clip path only needs `rank_score`; a pool moment lacking `scores` entirely would raise KeyError.** Every pool moment in the tests carries `scores` (the `pool()` helper at test_medley.py:302–308 adds it), and `cleared` moments come from the same scoring pipeline as `lineup_for`'s inputs, so this is conditional on `lineup_for`'s own contract. P2, conditional.

**P2-4 (new, minor) — the `repeat_ok` combination loop (package.py:77–84) tries `repeat_ok=False` fully before `True`, but `lineup_ok(new, crange, repeat_ok)` is re-evaluated for every combo; with SWAP_TOP=10 and 4 weak places that's up to 2×10⁴ `lineup_ok` calls, each running `stand_alone_check`.** Pure CPU, no model calls; bounded and cheap. P2, observability only.

**P2-5 (new) — `out["search"]["limit"]` reports `lineups` (the parameter), not `LINEUPS_PER_BUILD` (package.py:243).** If a caller passes a smaller `lineups`, the report is still accurate (it reports the actual limit), so this is correct as written — noted only so nobody "fixes" it to the constant.

Nothing rises above P2. I found no P0 or P1 that the consensus missed.

## 4. Revised scores

| Subsystem | Cycle 1 | Cycle 2 | Why |
|---|---|---|---|
| lineup_ok vs lineup_for rule parity | pass (conditional) | pass | K3 test + the diff's filter ordering; the parity test at :343–349 exercises three orders |
| Loop / re-judge safety | pass | pass | K1 verified: `dropped` grows before the swap; `total` bounds the loop |
| Budget enforcement (search + per-package) | pass | pass | The rewritten test at :262–289 covers both: search stop ends the build; a $1.60 line-up stops only itself and the search continues to a package |
| Weak set / hook swap | pass | pass | The hook now joins `weak` (package.py:202); the bar (COHERENCE_MIN) and every gate are untouched in the diff |
| Everything-else-unchanged | pass | pass | The writes/gates/no-voice hunks are additions only (`w_over` check, the `why` recorder, the `search` report); no acceptance changed |

## 5. Final priority list

- **P0:** none.
- **P1:** none.
- **P2:**
  1. package.py:70 — `scores["hook_first_2s"]` KeyError if a cleared moment lacks `scores` (conditional on lineup_for's contract; confirm or use `.get`).
  2. package.py:77–84 — the repeat_ok retry re-runs `lineup_ok` (incl. `stand_alone_check`) over the full product; bounded, CPU-only, note it.
  3. package.py:193 vs the `package_over` docstring — the clock starts just before the verdict call, not after it; one sentence of wording, stricter than the ruling, harmless.

## 6. Single highest-leverage change

Confirm (or defensively `.get`) that every moment in `cleared` carries a `scores` dict with `hook_first_2s` and `rank_score`, since `swap_lineup` reads both unconditionally on the whole pool — the only place the new code trusts a contract it cannot see in this diff.

## 7. Production ready?

**Yes** — no conditions. The two P2s are hardening notes, not blockers: the loop is bounded, the budgets are enforced at the right boundaries, the bar and every gate are unchanged, and the tests exercise the ruling's stated behaviors (the hook swap, the 8-line-up cap, both budget semantics, the place's rule before the cap) with the exact constants.