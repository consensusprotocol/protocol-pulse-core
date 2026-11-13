# glm-5.3-flash (z-ai/glm-5.3-flash) 100 s finish=stop usage in 26085 / out 3366 usd~0.129 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 AUDIT (pp-selectid-1207, rulings 61–64)

## 1. WHAT THE OTHERS CAUGHT THAT I MISSED

- **Grok's P0 (itertools import)** — I missed it. I never checked whether `itertools` was imported at module level; I treated `reorder()`'s `itertools.permutations` as if the import came with the diff. Grok was right to flag it, and the consensus (R1) closes it: `package.py:50` (unchanged, outside the diff) already reads `import itertools`, and the module already used `itertools.combinations` in `lineup_for` and `itertools.product` in `swap_lineup`. The new reorder tests execute the function, so a missing import would fail the suite. **Downgrade: not a finding.** I should have verified this myself in Cycle 1.
- **Qwen's P0 (unrated hook crashes `hrank`/`hooks_txt`)** — I missed the *interaction* between `can_open()`'s "not rated yet → True" branch and the downstream `hook_own(m)["rating"]` subscripts. Qwen's crash scenario is real *in isolation*; the consensus (R2) closes it: `build()` stamps `hook_rating` on every cleared moment before `passing` is computed, so every moment in `passing` carries the key and `hook_own` never returns None there. The "not rated yet" branch serves callers outside `build()` (unit tests, ruling-59 reading). I agree with the refutation, but Qwen's instinct was correct — the invariant lives outside the diff, which is exactly the kind of thing a strict reviewer should have hedged.
- **GLM's P1-1 (other callers of `coherence()`)** — I noted the signature change but did not flag the grep. GLM and Grok both did. The consensus answers it: the diff shows one call site (line 425–426, now passing `hook=segs[0]`), and the instruction to grep for others stands as a merge condition, not a code defect.
- **GLM's P1-2 / Qwen's P1 (ruling 62's count condition)** — I missed the subtlety that `len(segs) - 1 > LY_CLIPS[0]` is a *count* condition, not a floor condition. The consensus (R3) resolves it: `segs` includes the hook, so `len(segs) - 1` is the clip count, and the condition holds exactly when dropping keeps ≥ `LY_CLIPS[0]` (2) clips. Correct, but it took three models to converge on it — the code would benefit from a comment.

## 2. WHERE I AGREE / DISAGREE

| Finding | Verdict | Why |
|---|---|---|
| Grok P0 (itertools) | **Agree, refuted** | `package.py:50` imports it; tests execute `reorder()`. |
| Qwen P0 (unrated hook → hrank/hooks_txt crash) | **Agree, refuted** | `build()` stamps `hook_rating` on every cleared moment before `passing`; the "not rated yet" branch of `can_open` serves callers outside `build()`. |
| GLM P1-1 (other `coherence()` callers) | **Agree** | One call site in the diff; grep is a legitimate merge condition. |
| GLM P1-2 (ruling 62 count vs. floor) | **Agree with consensus** | `len(segs) - 1` = clip count; the condition is exactly "dropping keeps ≥ 2 clips". |
| GLM P1-2 (repeat_ok waives the floor?) | **Agree with consensus (R4)** | `lineup_ok` checks the seconds window per call; `repeat_ok` only admits L-y 4's one repeated channel. |
| Grok P1 (follow-up angle_write lacks avoid_vendor/family) | **Partially agree** | Grok's observation is correct (diff line 328: no `avoid_vendor=...` kwargs); the consensus (R5) says it's intentional — angle_write is a WRITER role, and the first angle call never passed them either. I agree it's intentional, but the *follow-up* call also omits `deadline_s`... no wait, it has `deadline_s=WRITER_DEADLINE_S` (diff line 331). Grok's finding is refuted on the vendor point; the deadline is present. |

## 3. NEW FINDINGS (Cycle 2)

**N1 (P1): Ruling 62's retry consumes a judged line-up from the 8 budget, but the ruling says the retry happens "before any swap is spent" — the code's `total` accounting is correct, yet the retry's `continue` skips the `weak`-swap accounting for that iteration, and `swapped = segs[:-1]` is set without going through `swap_lineup`.** I can verify from the diff (lines 391–397) that `swapped` is assigned directly and the loop continues; whether `swap_lineup`'s accounting (e.g. `n_lineup`, spend) is duplicated elsewhere in the loop, I cannot see — the loop body between the `continue` and the swap path is not fully shown. **Condition: confirm the ruling-62/63 `continue` paths don't skip spend accounting that the swap path performs.** Nobody caught this in Cycle 1 — GLM hedged at it ("I cannot see `lineup_for`") but nobody pinned the `swapped = segs[:-1]` / `swapped = order` assignments bypassing `swap_lineup`.

**N2 (P2): `allot()` compares dicts by identity/equality in `out["angle_allotment"]["dropped"] = [a["angle"] for a in got if a not in angles]`.** `a not in angles` uses `==` on dicts; if two angles from the writer are *equal dicts* (same hook, same angle text) but one was kept and one dropped, the list comprehension yields both or neither incorrectly. Concrete: `got = [A, A']` where `A == A'` (same hook, same sentence), `per=1` → `angles = [A]`, and `a not in angles` is False for both, so `dropped` records nothing even though one angle was dropped. **Nobody caught this.** It's cosmetic (the record, not the package), so P2.

**N2b (P2): the follow-up's `per` is `max(1, k2 // len(missing))` but the follow-up's `k=k2` — if the writer returns more than `per` angles for one hook, `allot(..., max(1, N2b))` trims to `per`, but the *first* call's `per` was `max(1, max_angles // len(offered))`. If `len(offered) == 1`, `per = 3` for the first call but the follow-up's `per` could be 1.** I can't verify the interaction without `check_angles`'s contract (does it enforce `per` or only `k`?). **Condition, not a finding.** Nobody caught this either; it's a hedge.

**N3 (P2): `hook_ratings()`'s cached-record recompute (diff lines 54–56) requires `all(isinstance(rec.get(k), int) for k in HOOK_PARTS)` — but `isinstance(True, int)` is True, so a cached record whose parts are booleans passes the guard and `min(rec[k] for k in HOOK_OWN)` yields a bool, which then... `min` of bools is a bool, and `can_open`'s `own["rating"] >= HOOK_MIN` compares bool to int, which works (True == 1 < 4).** So a cached record with `scroll: True` would rate 1, fail the bar, fail closed — safe but silently. Note the *new* `hook_own()` (line 104) *does* exclude bools (`not isinstance(x, bool)`), so the two guards are inconsistent: the cache-read path admits bools, the moment-read path doesn't. **Nobody caught this.** P2: a cached record with bool parts gets rating 1 instead of being re-asked — a silent, conservative divergence, not a crash.

**N4 (P2): `reorder()`'s `judged` membership test uses the id tuple of the *whole* line-up including the hook — `ids = tuple(m["moment_id"] for m in permutations...)` — but `judged` is keyed by the id tuple of `segs` (line 369: `key = tuple(m["moment_id"] for m in segs)`).** Both are hook-first id tuples of the full line-up, so they agree. But `reorder()`'s `judged` parameter is the *same* dict whose keys are the judged tuples — and `reorder` is called *before* the current line-up's verdict is stored? No: the verdict is stored at line 376 (`judged[key] = (ok_m, med)`) before the failure handling at 391–405, so the current line-up IS in `judged` when `reorder` runs, which is correct (the current order is excluded). **Verified, not a finding.** But note: `reorder()`'s `judged` check happens *before* `lineup_ok`, so a judged-but-failed order is skipped — correct per K3.

**N5 (P2): the `spins > 4 * lineups` guard (line 364) — `lineups` is not defined in the diff.** It's presumably the ruling-41 budget (8), so the guard is 32 iterations. I cannot see where `lineups` is bound; if it's the *remaining* budget rather than the constant, the guard's meaning changes. **Condition: confirm `lineups` is the constant 8, not a decrementing counter.** Nobody caught this.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| Ruling 61 (hook rated once) | 8/10 | 9/10 | The consensus closed my hedges (unrated-hook crash, other callers); the bool/int guard inconsistency (N3) is the only residue, and it's conservative. |
| Ruling 62 (last clip) | 7/10 | 8/10 | The count-vs-floor subtlety resolved; the `swapped = segs[:-1]` bypassing `swap_lineup` (N1) remains unverifiable from the diff. |
| Ruling 63 (reorder) | 8/10 | 9/10 | Termination, hook-fixed, judged-exclusion, placement all verified; itertools import confirmed present. |
| Ruling 64 (follow-up) | 7/10 | 7.5/10 | The `allot` dict-equality record (N2) is cosmetic; the follow-up's error handling is genuinely fail-safe (try/except, never the build). |
| Budget/termination | 8/10 | 8/5→8/10 | The `spins > 4 * lineups` guard exists; `lineups`' binding is outside the diff (N5). |
| Tests | 8/10 | 8/10 | 119 OK; the rewritten verdict tests are thorough; the ruling-62/63/64 tests exercise the real paths. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** none. Every Cycle-1 P0 was refuted with evidence (R1, R2); I concur.

**P1 HIGH:**
1. **N1** — `pipeline/package.py` (diff lines 391–397, 400–405): the ruling-62/63 `continue` paths set `swapped = segs[:-1]` / `swapped = order` directly, bypassing `swap_lineup`; confirm no spend/accounting that the swap path performs is skipped. *Condition: verify against the unseen loop body.*
2. **GLM P1-1** — `pipeline/package.py:147` (`coherence(..., hook=None)` default): grep for callers outside the diff; any old positional caller now fails closed. *Condition: grep before merge.*

**P2 MEDIUM:**
3. **N3** — `pipeline/package.py` (diff lines 54–56 vs. 104): the cache-read guard admits bools (`isinstance(rec.get(k), int)`), `hook_own()` excludes them (`not isinstance(x, bool)`); a cached record with bool parts silently rates 1 instead of being re-asked. Conservative, but the two guards should agree.
4. **N2** — `pipeline/package.py` (diff line 316): `out["angle_allotment"]["dropped"]` uses `a not in angles` (dict `==`); equal dicts deduplicate the record. Cosmetic.
5. **N5** — `pipeline/package.py` (diff line 364): `spins > 4 * lineups` — confirm `lineups` is the constant 8, not a decrementing remainder.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**Verify (by reading the unseen loop body around diff lines 386–420) that the ruling-62/63 `continue` paths — which set `swapped` directly and skip the `weak`-swap accounting — perform every bookkeeping step the `swap_lineup` path performs, because that's the only place where the new search logic can silently diverge from the old search's invariants, and it's the one thing the diff alone cannot prove.**

## 7. PRODUCTION READY?

**Yes with conditions.** Conditions, precisely:

1. **Grep for callers of `coherence(` outside the diff** (GLM P1-1 / Grok P1): any caller not passing `hook=` now fails closed by design; confirm none exists or that failing closed is acceptable there.
2. **Read the loop body around diff lines 386–420** and confirm the ruling-62/63 `continue` paths (which assign `swapped` directly) don't skip spend/`n_lineup`/rec bookkeeping that the `swap_lineup` path performs (N1).
3. **Confirm `lineups` in `spins > 4 * lineups` (diff line 364) is the constant 8**, so the guard is 32 iterations, not a shrinking remainder (N5).
4. (Optional, P2) Align the bool-handling of the cache-read guard (diff lines 54–56) with `hook_own()`'s (line 104) — either both admit bools or neither.

No P0. The consensus refutations (R1–R5) hold on the evidence given; the diff implements rulings 61–64 faithfully, the fail-closed paths are correct, the search terminates by construction (judged-memo + the 4× guard), and the tests exercise the real paths. Ship it once the three conditions above are checked — they're all read-and-confirm, no code changes required.