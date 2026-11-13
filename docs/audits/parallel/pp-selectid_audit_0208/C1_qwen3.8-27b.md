# qwen3.8-27b (qwen/qwen3.8-27b) 47 s finish=stop usage in 13628 / out 3242 usd~0.090 (upper-bound price)

I’ll audit the diff strictly against the five questions, using only what is visible in the provided patch.

## Findings

### P1 — `speakers.attribute_package` may pass `None` as the Source for window moments (fail-open risk)
**File:** `pipeline/speakers.py` (diff line 265)

```python
src, meta = sources.get(s.get("source_key") or s["video_id"]), meta_for(s["video_id"])
```

**Scenario:**
1. A window moment is packaged with `source_key = "vidW@600.000-645.000"`.
2. `sources` is keyed by that `source_key` (per `ledger_build.py` line 174: `sources[key] = wsrc`).
3. If the package segment **lacks** the `source_key` field (e.g., an older package, a serialization bug, or a code path that drops it), the lookup falls back to `s["video_id"]` → `"vidW"`.
4. `sources.get("vidW")` returns `None` because the window path **never** inserts a `video_id`-keyed Source (only the full-video path does, at line 99).
5. `attribute(router, s, None, meta)` is called with `src=None`.

**Why this matters:** The diff does not show `attribute()`’s body. If it dereferences `src` (e.g., `src.words`, `src.window`), this is a crash. If it treats `None` as “no source” and returns a default/empty speaker record, it **silently produces an unmeasured speaker attribution**, violating L-m (“nothing measured is never a pass”) and L-j (fail closed). The full-video path is safe because `sources[vid]` is always set. The window path has no such guarantee for the fallback key.

**Contrast with other call sites:** `package.py`’s `src_of()` (line 218) uses `sources[x.get("source_key") or x["video_id"]]` with **direct indexing** (`[]`), which raises `KeyError` if the key is missing — fail-closed. `speakers.py` uses `.get()` — fail-open. This inconsistency is a defect.

**Fix:** Use `src_of(s, sources)` (which raises) or explicitly check for `None` and mark the segment as unmeasured/failed.

---

### P1 — `context_integrity.contexts_from_sources` uses direct indexing but the fallback key may not exist
**File:** `pipeline/context_integrity.py` (diff line 10)

```python
src = sources[seg.get("source_key") or seg["video_id"]]
```

**Scenario:**
1. A window segment has `source_key = "vidW@600.000-645.000"`.
2. `sources` is keyed by that `source_key`.
3. If `source_key` is present, the lookup succeeds.
4. If `source_key` is **absent** (serialization loss, older package), the fallback is `seg["video_id"]` → `"vidW"`.
5. `sources["vidW"]` raises `KeyError` because the window path never inserts a `video_id`-keyed Source.

**Why this is P1, not P0:** The `KeyError` is fail-closed (it crashes, it does not silently pass). However, it means that **any** window segment that loses its `source_key` in transit will crash the context-integrity gate rather than being cleanly rejected with a diagnostic. The `speakers.py` case is worse because it may not crash. This is a robustness gap: the two lookup sites disagree on failure mode.

**Note:** The diff shows `_package` (line 207) conditionally includes `source_key`:
```python
**({"source_key": m["source_key"]} if m.get("source_key") else {})
```
So a moment **without** a `source_key` (full-video path) will not have the field in the segment. That is correct for full-video moments (keyed by `video_id`). But if a **window** moment somehow loses its `source_key` before packaging, the segment will fall back to `video_id` and crash here. The risk is low if `source_key` is always set for window moments (which the diff shows it is, line 167), but the failure mode is a crash, not a clean rejection.

---

### P2 — `window_records` report structure change may break downstream consumers
**File:** `pipeline/ledger_build.py` (diff line 137)

```python
report["window_records"].setdefault(vid, []).append(os.path.relpath(wpath, os.path.realpath(store)))
```

**Before:** `report["window_records"]` was `{video_id: path}` (a single path per video).
**After:** `report["window_records"]` is `{video_id: [path1, path2, ...]}` (a list of paths per video).

**Scenario:**
1. Any downstream code that reads `report["window_records"][vid]` expecting a string will now receive a list.
2. If that code does `os.path.basename(report["window_records"][vid])`, it will crash or produce garbage.
3. The diff does not show any downstream consumers of `report["window_records"]`, so I cannot verify whether this breaks anything.

**Why P2:** The diff is self-contained in the files shown. If no other code reads `window_records`, this is a non-issue. But the change in data structure is a breaking change for any external consumer. The log line (line 195) correctly uses `sum(len(v) for v in report["window_records"].values())`, so the internal logging is updated.

---

### P2 — `sources` count in report may be misleading
**File:** `pipeline/ledger_build.py` (diff line 185)

```python
report["moments"], report["sources"] = len(moments), len(sources)
```

**Scenario:**
1. `sources` is a dict keyed by `source_key` (window path) or `video_id` (full-video path).
2. If two window moments of the same video have **different** `source_key`s (different windows), they produce two entries in `sources`.
3. If two window moments of the same video have the **same** `source_key` (same window, different moments), they share one entry.
4. The report says “N sources,” which is the number of distinct Source objects, not the number of videos. This is correct but may be confusing if a consumer expects `sources` to mean “videos.”

**Why P2:** The log line (line 187) clarifies: `{report['moments']} moments on {report['videos']} videos ({report['sources']} word records)`. So the distinction is made explicit. No defect, but worth noting.

---

### P2 — Deduplication logic for overlapping windows may miss edge cases
**File:** `pipeline/ledger_build.py` (diff line 143)

