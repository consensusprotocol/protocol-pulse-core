# qwen3.8-27b (qwen/qwen3.8-27b) 75 s finish=stop usage in 30772 / out 3597 usd~0.146 (upper-bound price)

I’ll audit the diff strictly against the stated laws and the RULING 70 requirements, focusing on the new visual gate, router changes, sealing, and cost accounting.

## P0 Findings

**1. `pipeline/package.py:113` — `out_visual["calls"]` / `out_visual["cached"]` accounting is wrong (undercounts, can misreport).**
- Concrete scenario: `see()` iterates `todo` and does:
  ```python
  out_visual["cached" if rec.get("cached") else "calls"] += 1 if rec.get("measured") else 0
  ```
  This only increments when `rec.get("measured")` is truthy. But `visual_for` returns a record with `measured: False` on failure (no sheet, out-of-contract twice). Those failures are *calls* (or at least attempts) that should be visible in the “calls”/“unmeasured” accounting, yet they are not counted in `calls`/`cached`. Meanwhile `out_visual["unmeasured"]` is incremented separately, so the total `calls + cached` will not equal the number of `see()` invocations, and the log line “{calls} sheet(s) judged, {cached} cached” is misleading: a failed call is neither “judged” nor “cached”, but it was still a paid/attempted call.
- Why it matters: RULING 70 says “Report the measured cost on the first build.” The `usd` field is updated correctly, but the call/cached counts are not a faithful record of what happened. This is a reporting defect in a new gate that is meant to be auditable.
- Fix: count every `todo` item as a call unless it was served from cache; e.g.
  ```python
  if rec.get("cached"):
      out_visual["cached"] += 1
  else:
      out_visual["calls"] += 1
  ```
  and keep `unmeasured` as a separate counter.

**2. `pipeline/visual_pin.py:673-674` — cache stores a record that may include `usd` and `usage`, but `sealed()` later strips them; however the cache key does not include the image bytes, only `moment_id:start-end:VERSION`.**
- Concrete scenario: Two different contact sheets for the same `moment_id` and same `start`/`end` (e.g. after a re-fetch of a different quality, or a change in `TILES`/`EVERY_S` that is not reflected in `VERSION`) would collide in the cache. The cache is keyed by `key(m)` which is `f"{m['moment_id']}:{float(m['start']):.3f}-{float(m['end']):.3f}:{VERSION}"`. The sheet’s `sha256` is not part of the key. If the sheet changes (different frames, different resolution, different labeling) but the moment and span are the same, the old verdict is returned as `cached=True` and the new sheet is never judged.
- Why it matters: Law L-m (fail closed) and the ruling’s “one contact sheet per clip” require that the verdict corresponds to the exact bytes the model saw. A stale cache entry violates this. The `VERSION` constant is `"visual-1"`, but it is not bumped when `TILES`, `EVERY_S`, `TILE_W`, or `FORMAT` change.
- Fix: include the sheet’s `sha256` in the cache key, or bump `VERSION` whenever any sheet-generation parameter changes. Better: key by `moment_id:start-end:VERSION:sheet_sha256`.

**3. `pipeline/providers.py:393-396` — router skip logic for vision prompts is asymmetric and can cause a vision prompt to be routed to a text-only backend if the chain is misconfigured.**
- Concrete scenario: The router skips a backend if `is_vision(prompt) and not b.vision`. But it also skips `XAIVisionBackend` if `not is_vision(prompt)`. This is correct. However, the `visual_check` chain in `model_providers.json` is:
  ```json
  ["xai_vision:grok-4.7", "heimdall:qwen/qwen3.8-27b", "heimdall:nvidia/nemotron-3.5-super-vl"]
  ```
  The `heimdall:qwen/qwen3.8-27b` backend is not defined in the diff (only `heimdall:nvidia/nemotron-3.5-super-vl` is added). If `heimdall:qwen/qwen3.8-27b` is a text-only Heimdall backend (i.e. `vision = False`), it will be skipped for vision prompts, which is correct. But if it is not defined at all, the router will raise an error or skip it. The diff does not show its definition, so I cannot verify it has `vision = True`. This is a potential fail-open: if the first backend (`xai_vision:grok-4.7`) fails and the second (`heimdall:qwen/qwen3.8-27b`) is not a vision backend, it is skipped, and the third (`heimdall:nvidia/nemotron-3.5-super-vl`) is tried. That is acceptable. But if the second backend is a vision backend that is not properly configured, it may fail. The key issue is that the diff does not define `heimdall:qwen/qwen3.8-27b`, so I cannot confirm it has `vision = True`.
