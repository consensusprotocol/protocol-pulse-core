# qwen3.8-27b (qwen/qwen3.8-27b) 111 s finish=stop usage in 32248 / out 4025 usd~0.157 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-1541
# Reviewer: [Your Model]

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I focused heavily on the *logic* of the gate (fail-closed behavior, hook blocking) and the *router* mechanics. I missed or under-weighted two specific implementation details that the other models (specifically Qwen and GLM) flagged, which turned out to be the most critical defects in the "fixed" diff:

1.  **The Cache Key Collision (Qwen P0-2 / GLM P1-5):** I assumed the `VERSION` bump or the `moment_id` was sufficient for cache integrity. I missed that the cache key in `visual_pin.py` (line 514) includes a digest of `PROMPT`, `TILES`, `EVERY_S`, `TILE_W`, `FORMAT`, and `text`. However, I failed to verify if *all* inputs to the sheet generation are covered. Specifically, the `sheet()` function uses `os.getpid()` and `threading.get_ident()` in temporary filenames, but more importantly, the *content* of the sheet depends on the video file fetched. If the video file changes (e.g., re-fetch due to network error or source update) but the `moment_id` and `text` remain the same, the cache key remains the same. The code *does* check `_sha_of(p) == hit["sheet"]["sha256"]` (line 667), which mitigates this. **However**, I missed the subtlety that `key()` does *not* include the `video_id`. If two different videos had the same `moment_id` (unlikely but possible in a bug) or if the `moment_id` is not unique across sources, the cache could collide. More critically, I missed that the `text` in the key is `str(m.get("text") or "")`. If the `text` field is modified *after* the cache is written but *before* the next build, the key changes, forcing a re-judge. This is correct. But if the `text` is *stable* and the *video* changes, the SHA check catches it. So this is actually **safe** in the current diff. I retract my initial worry here, but I acknowledge I didn't trace the SHA verification path as rigorously as Qwen did.

2.  **The Accounting Logic (Qwen P0-1 / GLM P0-2):** I missed the specific bug in `package.py` line 113. In Cycle 1, I noted that `out_visual` counters were updated, but I didn't scrutinize the *condition* for incrementing `calls` vs `cached`. The code is:
    ```python
    out_visual["cached" if rec.get("cached") else "calls"] += 1
    ```
    Wait, looking at the *fixed* diff (line 113):
    ```python
    out_visual["cached" if rec.get("cached") else "calls"] += 1     # audit 1541 C1: every attempt
    ```
    This line *always* increments either `cached` or `calls` by 1. It does **not** check `measured`. This means an *unmeasured* attempt (where `rec.get("cached")` is False) is counted as a `call`. This is **correct** behavior for "attempts made". The `unmeasured` counter is incremented separately (line 115). So the total `calls + cached` equals the number of `todo` items processed. This is consistent. **I missed that the fix *was* applied correctly in this diff.** In Cycle 1, I might have been looking at the *pre-fix* logic or misread the line. The other models flagged this as a P0 in Cycle 1, and the consensus applied C2. The current diff *shows* the fix. So, I agree with the consensus that this was a P0, and I verify it is now fixed.

3.  **The `visual_hook_block` Staleness (Qwen P1-9 / GLM P1-8):** I missed the potential issue where `visual_hook_block` might persist across builds if not cleared. The diff shows `m.pop("visual_hook_block", None)` at line 126 in `build()`. This clears it for *all* cleared moments before re-evaluating. This is correct. I acknowledge I missed this specific line in my Cycle 1 review.

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **Qwen P0-1 (Accounting):** **Agree** it was a P0. The current diff fixes it. I verify the fix is present and correct.
*   **Qwen P0-2 (Cache Key):** **Partially Agree.** The risk of stale cache is mitigated by the SHA check (line 667). However, the cache key *should* include `video_id` for robustness, even if `moment_id` is unique. If `moment_id` is not unique, this is a P1. I will flag this as a P1 for hardening.
*   **Qwen P0-3 (Router Vision/Text):** **Disagree** with the severity. The router logic (lines 393-396) correctly skips non-vision backends for vision prompts and vice versa. The `heimdall:qwen/qwen3.8-27b` backend is defined in `model_providers.json` (line 42) and `HeimdallBackend.vision = True` (line 313). So it *is* a vision backend. The failover chain is valid. This is not a P0.
*   **GLM P0-1 (Seal Unmeasured):** **Disagree.** `sealed()` (line 648) copies keys from `rec`. If `rec` is unmeasured, it has `measured: False`. The gate row (line 209) requires `measured is True` for PASS. So an unmeasured record *cannot* pass the gate. The seal itself is just a data structure; the *gate* enforces the rule. This is safe.
*   **Grok P2 (Broad Exception):** **Agree.** The `except Exception` in `visual_for` (line 676) is broad. It masks specific errors (e.g., OOM, network timeout) as "not measured". This is acceptable for fail-closed, but reduces observability. P2.

