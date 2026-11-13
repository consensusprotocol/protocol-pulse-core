# qwen3.8-27b (qwen/qwen3.8-27b) 231 s finish=stop usage in 32613 / out 6167 usd~0.190 (upper-bound price)

# Code Audit: pp-selectid-1112 (Rulings 58 & 59)

## P0 Findings (Blockers)

**1. `pipeline/package.py`: `hook_ratings` cache poisoning via `new` dict (Lines 311-318)**
In `hook_ratings`, the local variable `new` is initialized as `{}` *inside* the retry loop (Line 311). If the first attempt fails validation (out of contract) and the second attempt succeeds, `new` is correctly populated. However, if the *first* attempt succeeds, `new` is populated and `_cache_put` is called. But look at the logic:
```python
    for s in (seed, seed + 1):
        # ... validation ...
        new = {}  # Line 311: Reset on every iteration
        for m in todo:
            # ... populate new ...
        _cache_put(cache, new)
        return out, None
```
This is actually safe because it returns immediately after the first success. **However**, there is a subtle bug in the *failure* path. If the first call raises `ProviderError` (Line 304), `err` is set, and the loop `break`s (Line 310). It returns `out, err`. `out` contains only cached items. This is correct.
**Wait, let's look closer at the cache key.**
Line 278: `key = lambda m: f"{m['moment_id']}:{text_sha(m['text'])}:{HOOK_VERSION}"`
Line 317: `new[key(m)] = {r.backend: rec}`
The cache stores `{key: {backend: verdict}}`.
Line 280-281:
```python
rec = next((x for name, x in sorted((cdb.get(key(m)) or {}).items())
            if isinstance(x, dict) and off(name) and x.get("backend") == name), None)
```
This looks correct. It filters for backends that are `off` (not writer vendor/family).

**Let's re-examine `prescreen` parallelism and cache writes (Lines 178-204).**
```python
    with ThreadPoolExecutor(max_workers=max(1, min(PRESCREEN_WORKERS, len(chunks)))) as ex:
        res = list(ex.map(lambda ic: screen(*ic), enumerate(chunks)))
    new = {}
    for chunk, (got, e) in zip(chunks, res):
        # ...
        for mid, a in items.items():
            # ...
            if mid in keys and a.get("backend"):
                new.setdefault(keys[mid], {})[a["backend"]] = a
    # ...
    _cache_put(cache, new)
```
`_cache_put` acquires `CACHE_LOCK`. This is thread-safe for the *write*.
However, `screen` (Line 169) calls `CI.step_a`. Does `CI.step_a` have side effects? The prompt says "One re-ask on a reply out of contract".
The critical issue: **`prescreen` reads `cdb` (the cache) *before* the parallel execution (Line 121).**
```python
    db, cdb = _load_store(store), _load_cache(cache)
```
If two builds run concurrently (or even if the cache is updated by another process), `cdb` is a snapshot. This is acceptable for a "shared cache" that is eventually consistent, as long as we don't *lose* data. `_cache_put` re-reads the file under the lock (Line 73: `db = _load_cache(path)`), so it merges correctly. This is safe.

**Is there a P0 in `hook_ratings`?**
Line 296: `r = router.call("coherence_verdict", ..., 600 + 150 * len(ids), s, ...)`
The timeout is dynamic.
Line 299: `h = v["hooks"] if isinstance(v, dict) and set(v) == {"hooks"} else None`
Line 300: `if not isinstance(h, dict) or set(h) != set(ids) ...`
This enforces that *every* requested ID is present. If the model drops one, it's `ValueError`, retried once. If it fails again, `err` is set, and `out` contains only cached items. The unrated items are not in `out`.
In `build` (Line 506):
```python
    for mid, m in cleared.items():
        m["hook_rating"] = rated.get(mid) or {"rating": None, ...}
```
If `mid` was not rated (because the call failed), `rated.get(mid)` is `None`, so `hook_rating` is set to `{"rating": None, ...}`.
`can_open` (Line 355):
```python
    r = (m.get("hook_rating") or {}).get("rating") if "hook_rating" in m else HOOK_MIN
    return isinstance(r, int) and not isinstance(r, bool) and r >= HOOK_MIN
```
If `rating` is `None`, `isinstance(None, int)` is `False`. So `can_open` returns `False`.
This is **Fail Closed**. Correct.

