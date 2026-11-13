# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-1112
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 725 s finish=length usage in 29895 / out 24000 usd~0.450 (upper-bound price)

# Audit: pp-selectid — rulings 58 / 59 (prescreen-every + hook-first)

Scope note: I reviewed only the diff provided. `context_integrity.py`, `providers.py`, `stand_alone.py`, `edl_rules.py`, `Canned`, `a_item`, `pm`, `angle()`, `E.Context` are referenced but not shown; where their behavior matters I say so.

---

## P0 findings

None found. I could not construct a scenario from the diff alone where an unrated or low-rated moment opens a line-up, or where a failed call produces a pass.

---

## P1 findings

**P1-1. `prescreen` writes the build ledger even when nothing was screened, and the condition changed silently — package.py:199 (`if store and (todo or db):`)**
Old code: `if store and todo:`. New: `if store and (todo or db)`. When every moment is served from the shared cache (`todo == []`), the build now rewrites its own ledger file (with the cached records copied into it, line 148). That is presumably intended ("this build's ledger still records them", test line 817), but it means the ledger now contains verdicts whose provenance is the shared cache, not this build's calls. If any downstream consumer treats the ledger as "what this build paid for", it now over-counts. I cannot verify from the diff whether anything reads the ledger that way — flagging as a behavior-change question, not a proven defect.

**P1-2. `hook_ratings` cache read: `sorted((cdb.get(key(m)) or {}).items())` — package.py:280 (and the same pattern at 143)**
The sort is by back-end *name*, and the pick is the first entry whose `off(name)` holds and whose `x.get("backend") == name`. Two consequences:
- If the cache holds verdicts from several back-ends, the choice is deterministic but arbitrary (alphabetically first eligible), not "best" or "most recent". For step A this matches the old ledger behavior only if the ledger also held one record per key — it did (`db.get(f"{mid}:{STEP_A_VERSION}")`), so the *ledger* path is unchanged, but the *cache* path introduces a multi-vendor record shape the ledger never had. If `second_screen` (which calls `prescreen` with different writer-avoidance sets, line 218) writes a second vendor's verdict under the same key, a later build's *first* screen may now be served the second-screen vendor's verdict. That is still "off the writers' vendor" (the `off()` check), so it complies with L-s/L-x as stated — but it means the first screen and second screen may come from the same back-end in one build, which the order-06:22 item-45 test (line 980-988) suggests is prevented for `z` ("the SAME vendor" case). I cannot fully verify the interaction from the diff; the test at 980-988 fakes `prescreen` wholesale, so it does not exercise the cache. **Concrete scenario:** build 1: writers = {heimdall, deepseek}; first screen from `xai:grok`, second screen (avoiding heimdall/deepseek) also from `xai:grok` — both cached under the same key. Build 2, same writers: first screen served from cache (xai), second screen also finds only xai in the cache → both verdicts from one back-end. Whether that violates item 45 depends on `context_integrity`'s second_screen logic, which is not in the diff. **Recommend: verify or add a test.**
- `sorted()` on a dict of `{name: verdict}` where a value is not a dict is guarded by `isinstance(x, dict)` — OK.

**P1-3. `hook_ratings` reply contract requires `set(h) == set(ids)` — package.py:300**
The model must return exactly the asked ids. If the model returns one extra or one missing id, the *entire* batch is out of contract and, after one re-ask, nothing is rated (law L-m, correct), but the whole pool's hook ratings are lost for one stray id. With ~150 candidates... wait — actually `hook_ratings` is called on `openers` only, which is typically far smaller. Still, one malformed id kills all. This is arguably intended (fail closed, L-m), and the test at 897 covers it. Downgrade to P2 if the prompt's `keys` string makes exact-ids likely. I flag it because the re-ask (line 293, `for s in (seed, seed + 1)`) re-asks with the *same* prompt and only a different seed; a systematically-derailing model fails twice and the build stops with "no hook in the pool" — which is the correct fail-closed outcome, but note the error message at 517-519 will say "not rated: {hook_err}" only when `hook_err` is truthy, which it is here. OK.

