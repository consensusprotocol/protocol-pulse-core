# qwen3.8-27b (qwen/qwen3.8-27b) 112 s finish=stop usage in 47164 / out 6385 usd_reported=0.006746 usd~0.237 (upper-bound price)

I will begin by analyzing the code changes against the provided "Governing Laws" and the specific requirements of Ruling 115.

### 1. Analysis of `pipeline/hook_bar.py`

**Logic Check:**
- `floors_from`: Calculates the minimum value for each part (`scroll`, `alone`, `setup`) across approved hooks. Enforces `FLOOR_MIN = 3`.
- `load`: Verifies SHA256 integrity.
- `bar`: Checks validity (rater, question version, seed, asking, age < 24h).
- `passes`: Checks if a specific rating record meets the floors and was rated by the correct backend.

**Potential Issue 1: Type Checking in `floors_from`**
```python
if not vals or any(type(v) is not int for v in vals):
    raise ValueError(...)
```
This correctly rejects floats and booleans (since `type(True) is not int` is `False` in Python? No, `type(True) is int` is `False` because `bool` is a subclass of `int` but `type(True)` is `bool`). Wait, `isinstance(True, int)` is `True`, but `type(True) is int` is `False`. So `type(v) is not int` will be `True` for booleans, causing a `ValueError`. This is good, strict fail-closed behavior.

**Potential Issue 2: `passes` Logic**
```python
short = [f"{p} {rec.get(p)} < {live['floors'][p]}" for p in PARTS
         if type(rec.get(p)) is not int or rec[p] < live['floors'][p]]
```
If `rec.get(p)` is `None` (missing key), `type(None) is not int` is `True`, so it adds to `short`. This is correct fail-closed.
If `rec.get(p)` is a float (e.g., 4.0), `type(4.0) is not int` is `True`, so it fails. This is consistent with `floors_from`.

### 2. Analysis of `pipeline/package.py`

**Change: `hook_ratings`**
- Previously: One batched call for all candidates.
- Now: One call per candidate (`for m in todo`).
- `HOOK_VERSION` is updated to include `HOOK_ASKING`. This invalidates old caches.
- Error handling: If one candidate fails, `err` is set, but the loop continues for other candidates. This matches the requirement "a candidate whose chain is spent has no rating... the others are still asked".

**Change: `hook_own`**
- Returns `passes` based on `hook_bar.passes`.
- `rating` is still `min(scroll, alone)` for ordering.
- `short` contains the reason for failure.

**Change: `_can_open`**
- Uses `own["passes"]` instead of `own["rating"] >= HOOK_MIN`.
- This correctly implements the "calibrated bar" logic.

**Change: `medley` and `coherence`**
- The hook's rating is excluded from the `min(...) >= COHERENCE_MIN` check.
- `ok = own is not None and own["passes"] and _line_ok(v["through_line"]) and min([x for lb, x in v["clips"].items() if lb != labs[0]] + [v["vo_point"]]) >= COHERENCE_MIN`
- This ensures the hook passes its *own* bar (floors), while clips pass the *coherence* bar (min 4). This aligns with the "reading of 'nothing else changes'" note in the prompt.

**Change: `last_clip_only`**
- Checks `own["passes"]` for the hook.
- Checks `x < COHERENCE_MIN` for clips (excluding the hook).
- This is consistent.

### 3. Analysis of `pipeline/spotlight.py`

**Change: `inventory`**
- `rows["hook_own"]` uses `own["passes"]`.
- Includes `setup` and `bar` in the row data.

**Change: `build`**
- Filters moments where `own["passes"]` is True.
- Logs the calibrated bar text.

### 4. Analysis of `pipeline/providers.py`

**Change: Shadow Logic**
- `_shadow_of` now accepts `kind`.
- `_shadow_ask` uses `kind` to determine the shadow chain.
- `call` passes `kind` to `_shadow_ask`.
- This allows `coherence_verdict:hook` to have a specific shadow (qwen) while other `coherence_verdict` calls use the general shadow (Grok).

### 5. Analysis of `pipeline/model_providers.json`

- `coherence_verdict:hook` is set to `["xai:grok-4.20-0309-reasoning"]` in all routings.
- This ensures only Grok rates hooks.

### 6. Analysis of Tests

**`tests/package/conftest.py`**
- Patches `package._live_bar` to return a fixed rig bar.
- This isolates tests from the live calibration file.