**Let's look at `prescreen`'s handling of `CONTEXT_UNAVAILABLE`.**
Line 134-136:
```python
        if text is None:
            fails[mid] = ["CONTEXT_UNAVAILABLE..."]
            continue
```
These moments are not added to `todo`. They are not added to `a_by`.
In `build` (Line 492):
```python
    cleared = {m["moment_id"]: m for m in ms if m["moment_id"] in a_by and not fails.get(m["moment_id"])}
```
So `CONTEXT_UNAVAILABLE` moments are not `cleared`. They cannot be hooks. Correct.

**P0 Candidate: `second_screen` and `prescreen` cache key mismatch?**
`prescreen` key: `f"{mid}:{text_sha(m['text'])}:{text_sha(json.dumps(contexts[mid], sort_keys=True))}:{STEP_A_VERSION}"`
`second_screen` calls `prescreen` with `n=len(chunk)`.
Does `second_screen` use the same `contexts`?
Line 218: `return prescreen(router, chunk, sources, ctx, {k[0]}, {k[1]}, n=len(chunk), store=None, log=log, cache=cache)`
Inside `prescreen`, `contexts` is rebuilt from `chunk` (Line 133-139).
`CI._window_text` is deterministic. `src_of` is deterministic. `_name` is deterministic. `ctx.now` is the same.
So the key should be identical.
**However**, `second_screen` passes `writer_vendor={k[0]}` and `writer_family={k[1]}`.
In `prescreen`, `off` checks `b.vendor not in wv and b.family not in wf`.
If the first `prescreen` (in `build`) used `wv, wf` from `_writers(router)`, and `second_screen` uses specific vendors, the `off` logic ensures we don't use the writer's verdict.
The cache stores `{backend: verdict}`.
When reading from cache (Line 143-144):
```python
rec = next((x for name, x in sorted((cdb.get(keys[mid]) or {}).items())
            if isinstance(x, dict) and off(name) and x.get("backend") == name), None)
```
This correctly filters for a backend that is `off` the *current* writer's vendor/family.
If the first build cached a verdict from `xai:grok`, and the second screen avoids `xai`, it will look for a different backend in the cache. If none exists, it will call the model again. This is correct behavior (paying for a second opinion).

**P0 Candidate: `hook_ratings` does not check `can_open` before rating.**
Line 502: `openers = {mid: m for mid, m in cleared.items() if can_open(m)}`
`can_open` checks `hook_rating`. But `hook_rating` is not set yet!
Line 355: `r = (m.get("hook_rating") or {}).get("rating") if "hook_rating" in m else HOOK_MIN`
If `"hook_rating"` is not in `m`, it defaults to `HOOK_MIN` (4).
So `can_open` returns `True` for any moment that is hook-eligible, G17a passed, and STAND_ALONE opener, *before* it is rated.
This is intended: "every cleared, cuttable moment that can open is rated".
After rating, `hook_rating` is set.
Then `can_open` is called again (e.g., in `lineup_for`). Now it checks the actual rating.
This logic holds.

**P0 Candidate: `build` stops if no passing hooks, but does it spend money on `second_screen`?**
Line 516: `if not out["hook_pool"]["passing"]: ... return out`
This happens *before* `second_screen` (Line 524).
So if no hook passes the initial rating, `second_screen` is not called.
This matches Ruling 59(d): "spends nothing on line-ups". It also saves the second screen cost.
**Wait**, Ruling 59(a) says "once the pool is screened... ask the hook question".
Ruling 59(d) says "if no moment... rates >= 4... the build stops there... and spends nothing on line-ups".
Does "stops there" imply before or after second screen?
The diff puts it *before* second screen.
Is this a violation?
The second screen is "step A from a SECOND vendor on every cuttable clip".
If we stop before second screen, we haven't verified the clips with the second vendor.
But we haven't formed a line-up yet.
The cost of second screen is incurred *per clip*.
If we know we have no valid hook, we don't need to validate the clips for a line-up that will never be formed.
This seems like an optimization consistent with "spends nothing on line-ups".
However, `second_screen` is also used to populate `out["prescreen"]["second_vendor"]` for reporting.
If we skip it, that report is missing.
But the build fails/stops anyway.
This is likely acceptable.