**P1-4. `can_open` treats a *carried-in* `hook_rating` differently before and after build() — package.py:355**
`r = (m.get("hook_rating") or {}).get("rating") if "hook_rating" in m else HOOK_MIN`. If `m` has the key with value `None` (build() sets exactly that at 506 for non-openers... no wait, build() sets it on *cleared* moments; a moment that is not cleared never reaches `can_open` via build, but `lineup_ok`/`placement`/`swap_lineup` are also called on moments that went through build, so they have the key). The subtlety: `"hook_rating" in m` with value `None` → `r 

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 74 s finish=stop usage in 29294 / out 966 usd~0.171 (upper-bound price)

**P2: pipeline/package.py:49** (CACHE_LOCK = threading.Lock()): Protects only intra-process parallel batches in prescreen() and _cache_put(). As a threading lock + file-based read/merge/.tmp/os.replace, it cannot synchronize across separate Python processes sharing the same step_a_cache or hook_cache. If the orchestrator ever runs concurrent builds, lost updates are possible (both load same JSON, both write). Diff does not show orchestrator scheduling, so uncertain whether this is reachable; matches "parallel step-A batches" comment but not full shared-cache safety.

**P2: pipeline/package.py:278** (key = lambda m: f"{m['moment_id']}:{text_sha(m['text'])}:{HOOK_VERSION}"): Hook cache key omits context SHA (show_date, title, window) that step-A key includes (lines 140, 98-99). HOOKS_PROMPT uses only text + id, ruling 59 description does not mention context, and K1 explicitly notes context only for step A, so this matches the implemented rulings. Still, a date-sensitive hook judgment could reuse a cached verdict on new show_date.

**P2: pipeline/package.py:502-512 & 533-538** (hook_rating population, post-second-screen re-filter): build() clears any carried "hook_rating", rates only pre-second-screen openers, then sets rating=None + error why for any unrated/low-rated after second_screen. The "passing hooks still cleared after the second screen" comment and explicit re-computation of passing list + why_none path are present and fail-closed (no line-ups, no angle_write). Matches K2 exactly. No path lets an unrated/low-rated hook reach lineup_for/pool_fill/swap_lineup/lineup_ok/can_open (all updated, including keep_hook=True and hook_only=True).

**P2: pipeline/package.py:169-179** (ThreadPoolExecutor + enumerate(chunks)): Parallel batches preserve original per-chunk seed (7 + i * batch) and map order. Failed batch sets per-moment STEP_A_UNAVAILABLE with exception text, never caches (lines 182-184, 840-845 in test), never poisons other moments. _load_cache returns {} on corrupt file (line 64). Good fail-closed.

**P2: pipeline/package.py:296-310 & 897-903** (hook_ratings reply contract): Strict validation (exact ids, int 1-5 for each of scroll/alone/setup, why str, set equality), one re-ask on ValueError/TypeError/KeyError, ProviderError/SpendLimit = err + no verdict (law L-m / L-j). Derived min rating, cached only on success. Test coverage (test_a_reply_out_of_contract..., test_one_batched_call...) verifies.

**P2: pipeline/package.py:337, 558, 931** (check_angles hooks= param): Rejects angle whose "hook" not in supplied passing set → ValueError → re-ask on angle_write. Prompt now supplies THE HOOKS best-first with ratings/reasons and "up to {per} for EACH hook". Matches K3. No unintentional change to old callers (default=None, test preserves).

**P2: pipeline/package.py:382, 410, 423, 458, 506, 912** (can_open, placement, lineup_ok, lineup_for hook_only=True, swap_lineup keep_hook=True): All paths updated; unrated/low-rated hook cannot open (including no-hook early return before second_screen/angles/lineups, matching (d)). K5 default (HOOK_MIN when key absent) preserved for unit tests/old callers. Weak hook now ends angle with specific message (lines 610-612) instead of swap. Matches K4 and rewritten ruling-41 test.

**P2: tests/package/test_medley.py:686-698** (Rig.rate_hooks) and new TestRuling58/TestRuling59 suites: Rig fakes exactly the new contract (including hook_err path, cached flag, per-moment why). proof_ledger supplies caches. All 11 suites still pass per diff summary; no behavior change outside rulings 58/59 visible.

No P0/P1. Every fail-closed path (unrated hook, failed batch/call, corrupt cache, out-of-contract angle, no passing after second screen), cache vendor filtering, thread batching, angle contract, and "spends nothing on line-ups" when no hook are verifiable in the diff and match the stated rulings/K1-K6. No violation of listed governing laws detectable in changed selection paths (L-f, L-j, M12, LAW 20/22 appear untouched).

**SHIP: yes**

## QWEN3.8-27B — CYCLE 1 OUTPUT
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
`CI._window_text`

## CLAUDE'S CYCLE 1 CONSENSUS
# pp-selectid audit 1112 (RULINGS 58 + 59: every candidate at step A, cached; HOOK FIRST): cycle 1 consensus

**Run:**
- grok: "SHIP: yes", no P0 or P1.
- qwen: "SHIP: No", on one P0 (refuted below).
- glm: "None found" for P0. Its 39 numbered "P1" items mostly close themselves ("Good", "Correct", "consistent"). It
  stopped at its 24,000-token limit.

No P0 or P1 holds. Nothing changes in the code; cycle 2 reviews the same diff.

## REFUTED (with evidence)

| # | claim | the code |
|---|---|---|
| R1 | qwen P0: "build does not filter cleared moments based on second_screen results" | The filter is there, unchanged, just outside the diff's context. pipeline/package.py:1708 (the scratch copy; HEAD's line ~1514) reads `cleared = {mid: m for mid, m in cleared.items() if mid in a_two}`, right after the second screen's record. qwen's own text says the diff does not show it. Ruling 59's re-check of the passing hooks reads this filtered set. |
| R2 | glm P1-5: the router may not be thread-safe under parallel step-A batches | The router's spend ledger is reserved and settled under an fcntl file lock (pipeline/providers.py:536-541, `_lock`, used at 581 / 615 / 624 / 640). Replies are recorded at content-addressed paths (`_path`, 531-533). The build already called the router concurrently before this diff: L-v 2's 8 workers (package.py:1483) and the second screen's parallel groups (:476). |
| R3 | glm P1-8: the "no hook" early return leaves out["search"] unset, so a caller doing out["search"][...] raises | out["search"] is set only at the end of the line-up loop (package.py:1931 in HEAD). Every earlier return already leaves it unset: fewer than 3 channels, no work_dir, no readable angles. The driver (tests/package/proof_ledger.py) never reads "search". |
| R4 | glm P1-7: hook_ratings does not reject a reply on ProviderError / SpendLimit | `r = None` at the top of each attempt. Only `router.call` raises those, and when it raises no reply was returned, so `r` is still None and there is nothing to reject. A reply that arrives and fails the contract is rejected (ValueError / TypeError / KeyError). |

## Recorded (P2, no change)

| # | finding | why no change |
|---|---|---|
| G1 | grok: CACHE_LOCK is per process, so two builds at once could lose a cache update | Builds run one at a time. A lost update loses only a saving: the entry is asked again and paid for again. A cached entry is keyed by content, so it can never be the wrong verdict. |
| G2 | grok: the hook cache key has no show date | The hook question carries only the clip's words and its channel's name: no date, title or window (HOOKS_PROMPT). The judge never sees a date, so its rating cannot depend on one (qwen reached the same reading). |
| G3 | glm P1-36: the channel name shown to the hook judge is not in the hook cache key | A renamed channel would keep a rating made under its old name. The rating judges the words; recorded for the next change to the hook key. |
| G4 | glm P1-1: this build's ledger (

---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_1112/C2_STEP.diff (1017 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index a3bc8fc..3e07f37 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -6,8 +6,11 @@ usable()      moments a package may use: on screen eligible (word timing, law L-
   6 |                overlapping a moment delivered in the previous 24 h (novelty by video and time, L-p), channel not opted
   7 |                out, <= 20 s (L-u), a time-sensitive moment only from a source <= TIME_SENSITIVE_H old (L-v 3), no
   8 |                measured speaker change (L-v 1)
   9 | -prescreen()   step A of law L-s on each usable moment's own context, ONCE per moment (package-independent), stored on
  10 | -              the moment (`store`: a JSON ledger keyed by moment and the step-A prompt); never recomputed
  11 | +prescreen()   step A of law L-s on EVERY usable moment's own context (ruling 58), ONCE per moment (package-independent):
  12 | +              this build's ledger (`store`) and the step-A cache every build shares (`cache`: moment id + text sha +
  13 | +              context sha + the step-A prompt); never recomputed
  14 | +hook_ratings() RULING 59: the hook question of ruling 52 on every cleared, cuttable moment that can open, ONE batched
  15 | +              call, cached; only a hook rated >= HOOK_MIN opens, and the angles are written FOR the passing hooks
  16 |  ANGLES        role angle_write: up to MAX_ANGLES one-sentence angles, each backed by 3-8 cleared moments from >= 3
  17 |                channels (one clip per channel, L-u), listed in PLAY ORDER (L-y 3)
  18 |  lineup_for()  code: the hook + 2-4 clips for one angle in the proposer's play order, every segment from a different
  19 | @@ -49,6 +52,7 @@ import json
  20 |  import math
  21 |  import os
  22 |  import re
  23 | +import threading
  24 |  import time
  25 |  from concurrent.futures import ThreadPoolExecutor
  26 |  
  27 | @@ -64,13 +68,16 @@ R4_WPS, R4_PREROLL_S, R4_SHARE = 2.5, 1.0, 0.25      # edl_rules.rule_r4's own e
  28 |  TIME_SENSITIVE_H = 24.0            # L-v 3: 'today' / 'just' / a price level only from a source this fresh
  29 |  FRESH_H = 24.0                     # ruling 57 (09:59 Nov 13): a line-up with a clip this fresh is preferred
  30 |  UNKNOWN_AGE_H = 1.0e6              # ruling 57: a clip with no readable publish time counts as the oldest there is
  31 | -PRESCREEN_N = 24                   # moments whose own context is screened (step A) before any writing
  32 | +PRESCREEN_N = None                 # RULING 58 (11:00 Nov 13): EVERY candidate is screened at step A (was 24), the
  33 | +                                   # miner's best first; a number keeps the old cap (the re-screens pass their own)
  34 |  PRESCREEN_BATCH = 8                # excerpts per step-A call
  35 | +PRESCREEN_WORKERS = 6              # ruling 58: the step-A batches run in parallel (about 19 batches at 72 h)
  36 |  PRICE_PREDICTIONS_MAX = 1          # L-u: at most one per video
  37 |  SHORT_CLIP_S = 8.0                 # a clip under ~8 s is a penalty unless it is the angle's punchline (the last clip)
  38 |  MAX_ANGLES = 3                     # orchestrator 05:30: at most 3 angles x 2 writes
  39 |  WRITES = 2
  40 |  COHERENCE_MIN = 4                  # the blind coherence verdict: every rating >= 4 and a through-line, else next angle
  41 | +HOOK_MIN = COHERENCE_MIN           # RULING 59 (b): only a moment rated >= 4 on the hook's own job may open a line-up
  42 |  BUDGET_WALL_S = 900.0              # orchestrator 22:40 ruling 5 (Heimdall as the writer; was 05:25 item 5's 360 s x2):
  43 |  BUDGET_USD_REPORTED = 1.50         # per package 15 min wall and $1.50 by the vendors' OWN reported cost,
  44 |  BUDGET_USD_ESTIMATE = 5.00         # with the price-table estimate (it over-states ~7x) only as a hard ceiling
  45 | @@ -384,74 +391,127 @@ def _load_store(store):
  46 |          return json.load(f)
  47 |  
  48 |  
  49 | +CACHE_LOCK = threading.Lock()      # ruling 58 / 59: a cache file is merged under one lock (parallel step-A batches)
  50 | +
  51 | +
  52 | +def text_sha(text):
  53 | +    """The sha256 of a text's UTF-8 bytes (ruling 58: a cached verdict is for exactly this text)."""
  54 | +    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()
  55 | +
  56 | +
  57 | +def _load_cache(path):
  58 | +    """A verdict cache shared by every build (ruling 58 / 59): {key: {back-end: verdict}}. A missing or unreadable
  59 | +    file is an empty cache (the verdicts are asked again and paid for again, never invented)."""
  60 | +    try:
  61 | +        with open(path) as f:
  62 | +            d = json.load(f)
  63 | +        return d if isinstance(d, dict) else {}
  64 | +    except (OSError, ValueError, TypeError):
  65 | +        return {}
  66 | +
  67 | +
  68 | +def _cache_put(path, new):
  69 | +    """Merge {key: {back-end: verdict}} into the cache file (read again under the lock, .tmp then rename)."""
  70 | +    if not path or not new:
  71 | +        return
  72 | +    with CACHE_LOCK:
  73 | +        db = _load_cache(path)
  74 | +        for k, by_b in new.items():
  75 | +            db[k] = dict(db.get(k) if isinstance(db.get(k), dict) else {}, **by_b)
  76 | +        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
  77 | +        with open(path + ".tmp", "w") as f:
  78 | +            json.dump(db, f, indent=1)
  79 | +        os.replace(path + ".tmp", path)
  80 | +
  81 | +
  82 |  def src_of(x, sources):
  83 |      """A moment's (or a package segment's) own Source: context_integrity.source_for, the one lookup rule."""
  84 |      return CI.source_for(x, sources)
  85 |  
  86 |  
  87 |  def prescreen(router, ms, sources, ctx, writer_vendor, writer_family=None, n=PRESCREEN_N, batch=PRESCREEN_BATCH,
  88 | -              store=None, log=print):
  89 | -    """Step A (context only, package-independent by law L-s) on the best n usable moments, distinct channels first:
  90 | -    ({moment_id: A item}, {moment_id: [failing rules]}, {vendor}, {family}). Each moment is screened ONCE: a stored item
  91 | -    (same moment, same step-A prompt, a back-end off the writers' vendor and family) is reused, never recomputed.
  92 | -    writer_vendor / writer_family: of the writers, so step A never runs on them."""
  93 | +              store=None, log=print, cache=None):
  94 | +    """Step A (context only, package-independent by law L-s): ({moment_id: A item}, {moment_id: [failing rules]},
  95 | +    {vendor}, {family}). RULING 58 (11:00 Nov 13): n None (the default) screens EVERY usable moment, the miner's best
  96 | +    first (rank_score); a number keeps the old cap (distinct channels first). Each moment is paid for ONCE: a verdict
  97 | +    from a back-end off the writers' vendor and family is reused from this build's ledger (`store`), else from the
  98 | +    step-A cache every build shares (`cache`), keyed by the moment id, the sha256 of its text, the sha256 of the exact
  99 | +    context step A reads (its window, title, channel, publish time and the show date, so time words are judged again on
 100 | +    a new show date) and the step-A prompt's version. The batches run in parallel (PRESCREEN_WORKERS), each with the
 101 | +    seed of its place in the queue. Only a parsed verdict is stored: a call that fails is no verdict (law L-m), never
 102 | +    remembered. writer_vendor / writer_family: of the writers, so step A never runs on them."""
 103 |      import providers as P
 104 | -    seen, order = set(), []
 105 |      ranked = sorted(ms, key=lambda m: (-m["rank_score"], m["moment_id"]))
 106 | -    for m in ranked:
 107 | -        if m["channel_id"] not in seen:
 108 | -            order.append(m)
 109 | -            seen.add(m["channel_id"])
 110 | -    order = (order + [m for m in ranked if m not in order])[:n]
 111 | -    db = _load_store(store)
 112 | +    if n is None:
 113 | +        order = ranked                                   # ruling 58: every candidate, the miner's best first
 114 | +    else:
 115 | +        seen, order = set(), []
 116 | +        for m in ranked:
 117 | +            if m["channel_id"] not in seen:
 118 | +                order.append(m)
 119 | +                seen.add(m["channel_id"])
 120 | +        order = (order + [m for m in ranked if m not in order])[:n]
 121 | +    db, cdb = _load_store(store), _load_cache(cache)
 122 |      wv, wf = P._as_set(writer_vendor), P._as_set(writer_family)
 123 | -    a_by, fails, vendors, families, todo = {}, {}, set(), set(), []
 124 | +    off = lambda name: (lambda b: b is not None and b.vendor not in wv and b.family not in wf)(router.backends.get(name))
 125 | +    a_by, fails, vendors, families, todo, contexts, keys = {}, {}, set(), set(), [], {}, {}
 126 |      for m in order:
 127 | -        rec = db.get(f"{m['moment_id']}:{STEP_A_VERSION}")
 128 | -        b = router.backends.get((rec or {}).get("backend"))
 129 | -        if rec and b is not None and b.vendor not in wv and b.family not in wf:
 130 | -            a_by[m["moment_id"]] = rec
 131 | -            fails[m["moment_id"]] = CI.a_failures(rec)
 132 | +        mid = m["moment_id"]
 133 | +        text, win = CI._window_text(src_of(m, sources), m["sentences"][0], m["sentences"][1], *m["words"])
 134 | +        if text is None:            # no L-s context (a window record without its caption record, short coverage, an
 135 | +            fails[mid] = ["CONTEXT_UNAVAILABLE: no L-s context for this moment (law L-s)"]     # unclocked moment): THIS
 136 | +            continue                # moment is not cleared; it never poisons its batch's call
 137 | +        contexts[mid] = {"text": text, "title": src_of(m, sources).title or "", "channel": _name(m, ctx),
 138 | +                         "window": win, "published": str(m.get("published_at") or "")[:16],
 139 | +                         "show_date": ctx.now.strftime("%Y-%m-%d")}
 140 | +        keys[mid] = f"{mid}:{text_sha(m['text'])}:{text_sha(json.dumps(contexts[mid], sort_keys=True))}:{STEP_A_VERSION}"
 141 | +        rec = db.get(f"{mid}:{STEP_A_VERSION}")
 142 | +        if not (isinstance(rec, dict) and off(rec.get("backend"))):
 143 | +            rec = next((x for name, x in sorted((cdb.get(keys[mid]) or {}).items())
 144 | +                        if isinstance(x, dict) and off(name) and x.get("backend") == name), None)
 145 | +        if rec is not None:
 146 | +            b = router.backends[rec["backend"]]
 147 | +            a_by[mid], fails[mid] = rec, CI.a_failures(rec)
 148 | +            db[f"{mid}:{STEP_A_VERSION}"] = rec
 149 |              vendors.add(b.vendor)
 150 |              families.add(b.family)
 151 |          else:
 152 |              todo.append(m)
 153 | -    for i in range(0, len(todo), batch):
 154 | -        chunk = todo[i:i + batch]
 155 | -        contexts = {}
 156 | -        for m in chunk:
 157 | -            text, win = CI._window_text(src_of(m, sources), m["sentences"][0], m["sentences"][1], *m["words"])
 158 | -            if text is None:        # no L-s context (a window record without its caption record, short coverage, an
 159 | -                fails[m["moment_id"]] = ["CONTEXT_UNAVAILABLE: no L-s context for this moment (law L-s)"]   # unclocked
 160 | -                continue            # moment): THIS moment is not cleared; it never poisons its batch's call
 161 | -            contexts[m["moment_id"]] = {"text": text, "title": src_of(m, sources).title or "",
 162 | -                                        "channel": _name(m, ctx), "window": win,
 163 | -                                        "published": str(m.get("published_at") or "")[:16],
 164 | -                                        "show_date": ctx.now.strftime("%Y-%m-%d")}
 165 | -        if not contexts:
 166 | -            continue
 167 | +    chunks = [todo[i:i + batch] for i in range(0, len(todo), batch)]
 168 | +
 169 | +    def screen(i, chunk):
 170 |          try:
 171 | -            got, backend = CI.step_a(router, contexts, writer_vendor, seed=7 + i, writer_family=writer_family)
 172 | +            return CI.step_a(router, {m["moment_id"]: contexts[m["moment_id"]] for m in chunk}, writer_vendor,
 173 | +                             seed=7 + i * batch, writer_family=writer_family), None
 174 |          except Exception as e:                           # unreadable: these moments are not cleared (law L-m)
 175 | -            for mid in contexts:
 176 | -                fails[mid] = [f"STEP_A_UNAVAILABLE: {type(e).__name__}"]
 177 | +            return None, e
 178 | +    with ThreadPoolExecutor(max_workers=max(1, min(PRESCREEN_WORKERS, len(chunks)))) as ex:
 179 | +        res = list(ex.map(lambda ic: screen(*ic), enumerate(chunks)))   # map keeps the chunks' order: zipped below
 180 | +    new = {}
 181 | +    for chunk, (got, e) in zip(chunks, res):
 182 | +        if got is None:
 183 | +            for m in chunk:
 184 | +                fails[m["moment_id"]] = [f"STEP_A_UNAVAILABLE: {type(e).__name__}: {str(e)[:160]}"]
 185 |              continue
 186 | +        items, backend = got
 187 |          b = router.backends.get(backend)
 188 |          vendors.add(b.vendor if b else backend)
 189 |          families.add(b.family if b else backend)
 190 | -        for mid, a in got.items():
 191 | -            a_by[mid] = a
 192 | -            fails[mid] = CI.a_failures(a)
 193 | +        for mid, a in items.items():
 194 | +            a_by[mid], fails[mid] = a, CI.a_failures(a)
 195 |              db[f"{mid}:{STEP_A_VERSION}"] = a
 196 | -    if store and todo:
 197 | +            if mid in keys and a.get("backend"):
 198 | +                new.setdefault(keys[mid], {})[a["backend"]] = a
 199 | +    if store and (todo or db):
 200 |          os.makedirs(os.path.dirname(os.path.abspath(store)), exist_ok=True)
 201 |          with open(store + ".tmp", "w") as f:
 202 |              json.dump(db, f, indent=1)
 203 |          os.replace(store + ".tmp", store)
 204 | +    _cache_put(cache, new)
 205 |      return a_by, fails, vendors, families
 206 |  
 207 |  
 208 | -def second_screen(router, cleared, a_by, sources, ctx, log=print):
 209 | +def second_screen(router, cleared, a_by, sources, ctx, log=print, cache=None):
 210 |      """ORDER 06:22 item 45: step A from a SECOND vendor on every cuttable clip, BEFORE the angle step. The writer is
 211 |      known only when the angle call answers (Heimdall first, Grok on its failure: angle_write), and a verdict never
 212 |      comes from the writer's vendor (L-x). The only step-A vendors are the writers' own two (context_verdict: xai, then
 213 | @@ -469,7 +529,8 @@ def second_screen(router, cleared, a_by, sources, ctx, log=print):
 214 |              for i in range(0, len(g), PRESCREEN_BATCH)]
 215 |      def one(k, chunk):                  # a chunk whose screen raises fails closed, never the build (audit 0640 C1)
 216 |          try:
 217 | -            return prescreen(router, chunk, sources, ctx, {k[0]}, {k[1]}, n=len(chunk), store=None, log=log)
 218 | +            return prescreen(router, chunk, sources, ctx, {k[0]}, {k[1]}, n=len(chunk), store=None, log=log,
 219 | +                             cache=cache)                    # ruling 58: a second verdict is paid for once too
 220 |          except Exception as e:
 221 |              return {}, {m["moment_id"]: [f"STEP_A_UNAVAILABLE: {type(e).__name__}: {str(e)[:120]}"]
 222 |                          for m in chunk}, set(), set()
 223 | @@ -502,7 +563,12 @@ channels were not in one conversation and never answer each other.
 224 |  {note}
 225 |  {clips}
 226 |  
 227 | -Find up to {k} ANGLES, best first. An angle is ONE sentence a viewer could repeat: a point that several of these clips
 228 | +THE HOOKS: a video may OPEN only on one of these clips; each was judged first, alone, on its job as the opener (rated
 229 | +4-5 of 5), best first:
 230 | +{hooks}
 231 | +
 232 | +Find ANGLES, best hook first: up to {per} for EACH hook above, at most {k} in all, each written FOR its hook (it opens
 233 | +the video and sets up the point). An angle is ONE sentence a viewer could repeat: a point that several of these clips
 234 |  GENUINELY support together (each clip adds a different reason, fact or voice to the same point). Do not make a point
 235 |  the clips do not state. Do not build an angle on a price level or move as if it were today's news unless a clip says
 236 |  it is today's.
 237 | @@ -511,11 +577,10 @@ clip's opening makes sense right after the previous clip's ending, in the speake
 238 |  introduction to be understood). The video plays the hook and 2-4 more clips, ONE per channel, from 3-5 DIFFERENT
 239 |  channels, together {lo:.0f}-{hi:.0f} seconds of clips. PLACEMENT LIMITS: a clip marked "only the hook or the LAST
 240 |  clip" is the first or the LAST id of an angle's list, never in between; a clip marked "only the LAST clip" is the LAST
 241 | -id or is not in it; a clip marked "cannot open" is never the hook. Give as many good angles as the clips allow (aim for
 242 | -{k}); for
 243 | +id or is not in it; a clip marked "cannot open" is never the hook. Give as many good angles as the clips allow; for
 244 |  each angle give: "angle" (the sentence); "moments": the ids of 4 to 8 clips IN PLAY ORDER, the hook first (more choice
 245 |  survives a clip that later fails a check), from at least 3 different channels, with enough seconds among them;
 246 | -"hook": the first id, whose FIRST WORDS grab attention AND set up the angle; "support": for each of those ids, a few
 247 | +"hook": the first id: the hook from THE HOOKS this angle is written for; "support": for each of those ids, a few
 248 |  words on what it adds and why it follows the clip before it (an internal note).
 249 |  Return ONLY this JSON object: {{"angles": [{{"angle": "...", "moments": ["id", "id", "id"], "hook": "id",
 250 |  "support": {{"id": "..."}}}}]}}"""
 251 | @@ -543,6 +608,72 @@ Return ONLY this JSON object: {{"through_line": "...", "hook": {{"scroll": 1, "a
 252 |  "clips": {{{clip_keys}}}, "joins": {{{joins}}}}}"""
 253 |  HOOK_PARTS = ("scroll", "alone", "setup")   # ruling 52 (08:06 Nov 13): the hook's own job, each part rated 1-5
 254 |  HOOK_RULE = "the lowest of scroll / alone / setup (ruling 52): every part must reach the bar"
 255 | +HOOKS_PROMPT = """You judge OPENING clips for 60-second videos made of other channels' own words (each clip is a person's
 256 | +own words from a show). Each candidate below would play FIRST, before anything else is said. Judge each one ALONE, as
 257 | +the opener of a video; the candidates are not compared with each other and never play together.
 258 | +
 259 | +{hooks}
 260 | +
 261 | +For EACH candidate: """ + HOOK_QUESTION + """
 262 | +Give "why": a few words on the candidate's weakest part.
 263 | +Return ONLY this JSON object: {{"hooks": {{{keys}}}}}"""   # ruling 59 (a): ruling 52's ONE hook question, per candidate
 264 | +HOOK_VERSION = hashlib.sha256(HOOKS_PROMPT.encode()).hexdigest()[:12]   # a cached rating is for exactly this question
 265 | +
 266 | +
 267 | +def hook_ratings(router, ms, ctx, writer_vendor, writer_family=None, cache=None, seed=7):
 268 | +    """RULING 59 (a): the hook question of ruling 52 (HOOK_QUESTION: scroll / alone / setup, each 1-5) asked of EVERY
 269 | +    given moment ALONE, in ONE batched call (coherence_verdict, never the writers' vendor or family), each rating
 270 | +    DERIVED as the lowest part (HOOK_RULE). Cached (`cache`, shared by every build) by the moment id, the sha256 of its
 271 | +    text and the question's version: a moment is rated once, by a back-end off the writers. One re-ask on a reply out
 272 | +    of contract. -> ({moment id: {"scroll", "alone", "setup", "rating", "why", "backend", "cached"}}, the error or None).
 273 | +    A moment the call did not rate has no rating (law L-m: never a pass)."""
 274 | +    import providers as P
 275 | +    wv, wf = P._as_set(writer_vendor), P._as_set(writer_family)
 276 | +    off = lambda name: (lambda b: b is not None and b.vendor not in wv and b.family not in wf)(router.backends.get(name))
 277 | +    cdb, out, todo = _load_cache(cache), {}, []
 278 | +    key = lambda m: f"{m['moment_id']}:{text_sha(m['text'])}:{HOOK_VERSION}"
 279 | +    for m in ms:
 280 | +        rec = next((x for name, x in sorted((cdb.get(key(m)) or {}).items())
 281 | +                    if isinstance(x, dict) and off(name) and x.get("backend") == name), None)
 282 | +        if rec is not None:
 283 | +            out[m["moment_id"]] = dict(rec, cached=True)
 284 | +        else:
 285 | +            todo.append(m)
 286 | +    if not todo:
 287 | +        return out, None
 288 | +    ids = [m["moment_id"] for m in todo]
 289 | +    cands = "\n".join(f'CANDIDATE id="{m["moment_id"]}" (on screen: {CI._q(_name(m, ctx), 80)}): '
 290 | +                      f'"{CI._q(m["text"], 900)}"' for m in todo)
 291 | +    keys = ", ".join(f'"{i}": {{"scroll": 1, "alone": 1, "setup": 1, "why": "..."}}' for i in ids)
 292 | +    err = None
 293 | +    for s in (seed, seed + 1):
 294 | +        r = None
 295 | +        try:
 296 | +            r = router.call("coherence_verdict", HOOKS_PROMPT.format(hooks=cands, keys=keys), 600 + 150 * len(ids), s,
 297 | +                            avoid_vendor=writer_vendor, avoid_family=writer_family)
 298 | +            v = json.loads(r.text.strip())
 299 | +            h = v["hooks"] if isinstance(v, dict) and set(v) == {"hooks"} else None
 300 | +            if not isinstance(h, dict) or set(h) != set(ids) or any(
 301 | +                    not isinstance(x, dict) or set(x) != set(HOOK_PARTS) | {"why"} or not isinstance(x["why"], str) or
 302 | +                    any(type(x[k]) is not int or not 1 <= x[k] <= 5 for k in HOOK_PARTS) for x in h.values()):
 303 | +                raise ValueError("hook ratings out of contract")
 304 | +        except (P.ProviderError, P.SpendLimit, ValueError, TypeError, KeyError) as e:
 305 | +            if r is not None and isinstance(e, (ValueError, TypeError, KeyError)):
 306 | +                router.reject(r)
 307 | +            err = f"{type(e).__name__}: {str(e)[:200]}"
 308 | +            if isinstance(e, (ValueError, TypeError, KeyError)):
 309 | +                continue                                 # out of contract: one re-ask
 310 | +            break                                        # unavailable or the spend guard: no verdict (law L-m)
 311 | +        new = {}
 312 | +        for m in todo:
 313 | +            x = h[m["moment_id"]]
 314 | +            rec = {**{k: x[k] for k in HOOK_PARTS}, "rating": min(x[k] for k in HOOK_PARTS), "why": x["why"][:300],
 315 | +                   "backend": r.backend, "rule": HOOK_RULE}
 316 | +            out[m["moment_id"]] = dict(rec, cached=False, replayed=bool(getattr(r, "replayed", False)))
 317 | +            new[key(m)] = {r.backend: rec}
 318 | +        _cache_put(cache, new)
 319 | +        return out, None
 320 | +    return out, err
 321 |  
 322 |  WRITE_LY = """You are PBX MAX, the host of a 60-second Bitcoin video made of other channels' own words.
 323 |  THE ANGLE (the point this video makes): "{angle}"
 324 | @@ -612,7 +743,7 @@ def current_levels(sources, ctx, hours=24.0):
 325 |      return sorted(out)
 326 |  
 327 |  
 328 | -def check_angles(obj, by_id, k=MAX_ANGLES):
 329 | +def check_angles(obj, by_id, k=MAX_ANGLES, hooks=None):
 330 |      if not isinstance(obj, dict) or set(obj) != {"angles"} or not isinstance(obj["angles"], list) or \
 331 |              not 1 <= len(obj["angles"]) <= k:
 332 |          raise ValueError(f"exactly {{'angles': [1-{k} items]}}")
 333 | @@ -633,6 +764,8 @@ def check_angles(obj, by_id, k=MAX_ANGLES):
 334 |              raise ValueError(f"angle {i + 1}: >= 3 channels (one clip per channel, L-u), and the hook one of its moments")
 335 |          if not isinstance(a["support"], dict) or set(a["support"]) != set(ms):
 336 |              raise ValueError(f"angle {i + 1}: 'support' needs exactly its moment ids")
 337 | +        if hooks is not None and a["hook"] not in hooks:            # ruling 59 (c): written FOR a passing hook
 338 | +            raise ValueError(f"angle {i + 1}: its hook {a['hook']!r} is not one of THE HOOKS")
 339 |          out.append(a)
 340 |      return out
 341 |  
 342 | @@ -853,6 +986,34 @@ def no_role_on_screen(m):
 343 |      return None if (c_ok or h_ok) else f"the render's STAND_ALONE with no clip scorer at the pin stage: {c_why}; {h_why}"
 344 |  
 345 |  
 346 | +def can_open(m):
 347 | +    """Whether a moment may OPEN a line-up: hook-eligible, its hook onset measured and passed (G17a), a first word the
 348 | +    render's STAND_ALONE takes for a hook (stand_alone.opener), and, once the build has rated the pool's hooks (RULING
 349 | +    59: build() sets "hook_rating" on every cleared moment before any line-up), rated >= HOOK_MIN on the hook's own job
 350 | +    (an unmeasured rating is never a pass, law L-m). A moment without the key is judged as before ruling 59."""
 351 | +    import stand_alone as SA
 352 | +    if not ((m.get("eligibility") or {}).get("hook", {}).get("ok") and (m.get("hook_onset") or {}).get("pass") is True
 353 | +            and SA.opener("hook", m.get("text") or "")[0]):
 354 | +        return False
 355 | +    r = (m.get("hook_rating") or {}).get("rating") if "hook_rating" in m else HOOK_MIN
 356 | +    return isinstance(r, int) and not isinstance(r, bool) and r >= HOOK_MIN
 357 | +
 358 | +
 359 | +def hook_order(ms):
 360 | +    """RULING 59 (c): the passing hooks best first: the derived rating, then the sum of its parts, then the miner's
 361 | +    score, then the id (a total order)."""
 362 | +    hr = lambda m: m.get("hook_rating") or {}
 363 | +    return sorted(ms, key=lambda m: (-(hr(m).get("rating") or 0), -sum(hr(m).get(k) or 0 for k in HOOK_PARTS),
 364 | +                                     -m["rank_score"], m["moment_id"]))
 365 | +
 366 | +
 367 | +def hook_line(m, ctx):
 368 | +    """One rated hook as ruling 59 (d) lists it: the channel, the rating and its parts, the judge's reason, the words."""
 369 | +    r = m.get("hook_rating") or {}
 370 | +    return {"moment_id": m["moment_id"], "channel": _name(m, ctx), "rating": r.get("rating"),
 371 | +            **{k: r.get(k) for k in HOOK_PARTS}, "why": r.get("why"), "text": (m.get("text") or "")[:160]}
 372 | +
 373 | +
 374 |  def lineup_ok(segs, crange=None, repeat_ok=False):
 375 |      """The rules lineup_for applies, checked on a GIVEN line-up in play order -> (ok, why): the hook can open (hook
 376 |      eligibility and the G17a measure), every clip is clip-eligible, the hook + LY_CLIPS clips, one segment per channel
 377 | @@ -862,7 +1023,7 @@ def lineup_ok(segs, crange=None, repeat_ok=False):
 378 |      h, clips = segs[0], segs[1:]
 379 |      if not LY_CLIPS[0] <= len(clips) <= LY_CLIPS[1]:
 380 |          return False, f"{len(clips)} clips"
 381 | -    if not ((h.get("eligibility") or {}).get("hook", {}).get("ok") and (h.get("hook_onset") or {}).get("pass") is True):
 382 | +    if not can_open(h):                                  # ruling 59 (b): rated too, once the pool's hooks are
 383 |          return False, "the hook cannot open"
 384 |      if not all((m.get("eligibility") or {}).get("clip", {}).get("ok") for m in clips):
 385 |          return False, "a clip is not clip-eligible"
 386 | @@ -884,22 +1045,22 @@ def lineup_ok(segs, crange=None, repeat_ok=False):
 387 |      return True, "ok"
 388 |  
 389 |  
 390 | -def swap_lineup(segs, weak, pool, avoid=frozenset(), crange=None):
 391 | +def swap_lineup(segs, weak, pool, avoid=frozenset(), crange=None, keep_hook=False):
 392 |      """RULING 41: the next line-up after a clips-alone failure. Every segment in `weak` (moment ids rated below the
 393 |      bar) is swapped AT ITS PLACE for the next candidate by score from the whole cleared pool: the hook for the next hook
 394 |      by its first 2 s (scores.hook_first_2s), a clip for the next clip by rank_score. The segments rated 4-5 stay where
 395 |      they are. The first combination (up to SWAP_TOP candidates per place, in score order) that passes lineup_ok wins,
 396 | -    one clip per channel first, then L-y 4's supply exception. -> (segs, {old id: new id}) or (None, None)."""
 397 | +    one clip per channel first, then L-y 4's supply exception. keep_hook (RULING 59 c: a line-up is built AROUND its
 398 | +    hook): a weak hook is never swapped, so no swap fits. -> (segs, {old id: new id}) or (None, None)."""
 399 |      used = {m["moment_id"] for m in segs}
 400 |      places = [i for i, m in enumerate(segs) if m["moment_id"] in weak]
 401 | -    if not places:
 402 | +    if not places or (keep_hook and 0 in places):
 403 |          return None, None
 404 |      free = [m for m in pool.values() if m["moment_id"] not in used and m["moment_id"] not in avoid]
 405 |  
 406 |      def cands(i):
 407 |          if i == 0:
 408 | -            c = [m for m in free if (m.get("eligibility") or {}).get("hook", {}).get("ok")
 409 | -                 and (m.get("hook_onset") or {}).get("pass") is True]
 410 | +            c = [m for m in free if can_open(m)]                     # ruling 59 (b): rated, once rated
 411 |              c.sort(key=lambda m: (-m["scores"]["hook_first_2s"], -m["rank_score"], m["moment_id"]))
 412 |          else:
 413 |              c = [m for m in free if (m.get("eligibility") or {}).get("clip", {}).get("ok")
 414 | @@ -923,15 +1084,15 @@ def placement(m):
 415 |      """RULING 54: a clip's placement limits as the angle proposer is told them, exactly lineup_for's rules. Without hook
 416 |      eligibility and a passed hook onset (G17a) it cannot open. Under SHORT_CLIP_S it may not play mid-line-up: the
 417 |      short-clip rule binds the clips AFTER the hook only, so a short clip that can open may be the hook or the LAST clip,
 418 | -    and one that cannot open only the LAST (the 08:46 build: a 7.26 s opener was the only formable hook)."""
 419 | -    opens = bool((m.get("eligibility") or {}).get("hook", {}).get("ok")) and \
 420 | -        (m.get("hook_onset") or {}).get("pass") is True
 421 | +    and one that cannot open only the LAST (the 08:46 build: a 7.26 s opener was the only formable hook). RULING 59:
 422 | +    "may open" is can_open(): once the pool's hooks are rated, only a hook rated >= HOOK_MIN opens."""
 423 | +    opens = can_open(m)
 424 |      if m["duration_s"] < SHORT_CLIP_S:
 425 |          return f" | under {SHORT_CLIP_S:.0f} s: " + ("only the hook or the LAST clip" if opens else "only the LAST clip")
 426 |      return "" if opens else " | cannot open (never the hook)"
 427 |  
 428 |  
 429 | -def pool_fill(angle, pool, dropped=frozenset(), now=None):
 430 | +def pool_fill(angle, pool, dropped=frozenset(), now=None, hook_only=False):
 431 |      """PROPOSAL 1: an angle whose own moments form no line-up (lineup_for, one clip per channel, then L-y 4's
 432 |      exception) is completed from the WHOLE cleared pool, as ruling 41's swap fills a place: the pool's other moments
 433 |      are appended to the angle's after its own, best by rank_score, and lineup_for runs again under every unchanged
 434 | @@ -951,7 +1112,7 @@ def pool_fill(angle, pool, dropped=frozenset(), now=None):
 435 |      half = lambda segs: 2 * sum(m["moment_id"] in mine for m in segs) >= len(segs)   # the angle's own: >= half
 436 |      for repeat_ok in (False, True):
 437 |          segs = lineup_for(ext, pool, dropped, repeat_ok=repeat_ok, need_onset=True, need_stand_alone=True, accept=half,
 438 | -                          now=now)
 439 | +                          now=now, hook_only=hook_only)
 440 |          if segs is not None:
 441 |              return segs, [m["moment_id"] for m in segs if m["moment_id"] not in mine]
 442 |      return None, None
 443 | @@ -976,7 +1137,7 @@ def fresh_key(segs, now):
 444 |  
 445 |  
 446 |  def lineup_for(angle, by_id, dropped=frozenset(), clips=LY_CLIPS, crange=None, repeat_ok=False, need_onset=False,
 447 | -               need_stand_alone=False, accept=None, now=None):
 448 | +               need_stand_alone=False, accept=None, now=None, hook_only=False):
 449 |      """The hook + clips[0]..clips[1] clips for one angle, in the PROPOSER'S PLAY ORDER (L-y 3: the order carries a
 450 |      medley): the proposer's hook (else the angle's best hook-eligible moment by its first 2 s), the clips from the
 451 |      angle's other moments, every segment from a different channel (L-u), at most PRICE_PREDICTIONS_MAX price
 452 | @@ -991,8 +1152,8 @@ def lineup_for(angle, by_id, dropped=frozenset(), clips=LY_CLIPS, crange=None, r
 453 |      lo, hi = crange or medley_content_range()
 454 |      pos = {m: i for i, m in enumerate(angle["moments"])}
 455 |      ms = [by_id[m] for m in angle["moments"] if m in by_id and m not in dropped]
 456 | -    hooks = [m for m in ms if (m.get("eligibility") or {}).get("hook", {}).get("ok") and
 457 | -             (not need_onset or (m.get("hook_onset") or {}).get("pass") is True)]
 458 | +    hooks = [m for m in ms if (can_open(m) if need_onset else (m.get("eligibility") or {}).get("hook", {}).get("ok"))
 459 | +             and (not hook_only or m["moment_id"] == angle["hook"])]   # ruling 59 (b) rated; (c) the angle's own hook
 460 |      hooks.sort(key=lambda m: (m["moment_id"] != angle["hook"], -m["scores"]["hook_first_2s"]))
 461 |      for h in hooks:
 462 |          pool = [m for m in ms if m is not h and (m.get("eligibility") or {}).get("clip", {}).get("ok")
 463 | @@ -1437,13 +1598,20 @@ def _takeaway_record(ai, n_lineup, w_used, pk, cheap, fid=None, cx=None):
 464 |  
 465 |  
 466 |  def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=print, max_angles=MAX_ANGLES,
 467 | -          writes=WRITES, work_dir=None, store=None, spend=None, lineups=LINEUPS_PER_BUILD):
 468 | +          writes=WRITES, work_dir=None, store=None, spend=None, lineups=LINEUPS_PER_BUILD, step_a_cache=None,
 469 | +          hook_cache=None):
 470 |      """L-y MEDLEY (the default since orchestrator 20:30 Nov 12), angle first, inside the orchestrator's budgets (05:25
 471 |      item 5, 05:30): per angle at most `lineups` line-ups, each judged on the clips ALONE first (medley(); nothing is
 472 |      written for a line-up that fails it); a line-up that passes gets at most `writes` writes of the takeaway (and of the
 473 |      one bridge, only at the join the clips-alone verdict flagged); the first package that passes every hard gate wins.
 474 |      work_dir: where law L-v 2's audio windows go (required: without it no package can pass). store: the step-A ledger.
 475 |      spend: a callable returning the ledger's USD (dollars per package).
 476 | +    step_a_cache / hook_cache (rulings 58 / 59): the verdict caches every build shares (None: this build's only).
 477 | +    RULING 59, HOOK FIRST: once the pool is screened, every cleared, cuttable moment that can open is rated on the hook's
 478 | +    own job in one batched call (hook_ratings); only a hook rated >= HOOK_MIN opens; with none, the build stops there
 479 | +    ('no hook in the pool', the three best listed) before the second screen, the angles and any line-up. The angle
 480 | +    writer is given THE HOOKS and writes each angle FOR one; the angles are tried best hook first (ruling 57's
 481 | +    freshness next), each line-up opens on its angle's own hook and never swaps it.
 482 |      -> {"package", "packages", "tried", "angles", "takeaways" (every written takeaway with its gates), ...}."""
 483 |      t0 = time.time()
 484 |      usd0 = _spent(spend)
 485 | @@ -1457,7 +1625,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 486 |      ad_read = ad_read_out(ms, sources)                # the exclusion screen's free part, BEFORE the angle is built
 487 |      ms = [m for m in ms if m["moment_id"] not in ad_read]     # around a moment it refuses (the 03:39 build's hook)
 488 |      wv, wf = _writers(router)
 489 | -    a_by, fails, a_vendors, a_families = prescreen(router, ms, sources, ctx, wv, wf, store=store, log=log)
 490 | +    a_by, fails, a_vendors, a_families = prescreen(router, ms, sources, ctx, wv, wf, store=store, log=log,
 491 | +                                                   cache=step_a_cache)          # ruling 58: every candidate, once
 492 |      cleared = {m["moment_id"]: m for m in ms if m["moment_id"] in a_by and not fails.get(m["moment_id"])}
 493 |      levels = current_levels(sources.values(), ctx)
 494 |      out = {"shape": "medley", "packages": [], "tried": [], "unusable": why, "usable": n_usable, "current_levels": levels,
 495 | @@ -1507,7 +1676,32 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 496 |      out["prescreen"]["trim_cut"] = trim_cut
 497 |      log(f"  {sum(m['hook_onset'].get('pass') is True for m in cleared.values())} of them can open a medley "
 498 |          f"(G17a at the pin stage: genuine quiet before the first onset)")
 499 | -    a_two, off_fail = second_screen(router, cleared, a_by, sources, ctx, log=log)        # ORDER 06:22 item 45
 500 | +    for m in cleared.values():                                           # a rating is this build's own (its
 501 | +        m.pop("hook_rating", None)                                       # cache's), never one carried in
 502 | +    openers = {mid: m for mid, m in cleared.items() if can_open(m)}      # RULING 59 (a): every one that can open,
 503 | +    rated, hook_err = hook_ratings(router, list(openers.values()), ctx, wv, wf, cache=hook_cache) if openers else \
 504 | +        ({}, None)                                                        # one batched call, cached
 505 | +    for mid, m in cleared.items():                                       # (b): the rating gates every opening now
 506 | +        m["hook_rating"] = rated.get(mid) or {"rating": None, "why": (f"not rated: {hook_err}" if mid in openers else
 507 | +                                                                      "cannot open (hook eligibility, G17a or the "
 508 | +                                                                      "render's hook rule)")}
 509 | +    best = [hook_line(m, ctx) for m in hook_order([m for mid, m in openers.items() if mid in rated])[:3]]
 510 | +    out["hook_pool"] = {"can_open": len(openers), "rated": len(rated), "error": hook_err, "min": HOOK_MIN,
 511 | +                        "ratings": {mid: rated[mid] for mid in sorted(rated)}, "best": best,
 512 | +                        "passing": [m["moment_id"] for m in hook_order([m for m in cleared.values() if can_open(m)])]}
 513 | +    log(f"  hooks (ruling 59): {len(openers)} can open, {len(rated)} rated, {len(out['hook_pool']['passing'])} rated >= "
 514 | +        f"{HOOK_MIN} on the hook's own job" + (f"; NOT RATED: {hook_err}" if hook_err else "") +
 515 | +        f" ({time.time() - t0:.0f} s)")
 516 | +    if not out["hook_pool"]["passing"]:                                  # (d): no line-up is paid for
 517 | +        out["why_none"] = ("no hook in the pool (ruling 59 d): " + (
 518 | +            f"none of the {len(openers)} moments that can open rates >= {HOOK_MIN} on the hook's own job" +
 519 | +            (f" ({len(openers) - len(rated)} not rated: {hook_err})" if hook_err else "") + "; the best: " +
 520 | +            "; ".join(f"{b['channel']} {b['rating']} (scroll {b['scroll']}, alone {b['alone']}, setup {b['setup']}): "
 521 | +                      f"{b['why']}" for b in best) if openers else
 522 | +            "no cleared, cuttable moment can open (hook eligibility, G17a, the render's hook rule)"))
 523 | +        return out
 524 | +    a_two, off_fail = second_screen(router, cleared, a_by, sources, ctx, log=log,
 525 | +                                    cache=step_a_cache)                  # ORDER 06:22 item 45
 526 |      out["prescreen"]["second_vendor"] = {mid: f"PASS ({a_two[mid][1].get('backend')})" if mid in a_two else
 527 |                                           "FAIL: " + "; ".join(off_fail.get(mid) or ["no second verdict"])
 528 |                                           for mid in cleared}
 529 | @@ -1518,30 +1712,45 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 530 |          out["why_none"] = (f"{len(cleared)} cleared moments pass the second pass, CUTTABLE and step A from both "
 531 |                             f"vendors, from fewer than 3 channels")
 532 |          return out
 533 | +    passing = hook_order([m for m in cleared.values() if can_open(m)])    # ruling 59: the passing hooks still
 534 | +    if not passing:                                                        # cleared after the second screen
 535 | +        out["why_none"] = ("no hook in the pool (ruling 59 d): every hook rated >= " + str(HOOK_MIN) + " failed the "
 536 | +                           "second vendor's step A: " + "; ".join(out["prescreen"]["second_vendor"].get(mid, "?")
 537 | +                                                                    for mid in out["hook_pool"]["passing"]))
 538 | +        return out
 539 |      clips = "\n".join(f'id={m["moment_id"]} | {_name(m, ctx)} | {m["duration_s"]:.1f} s{placement(m)} | '
 540 |                        f'"{quote_data(m["text"], 600)}"'
 541 |                        for m in sorted(cleared.values(), key=lambda m: (-m["rank_score"], m["moment_id"])))
 542 | +    hooks_txt = "\n".join(f'id={m["moment_id"]} | rated {m["hook_rating"]["rating"]} on its own job: '
 543 | +                          f'"{quote_data(m["hook_rating"].get("why") or "", 200)}"' for m in passing)
 544 | +    per = max(1, max_angles // len(passing))
 545 |      lo, hi = medley_content_range()
 546 | -    angles, angle_reply = None, None
 547 | +    angles, angle_reply, errs = None, None, []
 548 |      for seed in (7, 8):                               # one re-ask on an out-of-contract reply (never served again)
 549 |          r = None
 550 |          try:
 551 |              r = router.call("angle_write", ANGLE_PROMPT.format(note=UNTRUSTED.replace("<sentences>", "the quotes"),
 552 | -                                                               clips=clips, k=max_angles, lo=lo, hi=hi), 3000, seed,
 553 | +                                                               clips=clips, hooks=hooks_txt, per=per, k=max_angles,
 554 | +                                                               lo=lo, hi=hi), 3000, seed,
 555 |                              deadline_s=WRITER_DEADLINE_S)
 556 | -            angles, angle_reply = check_angles(json.loads(r.text.strip()), cleared, max_angles), r
 557 | +            angles, angle_reply = check_angles(json.loads(r.text.strip()), cleared, max_angles,
 558 | +                                               hooks={m["moment_id"] for m in passing}), r   # ruling 59 (c)
 559 |              break
 560 |          except Exception as e:
 561 |              if r is not None:
 562 |                  router.reject(r)
 563 | -            out["why_none"] = f"no readable angles: {type(e).__name__}: {str(e)[:200]}"
 564 | +            errs.append(f"{type(e).__name__}: {str(e)[:200]}")       # every reason, the first one too
 565 | +            out["why_none"] = "no readable angles: " + "; then ".join(errs)
 566 |      if not angles:
 567 |          return out
 568 |      out.pop("why_none", None)
 569 |      def first_fresh(a):                                   # ruling 57: the angles whose first line-up holds a clip
 570 | -        segs = lineup_for(a, cleared, need_onset=True, need_stand_alone=True, now=ctx.now)   # <= FRESH_H old go first
 571 | -        return bool(segs) and fresh_key(segs, ctx.now)[0]
 572 | -    angles = sorted(angles, key=lambda a: not first_fresh(a))      # stable: the writer's order within each group
 573 | +        segs = lineup_for(a, cleared, need_onset=True, need_stand_alone=True, now=ctx.now, hook_only=True)  # <= FRESH_H
 574 | +        return bool(segs) and fresh_key(segs, ctx.now)[0]                                              # old go first
 575 | +    hrank = {m["moment_id"]: (-m["hook_rating"]["rating"], -sum(m["hook_rating"][k] for k in HOOK_PARTS))
 576 | +             for m in passing}                            # ruling 59 (c): the best hook first, then ruling 57's
 577 | +    angles = sorted(angles, key=lambda a: (hrank[a["hook"]], not first_fresh(a)))   # freshness; stable: the writer's
 578 | +    # order within each
 579 |      out["angles"] = [{"angle": a["angle"], "moments": a["moments"], "hook": a["hook"]} for a in angles]
 580 |      out["angle_backend"], out["angle_tried"] = angle_reply.backend, [list(x) for x in angle_reply.tried]   # ruling 5
 581 |      writers_v, writers_f = {angle_reply.vendor}, {angle_reply.family}
 582 | @@ -1692,15 +1901,16 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 583 |                      exception = supply_exception(segs, ctx)
 584 |                  else:
 585 |                      segs, exception = lineup_for(angle, cleared, frozenset(dropped | doomed), need_onset=True,
 586 | -                                                 need_stand_alone=True, now=ctx.now), None
 587 | +                                                 need_stand_alone=True, now=ctx.now, hook_only=True), None
 588 |                      if segs is None:                      # L-y 4: one clip per channel unless the supply forces otherwise
 589 |                          segs = lineup_for(angle, cleared, frozenset(dropped | doomed), repeat_ok=True, need_onset=True,
 590 | -                                          need_stand_alone=True, now=ctx.now)
 591 | +                                          need_stand_alone=True, now=ctx.now, hook_only=True)
 592 |                          if segs is not None:
 593 |                              exception = supply_exception(segs, ctx)
 594 |                      filled = None
 595 |                      if segs is None and n_lineup == 0:    # PROPOSAL 1: the angle's own moments form not even its
 596 | -                        segs, filled = pool_fill(angle, cleared, frozenset(dropped | doomed), ctx.now)   # FIRST: the
 597 | +                        segs, filled = pool_fill(angle, cleared, frozenset(dropped | doomed), ctx.now,
 598 | +                                                 hook_only=True)   # FIRST: the
 599 |                          # pool completes it. A re-line after a drop moves on to the next angle, as before
 600 |                          exception = supply_exception(segs, ctx) if segs is not None else None
 601 |                  rec = {"angle": ai + 1, "text": angle["angle"], "lineup": [m["moment_id"] for m in segs] if segs else None,
 602 | @@ -1725,11 +1935,15 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 603 |                              if lb in by_lab and x < COHERENCE_MIN}      # ruling 41: the HOOK too (the next hook)
 604 |                      if len(med.get("flagged") or []) > LY_MAX_BRIDGES:
 605 |                          weak |= {by_lab[j.split(" -> ")[1]]["moment_id"] for j in med["flagged"][1:]}
 606 | +                    hook_weak = segs[0]["moment_id"] in weak
 607 | +                    weak.discard(segs[0]["moment_id"])    # ruling 59 (c): the line-up is built AROUND its hook
 608 |                      if not med.get("measured") or not weak:
 609 | -                        rec["why"] = "the clips alone have no through-line a viewer can state (or it was not measured)"
 610 | +                        rec["why"] = ("the hook rates below the bar in this line-up and no clip after it does; the angle "
 611 | +                                      "is written for this hook (ruling 59 c)" if med.get("measured") and hook_weak else
 612 | +                                      "the clips alone have no through-line a viewer can state (or it was not measured)")
 613 |                          break
 614 |                      dropped |= weak
 615 | -                    swapped, swaps = swap_lineup(segs, weak, cleared, frozenset(dropped | doomed))
 616 | +                    swapped, swaps = swap_lineup(segs, weak, cleared, frozenset(dropped | doomed), keep_hook=True)
 617 |                      rec["why"] = (f"the clips alone fail (ratings / joins): swapped {swaps}, re-judged (ruling 41)"
 618 |                                    if swapped is not None else
 619 |                                    f"the clips alone fail (ratings / joins): dropped {sorted(weak)}, no swap fits the "
 620 | @@ -1777,7 +1991,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 621 |                          router.backends.get((a_by.get(m["moment_id"]) or {}).get("backend")))]
 622 |                      if stale:                                  # audit C2 K5: never judged by the writer's vendor
 623 |                          got_a, fails_a, _, _ = prescreen(router, stale, sources, ctx, writers_v, writers_f,
 624 | -                                                         n=len(stale), store=None)
 625 | +                                                         n=len(stale), store=None, cache=step_a_cache)
 626 |                          bad = {}
 627 |                          for m in stale:
 628 |                              mid = m["moment_id"]
 629 | @@ -1791,7 +2005,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 630 |                              dropped |= set(bad)                # with their reason; the next-best cuttable clip takes
 631 |                              doomed |= set(bad)                 # each place (ruling 41's swap); the clips-alone verdict
 632 |                              out["prescreen"].setdefault("rescreen_failed", {}).update(bad)     # re-judges the line-up
 633 | -                            swapped, swaps = swap_lineup(segs, set(bad), cleared, frozenset(dropped | doomed))
 634 | +                            swapped, swaps = swap_lineup(segs, set(bad), cleared, frozenset(dropped | doomed),
 635 | +                                                         keep_hook=True)
 636 |                              rec["why"] = (f"step A, re-screened off the writer's vendor, fails {sorted(bad)} (out for "
 637 |                                            f"good): " + (f"swapped {swaps}, re-judged (order 06:22 item 44)"
 638 |                                                          if swapped is not None else
 639 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
 640 | index 1ea63a0..6aa7ba2 100644
 641 | --- a/tests/package/proof_ledger.py
 642 | +++ b/tests/package/proof_ledger.py
 643 | @@ -134,7 +134,9 @@ def main(argv=None):
 644 |      t0 = time.time()
 645 |      res = PK.build(router, moments, sources, ctx, delivered=delivered, optout=M.optout_ids(), log=say,
 646 |                     work_dir=a.work_dir, store=os.path.join(out_dir, "step_a.json"),
 647 | -                   spend=lambda: (own["est"], own["best"]))
 648 | +                   spend=lambda: (own["est"], own["best"]),
 649 | +                   step_a_cache=os.path.join(HERE, "proof", "STEP_A_CACHE.json"),     # ruling 58: paid for once
 650 | +                   hook_cache=os.path.join(HERE, "proof", "HOOK_CACHE.json"))          # ruling 59 (a): cached
 651 |      res.update(seconds=round(time.time() - t0, 1), usd_estimate=round(own["est"], 4), usd_best_known=round(own["best"], 4),
 652 |                 full={k: round(v, 4) for k, v in used.items()}, code=PL.code_sha(), now=now.isoformat(),
 653 |                 since=since.isoformat(), delivered_pins=pins, chains=router.chains, inputs=inputs)
 654 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 655 | index 04cb0a1..b8e5231 100644
 656 | --- a/tests/package/test_medley.py
 657 | +++ b/tests/package/test_medley.py
 658 | @@ -505,12 +505,13 @@ class Rig:
 659 |  
 660 |      def __init__(self, moments, angle_moments, medleys, writes, uncuttable=(), excluded=(), takeaways=None,
 661 |                   spend=None, no_hook=(), a_fail=None, unavailable=(), angle_from=None, write_from=None,
 662 | -                 trim_fail=()):
 663 | +                 trim_fail=(), hooks=None, hook_err=None):
 664 |          import providers as P
 665 |          self.P, self.moments, self.medleys, self.writes = P, moments, list(medleys), list(writes)
 666 |          self.takeaways, self.spend = list(takeaways or []), spend
 667 |          self.uncuttable, self.excluded, self.no_hook = set(uncuttable), set(excluded), set(no_hook)
 668 |          self.trim_fail = set(trim_fail)                    # trimmed moments whose trimmed cut fails ruling 33 (a)
 669 | +        self.hooks, self.hook_err, self.hook_calls = dict(hooks or {}), hook_err, []   # ruling 59 (a): {id: (s, a, u)}
 670 |          self.medley_calls, self.write_calls, self.prompts = [], [], []
 671 |          self.a_fail, self.unavailable = dict(a_fail or {}), set(unavailable)   # step A per (vendor, moment id)
 672 |          self.screens, self.events, self.a_seen = [], [], []
 673 | @@ -534,7 +535,7 @@ class Rig:
 674 |          self.write_avoid = []
 675 |  
 676 |      def prescreen(self, router, ms, sources, ctx_, writer_vendor, writer_family=None, n=PK.PRESCREEN_N,
 677 | -                  batch=PK.PRESCREEN_BATCH, store=None, log=print):
 678 | +                  batch=PK.PRESCREEN_BATCH, store=None, log=print, cache=None):
 679 |          """Step A as the real prescreen calls it: on the first back-end off the given vendors and families
 680 |          (context_verdict: xai, then heimdall; a third vendor only for the rig); per (vendor, moment) failures."""
 681 |          av, af = self.P._as_set(writer_vendor), self.P._as_set(writer_family)
 682 | @@ -553,6 +554,20 @@ class Rig:
 683 |              fails[mid] = list(self.a_fail.get((v, mid), []))
 684 |          return got, fails, set(), set()
 685 |  
 686 | +    def rate_hooks(self, router, ms, ctx_, writer_vendor, writer_family=None, cache=None, seed=7):
 687 | +        """Ruling 59 (a) as the real hook_ratings answers: every given moment rated (self.hooks, default 5 / 5 / 5),
 688 | +        the rating derived as the lowest part; hook_err: the call failed and nothing is rated."""
 689 | +        self.hook_calls.append([m["moment_id"] for m in ms])
 690 | +        self.events.append("hook_ratings")
 691 | +        if self.hook_err:
 692 | +            return {}, self.hook_err
 693 | +        out = {}
 694 | +        for m in ms:
 695 | +            sc, al, se = self.hooks.get(m["moment_id"], (5, 5, 5))
 696 | +            out[m["moment_id"]] = {"scroll": sc, "alone": al, "setup": se, "rating": min(sc, al, se),
 697 | +                                   "why": f"why {m['moment_id']}", "backend": "xai:grok", "cached": False}
 698 | +        return out, None
 699 | +
 700 |      def medley(self, router, segs, ctx_, wv, seed=7, writer_family=None):
 701 |          self.medley_calls.append([m["moment_id"] for m in segs])
 702 |          ok, flagged, ratings, line = self.medleys.pop(0)
 703 | @@ -602,6 +617,7 @@ class Rig:
 704 |              "truth_for": lambda router, m, *a, **k: {"ok": True, "replayed": False, "model": "scribe_v1",
 705 |                                                       "edges": {"cuttable": m["moment_id"] not in self.uncuttable}},
 706 |              "hook_onset_for": self.onset,
 707 | +            "hook_ratings": self.rate_hooks,
 708 |              "coherence": lambda router, pk, *a, **k: (True, {"through_line": "Nobody gets to bend the rules.",
 709 |                                                               "clips": {sg["label"]: 5 for sg in pk["segments"]},
 710 |                                                               "vo_point": 5, "backend": "xai:grok", "measured": True,
 711 | @@ -754,19 +770,26 @@ class TestBuildLoop(unittest.TestCase):
 712 |          self.assertIsNotNone(out["package"])                               # the search went on: $1.60 < $3.00
 713 |          self.assertEqual((out["search"]["lineups"], out["search"]["usd_reported"]), (2, 1.6))
 714 |  
 715 | -    def test_a_hook_without_80_ms_of_genuine_quiet_gives_way_and_none_means_no_line_up(self):
 716 | +    def test_a_hook_without_80_ms_of_genuine_quiet_never_opens_and_none_means_no_hook(self):
 717 |          """Batch pin #1, held 01:39 ET Nov 13 (G17a: 30 ms of genuine lead before the hook). A moment opens a medley
 718 | -        only when its hook onset was measured and passed; the proposer's hook gives way to the angle's next."""
 719 | -        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], no_hook={"h"})
 720 | -        pk = rig.run()["package"]
 721 | -        self.assertNotEqual(pk["segments"][0]["moment_id"], "h")
 722 | +        only when its hook onset was measured and passed. RULING 59: it is never rated as a hook nor one of THE HOOKS
 723 | +        the writer is given; with no moment that can open, the build stops before any line-up."""
 724 | +        rig = Rig(self.MS, ["x", "h", "y", "z"], [(True, [], None, Rig.LINE)], [None], no_hook={"h"})
 725 | +        out = rig.run()
 726 | +        self.assertNotIn("h", rig.hook_calls[0])                          # never asked as a hook
 727 | +        p = next(p for r, p in rig.prompts if r == "angle_write")
 728 | +        self.assertIn("id=h | A | 12.0 s | cannot open (never the hook) | ", p)
 729 | +        self.assertNotIn("id=h | rated", p)                               # not one of THE HOOKS
 730 | +        pk = out["package"]
 731 | +        self.assertEqual(pk["segments"][0]["moment_id"], "x")
 732 |          self.assertEqual(pk["gates"]["hook_onset"]["status"], "PASS")
 733 |          self.assertEqual(pk["gates"]["hook_onset"]["lead_ms"], 200)
 734 |          rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], no_hook={"h", "x", "y", "z"})
 735 |          out = rig.run()
 736 |          self.assertIsNone(out["package"])
 737 | -        self.assertEqual(rig.medley_calls, [])                    # nothing paid for a line-up that cannot open
 738 | -        self.assertIn("no line-up", out["tried"][0]["why"])
 739 | +        self.assertEqual((rig.medley_calls, rig.hook_calls), ([], []))   # nothing paid for: no hook, no line-up
 740 | +        self.assertIn("no hook in the pool", out["why_none"])
 741 | +        self.assertIn("no cleared, cuttable moment can open", out["why_none"])
 742 |  
 743 |      def test_the_supply_exception_is_recorded(self):
 744 |          ms = [pm("h", "A", 14.0), pm("x", "B", 13.0), pm("y", "C", 3.0), pm("e", "A", 13.0)]
 745 | @@ -987,6 +1010,234 @@ class TestRuling33TrimAtThePinStage(unittest.TestCase):
 746 |          self.assertIn("id=b~trim ", next(p for r, p in rig2.prompts if r == "angle_write"))   # stays as a clip
 747 |  
 748 |  
 749 | +class TestRuling58StepAEveryCandidate(unittest.TestCase):
 750 | +    """RULING 58 (11:00): EVERY candidate is screened at step A, the miner's best first, and a verdict is cached by the
 751 | +    moment id + its text sha (and the exact context step A reads), so a moment is paid for once, not once per build."""
 752 | +
 753 | +    def pool(self, n=20, words="is the hardest money ever made"):
 754 | +        ms, srcs = [], {}
 755 | +        for i in range(n):
 756 | +            mid = f"m{i:02d}"
 757 | +            src = source(["Before it came the long part of the show.", f"Bitcoin number {i} {words}.",
 758 | +                          "After it came the end of the show."], vid=f"v{mid}")
 759 | +            a, b = src.sentences[1]
 760 | +            m = dict(pm(mid, f"C{i:02d}", 0.0, rank=float(i), vid=f"v{mid}"), text=E.spoken(src.tokens[a:b + 1]),
 761 | +                     words=[a, b], sentences=[1, 1], start=float(src.tokens[a]["start"]), end=float(src.tokens[b]["end"]))
 762 | +            m["duration_s"] = round(m["end"] - m["start"], 2)
 763 | +            ms.append(m)
 764 | +            srcs[f"v{mid}"] = src
 765 | +        return ms, srcs
 766 | +
 767 | +    def router(self):
 768 | +        B = lambda v, f: type("B", (), {"vendor": v, "family": f})()
 769 | +        return type("R", (), {"backends": {"xai:grok": B("xai", "grok"), "heimdall:deepseek": B("heimdall", "deepseek")}})()
 770 | +
 771 | +    def fake(self, calls, fail=frozenset()):
 772 | +        import context_integrity as CI
 773 | +        from test_gates import a_item
 774 | +
 775 | +        def step_a(router_, contexts, wv, seed=7, writer_family=None):
 776 | +            calls.append((sorted(contexts), seed))
 777 | +            if set(contexts) & set(fail):
 778 | +                raise RuntimeError("the batch reply was out of contract")
 779 | +            b = "heimdall:deepseek" if "xai" in (wv or set()) else "xai:grok"
 780 | +            return {mid: dict(a_item(mid), backend=b) for mid in contexts}, b
 781 | +        saved = CI.step_a
 782 | +        CI.step_a = step_a
 783 | +        self.addCleanup(setattr, CI, "step_a", saved)
 784 | +
 785 | +    def test_every_candidate_is_screened_the_miners_best_first(self):
 786 | +        self.assertIsNone(PK.PRESCREEN_N)
 787 | +        import tempfile
 788 | +        ms, srcs = self.pool(20)
 789 | +        calls = []
 790 | +        self.fake(calls)
 791 | +        with tempfile.TemporaryDirectory() as d:
 792 | +            a_by, fails, vendors, _ = PK.prescreen(self.router(), ms, srcs, ctx(), {"heimdall"}, {"deepseek"},
 793 | +                                                   store=os.path.join(d, "a.json"), cache=os.path.join(d, "c.json"))
 794 | +        self.assertEqual(len(a_by), 20)                                   # all 20, not 24 of 150
 795 | +        self.assertEqual(sum(len(c[0]) for c in calls), 20)
 796 | +        self.assertEqual(sorted(c[1] for c in calls), [7, 15, 23])        # 8 + 8 + 4, the seeds of their places
 797 | +        first = next(c[0] for c in calls if c[1] == 7)
 798 | +        self.assertEqual(first, sorted(f"m{i:02d}" for i in range(19, 11, -1)))   # the miner's best 8 first
 799 | +        self.assertEqual(vendors, {"xai"})
 800 | +        self.assertFalse(any(fails.values()))
 801 | +
 802 | +    def test_a_moment_is_paid_for_once_across_builds(self):
 803 | +        import tempfile
 804 | +        ms, srcs = self.pool(10)
 805 | +        calls = []
 806 | +        self.fake(calls)
 807 | +        with tempfile.TemporaryDirectory() as d:
 808 | +            cache = os.path.join(d, "STEP_A_CACHE.json")
 809 | +            PK.prescreen(self.router(), ms, srcs, ctx(), {"heimdall"}, {"deepseek"}, store=os.path.join(d, "1.json"),
 810 | +                         cache=cache)
 811 | +            self.assertEqual(sum(len(c[0]) for c in calls), 10)
 812 | +            calls.clear()                                                 # the next build: a new ledger, same cache
 813 | +            a_by, fails, _, _ = PK.prescreen(self.router(), ms, srcs, ctx(), {"heimdall"}, {"deepseek"},
 814 | +                                             store=os.path.join(d, "2.json"), cache=cache)
 815 | +            self.assertEqual((calls, len(a_by)), ([], 10))               # nothing paid for again
 816 | +            with open(os.path.join(d, "2.json")) as f:
 817 | +                self.assertEqual(len(json.load(f)), 10)                   # this build's ledger still records them
 818 | +            changed, srcs2 = self.pool(10, words="is the softest money ever made")
 819 | +            PK.prescreen(self.router(), changed[:2] + ms[2:], dict(srcs, **{k: srcs2[k] for k in ("vm00", "vm01")}),
 820 | +                         ctx(), {"heimdall"}, {"deepseek"}, cache=cache)
 821 | +            self.assertEqual(sorted(sum((c[0] for c in calls), [])), ["m00", "m01"])   # a new text: asked again
 822 | +            calls.clear()
 823 | +            later = E.Context(NOW + timedelta(days=1), REG)
 824 | +            PK.prescreen(self.router(), ms[:3], srcs, later, {"heimdall"}, {"deepseek"}, cache=cache)
 825 | +            self.assertEqual(sorted(sum((c[0] for c in calls), [])), ["m00", "m01", "m02"])   # a new show date
 826 | +            calls.clear()
 827 | +            a_by, _, _, _ = PK.prescreen(self.router(), ms[:3], srcs, ctx(), {"xai"}, {"grok"}, cache=cache)
 828 | +            self.assertEqual(sorted(sum((c[0] for c in calls), [])), ["m00", "m01", "m02"])   # never the writer's
 829 | +            self.assertEqual({a["backend"] for a in a_by.values()}, {"heimdall:deepseek"})     # vendor's verdict
 830 | +
 831 | +    def test_a_failed_batch_is_no_verdict_never_cached_and_says_why(self):
 832 | +        import tempfile
 833 | +        ms, srcs = self.pool(10)
 834 | +        calls = []
 835 | +        self.fake(calls, fail={"m09"})                                    # the miner's best batch fails
 836 | +        with tempfile.TemporaryDirectory() as d:
 837 | +            cache = os.path.join(d, "c.json")
 838 | +            a_by, fails, _, _ = PK.prescreen(self.router(), ms, srcs, ctx(), {"heimdall"}, {"deepseek"}, cache=cache)
 839 | +            self.assertEqual(len(a_by), 2)                                # the other batch (2) only
 840 | +            self.assertEqual(fails["m09"], ["STEP_A_UNAVAILABLE: RuntimeError: the batch reply was out of contract"])
 841 | +            with open(cache) as f:
 842 | +                self.assertEqual(len(json.load(f)), 2)                    # a failure is never remembered
 843 | +            calls.clear()
 844 | +            PK.prescreen(self.router(), ms, srcs, ctx(), {"heimdall"}, {"deepseek"}, cache=cache)
 845 | +            self.assertEqual(len(sum((c[0] for c in calls), [])), 8)      # asked again, the 8 only
 846 | +
 847 | +
 848 | +class TestRuling59HookFirst(unittest.TestCase):
 849 | +    """RULING 59 (11:00): HOOK FIRST. Every cleared, cuttable moment that can open is rated on the hook's own job (ruling
 850 | +    52's question) in one batched call, cached; only a hook rated >= 4 opens; the angles are written FOR the passing
 851 | +    hooks and tried best hook first; with no passing hook the build stops before any line-up, listing the best three."""
 852 | +
 853 | +    def canned(self, *replies):
 854 | +        c = Canned(coherence_verdict=list(replies))
 855 | +        B = lambda v, f: type("B", (), {"vendor": v, "family": f})()
 856 | +        c.backends = {"fake:coherence_verdict": B("fake", "fake")}
 857 | +        return c
 858 | +
 859 | +    def test_one_batched_call_rates_every_hook_and_the_rating_is_derived_and_cached(self):
 860 | +        import tempfile
 861 | +        ms = [pm("a", "A", 12.0), pm("b", "B", 12.0)]
 862 | +        reply = {"hooks": {"a": {"scroll": 5, "alone": 4, "setup": 5, "why": "w a"},
 863 | +                           "b": {"scroll": 5, "alone": 2, "setup": 5, "why": "needs what came before"}}}
 864 | +        with tempfile.TemporaryDirectory() as d:
 865 | +            cache = os.path.join(d, "HOOK_CACHE.json")
 866 | +            c = self.canned(reply)
 867 | +            got, err = PK.hook_ratings(c, ms, ctx(), {"heimdall"}, {"deepseek"}, cache=cache)
 868 | +            self.assertIsNone(err)
 869 | +            self.assertEqual(c.calls, [("coherence_verdict", {"heimdall"}, {"deepseek"})])   # ONE call, off the writers
 870 | +            self.assertEqual((got["a"]["rating"], got["b"]["rating"]), (4, 2))   # the lowest part (ruling 52)
 871 | +            self.assertEqual(got["b"]["why"], "needs what came before")
 872 | +            again, err = PK.hook_ratings(self.canned(), ms, ctx(), {"heimdall"}, {"deepseek"}, cache=cache)
 873 | +            self.assertEqual((err, again["a"]["rating"], again["a"]["cached"]), (None, 4, True))   # no call at all
 874 | +            new = [dict(ms[0], text="Bitcoin is a new text now."), ms[1]]
 875 | +            c = self.canned({"hooks": {"a": {"scroll": 3, "alone": 3, "setup": 3, "why": "w"}}})
 876 | +            got, _ = PK.hook_ratings(c, new, ctx(), {"heimdall"}, {"deepseek"}, cache=cache)
 877 | +            self.assertEqual((len(c.calls), got["a"]["rating"], got["b"]["cached"]), (1, 3, True))   # its new text only
 878 | +
 879 | +    def test_the_prompt_asks_ruling_52s_question_of_each_candidate_alone(self):
 880 | +        ms = [pm("a", "A", 12.0), pm("b", "B", 12.0)]
 881 | +        prompts = []
 882 | +        c = self.canned({"hooks": {k: {"scroll": 5, "alone": 5, "setup": 5, "why": "w"} for k in "ab"}})
 883 | +        call = c.call
 884 | +        c.call = lambda role, prompt, *a, **k: (prompts.append(prompt), call(role, prompt, *a, **k))[1]
 885 | +        PK.hook_ratings(c, ms, ctx(), set(), set())
 886 | +        self.assertIn(PK.HOOK_QUESTION, prompts[0])                       # ONE definition of the hook's job
 887 | +        self.assertIn('CANDIDATE id="a"', prompts[0])
 888 | +        self.assertIn('CANDIDATE id="b"', prompts[0])
 889 | +        self.assertIn("Judge each one ALONE", prompts[0])
 890 | +
 891 | +    def test_a_reply_out_of_contract_is_asked_once_more_then_nothing_is_rated(self):
 892 | +        ms = [pm("a", "A", 12.0)]
 893 | +        ok = {"hooks": {"a": {"scroll": 4, "alone": 4, "setup": 4, "why": "w"}}}
 894 | +        c = self.canned({"hooks": {"a": {"scroll": 9, "alone": 4, "setup": 4, "why": "w"}}}, ok)
 895 | +        got, err = PK.hook_ratings(c, ms, ctx(), set(), set())
 896 | +        self.assertEqual((err, got["a"]["rating"], len(c.calls), len(c.rejected)), (None, 4, 2, 1))
 897 | +        for bad in ({"hooks": {}}, {"hooks": {"a": {"scroll": 4, "alone": 4, "setup": 4}}}, {"x": 1}, "no json"):
 898 | +            got, err = PK.hook_ratings(self.canned(bad, bad), ms, ctx(), set(), set())
 899 | +            self.assertEqual(got, {})
 900 | +            self.assertIn("Error", err)
 901 | +        got, err = PK.hook_ratings(self.canned(), ms, ctx(), set(), set())   # unavailable: no verdict (law L-m)
 902 | +        self.assertEqual(got, {})
 903 | +        self.assertIn("ProviderError", err)
 904 | +
 905 | +    def test_only_a_hook_rated_4_or_more_opens(self):
 906 | +        m = dict(pm("a", "A", 12.0), hook_onset={"pass": True})
 907 | +        self.assertTrue(PK.can_open(m))                                   # not rated yet: as before ruling 59
 908 | +        for rating, ok in ((4, True), (5, True), (3, False), (None, False)):
 909 | +            r = dict(m, hook_rating={"rating": rating})
 910 | +            self.assertEqual(PK.can_open(r), ok, rating)
 911 | +            self.assertEqual(PK.placement(r), "" if ok else " | cannot open (never the hook)")
 912 | +        self.assertFalse(PK.can_open(dict(m, hook_rating=None)))
 913 | +        self.assertFalse(PK.can_open(dict(m, hook_rating={"rating": True})))
 914 | +        self.assertFalse(PK.can_open(dict(m, text="And Bitcoin is money.")))   # the render's hook rule
 915 | +        self.assertFalse(PK.lineup_ok([dict(m, hook_rating={"rating": 3}), pm("x", "B", 14.0), pm("y", "C", 13.0)])[0])
 916 | +
 917 | +    def test_a_line_up_opens_on_its_angles_own_hook_and_never_swaps_it(self):
 918 | +        ms = [dict(pm(k, k.upper(), d), hook_onset={"pass": True}, hook_rating={"rating": 5})
 919 | +              for k, d in (("a", 12.0), ("b", 14.0), ("c", 13.0), ("d", 13.0))]
 920 | +        by = {m["moment_id"]: m for m in ms}
 921 | +        by["b"]["scores"] = dict(by["b"]["scores"], hook_first_2s=99)     # a stronger opener elsewhere
 922 | +        segs = PK.lineup_for(angle(["b", "a", "c", "d"], "a"), by, need_onset=True, hook_only=True)
 923 | +        self.assertEqual(segs[0]["moment_id"], "a")
 924 | +        low = dict(by, a=dict(by["a"], hook_rating={"rating": 3}))
 925 | +        self.assertIsNone(PK.lineup_for(angle(["b", "a", "c", "d"], "a"), low, need_onset=True, hook_only=True))
 926 | +        self.assertEqual(PK.lineup_for(angle(["b", "a", "c", "d"], "a"), low, need_onset=True)[0]["moment_id"], "b")
 927 | +        self.assertEqual(PK.swap_lineup(segs, {"a"}, by, keep_hook=True), (None, None))
 928 | +        new, swaps = PK.swap_lineup(segs, {segs[1]["moment_id"]}, by, keep_hook=True)
 929 | +        self.assertEqual(new[0]["moment_id"], "a")
 930 | +        with self.assertRaises(ValueError):
 931 | +            PK.check_angles({"angles": [angle(["b", "a", "c"], "b")]}, by, hooks={"a"})
 932 | +        self.assertEqual(len(PK.check_angles({"angles": [angle(["a", "b", "c"], "a")]}, by, hooks={"a"})), 1)
 933 | +
 934 | +    def test_no_hook_in_the_pool_stops_before_the_second_screen_and_lists_the_best_three(self):
 935 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0)]
 936 | +        rig = Rig(ms, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None],
 937 | +                  hooks={"h": (3, 4, 4), "x": (2, 5, 5), "y": (4, 3, 4), "z": (1, 1, 1)})
 938 | +        out = rig.run()
 939 | +        self.assertIsNone(out["package"])
 940 | +        self.assertTrue(out["why_none"].startswith("no hook in the pool (ruling 59 d): none of the 4 moments"))
 941 | +        self.assertEqual([b["moment_id"] for b in out["hook_pool"]["best"]], ["h", "y", "x"])
 942 | +        self.assertEqual([b["rating"] for b in out["hook_pool"]["best"]], [3, 3, 2])
 943 | +        self.assertIn("A 3 (scroll 3, alone 4, setup 4): why h", out["why_none"])
 944 | +        self.assertEqual(rig.medley_calls, [])
 945 | +        self.assertNotIn("angle_write", rig.events)                     # no angle, no line-up paid for
 946 | +        self.assertEqual(len(rig.screens), 1)                            # and no second screen
 947 | +        rig = Rig(ms, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], hook_err="ProviderError: down")
 948 | +        out = rig.run()
 949 | +        self.assertIn("not rated: ProviderError: down", out["why_none"])
 950 | +        self.assertEqual(rig.medley_calls, [])
 951 | +
 952 | +    def test_the_writer_is_given_the_passing_hooks_and_the_best_hook_goes_first(self):
 953 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0)]
 954 | +        rig = Rig(ms, [["h", "x", "y", "z"], ["x", "h", "y", "z"]], [(True, [], None, Rig.LINE)], [None],
 955 | +                  hooks={"h": (4, 4, 4), "x": (5, 5, 5), "y": (3, 3, 3), "z": (3, 4, 5)})
 956 | +        out = rig.run()
 957 | +        p = next(p for r, p in rig.prompts if r == "angle_write")
 958 | +        self.assertIn("THE HOOKS", p)
 959 | +        self.assertLess(p.index("id=x | rated 5"), p.index("id=h | rated 4"))    # best first
 960 | +        self.assertNotIn("id=y | rated", p)
 961 | +        self.assertIn("id=y | C | 13.0 s | cannot open (never the hook) | ", p)
 962 | +        self.assertIn("up to 1 for EACH hook above, at most 3 in all", p)
 963 | +        self.assertEqual(rig.medley_calls[0][0], "x")                   # the x angle, though the writer gave it second
 964 | +        self.assertEqual(out["hook_pool"]["passing"], ["x", "h"])
 965 | +        self.assertIsNotNone(out["package"])
 966 | +
 967 | +    def test_an_angle_not_written_for_a_passing_hook_is_out_of_contract(self):
 968 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0)]
 969 | +        rig = Rig(ms, ["y", "h", "x", "z"], [(True, [], None, Rig.LINE)], [None], hooks={"y": (3, 3, 3)})
 970 | +        out = rig.run()
 971 | +        self.assertIsNone(out["package"])
 972 | +        self.assertIn("is not one of THE HOOKS", out["why_none"])           # the first reply, rejected
 973 | +        self.assertEqual((len(rig.router.rejected), sum(r == "angle_write" for r, _ in rig.prompts)), (1, 2))
 974 | +        self.assertEqual(rig.medley_calls, [])
 975 | +
 976 | +
 977 |  class TestOrder0622StepAFromBothVendors(unittest.TestCase):
 978 |      """ORDER 06:22: 45, step A from BOTH vendors on every cuttable clip before the angle step; 44, a failed re-screen
 979 |      after a write swaps out that clip only, and the line-up carries on."""
 980 | @@ -1089,7 +1340,7 @@ class TestOrder0622StepAFromBothVendors(unittest.TestCase):
 981 |                  "z": {"backend": "heimdall:deepseek"}}
 982 |          seen = []
 983 |  
 984 | -        def fake(router_, chunk, sources, ctx_, wv, wf, n=None, store=None, log=print):
 985 | +        def fake(router_, chunk, sources, ctx_, wv, wf, n=None, store=None, log=print, cache=None):
 986 |              seen.append((sorted(wv), [m["moment_id"] for m in chunk]))
 987 |              name = "heimdall:deepseek"          # off xai for h and x; for z (first verdict heimdall) the SAME vendor
 988 |              return {m["moment_id"]: {"backend": name} for m in chunk}, {m["moment_id"]: [] for m in chunk}, set(), set()
 989 | @@ -1323,13 +1574,13 @@ class TestRuling41Search(unittest.TestCase):
 990 |              if segs is not None:
 991 |                  self.assertEqual(PK.lineup_ok(segs), (True, "ok"), order)
 992 |  
 993 | -    def test_the_build_swaps_a_low_rated_hook_and_stops_at_8_line_ups(self):
 994 | +    def test_a_low_rated_hook_is_never_swapped_and_the_search_stops_at_8_line_ups(self):
 995 |          ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0), pm("g", "E", 12.0)]
 996 | -        rig = Rig(ms, ["h", "x", "y", "z"], [(False, [], {"hook": 3}, Rig.LINE), (True, [], None, Rig.LINE)], [None])
 997 | +        rig = Rig(ms, [["h", "x", "y", "z"], ["g", "x", "y", "z"]],
 998 | +                  [(False, [], {"hook": 3}, Rig.LINE), (True, [], None, Rig.LINE)], [None])
 999 |          out = rig.run()
1000 | -        self.assertEqual(rig.medley_calls[0][0], "h")
1001 | -        self.assertNotEqual(rig.medley_calls[1][0], "h")                    # the hook rated 3 was swapped
1002 | -        self.assertIn("swapped", out["tried"][0]["why"])
1003 | +        self.assertEqual([c[0] for c in rig.medley_calls], ["h", "g"])     # ruling 59 (c): h's angle ends, g's next
1004 | +        self.assertIn("written for this hook (ruling 59 c)", out["tried"][0]["why"])
1005 |          self.assertIsNotNone(out["package"])
1006 |          many = [pm(c, c.upper(), 13.0) for c in "abcdefghijklmnop"]
1007 |          fails = [(False, [], {"clip_01": 2}, Rig.LINE)] * 12
1008 | @@ -1337,7 +1588,7 @@ class TestRuling41Search(unittest.TestCase):
1009 |          out = rig.run()
1010 |          self.assertEqual(len(rig.medley_calls), PK.LINEUPS_PER_BUILD)       # 8, over every angle
1011 |          self.assertEqual(out["search"]["lineups"], 8)
1012 | -
1013 | +        self.assertTrue(all(c[0] in ("a", "i") for c in rig.medley_calls))  # each line-up keeps its angle's hook
1014 |  
1015 |  class TestRuling37QuestionHook(unittest.TestCase):
1016 |      """Ruling 37: a clip ending on a question may be the HOOK only; the clips-alone verdict judges the join after it,
1017 | 
```