```python
dup = next((mid for a, b, mid in kept if a < sp.end and sp.start < b), None)
```

**Scenario:**
1. `kept` is a list of `(start, end, moment_id)` tuples for already-accepted window moments.
2. The check is `a < sp.end and sp.start < b`, which is the standard interval-overlap test.
3. If two spans **touch** at a single point (e.g., `sp.end == a`), they are **not** considered overlapping. This is correct for speech (a word ending at time T and another starting at T are distinct).
4. However, if the same speech is cut from two windows with **identical** spans, the second is correctly deduplicated.
5. The dedup is **per video** (within the `irs` loop for a given `vid`), not global. If the same speech appears in two **different** videos, it is not deduplicated here. That is correct (different sources).

**Why P2:** The logic appears correct for the stated purpose. No defect found.

---

### P2 — `caption_source` is called once per `transcript_sha256`, but the result is shared across moments
**File:** `pipeline/ledger_build.py` (diff lines 131–134)

```python
sha = r.get("transcript_sha256")
if sha not in caps:
    caps[sha] = caption_source(r, ctx, store, ledger_store)
wsrc.context_source, cwhy = caps[sha]
```

**Scenario:**
1. Two moments from the same video have the same `transcript_sha256` (same caption record).
2. `caption_source` is called once, and the result is shared.
3. If `caption_source` mutates its input or returns a shared object, this could cause issues. The diff does not show `caption_source`’s body, so I cannot verify.
4. The `context_source` is set on `wsrc` (the window Source), which is per-moment. So even if `caps[sha]` is shared, each `wsrc` gets its own `context_source` reference. This is correct.

**Why P2:** No defect found, but the shared `caps` dict is a potential source of subtle bugs if `caption_source` has side effects.

---

## Answers to the Five Questions

### (a) Can any lookup still reach the WRONG window or Source for a moment or segment?

**Yes, in `speakers.py`.** If a window segment lacks `source_key`, the fallback to `video_id` returns `None` (via `.get()`), which is the wrong Source. In `context_integrity.py`, the same fallback raises `KeyError` (fail-closed, but not the wrong Source). In `package.py`, `src_of()` uses direct indexing, so it raises `KeyError` if the key is missing. The only fail-open path is `speakers.py`.

### (b) Can the same speech enter two clips through two overlapping windows, or a span cross a window’s edge?

**No, for overlapping windows.** The dedup logic (line 143) prevents two window moments of the same video with overlapping spans from both being accepted. The better-ranked row keeps the moment; the other is counted in `duplicates_of`.

**For spans crossing a window’s edge:** The diff does not show `reanchor()`’s body. If `reanchor` allows a span to extend beyond the window’s `[start_s, end_s]`, the span could cross the window’s edge. The test `test_the_caption_coverage_is_measured_never_assumed` (line 326) suggests that caption coverage is checked, but the diff does not show whether `reanchor` enforces that the span is **within** the window. I cannot verify this from the diff alone.

### (c) Is anything in the full-video path changed?

**No.** The full-video path (lines 75–100) is structurally unchanged: every row re-anchors in the full-video Source, dedup is by `(vid, k0, k1)`, and the Source is keyed by `video_id`. The only change is the extraction of the `make()` helper (lines 49–64), which is used by both paths. The `make()` helper is new, but it does not change the full-video path’s behavior.

### (d) Does anything downstream (pin, render, novelty, dedup, speakers) still assume one Source per video?

**`speakers.py` does not assume one Source per video** — it looks up by `source_key` or `video_id`. However, it uses `.get()`, which returns `None` if the key is missing, as noted in P1.

**The diff does not show pin, render, novelty, or dedup code.** I cannot verify whether they assume one Source per video. The `sources` dict is now keyed by `source_key` for window moments, so any downstream code that iterates over `sources` and expects `video_id` keys will break. The diff does not show any such iteration.

### (e) Do the tests fail on the defect each one names?

**The tests are updated to use `source_key`** (lines 288, 334, 343, 352). The new test `test_each_moment_reads_its_own_window_and_the_same_speech_twice_is_one_moment` (line 296) verifies:
1. Two windows of one video give two moments with two Sources.
2. The same speech in two windows is one moment (dedup).
3. The gate’s context check reads the segment’s own window.

**However, the tests do not cover the `speakers.py` fail-open case.** There is no test that verifies what happens when a window segment lacks `source_key` and `speakers.attribute_package` is called. The tests also do not cover the `context_integrity.py` `KeyError` case.

**The existing tests are updated to use `source_key`**, so they will fail if the code does not correctly key Sources by `source_key`. This is correct.

---

## Verdict

**SHIP: no**

**Reasons:**
1. **P1:** `speakers.attribute_package` uses `.get()` with a fallback to `video_id`, which returns `None` for window moments if `source_key` is missing. This is fail-open and may produce unmeasured speaker attributions, violating L-m and L-j.
2. **P1:** `context_integrity.contexts_from_sources` uses direct indexing with a fallback to `video_id`, which raises `KeyError` for window moments if `source_key` is missing. This is fail-closed but inconsistent with `speakers.py` and may crash the gate.
3. **P2:** The `window_records` report structure change may break downstream consumers (unverifiable from the diff).
4. **P2:** The tests do not cover the fail-open/fail-closed edge cases in `speakers.py` and `context_integrity.py`.

**Required fixes before shipping:**
1. Change `speakers.py` to use `src_of()` or explicit `KeyError` handling (fail-closed).
2. Add tests for the case where a window segment lacks `source_key`.
3. Verify that no downstream code assumes one Source per video (pin, render, novelty, dedup).
4. Verify that `reanchor()` enforces that spans are within the window’s edges.