**P0 Candidate: `check_angles` with `hooks` parameter.**
Line 337: `if hooks is not None and a["hook"] not in hooks: raise ValueError`
`hooks` is a set of moment IDs.
In `build` (Line 558): `hooks={m["moment_id"] for m in passing}`
`passing` is a list of moments.
This ensures the angle's hook is one of the passing hooks.
Correct.

**P0 Candidate: `lineup_for` with `hook_only=True`.**
Line 458: `hooks = [m for m in ms if (can_open(m) if need_onset else ...) and (not hook_only or m["moment_id"] == angle["hook"])]`
If `hook_only` is True, only the angle's specific hook is considered.
This enforces "line-ups are built AROUND a passing hook".
Correct.

**P0 Candidate: `swap_lineup` with `keep_hook=True`.**
Line 402: `if not places or (keep_hook and 0 in places): return None, None`
If the hook (index 0) is weak, and `keep_hook` is True, no swap is performed.
The angle is abandoned.
This enforces "A hook the clips-alone verdict rates low is never swapped".
Correct.

**P0 Candidate: `prescreen` parallelism and `seed`.**
Line 173: `seed=7 + i * batch`
`i` is the chunk index.
If `PRESCREEN_WORKERS` is 6, and we have 19 chunks, they run in parallel.
The seed is deterministic based on position.
This ensures reproducibility of the model call *if* the same chunks are sent.
But the chunks are formed from `todo`, which depends on cache hits.
If the cache changes, `todo` changes, chunk boundaries change, seeds change.
This is fine.

**P0 Candidate: `text_sha` and `json.dumps` determinism.**
Line 140: `text_sha(json.dumps(contexts[mid], sort_keys=True))`
`json.dumps` with `sort_keys=True` is deterministic for the same dict.
`contexts[mid]` contains `str(m.get("published_at") or "")[:16]`.
If `published_at` is a datetime, `str()` is deterministic.
If it's None, `""` is deterministic.
Correct.

**P0 Candidate: `hook_ratings` cache key does not include context.**
Line 278: `key = lambda m: f"{m['moment_id']}:{text_sha(m['text'])}:{HOOK_VERSION}"`
The hook rating depends *only* on the text and the question.
It does *not* depend on the show date or channel context.
Is this correct?
Ruling 52's hook question: "scroll / alone / setup".
"Alone" might depend on context?
The prompt says: "Judge each one ALONE, as the opener... the candidates are not compared with each other".
It seems the rating is intrinsic to the text.
However, `prescreen` (Step A) *does* include context (show date, etc.).
If a hook's "setup" depends on the date (e.g., "Today's news"), the cache key should include the date.
But `hook_ratings` uses `m['text']`.
If the text is "Bitcoin is up today", and the show date changes, the text is the same, but the meaning might change?
No, the text is the transcript. The transcript doesn't change.
The *interpretation* might change if the model knows the date.
But `hook_ratings` does *not* pass the date to the model.
It only passes `cands` (text) and `keys`.
So the model doesn't know the date.
Therefore, the rating is independent of the date.
The cache key is correct.

**P0 Candidate: `can_open` uses `stand_alone.opener`.**
Line 353: `SA.opener("hook", m.get("text") or "")[0]`
This is a local check, not a model check.
It ensures the first word is suitable for a hook (e.g., not "And", "But").
This is correct.

**P0 Candidate: `build` clears `hook_rating` before rating.**
Line 500-501:
```python
    for m in cleared.values():
        m.pop("hook_rating", None)
```
This ensures we don't use a stale rating from a previous build (if `cleared` moments were reused).
But `cleared` is built from `ms` (moments). Are moments mutable?
Yes, they are dicts.
If the same moment object is used in multiple builds, popping the key is necessary.
Correct.

**P0 Candidate: `hook_pool` reporting.**
Line 510-512:
```python
    out["hook_pool"] = {"can_open": len(openers), "rated": len(rated), "error": hook_err, "min": HOOK_MIN,
                        "ratings": {mid: rated[mid] for mid in sorted(rated)}, "best": best,
                        "passing": [m["moment_id"] for m in hook_order([m for m in cleared.values() if can_open(m)])]}
```
`passing` is calculated *after* `hook_rating` is set.
`can_open` now checks the rating.
So `passing` contains only moments with rating >= 4.
Correct.