## 3. NEW FINDINGS FROM THIS REVIEW

**P1-1: Cache Key Missing `video_id`**
`visual_pin.py:514`
The cache key is `f"{m['moment_id']}:{float(m['start']):.3f}-{float(m['end']):.3f}:{VERSION}:{digest}"`.
The digest includes `PROMPT`, `TILES`, `EVERY_S`, `TILE_W`, `FORMAT`, and `text`.
It does **not** include `m['video_id']`.
If two different moments (from different videos) happen to have the same `moment_id` (e.g., due to a bug in moment generation or ID collision), the cache would serve the wrong verdict.
While `moment_id` is *supposed* to be unique, the cache is a global store. Adding `video_id` to the key is a cheap hardening measure.
**Scenario:** Moment A (video X) and Moment B (video Y) have the same `moment_id` "m1". Moment A is judged and cached. Moment B is processed. The cache key matches. The SHA check (line 667) compares the *new* sheet's SHA with the *old* sheet's SHA. If the sheets are different (different videos), the SHA check fails, and it re-judges. So the SHA check *does* protect against this.
**Revised:** This is **P2** because the SHA check mitigates the risk. However, if the SHA check is bypassed (e.g., `hit` is None), it's safe. If `hit` is not None, the SHA check runs. So it's safe. I downgrade to P2.

**P1-2: `visual_for` Retry Logic Does Not Update `why` for First Failure**
`visual_pin.py:680-696`
The loop `for sd in (seed, seed + 1):` catches exceptions.
If the first try fails, `why` is set to the first error.
If the second try fails, `why` is set to the second error.
The final return (line 697) uses the *last* `why`.
This is correct behavior (report the last error).
However, if the first try fails with a *network* error and the second try fails with a *contract* error, the user only sees the contract error. This is acceptable.
**No defect.**

**P1-3: `sheet()` Function Uses `os.getpid()` and `threading.get_ident()` in Temp Filenames**
`visual_pin.py:569`
`out = os.path.join(d, f"_still_{os.getpid()}_{threading.get_ident()}_{i}.jpg")`
This is safe for concurrency within a single process.
However, if multiple processes run `build()` concurrently on the same `work_dir`, they could collide on the *final* sheet name `visual_{sha[:16]}.jpg` (line 590).
The SHA is based on the *content* of the sheet. If two processes generate the *same* sheet (same video, same params), they will have the same SHA and thus the same filename.
`os.replace(tmp, path)` (line 591) is atomic. If two processes write to the same path, the last one wins. Since the content is identical, this is safe.
**No defect.**

**P1-4: `fetch()` Does Not Verify Video Integrity**
`visual_pin.py:543-556`
`fetch()` downloads the video. It does not check the SHA of the video file.
If the video file is corrupted or truncated, `sheet()` will fail (ffmpeg error), leading to "not measured".
This is fail-closed.
However, if the video file is *valid* but *different* from what was previously cached (e.g., re-encoded by YouTube), the SHA check in `visual_for` (line 667) will catch it *only if* the sheet is rebuilt.
Wait, `visual_for` checks the SHA of the *sheet*, not the video.
If the video changes, the sheet changes, the SHA changes, and the cache miss occurs.
So this is safe.
**No defect.**

**P1-5: `package.py` Line 113: `out_visual["cached" if rec.get("cached") else "calls"] += 1`**
This line increments `calls` for *every* non-cached attempt, including unmeasured ones.
This is correct for "attempts made".
The `unmeasured` counter is incremented separately.
The log line (line 136) says: `{len(rated_open)} hook(s) seen, {len(blocked)} may not open`.
It does *not* log the `calls`/`cached`/`unmeasured` breakdown for the hooks.
The `out["visual"]` dict (line 134) contains the breakdown.
This is fine.
**No defect.**