**`tests/package/test_hook_bar.py`**
- Tests `floors_from`, `load`, `bar`, `passes`, `add_example`.
- Verifies SHA256 integrity.
- Verifies staleness.
- Verifies that a hand-edit breaks the seal.

**`tests/package/test_medley.py`**
- Updates `SEGS` to include `backend` in `hook_rating`.
- Tests that a hook with `scroll: 3, alone: 4, setup: 3` passes (meets floors).
- Tests that a hook with `scroll: 2` fails.
- Tests that a hook rated by a different backend fails.

**`tests/package/test_spotlight.py`**
- Updates `moment` helper to include `backend`.
- Tests `inventory` row for `hook_own`.
- Tests `build` filtering.

**`tests/providers/test_providers.py`**
- Tests shadow routing for `kind="hook"`.

### 7. Critical Review & Findings

**Finding 1: [P1] `hook_bar.py` `bar()` function does not validate `floors` structure before use.**
In `bar()`:
```python
fl = {p: int(cal["floors"][p]) for p in PARTS}
```
If `cal["floors"]` is missing a key (e.g., `setup`), this raises `KeyError`, which is caught by the `except (KeyError, TypeError, ValueError)` block. This is fine.
However, if `cal["floors"]` contains a value that is not an integer (e.g., a string "3"), `int("3")` works, but `int("abc")` raises `ValueError`. This is caught.
What if `cal["floors"]` is `None`? `int(None)` raises `TypeError`. Caught.
This seems robust.

**Finding 2: [P2] `package.py` `hook_ratings` error handling.**
```python
new, err = {}, None
for m in todo:
    ...
    try:
        ...
    except ... as e:
        err = err or f"{type(e).__name__}: {str(e)[:200]}"
        continue
    ...
return out, err
```
If the *first* candidate fails, `err` is set. If the *second* candidate succeeds, `out` contains the second candidate's rating. The function returns `out` (with partial data) and `err` (the first error).
The caller `build()`:
```python
rated, hook_err = hook_ratings(...)
...
for mid, m in cleared.items():
    m["hook_rating"] = rated.get(mid) or {"rating": None, "why": ...}
```
This correctly handles partial failures: rated candidates get their ratings, unrated ones get `None`. The `hook_err` is logged. This is correct fail-closed behavior for the unrated ones.

**Finding 3: [P1] `hook_bar.py` `passes()` does not check if `live` is `None` before accessing `live['floors']`.**
```python
def passes(rec, live):
    if live is None:
        return False, "no valid hook calibration"
    ...
```
It does check. This is fine.

**Finding 4: [P2] `package.py` `hook_own` uses `_live_bar()` which caches based on `mtime`.**
```python
def _live_bar():
    import hook_bar as HB
    try:
        k = os.stat(HB.PATH).st_mtime_ns
    except OSError:
        k = None
    if k not in _LIVE:
        _LIVE.clear()
        _LIVE[k] = hook_live_bar()
    return _LIVE[k]
```
If the file is deleted, `os.stat` raises `OSError`, `k` is `None`. If `None` is not in `_LIVE`, it clears and calls `hook_live_bar()`. `hook_live_bar` calls `HB.bar(None, ...)`. `HB.bar` calls `load()`. `load` catches `OSError` and returns `(None, why)`. So `_LIVE[None]` becomes `(None, why)`.
If the file is restored, `mtime` changes, `k` is new, cache is cleared, new bar is loaded.
This logic is sound.