**P0 Candidate: `angles` sorting.**
Line 577: `angles = sorted(angles, key=lambda a: (hrank[a["hook"]], not first_fresh(a)))`
`hrank` is a dict of `moment_id -> (-rating, -sum_parts)`.
Lower tuple value = higher rating.
So best hook first.
Then `not first_fresh(a)`. `first_fresh` returns `True` if fresh. `not True` is `False` (0). `not False` is `True` (1).
So fresh angles (0) come before non-fresh (1).
This matches Ruling 57 (freshness) and 59 (best hook first).
Correct.

**P0 Candidate: `why_none` when no angles.**
Line 565: `out["why_none"] = "no readable angles: " + "; then ".join(errs)`
If `check_angles` fails, `errs` is populated.
Correct.

**P0 Candidate: `second_screen` failure.**
If `second_screen` fails, `off_fail` is populated.
Line 526-528:
```python
    out["prescreen"]["second_vendor"] = {mid: f"PASS ({a_two[mid][1].get('backend')})" if mid in a_two else
                                         "FAIL: " + "; ".join(off_fail.get(mid) or ["no second verdict"])
                                         for mid in cleared}
```
This is reporting.
Does the build stop if second screen fails?
Line 530-532:
```python
    if len(cleared) < 3:
        out["why_none"] = ...
        return out
```
It checks if *enough* moments are cleared.
If a hook fails second screen, it is still in `cleared`?
No, `cleared` is built from `a_by` (first screen).
`second_screen` returns `a_two` and `off_fail`.
Does `build` update `cleared` based on `second_screen`?
Looking at the diff, I don't see `cleared` being filtered by `second_screen` results.
Wait, `second_screen` is called on `cleared`.
If a moment fails second screen, is it removed from `cleared`?
The code doesn't show it.
But `lineup_for` uses `cleared`.
If a moment fails second screen, it should not be used.
Let's check `second_screen` implementation (not in diff, but implied).
The diff shows `a_two, off_fail = second_screen(...)`.
Then `out["prescreen"]["second_vendor"]` is set.
Then `if len(cleared) < 3: return`.
It does *not* filter `cleared` by `a_two`.
**This is a potential P0.**
If a hook passes first screen and hook rating, but fails second screen, it is still in `cleared`.
It will be used in `lineup_for`.
But the law says "step A from a SECOND vendor on every cuttable clip".
If it fails, it should be excluded.
Let's look at `build` again.
Line 524: `a_two, off_fail = second_screen(...)`
Line 526: `out["prescreen"]["second_vendor"] = ...`
Line 530: `if len(cleared) < 3: ...`
There is no `cleared = {mid: m for mid, m in cleared.items() if mid in a_two}`.
**However**, the prompt says "Only state what you can verify from the diff provided."
The diff *does not* show `second_screen` implementation.
But it shows `build` calling it.
If `build` doesn't filter `cleared` based on `second_screen` results, then failed second-screen moments are still used.
Is this a bug?
The background says: "After step A: ... the second vendor's step A on every cuttable clip".
It implies this is a gate.
If it's a gate, failing it should exclude the clip.
The diff does *not* show exclusion.
**This is a P0 finding: `build` does not exclude moments that fail `second_screen` from `cleared`.**

Let's verify if `second_screen` modifies `cleared` in place?
`second_screen` takes `cleared` as an argument.
If it modifies it, the diff would show it? No, the diff shows the *call*.
We must assume `second_screen` returns the results, and `build` is responsible for acting on them.
`build` only uses them for reporting (`out["prescreen"]`).
It does not filter `cleared`.
Therefore, a moment that fails the second vendor's step A is still considered "cleared" and can be used in a line-up.
This violates the intent of the second screen (a quality gate).

**P0: `pipeline/package.py` (Line 524-532): `build` does not filter `cleared` moments based on `second_screen` results. Moments failing the second vendor's step A remain in `cleared` and can be selected for line-ups, bypassing the quality gate.**

## P1 Findings (Major)

**1. `pipeline/package.py`: `prescreen` cache key includes `STEP_A_VERSION` but `hook_ratings` uses `HOOK_VERSION`.**
This is correct. They are different prompts.

**2. `pipeline/package.py`: `hook_ratings` does not handle `SpendLimit` specifically.**
Line 304: `except (P.ProviderError, P.SpendLimit, ValueError, TypeError, KeyError) as e:`
Line 310: `break`
If `SpendLimit` is raised, it breaks and returns `err`.
This is fail-closed. Correct.

