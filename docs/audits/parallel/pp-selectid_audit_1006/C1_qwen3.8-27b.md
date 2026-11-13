# qwen3.8-27b (qwen/qwen3.8-27b) 59 s finish=stop usage in 8438 / out 1807 usd~0.052 (upper-bound price)

# Audit: pp-selectid-1006 (Ruling 57 Freshness Preference)

## P0 Findings
None.

## P1 Findings

**1. `fresh_key` treats "no readable time" as the oldest, which can invert the "newest clips" tie-breaker**
`pipeline/package.py:41-43` (in `fresh_key`)

```python
oldest = max(known, default=0.0) + 1.0
return (any(a is not None and a <= FRESH_H for a in ages),
        -sum(a if a is not None else oldest for a in ages) / max(1, len(ages)))
```

Scenario: Two line-ups both have `fresh == False` (no clip ≤ 24 h).
- Line-up A: clips aged 100 h, 100 h, 100 h. Mean = 100. Key = -100.
- Line-up B: clips aged 100 h, 100 h, `None` (no publish time). `oldest` = 101. Sum = 100+100+101 = 301. Mean = 100.33. Key = -100.33.

Since the key is compared with `>` (higher is better), -100 > -100.33, so Line-up A wins. This is correct *if* "no time" should be treated as oldest. However, the docstring says "counts as the oldest," but the implementation uses `max(known) + 1.0`, which is only *slightly* older than the oldest known clip. If a line-up has *only* clips with no readable time, `known` is empty, `oldest` = 1.0, and the mean is 1.0, making it appear *newer* than a line-up with clips aged 50 h. This is a bug: a line-up with entirely unknown publish times will rank as "newer" than one with known old clips.

**Concrete scenario:**
- Line-up X: 3 clips, all `published_at=None`. `known=[]`, `oldest=1.0`, mean=1.0, key=-1.0.
- Line-up Y: 3 clips, all aged 50 h. `known=[50,50,50]`, `oldest=51`, mean=50, key=-50.0.
- -1.0 > -50.0, so Line-up X (all unknown) is preferred over Line-up Y (all 50 h old). This contradicts the intent that unknown time = oldest.

**Fix:** When `known` is empty, the mean should be a large sentinel (e.g., `float('inf')` or a very large number) so the key is very negative, ensuring it ranks last.

## P2 Findings

**2. Extra `lineup_for` call per angle in `build()` adds latency**
`pipeline/package.py:1528-1529`

```python
def first_fresh(a):
    segs = lineup_for(a, cleared, need_onset=True, need_stand_alone=True, now=ctx.now)
    return bool(segs) and fresh_key(segs, ctx.now)[0]
```

This calls `lineup_for` for every angle *before* the main loop, then the main loop calls `lineup_for` again for the same angle. For 3 angles, this doubles the `lineup_for` invocations. `lineup_for` is O(n²) in the number of moments (it iterates over all permutations of hook + clips). With ~24 moments, this is non-trivial. The result of the first call is discarded (only `bool(segs)` and `fresh_key` are used). Consider caching the result or computing freshness from the angle's moments directly without a full `lineup_for` call.

**3. `fresh_key` is called on `[h] + order` in `lineup_for`, but the hook is included in the mean age**
`pipeline/package.py:57-58`

```python
f = fresh_key([h] + order, now)
key = (f[0], f[1], key[0], key[1])
```

The docstring for `fresh_key` says "the mean age in hours" of the line-up's segments. The hook is included. This matches K2 ("the hook included"), so this is consistent with the stated reading. However, if the hook is a very old clip (e.g., 70 h) and the two clips are fresh (5 h, 10 h), the mean is (70+5+10)/3 = 28.3 h, which is > 24 h, so `fresh` is still `True` (because `any` is used for the first element). This is correct per the ruling ("at least one clip from the last 24 h"). No issue, but worth noting that the hook's age dilutes the "newest" ranking.

**4. Test coverage gap: no test for the "all unknown publish times" case**
`tests/package/test_medley.py:120`

```python
self.assertFalse(PK.fresh_key([dict(ms[0], published_at=None)], NOW)[0])
```

This tests that a single clip with no time is not fresh, but does not test the *ranking* behavior when all clips have no time (the P1 bug above). A test should verify that a line-up with all-unknown times ranks below a line-up with known old times.

**5. `pool_fill` passes `now` through, but the test for `pool_fill` with `now` is not shown**
`pipeline/package.py:27-28`

The diff shows `pool_fill` passing `now` to `lineup_for`, but the test file only shows tests for `lineup_for` and `build()`. There is no explicit test that `pool_fill` with `now` produces a fresh-first line-up. This is a minor coverage gap.

## Verification of Stated Readings

- **K1:** Correct. The build stops at the first passing package, so the preference is applied to the *order of trying*. The diff confirms this: `lineup_for` returns the best line-up under the new key, and `build()` re-orders angles by freshness before the main loop.
- **K2:** Correct. `fresh_key` includes the hook in the mean age calculation.
- **K3:** Correct. The key is `(fresh, newest, proposer_earliest, seconds_nearest_middle)`, so recency ranks above the proposer's earliest-moment preference. The play order is preserved (the clips are still in the proposer's order; only the *selection* of which line-up to pick is affected).

## Verification of Specific Checks

- **No line-up rule changed:** Correct. The diff only adds a new key component; all existing rules (onset, stand-alone, one clip per channel, price prediction limit) are unchanged.
- **Time-sensitive moments not affected:** Correct. `TIME_SENSITIVE_H` is unchanged, and `usable()` is not modified. The freshness preference is orthogonal to time-sensitivity.
- **Angle re-order is stable and only by freshness:** Correct. `sorted(angles, key=lambda a: not first_fresh(a))` is a stable sort, and the key is only `True`/`False` based on freshness. Within each group, the writer's order is preserved.
- **Cost of extra `lineup_for` call:** See P2 #2.
- **No-time cases:** See P1 #1.

## SHIP: no

**Conditions for ship:**
1. Fix the P1 bug: when `known` is empty in `fresh_key`, the mean should be a large sentinel so the line-up ranks last, not first.
2. Add a test for the "all unknown publish times" case to verify the ranking.
3. Consider caching the `lineup_for` result in `build()` to avoid the double call (P2 #2).