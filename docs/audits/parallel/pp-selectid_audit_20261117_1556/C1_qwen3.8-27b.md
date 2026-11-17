# qwen3.8-27b (qwen/qwen3.8-27b) 520 s finish=stop usage in 10615 / out 22846 usd_reported=0.016783 usd~0.375 (upper-bound price)



# Code Audit — pp-selectid / RULING 142 (3) post_live stream handling

## Scope reviewed
`pipeline/transcript_truth.py` (new `media_seconds`, `whole_stream`, modified `audio_window`), `pipeline/visual_pin.py` (modified `fetch`), `tests/package/test_ruling_142_post_live.py` (new, 8 tests).

---

## Findings

### [P1] `visual_pin.fetch` — early return skips duration validation of `.cut.mp4`

```python
cut = os.path.join(d, stem + ".cut.mp4")
if not have and os.path.exists(cut):
    return cut          # ← no media_seconds check
```

If a prior run's ffmpeg cut was interrupted (SIGKILL, OOM, disk full), a 0-byte or partially-written `.cut.mp4` remains on disk. The next call for the same span finds `have` empty (the section was also empty) and returns the corrupt file **without** the `TT.media_seconds(cut) >= TT.MIN_SECTION_SHARE * (end - start)` guard that the later code path applies. Downstream frame-sheet extraction reads garbage; the visual gate may pass on black/tear frames or fail in a way that is not attributable to the real cause.

The `import transcript_truth as TT` sits *after* this early return, so the fix requires hoisting the import (or the check) above it:

```python
import transcript_truth as TT   # move here (or to module level)
...
if not have and os.path.exists(cut) \
        and TT.media_seconds(cut) >= TT.MIN_SECTION_SHARE * (end - start):
    return cut
```

The test `test_an_empty_section_is_cut_from_the_whole_stream_and_kept` exercises the happy-path reuse (second call, no new subprocess) but never plants a 0-byte `.cut.mp4` before the first call, so the defect is untested.

---

### [P2] `whole_stream` — partial file from a failed yt-dlp download is silently reused

```python
if not find():
    subprocess.run(["yt-dlp", ...], check=True, timeout=1800, capture_output=True)
have = find()
```

If yt-dlp is killed mid-download (timeout, network drop, `check=True` → `CalledProcessError`), a partial file with the correct stem is left in `out_dir`. The **next** call to `whole_stream` for the same `video_id`/`tag` finds it via `find()` and returns it. The caller's `MIN_SECTION_SHARE` check catches windows that fall beyond the partial file's duration, but a window *within* the partial file's range produces a cut that passes the duration gate yet contains missing or corrupt DASH segments.

Suggested fix: write to a temp name and `os.rename` on success, or `try/except` around the yt-dlp call and `os.remove` the partial file on failure.

---

### [P2] `whole_stream` — no concurrency guard on the download

Two pipeline workers (or a retry) calling `whole_stream` for the same `video_id`/`tag` simultaneously both see `find()` empty, both launch yt-dlp, and both write to the same output path. The second write corrupts the first. The 30-minute timeout makes the window for collision realistic on a 2-GPU box running parallel story builds.

Suggested fix: a lock file (`<stem>.lock`) with `O_CREAT | O_EXCL`, or the temp-file + atomic-rename pattern above.

---

### [P3] `import transcript_truth as TT` inside `visual_pin.fetch`

The import is placed mid-function, after the early-return block. This is what makes the P1 fix awkward and is inconsistent with the rest of the module (which uses top-level imports). Move it to module level.

---

### [P3] `WHOLE` dict is incomplete / misleading

```python
WHOLE = {"audio": ("audio.m4a", "bestaudio[acodec^=mp4a]/bestaudio")}
```

Only the `"audio"` key exists, yet `whole_stream` is also called with `tag="video"` (from `visual_pin.fetch`, which passes its own `FORMAT` constant). The integrator-cache filename mapping for video is a separate hard-coded dict inside `whole_stream`. Consolidating both entries into `WHOLE` would make the single source of truth explicit and prevent a future edit from diverging the two.

---

### [P3] `media_seconds` timeout of 60 s

`ffprobe` on a local file reads the container header and returns in < 1 s. A 60 s timeout is a safety net against a hung NFS mount or a pathological file, but it also means a stuck probe blocks the pipeline for a full minute before the `except` fires. 10 s is ample and keeps the fail-closed path snappy.

---

## Items checked and found sound

| Question from the diff header | Verdict |
|---|---|
| (1) Can an empty or wrong window be returned as measured? | `audio_window` always re-cuts (no stale-wav path); the `MIN_SECTION_SHARE` guard on both the section and the whole-stream cut, plus `os.remove` + `OSError` on failure, closes the loop. **Exception:** the `visual_pin.fetch` early return (P1 above). |
| (2) Is a normal (non-post_live) video unaffected? | Yes. A section whose duration ≥ 50 % of the window takes the original `ffmpeg -i src → wav` / direct-return path. No new code runs. |
| (3) Cache and download paths (concurrent builds, partial downloads) | Integrator cache is read-only and checked first — correct. Partial-download and concurrency gaps are the two P2 findings above. |
| (4) The tests | 8 offline tests cover: empty-section → whole-stream (audio + video), integrator-cache-first, no-section-file, normal-section-unchanged, empty-cut-fails-closed (audio + video), cut-reuse. Mutations 8/8 killed. **Gap:** no test plants a corrupt/0-byte `.cut.mp4` before the first `fetch` call to exercise the P1 early-return path. |

## Law compliance

No governing-law violation is introduced by this diff. The change is a fetch-layer fix (RULING 142 (3)); it does not alter sentence-law boundaries, selection locks, snap limits, edge-word rules, credits, sign-off, or release authorisation. The fail-closed behaviour (`OSError` on empty cut, `os.remove` of the bad file) is consistent with M12. The `MIN_SECTION_SHARE = 0.5` constant is a new gate threshold, which is permitted under LAW 20 / M2 (it is a constant, not a per-render tuning).

---

**P1_OR_WORSE: 1**