- Why it matters: The ruling says “xAI first, Heimdall image models as failover.” If the failover chain is broken, the clip is not measured, which is fail-closed (good), but the cost and latency are wasted. More importantly, if a text-only backend is accidentally in the chain and not skipped, it would receive a vision prompt and fail, which is also fail-closed. The asymmetry is not a bug per se, but the missing definition is a gap.
- Fix: Ensure `heimdall:qwen/qwen3.8-27b` is defined with `vision = True` in `model_providers.json` or in the backend class.

**4. `pipeline/visual_pin.py:661` — the prompt text is built with `str(m.get("text") or "").replace('"', "'")`, which can corrupt the transcript if it contains single quotes.**
- Concrete scenario: If the clip’s text is `It's a mistake`, the prompt becomes `It's a mistake` (unchanged). If the text is `He said "no"`, it becomes `He said 'no'`. This is fine. But if the text is `It's "quoted"`, it becomes `It's 'quoted'`. The model is asked to copy on-screen text exactly, but the spoken words are given in the prompt. If the spoken words contain quotes, they are replaced with single quotes, which may confuse the model about what the words actually are.
- Why it matters: The model’s judgment of `words_negative` and `asserts_beyond_words` depends on the accuracy of the spoken words in the prompt. Corrupting quotes could lead to a false negative (missing a negative claim) or a false positive (seeing a negative claim that isn’t there).
- Fix: Use `json.dumps` to escape the text, or pass the text as a separate field in the prompt structure.

## P1 Findings

**5. `pipeline/package.py:106-117` — `see()` uses `ThreadPoolExecutor(max_workers=4)` but `visual_for` is not thread-safe with respect to the cache.**
- Concrete scenario: `visual_for` reads and writes to `cache` (a dict) without a lock. `save_cache` uses `CACHE_LOCK`, but the in-memory `cache` dict is mutated by multiple threads. If two threads call `visual_for` for the same key simultaneously, they may both miss the cache, both call the model, and both write to the cache. This is a race condition that can lead to duplicate model calls and inconsistent cache state.
- Why it matters: The ruling says “a clip is paid for once across builds.” A race condition can cause a clip to be paid for twice in the same build.
- Fix: Use a lock around cache reads and writes in `visual_for`, or use a thread-safe cache.

**6. `pipeline/visual_pin.py:531-544` — `fetch()` uses `yt-dlp` with `--download-sections` and `--force-keyframes-at-cuts`, but the timeout is 300 seconds. If the download is slow, the entire build is blocked.**
- Concrete scenario: A large video or a slow network can cause `yt-dlp` to take >300 seconds, raising `TimeoutExpired`. This is caught by the `except Exception` in `visual_for` and returns `measured: False`. This is fail-closed, but it means the clip is dropped and the line-up is re-lined. If many clips are dropped, the build may fail to produce a package.
- Why it matters: The ruling does not specify a timeout, but a 300-second timeout per clip can make the build very slow or fail if the network is unreliable.
- Fix: Consider a shorter timeout or a retry with exponential backoff.

**7. `pipeline/visual_pin.py:547-580` — `sheet()` uses `ffmpeg` to extract stills and `PIL` to tile them. The `ffprobe` call has a 30-second timeout, and each `ffmpeg` call has a 60-second timeout. If the video is large or the CPU is busy, these can time out.**
- Concrete scenario: A 480p video of 16 seconds with 8 stills requires 8 `ffmpeg` calls. If each takes 60 seconds, the total is 480 seconds, which is >300 seconds (the `fetch` timeout). This is a potential deadlock: `fetch` times out before `sheet` finishes.
- Why it matters: The build can hang or fail if the video processing is slow.
- Fix: Use a single `ffmpeg` call to extract all stills, or increase the timeouts.