**Finding 5: [P1] `hook_calibration.json` `measured_at` is in the future relative to the "Generated" date?**
Generated: 2026-11-15 14:12 UTC.
`measured_at`: 2026-11-15T18:07:52+00:00.
The calibration was measured *after* the code audit package was generated?
The prompt says: "Generated: 2026-11-15 14:12 UTC".
The calibration file says: `measured_at: 2026-11-15T18:07:52+00:00`.
This implies the calibration was run at 18:07, but the audit package was generated at 14:12.
However, the audit package *includes* the calibration file. This is a temporal inconsistency in the metadata of the audit package itself, or the calibration was pre-staged.
More importantly, `bar()` checks:
```python
if (now or datetime.now(timezone.utc)) - at > timedelta(hours=VALID_H):
```
If `now` is the current time (2026-11-15 14:12 or later), and `at` is 18:07, then `now - at` is negative.
`timedelta(hours=24)` is positive.
`negative > positive` is `False`.
So the calibration is considered valid (not stale) even if it was measured in the future relative to the check time?
Wait, `datetime.now()` is the *current* time. If the code runs at 14:12, and `measured_at` is 18:07, the difference is -4 hours.
The check is `if (now - at) > 24h`.
-4h > 24h is False. So it passes the staleness check.
But logically, a calibration measured in the future is suspicious.
However, the prompt says "Generated: 2026-11-15 14:12 UTC". This is the timestamp of the *audit package*. The code inside might be run later.
If the code is run at 19:00, `now - at` is 1 hour. Valid.
If the code is run at 14:00, `now - at` is -4 hours. Valid.
This allows a calibration with a future timestamp to be used. This is a minor security/logic flaw if an attacker can set `measured_at` to the future to bypass the 24h limit indefinitely?
No, because `measured_at` is part of the body, and the SHA256 covers it. But the *value* itself can be in the future.
The law says "valid ... for 24 h after it was measured".
If I measure at 18:00, it is valid until 18:00 next day.
If I set `measured_at` to 2026-11-16 18:00, it is valid until 2026-11-17 18:00.
This effectively extends the validity period by allowing future timestamps.
**Severity: [P2]**. It violates the spirit of "24h after measured" by allowing pre-dating.

**Finding 6: [P1] `hook_bar.py` `floors_from` does not verify that the approved hooks are actually from the source file.**
The function just takes a list of dicts. The caller (`test_hook_bar.py` `TestTheLiveCalibration`) verifies this against `ALONE_TEST.json`.
But `hook_bar.py` itself does not enforce this. This is acceptable as `hook_bar.py` is a generic utility.

**Finding 7: [P1] `package.py` `hook_ratings` uses `HOOKS_PROMPT.format(hooks=cand, keys=keys)`.**
`cand` is a single candidate string.
`keys` is a single key string.
The prompt template `HOOKS_PROMPT` likely expects a list of candidates and keys.
Let's check `HOOKS_PROMPT` definition (not in diff, but referenced).
In the old code:
```python
cands = "\n".join(...)
keys = ", ".join(...)
P.call_parsed(..., HOOKS_PROMPT.format(hooks=cands, keys=keys), ...)
```
In the new code:
```python
cand = f'CANDIDATE id="{mid}" ...'
keys = f'"{mid}": ...'
P.call_parsed(..., HOOKS_PROMPT.format(hooks=cand, keys=keys), ...)
```
If `HOOKS_PROMPT` is designed for multiple candidates (e.g., "Here are the candidates: {hooks}"), passing a single one should still work syntactically.
However, the `parse` function:
```python
def parse(text, ids):
    v = json.loads(text.strip())
    h = v["hooks"] if isinstance(v, dict) and set(v) == {"hooks"} else None
    if not isinstance(h, dict) or set(h) != set(ids) or ...
```
`ids` is `(mid,)` (a tuple with one element).
`set(ids)` is `{mid}`.
The model must return `{"hooks": {mid: {...}}}`.
This is consistent.

**Finding 8: [P1] `providers.py` `_shadow_ask` thread safety.**
`_shadow_ask` runs in a thread. It accesses `self.chains` and `self.shadow`.
`self.chains.setdefault(own, [name])` is not atomic in Python if multiple threads run simultaneously.
However, `hook_ratings` calls `P.call_parsed` sequentially in a loop.
`P.call_parsed` calls `self.call`.
`self.call` calls `self._shadow_ask` (which starts a thread).
The main thread continues to the next candidate.
The shadow threads run in the background.
If two shadow threads try to `setdefault` on the same key `own` (which is unique per role:kind), there is no race condition on the *same* key.
Different candidates have different `mid`s, but the `own` key is `shadow86:coherence_verdict:hook`.
So all hook shadows use the same chain key.
`setdefault` is safe for concurrent reads/writes of *different* keys, but here it's the same key.
`dict.setdefault` is atomic in CPython due to the GIL, but logically, if two threads call it, one might overwrite the other?
No, `setdefault` only sets if the key is *not* present.
If the key is present, it does nothing.
So it's safe.

**Finding 9: [P1] `hook_bar.py` `add_example` does not re-seal the file if the example list grows too large?**
It just appends and writes. No limit. This is fine.