**P1-6: `providers.py` Line 275: `prompt_text` Hashes Base64 String**
`hashlib.sha256(i.encode()).hexdigest()`
This hashes the *base64 string*, not the *decoded bytes*.
Two different images could have the same base64 string? No, base64 is deterministic.
Two different images could have the same SHA of their base64 string? No, SHA256 is collision-resistant.
So this is safe.
However, the *recording* key (line 425) uses `prompt_text(prompt)`, which includes the SHA of the base64 string.
The *cache* key in `visual_pin` uses the SHA of the *sheet file* (line 589).
These are different SHAs.
The recording is for *audit* (what was sent to the model).
The cache is for *performance* (what was judged).
They do not need to match.
**No defect.**

**P1-7: `visual_pin.py` Line 664: `hit = cache.get(k) if cache is not None and (cache.get(k) or {}).get("measured") else None`**
This line only considers a cache hit if the cached record is `measured`.
If the cached record is *not* measured, it is ignored, and the clip is re-judged.
This is correct (fail-closed: don't cache failures).
**No defect.**

**P1-8: `package.py` Line 107: `todo = [m for m in ms_ if not (m.get("visual") or {}).get("measured")]`**
This line selects moments that are *not* measured.
If a moment is *already* measured (from a previous build or earlier in this build), it is skipped.
This is correct (cache hit).
**No defect.**

**P1-9: `package.py` Line 110: `recs = list(vp.map(lambda m: VP.visual_for(router, m, work_dir, vcache), todo))`**
`ThreadPoolExecutor` is used.
`visual_for` is *not* thread-safe if it modifies shared state.
It reads `cache` (line 664) and writes to `cache` (line 691).
The `cache` dict is shared across threads.
Python's GIL protects dict operations, but *compound* operations (read-modify-write) are not atomic.
Line 691: `cache[k] = {x: y for x, y in rec.items() if x not in ("cached", "usd")}`
This is a single assignment, which is atomic in CPython.
Line 664: `hit = cache.get(k)`
This is a single read, which is atomic.
So the cache is thread-safe.
**No defect.**

**P1-10: `visual_pin.py` Line 505: `CACHE_LOCK = threading.Lock()`**
The lock is used in `save_cache` (line 505).
It is *not* used in `visual_for` when reading/writing the `cache` dict.
This is fine because the dict operations are atomic.
**No defect.**

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| **Visual Gate Logic** | P1 | P2 | The fail-closed logic is robust. The hook blocking and clip dropping are correct. |
| **Cache Integrity** | P0 | P2 | The SHA check mitigates the risk of stale cache. The missing `video_id` in the key is a minor hardening issue. |
| **Accounting** | P0 | P2 | The fix is applied and correct. |
| **Router** | P1 | P2 | The vision/text separation is correct. The failover chain is valid. |
| **Seal Compatibility** | P1 | P2 | The `SEALED_LATER` addition is correct. Old pins are untouched. |
| **Cost Accounting** | P1 | P2 | The `upper_usd` and `usd` reporting are correct. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None.

**P1 HIGH:**
1.  **`visual_pin.py:514`**: Add `m['video_id']` to the cache key. While the SHA check mitigates the risk, it is a cheap hardening measure to prevent potential cache collisions if `moment_id` is not unique.
    *   *Fix:* `inputs = json.dumps([PROMPT, TILES, EVERY_S, TILE_W, FORMAT, str(m.get("text") or ""), m.get("video_id")])`

**P2 MEDIUM:**
1.  **`visual_pin.py:676`**: The broad `except Exception` masks specific errors. Consider logging the exception type and message to a separate file for debugging.
2.  **`providers.py:275`**: The `prompt_text` function hashes the base64 string. This is correct, but it is worth noting that the recording key and the cache key use different SHAs. This is intentional but could be confusing.
3.  **`package.py:113`**: The accounting logic is correct, but the log line (line 136) does not include the `calls`/`cached`/`unmeasured` breakdown. Consider adding it to the log for better observability.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**Add `video_id` to the cache key in `visual_pin.py:514`.**
This is the only change that could prevent a subtle cache collision bug. All other issues are either fixed or minor.

## 7. PRODUCTION READY?

**Yes with conditions.**

**Conditions:**
1.  Apply the P1 fix: Add `video_id` to the cache key in `visual_pin.py:514`.
2.  Verify that `moment_id` is unique across all sources. If it is not, the P1 fix is mandatory. If it is, the P1 fix is still recommended for hardening.
3.  Run the full test suite (14 suites) to ensure no regressions.

**Rationale:**
The core logic of the visual gate is sound. The fail-closed behavior is correct. The router changes are safe. The seal compatibility is maintained. The accounting is fixed. The only remaining risk is a subtle cache collision, which is mitigated by the SHA check but can be fully eliminated by adding `video_id` to the key.