**8. `pipeline/providers.py:348-374` — `XAIVisionBackend.complete()` uses `max_output_tokens = max(int(self.spec.get("min_out", 8000)), max_tokens * 4)`. The `min_out` for `xai_vision:grok-4.7` is not set in the diff, so it defaults to 8000. This is a large output cap for a vision model that should return a small JSON object.**
- Concrete scenario: The model is asked to return a JSON object with three fields. The output cap is 8000 tokens, which is overkill. This increases the cost and latency.
- Why it matters: The ruling says “Report the measured cost on the first build.” An unnecessarily large output cap inflates the cost.
- Fix: Set `min_out` to a smaller value, e.g. 1000, in `model_providers.json`.

**9. `pipeline/package.py:125-138` — `visual_hook_block` is set on `m` but not cleared if the hook is later re-evaluated.**
- Concrete scenario: A hook is blocked by `visual_hook_block`. If the build is re-run with a different visual cache, the hook may be unblocked, but `m["visual_hook_block"]` is still set from the previous run. This is a stale state issue.
- Why it matters: The hook may be incorrectly blocked in a subsequent build.
- Fix: Clear `visual_hook_block` at the start of each build, or derive it from the visual record each time.

## P2 Findings

**10. `pipeline/visual_pin.py:493-508` — `load_cache` and `save_cache` use `json.dump` with `indent=1`, which is not compact. For a large cache, this can be slow and use a lot of disk space.**
- Concrete scenario: A cache with 1000 entries can be several MB. `json.dump` with `indent=1` is slower than `indent=None`.
- Why it matters: Minor performance issue.
- Fix: Use `indent=None` for the cache file.

**11. `pipeline/visual_pin.py:515-528` — `times()` returns a list of offsets, but the last offset is `max(0.0, dur - 0.05)`. If `dur` is very small (<0.05), the last offset is 0.0, which is the same as the first. This can cause duplicate stills.**
- Concrete scenario: A 0.1-second clip has `dur = 0.1`, `last = 0.05`, `ts = [0.0, 0.05]`. This is fine. But a 0.04-second clip has `dur = 0.04`, `last = 0.0`, `ts = [0.0]`. This is also fine. The issue is if `dur` is exactly 0.05, `last = 0.0`, and `ts = [0.0]`. This is acceptable.
- Why it matters: Minor edge case.
- Fix: No change needed.

**12. `pipeline/providers.py:263-276` — `prompt_text()` uses `hashlib.sha256(i.encode()).hexdigest()` for each image. This is correct, but the hash is computed every time `prompt_text` is called, which can be slow for large images.**
- Concrete scenario: A 1MB image takes ~10ms to hash. If `prompt_text` is called multiple times for the same prompt, the hash is recomputed.
- Why it matters: Minor performance issue.
- Fix: Cache the hash in the prompt dict, or compute it once.

**13. `pipeline/package.py:102-103` — `import visual_pin as VP` is done inside `build()`, which is not ideal for performance. It should be done at the top of the module.**
- Concrete scenario: The import is done every time `build()` is called, which is slow.
- Why it matters: Minor performance issue.
- Fix: Move the import to the top of `package.py`.

**14. `pipeline/visual_pin.py:646-681` — `visual_for()` catches all exceptions and returns `measured: False`. This is fail-closed, but it can hide bugs.**
- Concrete scenario: A `KeyError` in `check()` is caught and returned as `measured: False`. This is correct, but it makes debugging harder.
- Why it matters: Minor maintainability issue.
- Fix: Log the exception with a stack trace.

**15. `pipeline/package_pin.py:227-228` — `MEDLEY_GATES` gains `"visual"`, but `REQUIRED_GATES` does not. This means that for non-medley pins, the visual gate is not required. This is correct, but it should be documented.**
- Concrete scenario: A non-medley pin does not have a visual gate, so it is not required. This is fine.
- Why it matters: Minor documentation issue.
- Fix: Add a comment explaining why `visual` is only in `MEDLEY_GATES`.

## SHIP: no

The P0 findings are serious enough to block shipping:
1. The call/cached accounting is wrong, which violates the ruling’s requirement to report the measured cost.
2. The cache key does not include the sheet’s `sha256`, which can lead to stale verdicts and violate law L-m.
3. The router’s vision prompt handling is correct, but the missing definition of `heimdall:qwen/qwen3.8-27b` is a gap that needs to be verified.
4. The prompt text corruption can lead to false negatives/positives in the model’s judgment.

Fix these P0 issues and re-audit before shipping.