---

You are auditing a diff on branch pp-selectid (Protocol Pulse: the L-y MEDLEY, a hook + 2-4 clips from YouTube
channels, sealed in a pin that the integrator renders). Your role: a strict reviewer of a screening and selection change.

Only state what you can verify from the diff provided. If uncertain, say so; do not guess.

Background (static):
- A build turns the moments of a 72 h window into "usable" moments. Step A (law L-s) then judges each moment's own
  context with a model: a verdict per moment, never from the angle writer's vendor or family. Until now step A
  screened only the PRESCREEN_N = 24 best (distinct channels first), and its verdicts were stored only in the build's
  own ledger.
- After step A:
  - L-v 2 + CUTTABLE (a second recognition pass);
  - the hook onset rule G17a (a moment may OPEN a medley only with genuine quiet before its first onset);
  - the second vendor's step A on every cuttable clip (order 06:22 item 45);
  - ONE angle-writer call (up to 3 angles, each a sentence + clip ids in play order + a "hook");
  - line-ups (lineup_for, up to 8 per build, ruling 41), each judged on the clips ALONE by a blind verdict
    (medley(): a through-line, ruling 52's three-part hook rating, a rating per clip, the joins);
  - then writes and gates.
- Ruling 41: a clips-alone failure swaps the weak segments (swap_lineup), the hook included.
- Ruling 52's hook question (HOOK_QUESTION): scroll / alone / setup, each 1-5. The rating is DERIVED as the lowest
  part, and the bar is 4 (COHERENCE_MIN).
- The router: role "coherence_verdict" (the blind quality verdicts), role "angle_write" (Heimdall first, Grok on its
  failure), role "context_verdict" (step A). A call that fails is never a verdict (law L-m); fail closed (law L-j).

The orders this diff implements (ORCHESTRATOR RULINGS 58 and 59, 11:00 ET Nov 13, verbatim):
58. "PRESCREEN_N = 24 is retired: screen EVERY candidate at step A (about 150 at 72 h, about $0.40 reported), highest
miner score first, verdicts cached by moment id + text sha so a moment is paid for once, not once per build."
59. "HOOK FIRST. Every recent line-up died on its hook (rated 1-2 on its own job) after the money was spent judging the
whole line-up. Change the order:
(a) once the pool is screened, ask the hook question of ruling 52 about EVERY cleared, cuttable moment that can open
(one batched call; cache it);
(b) only moments rated >= 4 as a hook may open a line-up;
(c) line-ups are built AROUND a passing hook, best hook first, the angle writer told which hook it is writing for;
(d) if no moment in the pool rates >= 4 as a hook, the build stops there with 'no hook in the pool', lists the three
best with their ratings and reasons, and spends nothing on line-ups."

The change (pipeline/package.py, tests/package/proof_ledger.py, tests/package/test_medley.py):

58:
1. PRESCREEN_N = None: prescreen screens every usable moment, by the miner's rank_score, best first. A number keeps the
   old cap (the re-screens pass their own n).
2. The step-A batches (8 each) run in parallel (PRESCREEN_WORKERS = 6). Each batch keeps the seed of its place in the
   queue, as before.
3. A verdict cache shared by every build (`cache`). The key is the moment id, the sha256 of its text, the sha256 of
   the exact context step A reads, and the step-A prompt version. The context covers the window, title, channel,
   publish time and the show date, so time words are judged again on a new show date. The value is {back-end: item}.
   - A cached item is reused only from a back-end off the writers' vendor and family.
   - Only parsed verdicts are stored; a failed batch is never cached. Its reason now carries the exception message,
     not only its type.
   - The file is merged under a lock: read again, update, .tmp, then rename.
4. second_screen and the re-screen after a write use the same cache.

59:
5. hook_ratings(): ruling 52's HOOK_QUESTION, verbatim, asked of every moment that can open, in ONE batched call
   (role coherence_verdict, off the writers).
   - The prompt is HOOKS_PROMPT: each candidate is judged alone, as the opener.
   - The reply contract: exactly the asked ids, each {scroll, alone, setup} as ints 1-5 plus "why".
   - The rating is derived as the lowest part.
   - One re-ask on a reply out of contract. An unavailable call or the spend guard rates nothing.
   - Cached by the moment id + text sha + the question's version.
6. can_open(m): hook-eligible, G17a passed, a first word the render's STAND_ALONE takes for a hook
   (stand_alone.opener). Once build() has set "hook_rating" on every cleared moment, it also needs a rating
   >= HOOK_MIN (4); an unrated moment never opens. lineup_for (with need_onset), lineup_ok, swap_lineup's hook places
   and placement() all use it.
7. build():
   - After L-v 2 + CUTTABLE + G17a and the trimmed-cut check, it rates every cleared moment that can open, first
     clearing any rating carried in.
   - It sets hook_rating on every cleared moment.
   - It records out["hook_pool"]: can_open, rated, passing (best first), the best three, and the error.
   - With no passing hook it returns 'no hook in the pool (ruling 59 d)'. The three best appear in the why, with
     their parts and reasons. The second screen, the angle call and any line-up are never reached.
   - After the second screen it re-checks that a passing hook is still cleared.
8. The angle prompt carries THE HOOKS: the passing hooks, best first, each with its rating and reason. The writer gives
   up to `per` = max(1, 3 // the number of passing hooks) angles for EACH hook, at most 3 in all, each written FOR its
   hook. check_angles(..., hooks=) rejects an angle whose hook is not one of them; that is out of contract, so one
   re-ask. why_none keeps every reason.
9. The angles are tried best hook first (rating, then the sum of its parts), then by ruling 57's freshness, then in the
   writer's order (a stable sort).
10. Every line-up opens on its angle's own hook (lineup_for / pool_fill hook_only=True). A hook the clips-alone verdict
    rates low is never swapped (swap_lineup keep_hook=True; weak.discard(hook)). The weak clips after it are swapped
    as before. When only the hook is weak, the angle ends and the next angle (another hook) is tried.
11. proof_ledger passes tests/package/proof/STEP_A_CACHE.json and HOOK_CACHE.json.
12. Tests:
    - new: 3 for ruling 58 and 8 for ruling 59;
    - rewritten for 59: the G17a test (a hook without the quiet is never one of THE HOOKS) and ruling 41's hook-swap
      test (now: never swapped; the next hook's angle is tried);
    - the test Rig rates hooks the way the real function answers.
    test_medley 105 OK; all 11 suites OK.

Stated readings (say so if you read the rulings differently):
- K1 (58): the cache key adds the context's sha to "moment id + text sha". Step A judges the context, and a new show
  date re-judges time words (law L-v 3), so a moment is paid for once per context and show date.
- K2 (59 a): "once the pool is screened" is read as after step A, L-v 2 + CUTTABLE, G17a and the trimmed cut, and
  BEFORE the second vendor's step A. With no passing hook, the second screen's cost is not spent either. A passing
  hook that then fails the second screen is gone, and the build stops if none remains.
- K3 (59 c): one angle call carries all passing hooks. Each angle is written for exactly one of them, and the build
  tries them best hook first. It does not make one writer call per hook.
- K4 (59 c): "built AROUND a passing hook": the hook is fixed for its angle's line-ups and never swapped (this
  narrows ruling 41's swap to the clips). A weak hook in context ends the angle.
- K5: the hook rating gate lives on the moment ("hook_rating", set by build()). A moment without the key (unit tests,
  any caller before ruling 59) is judged as before.
- K6: ruling 57's "newest clips" now ranks after the hook's rating across angles.

Check in particular:
- every fail-closed path (an unrated hook, a failed rating call, a failed step-A batch, a corrupt cache file);
- the cache keys and that a cached verdict is never from the writers' vendor;
- that no unrated or low-rated moment can open by any path: lineup_for, pool_fill, swap_lineup, lineup_ok, the
  no-voice path;
- that (d) spends nothing on line-ups;
- the thread safety of the parallel batches and the cache writes;
- the angle contract;
- whether any old caller of prescreen / lineup_for / swap_lineup / check_angles changes behaviour unintentionally.

Answer with P0/P1/P2 findings (file:line, concrete scenario), then "SHIP: yes / no / yes with conditions".


---

## CYCLE 2 INSTRUCTIONS

You've now seen what the other models said. This is your final review.

1. WHAT DID THEY CATCH THAT YOU MISSED?
   Review their findings. Be honest about what you overlooked.

2. WHERE DO YOU AGREE OR DISAGREE?
   For each of their key findings: agree / disagree / partially agree + why.

3. NEW FINDINGS FROM THIS REVIEW
   Anything the combined analysis revealed that nobody caught in Cycle 1?

4. REVISED SCORES
   Update your scores from Cycle 1. Did anything change your assessment?
   | Subsystem | Cycle 1 | Cycle 2 | Why changed |

5. FINAL PRIORITY LIST
   Your definitive list of what must change before this ships.
   P0 CRITICAL | P1 HIGH | P2 MEDIUM — cite file and line numbers.

6. THE SINGLE HIGHEST-LEVERAGE CHANGE
   After seeing everything — one sentence. What matters most?

7. PRODUCTION READY?
   Yes / No / Yes with conditions. State your conditions precisely.
