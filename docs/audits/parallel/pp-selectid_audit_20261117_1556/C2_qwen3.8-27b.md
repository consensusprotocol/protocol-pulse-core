# qwen3.8-27b (qwen/qwen3.8-27b) 308 s finish=stop usage in 9901 / out 11898 usd_reported=0.008944 usd~0.208 (upper-bound price)



# PROTOCOL PULSE — CYCLE 2 CODE AUDIT (Final)
## Feature: pp-selectid-20261117_1556

---

## 1. WHAT DID THEY CATCH THAT I MISSED?

In Cycle 1 I (like Gemma) found no P0/P1/P2 defects. Qwen's **[P1]** — the `visual_pin.fetch` early return that handed back a `.cut.mp4` with no duration validation — is the one I missed. The code path was:

```python
if not have and os.path.exists(cut):
    return cut          # no media_seconds guard
```

A 0-byte or partially-written `.cut.mp4` from a SIGKILL/OOM/disk-full interruption would be returned as if it were a valid frame clip. The `import transcript_truth as TT` sitting *below* that line made the fix look trivially "just add a check" but actually required restructuring the early-return logic. I should have traced every return path in `fetch` and asked "what file state does this assume?" I didn't.

Qwen's two **[P2]** findings (partial whole-stream download reuse; no concurrency guard) I also under-weighted. I dismissed the partial-download case as "yt-dlp handles temp files" without verifying the exact failure mode (timeout → `TimeoutExpired` → `.part` file left behind → next call's `find()` doesn't match it → re-download, which is actually fine). The concurrency case I waved away with "out_dir is unique per run" without checking whether two workers in the *same* run could share it.

Gemma's review was thorough on the happy paths and the fail-closed invariant but, like mine, missed the interrupted-cut scenario entirely.

---

## 2. WHERE DO I AGREE OR DISAGREE?

| Finding | Source | Verdict | Reasoning |
|---|---|---|---|
| P1: early return skips duration check on `.cut.mp4` | Qwen | **Agree — and the fix is correct** | The Cycle 2 code now uses `whole_cut()` (exists **and** `media_seconds ≥ 50 %`) for the reuse path, and the cut is written atomically via `tmp` → `os.replace`. The new test (`test_a_partial_cut_left_behind_is_never_returned`) plants a 0-second file and verifies it is re-cut. Mutation P10 (revert to bare `exists`) is killed. |
| P2: partial whole-stream file silently reused | Qwen | **Partially agree — downgrade to P3** | yt-dlp writes to `<name>.part` during download and renames on completion. A timeout or SIGKILL leaves the `.part` file, which does **not** match `find()`'s stem filter. The next call re-downloads. The only edge case is a kill *between* rename and process exit, which leaves a complete file — correct to reuse. Not a real defect. |
| P2: no concurrency guard on `whole_stream` | Qwen | **Agree — still P2** | Two workers in the same run sharing `out_dir` can both see `find()` empty, both launch yt-dlp, and both write to the same path. The 30-minute timeout makes the collision window realistic. The atomic-cut fix does not help here because the race is on the *download*, not the *cut*. |
| P3: inline `import transcript_truth as TT` | Gemma, Qwen | **Agree — P3** | Now hoisted above the `whole_cut` lambda (required for the P1 fix), but still inside `fetch`. Stylistic; no functional issue. |
| P3: `WHOLE` dict only has `"audio"` | Qwen | **Agree — P3** | Video uses `FORMAT` from `visual_pin.py`. The dict name implies it covers both. Misleading but not wrong. |
| P3: `media_seconds` 60 s timeout | Qwen | **Agree — P3** | Local ffprobe returns in <1 s. 60 s is a safety net for NFS hangs. 10 s would be snappier. No correctness impact. |
| "No P0/P1/P2, logic is sound" | Gemma | **Disagree on P1** | Gemma missed the interrupted-cut path. Everything else Gemma said is correct. |

---

## 3. NEW FINDINGS FROM THIS REVIEW

### [P2] `whole_stream` — no concurrency guard (carried from Qwen, still unaddressed)

`pipeline/transcript_truth.py`, lines 35–37 (the `if not find():` block). Two pipeline workers processing different windows of the same `video_id` in the same `out_dir` both see `find()` empty, both launch `yt-dlp`, and both write to `os.path.join(out_dir, stem + ".%(ext)s")`. The second write corrupts or overwrites the first mid-download. The 1800-second timeout makes the overlap window realistic on a multi-GPU box.