**Finding 10: [P1] `package.py` `hook_own` returns `short` as `why if live is None else short`.**
```python
ok, short = HB.passes(dict(parts, backend=r.get("backend")), live)
return dict(..., short=why if live is None else short, ...)
```
If `live` is `None`, `HB.passes` returns `(False, "no valid hook calibration")`.
So `short` is `"no valid hook calibration"`.
But the code uses `why` (from `_live_bar()`) if `live` is `None`.
`_live_bar()` returns `(live, why)`.
If `live` is `None`, `why` is the specific reason (e.g., "stale", "sha mismatch").
So `short` will be the specific reason. This is better.
If `live` is not `None`, `short` is the specific part failures (e.g., "scroll 2 < 3").
This is correct.

**Finding 11: [P1] `spotlight.py` `build` uses `P.hook_own(m)` which calls `_live_bar()`.**
`_live_bar()` is cached in `package._LIVE`.
`spotlight.py` imports `package as P`.
So it uses the same cache. This is consistent.

**Finding 12: [P1] `tests/package/conftest.py` patches `PK._live_bar`.**
```python
monkeypatch.setattr(PK, "_live_bar", lambda: (bar, None))
```
This replaces the function.
`hook_own` calls `_live_bar()`.
`hook_bar_mark` calls `_live_bar()`.
This works.
However, `hook_bar.py` functions (`bar`, `load`) are *not* patched.
`test_hook_bar.py` tests `hook_bar.py` directly.
`test_medley.py` tests `package.py` logic.
This separation is good.

**Finding 13: [P1] `hook_calibration.json` `sha256` verification.**
The file contains `sha256`.
`load()` verifies it.
The test `test_written_sealed_and_read_back_as_the_live_bar` verifies it.
This is robust.

**Finding 14: [P1] `package.py` `build` logs `HB.text(live)`.**
If `live` is `None`, `HB.text(None)` returns `"no valid hook calibration: no hook passes"`.
This is logged.
This satisfies "the build says why in one line".

**Finding 15: [P1] `providers.py` `call` method signature.**
The diff shows `call` being modified to pass `kind`.
```python
def call(self, role, prompt, max_tokens, seed, system=None, kind=None):
```
Wait, the diff doesn't show the `call` definition, only the internal usage.
Line 654: `r = self.call(own, prompt, max_tokens, seed, system=system)`
Line 674: `out = Reply(...)`
The `call` method must accept `kind` or the `own` chain name handles it.
`own` is `shadow86:coherence_verdict:hook`.
`self.call(own, ...)` uses the chain name `own`.
The `kind` parameter in `call` is used to look up the shadow.
The diff shows `call` being called with `kind` in `hook_ratings`:
```python
P.call_parsed(router, "coherence_verdict", ..., kind="hook")
```
`call_parsed` likely passes `kind` to `call`.
This is consistent.

**Finding 16: [P1] `hook_bar.py` `bar()` `rater` check.**
```python
for k, want in (("rater", rater), ...):
    if k == "rater" and want is None:
        continue
    if cal.get(k) != want:
        return None, ...
```
If `rater` is `None` (not specified), it skips the check.
`hook_live_bar()` calls `HB.bar(None, HOOK_VERSION, HOOK_SEED)`.
So `rater` is `None`.
The check is skipped.
But `passes()` checks:
```python
if rec.get("backend") != live["rater"]:
```
`live["rater"]` comes from `cal["rater"]`.
So the calibration file *must* have a `rater`.
If `cal["rater"]` is missing, `live["rater"]` is `None`.
Then `rec.get("backend") != None` is `True` (assuming backend is a string).
So it fails.
This is fail-closed.

**Finding 17: [P1] `hook_calibration.json` `rater` is `"xai:grok-4.20-0309-reasoning"`.**
`model_providers.json` `coherence_verdict:hook` is `["xai:grok-4.20-0309-reasoning"]`.
So the backend name matches.

**Finding 18: [P1] `package.py` `hook_ratings` `max_tokens`.**
Old: `600 + 150 * len(ids)`.
New: `600 + 150` (since `len(ids)` is 1).
This is consistent with "one call per candidate".

**Finding 19: [P1] `tests/package/test_hook_bar.py` `TestTheLiveCalibration`.**
```python
def test_its_floors_are_its_sources_lowest_parts(self):
    ...
    grok = dict(src["models"][c["rater"]], **src["retries"])
    self.assertEqual(sorted(a["ref"] for a in c["approved"]), sorted(grok))
```
This verifies that the approved hooks in the calibration file match the source file.
This is a strong test.

**Finding 20: [P1] `hook_bar.py` `VALID_H = 24.0`.**
The law says "once a day".
24 hours is correct.

**Finding 21: [P1] `package.py` `HOOK_SEED = 7`.**
The law says "production's seed".
The calibration file has `"seed": 7`.
This matches.