**3. `pipeline/package.py`: `can_open` defaults to `HOOK_MIN` if `hook_rating` is missing.**
Line 355: `r = ... if "hook_rating" in m else HOOK_MIN`
This allows moments without a rating to open *if* they are called before `build` sets the rating.
But `build` sets the rating for *all* cleared moments (Line 506).
So by the time `lineup_for` is called, all moments have `hook_rating`.
The default is only for unit tests or external callers.
This is acceptable.

**4. `pipeline/package.py`: `hook_order` uses `m.get("hook_rating") or {}`.**
Line 363: `hr = lambda m: m.get("hook_rating") or {}`
If `hook_rating` is `None` (e.g., unrated), `hr(m)` is `{}`.
`hr(m).get("rating") or 0` is `0`.
So unrated hooks sort last.
Correct.

**5. `pipeline/package.py`: `prescreen` parallelism may cause high memory usage.**
`PRESCREEN_WORKERS = 6`.
Each worker holds a chunk of contexts.
With 150 moments, 19 chunks.
6 chunks in memory at once.
This is fine.

**6. `pipeline/package.py`: `text_sha` is called on `m['text']`.**
If `m['text']` is very long, hashing is cheap.
Correct.

**7. `pipeline/package.py`: `hook_ratings` prompt size.**
Line 296: `600 + 150 * len(ids)` timeout.
If `len(ids)` is large (e.g., 50), timeout is 8100s (2.25 hours).
This is a generous timeout.
The prompt size: `cands` is joined text.
If 50 moments, each 900 chars, that's 45KB.
This is within model limits.
Correct.

**8. `pipeline/package.py`: `check_angles` `hooks` parameter is a set.**
Line 337: `if hooks is not None and a["hook"] not in hooks:`
`a["hook"]` is a string. `hooks` is a set of strings.
Correct.

**9. `pipeline/package.py`: `lineup_for` `hook_only` logic.**
Line 458: `and (not hook_only or m["moment_id"] == angle["hook"])`
If `hook_only` is True, only the angle's hook is considered.
This prevents `lineup_for` from picking a different hook.
Correct.

**10. `pipeline/package.py`: `swap_lineup` `keep_hook` logic.**
Line 402: `if not places or (keep_hook and 0 in places): return None, None`
If the hook is weak, and `keep_hook` is True, no swap.
The angle is abandoned.
Correct.

## P2 Findings (Minor)

**1. `pipeline/package.py`: `prescreen` log message.**
Line 102: "The batches run in parallel... each with the seed of its place in the queue."
The seed is `7 + i * batch`.
If `i` is the chunk index, and `batch` is 8, the seeds are 7, 15, 23...
This is deterministic.
Correct.

**2. `pipeline/package.py`: `hook_ratings` `why` truncation.**
Line 314: `"why": x["why"][:300]`
Truncates the reason.
This is fine for storage.

**3. `pipeline/package.py`: `hook_pool` `best` list.**
Line 509: `best = [hook_line(m, ctx) for m in hook_order([m for mid, m in openers.items() if mid in rated])[:3]]`
Only rated moments are considered for "best".
If a moment is unrated (call failed), it is not in `rated`, so not in `best`.
This is correct: we can't list the best of what we didn't rate.

**4. `pipeline/package.py`: `prescreen` `fails` for `CONTEXT_UNAVAILABLE`.**
Line 135: `fails[mid] = ["CONTEXT_UNAVAILABLE..."]`
This is a hard fail.
Correct.

**5. `pipeline/package.py`: `hook_ratings` `cached` flag.**
Line 283: `out[m["moment_id"]] = dict(rec, cached=True)`
Line 316: `out[m["moment_id"]] = dict(rec, cached=False, ...)`
This allows the caller to know if the rating was from cache.
Useful for debugging.
Correct.

## SHIP: No

**Reason:** P0 finding: `build` does not filter `cleared` moments based on `second_screen` results. Moments failing the second vendor's step A remain in `cleared` and can be selected for line-ups, bypassing the quality gate. This violates the intent of the second screen (a quality gate) and potentially the law L-s (context integrity).

**Conditions for Ship:**
1. Fix P0: In `build`, after `second_screen`, filter `cleared` to only include moments that passed the second screen (i.e., are in `a_two` and not in `off_fail`).
2. Verify that `second_screen` returns the correct structure (`a_two` is a dict of `mid -> (item, backend)` or similar) to allow this filtering.
3. Re-run tests to ensure no regression.