The atomic-cut fix (tmp → `os.replace`) protects the *ffmpeg* step but not the *yt-dlp* step. A lock file (`<stem>.lock` with `O_CREAT | O_EXCL`) or a temp-name + atomic-rename around the yt-dlp call would close this.

### [P3] `audio_window` normal path — no output duration validation

`pipeline/transcript_truth.py`, lines 66–68. The normal (non-post_live) path does:

```python
subprocess.run(["ffmpeg", ..., "-i", src, "-ac", "1", "-ar", "16000", wav], check=True, timeout=120)
return wav, a
```

It validates `src`'s duration before entering this branch, but does not validate `wav`'s duration after the re-encode. In practice, a simple `-ac 1 -ar 16000` re-encode preserves duration, so this is not a real risk. But for symmetry with the whole-stream path (which does validate the output), a `media_seconds(wav)` check would make the invariant explicit. Nit.

### [P3] `whole_stream` — `find()` matches any extension

`pipeline/transcript_truth.py`, line 34. `os.path.splitext(f)[0] == stem` matches `vid.whole-audio.m4a`, `vid.whole-audio.webm`, `vid.whole-audio.mp4`, etc. If a previous run left a file with a different extension (e.g., a failed format negotiation), `have[0]` (alphabetically first) might be the wrong file. In practice yt-dlp produces one file per download and the stem is unique per video+tag, so this is theoretical.

### [P3] Test `Media.run` — ffmpeg output detection assumes `cmd[-1]` is the output

`tests/package/test_ruling_142_post_live.py`, line 156. `out = cmd[-1]` works for the current ffmpeg invocations (output is always the last argument), but would break if a future ffmpeg command appends a flag after the output path. Fragile but fine for the current code.

---

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| `transcript_truth.audio_window` | Sound | Sound | Fail-closed invariant holds. Atomic tmp→replace on the whole-stream cut. Normal path unchanged. |
| `transcript_truth.whole_stream` | Sound | **P2 (concurrency)** | Qwen's concurrency finding is valid and unaddressed. Partial-download concern downgraded to P3 (yt-dlp `.part` mechanism). |
| `visual_pin.fetch` | **P1 (missed)** | Sound | The P1 is fixed: `whole_cut()` validates duration on reuse; atomic tmp→replace; import hoisted. New test kills the mutation. |
| Tests | 8/8 | 9/9, comprehensive | New test for the partial-cut scenario. All critical paths covered. One P3 fragility in the stub. |
| Fail-closed invariant | Holds | Holds | No path returns a file with < 50 % of the expected window as "measured." |

---

## 5. FINAL PRIORITY LIST

| Severity | File / Line | Finding |
|---|---|---|
| **[P2]** | `transcript_truth.py` L35–37 | `whole_stream` has no concurrency guard. Two workers in the same `out_dir` can race on the yt-dlp download. Add a lock file or temp-name + atomic-rename around the download. |
| **[P3]** | `transcript_truth.py` L12 | `WHOLE` dict only contains `"audio"`; video format lives in `visual_pin.FORMAT`. Rename to `AUDIO_WHOLE` or add the video entry. |
| **[P3]** | `transcript_truth.py` L20 | `media_seconds` timeout of 60 s is excessive for a local ffprobe. 10 s is sufficient. |
| **[P3]** | `visual_pin.py` L77 | `import transcript_truth as TT` is still inline. Move to module level (no circular dependency exists). |
| **[P3]** | `transcript_truth.py` L66–68 | Normal-path `audio_window` does not validate the output wav's duration (symmetry with the whole-stream path). |

**P1_OR_WORSE: 0**

---

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Add a lock file (or temp-name + `os.replace`) around the yt-dlp download in `whole_stream` so that two workers in the same run cannot race on the same `video_id`/`tag` and corrupt each other's 30-minute download.

---

## 7. PRODUCTION READY?

**Yes, with one condition.**

The P1 from Cycle 1 (interrupted `.cut.mp4` returned without validation) is properly fixed with atomic writes, duration checks on every return path, and a dedicated regression test. The fail-closed invariant holds: no code path can return a file shorter than 50 % of the expected window as "measured." Normal (non-post_live) videos take the unchanged code path. The integrator's read-only cache is checked first. Tests are comprehensive (9 tests, 9/9 mutations killed).

**Condition:** Before this ships to a multi-worker pipeline (2+ concurrent story builds sharing an `out_dir`), the `whole_stream` download needs a concurrency guard (lock file or atomic temp-name). If the pipeline is strictly single-worker per `out_dir` (which the architecture appears to enforce), this is a P2 hardening item that can be tracked as a follow-up rather than a merge blocker.

P1_OR_WORSE: 0