**Finding 22: [P1] `package.py` `HOOK_VERSION`.**
`HOOK_VERSION = hashlib.sha256((HOOKS_PROMPT + "\n" + HOOK_ASKING).encode()).hexdigest()[:12]`
The calibration file has `"question_version": "bfdf74078d5e"`.
The test `test_it_is_for_productions_question_seed_and_hook_list` verifies:
```python
self.assertEqual((c["question_version"], c["seed"]), (PK.HOOK_VERSION, PK.HOOK_SEED))
```
This ensures the version in the file matches the code.

**Finding 23: [P1] `providers.py` `_shadow_of` logic.**
```python
return (self.shadow.get(f"{role}:{kind}") if kind else None) or self.shadow.get(role) or self.shadow.get("*")
```
If `kind` is "hook", it looks for `coherence_verdict:hook`.
If not found, it looks for `coherence_verdict`.
If not found, it looks for `*`.
This is correct fallback logic.

**Finding 24: [P1] `tests/providers/test_providers.py` `test_ruling_115...`.**
```python
r = P.Router(..., shadow={"*": "xai:grok", "coherence_verdict:hook": "heimdall:qwen"}, ...)
...
self.assertEqual(r._shadow_of("coherence_verdict", "hook"), "heimdall:qwen")
self.assertEqual(r._shadow_of("coherence_verdict", "coherence"), "xai:grok")
```
This verifies the shadow lookup.

**Finding 25: [P1] `hook_bar.py` `add_example` `now` parameter.**
```python
"at": (now or datetime.now(timezone.utc)).isoformat(timespec="seconds")
```
This allows injecting a specific time for testing.

**Finding 26: [P1] `package.py` `hook_bar_mark` `ruling` field.**
```python
return {"note": HB.NOTE, "bar": HB.text(live), "floors": ..., "calibration_sha256": ..., "ruling": "115"}
```
This is included in the pin.

**Finding 27: [P1] `package_pin.py` `to_pin`.**
```python
**({"hook_bar": pk["hook_bar"]} if pk.get("hook_bar") else {}),
```
This adds the mark to the pin.
The comment says "outside the seal".
`package_pin.seal` does not include `hook_bar`.
This is correct.

**Finding 28: [P1] `spotlight.py` `build` `pk["hook_bar"] = P.hook_bar_mark()`.**
This adds the mark to the spotlight package.

**Finding 29: [P1] `package.py` `build` `out["package"]["hook_bar"] = hook_bar_mark()`.**
This adds the mark to the medley package.

**Finding 30: [P1] `hook_bar.py` `text` function.**
```python
return (f"the calibrated hook bar (ruling 115): scroll >= {f['scroll']}, alone >= {f['alone']}, setup >= "
        f"{f['setup']}, on {live['rater']} asked alone at seed {live['seed']} (calibration {live['sha256'][:12]})")
```
This is a clear, human-readable line.

### Conclusion

The code implements Ruling 115 correctly.
- The hook bar is defined by the calibration file.
- The calibration file is sealed and verified.
- The hook is rated alone by Grok.
- The hook passes if all parts meet the floors.
- The mark is added to the package and pin.
- The shadow logic is updated.
- The tests are comprehensive.

The only minor issue is the future timestamp in `measured_at` allowing potential pre-dating, but this is a [P2] nit given the SHA256 seal and the fact that the calibration is generated by the system.

One [P1] finding:
In `hook_bar.py` `bar()`, the check `if (now or datetime.now(timezone.utc)) - at > timedelta(hours=VALID_H)` allows `at` to be in the future. If `at` is 1 day in the future, `now - at` is -1 day. `-1 day > 24 hours` is False. So it is valid.
This means a calibration can be "pre-dated" to extend its validity.
While the SHA256 prevents tampering with the *content*, the *timestamp* is part of the content.
If the system generates the calibration, it uses `datetime.now()`.
But if a user manually creates a calibration file with a future `measured_at`, it will be accepted.
The law says "valid ... for 24 h after it was measured".
A future measurement is not "after it was measured" in the past.
This is a logical flaw.
**Severity: [P1]**.

Another [P1] finding:
In `package.py` `hook_ratings`, if `todo` is empty, it returns `out, None`.
If `todo` is not empty, but all candidates fail, `out` is empty, `err` is set.
This is correct.

I will report the future timestamp issue as [P1].

P1_OR_WORSE: 1