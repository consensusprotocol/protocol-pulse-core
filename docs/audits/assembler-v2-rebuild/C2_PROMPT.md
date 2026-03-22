# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: assembler-v2-rebuild
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GROK — CYCLE 1 OUTPUT
### CODE REVIEW REPORT: PROTOCOL PULSE — ASSEMBLER-V2-REBUILD

Below is a detailed forensic review of the provided codebase for the `assembler-v2-rebuild` feature of Protocol Pulse. I have analyzed the code across multiple dimensions as requested, with a focus on correctness, compliance with governing laws, security, quality, and actionable improvements. My feedback is direct and prioritizes quality over sentiment.

---

### SECTION 1: CORRECTNESS

**Main User Flow Analysis (Episode Rendering via `episode.py`):**
1. **Initialization and Preflight (episode.py:83-106):** The flow starts with manifest validation and preflight checks for required assets and disk space. This is correct and robust, ensuring critical dependencies are in place before rendering begins.
2. **Context Creation (episode.py:108):** EpisodeContext is created with a unique workdir per episode, avoiding global state issues. This is correct and aligns with the design intent.
3. **Segment Rendering (episode.py:111-136):** Segments are rendered sequentially by mapping segment types to their respective classes. The logic correctly handles unknown segment types by generating filler content, though there’s no parallelization, which could be a performance bottleneck for large episodes.
4. **Concatenation (episode.py:143-180):** Segments are concatenated using FFmpeg’s concat demuxer. The logic is sound, ensuring only existing files are included, but it lacks retry logic if concatenation fails due to temporary I/O issues.
5. **Final QC and Verdict (episode.py:202-246):** Quality checks (black frames, silence, duration, LUFS) are performed post-concatenation. This is correct, but the verdict logic could override a "PASS" to "HOLD" without clear logging of the specific QC failure reason at the point of decision (episode.py:239-243).

**Logic Errors and Silent Failures:**
- **Silent Failure in Concatenation (episode.py:173-177):** If `run_ffmpeg` fails during concatenation, the error is logged, but there’s no fallback mechanism to retry or use a partial concat. This could silently result in a failed episode with no actionable recovery.
- **Metrics Cache Refresh Timing (data_segment.py:84-90):** The metrics refresh in `data_segment.py` uses a lock with a 5-second timeout, but if the lock isn’t acquired, it silently falls back to stale data or network calls without logging the lock contention. This could lead to outdated metrics in high-concurrency scenarios.

**Race Conditions:**
- **Metrics Cache File Access (data_segment.py:55-62, 93-98):** Multiple episodes rendering concurrently could race on `metrics_cache.json` writes in the episode-specific `workdir`. While `os.replace` provides some atomicity, there’s no explicit file locking beyond the `metrics_lock`, which could fail under heavy load if the timeout is hit.

**Edge Cases:**
- **Empty Segment List (episode.py:101-102):** Handled correctly by raising a ValueError, preventing an empty episode from proceeding.
- **Missing TTS/Clip Files (preflight.py:29-34, 36-43):** Preflight checks catch missing or empty files, but if a file is deleted post-preflight, the segment rendering will silently use filler without re-checking (e.g., narration.py:39-42). This could lead to unexpected filler usage in production.
- **API Timeouts in Metrics Fetch (data_segment.py:101-112):** Fallbacks to cached or default values are in place, but repeated timeouts could exhaust retries without clear logging of the root cause, potentially masking API quota issues.

**N+1 Query Problems:**
- Not applicable directly since there’s no DB interaction in the provided code. However, the sequential rendering of segments (episode.py:111-136) mimics an N+1 problem by processing each segment individually without batching or parallelism, which could be optimized.

---

### SECTION 2: LAW COMPLIANCE

**1. render() NEVER raises. filler_result() on any failure.**
- **COMPLIANT**: All segment rendering methods (e.g., cold_open.py:33-37, narration.py:22-27) wrap their logic in try/except blocks and return `filler_result()` on failure. No exceptions escape to the caller.

**2. CRF-only encoding. No -b:v/-maxrate/-bufsize alongside -crf.**
- **COMPLIANT**: Encoding commands in `encode.py` (e.g., encode.py:21-22) and segment files (e.g., cold_open.py:109-110) use `-crf` exclusively without bitrate controls, adhering to the law.

**3. EpisodeContext episode-scoped. No module globals.**
- **COMPLIANT**: `EpisodeContext` in `state.py` is passed explicitly to all functions needing state (e.g., episode.py:132). No module-level mutable globals are used for state management.

**4. ffprobe_contract: 1920x1080 h264 yuv420p 30fps aac 192k 48000hz stereo.**
- **COMPLIANT**: `ffprobe_contract` in `helpers.py:78-165` enforces these exact parameters, checking width, height, codec, pixel format, frame rate, audio bitrate, sample rate, and channels (e.g., helpers.py:101-129).

**5. Atomic writes via atomic_rename.**
- **COMPLIANT**: All file writes use `atomic

## GEMINI — CYCLE 1 OUTPUT
Here is a forensic code review of the `assembler-v2-rebuild` feature.

### SECTION 1: CORRECTNESS

The overall logic of the pipeline is sound and demonstrates a strong focus on robustness. The flow from manifest -> preflight -> segment rendering -> concatenation -> QC is logical and well-handled. However, there are several key correctness issues:

*   **Race Condition in Metrics Caching:** `data_segment.py` uses a `threading.Lock` (`state.py:37`) to protect the metrics cache. The technology stack mentions "~1000 concurrent users at peak", which implies a multi-process server configuration (e.g., Gunicorn with multiple workers). A `threading.Lock` **only works within a single process** and provides no protection against multiple processes trying to write to `metrics_cache.json` simultaneously. This will lead to corrupted cache files and race conditions where multiple processes all miss the cache and overwhelm the upstream `mempool.space` API (a "thundering herd" problem). A file-based lock or a centralized cache like Redis is required for multi-process safety.

*   **Massive Code Duplication in Segment Encoding:** The `ffmpeg_core/encode.py::encode_segment` function is an excellent, robust wrapper that handles temp files, contract checking, filler fallbacks, and atomic renaming. However, it is only used by `TransitionSegment` and `WrapSegment`. Nearly every other content-generating segment bypasses it and implements its own, less robust version of the same logic:
    *   `cold_open.py`
    *   `narration.py`
    *   `partner_clip.py`
    *   `data_segment.py`
    *   `social.py`
    *   `signal_active.py`
    *   `x_spaces_segment.py`
    This leads to significant code duplication, inconsistencies in error handling, and a much larger surface area for bugs. For example, the robust "emergency black frame" fallback in `encode_segment` is not available to any of the segments that bypass it.

*   **Inconsistent Tooling Usage:** The `ffmpeg_core/probe.py` module uses `subprocess.run` directly instead of the centralized `run_ffmpeg` helper. While this may be to facilitate parsing `stderr`, it adds an inconsistency. The `stderr` parsing itself (`probe.py:16-19`, `probe.py:24-26`) is brittle and relies on string searching and slicing, which could easily break with minor changes in ffmpeg's log output format.

*   **Poor Code Formatting:** `preflight.py` is extremely difficult to read due to cramming multiple statements on single lines, single-letter variable names, and lack of whitespace. This impedes auditing and future maintenance.

### SECTION 2: LAW COMPLIANCE

*   **LAW 1: render() NEVER raises. filler_result() on any failure.**
    *   **COMPLIANT.** Every `Segment.render()` implementation is wrapped in a top-level `try...except Exception` block that correctly calls `self.filler_result()`.

*   **LAW 2: CRF-only encoding. No -b:v/-maxrate/-bufsize alongside -crf.**
    *   **COMPLIANT.** All video encoding calls correctly use the `-crf` flag for rate control and do not mix it with incompatible bitrate flags like `-b:v`. The use of `-b:a` for audio is standard practice and not a violation of this video-specific law.

*   **LAW 3: EpisodeContext episode-scoped. No module globals.**
    *   **COMPLIANT.** All mutable state is correctly managed within the `EpisodeContext` instance, which is passed throughout the call stack. Read-only constants like asset paths are defined at the module level, which is acceptable.

*   **LAW 4: ffprobe_contract: 1920x1080 h264 yuv420p 30fps aac 192k 48000hz stereo.**
    *   **COMPLIANT.** The function `helpers.py:ffprobe_contract` at line 77 meticulously checks for every specified parameter, including codecs, dimensions, framerate, and audio properties with appropriate tolerances.

*   **LAW 5: Atomic writes via atomic_rename.**
    *   **COMPLIANT.** All final file outputs are written to temporary files first and then moved to their final destination using `atomic_rename` (which correctly uses `os.replace`). This is seen in `encode.py:66`, `episode.py:191`, and across many segment files.

*   **LAW 6: safe_text() from helpers.py is the single drawtext sanitizer.**
    *   **COMPLIANT.** All `drawtext` filter strings that use dynamic text correctly sanitize it via `helpers.safe_text`. Examples: `partner_clip.py:65`, `narration.py:123`, `data_segment.py:141`.

*   **LAW 7: PiP: eof_action=repeat. stream_loop=-1 on pre-normalized pip_preview.**
    *   **COMPLIANT.** `narration.py:127,130` correctly use `-stream_loop -1` on the PiP input file. The corresponding `overlay` filter in `narration.py:70` correctly uses `eof_action=repeat`.

*   **LAW 8: Metrics cache scoped to ctx.workdir NOT /tmp.**
    *   **COMPLIANT.** `data_segment.py:140` correctly sets the cache path to `ctx.workdir/"metrics_cache.json"`.

*   **LAW 9: Outro: -an strips audio before stream_loop.**
    *   **COMPLIANT.** `wrap.py:38,53` correctly include `-an` in the input options for `OUTRO_BRANDED` alongside `-stre

## GPT4O — CYCLE 1 OUTPUT
## SECTION 1: CORRECTNESS

### Main flow walkthrough

#### 1) `EpisodeRunner.run()` / `_run()`
- `run()` correctly wraps `_run()` in a broad `try/except`, so the **episode-level entrypoint never raises** and returns an `EpisodeReport` on fatal error. Good for top-level robustness. (`episode.py:69-80`)
- `_run()` validates the manifest, runs preflight, creates an episode-scoped context, renders each segment, concatenates outputs, then performs final contract/QC checks. The overall orchestration is coherent. (`episode.py:82-260`)

#### 2) Preflight ordering bug
- Preflight is run **before** `EpisodeContext.create()`, and it receives `output_dir` rather than the episode workdir. (`episode.py:94-108`)
- This is not a crash bug by itself, but it means disk checks are against the parent output directory, not the actual workdir mount/path if those differ. More importantly, any preflight checks that should be episode-scoped cannot use `ctx.workdir` yet.

#### 3) Unknown segment type handling double-counts degradation
- For unknown segment types, `_run()` explicitly calls `ctx.mark_degraded(...)` and then creates a filler via `_make_unknown_filler()`. (`episode.py:115-128`)
- If `_make_unknown_filler()` fails, `RenderedSegment.contract_passed` becomes false, but no fallback beyond that exists. The episode still proceeds.
- Also, this path is inconsistent with the rest of the segment system, which uses `filler_result()` and central degraded accounting.

#### 4) Segment rendering generally follows “never raise”
- Most segment `render()` methods wrap `_render()` in `try/except` and return `self.filler_result(...)` on exception. Good. Examples: `transition.py:15-20`, `wrap.py:19-24`, `cold_open.py:31-37`, `narration.py:21-27`, `partner_clip.py:42-47`, `data_segment.py:121-126`, `social.py:27-33`, `signal_active.py:31-37`, `x_spaces_segment.py:28-34`.

#### 5) Major correctness issue: `filler_result()` can leave no output file
- `Segment.filler_result()` calls `make_filler(output_path, ...)` directly, not via temp + atomic rename. (`segments/base.py:32-60`)
- If `make_filler()` fails, it tries an emergency ffmpeg write directly to `output_path`. (`segments/base.py:37-55`)
- If that also fails, it returns `RenderedSegment(... path=None, contract_passed=False, degraded=True ...)`. (`segments/base.py:57-60`)
- This violates the stated invariant in `RenderedSegment` docstring: “Always populated — degraded=True if filler used.” (`manifest.py:42`)
- It also undermines concat completeness because missing segment files are silently skipped later. (`episode.py:143`)

#### 6) Silent truncation of failed segments in final episode
- Final concat only includes segment reports whose `path` exists. (`episode.py:143`)
- If a segment fails so badly that even filler creation fails, that segment is simply omitted from the final episode rather than forcing a HOLD immediately.
- This can produce a final episode missing required content while still reaching concat/QC stages. That is a production correctness problem.

#### 7) `encode_segment()` return contract is misleading
- `encode_segment()` claims “Write filler to output_path. Never raises.” (`ffmpeg_core/encode.py:31-32`)
- But on failure it returns `(False, False, summary, ms)` even if filler was successfully written. (`ffmpeg_core/encode.py:57-70`)
- Callers then infer degradation from `primary_ok` or `summary["filler_used"]`. This works, but the boolean naming is confusing and easy to misuse.

#### 8) `TransitionSegment` duration reporting can be wrong
- It always returns `duration=dur` (0.25s), even if encode fallback wrote a filler of a different duration or ffprobe summary says otherwise. (`segments/transition.py:65-68`)
- This is minor but inaccurate.

#### 9) `NarrationSegment` double degradation accounting
- On post-publish contract failure, it calls `ctx.mark_degraded(...)` and then calls `self.filler_result(...)`, which itself also calls `ctx.mark_degraded(...)`. (`segments/narration.py:53-57`, `segments/base.py:56`)
- This **double-counts degraded segments and filler seconds** for one failure.
- That directly affects verdict logic in `EpisodeContext.verdict()`. (`state.py:72-83`)

#### 10) `ffprobe_contract()` audio codec check nested incorrectly
- Video codec check is inside the `else:` block for audio presence. (`helpers.py:116-129`)
- If a file has video but no audio, the code never checks whether the video codec is h264.
- Since the contract requires both streams, this won’t create a false pass, but it makes diagnostics incomplete and contract enforcement less precise.

#### 11) `ffprobe_contract()` does not verify stereo layout name, only channels
- Law requires stereo; code checks `channels == 2` but not channel layout. (`helpers.py:119-124`)
- Usually acceptable, but not a strict contract match.

#### 12) `normalize_pip_preview()` does not validate output contract
- It logs success if ffmpeg succeeded and file exists. (`helpers.py:276-279`)
- No `ffprobe_contract()`-sty

## CLAUDE'S CYCLE 1 CONSENSUS
# CONSENSUS REPORT — ASSEMBLER-V2-REBUILD — CYCLE 1
Generated: 2026-03-18 18:06
Models: grok, gemini, gpt4o

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Correctness | 6.5/10 | 6.0/10 | 7.0/10 | **6.5/10** |
| Law Compliance | 9.5/10 | 9.0/10 | 9.0/10 | **9.2/10** |
| Security | 7.0/10 | 7.5/10 | 7.0/10 | **7.2/10** |
| Backend Quality | 7.0/10 | 7.0/10 | 6.5/10 | **6.8/10** |
| Overall | 7.5/10 | 7.0/10 | 7.5/10 | **7.3/10** |

*Scores extracted by synthesis. No model provided explicit numeric scores; these are calibrated from language ("robust," "very robust," specific severity of issues raised).*

---

## UNANIMOUS FINDINGS
*All 3 models agree — implement unconditionally.*

---

### U1 — Rate Limiting on ElevenLabs API is Absent
**What:** `social.py`, `signal_active.py`, and `x_spaces_segment.py` all call the ElevenLabs TTS API on cache miss with zero rate-limiting or per-episode quota guard. A single large episode, or concurrent renders, could exhaust API quotas, incur runaway cost, or silently produce silence-filled episodes with no operator alert.
**Files:** `segments/social.py:98-105`, `segments/signal_active.py:180-195`, `segments/x_spaces_segment.py:97-110`
**Change:** Implement a per-process semaphore and/or a token-bucket rate limiter around all ElevenLabs call sites. Add a per-episode cap (e.g., max N TTS calls). On quota error, log a distinct `QUOTA_EXCEEDED` event and degrade gracefully rather than silently.

---

### U2 — Hardcoded ElevenLabs `voice_id` Magic String
**What:** All three TTS call sites hardcode the same voice ID string `'1SM7GgM6IMuvQlz2BwM3'`. If the voice is deprecated or a new voice is required for A/B testing, three files must be changed. This is a maintenance and consistency hazard.
**Files:** `segments/social.py:98`, `segments/signal_active.py:183`, `segments/x_spaces_segment.py:97`
**Change:** Extract to a single named constant: `ELEVENLABS_VOICE_ID = '1SM7GgM6IMuvQlz2BwM3'` in a config or constants module. All three sites reference the constant.

---

### U3 — Massive Encode Path Duplication (Segment Bypass of `encode_segment`)
**What:** `encode_segment()` in `ffmpeg_core/encode.py` is a robust wrapper providing temp-file writes, contract checking, filler fallback, and atomic rename. However, `cold_open.py`, `narration.py`, `partner_clip.py`, `data_segment.py`, `social.py`, `signal_active.py`, and `x_spaces_segment.py` all bypass it and re-implement subset versions of this logic inconsistently. The "emergency black frame" safety net exists only in `encode_segment` — segments that bypass it have no equivalent last-resort fallback.
**Files:** `segments/cold_open.py`, `segments/narration.py`, `segments/partner_clip.py`, `segments/data_segment.py`, `segments/social.py`, `segments/signal_active.py`, `segments/x_spaces_segment.py`
**Change:** Refactor all segment encode paths to route through `encode_segment()`. Each segment's `_render()` should build the ffmpeg argumen

---

## ORIGINAL CODE (same code as Cycle 1)
## THE CODE (every new and modified file)

### File: video_pipeline_v3/assembler_v2/constants.py (66 lines)
```
   1 | """
   2 | Protocol Pulse V2 — constants.py
   3 | IMMUTABLE CODEC LAW. Every segment must conform. No exceptions.
   4 | """
   5 | from pathlib import Path
   6 | 
   7 | # ── Video ──────────────────────────────────────────────────────────
   8 | VIDEO_W        = 1920
   9 | VIDEO_H        = 1080
  10 | VIDEO_FPS      = 30
  11 | VIDEO_PIX_FMT  = "yuv420p"
  12 | VIDEO_CODEC    = "libx264"
  13 | VIDEO_CRF      = 17
  14 | VIDEO_PRESET   = "medium"
  15 | 
  16 | # ── Audio ──────────────────────────────────────────────────────────
  17 | AUDIO_CODEC        = "aac"
  18 | AUDIO_BITRATE      = "192k"
  19 | AUDIO_SAMPLE_RATE  = 48000
  20 | AUDIO_CHANNELS     = 2
  21 | AUDIO_FORMAT       = "fltp"
  22 | AUDIO_TARGET_LUFS  = -14.0
  23 | AUDIO_MAX_TRUE_PEAK = -2.0
  24 | AUDIO_LRA          = 7.0
  25 | AUDIO_LIMITER      = 0.85
  26 | 
  27 | # ── Asset paths ────────────────────────────────────────────────────
  28 | PIPELINE_DIR   = Path(__file__).parent.parent
  29 | ASSETS_DIR     = PIPELINE_DIR / "assets"
  30 | INTRO_TAG      = ASSETS_DIR / "intro_tag.mp4"
  31 | INTRO_MUSIC    = ASSETS_DIR / "intro_music.mp3"
  32 | BG_LOOP        = ASSETS_DIR / "bg_loop.mp4"
  33 | OUTRO_BRANDED  = ASSETS_DIR / "outro_branded_new.mp4"
  34 | SCANLINE       = ASSETS_DIR / "scanline_overlay.png"
  35 | SFX_WHOOSH     = ASSETS_DIR / "sfx" / "custom_whoosh.wav"
  36 | SFX_SWOOSH     = ASSETS_DIR / "sfx" / "card_swoosh.wav"
  37 | FONT_BOLD      = ASSETS_DIR / "fonts" / "JetBrainsMono-Bold.ttf"
  38 | FONT_MONO      = ASSETS_DIR / "fonts" / "JetBrainsMono-Regular.ttf"
  39 | CHARTS_DIR     = PIPELINE_DIR / "cache" / "charts"
  40 | OUTPUT_DIR     = PIPELINE_DIR / "output"
  41 | 
  42 | # ── Brand colors (ffmpeg hex format) ──────────────────────────────
  43 | COLOR_BG    = "0x0A0A0F"
  44 | COLOR_RED   = "0xFF3B5F"
  45 | COLOR_WHITE = "0xFFFFFF"
  46 | COLOR_CYAN  = "0x5DE4FF"
  47 | COLOR_GOLD  = "0xFFD700"
  48 | 
  49 | # ── QC acceptance policy ───────────────────────────────────────────
  50 | QC_MIN_DURATION          = 480    # 8 minutes
  51 | QC_MAX_DURATION          = 900    # 15 minutes
  52 | QC_MAX_FILLER_SECONDS    = 60
  53 | QC_MAX_DEGRADED_SEGMENTS = 2
  54 | QC_MAX_BLACK_FRAME_S     = 2.0
  55 | QC_MAX_SILENCE_S         = 2.0
  56 | QC_EPISODE_SILENCE_HOLD_S = QC_MAX_SILENCE_S * 3  # 6.0s — per-episode silence HOLD threshold
  57 | QC_MIN_LUFS              = -17.0
  58 | QC_MAX_LUFS              = -13.0
  59 | QC_MAX_TRUE_PEAK         = -1.0
  60 | 
  61 | # FFmpeg operation timeouts
  62 | FFMPEG_TIMEOUT_ENCODE = 300
  63 | FFMPEG_TIMEOUT_FILTER = 120
  64 | FFMPEG_TIMEOUT_PROBE  =  15
  65 | FFMPEG_TIMEOUT_SHORT  =  30
  66 | 
```

### File: video_pipeline_v3/assembler_v2/helpers.py (349 lines)
```
   1 | """
   2 | Protocol Pulse V2 — helpers.py
   3 | Core utilities. Every ffmpeg call goes through run_ffmpeg(). No exceptions.
   4 | """
   5 | from __future__ import annotations
   6 | import subprocess, json, os, time, shutil, logging
   7 | from pathlib import Path
   8 | from typing import Optional
   9 | from .constants import (
  10 |     VIDEO_W, VIDEO_H, VIDEO_FPS, VIDEO_PIX_FMT, VIDEO_CODEC, VIDEO_CRF,
  11 |     AUDIO_CODEC, AUDIO_BITRATE, AUDIO_SAMPLE_RATE, AUDIO_CHANNELS,
  12 |     COLOR_BG, CHARTS_DIR,
  13 |     FFMPEG_TIMEOUT_ENCODE, FFMPEG_TIMEOUT_FILTER, FFMPEG_TIMEOUT_PROBE
  14 | )
  15 | 
  16 | logger = logging.getLogger(__name__)
  17 | 
  18 | 
  19 | # ── Core FFmpeg runner ────────────────────────────────────────────────────────
  20 | 
  21 | def run_ffmpeg(args: list, label: str = "", timeout: int = FFMPEG_TIMEOUT_ENCODE) -> bool:
  22 |     """
  23 |     Single authoritative ffmpeg runner. All segments use this. Never bypass.
  24 |     Logs full command, duration, and stderr on failure.
  25 |     """
  26 |     cmd = ["ffmpeg", "-y"] + [str(a) for a in args]
  27 |     full_cmd = ' '.join(cmd)
  28 |     logger.debug(f"[ffmpeg] {label} | full cmd: {full_cmd}")
  29 |     logger.info(f"[ffmpeg] {label} | cmd: {' '.join(cmd[:10])}...")
  30 |     t0 = time.time()
  31 |     try:
  32 |         result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
  33 |         elapsed = round(time.time() - t0, 2)
  34 |         if result.returncode != 0:
  35 |             logger.error(f"[ffmpeg] FAIL {label} ({elapsed}s) rc={result.returncode}")
  36 |             logger.error(f"[ffmpeg] STDERR: {result.stderr[-1200:]}")
  37 |             return False
  38 |         logger.info(f"[ffmpeg] OK {label} ({elapsed}s)")
  39 |         return True
  40 |     except subprocess.TimeoutExpired:
  41 |         logger.error(f"[ffmpeg] TIMEOUT {label} after {timeout}s")
  42 |         return False
  43 |     except Exception as e:
  44 |         logger.error(f"[ffmpeg] EXCEPTION {label}: {e}")
  45 |         return False
  46 | 
  47 | 
  48 | # ── FFprobe utilities ─────────────────────────────────────────────────────────
  49 | 
  50 | def ffprobe_duration(path: Path) -> float:
  51 |     """Return audio/video duration in seconds. Returns 0.0 on any error."""
  52 |     try:
  53 |         r = subprocess.run(
  54 |             ["ffprobe", "-v", "error", "-show_entries", "format=duration",
  55 |              "-of", "csv=p=0", str(path)],
  56 |             capture_output=True, text=True, timeout=FFMPEG_TIMEOUT_PROBE
  57 |         )
  58 |         val = r.stdout.strip()
  59 |         return float(val) if val else 0.0
  60 |     except Exception:
  61 |         return 0.0
  62 | 
  63 | 
  64 | def ffprobe_streams(path: Path) -> dict:
  65 |     """Return full ffprobe JSON. Returns {} on error."""
  66 |     try:
  67 |         r = subprocess.run(
  68 |             ["ffprobe", "-v", "error", "-print_format", "json",
  69 |              "-show_streams", "-show_format", str(path)],
  70 |             capture_output=True, text=True, timeout=FFMPEG_TIMEOUT_PROBE
  71 |         )
  72 |         return json.loads(r.stdout)
  73 |     except Exception:
  74 |         return {}
  75 | 
  76 | 
  77 | def ffprobe_contract(path: Path) -> tuple:
  78 |     """
  79 |     Verify segment meets the V2 output contract.
  80 |     Returns (passed: bool, summary: dict).
  81 |     Every segment is checked after render. Filler used if failed.
  82 |     """
  83 |     if not path.exists() or path.stat().st_size < 1000:
  84 |         return False, {"error": "file missing or too small", "passed": False}
  85 | 
  86 |     info = ffprobe_streams(path)
  87 |     if not info:
  88 |         return False, {"error": "ffprobe returned no data", "passed": False}
  89 | 
  90 |     streams = info.get("streams", [])
  91 |     fmt = info.get("format", {})
  92 |     video = next((s for s in streams if s.get("codec_type") == "video"), None)
  93 |     audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
  94 | 
  95 |     duration = float(fmt.get("duration", 0))
  96 |     issues = []
  97 | 
  98 |     if not video:
  99 |         issues.append("no video stream")
 100 |     else:
 101 |         if video.get("width") != VIDEO_W:
 102 |             issues.append(f"width={video.get('width')} (need {VIDEO_W})")
 103 |         if video.get("height") != VIDEO_H:
 104 |             issues.append(f"height={video.get('height')} (need {VIDEO_H})")
 105 |         if video.get("pix_fmt") != VIDEO_PIX_FMT:
 106 |             issues.append(f"pix_fmt={video.get('pix_fmt')} (need {VIDEO_PIX_FMT})")
 107 |         fps_str = video.get("r_frame_rate", "0/1")
 108 |         try:
 109 |             n, d = fps_str.split("/")
 110 |             fps = float(n) / float(d)
 111 |             if abs(fps - VIDEO_FPS) > 0.5:
 112 |                 issues.append(f"fps={fps:.2f} (need {VIDEO_FPS})")
 113 |         except Exception:
 114 |             issues.append(f"unparseable fps: {fps_str}")
 115 | 
 116 |     if not audio:
 117 |         issues.append("no audio stream")
 118 |     else:
 119 |         sr = int(audio.get("sample_rate", 0))
 120 |         if sr != AUDIO_SAMPLE_RATE:
 121 |             issues.append(f"sample_rate={sr} (need {AUDIO_SAMPLE_RATE})")
 122 |         ch = audio.get("channels", 0)
 123 |         if ch != AUDIO_CHANNELS:
 124 |             issues.append(f"channels={ch} (need {AUDIO_CHANNELS})")
 125 |         # Codec checks — critical for concat compatibility
 126 |         if video and video.get("codec_name") != "h264":
 127 |             issues.append(f"video_codec={video.get('codec_name')} (need h264)")
 128 |         if audio.get("codec_name") != AUDIO_CODEC:
 129 |             issues.append(f"audio_codec={audio.get('codec_name')} (need {AUDIO_CODEC})")
 130 |         # Audio bitrate check — ±10% tolerance for VBR rounding (192k = 192000 bps)
 131 |         # AAC VBR compresses silence very efficiently, so short or silent segments
 132 |         # will average far below nominal. Upper bound always checked (catches wrong
 133 |         # -b:a setting). Lower bound only reliable on segments >= 30s with real audio.
 134 |         raw_br = audio.get("bit_rate", 0)
 135 |         try:
 136 |             audio_br = int(raw_br)
 137 |         except (ValueError, TypeError):
 138 |             audio_br = 0
 139 |         if audio_br > 211200:
 140 |             issues.append(f"audio_bitrate={audio_br} too high (max 211200)")
 141 |         elif audio_br > 0 and duration >= 30.0 and audio_br < 172800:
 142 |             issues.append(f"audio_bitrate={audio_br} too low (min 172800)")
 143 | 
 144 |     passed = len(issues) == 0
 145 | 
 146 |     summary = {
 147 |         "passed": passed,
 148 |         "issues": issues,
 149 |         "duration": round(duration, 3),
 150 |         "video_codec": video.get("codec_name") if video else None,
 151 |         "audio_codec": audio.get("codec_name") if audio else None,
 152 |         "width": video.get("width") if video else None,
 153 |         "height": video.get("height") if video else None,
 154 |         "fps": fps_str if video else None,
 155 |         "pix_fmt": video.get("pix_fmt") if video else None,
 156 |         "sample_rate": audio.get("sample_rate") if audio else None,
 157 |         "channels": audio.get("channels") if audio else None,
 158 |     }
 159 | 
 160 |     if issues:
 161 |         logger.warning(f"[contract] FAIL {path.name}: {', '.join(issues)}")
 162 |     else:
 163 |         logger.info(f"[contract] PASS {path.name} ({duration:.1f}s)")
 164 | 
 165 |     return passed, summary
 166 | 
 167 | 
 168 | # ── Filler segment ────────────────────────────────────────────────────────────
 169 | 
 170 | def make_filler(output_path: Path, duration: float,
 171 |                 tts_path: Optional[Path] = None) -> bool:
 172 |     """
 173 |     Generate a contract-compliant filler segment.
 174 |     Uses TTS audio if available so PBX voice continues even if video failed.
 175 |     Dark background — clearly not final content but episode continues.
 176 |     """
 177 |     dur = max(float(duration), 5.0)
 178 |     if float(duration) < 5.0:
 179 |         logger.info(f"[filler] 5s floor applied (requested {duration:.1f}s)")
 180 | 
 181 |     if tts_path and tts_path.exists() and tts_path.stat().st_size > 1000:
 182 |         ok = run_ffmpeg([
 183 |             "-f", "lavfi", "-i",
 184 |             f"color=c={COLOR_BG}:s={VIDEO_W}x{VIDEO_H}:r={VIDEO_FPS}",
 185 |             "-i", str(tts_path),
 186 |             "-map", "0:v", "-map", "1:a",
 187 |             "-c:v", VIDEO_CODEC, "-crf", str(VIDEO_CRF), "-preset", "veryfast",
 188 |             "-pix_fmt", VIDEO_PIX_FMT, "-r", str(VIDEO_FPS),
 189 |             "-c:a", AUDIO_CODEC, "-ar", str(AUDIO_SAMPLE_RATE), "-b:a", AUDIO_BITRATE,
 190 |             "-ac", str(AUDIO_CHANNELS),
 191 |             "-t", str(dur), "-shortest",
 192 |             str(output_path)
 193 |         ], f"filler+audio {output_path.name}", FFMPEG_TIMEOUT_FILTER)
 194 |     else:
 195 |         ok = run_ffmpeg([
 196 |             "-f", "lavfi", "-i",
 197 |             f"color=c={COLOR_BG}:s={VIDEO_W}x{VIDEO_H}:r={VIDEO_FPS}",
 198 |             "-f", "lavfi", "-i",
 199 |             f"anullsrc=r={AUDIO_SAMPLE_RATE}:cl=stereo",
 200 |             "-c:v", VIDEO_CODEC, "-crf", str(VIDEO_CRF), "-preset", "veryfast",
 201 |             "-pix_fmt", VIDEO_PIX_FMT, "-r", str(VIDEO_FPS),
 202 |             "-c:a", AUDIO_CODEC, "-ar", str(AUDIO_SAMPLE_RATE), "-b:a", AUDIO_BITRATE,
 203 |             "-ac", str(AUDIO_CHANNELS),
 204 |             "-t", str(dur),
 205 |             str(output_path)
 206 |         ], f"filler+silence {output_path.name}", FFMPEG_TIMEOUT_FILTER)
 207 | 
 208 |     return ok and output_path.exists() and output_path.stat().st_size > 1000
 209 | 
 210 | 
 211 | # ── Atomic file operations ────────────────────────────────────────────────────
 212 | 
 213 | def atomic_rename(src: Path, dst: Path) -> bool:
 214 |     """
 215 |     Atomically move src to dst. Never leaves partial files at dst.
 216 |     Uses os.replace() for POSIX atomicity. Falls back to copy+replace
 217 |     for cross-device moves.
 218 |     """
 219 |     try:
 220 |         dst.parent.mkdir(parents=True, exist_ok=True)
 221 |         try:
 222 |             os.replace(str(src), str(dst))
 223 |         except OSError:
 224 |             # Cross-device: copy then atomic swap
 225 |             tmp_copy = dst.with_suffix(dst.suffix + ".atomic_tmp")
 226 |             shutil.copy2(str(src), str(tmp_copy))
 227 |             os.replace(str(tmp_copy), str(dst))
 228 |             src.unlink(missing_ok=True)
 229 |         logger.info(f"[atomic] {src.name} -> {dst}")
 230 |         return True
 231 |     except Exception as e:
 232 |         logger.error(f"[atomic] FAIL {src} -> {dst}: {e}")
 233 |         return False
 234 | 
 235 | 
 236 | # ── PiP pre-normalization ─────────────────────────────────────────────────────
 237 | 
 238 | def normalize_pip_preview(clip_path: Path, output_path: Path,
 239 |                            duration: float = 8.0) -> bool:
 240 |     """
 241 |     Pre-normalize a partner clip to pip_preview_norm format.
 242 |     Run ONCE per clip in Stage 2, NOT inside narration renders.
 243 |     Output: 640x360, yuv420p, 30fps CFR, no audio, h264 crf=18, hue=s=0.25.
 244 |     This pre-processing means narration.py only does a simple overlay.
 245 |     No zoompan, no heavy real-time transforms.
 246 |     """
 247 |     if not clip_path.exists() or clip_path.stat().st_size < 50000:
 248 |         logger.warning(f"[pip_norm] clip missing or tiny: {clip_path}")
 249 |         return False
 250 | 
 251 |     clip_dur = ffprobe_duration(clip_path)
 252 |     if clip_dur < 2.0:
 253 |         logger.warning(f"[pip_norm] clip too short ({clip_dur:.1f}s): {clip_path.name}")
 254 |         return False
 255 | 
 256 |     # Extract from midpoint — better face/content shots
 257 |     start = max(0.0, (clip_dur / 2.0) - (duration / 2.0))
 258 |     actual_dur = min(duration, clip_dur - start)
 259 | 
 260 |     ok = run_ffmpeg([
 261 |         "-ss", str(round(start, 3)),
 262 |         "-i", str(clip_path),
 263 |         "-t", str(round(actual_dur, 3)),
 264 |         "-an",
 265 |         "-vf", (
 266 |             "scale=640:360:force_original_aspect_ratio=decrease,"
 267 |             "pad=640:360:(ow-iw)/2:(oh-ih)/2:black,"
 268 |             f"fps={VIDEO_FPS},"
 269 |             f"format={VIDEO_PIX_FMT},"
 270 |             "hue=s=0.25"
 271 |         ),
 272 |         "-c:v", VIDEO_CODEC, "-crf", "18", "-preset", "veryfast",
 273 |         str(output_path)
 274 |     ], f"pip_norm {clip_path.name}", FFMPEG_TIMEOUT_FILTER)
 275 | 
 276 |     if ok and output_path.exists():
 277 |         logger.info(f"[pip_norm] OK {output_path.name} ({actual_dur:.1f}s)")
 278 |         return True
 279 |     return False
 280 | 
 281 | 
 282 | # ── Chart PNG helper ──────────────────────────────────────────────────────────
 283 | 
 284 | def get_chart_path(keyword: str) -> Optional[Path]:
 285 |     """
 286 |     Map narration keyword to chart PNG path.
 287 |     Returns None if chart missing — caller must handle gracefully.
 288 |     """
 289 |     mapping = {
 290 |         "price": CHARTS_DIR / "price_chart.png",
 291 |         "hashrate": CHARTS_DIR / "hashrate_chart.png",
 292 |         "mempool": CHARTS_DIR / "dominance_chart.png",
 293 |         "dominance": CHARTS_DIR / "dominance_chart.png",
 294 |     }
 295 |     path = mapping.get(keyword.lower())
 296 |     if path and path.exists() and path.stat().st_size > 1000:
 297 |         return path
 298 |     # Return None for unmapped keywords — segment handles missing chart gracefully
 299 |     # Never return a wrong chart (content integrity rule)
 300 |     if keyword and keyword.lower() not in mapping:
 301 |         logger.warning(f"[chart] unmapped chart keyword '{keyword}' — returning None")
 302 |         return None
 303 |     # For empty keyword (show all charts), return None — segment handles grid layout
 304 |     return None
 305 | 
 306 | def write_concat_list(paths: list, dest: Path) -> bool:
 307 |     """Write FFmpeg concat demuxer list file with proper path escaping.
 308 |     Single quotes in paths are escaped as '\\'' for the concat demuxer format.
 309 |     Writes atomically via temp file. Returns True on success."""
 310 |     try:
 311 |         import tempfile
 312 |         lines = []
 313 |         for p in paths:
 314 |             escaped = str(p).replace("'", "'\\''")
 315 |             lines.append(f"file '{escaped}'")
 316 |         content = "\n".join(lines) + "\n"
 317 |         with tempfile.NamedTemporaryFile(
 318 |             mode='w', dir=str(dest.parent), suffix='.tmp', delete=False
 319 |         ) as f:
 320 |             f.write(content)
 321 |             tmp_path = Path(f.name)
 322 |         os.replace(str(tmp_path), str(dest))
 323 |         return True
 324 |     except Exception as e:
 325 |         logger.error(f"[helpers] write_concat_list failed: {e}")
 326 |         return False
 327 | 
 328 | 
 329 | def safe_text(text, max_chars=80):
 330 |     """
 331 |     Single authoritative text sanitizer for FFmpeg drawtext filter values.
 332 |     FFmpeg drawtext escape rules:
 333 |       - Backslash must be escaped first: \\ → \\\\
 334 |       - Single quotes are the text= delimiter, escape as: ' → '\\''
 335 |         (close quote, literal escaped quote, reopen quote)
 336 |       - Colons, percent signs, brackets, commas, semicolons need backslash escape
 337 |       - Newlines replaced with space (drawtext does not support literal newlines)
 338 |     Every drawtext text= value MUST go through this function. No exceptions.
 339 |     """
 340 |     t = str(text).strip()[:max_chars]
 341 |     # Backslash first (before any other escape introduces backslashes)
 342 |     t = t.replace("\\", "\\\\")
 343 |     # Single quote: FFmpeg drawtext escape sequence
 344 |     t = t.replace("'", "'\\''")
 345 |     # Special chars that need backslash escaping in drawtext
 346 |     for ch in (":", "%", "[", "]", ",", ";"):
 347 |         t = t.replace(ch, "\\" + ch)
 348 |     return t.replace("\n", " ")
 349 | 
```

### File: video_pipeline_v3/assembler_v2/manifest.py (122 lines)
```
   1 | """
   2 | Protocol Pulse V2 — manifest.py
   3 | Episode manifest and segment spec dataclasses.
   4 | The manifest is the single source of truth for every episode.
   5 | """
   6 | from __future__ import annotations
   7 | from dataclasses import dataclass, field, asdict
   8 | from pathlib import Path
   9 | from typing import Optional
  10 | import json, uuid, time, os
  11 | 
  12 | 
  13 | @dataclass
  14 | class SegmentSpec:
  15 |     """Complete specification for one segment. Passed to segment.render()."""
  16 |     segment_type: str           # cold_open|narration|partner_clip|transition|data|social|signal_active|wrap
  17 |     clip_rank: int = 0          # partner clip rank (0 = no clip)
  18 |     tts_path: Optional[str] = None      # absolute path to ElevenLabs m4a
  19 |     clip_path: Optional[str] = None     # absolute path to partner clip mp4
  20 |     pip_path: Optional[str] = None      # absolute path to pip_preview_norm_{rank}.mp4
  21 |     headline: str = ""
  22 |     body: str = ""
  23 |     chart_keyword: str = ""     # "price"|"hashrate"|"mempool"|""
  24 |     social_posts: list = field(default_factory=list)
  25 |     signal_content: dict = field(default_factory=dict)
  26 |     is_required: bool = False   # filler still marks episode DEGRADED if True
  27 |     duration_hint: float = 0.0  # from ffprobe(tts_path)
  28 |     btc_price: str = "N/A"
  29 | 
  30 |     def tts(self) -> Optional[Path]:
  31 |         return Path(self.tts_path) if self.tts_path else None
  32 | 
  33 |     def clip(self) -> Optional[Path]:
  34 |         return Path(self.clip_path) if self.clip_path else None
  35 | 
  36 |     def pip(self) -> Optional[Path]:
  37 |         return Path(self.pip_path) if self.pip_path else None
  38 | 
  39 | 
  40 | @dataclass
  41 | class RenderedSegment:
  42 |     """Result of segment.render(). Always populated — degraded=True if filler used."""
  43 |     spec: SegmentSpec
  44 |     path: Optional[str] = None          # absolute path to rendered mp4
  45 |     duration: float = 0.0
  46 |     contract_passed: bool = False
  47 |     degraded: bool = False
  48 |     render_ms: int = 0
  49 |     ffprobe_summary: dict = field(default_factory=dict)
  50 |     error: str = ""
  51 | 
  52 |     def output(self) -> Optional[Path]:
  53 |         return Path(self.path) if self.path else None
  54 | 
  55 | 
  56 | @dataclass
  57 | class EpisodeManifest:
  58 |     """Complete episode plan. Written before any ffmpeg is called."""
  59 |     episode_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
  60 |     date_str: str = ""
  61 |     title: str = ""
  62 |     cold_open: str = ""
  63 |     segments: list = field(default_factory=list)  # list of SegmentSpec
  64 |     btc_price: str = "N/A"
  65 |     created_at: float = field(default_factory=time.time)
  66 | 
  67 |     def to_dict(self) -> dict:
  68 |         d = asdict(self)
  69 |         return d
  70 | 
  71 |     def to_json(self) -> str:
  72 |         return json.dumps(self.to_dict(), indent=2, default=str)
  73 | 
  74 |     def save(self, path: Path):
  75 |         import tempfile
  76 |         tmp_fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), suffix='.tmp')
  77 |         try:
  78 |             with os.fdopen(tmp_fd, 'w') as f:
  79 |                 f.write(self.to_json())
  80 |             os.replace(tmp_path, str(path))
  81 |         except Exception:
  82 |             try: os.unlink(tmp_path)
  83 |             except OSError: pass
  84 |             raise
  85 |         return path
  86 | 
  87 |     @classmethod
  88 |     def from_json(cls, path: Path) -> "EpisodeManifest":
  89 |         d = json.loads(path.read_text())
  90 |         d["segments"] = [SegmentSpec(**s) for s in d.get("segments", [])]
  91 |         return cls(**d)
  92 | 
  93 |     VALID_TYPES = {
  94 |         "cold_open", "narration", "partner_clip", "transition",
  95 |         "data", "social", "signal_active", "wrap", "x_spaces"
  96 |     }
  97 | 
  98 |     def validate(self):
  99 |         import logging as _logging
 100 |         _log = _logging.getLogger(__name__)
 101 |         if not self.segments:
 102 |             raise ValueError(f"EpisodeManifest {self.episode_id} has no segments")
 103 |         for i, seg in enumerate(self.segments):
 104 |             if not isinstance(seg, SegmentSpec):
 105 |                 raise ValueError(f"Segment {i} is not a SegmentSpec")
 106 |             if seg.segment_type not in self.VALID_TYPES:
 107 |                 _log.warning(
 108 |                     f"Segment {i} has unknown type '{seg.segment_type}'. "
 109 |                     f"Valid types: {sorted(self.VALID_TYPES)}"
 110 |                 )
 111 |             if seg.social_posts is not None and not isinstance(seg.social_posts, list):
 112 |                 raise ValueError(f"Segment {i} social_posts must be a list")
 113 |             if seg.signal_content is not None and not isinstance(seg.signal_content, dict):
 114 |                 raise ValueError(f"Segment {i} signal_content must be a dict")
 115 |         return self
 116 | 
 117 |     def segment_count(self) -> int:
 118 |         return len(self.segments)
 119 | 
 120 |     def narration_segments(self) -> list:
 121 |         return [s for s in self.segments if s.segment_type in ("narration", "cold_open")]
 122 | 
```

### File: video_pipeline_v3/assembler_v2/state.py (107 lines)
```
   1 | """
   2 | Protocol Pulse V2 — state.py
   3 | Episode-scoped state object. NO module-level globals anywhere.
   4 | EpisodeContext is passed as a parameter to every function that needs state.
   5 | """
   6 | from __future__ import annotations
   7 | from dataclasses import dataclass, field
   8 | from pathlib import Path
   9 | import uuid, time, logging
  10 | 
  11 | logger = logging.getLogger(__name__)
  12 | 
  13 | 
  14 | @dataclass
  15 | class EpisodeContext:
  16 |     """
  17 |     All mutable state for one episode render.
  18 |     Created once in episode.py, passed everywhere as ctx.
  19 |     Never stored as a module-level global.
  20 |     """
  21 |     episode_id: str
  22 |     date_str: str
  23 |     workdir: Path
  24 | 
  25 |     # SFX dedup — episode-scoped, not global
  26 |     whoosh_applied: set = field(default_factory=set)
  27 | 
  28 |     # Segment tracking
  29 |     segments_rendered: list = field(default_factory=list)
  30 |     degraded_count: int = 0
  31 |     total_filler_seconds: float = 0.0
  32 | 
  33 |     # Sponsor tracking
  34 |     sponsor_reads_done: list = field(default_factory=list)
  35 | 
  36 |     # Metrics refresh (Law 3: episode-scoped, not module globals)
  37 |     metrics_lock: object = field(default_factory=lambda: __import__('threading').Lock())
  38 |     last_metrics_refresh_ts: float = 0.0
  39 | 
  40 |     # Runtime
  41 |     started_at: float = field(default_factory=time.time)
  42 | 
  43 |     @classmethod
  44 |     def create(cls, date_str: str, base_output_dir: Path) -> "EpisodeContext":
  45 |         """Factory method. Creates workdir structure."""
  46 |         episode_id = str(uuid.uuid4())[:8]
  47 |         workdir = base_output_dir / f"{date_str}_{episode_id}"
  48 |         workdir.mkdir(parents=True, exist_ok=True)
  49 |         (workdir / "segments").mkdir(exist_ok=True)
  50 |         (workdir / "logs").mkdir(exist_ok=True)
  51 |         (workdir / "reports").mkdir(exist_ok=True)
  52 |         logger.info(f"[ctx] Episode {episode_id} | workdir: {workdir}")
  53 |         return cls(episode_id=episode_id, date_str=date_str, workdir=workdir)
  54 | 
  55 |     # ── Whoosh dedup ────────────────────────────────────────────────
  56 |     def mark_whoosh(self, path: Path):
  57 |         self.whoosh_applied.add(str(path.resolve()))
  58 | 
  59 |     def has_whoosh(self, path: Path) -> bool:
  60 |         return str(path.resolve()) in self.whoosh_applied
  61 | 
  62 |     # ── Degraded tracking ────────────────────────────────────────────
  63 |     def mark_degraded(self, segment_type: str, reason: str, filler_sec: float = 0.0):
  64 |         self.degraded_count += 1
  65 |         self.total_filler_seconds += filler_sec
  66 |         logger.warning(
  67 |             f"[ctx] DEGRADED #{self.degraded_count} | {segment_type} | {reason} | "
  68 |             f"+{filler_sec:.1f}s filler | total_filler={self.total_filler_seconds:.1f}s"
  69 |         )
  70 | 
  71 |     # ── Verdict ─────────────────────────────────────────────────────
  72 |     def verdict(self) -> str:
  73 |         """PASS | DEGRADED | HOLD
  74 |         Intentional ordering: HOLD is checked before DEGRADED so that
  75 |         episodes with excessive filler are held regardless of degraded count.
  76 |         HOLD is the strictest gate — it supersedes DEGRADED.
  77 |         """
  78 |         from .constants import QC_MAX_FILLER_SECONDS, QC_MAX_DEGRADED_SEGMENTS
  79 |         if self.total_filler_seconds >= QC_MAX_FILLER_SECONDS:
  80 |             return "HOLD"
  81 |         if self.degraded_count > QC_MAX_DEGRADED_SEGMENTS:
  82 |             return "DEGRADED"
  83 |         return "PASS"
  84 | 
  85 |     def elapsed(self) -> float:
  86 |         return time.time() - self.started_at
  87 | 
  88 |     def segment_dir(self) -> Path:
  89 |         return self.workdir / "segments"
  90 | 
  91 |     def log_dir(self) -> Path:
  92 |         return self.workdir / "logs"
  93 | 
  94 |     def report_dir(self) -> Path:
  95 |         return self.workdir / "reports"
  96 | 
  97 |     def summary(self) -> dict:
  98 |         return {
  99 |             "episode_id": self.episode_id,
 100 |             "date_str": self.date_str,
 101 |             "segments_rendered": len(self.segments_rendered),
 102 |             "degraded_count": self.degraded_count,
 103 |             "total_filler_seconds": self.total_filler_seconds,
 104 |             "verdict": self.verdict(),
 105 |             "elapsed_seconds": round(self.elapsed(), 1),
 106 |         }
 107 | 
```

### File: video_pipeline_v3/assembler_v2/preflight.py (52 lines)
```
   1 | """Protocol Pulse V2 - preflight.py"""
   2 | from __future__ import annotations
   3 | import os,shutil,logging
   4 | from pathlib import Path
   5 | from .constants import INTRO_TAG,INTRO_MUSIC,BG_LOOP,OUTRO_BRANDED,SFX_WHOOSH,SFX_SWOOSH,FONT_BOLD,FONT_MONO,CHARTS_DIR
   6 | from .helpers import ffprobe_duration,ffprobe_streams
   7 | logger=logging.getLogger(__name__)
   8 | CRITICAL=[(INTRO_TAG,"intro_tag.mp4",1000000),(INTRO_MUSIC,"intro_music.mp3",100000),(BG_LOOP,"bg_loop.mp4",1000000),(OUTRO_BRANDED,"outro_branded_new.mp4",1000000),(SFX_WHOOSH,"custom_whoosh.wav",10000),(SFX_SWOOSH,"card_swoosh.wav",10000),(FONT_BOLD,"JetBrainsMono-Bold.ttf",50000),(FONT_MONO,"JetBrainsMono-Regular.ttf",50000)]
   9 | def run_preflight(tts_files:list,clip_files:list,work_dir:Path)->dict:
  10 |     rpt={"passed":True,"critical_failures":[],"warnings":[],"checks":{}}
  11 |     def fail(m):
  12 |         rpt["critical_failures"].append(m);rpt["passed"]=False;logger.error(f"[preflight] CRITICAL: {m}")
  13 |     def warn(m):
  14 |         rpt["warnings"].append(m);logger.warning(f"[preflight] WARNING: {m}")
  15 |     for t in("ffmpeg","ffprobe"):
  16 |         if shutil.which(t):rpt["checks"][t]="OK"
  17 |         else:fail(f"{t} not in PATH")
  18 |     for path,name,mn in CRITICAL:
  19 |         if not path.exists():fail(f"Missing: {name}")
  20 |         elif path.stat().st_size<mn:fail(f"Too small: {name}")
  21 |         else:rpt["checks"][name]=f"OK {path.stat().st_size//1024}KB"
  22 |     try:
  23 |         s=os.statvfs(str(work_dir));fg=(s.f_bavail*s.f_frsize)/(1024**3)
  24 |         if fg<5.0:fail(f"Disk critical {fg:.1f}GB")
  25 |         elif fg<10.0:warn(f"Disk low {fg:.1f}GB")
  26 |         else:rpt["checks"]["disk"]=f"OK {fg:.1f}GB"
  27 |     except Exception as e:warn(f"Disk check: {e}")
  28 |     for p in[Path(x) for x in tts_files]:
  29 |         if not p.exists():fail(f"TTS missing: {p.name}")
  30 |         elif p.stat().st_size<1000:fail(f"TTS empty: {p.name}")
  31 |         else:
  32 |             d=ffprobe_duration(p)
  33 |             if d<0.5:fail(f"TTS silent: {p.name}")
  34 |             else:rpt["checks"][f"tts:{p.name}"]=f"OK {d:.1f}s"
  35 |     for p in[Path(x) for x in clip_files]:
  36 |         if not p.exists():warn(f"Clip missing (filler): {p.name}");continue
  37 |         info=ffprobe_streams(p);streams=info.get("streams",[])
  38 |         hv=any(s.get("codec_type")=="video" for s in streams)
  39 |         ha=any(s.get("codec_type")=="audio" for s in streams)
  40 |         d=ffprobe_duration(p)
  41 |         if not hv:fail(f"Clip no video: {p.name}")
  42 |         if not ha:warn(f"Clip no audio: {p.name}")
  43 |         rpt["checks"][f"clip:{p.name}"]=f"OK {d:.1f}s v={hv} a={ha}"
  44 |     for c in("price_chart.png","hashrate_chart.png","dominance_chart.png"):
  45 |         cp=CHARTS_DIR/c
  46 |         if cp.exists() and cp.stat().st_size>1000:rpt["checks"][c]="OK"
  47 |         else:warn(f"Chart missing: {c}")
  48 |     if rpt["critical_failures"]:
  49 |         raise RuntimeError("Preflight FAILED: "+("; ".join(rpt["critical_failures"])))
  50 |     logger.info(f"[preflight] PASSED {len(rpt['checks'])} checks, {len(rpt['warnings'])} warnings")
  51 |     return rpt
  52 | 
```

### File: video_pipeline_v3/assembler_v2/ffmpeg_core/encode.py (74 lines)
```
   1 | from __future__ import annotations
   2 | import time,logging
   3 | from pathlib import Path
   4 | from typing import Optional
   5 | from ..constants import VIDEO_CODEC,VIDEO_CRF,VIDEO_PRESET,VIDEO_FPS,VIDEO_PIX_FMT,AUDIO_CODEC,AUDIO_BITRATE,AUDIO_SAMPLE_RATE,AUDIO_CHANNELS,FFMPEG_TIMEOUT_ENCODE
   6 | from ..helpers import run_ffmpeg,ffprobe_contract,make_filler,atomic_rename
   7 | logger=logging.getLogger(__name__)
   8 | 
   9 | def encode_segment(inputs,filter_complex,video_map,audio_map,output_path,duration,label="segment",timeout=FFMPEG_TIMEOUT_ENCODE,tts_path=None):
  10 |     """Single authoritative encode function. Every segment calls this. Never bypass."""
  11 |     tmp=output_path.with_suffix(".tmp.mp4")
  12 |     t0=time.time()
  13 |     flat=[]
  14 |     for i in inputs:
  15 |         flat.extend([str(x) for x in i] if isinstance(i,(list,tuple)) else [str(i)])
  16 |     args=(
  17 |         ["-hide_banner"]  # suppress version banner in logs
  18 |         +flat
  19 |         +["-filter_complex",filter_complex]
  20 |         +["-map",video_map,"-map",audio_map]
  21 |         +["-c:v",VIDEO_CODEC,"-crf",str(VIDEO_CRF),"-preset",VIDEO_PRESET]
  22 |         +["-r",str(VIDEO_FPS),"-pix_fmt",VIDEO_PIX_FMT]
  23 |         +["-c:a",AUDIO_CODEC,"-ar",str(AUDIO_SAMPLE_RATE),"-b:a",AUDIO_BITRATE,"-ac",str(AUDIO_CHANNELS)]
  24 |         +["-t",str(round(duration,3))]
  25 |         +["-movflags","+faststart"]
  26 |         +[str(tmp)]
  27 |     )
  28 |     # NOTE: run_ffmpeg already prepends ["ffmpeg","-y"] — overwrites tmp safely
  29 |     ok=run_ffmpeg(args,label,timeout)
  30 |     ms=int((time.time()-t0)*1000)
  31 |     def use_filler(reason):
  32 |         """Write filler to output_path. Never raises — emergency black on any failure."""
  33 |         logger.error(f"[encode] {reason} for {label} — writing filler")
  34 |         try:
  35 |             fp=output_path.with_suffix(".filler.mp4")
  36 |             filler_ok=make_filler(fp,duration,tts_path)
  37 |             if filler_ok and fp.exists() and fp.stat().st_size>1000:
  38 |                 rename_ok=atomic_rename(fp,output_path)
  39 |                 if rename_ok:
  40 |                     return True  # filler written successfully
  41 |             # Filler creation failed — write emergency static black frame
  42 |             logger.error(f"[encode] filler also failed for {label} — writing emergency black")
  43 |             emergency_ok=run_ffmpeg([
  44 |                 "-f","lavfi","-i",
  45 |                 f"color=c=black:s=1920x1080:r=30,format=yuv420p",
  46 |                 "-f","lavfi","-i",
  47 |                 f"anullsrc=r=48000:cl=stereo",
  48 |                 "-c:v","libx264","-crf","17","-preset","ultrafast",
  49 |                 "-c:a","aac","-b:a","192k","-ar","48000","-ac","2",
  50 |                 "-t",str(max(float(duration),1.0)),
  51 |                 "-movflags","+faststart",str(output_path)
  52 |             ],f"emergency filler {label}",30)
  53 |             return emergency_ok
  54 |         except Exception as ex:
  55 |             logger.error(f"[encode] emergency filler ALSO failed: {ex}")
  56 |             return False
  57 |     if not ok or not tmp.exists() or tmp.stat().st_size<1000:
  58 |         use_filler("ENCODE FAILED")
  59 |         return False,False,{"error":"encode failed","filler_used":True},ms
  60 |     passed,summary=ffprobe_contract(tmp)
  61 |     if not passed:
  62 |         tmp.unlink(missing_ok=True)
  63 |         use_filler("CONTRACT FAILED")
  64 |         summary["filler_used"]=True
  65 |         return False,False,summary,ms
  66 |     rename_ok=atomic_rename(tmp,output_path)
  67 |     if not rename_ok:
  68 |         tmp.unlink(missing_ok=True)
  69 |         use_filler("RENAME FAILED")
  70 |         return False,False,{"error":"rename failed","filler_used":True},ms
  71 |     dur=summary.get("duration",0)
  72 |     logger.info(f"[encode] OK {label} ({dur:.1f}s, {ms}ms)")
  73 |     return True,True,summary,ms
  74 | 
```

### File: video_pipeline_v3/assembler_v2/ffmpeg_core/filters.py (95 lines)
```
   1 | """
   2 | Protocol Pulse V2 - ffmpeg_core/filters.py
   3 | Reusable FFmpeg filter snippets. Pure functions — return filter strings.
   4 | No FFmpeg calls here. All transforms composable.
   5 | """
   6 | from __future__ import annotations
   7 | from ..constants import (
   8 |     VIDEO_W, VIDEO_H, VIDEO_FPS, VIDEO_PIX_FMT,
   9 |     AUDIO_SAMPLE_RATE, AUDIO_CHANNELS, AUDIO_FORMAT,
  10 |     AUDIO_TARGET_LUFS, AUDIO_MAX_TRUE_PEAK, AUDIO_LRA, AUDIO_LIMITER,
  11 |     COLOR_BG
  12 | )
  13 | 
  14 | 
  15 | def normalize_video(label_in: str, label_out: str,
  16 |                     w: int = VIDEO_W, h: int = VIDEO_H) -> str:
  17 |     """Scale, set SAR, set pixel format, reset PTS. Apply to every video input."""
  18 |     return (
  19 |         f"[{label_in}]scale={w}:{h}:force_original_aspect_ratio=decrease,"
  20 |         f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:{COLOR_BG},"
  21 |         f"setsar=1,format={VIDEO_PIX_FMT},"
  22 |         f"fps={VIDEO_FPS},"
  23 |         f"setpts=PTS-STARTPTS[{label_out}]"
  24 |     )
  25 | 
  26 | 
  27 | def normalize_audio(label_in: str, label_out: str,
  28 |                     apply_loudnorm: bool = False) -> str:
  29 |     """
  30 |     Normalize audio to pipeline standard.
  31 |     apply_loudnorm=True for final voice segments.
  32 |     apply_loudnorm=False for clips where we preserve original dynamics.
  33 |     Always: resample, stereo, reset PTS, limiter.
  34 |     """
  35 |     chain = (
  36 |         f"[{label_in}]aformat=channel_layouts=stereo:"
  37 |         f"sample_rates={AUDIO_SAMPLE_RATE}:sample_fmts={AUDIO_FORMAT},"
  38 |         f"asetpts=PTS-STARTPTS"
  39 |     )
  40 |     if apply_loudnorm:
  41 |         chain += (
  42 |             f",loudnorm=I={AUDIO_TARGET_LUFS}:TP={AUDIO_MAX_TRUE_PEAK}"
  43 |             f":LRA={AUDIO_LRA}:linear=true"
  44 |         )
  45 |     chain += f",alimiter=limit={AUDIO_LIMITER}:attack=5:release=50[{label_out}]"
  46 |     return chain
  47 | 
  48 | 
  49 | def overlay_pip(bg_label: str, pip_label: str, out_label: str,
  50 |                 x: int = 1240, y: int = 160,
  51 |                 w: int = 640, h: int = 360) -> str:
  52 |     """
  53 |     Overlay PiP video on background.
  54 |     eof_action=pass: PiP loops without freezing at end.
  55 |     """
  56 |     return (
  57 |         f"[{pip_label}]scale={w}:{h}:force_original_aspect_ratio=decrease,"
  58 |         f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:{COLOR_BG},"
  59 |         f"format={VIDEO_PIX_FMT}[pip_scaled];"
  60 |         f"[{bg_label}][pip_scaled]overlay=x={x}:y={y}:"
  61 |         f"eof_action=repeat:shortest=0[{out_label}]"
  62 |     )
  63 | 
  64 | 
  65 | def build_waveform(audio_label: str, out_label: str,
  66 |                    w: int = 1920, h: int = 80,
  67 |                    color: str = "0xFF3B5F") -> str:
  68 |     """Waveform visualizer strip from audio signal."""
  69 |     return (
  70 |         f"[{audio_label}]showwaves=s={w}x{h}:mode=cline:"
  71 |         f"colors={color}@0.8:scale=sqrt,format={VIDEO_PIX_FMT}[{out_label}]"
  72 |     )
  73 | 
  74 | 
  75 | def fade_video(label_in: str, label_out: str,
  76 |                duration: float, fade_out_dur: float = 0.3) -> str:
  77 |     """Add fade-out to end of video segment."""
  78 |     fade_start = max(0.0, duration - fade_out_dur)
  79 |     return (
  80 |         f"[{label_in}]fade=t=out:st={fade_start:.3f}:"
  81 |         f"d={fade_out_dur}[{label_out}]"
  82 |     )
  83 | 
  84 | 
  85 | def drawtext(label_in: str, label_out: str,
  86 |              text: str, font: str, size: int,
  87 |              color: str, x: str, y: str,
  88 |              box: bool = False, box_color: str = "black@0.5") -> str:
  89 |     """Single drawtext filter. Text MUST be pre-sanitized via helpers.safe_text()."""
  90 |     box_str = f":box=1:boxcolor={box_color}:boxborderw=8" if box else ""
  91 |     return (
  92 |         f"[{label_in}]drawtext=fontfile={font}:text='{text}':"
  93 |         f"fontcolor={color}:fontsize={size}:x={x}:y={y}{box_str}[{label_out}]"
  94 |     )
  95 | 
```

### File: video_pipeline_v3/assembler_v2/ffmpeg_core/probe.py (84 lines)
```
   1 | from __future__ import annotations
   2 | import subprocess,re,json,logging
   3 | from pathlib import Path
   4 | logger=logging.getLogger(__name__)
   5 | 
   6 | def measure_lufs(path:Path)->tuple:
   7 |     """Measure integrated loudness via loudnorm JSON output. Returns (lufs,true_peak) or (-99,-99)."""
   8 |     try:
   9 |         res=subprocess.run(
  10 |             ['ffmpeg','-hide_banner','-i',str(path),
  11 |              '-af','loudnorm=I=-14:TP=-2:LRA=7:print_format=json',
  12 |              '-f','null','-'],
  13 |             capture_output=True,text=True,timeout=120)
  14 |         # loudnorm JSON is in stderr — find the JSON block
  15 |         stderr=res.stderr
  16 |         json_start=stderr.rfind('{')
  17 |         json_end=stderr.rfind('}')+1
  18 |         if json_start>=0 and json_end>json_start:
  19 |             data=json.loads(stderr[json_start:json_end])
  20 |             lufs=float(data.get('input_i',-99))
  21 |             tp=float(data.get('input_tp',-99))
  22 |             return lufs,tp
  23 |         # Fallback to regex if JSON not found
  24 |         i_m=re.search(r'"input_i"\s*:\s*"([^"]+)"',stderr)
  25 |         tp_m=re.search(r'"input_tp"\s*:\s*"([^"]+)"',stderr)
  26 |         return (float(i_m.group(1)) if i_m else -99.0),(float(tp_m.group(1)) if tp_m else -99.0)
  27 |     except Exception as e:
  28 |         logger.warning(f'[probe] lufs failed {path.name}: {e}')
  29 |         return -99.0,-99.0
  30 | 
  31 | def detect_black_frames(path:Path,min_dur:float=0.5)->list:
  32 |     """Returns list of (start,end,duration) tuples for black segments."""
  33 |     try:
  34 |         res=subprocess.run(
  35 |             ['ffmpeg','-hide_banner','-i',str(path),
  36 |              '-vf',f'blackdetect=d={min_dur}:pix_th=0.02','-an','-f','null','-'],
  37 |             capture_output=True,text=True,timeout=120)
  38 |         return [(float(m.group(1)),float(m.group(2)),float(m.group(3)))
  39 |                 for m in re.finditer(
  40 |                     r'black_start:([\d.]+).*?black_end:([\d.]+).*?black_duration:([\d.]+)',
  41 |                     res.stderr)]
  42 |     except Exception as e:
  43 |         logger.warning(f'[probe] blackdetect failed: {e}')
  44 |         return []
  45 | 
  46 | def detect_silence(path:Path,min_dur:float=1.0,noise_db:float=-50.0)->list:
  47 |     """Returns list of (start,end) tuples for silence gaps."""
  48 |     try:
  49 |         res=subprocess.run(
  50 |             ['ffmpeg','-hide_banner','-i',str(path),
  51 |              '-af',f'silencedetect=n={noise_db}dB:d={min_dur}','-f','null','-'],
  52 |             capture_output=True,text=True,timeout=120)
  53 |         starts=re.findall(r'silence_start: ([\d.]+)',res.stderr)
  54 |         ends=re.findall(r'silence_end: ([\d.]+)',res.stderr)
  55 |         pairs=list(zip(starts,ends))
  56 |         # Handle trailing silence at EOF (silence_start without matching silence_end)
  57 |         if len(starts) > len(ends):
  58 |             try:
  59 |                 dur_match=re.search(r'Duration: (\d+):(\d+):([\d.]+)',res.stderr)
  60 |                 if dur_match:
  61 |                     h,m,s=dur_match.groups()
  62 |                     file_dur=int(h)*3600+int(m)*60+float(s)
  63 |                 else:
  64 |                     file_dur=float(starts[-1])+1.0
  65 |                 pairs.append((starts[-1],str(file_dur)))
  66 |             except Exception:
  67 |                 pass
  68 |         return [(float(s),float(e)) for s,e in pairs]
  69 |     except Exception as e:
  70 |         logger.warning(f'[probe] silencedetect failed: {e}')
  71 |         return []
  72 | 
  73 | def has_motion(path:Path)->bool:
  74 |     """Quick check video has actual frames (not frozen/static)."""
  75 |     try:
  76 |         res=subprocess.run(
  77 |             ['ffprobe','-v','error','-select_streams','v',
  78 |              '-show_entries','stream=nb_frames','-of','csv=p=0',str(path)],
  79 |             capture_output=True,text=True,timeout=15)
  80 |         val=res.stdout.strip()
  81 |         return int(val)>1 if val and val.isdigit() else True
  82 |     except Exception:
  83 |         return True
  84 | 
```

### File: video_pipeline_v3/assembler_v2/segments/base.py (61 lines)
```
   1 | from __future__ import annotations
   2 | from abc import ABC, abstractmethod
   3 | from pathlib import Path
   4 | import logging
   5 | from ..manifest import SegmentSpec, RenderedSegment
   6 | from ..state import EpisodeContext
   7 | from ..helpers import ffprobe_duration, make_filler
   8 | logger = logging.getLogger(__name__)
   9 | 
  10 | class Segment(ABC):
  11 |     criticality: str = 'optional'
  12 | 
  13 |     @abstractmethod
  14 |     def render(self, spec: SegmentSpec, ctx: EpisodeContext, output_path: Path, idx: int) -> RenderedSegment:
  15 |         ...
  16 | 
  17 |     def validate(self, spec: SegmentSpec) -> tuple:
  18 |         if spec.tts_path and not Path(spec.tts_path).exists():
  19 |             return False, f'TTS missing: {spec.tts_path}'
  20 |         return True, ''
  21 | 
  22 |     def get_duration(self, spec: SegmentSpec) -> float:
  23 |         if spec.duration_hint and spec.duration_hint > 0:
  24 |             return spec.duration_hint
  25 |         if spec.tts_path:
  26 |             p = Path(spec.tts_path)
  27 |             if p.exists():
  28 |                 d = ffprobe_duration(p)
  29 |                 if d > 0: return d
  30 |         return 15.0
  31 | 
  32 |     def filler_result(self, spec: SegmentSpec, ctx: EpisodeContext,
  33 |                       output_path: Path, reason: str) -> RenderedSegment:
  34 |         dur = self.get_duration(spec)
  35 |         tts = Path(spec.tts_path) if spec.tts_path else None
  36 |         ok = make_filler(output_path, dur, tts)
  37 |         if not ok or not output_path.exists() or output_path.stat().st_size < 1000:
  38 |             # Emergency: write static black+silent as last resort
  39 |             logger.error(f"[base] make_filler failed for {reason} — emergency black")
  40 |             try:
  41 |                 from ..helpers import run_ffmpeg
  42 |                 run_ffmpeg([
  43 |                     "-f", "lavfi", "-i",
  44 |                     f"color=c=black:s=1920x1080:r=30,format=yuv420p",
  45 |                     "-f", "lavfi", "-i",
  46 |                     "anullsrc=r=48000:cl=stereo",
  47 |                     "-c:v", "libx264", "-crf", "17", "-preset", "ultrafast",
  48 |                     "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
  49 |                     "-t", str(max(dur, 1.0)),
  50 |                     "-movflags", "+faststart", str(output_path)
  51 |                 ], f"emergency filler {reason}", 30)
  52 |                 ok = output_path.exists() and output_path.stat().st_size > 1000
  53 |             except Exception as ex:
  54 |                 logger.exception(f"[base] emergency filler also failed: {ex}")
  55 |                 ok = False
  56 |         ctx.mark_degraded(spec.segment_type, reason, dur)
  57 |         actual = ffprobe_duration(output_path) if ok and output_path.exists() else dur
  58 |         return RenderedSegment(spec=spec, path=str(output_path) if ok else None,
  59 |                                duration=actual, contract_passed=ok,
  60 |                                degraded=True, error=reason)
  61 | 
```

### File: video_pipeline_v3/assembler_v2/segments/transition.py (69 lines)
```
   1 | from __future__ import annotations
   2 | import logging
   3 | from pathlib import Path
   4 | from .base import Segment
   5 | from ..manifest import SegmentSpec, RenderedSegment
   6 | from ..state import EpisodeContext
   7 | from ..constants import VIDEO_W,VIDEO_H,VIDEO_FPS,VIDEO_PIX_FMT,COLOR_BG,AUDIO_SAMPLE_RATE,AUDIO_CHANNELS,SFX_WHOOSH,FFMPEG_TIMEOUT_SHORT
   8 | from ..ffmpeg_core.encode import encode_segment
   9 | logger=logging.getLogger(__name__)
  10 | TRANSITION_DURATION=0.25
  11 | 
  12 | class TransitionSegment(Segment):
  13 |     criticality='optional'
  14 | 
  15 |     def render(self,spec:SegmentSpec,ctx:EpisodeContext,output_path:Path,idx:int)->RenderedSegment:
  16 |         try:
  17 |             return self._render(spec,ctx,output_path)
  18 |         except Exception as e:
  19 |             logger.exception(f'[transition] exception: {e}')
  20 |             return self.filler_result(spec,ctx,output_path,str(e))
  21 | 
  22 |     def _render(self,spec,ctx,output_path):
  23 |         dur=TRANSITION_DURATION
  24 |         apply_whoosh=SFX_WHOOSH.exists() and not ctx.has_whoosh(output_path)
  25 | 
  26 |         if apply_whoosh:
  27 |             inputs=[
  28 |                 ['-f','lavfi','-i',f'color=c={COLOR_BG}:s={VIDEO_W}x{VIDEO_H}:r={VIDEO_FPS}'],
  29 |                 ['-f','lavfi','-i',f'anullsrc=r={AUDIO_SAMPLE_RATE}:cl=stereo'],
  30 |                 ['-i',str(SFX_WHOOSH)],
  31 |             ]
  32 |             fg=(
  33 |                 f'[0:v]format={VIDEO_PIX_FMT},setpts=PTS-STARTPTS[v_out];'
  34 |                 f'[1:a]aformat=channel_layouts=stereo:sample_rates={AUDIO_SAMPLE_RATE}[sil];'
  35 |                 f'[2:a]aformat=channel_layouts=stereo:sample_rates={AUDIO_SAMPLE_RATE},'
  36 |                 f'afade=t=in:st=0:d=0.05,volume=0.6[whoosh];'
  37 |                 f'[sil][whoosh]amix=inputs=2:duration=first:weights=1 1[a_out]'
  38 |             )
  39 |         else:
  40 |             inputs=[
  41 |                 ['-f','lavfi','-i',f'color=c={COLOR_BG}:s={VIDEO_W}x{VIDEO_H}:r={VIDEO_FPS}'],
  42 |                 ['-f','lavfi','-i',f'anullsrc=r={AUDIO_SAMPLE_RATE}:cl=stereo'],
  43 |             ]
  44 |             fg=(
  45 |                 f'[0:v]format={VIDEO_PIX_FMT},setpts=PTS-STARTPTS[v_out];'
  46 |                 f'[1:a]aformat=channel_layouts=stereo:sample_rates={AUDIO_SAMPLE_RATE}[a_out]'
  47 |             )
  48 | 
  49 |         primary_ok,passed,summary,ms=encode_segment(
  50 |             inputs,fg,'[v_out]','[a_out]',output_path,dur,'transition',FFMPEG_TIMEOUT_SHORT)
  51 | 
  52 |         if not output_path.exists():
  53 |             return self.filler_result(spec,ctx,output_path,'transition encode failed')
  54 | 
  55 |         if apply_whoosh:
  56 |             ctx.mark_whoosh(output_path)
  57 | 
  58 |         filler_used=summary.get('filler_used',False) if isinstance(summary,dict) else False
  59 |         if not primary_ok or filler_used:
  60 |             ctx.mark_degraded('transition','contract failed (filler via encode_segment)',dur)
  61 |             logger.warning('[transition] DEGRADED — filler via encode_segment')
  62 |         else:
  63 |             logger.info(f'[transition] OK {"with whoosh" if apply_whoosh else "(no whoosh)"}')
  64 | 
  65 |         return RenderedSegment(spec=spec,path=str(output_path),
  66 |                                duration=dur,contract_passed=passed,
  67 |                                degraded=not primary_ok or filler_used,ffprobe_summary=summary,
  68 |                                render_ms=ms)
  69 | 
```

### File: video_pipeline_v3/assembler_v2/segments/wrap.py (81 lines)
```
   1 | from __future__ import annotations
   2 | import logging
   3 | from pathlib import Path
   4 | from .base import Segment
   5 | from ..manifest import SegmentSpec, RenderedSegment
   6 | from ..state import EpisodeContext
   7 | from ..constants import (VIDEO_W,VIDEO_H,VIDEO_FPS,VIDEO_PIX_FMT,
   8 |                          AUDIO_TARGET_LUFS,AUDIO_MAX_TRUE_PEAK,AUDIO_LRA,AUDIO_LIMITER,
   9 |                          AUDIO_SAMPLE_RATE,AUDIO_CODEC,AUDIO_BITRATE,AUDIO_CHANNELS,
  10 |                          VIDEO_CODEC,VIDEO_CRF,VIDEO_PRESET,
  11 |                          OUTRO_BRANDED,COLOR_BG)
  12 | from ..helpers import ffprobe_duration
  13 | from ..ffmpeg_core.encode import encode_segment
  14 | logger=logging.getLogger(__name__)
  15 | 
  16 | class WrapSegment(Segment):
  17 |     criticality='optional'
  18 | 
  19 |     def render(self,spec:SegmentSpec,ctx:EpisodeContext,output_path:Path,idx:int)->RenderedSegment:
  20 |         try:
  21 |             return self._render(spec,ctx,output_path)
  22 |         except Exception as e:
  23 |             logger.exception(f'[wrap] exception: {e}')
  24 |             return self.filler_result(spec,ctx,output_path,str(e))
  25 | 
  26 |     def _render(self,spec,ctx,output_path):
  27 |         tts=Path(spec.tts_path) if spec.tts_path else None
  28 |         tts_dur=ffprobe_duration(tts) if tts and tts.exists() else 0.0
  29 |         outro_dur=ffprobe_duration(OUTRO_BRANDED) if OUTRO_BRANDED.exists() else 0.0
  30 |         total_dur=max(tts_dur,outro_dur,10.0)
  31 | 
  32 |         if not OUTRO_BRANDED.exists() or outro_dur<1.0:
  33 |             logger.warning('[wrap] outro asset missing — filler')
  34 |             return self.filler_result(spec,ctx,output_path,'outro asset missing')
  35 | 
  36 |         if tts and tts.exists() and tts_dur>0.5:
  37 |             inputs=[
  38 |                 ['-stream_loop','-1','-an','-i',str(OUTRO_BRANDED)],
  39 |                 ['-i',str(tts)],
  40 |             ]
  41 |             fade_st=max(0,total_dur-0.5)
  42 |             fg=(
  43 |                 f'[0:v]scale={VIDEO_W}:{VIDEO_H},setsar=1,format={VIDEO_PIX_FMT},'
  44 |                 f'setpts=PTS-STARTPTS,'
  45 |                 f'fade=t=out:st={fade_st:.3f}:d=0.5[v_out];'
  46 |                 f'[1:a]aformat=channel_layouts=stereo:sample_rates={AUDIO_SAMPLE_RATE},'
  47 |                 f'asetpts=PTS-STARTPTS,'
  48 |                 f'loudnorm=I={AUDIO_TARGET_LUFS}:TP={AUDIO_MAX_TRUE_PEAK}:LRA={AUDIO_LRA}:linear=true,'
  49 |                 f'alimiter=limit={AUDIO_LIMITER}:attack=5:release=50[a_out]'
  50 |             )
  51 |         else:
  52 |             inputs=[
  53 |                 ['-stream_loop','-1','-an','-i',str(OUTRO_BRANDED)],
  54 |                 ['-f','lavfi','-i',f'anullsrc=r={AUDIO_SAMPLE_RATE}:cl=stereo'],
  55 |             ]
  56 |             fade_st=max(0,total_dur-0.5)
  57 |             fg=(
  58 |                 f'[0:v]scale={VIDEO_W}:{VIDEO_H},setsar=1,format={VIDEO_PIX_FMT},'
  59 |                 f'setpts=PTS-STARTPTS,'
  60 |                 f'fade=t=out:st={fade_st:.3f}:d=0.5[v_out];'
  61 |                 f'[1:a]aformat=channel_layouts=stereo:sample_rates={AUDIO_SAMPLE_RATE},'
  62 |                 f'alimiter=limit={AUDIO_LIMITER}:attack=5:release=50[a_out]'
  63 |             )
  64 | 
  65 |         primary_ok,passed,summary,ms=encode_segment(
  66 |             inputs,fg,'[v_out]','[a_out]',output_path,total_dur,'wrap outro',120,tts)
  67 | 
  68 |         if not output_path.exists():
  69 |             return self.filler_result(spec,ctx,output_path,'wrap encode failed')
  70 | 
  71 |         filler_used=summary.get('filler_used',False) if isinstance(summary,dict) else False
  72 |         if not primary_ok or filler_used:
  73 |             ctx.mark_degraded('wrap','contract failed (filler via encode_segment)',total_dur)
  74 |             logger.warning(f'[wrap] DEGRADED — filler via encode_segment')
  75 |         else:
  76 |             logger.info(f'[wrap] OK ({total_dur:.1f}s)')
  77 |         return RenderedSegment(spec=spec,path=str(output_path),
  78 |                                duration=summary.get('duration',total_dur),
  79 |                                contract_passed=passed,degraded=not primary_ok or filler_used,
  80 |                                ffprobe_summary=summary,render_ms=ms)
  81 | 
```

### File: video_pipeline_v3/assembler_v2/segments/cold_open.py (170 lines)
```
   1 | from __future__ import annotations
   2 | import logging
   3 | from pathlib import Path
   4 | from .base import Segment
   5 | from ..manifest import SegmentSpec, RenderedSegment
   6 | from ..state import EpisodeContext
   7 | from ..helpers import run_ffmpeg, ffprobe_duration, ffprobe_contract, atomic_rename, safe_text
   8 | from ..constants import (
   9 |     VIDEO_W, VIDEO_H, VIDEO_FPS, VIDEO_PIX_FMT,
  10 |     VIDEO_CODEC, VIDEO_CRF,
  11 |     AUDIO_CODEC, AUDIO_BITRATE, AUDIO_SAMPLE_RATE, AUDIO_CHANNELS,
  12 |     AUDIO_LIMITER, AUDIO_TARGET_LUFS, AUDIO_MAX_TRUE_PEAK, AUDIO_LRA,
  13 |     INTRO_TAG, INTRO_MUSIC, COLOR_BG, FONT_BOLD, FONT_MONO,
  14 |     COLOR_RED, COLOR_WHITE, COLOR_CYAN,
  15 |     FFMPEG_TIMEOUT_FILTER
  16 | )
  17 | logger = logging.getLogger(__name__)
  18 | FREEZE_FRAME_BUFFER_S = 1.0  # Extra frames after tag ends so fade-out has video to work on
  19 | 
  20 | 
  21 | class ColdOpenSegment(Segment):
  22 |     """
  23 |     Cold open: intro_tag.mp4 plays with intro_music.mp3 fading under PBX narration.
  24 |     Audio law (confirmed working from old pipeline):
  25 |       - intro_music: volume=0.05, fades out at 6s
  26 |       - PBX TTS: delayed 300ms, amix weight=3.0 vs music weight=0.5
  27 |       - amix duration=first — TTS anchors the output length
  28 |     """
  29 |     criticality = "required"
  30 | 
  31 |     def render(self, spec: SegmentSpec, ctx: EpisodeContext,
  32 |                output_path: Path, idx: int) -> RenderedSegment:
  33 |         try:
  34 |             return self._render(spec, ctx, output_path)
  35 |         except Exception as e:
  36 |             logger.exception(f"[cold_open] exception: {e}")
  37 |             return self.filler_result(spec, ctx, output_path, str(e))
  38 | 
  39 |     def _render(self, spec: SegmentSpec, ctx: EpisodeContext,
  40 |                 output_path: Path) -> RenderedSegment:
  41 |         tts = spec.tts()
  42 |         if not tts or not tts.exists() or tts.stat().st_size < 1000:
  43 |             return self.filler_result(spec, ctx, output_path, "TTS missing")
  44 | 
  45 |         tts_dur = ffprobe_duration(tts)
  46 |         if tts_dur < 0.5:
  47 |             return self.filler_result(spec, ctx, output_path, "TTS silent")
  48 | 
  49 |         # intro_tag provides the visual; its duration caps the segment
  50 |         tag_dur = ffprobe_duration(INTRO_TAG) if INTRO_TAG.exists() else 0.0
  51 |         total_dur = max(tts_dur, tag_dur if tag_dur > 0 else tts_dur)
  52 | 
  53 |         tmp = output_path.with_suffix(".tmp.mp4")
  54 | 
  55 |         if INTRO_TAG.exists() and INTRO_MUSIC.exists():
  56 |             ok = self._render_full(tts, tmp, tts_dur, tag_dur, total_dur)
  57 |         elif INTRO_TAG.exists():
  58 |             ok = self._render_tag_only(tts, tmp, tts_dur, tag_dur, total_dur)
  59 |         else:
  60 |             ok = self._render_tts_only(tts, tmp, tts_dur, spec)
  61 | 
  62 |         if not ok or not tmp.exists() or tmp.stat().st_size < 1000:
  63 |             return self.filler_result(spec, ctx, output_path, "cold_open encode failed")
  64 | 
  65 |         passed, summary = ffprobe_contract(tmp)
  66 |         if not passed:
  67 |             tmp.unlink(missing_ok=True)
  68 |             return self.filler_result(spec, ctx, output_path, "contract_failed")
  69 |         rename_ok = atomic_rename(tmp, output_path)
  70 |         if not rename_ok:
  71 |             tmp.unlink(missing_ok=True)
  72 |             return self.filler_result(spec, ctx, output_path, 'atomic_rename failed')
  73 |         dur = summary.get("duration", total_dur)
  74 |         logger.info(f"[cold_open] OK ({dur:.1f}s)")
  75 |         return RenderedSegment(
  76 |             spec=spec, path=str(output_path),
  77 |             duration=dur, contract_passed=True,
  78 |             degraded=False, ffprobe_summary=summary
  79 |         )
  80 | 
  81 |     def _render_full(self, tts, tmp, tts_dur, tag_dur, total_dur):
  82 |         """Full cold open: intro tag video + music + PBX TTS."""
  83 |         # video: scale intro_tag, freeze last frame to fill TTS duration
  84 |         freeze_extra = max(0.0, tts_dur - tag_dur + FREEZE_FRAME_BUFFER_S)
  85 |         vf = (
  86 |             f"scale={VIDEO_W}:{VIDEO_H},setsar=1,format={VIDEO_PIX_FMT},"
  87 |             f"tpad=stop_mode=clone:stop_duration={freeze_extra:.3f}"
  88 |         )
  89 |         fg = (
  90 |             f"[0:v]{vf},fade=t=out:st={max(0,total_dur-0.4):.3f}:d=0.4[v_out];"
  91 |             # Music: trim to 8s, fade out at 6s, very quiet under voice
  92 |             f"[2:a]atrim=0:8.0,asetpts=PTS-STARTPTS,"
  93 |             f"afade=t=out:st=6.0:d=2.0,volume=0.05[mus];"
  94 |             # TTS: 300ms delay so music hits first, then PBX voice dominates
  95 |             f"[1:a]aformat=channel_layouts=stereo:sample_rates={AUDIO_SAMPLE_RATE},"
  96 |             f"adelay=300|300[tts];"
  97 |             # Mix: duration=first = TTS anchors length (confirmed working)
  98 |             f"[mus][tts]amix=inputs=2:duration=first:weights=0.5 3.0,"
  99 |             f"loudnorm=I={AUDIO_TARGET_LUFS}:TP={AUDIO_MAX_TRUE_PEAK}:LRA={AUDIO_LRA}:linear=true,"
 100 |             f"alimiter=limit={AUDIO_LIMITER}:attack=5:release=50,"
 101 |             f"aresample=async=1[a_out]"
 102 |         )
 103 |         return run_ffmpeg([
 104 |             "-i", str(INTRO_TAG),
 105 |             "-i", str(tts),
 106 |             "-i", str(INTRO_MUSIC),
 107 |             "-filter_complex", fg,
 108 |             "-map", "[v_out]", "-map", "[a_out]",
 109 |             "-c:v", VIDEO_CODEC, "-crf", str(VIDEO_CRF), "-preset", "medium",
 110 |             "-r", str(VIDEO_FPS), "-pix_fmt", VIDEO_PIX_FMT,
 111 |             "-c:a", AUDIO_CODEC, "-ar", str(AUDIO_SAMPLE_RATE),
 112 |             "-b:a", AUDIO_BITRATE, "-ac", str(AUDIO_CHANNELS),
 113 |             "-t", str(round(total_dur, 3)),
 114 |             "-movflags", "+faststart", str(tmp)
 115 |         ], "cold_open full", FFMPEG_TIMEOUT_FILTER)
 116 | 
 117 |     def _render_tag_only(self, tts, tmp, tts_dur, tag_dur, total_dur):
 118 |         """Intro tag video + TTS only (no music file)."""
 119 |         freeze_extra = max(0.0, tts_dur - tag_dur + FREEZE_FRAME_BUFFER_S)
 120 |         vf = (
 121 |             f"scale={VIDEO_W}:{VIDEO_H},setsar=1,format={VIDEO_PIX_FMT},"
 122 |             f"tpad=stop_mode=clone:stop_duration={freeze_extra:.3f}"
 123 |         )
 124 |         fg = (
 125 |             f"[0:v]{vf},fade=t=out:st={max(0,total_dur-0.4):.3f}:d=0.4[v_out];"
 126 |             f"[1:a]aformat=channel_layouts=stereo:sample_rates={AUDIO_SAMPLE_RATE},"
 127 |             f"adelay=300|300,"
 128 |             f"loudnorm=I={AUDIO_TARGET_LUFS}:TP={AUDIO_MAX_TRUE_PEAK}:LRA={AUDIO_LRA}:linear=true,"
 129 |             f"alimiter=limit={AUDIO_LIMITER}:attack=5:release=50,"
 130 |             f"aresample=async=1[a_out]"
 131 |         )
 132 |         return run_ffmpeg([
 133 |             "-i", str(INTRO_TAG), "-i", str(tts),
 134 |             "-filter_complex", fg,
 135 |             "-map", "[v_out]", "-map", "[a_out]",
 136 |             "-c:v", VIDEO_CODEC, "-crf", str(VIDEO_CRF), "-preset", "medium",
 137 |             "-r", str(VIDEO_FPS), "-pix_fmt", VIDEO_PIX_FMT,
 138 |             "-c:a", AUDIO_CODEC, "-ar", str(AUDIO_SAMPLE_RATE),
 139 |             "-b:a", AUDIO_BITRATE, "-ac", str(AUDIO_CHANNELS),
 140 |             "-t", str(round(total_dur, 3)),
 141 |             "-movflags", "+faststart", str(tmp)
 142 |         ], "cold_open tag-only", FFMPEG_TIMEOUT_FILTER)
 143 | 
 144 |     def _render_tts_only(self, tts, tmp, tts_dur, spec):
 145 |         """Fallback: dark background + TTS narration only."""
 146 |         safe_hl = safe_text(spec.headline or "PULSE CHECK", 60)
 147 |         fg = (
 148 |             f"[0:v]scale={VIDEO_W}:{VIDEO_H},format={VIDEO_PIX_FMT}[bg];"
 149 |             f"[bg]drawtext=fontfile={FONT_BOLD}:text='{safe_hl}':"
 150 |             f"fontcolor={COLOR_RED}:fontsize=72:"
 151 |             f"x=(w-text_w)/2:y=(h-text_h)/2[v_out];"
 152 |             f"[1:a]aformat=channel_layouts=stereo:sample_rates={AUDIO_SAMPLE_RATE},"
 153 |             f"adelay=300|300,"
 154 |             f"loudnorm=I={AUDIO_TARGET_LUFS}:TP={AUDIO_MAX_TRUE_PEAK}:LRA={AUDIO_LRA}:linear=true,"
 155 |             f"alimiter=limit={AUDIO_LIMITER}:attack=5:release=50[a_out]"
 156 |         )
 157 |         return run_ffmpeg([
 158 |             "-f", "lavfi", "-i",
 159 |             f"color=c={COLOR_BG}:s={VIDEO_W}x{VIDEO_H}:r={VIDEO_FPS}",
 160 |             "-i", str(tts),
 161 |             "-filter_complex", fg,
 162 |             "-map", "[v_out]", "-map", "[a_out]",
 163 |             "-c:v", VIDEO_CODEC, "-crf", str(VIDEO_CRF), "-preset", "medium",
 164 |             "-r", str(VIDEO_FPS), "-pix_fmt", VIDEO_PIX_FMT,
 165 |             "-c:a", AUDIO_CODEC, "-ar", str(AUDIO_SAMPLE_RATE),
 166 |             "-b:a", AUDIO_BITRATE, "-ac", str(AUDIO_CHANNELS),
 167 |             "-t", str(round(tts_dur + 0.5, 3)),
 168 |             "-movflags", "+faststart", str(tmp)
 169 |         ], "cold_open tts-only fallback", FFMPEG_TIMEOUT_FILTER)
 170 | 
```

### File: video_pipeline_v3/assembler_v2/segments/narration.py (145 lines)
```
   1 | from __future__ import annotations
   2 | import logging
   3 | from pathlib import Path
   4 | from .base import Segment
   5 | from ..manifest import SegmentSpec, RenderedSegment
   6 | from ..state import EpisodeContext
   7 | from ..helpers import run_ffmpeg,ffprobe_duration,ffprobe_contract,atomic_rename,safe_text
   8 | from ..constants import (
   9 |     VIDEO_W,VIDEO_H,VIDEO_FPS,VIDEO_PIX_FMT,VIDEO_CODEC,VIDEO_CRF,
  10 |     AUDIO_CODEC,AUDIO_BITRATE,AUDIO_SAMPLE_RATE,AUDIO_CHANNELS,
  11 |     AUDIO_LIMITER,AUDIO_TARGET_LUFS,AUDIO_MAX_TRUE_PEAK,AUDIO_LRA,
  12 |     BG_LOOP,COLOR_BG,COLOR_RED,COLOR_WHITE,FONT_BOLD,FONT_MONO
  13 | )
  14 | logger=logging.getLogger(__name__)
  15 | PIP_X,PIP_Y,PIP_W,PIP_H=1240,140,640,360
  16 | 
  17 | 
  18 | class NarrationSegment(Segment):
  19 |     criticality='required'
  20 | 
  21 |     def render(self,spec,ctx,output_path,idx):
  22 |         try:
  23 |             pip=self._check_pip(spec)
  24 |             return self._render(spec,ctx,output_path,pip)
  25 |         except Exception as e:
  26 |             logger.exception(f'[narration] exception: {e}')
  27 |             return self.filler_result(spec,ctx,output_path,str(e))
  28 | 
  29 |     def _check_pip(self,spec):
  30 |         """Check for pre-normalized PiP. Do NOT generate on demand (Law 7)."""
  31 |         pip=spec.pip()
  32 |         if pip and pip.exists() and pip.stat().st_size>10000:
  33 |             return pip
  34 |         logger.warning(f'[narration] pre-normalized pip missing rank={spec.clip_rank} — using no-PiP path')
  35 |         return None
  36 | 
  37 |     def _render(self,spec,ctx,output_path,pip):
  38 |         tts=spec.tts()
  39 |         if not tts or not tts.exists() or tts.stat().st_size<1000:
  40 |             return self.filler_result(spec,ctx,output_path,'TTS missing')
  41 |         dur=ffprobe_duration(tts)
  42 |         if dur<0.5:
  43 |             return self.filler_result(spec,ctx,output_path,'TTS silent')
  44 |         has_pip=pip and pip.exists() and pip.stat().st_size>1000
  45 |         has_bg=BG_LOOP.exists()
  46 |         if has_pip:
  47 |             ok=self._render_with_pip(tts,pip,output_path,dur,spec,has_bg)
  48 |         else:
  49 |             ok=self._render_no_pip(tts,output_path,dur,spec,has_bg)
  50 |         if not ok or not output_path.exists() or output_path.stat().st_size<1000:
  51 |             return self.filler_result(spec,ctx,output_path,'narration encode failed')
  52 |         # Contract already validated inside _encode() — verify final published file
  53 |         passed,summary=ffprobe_contract(output_path)
  54 |         if not passed:
  55 |             output_path.unlink(missing_ok=True)
  56 |             ctx.mark_degraded(spec.segment_type, 'post-publish contract failed', dur)
  57 |             return self.filler_result(spec, ctx, output_path, 'post-publish contract failed')
  58 |         actual=summary.get('duration',dur)
  59 |         logger.info(f'[narration] OK ({actual:.1f}s pip={has_pip})')
  60 |         return RenderedSegment(spec=spec,path=str(output_path),duration=actual,
  61 |                                contract_passed=True,degraded=False,
  62 |                                ffprobe_summary=summary)
  63 | 
  64 |     def _build_fg_with_pip(self,pip,dur,headline,body):
  65 |         return (
  66 |             f'[0:v]scale={VIDEO_W}:{VIDEO_H},setsar=1,format={VIDEO_PIX_FMT},setpts=PTS-STARTPTS[bg];'
  67 |             f'[2:v]scale={PIP_W}:{PIP_H}:force_original_aspect_ratio=decrease,'
  68 |             f'pad={PIP_W}:{PIP_H}:(ow-iw)/2:(oh-ih)/2:{COLOR_BG},'
  69 |             f'format={VIDEO_PIX_FMT}[pip];'
  70 |             f'[bg][pip]overlay=x={PIP_X}:y={PIP_Y}:eof_action=repeat:shortest=0[wp];'
  71 |             f'[wp]drawbox=x={PIP_X-2}:y={PIP_Y-2}:w={PIP_W+4}:h={PIP_H+4}:'
  72 |             f'color={COLOR_RED}@0.8:t=2[pf];'
  73 |             f"[pf]drawtext=fontfile={FONT_BOLD}:text='{headline}':"
  74 |             f'fontcolor={COLOR_RED}:fontsize=28:x=48:y=48[wh];'
  75 |             f"[wh]drawtext=fontfile={FONT_MONO}:text='{body}':"
  76 |             f'fontcolor={COLOR_WHITE}:fontsize=22:x=48:y=100:line_spacing=8[v_out];'
  77 |             f'[1:a]aformat=channel_layouts=stereo:sample_rates={AUDIO_SAMPLE_RATE},'
  78 |             f'asetpts=PTS-STARTPTS,'
  79 |             f'loudnorm=I={AUDIO_TARGET_LUFS}:TP={AUDIO_MAX_TRUE_PEAK}:LRA={AUDIO_LRA}:linear=true,'
  80 |             f'alimiter=limit={AUDIO_LIMITER}:attack=5:release=50[a_out]'
  81 |         )
  82 | 
  83 |     def _build_fg_no_pip(self,dur,headline,body):
  84 |         return (
  85 |             f'[0:v]scale={VIDEO_W}:{VIDEO_H},setsar=1,format={VIDEO_PIX_FMT},setpts=PTS-STARTPTS[bg];'
  86 |             f'[bg]drawbox=x={PIP_X}:y={PIP_Y}:w={PIP_W}:h={PIP_H}:'
  87 |             f'color={COLOR_BG}@1.0:t=fill[wp];'
  88 |             f"[wp]drawtext=fontfile={FONT_BOLD}:text='{headline}':"
  89 |             f'fontcolor={COLOR_RED}:fontsize=28:x=48:y=48[wh];'
  90 |             f"[wh]drawtext=fontfile={FONT_MONO}:text='{body}':"
  91 |             f'fontcolor={COLOR_WHITE}:fontsize=22:x=48:y=100:line_spacing=8[v_out];'
  92 |             f'[1:a]aformat=channel_layouts=stereo:sample_rates={AUDIO_SAMPLE_RATE},'
  93 |             f'asetpts=PTS-STARTPTS,'
  94 |             f'loudnorm=I={AUDIO_TARGET_LUFS}:TP={AUDIO_MAX_TRUE_PEAK}:LRA={AUDIO_LRA}:linear=true,'
  95 |             f'alimiter=limit={AUDIO_LIMITER}:attack=5:release=50[a_out]'
  96 |         )
  97 | 
  98 |     def _encode(self,inputs_list,fg,output_path,dur,label):
  99 |         tmp=output_path.with_suffix('.tmp.mp4')
 100 |         flat=[str(x) for i in inputs_list for x in i]
 101 |         ok=run_ffmpeg(flat+['-filter_complex',fg,
 102 |             '-map','[v_out]','-map','[a_out]',
 103 |             '-c:v',VIDEO_CODEC,'-crf',str(VIDEO_CRF),'-preset','medium',
 104 |             '-r',str(VIDEO_FPS),'-pix_fmt',VIDEO_PIX_FMT,
 105 |             '-c:a',AUDIO_CODEC,'-ar',str(AUDIO_SAMPLE_RATE),
 106 |             '-b:a',AUDIO_BITRATE,'-ac',str(AUDIO_CHANNELS),
 107 |             '-t',str(round(dur,3)),'-movflags','+faststart',str(tmp)],label,180)
 108 |         if not ok or not tmp.exists() or tmp.stat().st_size<1000:
 109 |             tmp.unlink(missing_ok=True)
 110 |             return False
 111 |         # Validate BEFORE publishing (Law 2 — match partner_clip.py pattern)
 112 |         passed,summary=ffprobe_contract(tmp)
 113 |         if not passed:
 114 |             tmp.unlink(missing_ok=True)
 115 |             return False
 116 |         rename_ok=atomic_rename(tmp,output_path)
 117 |         if not rename_ok:
 118 |             tmp.unlink(missing_ok=True)
 119 |             return False
 120 |         return True
 121 | 
 122 |     def _render_with_pip(self,tts,pip,output_path,dur,spec,has_bg):
 123 |         hl=safe_text(spec.headline or spec.segment_type.upper(),55)
 124 |         bd=safe_text(spec.body or '',80)
 125 |         if has_bg:
 126 |             inputs=[['-stream_loop','-1','-i',str(BG_LOOP)],['-i',str(tts)],
 127 |                     ['-stream_loop','-1','-i',str(pip)]]
 128 |         else:
 129 |             inputs=[['-f','lavfi','-i',f'color=c={COLOR_BG}:s={VIDEO_W}x{VIDEO_H}:r={VIDEO_FPS}'],
 130 |                     ['-i',str(tts)],['-stream_loop','-1','-i',str(pip)]]
 131 |         return self._encode(inputs,self._build_fg_with_pip(pip,dur,hl,bd),
 132 |                             output_path,dur,f'narration+pip rank={spec.clip_rank}')
 133 | 
 134 |     def _render_no_pip(self,tts,output_path,dur,spec,has_bg):
 135 |         hl=safe_text(spec.headline or spec.segment_type.upper(),55)
 136 |         bd=safe_text(spec.body or '',80)
 137 |         if has_bg:
 138 |             inputs=[['-stream_loop','-1','-i',str(BG_LOOP)],['-i',str(tts)]]
 139 |         else:
 140 |             inputs=[['-f','lavfi','-i',f'color=c={COLOR_BG}:s={VIDEO_W}x{VIDEO_H}:r={VIDEO_FPS}'],
 141 |                     ['-i',str(tts)]]
 142 |         return self._encode(inputs,self._build_fg_no_pip(dur,hl,bd),
 143 |                             output_path,dur,f'narration no-pip rank={spec.clip_rank}')
 144 | 
 145 | 
```

### File: video_pipeline_v3/assembler_v2/segments/partner_clip.py (119 lines)
```
   1 | from __future__ import annotations
   2 | import logging
   3 | from pathlib import Path
   4 | from .base import Segment
   5 | from ..manifest import SegmentSpec, RenderedSegment
   6 | from ..state import EpisodeContext
   7 | from ..helpers import run_ffmpeg,ffprobe_duration,ffprobe_streams,ffprobe_contract,atomic_rename,safe_text
   8 | from ..constants import (VIDEO_W,VIDEO_H,VIDEO_FPS,VIDEO_PIX_FMT,VIDEO_CODEC,VIDEO_CRF,
   9 |     AUDIO_CODEC,AUDIO_BITRATE,AUDIO_SAMPLE_RATE,AUDIO_CHANNELS,
  10 |     AUDIO_LIMITER,COLOR_RED,COLOR_WHITE,FONT_BOLD,FONT_MONO)
  11 | logger=logging.getLogger(__name__)
  12 | LT_HEIGHT,LT_Y_OFFSET=80,60
  13 | LT_BG_ALPHA="0.82"
  14 | 
  15 | 
  16 | def _is_hdr(clip):
  17 |     """Detect if clip uses HDR color space (BT.2020 / PQ / HLG)."""
  18 |     try:
  19 |         import subprocess,json as j
  20 |         res=subprocess.run(["ffprobe","-v","error","-select_streams","v:0",
  21 |             "-show_entries","stream=color_space,color_transfer,color_primaries",
  22 |             "-of","json",str(clip)],capture_output=True,text=True,timeout=10)
  23 |         s=j.loads(res.stdout).get("streams",[{}])[0]
  24 |         hdr_markers={"bt2020","smpte2084","arib-std-b67","bt2020nc","bt2020c"}
  25 |         vals={s.get("color_space",""),s.get("color_transfer",""),s.get("color_primaries","")}
  26 |         return bool(vals & hdr_markers)
  27 |     except Exception:
  28 |         return False
  29 | 
  30 | 
  31 | def _tonemap_filter():
  32 |     """HDR-to-SDR tone mapping chain. Applied when HDR source detected."""
  33 |     return ("zscale=t=linear:npl=100,format=gbrpf32le,"
  34 |             "zscale=p=bt709,tonemap=tonemap=hable:desat=0,"
  35 |             "zscale=t=bt709:m=bt709:r=tv,format=yuv420p")
  36 | 
  37 | 
  38 | 
  39 | class PartnerClipSegment(Segment):
  40 |     criticality="required"
  41 | 
  42 |     def render(self,spec,ctx,output_path,idx):
  43 |         try:
  44 |             return self._render(spec,ctx,output_path)
  45 |         except Exception as e:
  46 |             logger.exception("[partner_clip] exception: "+str(e))
  47 |             return self.filler_result(spec,ctx,output_path,str(e))
  48 | 
  49 |     def _render(self,spec,ctx,output_path):
  50 |         clip=spec.clip()
  51 |         if not clip or not clip.exists() or clip.stat().st_size<50000:
  52 |             return self.filler_result(spec,ctx,output_path,"clip missing")
  53 |         dur=ffprobe_duration(clip)
  54 |         if dur<2.0:
  55 |             logger.warning("[partner_clip] clip too short ("+str(round(dur,2))+"s) filler: "+clip.name)
  56 |             return self.filler_result(spec,ctx,output_path,"clip too short ("+str(round(dur,2))+"s)")
  57 |         info=ffprobe_streams(clip)
  58 |         streams=info.get("streams",[])
  59 |         has_v=any(s.get("codec_type")=="video" for s in streams)
  60 |         has_a=any(s.get("codec_type")=="audio" for s in streams)
  61 |         if not has_v:
  62 |             return self.filler_result(spec,ctx,output_path,"clip no video")
  63 |         hdr=_is_hdr(clip)
  64 |         # All user-derived text must pass through safe_text() before drawtext
  65 |         ch=safe_text(spec.headline or "PARTNER SIGNAL",40)
  66 |         sl=safe_text("PROTOCOL PULSE  PARTNER CLIP",40)
  67 |         lty=VIDEO_H-LT_HEIGHT-LT_Y_OFFSET
  68 |         tmp=output_path.with_suffix(".tmp.mp4")
  69 |         W,H,pf=str(VIDEO_W),str(VIDEO_H),VIDEO_PIX_FMT
  70 |         fb,fm=str(FONT_BOLD),str(FONT_MONO)
  71 |         cw,cr=COLOR_WHITE,COLOR_RED
  72 |         sr,lim=str(AUDIO_SAMPLE_RATE),str(AUDIO_LIMITER)
  73 |         tonemap_str=_tonemap_filter()+"," if hdr else ""
  74 |         vfg_parts=[
  75 |             "[0:v]scale="+W+":"+H+":force_original_aspect_ratio=increase,"
  76 |             +"crop="+W+":"+H+","
  77 |             +tonemap_str
  78 |             +"setsar=1,format="+pf+",setpts=PTS-STARTPTS[vn]",
  79 |             "[vn]drawbox=x=0:y="+str(lty)+":w="+W+":h="+str(LT_HEIGHT)
  80 |             +":color=black@"+LT_BG_ALPHA+":t=fill[lb]",
  81 |             "[lb]drawtext=fontfile="+fb+":text='"+ch
  82 |             +"':fontcolor="+cw+":fontsize=28:x=32:y="+str(lty+12)+"[lc]",
  83 |             "[lc]drawtext=fontfile="+fm+":text='"+sl
  84 |             +"':fontcolor="+cr+":fontsize=18:x=32:y="+str(lty+46)+"[v_out]",
  85 |         ]
  86 |         vfg=";".join(vfg_parts)
  87 |         afg=("[{i}:a]aformat=channel_layouts=stereo:sample_rates="+sr+","
  88 |              "asetpts=PTS-STARTPTS,alimiter=limit="+lim+":attack=5:release=50[a_out]")
  89 |         if has_a:
  90 |             fg=vfg+";"+afg.format(i=0)
  91 |             inputs=[["-i",str(clip)]]
  92 |         else:
  93 |             logger.warning("[partner_clip] no audio: "+clip.name)
  94 |             fg=vfg+";"+afg.format(i=1)
  95 |             inputs=[["-i",str(clip)],["-f","lavfi","-i","anullsrc=r="+sr+":cl=stereo"]]
  96 |         flat=[str(x) for i in inputs for x in i]
  97 |         ok=run_ffmpeg(flat+["-filter_complex",fg,
  98 |             "-map","[v_out]","-map","[a_out]",
  99 |             "-c:v",VIDEO_CODEC,"-crf",str(VIDEO_CRF),"-preset","medium",
 100 |             "-r",str(VIDEO_FPS),"-pix_fmt",pf,
 101 |             "-c:a",AUDIO_CODEC,"-ar",sr,"-b:a",AUDIO_BITRATE,"-ac",str(AUDIO_CHANNELS),
 102 |             "-t",str(round(dur,3)),"-movflags","+faststart",str(tmp)],
 103 |             "partner_clip rank="+str(spec.clip_rank),300)
 104 |         if not ok or not tmp.exists() or tmp.stat().st_size<1000:
 105 |             tmp.unlink(missing_ok=True)
 106 |             return self.filler_result(spec,ctx,output_path,"encode failed")
 107 |         passed,summary=ffprobe_contract(tmp)
 108 |         if not passed:
 109 |             tmp.unlink(missing_ok=True)
 110 |             return self.filler_result(spec,ctx,output_path,"contract_failed")
 111 |         rename_ok=atomic_rename(tmp,output_path)
 112 |         if not rename_ok:
 113 |             tmp.unlink(missing_ok=True)
 114 |             return self.filler_result(spec,ctx,output_path,'atomic_rename failed')
 115 |         actual=summary.get("duration",dur)
 116 |         logger.info("[partner_clip] OK rank="+str(spec.clip_rank))
 117 |         return RenderedSegment(spec=spec,path=str(output_path),duration=actual,
 118 |                                contract_passed=True,degraded=False,ffprobe_summary=summary)
 119 | 
```

### File: video_pipeline_v3/assembler_v2/segments/data_segment.py (205 lines)
```
   1 | from __future__ import annotations
   2 | import logging
   3 | from pathlib import Path
   4 | from .base import Segment
   5 | from ..manifest import SegmentSpec, RenderedSegment
   6 | from ..state import EpisodeContext
   7 | from ..helpers import run_ffmpeg,ffprobe_duration,ffprobe_contract,atomic_rename,get_chart_path,safe_text
   8 | from ..constants import (VIDEO_W,VIDEO_H,VIDEO_FPS,VIDEO_PIX_FMT,VIDEO_CODEC,VIDEO_CRF,
   9 |     AUDIO_CODEC,AUDIO_BITRATE,AUDIO_SAMPLE_RATE,AUDIO_CHANNELS,
  10 |     AUDIO_LIMITER,BG_LOOP,COLOR_BG,COLOR_RED,COLOR_WHITE,COLOR_CYAN,FONT_BOLD,FONT_MONO)
  11 | logger=logging.getLogger(__name__)
  12 | 
  13 | KEYWORD_MAP={
  14 |     "price":"price","$":"price","dollar":"price","usd":"price",
  15 |     "hashrate":"hashrate","eh/s":"hashrate","mining":"hashrate",
  16 |     "miner":"hashrate","difficulty":"hashrate","exahash":"hashrate",
  17 |     "mempool":"mempool","fee":"mempool","sat/vb":"mempool",
  18 |     "transaction":"mempool","congestion":"mempool","backlog":"mempool",
  19 | }
  20 | 
  21 | def _detect_keyword(text):
  22 |     t=text.lower()
  23 |     for kw,cat in KEYWORD_MAP.items():
  24 |         if kw in t: return cat
  25 |     return ""
  26 | 
  27 | METRICS_CACHE_TTL=120  # seconds — cache valid for 2 minutes
  28 | _METRICS_MIN_REFRESH_INTERVAL = 60  # minimum seconds between refresh attempts
  29 | 
  30 | 
  31 | def _refresh_metrics_cache(cache_path, ctx):
  32 |     """Fetch all metrics and write to cache. Called in background thread under ctx.metrics_lock."""
  33 |     import json,urllib.request,time,os
  34 |     data={}
  35 |     try:
  36 |         with urllib.request.urlopen("https://mempool.space/api/v1/prices",timeout=4) as resp:
  37 |             d=json.loads(resp.read())
  38 |             data["price"]="$"+"{:,}".format(d.get("USD",0))
  39 |     except Exception as e:
  40 |         logger.exception(f"[data] metrics fetch failed (price): {e}")
  41 |     try:
  42 |         with urllib.request.urlopen("https://mempool.space/api/v1/mining/hashrate/3d",timeout=4) as resp:
  43 |             d=json.loads(resp.read())
  44 |             data["hashrate"]=str(round(d.get("currentHashrate",0)/1e18,1))+" EH/s"
  45 |     except Exception as e:
  46 |         logger.exception(f"[data] metrics fetch failed (hashrate): {e}")
  47 |     try:
  48 |         with urllib.request.urlopen("https://mempool.space/api/mempool",timeout=4) as resp:
  49 |             d=json.loads(resp.read())
  50 |             data["mempool"]=str(round(d.get("mempool_byte_per_vbyte",0),1))+" sat/vB"
  51 |     except Exception as e:
  52 |         logger.exception(f"[data] metrics fetch failed (mempool): {e}")
  53 |     if data:
  54 |         data["_ts"]=time.time()
  55 |         try:
  56 |             tmp=str(cache_path)+".tmp"
  57 |             with open(tmp,"w") as f:
  58 |                 json.dump(data,f)
  59 |             os.replace(tmp,str(cache_path))
  60 |         except Exception as e:
  61 |             logger.exception(f"[data] metrics cache write failed: {e}")
  62 |     ctx.last_metrics_refresh_ts=time.time()
  63 | 
  64 | 
  65 | def _get_metric(key, fallback, cache_path, ctx):
  66 |     """
  67 |     Cache-first metric fetch. Scoped to episode workdir — no /tmp races.
  68 |     Refreshes cache SYNCHRONOUSLY under ctx.metrics_lock — same thread owns lock.
  69 |     On any failure: returns fallback immediately, never raises.
  70 |     """
  71 |     import json, time
  72 |     from pathlib import Path
  73 |     cp = Path(cache_path)
  74 |     try:
  75 |         if cp.exists():
  76 |             cache = json.loads(cp.read_text())
  77 |             age = time.time() - cache.get("_ts", 0)
  78 |             if age < METRICS_CACHE_TTL and key in cache:
  79 |                 return cache[key]  # cache hit — return immediately
  80 |     except Exception as e:
  81 |         logger.warning(f"[data] cache read failed: {e}")
  82 | 
  83 |     # Cache miss or stale — refresh synchronously under lock with timeout
  84 |     if time.time() - ctx.last_metrics_refresh_ts >= _METRICS_MIN_REFRESH_INTERVAL:
  85 |         if ctx.metrics_lock.acquire(timeout=5.0):
  86 |             try:
  87 |                 _refresh_metrics_cache(cp, ctx)
  88 |                 ctx.last_metrics_refresh_ts = time.time()
  89 |             finally:
  90 |                 ctx.metrics_lock.release()
  91 | 
  92 |     # Re-read cache after refresh attempt
  93 |     try:
  94 |         if cp.exists():
  95 |             cache = json.loads(cp.read_text())
  96 |             if key in cache:
  97 |                 return cache[key]
  98 |     except Exception:
  99 |         pass
 100 | 
 101 |     # Fallback via network.http_get (no thundering herd — single attempt)
 102 |     try:
 103 |         from ..network import http_get
 104 |         if key == "price":
 105 |             r = http_get("https://mempool.space/api/v1/prices", timeout=3, max_attempts=2)
 106 |             if r: return "$" + "{:,}".format(r.json().get("USD", 0))
 107 |         if key == "hashrate":
 108 |             r = http_get("https://mempool.space/api/v1/mining/hashrate/3d", timeout=3, max_attempts=2)
 109 |             if r: return str(round(r.json().get("currentHashrate", 0) / 1e18, 1)) + " EH/s"
 110 |         if key == "mempool":
 111 |             r = http_get("https://mempool.space/api/mempool", timeout=3, max_attempts=2)
 112 |             if r: return str(round(r.json().get("mempool_byte_per_vbyte", 0), 1)) + " sat/vB"
 113 |     except Exception as e:
 114 |         logger.exception(f"[data] fallback fetch failed for '{key}': {e}")
 115 |     return fallback
 116 | 
 117 | class DataSegment(Segment):
 118 |     """Bitcoin data overlay: live metrics + keyword-matched chart. Optional segment."""
 119 |     criticality="optional"
 120 | 
 121 |     def render(self,spec,ctx,output_path,idx):
 122 |         try:
 123 |             return self._render(spec,ctx,output_path)
 124 |         except Exception as e:
 125 |             logger.exception("[data] exception: "+str(e))
 126 |             return self.filler_result(spec,ctx,output_path,str(e))
 127 | 
 128 |     def _render(self,spec,ctx,output_path):
 129 |         tts=spec.tts()
 130 |         if not tts or not tts.exists() or tts.stat().st_size<1000:
 131 |             return self.filler_result(spec,ctx,output_path,"TTS missing")
 132 |         dur=ffprobe_duration(tts)
 133 |         if dur<0.5:
 134 |             return self.filler_result(spec,ctx,output_path,"TTS silent")
 135 |         keyword=spec.chart_keyword or _detect_keyword(spec.body+" "+spec.headline)
 136 |         VALID_CHART_KEYWORDS={"price","hashrate","mempool","dominance",""}
 137 |         if keyword and keyword.lower() not in VALID_CHART_KEYWORDS:
 138 |             logger.warning(f"[data] invalid chart_keyword '{keyword}' — falling back to no chart")
 139 |         chart=get_chart_path(keyword)
 140 |         cache_path=ctx.workdir/"metrics_cache.json"
 141 |         btc=safe_text(_get_metric("price",spec.btc_price or "$N/A",cache_path,ctx),20)
 142 |         hr=safe_text(_get_metric("hashrate","N/A EH/s",cache_path,ctx),20)
 143 |         mp=safe_text(_get_metric("mempool","N/A sat/vB",cache_path,ctx),20)
 144 |         hl=safe_text(spec.headline or "BITCOIN SIGNAL",45)
 145 |         tmp=output_path.with_suffix(".tmp.mp4")
 146 |         W,H,pf=str(VIDEO_W),str(VIDEO_H),VIDEO_PIX_FMT
 147 |         fb,fm=str(FONT_BOLD),str(FONT_MONO)
 148 |         cw,cr,cc=COLOR_WHITE,COLOR_RED,COLOR_CYAN
 149 |         sr,lim=str(AUDIO_SAMPLE_RATE),str(AUDIO_LIMITER)
 150 | 
 151 |         if BG_LOOP.exists():
 152 |             inputs=[["-stream_loop","-1","-i",str(BG_LOOP)],["-i",str(tts)]]
 153 |             bg_fg="[0:v]scale="+W+":"+H+",setsar=1,format="+pf+",setpts=PTS-STARTPTS[bg]"
 154 |         else:
 155 |             inputs=[["-f","lavfi","-i","color=c="+COLOR_BG+":s="+W+"x"+H+":r="+str(VIDEO_FPS)],["-i",str(tts)]]
 156 |             bg_fg="[0:v]format="+pf+",setpts=PTS-STARTPTS[bg]"
 157 | 
 158 |         if chart and chart.exists():
 159 |             inputs.append(["-loop","1","-framerate",str(VIDEO_FPS),"-i",str(chart)])
 160 |             ci=str(len(inputs)-1)
 161 |             chart_fg=("[bg]drawbox=x=0:y=0:w=480:h="+H+":color=black@0.65:t=fill[mp];"
 162 |                 +"[mp]drawtext=fontfile="+fb+":text='"+hl+"':fontcolor="+cr+":fontsize=30:x=20:y=28[h1];"
 163 |                 +"[h1]drawtext=fontfile="+fm+":text='"+btc+"':fontcolor="+cc+":fontsize=26:x=20:y=80[m1];"
 164 |                 +"[m1]drawtext=fontfile="+fm+":text='"+hr+"':fontcolor="+cw+":fontsize=22:x=20:y=118[m2];"
 165 |                 +"[m2]drawtext=fontfile="+fm+":text='"+mp+"':fontcolor="+cw+":fontsize=22:x=20:y=152[v_m];"
 166 |                 +"["+ci+":v]scale=1340:754:force_original_aspect_ratio=decrease,"
 167 |                 +"pad=1340:754:(ow-iw)/2:(oh-ih)/2:"+COLOR_BG+",format="+pf+"[chart];"
 168 |                 +"[v_m][chart]overlay=x=490:y=163:eof_action=repeat[v_out]")
 169 |             fg=bg_fg+";"+chart_fg
 170 |         else:
 171 |             no_chart_fg=("[bg]drawbox=x=0:y=0:w=480:h="+H+":color=black@0.65:t=fill[mp];"
 172 |                 +"[mp]drawtext=fontfile="+fb+":text='"+hl+"':fontcolor="+cr+":fontsize=30:x=20:y=28[h1];"
 173 |                 +"[h1]drawtext=fontfile="+fm+":text='"+btc+"':fontcolor="+cc+":fontsize=26:x=20:y=80[m1];"
 174 |                 +"[m1]drawtext=fontfile="+fm+":text='"+hr+"':fontcolor="+cw+":fontsize=22:x=20:y=118[m2];"
 175 |                 +"[m2]drawtext=fontfile="+fm+":text='"+mp+"':fontcolor="+cw+":fontsize=22:x=20:y=152[v_out]")
 176 |             fg=bg_fg+";"+no_chart_fg
 177 | 
 178 |         audio_fg=("[1:a]aformat=channel_layouts=stereo:sample_rates="+sr+","
 179 |                   "asetpts=PTS-STARTPTS,"
 180 |                   "loudnorm=I=-14:TP=-2:LRA=7:linear=true,"
 181 |                   "alimiter=limit="+lim+":attack=5:release=50[a_out]")
 182 |         fg=fg+";"+audio_fg
 183 |         flat=[str(x) for i in inputs for x in i]
 184 |         ok=run_ffmpeg(flat+["-filter_complex",fg,
 185 |             "-map","[v_out]","-map","[a_out]",
 186 |             "-c:v",VIDEO_CODEC,"-crf",str(VIDEO_CRF),"-preset","medium",
 187 |             "-r",str(VIDEO_FPS),"-pix_fmt",pf,
 188 |             "-c:a",AUDIO_CODEC,"-ar",sr,"-b:a",AUDIO_BITRATE,"-ac",str(AUDIO_CHANNELS),
 189 |             "-t",str(round(dur,3)),"-movflags","+faststart",str(tmp)],
 190 |             "data_segment keyword="+keyword,180)
 191 |         if not ok or not tmp.exists() or tmp.stat().st_size<1000:
 192 |             tmp.unlink(missing_ok=True)
 193 |             return self.filler_result(spec,ctx,output_path,"data encode failed")
 194 |         passed,summary=ffprobe_contract(tmp)
 195 |         if not passed:
 196 |             tmp.unlink(missing_ok=True)
 197 |             return self.filler_result(spec,ctx,output_path,"contract_failed")
 198 |         rename_ok=atomic_rename(tmp,output_path)
 199 |         if not rename_ok:
 200 |             tmp.unlink(missing_ok=True)
 201 |             return self.filler_result(spec,ctx,output_path,'atomic_rename failed')
 202 |         logger.info("[data] OK ("+str(round(dur,1))+"s chart="+keyword+")")
 203 |         return RenderedSegment(spec=spec,path=str(output_path),duration=summary.get("duration",dur),
 204 |                                contract_passed=True,degraded=False,ffprobe_summary=summary)
 205 | 
```

### File: video_pipeline_v3/assembler_v2/segments/social.py (364 lines)
```
   1 | from __future__ import annotations
   2 | import glob as _glob
   3 | import html
   4 | import os, logging
   5 | from pathlib import Path
   6 | from .base import Segment
   7 | from ..manifest import SegmentSpec, RenderedSegment
   8 | from ..state import EpisodeContext
   9 | from ..helpers import run_ffmpeg, ffprobe_duration, ffprobe_contract, atomic_rename, safe_text
  10 | from ..constants import (
  11 |     VIDEO_W, VIDEO_H, VIDEO_FPS, VIDEO_PIX_FMT, VIDEO_CODEC, VIDEO_CRF,
  12 |     AUDIO_CODEC, AUDIO_BITRATE, AUDIO_SAMPLE_RATE, AUDIO_CHANNELS,
  13 |     AUDIO_LIMITER, AUDIO_TARGET_LUFS, AUDIO_MAX_TRUE_PEAK, AUDIO_LRA,
  14 |     COLOR_BG, FONT_BOLD, FONT_MONO
  15 | )
  16 | logger = logging.getLogger(__name__)
  17 | 
  18 | BRAND_RED = "0xE8272B"
  19 | CARD_BG = "0x141419"
  20 | META_GRAY = "0x888888"
  21 | 
  22 | 
  23 | class SocialSegment(Segment):
  24 |     """Renders up to 3 X posts as styled cards on branded background."""
  25 |     criticality = 'optional'
  26 | 
  27 |     def render(self, spec: SegmentSpec, ctx: EpisodeContext,
  28 |                output_path: Path, idx: int) -> RenderedSegment:
  29 |         try:
  30 |             return self._render(spec, ctx, output_path, idx)
  31 |         except Exception as e:
  32 |             logger.exception(f'[social] exception: {e}')
  33 |             return self.filler_result(spec, ctx, output_path, str(e))
  34 | 
  35 |     def _render(self, spec, ctx, output_path, idx=0):
  36 |         posts = spec.social_posts
  37 |         if not posts:
  38 |             return self.filler_result(spec, ctx, output_path, 'no_social_posts')
  39 | 
  40 |         posts = posts[:3]
  41 | 
  42 |         # Audio: spec TTS → inline ElevenLabs → fallback silence
  43 |         tts = spec.tts()
  44 |         if not tts or not tts.exists() or tts.stat().st_size < 1000:
  45 |             tts = self._try_inline_tts(posts, ctx, idx)
  46 |         if not tts or not tts.exists() or tts.stat().st_size < 1000:
  47 |             tts = ctx.segment_dir() / f'social_{idx}_fallback.m4a'
  48 |             self._make_fallback_audio(tts, 10.0)
  49 | 
  50 |         dur = ffprobe_duration(tts)
  51 |         if dur < 0.5:
  52 |             dur = 10.0
  53 | 
  54 |         tmp = output_path.with_suffix('.tmp.mp4')
  55 | 
  56 |         # Playwright first → drawtext fallback (Law 1)
  57 |         ok = False
  58 |         try:
  59 |             ok = self._render_cards_playwright(posts, tts, tmp, dur, ctx)
  60 |         except Exception as e:
  61 |             logger.warning(f'[social] playwright failed: {e}, falling back to drawtext')
  62 |             ok = False
  63 | 
  64 |         if not ok or not tmp.exists() or tmp.stat().st_size < 1000:
  65 |             tmp.unlink(missing_ok=True)
  66 |             ok = self._render_cards(posts, tts, tmp, dur)
  67 | 
  68 |         if not ok or not tmp.exists() or tmp.stat().st_size < 1000:
  69 |             return self.filler_result(spec, ctx, output_path, 'social encode failed')
  70 | 
  71 |         passed, summary = ffprobe_contract(tmp)
  72 |         if not passed:
  73 |             tmp.unlink(missing_ok=True)
  74 |             return self.filler_result(spec, ctx, output_path, 'contract_failed')
  75 |         rename_ok = atomic_rename(tmp, output_path)
  76 |         if not rename_ok:
  77 |             tmp.unlink(missing_ok=True)
  78 |             return self.filler_result(spec, ctx, output_path, 'atomic_rename failed')
  79 |         actual = summary.get('duration', dur)
  80 |         logger.info(f'[social] OK ({actual:.1f}s, {len(posts)} posts)')
  81 |         return RenderedSegment(
  82 |             spec=spec, path=str(output_path), duration=actual,
  83 |             contract_passed=True, degraded=False,
  84 |             ffprobe_summary=summary
  85 |         )
  86 | 
  87 |     def _try_inline_tts(self, posts, ctx, idx=0):
  88 |         """Inline ElevenLabs TTS following cold_open pattern. Returns Path or None."""
  89 |         try:
  90 |             from ..network import http_post
  91 |             key = os.environ.get('ELEVENLABS_API_KEY', '')
  92 |             if not key:
  93 |                 return None
  94 |             text = '. '.join(
  95 |                 f"{p.get('account', 'unknown')} posted: {p.get('text', '')}"
  96 |                 for p in posts
  97 |             )[:500]
  98 |             voice_id = '1SM7GgM6IMuvQlz2BwM3'
  99 |             out = ctx.segment_dir() / f'social_{idx}_tts.mp3'
 100 |             resp = http_post(
 101 |                 f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}',
 102 |                 headers={'xi-api-key': key, 'Content-Type': 'application/json'},
 103 |                 json_body={'text': text, 'model_id': 'eleven_turbo_v2_5',
 104 |                       'voice_settings': {'stability': 0.5, 'similarity_boost': 0.5}},
 105 |                 timeout=30
 106 |             )
 107 |             if resp is not None and len(resp.content) > 1000:
 108 |                 out.write_bytes(resp.content)
 109 |                 return out
 110 |         except Exception as e:
 111 |             logger.warning(f'[social] inline TTS failed: {e}')
 112 |         return None
 113 | 
 114 |     def _make_fallback_audio(self, path, duration):
 115 |         run_ffmpeg([
 116 |             '-f', 'lavfi', '-i', f'anullsrc=r={AUDIO_SAMPLE_RATE}:cl=stereo',
 117 |             '-t', str(duration),
 118 |             '-c:a', AUDIO_CODEC, '-ar', str(AUDIO_SAMPLE_RATE),
 119 |             '-b:a', AUDIO_BITRATE, '-ac', str(AUDIO_CHANNELS),
 120 |             str(path)
 121 |         ], 'social fallback audio', 30)
 122 | 
 123 |     @staticmethod
 124 |     def _find_chromium():
 125 |         """Find chromium executable: env var → system binary → Playwright cache."""
 126 |         import shutil
 127 |         # 1. Explicit env var
 128 |         env_path = os.environ.get('PLAYWRIGHT_CHROMIUM_PATH')
 129 |         if env_path and os.path.exists(env_path):
 130 |             return env_path
 131 |         # 2. System chromium
 132 |         for name in ('chromium-browser', 'chromium', 'google-chrome', 'chrome'):
 133 |             found = shutil.which(name)
 134 |             if found:
 135 |                 return found
 136 |         # 3. Playwright cache (last resort)
 137 |         patterns = [
 138 |             os.path.expanduser('~/.cache/ms-playwright/chromium-*/chrome-linux/chrome'),
 139 |             os.path.expanduser('~/.cache/ms-playwright/chromium-*/chrome-mac/Chromium.app/Contents/MacOS/Chromium'),
 140 |         ]
 141 |         for pat in patterns:
 142 |             matches = sorted(_glob.glob(pat))
 143 |             if matches:
 144 |                 return matches[-1]  # most recent version
 145 |         return None
 146 | 
 147 |     def _render_cards_playwright(self, posts, tts, tmp, dur, ctx):
 148 |         """Render tweet cards as Playwright PNG screenshots, composite via ffmpeg.
 149 |         Returns True on success, False on failure."""
 150 |         from playwright.sync_api import sync_playwright  # lazy import — Law: no module-level import
 151 | 
 152 |         chrome_path = self._find_chromium()
 153 |         if not chrome_path:
 154 |             raise FileNotFoundError('chromium executable not found — falling back to drawtext')
 155 | 
 156 |         n = len(posts)
 157 |         card_pngs = []
 158 |         pw = sync_playwright().start()
 159 |         browser = None
 160 |         try:
 161 |             browser = pw.chromium.launch(headless=True, executable_path=chrome_path)
 162 |             for i, post in enumerate(posts):
 163 |                 account_escaped = html.escape(str(post.get('account', 'unknown')))
 164 |                 text_escaped = html.escape(str(post.get('text', '')))
 165 |                 likes = html.escape(str(post.get('likes', 0)))
 166 |                 retweets = html.escape(str(post.get('retweets', 0)))
 167 |                 timestamp_escaped = html.escape(str(post.get('timestamp', '')))
 168 | 
 169 |                 card_html = f'''<!DOCTYPE html>
 170 | <html>
 171 | <head><meta charset="utf-8">
 172 | <style>
 173 |   * {{ margin: 0; padding: 0; box-sizing: border-box; }}
 174 |   body {{
 175 |     width: 800px; height: 280px; overflow: hidden;
 176 |     background: #0d1118;
 177 |     font-family: 'Courier New', Courier, monospace;
 178 |     display: flex; align-items: stretch;
 179 |   }}
 180 |   .card {{
 181 |     width: 100%; background: #0d1118;
 182 |     border: 1px solid #1e2a3a;
 183 |     border-left: 4px solid #ff3b5f;
 184 |     padding: 24px 28px;
 185 |     display: flex; flex-direction: column; gap: 12px;
 186 |   }}
 187 |   .header {{ display: flex; align-items: center; gap: 10px; }}
 188 |   .x-logo {{ color: #eef2ff; font-size: 18px; font-weight: bold; }}
 189 |   .account {{
 190 |     color: #ff3b5f; font-size: 18px; font-weight: bold;
 191 |     letter-spacing: 0.5px;
 192 |   }}
 193 |   .badge {{
 194 |     background: #f8c15c22; color: #f8c15c;
 195 |     font-size: 11px; padding: 2px 8px; border-radius: 3px;
 196 |     border: 1px solid #f8c15c44; letter-spacing: 1px;
 197 |     text-transform: uppercase;
 198 |   }}
 199 |   .text {{
 200 |     color: #eef2ff; font-size: 17px; line-height: 1.5;
 201 |     flex: 1;
 202 |     display: -webkit-box; -webkit-line-clamp: 3;
 203 |     -webkit-box-orient: vertical; overflow: hidden;
 204 |   }}
 205 |   .meta {{
 206 |     display: flex; gap: 20px; align-items: center;
 207 |     color: #95a0ba; font-size: 13px;
 208 |   }}
 209 |   .meta-item {{ display: flex; gap: 5px; align-items: center; }}
 210 |   .meta-value {{ color: #f8c15c; font-weight: bold; }}
 211 |   .divider {{
 212 |     position: absolute; bottom: 0; left: 0; right: 0;
 213 |     height: 1px; background: linear-gradient(90deg, #ff3b5f44, transparent);
 214 |   }}
 215 | </style>
 216 | </head>
 217 | <body>
 218 | <div class="card">
 219 |   <div class="header">
 220 |     <span class="x-logo">\U0001d54f</span>
 221 |     <span class="account">@{account_escaped}</span>
 222 |     <span class="badge">Bitcoin Signal</span>
 223 |   </div>
 224 |   <div class="text">{text_escaped}</div>
 225 |   <div class="meta">
 226 |     <div class="meta-item">\u2764 <span class="meta-value">{likes}</span></div>
 227 |     <div class="meta-item">\U0001f501 <span class="meta-value">{retweets}</span></div>
 228 |     <div class="meta-item">{timestamp_escaped}</div>
 229 |   </div>
 230 | </div>
 231 | </body></html>'''
 232 | 
 233 |                 page = browser.new_page(viewport={'width': 800, 'height': 280})
 234 |                 page.set_content(card_html, wait_until='load')
 235 |                 png_path = ctx.segment_dir() / f'tweet_card_{i}.png'
 236 |                 page.screenshot(path=str(png_path), timeout=10000, full_page=False)
 237 |                 page.close()
 238 |                 if not png_path.exists() or png_path.stat().st_size < 100:
 239 |                     raise RuntimeError(f'tweet_card_{i}.png empty or missing')
 240 |                 card_pngs.append(png_path)
 241 |         finally:
 242 |             if browser:
 243 |                 browser.close()
 244 |             pw.stop()
 245 | 
 246 |         # Composite PNGs onto 1920x1080 branded background via ffmpeg
 247 |         # Scale each card proportionally: 800x280 source → maintain aspect ratio
 248 |         # Fit n cards into VIDEO_H with 80px top/bottom padding and gaps between cards
 249 |         padding = 160  # 80px top + 80px bottom
 250 |         gap = 20 * (n - 1) if n > 1 else 0  # 20px gap between cards
 251 |         max_card_h = min(616, (VIDEO_H - padding - gap) // n)
 252 |         card_h = max_card_h
 253 |         card_w = int(card_h * 800 / 280)  # maintain aspect ratio
 254 |         total_h = n * card_h + gap
 255 |         y_start = (VIDEO_H - total_h) // 2
 256 | 
 257 |         inputs = ['-f', 'lavfi', '-i', f'color=c=0x06070B:s={VIDEO_W}x{VIDEO_H}:r={VIDEO_FPS}']
 258 |         inputs += ['-i', str(tts)]
 259 |         for png in card_pngs:
 260 |             inputs += ['-i', str(png)]
 261 | 
 262 |         # Build filter_complex
 263 |         fc_parts = []
 264 |         prev_label = '0:v'
 265 |         for i in range(n):
 266 |             card_gap = 20 if n > 1 else 0
 267 |             y = y_start + i * (card_h + card_gap)
 268 |             inp_idx = i + 2  # 0=bg, 1=audio, 2+=pngs
 269 |             scale_label = f'sc{i}'
 270 |             out_label = f'ov{i}' if i < n - 1 else 'v_pre'
 271 |             x_center = (VIDEO_W - card_w) // 2
 272 |             fc_parts.append(f'[{inp_idx}:v]scale={card_w}:{card_h}:flags=lanczos,format={VIDEO_PIX_FMT}[{scale_label}]')
 273 |             fc_parts.append(f'[{prev_label}][{scale_label}]overlay=x={x_center}:y={y}[{out_label}]')
 274 |             prev_label = out_label
 275 | 
 276 |         # Add kicker text
 277 |         kicker_text = safe_text('TOP X SIGNALS', 30)
 278 |         fc_parts.append(
 279 |             f"[v_pre]drawtext=fontfile={FONT_BOLD}:text='{kicker_text}':"
 280 |             f"fontcolor=0xF8C15C:fontsize=24:x=80:y=40[v_out]"
 281 |         )
 282 | 
 283 |         # Audio normalization
 284 |         fc_parts.append(
 285 |             f'[1:a]aformat=channel_layouts=stereo:sample_rates={AUDIO_SAMPLE_RATE},'
 286 |             f'loudnorm=I={AUDIO_TARGET_LUFS}:TP={AUDIO_MAX_TRUE_PEAK}:LRA={AUDIO_LRA}:linear=true,'
 287 |             f'alimiter=limit={AUDIO_LIMITER}:attack=5:release=50[a_out]'
 288 |         )
 289 | 
 290 |         fc = ';'.join(fc_parts)
 291 | 
 292 |         return run_ffmpeg(
 293 |             inputs + [
 294 |                 '-filter_complex', fc,
 295 |                 '-map', '[v_out]', '-map', '[a_out]',
 296 |                 '-c:v', VIDEO_CODEC, '-crf', str(VIDEO_CRF), '-preset', 'medium',
 297 |                 '-r', str(VIDEO_FPS), '-pix_fmt', VIDEO_PIX_FMT,
 298 |                 '-c:a', AUDIO_CODEC, '-ar', str(AUDIO_SAMPLE_RATE),
 299 |                 '-b:a', AUDIO_BITRATE, '-ac', str(AUDIO_CHANNELS),
 300 |                 '-t', str(round(dur, 3)), '-movflags', '+faststart', str(tmp)
 301 |             ], f'social playwright {n} cards', 120
 302 |         )
 303 | 
 304 |     def _render_cards(self, posts, tts, tmp, dur):
 305 |         n = len(posts)
 306 |         card_h = min(300, (VIDEO_H - 40) // n - 20)
 307 |         card_w = VIDEO_W - 80
 308 | 
 309 |         fg_parts = [f'[0:v]scale={VIDEO_W}:{VIDEO_H},format={VIDEO_PIX_FMT}[bg0]']
 310 | 
 311 |         for i, post in enumerate(posts):
 312 |             y = 20 + i * (card_h + 20)
 313 |             x = 40
 314 |             prev = f'bg{i}'
 315 |             final = 'v_out' if i == n - 1 else f'bg{i + 1}'
 316 | 
 317 |             account = safe_text(post.get('account', 'unknown'), 40)
 318 |             text = safe_text(post.get('text', ''), 80)
 319 |             likes = post.get('likes', 0)
 320 |             retweets = post.get('retweets', 0)
 321 |             ts = safe_text(post.get('timestamp', ''), 30)
 322 |             meta = safe_text(f'{post.get("timestamp", "")} | {likes} likes | {retweets} retweets', 60)
 323 | 
 324 |             fg_parts.append(
 325 |                 f'[{prev}]drawbox=x={x}:y={y}:w={card_w}:h={card_h}:'
 326 |                 f'color={CARD_BG}:t=fill[cb{i}]'
 327 |             )
 328 |             fg_parts.append(
 329 |                 f'[cb{i}]drawbox=x={x}:y={y}:w=4:h={card_h}:'
 330 |                 f'color={BRAND_RED}:t=fill[ca{i}]'
 331 |             )
 332 |             fg_parts.append(
 333 |                 f"[ca{i}]drawtext=fontfile={FONT_BOLD}:text='{account}':"
 334 |                 f"fontcolor={BRAND_RED}:fontsize=26:x={x + 20}:y={y + 15}[an{i}]"
 335 |             )
 336 |             fg_parts.append(
 337 |                 f"[an{i}]drawtext=fontfile={FONT_MONO}:text='{text}':"
 338 |                 f"fontcolor=white:fontsize=20:x={x + 20}:y={y + 55}:line_spacing=6[bt{i}]"
 339 |             )
 340 |             fg_parts.append(
 341 |                 f"[bt{i}]drawtext=fontfile={FONT_MONO}:text='{meta}':"
 342 |                 f"fontcolor={META_GRAY}:fontsize=16:x={x + 20}:y={y + card_h - 30}[{final}]"
 343 |             )
 344 | 
 345 |         fg_parts.append(
 346 |             f'[1:a]aformat=channel_layouts=stereo:sample_rates={AUDIO_SAMPLE_RATE},'
 347 |             f'loudnorm=I={AUDIO_TARGET_LUFS}:TP={AUDIO_MAX_TRUE_PEAK}:LRA={AUDIO_LRA}:linear=true,'
 348 |             f'alimiter=limit={AUDIO_LIMITER}:attack=5:release=50[a_out]'
 349 |         )
 350 | 
 351 |         fg = ';'.join(fg_parts)
 352 | 
 353 |         return run_ffmpeg([
 354 |             '-f', 'lavfi', '-i', f'color=c={COLOR_BG}:s={VIDEO_W}x{VIDEO_H}:r={VIDEO_FPS}',
 355 |             '-i', str(tts),
 356 |             '-filter_complex', fg,
 357 |             '-map', '[v_out]', '-map', '[a_out]',
 358 |             '-c:v', VIDEO_CODEC, '-crf', str(VIDEO_CRF), '-preset', 'medium',
 359 |             '-r', str(VIDEO_FPS), '-pix_fmt', VIDEO_PIX_FMT,
 360 |             '-c:a', AUDIO_CODEC, '-ar', str(AUDIO_SAMPLE_RATE),
 361 |             '-b:a', AUDIO_BITRATE, '-ac', str(AUDIO_CHANNELS),
 362 |             '-t', str(round(dur, 3)), '-movflags', '+faststart', str(tmp)
 363 |         ], f'social {len(posts)} cards', 120)
 364 | 
```

### File: video_pipeline_v3/assembler_v2/segments/signal_active.py (236 lines)
```
   1 | from __future__ import annotations
   2 | import os, logging, json, time as _time
   3 | from pathlib import Path
   4 | from .base import Segment
   5 | from ..manifest import SegmentSpec, RenderedSegment
   6 | from ..state import EpisodeContext
   7 | from ..helpers import run_ffmpeg, ffprobe_duration, ffprobe_contract, atomic_rename, safe_text, write_concat_list
   8 | from ..constants import (
   9 |     VIDEO_W, VIDEO_H, VIDEO_FPS, VIDEO_PIX_FMT, VIDEO_CODEC, VIDEO_CRF,
  10 |     AUDIO_CODEC, AUDIO_BITRATE, AUDIO_SAMPLE_RATE, AUDIO_CHANNELS,
  11 |     AUDIO_LIMITER, AUDIO_TARGET_LUFS, AUDIO_MAX_TRUE_PEAK, AUDIO_LRA,
  12 |     COLOR_BG, COLOR_GOLD, FONT_BOLD, FONT_MONO, PIPELINE_DIR
  13 | )
  14 | logger = logging.getLogger(__name__)
  15 | 
  16 | BRAND_RED = "0xE8272B"
  17 | CARD_BG = "0x141419"
  18 | META_GRAY = "0x888888"
  19 | # Read-only config path — acceptable as module constant (Law 3: no MUTABLE module-level state)
  20 | SIGNAL_CACHE = PIPELINE_DIR / "cache" / "active_signal.json"
  21 | 
  22 | 
  23 | class SignalActiveSegment(Segment):
  24 |     """Top half: Nostr signal display. Bottom half: Curated Mining sponsor (always)."""
  25 |     criticality = 'optional'
  26 | 
  27 |     SPONSOR_L1 = "CURATED MINING"
  28 |     SPONSOR_L2 = "White-glove Bitcoin mining. Section 179 LLC structure."
  29 |     SPONSOR_L3 = "curatedmining.com"
  30 | 
  31 |     def render(self, spec: SegmentSpec, ctx: EpisodeContext,
  32 |                output_path: Path, idx: int) -> RenderedSegment:
  33 |         try:
  34 |             return self._render(spec, ctx, output_path, idx)
  35 |         except Exception as e:
  36 |             logger.exception(f'[signal_active] exception: {e}')
  37 |             return self.filler_result(spec, ctx, output_path, str(e))
  38 | 
  39 |     def _read_signal(self, spec):
  40 |         """Read top Nostr signal. Returns dict or None."""
  41 |         if spec.signal_content and spec.signal_content.get('nostr_posts'):
  42 |             posts = spec.signal_content['nostr_posts']
  43 |             return posts[0] if posts else None
  44 |         try:
  45 |             data = json.loads(SIGNAL_CACHE.read_text())
  46 |             posts = data.get('nostr_posts', [])
  47 |             return posts[0] if posts else None
  48 |         except Exception as e:
  49 |             logger.warning(f'[signal_active] cache read failed: {e}')
  50 |             return None
  51 | 
  52 |     def _render(self, spec, ctx, output_path, idx=0):
  53 |         signal = self._read_signal(spec)
  54 | 
  55 |         # Audio: spec TTS → inline ElevenLabs → fallback silence
  56 |         tts = spec.tts()
  57 |         if not tts or not tts.exists() or tts.stat().st_size < 1000:
  58 |             tts = self._generate_audio(signal, ctx, idx)
  59 |         if not tts or not tts.exists() or tts.stat().st_size < 1000:
  60 |             tts = ctx.segment_dir() / f'signal_{idx}_fallback.m4a'
  61 |             self._make_fallback_audio(tts, 8.0)
  62 | 
  63 |         dur = ffprobe_duration(tts)
  64 |         if dur < 0.5:
  65 |             dur = 8.0
  66 | 
  67 |         tmp = output_path.with_suffix('.tmp.mp4')
  68 |         fg = self._build_fg(signal)
  69 |         ok = run_ffmpeg([
  70 |             '-f', 'lavfi', '-i', f'color=c={COLOR_BG}:s={VIDEO_W}x{VIDEO_H}:r={VIDEO_FPS}',
  71 |             '-i', str(tts),
  72 |             '-filter_complex', fg,
  73 |             '-map', '[v_out]', '-map', '[a_out]',
  74 |             '-c:v', VIDEO_CODEC, '-crf', str(VIDEO_CRF), '-preset', 'medium',
  75 |             '-r', str(VIDEO_FPS), '-pix_fmt', VIDEO_PIX_FMT,
  76 |             '-c:a', AUDIO_CODEC, '-ar', str(AUDIO_SAMPLE_RATE),
  77 |             '-b:a', AUDIO_BITRATE, '-ac', str(AUDIO_CHANNELS),
  78 |             '-t', str(round(dur, 3)), '-movflags', '+faststart', str(tmp)
  79 |         ], 'signal_active', 120)
  80 | 
  81 |         if not ok or not tmp.exists() or tmp.stat().st_size < 1000:
  82 |             return self.filler_result(spec, ctx, output_path, 'signal_active encode failed')
  83 | 
  84 |         passed, summary = ffprobe_contract(tmp)
  85 |         if not passed:
  86 |             tmp.unlink(missing_ok=True)
  87 |             return self.filler_result(spec, ctx, output_path, 'contract_failed')
  88 |         rename_ok = atomic_rename(tmp, output_path)
  89 |         if not rename_ok:
  90 |             tmp.unlink(missing_ok=True)
  91 |             return self.filler_result(spec, ctx, output_path, 'atomic_rename failed')
  92 |         actual = summary.get('duration', dur)
  93 |         logger.info(f'[signal_active] OK ({actual:.1f}s signal={"yes" if signal else "no"})')
  94 |         return RenderedSegment(
  95 |             spec=spec, path=str(output_path), duration=actual,
  96 |             contract_passed=True, degraded=False,
  97 |             ffprobe_summary=summary
  98 |         )
  99 | 
 100 |     def _build_fg(self, signal):
 101 |         """Build filter graph for split-screen: signal top, sponsor bottom."""
 102 |         parts = [f'[0:v]scale={VIDEO_W}:{VIDEO_H},format={VIDEO_PIX_FMT}[bg]']
 103 | 
 104 |         # Top half: Nostr signal card
 105 |         parts.append(f'[bg]drawbox=x=40:y=20:w=1840:h=500:color={CARD_BG}:t=fill[top]')
 106 | 
 107 |         if signal:
 108 |             name = safe_text(signal.get('display_name', 'Unknown'), 40)
 109 |             text = safe_text(signal.get('text', ''), 80)
 110 |             score_str = safe_text(f"Signal Score: {signal.get('score', 0)}", 40)
 111 |             try:
 112 |                 ts_raw = _time.strftime('%Y-%m-%d %H:%M UTC',
 113 |                                         _time.gmtime(signal.get('created_at', 0)))
 114 |             except Exception:
 115 |                 ts_raw = str(signal.get('created_at', ''))
 116 |             meta = safe_text(f'{ts_raw} | {signal.get("relay", "")}', 60)
 117 | 
 118 |             parts.append(
 119 |                 f"[top]drawtext=fontfile={FONT_BOLD}:"
 120 |                 f"text='{safe_text('NOSTR SIGNAL', 20)}':"
 121 |                 f"fontcolor={BRAND_RED}:fontsize=32:x=60:y=40[th]"
 122 |             )
 123 |             parts.append(
 124 |                 f"[th]drawtext=fontfile={FONT_BOLD}:text='{name}':"
 125 |                 f"fontcolor=white:fontsize=26:x=60:y=90[tn]"
 126 |             )
 127 |             parts.append(
 128 |                 f"[tn]drawtext=fontfile={FONT_MONO}:text='{text}':"
 129 |                 f"fontcolor=white:fontsize=20:x=60:y=140:line_spacing=6[tt]"
 130 |             )
 131 |             parts.append(
 132 |                 f"[tt]drawtext=fontfile={FONT_BOLD}:text='{score_str}':"
 133 |                 f"fontcolor={COLOR_GOLD}:fontsize=24:x=60:y=400[ts]"
 134 |             )
 135 |             parts.append(
 136 |                 f"[ts]drawtext=fontfile={FONT_MONO}:text='{meta}':"
 137 |                 f"fontcolor={META_GRAY}:fontsize=16:x=60:y=440[mid]"
 138 |             )
 139 |         else:
 140 |             parts.append(
 141 |                 f"[top]drawtext=fontfile={FONT_BOLD}:"
 142 |                 f"text='{safe_text('NO SIGNAL', 20)}':"
 143 |                 f"fontcolor={BRAND_RED}:fontsize=48:x=(w-text_w)/2:y=220[mid]"
 144 |             )
 145 | 
 146 |         # Bottom half: Curated Mining sponsor — ALWAYS present, NEVER conditional
 147 |         s1 = safe_text(self.SPONSOR_L1, 40)
 148 |         s2 = safe_text(self.SPONSOR_L2, 80)
 149 |         s3 = safe_text(self.SPONSOR_L3, 40)
 150 |         parts.append(
 151 |             f'[mid]drawbox=x=40:y=560:w=1840:h=460:'
 152 |             f'color={COLOR_BG}:t=fill[bot]'
 153 |         )
 154 |         parts.append(
 155 |             f"[bot]drawtext=fontfile={FONT_BOLD}:text='{s1}':"
 156 |             f"fontcolor={BRAND_RED}:fontsize=36:x=(w-text_w)/2:y=660[sp1]"
 157 |         )
 158 |         parts.append(
 159 |             f"[sp1]drawtext=fontfile={FONT_MONO}:text='{s2}':"
 160 |             f"fontcolor=white:fontsize=22:x=(w-text_w)/2:y=740[sp2]"
 161 |         )
 162 |         parts.append(
 163 |             f"[sp2]drawtext=fontfile={FONT_BOLD}:text='{s3}':"
 164 |             f"fontcolor={BRAND_RED}:fontsize=28:x=(w-text_w)/2:y=820[v_out]"
 165 |         )
 166 | 
 167 |         # Audio
 168 |         parts.append(
 169 |             f'[1:a]aformat=channel_layouts=stereo:sample_rates={AUDIO_SAMPLE_RATE},'
 170 |             f'loudnorm=I={AUDIO_TARGET_LUFS}:TP={AUDIO_MAX_TRUE_PEAK}:LRA={AUDIO_LRA}:linear=true,'
 171 |             f'alimiter=limit={AUDIO_LIMITER}:attack=5:release=50[a_out]'
 172 |         )
 173 | 
 174 |         return ';'.join(parts)
 175 | 
 176 |     def _generate_audio(self, signal, ctx, idx=0):
 177 |         """Inline ElevenLabs TTS for both halves, concat with 0.5s gap."""
 178 |         try:
 179 |             from ..network import http_post
 180 |             key = os.environ.get('ELEVENLABS_API_KEY', '')
 181 |             if not key:
 182 |                 return None
 183 |             voice_id = '1SM7GgM6IMuvQlz2BwM3'
 184 |             top_text = signal.get('text', '')[:500] if signal else 'No active signal'
 185 |             bottom_text = f'{self.SPONSOR_L1}. {self.SPONSOR_L2}. {self.SPONSOR_L3}'
 186 | 
 187 |             top_path = ctx.segment_dir() / f'sig_{idx}_top.mp3'
 188 |             bot_path = ctx.segment_dir() / f'sig_{idx}_bot.mp3'
 189 | 
 190 |             for text, path in [(top_text, top_path), (bottom_text, bot_path)]:
 191 |                 resp = http_post(
 192 |                     f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}',
 193 |                     headers={'xi-api-key': key, 'Content-Type': 'application/json'},
 194 |                     json_body={'text': text, 'model_id': 'eleven_turbo_v2_5',
 195 |                           'voice_settings': {'stability': 0.5, 'similarity_boost': 0.5}},
 196 |                     timeout=30
 197 |                 )
 198 |                 if resp is None or len(resp.content) < 1000:
 199 |                     return None
 200 |                 path.write_bytes(resp.content)
 201 | 
 202 |             # 0.5s silence gap
 203 |             gap = ctx.segment_dir() / f'sig_{idx}_gap.m4a'
 204 |             run_ffmpeg([
 205 |                 '-f', 'lavfi', '-i', f'anullsrc=r={AUDIO_SAMPLE_RATE}:cl=stereo',
 206 |                 '-t', '0.5', '-c:a', AUDIO_CODEC, '-ar', str(AUDIO_SAMPLE_RATE),
 207 |                 '-b:a', AUDIO_BITRATE, '-ac', str(AUDIO_CHANNELS), str(gap)
 208 |             ], 'signal gap', 15)
 209 | 
 210 |             # Concat with ffmpeg concat demuxer
 211 |             concat_file = ctx.segment_dir() / f'sig_{idx}_concat.txt'
 212 |             if not write_concat_list([top_path, gap, bot_path], concat_file):
 213 |                 logger.warning('[signal_active] concat list write failed')
 214 |                 return None
 215 |             out = ctx.segment_dir() / f'sig_{idx}_concat_out.m4a'
 216 |             ok = run_ffmpeg([
 217 |                 '-f', 'concat', '-safe', '0', '-i', str(concat_file),
 218 |                 '-c:a', AUDIO_CODEC, '-ar', str(AUDIO_SAMPLE_RATE),
 219 |                 '-b:a', AUDIO_BITRATE, '-ac', str(AUDIO_CHANNELS), str(out)
 220 |             ], 'signal concat audio', 30)
 221 | 
 222 |             if ok and out.exists() and out.stat().st_size > 1000:
 223 |                 return out
 224 |         except Exception as e:
 225 |             logger.warning(f'[signal_active] inline TTS failed: {e}')
 226 |         return None
 227 | 
 228 |     def _make_fallback_audio(self, path, duration):
 229 |         run_ffmpeg([
 230 |             '-f', 'lavfi', '-i', f'anullsrc=r={AUDIO_SAMPLE_RATE}:cl=stereo',
 231 |             '-t', str(duration),
 232 |             '-c:a', AUDIO_CODEC, '-ar', str(AUDIO_SAMPLE_RATE),
 233 |             '-b:a', AUDIO_BITRATE, '-ac', str(AUDIO_CHANNELS),
 234 |             str(path)
 235 |         ], 'signal fallback audio', 30)
 236 | 
```

### File: video_pipeline_v3/assembler_v2/episode.py (282 lines)
```
   1 | """
   2 | Protocol Pulse V2 — episode.py
   3 | Episode runner — single entry point that orchestrates a full episode render
   4 | from EpisodeManifest to final concatenated MP4.
   5 | """
   6 | from __future__ import annotations
   7 | from dataclasses import dataclass, field
   8 | from pathlib import Path
   9 | from typing import Optional
  10 | import logging, time
  11 | 
  12 | from .manifest import EpisodeManifest, SegmentSpec, RenderedSegment
  13 | from .state import EpisodeContext
  14 | from .preflight import run_preflight
  15 | from .helpers import (
  16 |     run_ffmpeg, ffprobe_duration, ffprobe_contract, make_filler, atomic_rename,
  17 |     write_concat_list,
  18 | )
  19 | from .ffmpeg_core.probe import measure_lufs, detect_black_frames, detect_silence
  20 | from .constants import (
  21 |     VIDEO_W, VIDEO_H, VIDEO_FPS, VIDEO_PIX_FMT, VIDEO_CODEC, VIDEO_CRF,
  22 |     AUDIO_CODEC, AUDIO_BITRATE, AUDIO_SAMPLE_RATE, AUDIO_CHANNELS,
  23 |     COLOR_BG, FFMPEG_TIMEOUT_FILTER, FFMPEG_TIMEOUT_ENCODE,
  24 |     QC_MIN_LUFS, QC_MAX_LUFS, QC_MAX_TRUE_PEAK, QC_MAX_BLACK_FRAME_S, QC_MAX_SILENCE_S,
  25 |     QC_EPISODE_SILENCE_HOLD_S, QC_MIN_DURATION, QC_MAX_DURATION,
  26 | )
  27 | from .segments.cold_open import ColdOpenSegment
  28 | from .segments.narration import NarrationSegment
  29 | from .segments.partner_clip import PartnerClipSegment
  30 | from .segments.transition import TransitionSegment
  31 | from .segments.data_segment import DataSegment
  32 | from .segments.social import SocialSegment
  33 | from .segments.signal_active import SignalActiveSegment
  34 | from .segments.wrap import WrapSegment
  35 | from .segments.x_spaces_segment import XSpacesSegment
  36 | 
  37 | logger = logging.getLogger(__name__)
  38 | 
  39 | SEGMENT_MAP = {
  40 |     "cold_open": ColdOpenSegment,
  41 |     "narration": NarrationSegment,
  42 |     "partner_clip": PartnerClipSegment,
  43 |     "transition": TransitionSegment,
  44 |     "data": DataSegment,
  45 |     "social": SocialSegment,
  46 |     "signal_active": SignalActiveSegment,
  47 |     "wrap": WrapSegment,
  48 |     "x_spaces": XSpacesSegment,
  49 | }
  50 | 
  51 | 
  52 | @dataclass
  53 | class EpisodeReport:
  54 |     episode_id: str = ""
  55 |     output_path: Optional[Path] = None
  56 |     verdict: str = "HOLD"
  57 |     duration: float = 0.0
  58 |     contract_passed: bool = False
  59 |     degraded_count: int = 0
  60 |     total_filler_seconds: float = 0.0
  61 |     segment_reports: list = field(default_factory=list)
  62 |     elapsed_seconds: float = 0.0
  63 |     error: str = ""
  64 | 
  65 | 
  66 | class EpisodeRunner:
  67 |     """Orchestrates a full episode render. run() NEVER raises."""
  68 | 
  69 |     def run(self, manifest: EpisodeManifest, output_dir: Path) -> EpisodeReport:
  70 |         t0 = time.time()
  71 |         try:
  72 |             return self._run(manifest, output_dir, t0)
  73 |         except Exception as e:
  74 |             logger.exception(f"[episode] fatal exception: {e}")
  75 |             return EpisodeReport(
  76 |                 episode_id=manifest.episode_id,
  77 |                 verdict="HOLD",
  78 |                 elapsed_seconds=round(time.time() - t0, 3),
  79 |                 error=str(e),
  80 |             )
  81 | 
  82 |     def _run(self, manifest: EpisodeManifest, output_dir: Path, t0: float) -> EpisodeReport:
  83 |         # 0. Validate manifest
  84 |         try:
  85 |             manifest.validate()
  86 |         except ValueError as e:
  87 |             return EpisodeReport(
  88 |                 episode_id=manifest.episode_id,
  89 |                 verdict="HOLD",
  90 |                 elapsed_seconds=round(time.time() - t0, 3),
  91 |                 error=f"manifest validation failed: {e}",
  92 |             )
  93 | 
  94 |         # 1. Preflight
  95 |         tts_files = [s.tts_path for s in manifest.segments if s.tts_path]
  96 |         clip_files = [s.clip_path for s in manifest.segments if s.clip_path]
  97 |         try:
  98 |             run_preflight(tts_files, clip_files, output_dir)
  99 |         except RuntimeError as e:
 100 |             return EpisodeReport(
 101 |                 episode_id=manifest.episode_id,
 102 |                 verdict="HOLD",
 103 |                 elapsed_seconds=round(time.time() - t0, 3),
 104 |                 error=str(e),
 105 |             )
 106 | 
 107 |         # 2. Create EpisodeContext
 108 |         ctx = EpisodeContext.create(manifest.date_str, output_dir)
 109 | 
 110 |         # 3. Dispatch segments
 111 |         segment_reports: list[RenderedSegment] = []
 112 |         for idx, spec in enumerate(manifest.segments):
 113 |             seg_t0 = time.time()
 114 |             seg_class = SEGMENT_MAP.get(spec.segment_type)
 115 |             if seg_class is None:
 116 |                 # Unknown segment type — filler
 117 |                 logger.warning(f"[episode] unknown segment_type '{spec.segment_type}' — filler")
 118 |                 ctx.mark_degraded(spec.segment_type, f"unknown segment_type: {spec.segment_type}", 15.0)
 119 |                 filler_path = ctx.segment_dir() / f"seg_{idx:03d}_{spec.segment_type}_filler.mp4"
 120 |                 self._make_unknown_filler(filler_path)
 121 |                 result = RenderedSegment(
 122 |                     spec=spec,
 123 |                     path=str(filler_path) if filler_path.exists() else None,
 124 |                     duration=15.0,
 125 |                     contract_passed=filler_path.exists() and filler_path.stat().st_size > 1000,
 126 |                     degraded=True,
 127 |                     error=f"unknown segment_type: {spec.segment_type}",
 128 |                 )
 129 |             else:
 130 |                 out_path = ctx.segment_dir() / f"seg_{idx:03d}_{spec.segment_type}.mp4"
 131 |                 result = seg_class().render(spec, ctx, out_path, idx)
 132 |             seg_elapsed = round((time.time() - seg_t0) * 1000)
 133 |             result.render_ms = seg_elapsed
 134 |             segment_reports.append(result)
 135 |             ctx.segments_rendered.append(result)
 136 |             logger.info(
 137 |                 f"[episode] seg {idx} {spec.segment_type} "
 138 |                 f"{'OK' if not result.degraded else 'DEGRADED'} "
 139 |                 f"({seg_elapsed}ms)"
 140 |             )
 141 | 
 142 |         # 4. Build concat list
 143 |         concat_paths = [Path(r.path) for r in segment_reports if r.path and Path(r.path).exists()]
 144 |         if not concat_paths:
 145 |             return EpisodeReport(
 146 |                 episode_id=ctx.episode_id,
 147 |                 verdict="HOLD",
 148 |                 degraded_count=ctx.degraded_count,
 149 |                 total_filler_seconds=ctx.total_filler_seconds,
 150 |                 segment_reports=segment_reports,
 151 |                 elapsed_seconds=round(time.time() - t0, 3),
 152 |                 error="no valid segments to concatenate",
 153 |             )
 154 | 
 155 |         # 5. Concatenate
 156 |         concat_list = ctx.workdir / "concat_list.txt"
 157 |         if not write_concat_list(concat_paths, concat_list):
 158 |             return EpisodeReport(
 159 |                 episode_id=ctx.episode_id,
 160 |                 verdict="HOLD",
 161 |                 degraded_count=ctx.degraded_count,
 162 |                 total_filler_seconds=ctx.total_filler_seconds,
 163 |                 segment_reports=segment_reports,
 164 |                 elapsed_seconds=round(time.time() - t0, 3),
 165 |                 error="concat list write failed",
 166 |             )
 167 | 
 168 |         final_name = f"{manifest.date_str}_{ctx.episode_id}_episode.mp4"
 169 |         final_tmp = ctx.workdir / f"{final_name}.tmp.mp4"
 170 |         final_path = output_dir / final_name
 171 | 
 172 |         ok = run_ffmpeg([
 173 |             "-f", "concat", "-safe", "0", "-i", str(concat_list),
 174 |             "-c", "copy",
 175 |             "-movflags", "+faststart",
 176 |             str(final_tmp),
 177 |         ], "episode concat", FFMPEG_TIMEOUT_ENCODE)
 178 | 
 179 |         if not ok or not final_tmp.exists() or final_tmp.stat().st_size == 0:
 180 |             final_tmp.unlink(missing_ok=True)
 181 |             return EpisodeReport(
 182 |                 episode_id=ctx.episode_id,
 183 |                 verdict="HOLD",
 184 |                 degraded_count=ctx.degraded_count,
 185 |                 total_filler_seconds=ctx.total_filler_seconds,
 186 |                 segment_reports=segment_reports,
 187 |                 elapsed_seconds=round(time.time() - t0, 3),
 188 |                 error="concat produced empty output",
 189 |             )
 190 | 
 191 |         rename_ok = atomic_rename(final_tmp, final_path)
 192 |         if not rename_ok:
 193 |             final_tmp.unlink(missing_ok=True)
 194 |             return EpisodeReport(
 195 |                 episode_id=ctx.episode_id,
 196 |                 verdict="HOLD",
 197 |                 error="final episode atomic_rename failed",
 198 |                 elapsed_seconds=round(time.time() - t0, 3),
 199 |                 segment_reports=segment_reports,
 200 |             )
 201 | 
 202 |         # 6. Contract check on final
 203 |         contract_passed, final_summary = ffprobe_contract(final_path)
 204 | 
 205 |         # 7. Content QC — measure actual content quality
 206 |         qc_failures = []
 207 |         try:
 208 |             # Black frame check
 209 |             black_segs = detect_black_frames(final_path, min_dur=QC_MAX_BLACK_FRAME_S)
 210 |             total_black = sum(b[2] for b in black_segs)
 211 |             if total_black > QC_MAX_BLACK_FRAME_S:
 212 |                 qc_failures.append(f"black_frames={total_black:.1f}s (max {QC_MAX_BLACK_FRAME_S}s)")
 213 | 
 214 |             # Silence check
 215 |             silence_segs = detect_silence(final_path, min_dur=QC_MAX_SILENCE_S)
 216 |             total_silence = sum(e - s for s, e in silence_segs)
 217 |             if total_silence > QC_EPISODE_SILENCE_HOLD_S:
 218 |                 qc_failures.append(f"silence={total_silence:.1f}s")
 219 | 
 220 |             # Duration check — must be within spec
 221 |             duration = final_summary.get("duration", 0.0)
 222 |             if duration < QC_MIN_DURATION:
 223 |                 qc_failures.append(f"too_short={duration:.0f}s (min {QC_MIN_DURATION}s)")
 224 |             elif duration > QC_MAX_DURATION:
 225 |                 qc_failures.append(f"too_long={duration:.0f}s (max {QC_MAX_DURATION}s)")
 226 | 
 227 |             # LUFS check
 228 |             lufs, true_peak = measure_lufs(final_path)
 229 |             if lufs != -99.0:  # -99 means probe failed — skip check
 230 |                 if lufs < QC_MIN_LUFS or lufs > QC_MAX_LUFS:
 231 |                     qc_failures.append(f"lufs={lufs:.1f} (range {QC_MIN_LUFS} to {QC_MAX_LUFS})")
 232 |                 if true_peak > QC_MAX_TRUE_PEAK:
 233 |                     qc_failures.append(f"true_peak={true_peak:.1f} (max {QC_MAX_TRUE_PEAK})")
 234 |         except Exception as e:
 235 |             logger.warning(f"[episode] QC probe failed (non-fatal): {e}")
 236 | 
 237 |         if qc_failures:
 238 |             logger.warning(f"[episode] QC failures: {qc_failures}")
 239 |             verdict = "HOLD"
 240 | 
 241 |         # 8. Final verdict (QC failures override ctx verdict)
 242 |         if not qc_failures:
 243 |             verdict = ctx.verdict()
 244 |             if not contract_passed:
 245 |                 verdict = "HOLD"
 246 | 
 247 |         duration = final_summary.get("duration", 0.0)
 248 | 
 249 |         return EpisodeReport(
 250 |             episode_id=ctx.episode_id,
 251 |             output_path=final_path,
 252 |             verdict=verdict,
 253 |             duration=duration,
 254 |             contract_passed=contract_passed,
 255 |             degraded_count=ctx.degraded_count,
 256 |             total_filler_seconds=ctx.total_filler_seconds,
 257 |             segment_reports=segment_reports,
 258 |             elapsed_seconds=round(time.time() - t0, 3),
 259 |             error="",
 260 |         )
 261 | 
 262 |     def _make_unknown_filler(self, output_path: Path) -> bool:
 263 |         """Generate 15s black silent mp4 for unknown segment types. CRF only."""
 264 |         tmp = output_path.with_suffix('.tmp.mp4')
 265 |         ok = run_ffmpeg([
 266 |             "-f", "lavfi", "-i",
 267 |             f"color=c={COLOR_BG}:s={VIDEO_W}x{VIDEO_H}:r={VIDEO_FPS}",
 268 |             "-f", "lavfi", "-i",
 269 |             f"anullsrc=r={AUDIO_SAMPLE_RATE}:cl=stereo",
 270 |             "-c:v", VIDEO_CODEC, "-crf", str(VIDEO_CRF), "-preset", "veryfast",
 271 |             "-pix_fmt", VIDEO_PIX_FMT, "-r", str(VIDEO_FPS),
 272 |             "-c:a", AUDIO_CODEC, "-ar", str(AUDIO_SAMPLE_RATE), "-b:a", AUDIO_BITRATE,
 273 |             "-ac", str(AUDIO_CHANNELS),
 274 |             "-t", "15",
 275 |             "-movflags", "+faststart",
 276 |             str(tmp),
 277 |         ], "unknown_filler 15s", FFMPEG_TIMEOUT_FILTER)
 278 |         if not ok or not tmp.exists() or tmp.stat().st_size < 1000:
 279 |             tmp.unlink(missing_ok=True)
 280 |             return False
 281 |         return atomic_rename(tmp, output_path)
 282 | 
```

### File: video_pipeline_v3/assembler_v2/segments/x_spaces_segment.py (159 lines)
```
   1 | from __future__ import annotations
   2 | import os
   3 | import logging
   4 | from pathlib import Path
   5 | from .base import Segment
   6 | from ..manifest import SegmentSpec, RenderedSegment
   7 | from ..state import EpisodeContext
   8 | from ..helpers import run_ffmpeg, ffprobe_duration, ffprobe_contract, atomic_rename, safe_text
   9 | from ..constants import (
  10 |     VIDEO_W, VIDEO_H, VIDEO_FPS, VIDEO_PIX_FMT, VIDEO_CODEC, VIDEO_CRF,
  11 |     AUDIO_CODEC, AUDIO_BITRATE, AUDIO_SAMPLE_RATE, AUDIO_CHANNELS,
  12 |     AUDIO_LIMITER, AUDIO_TARGET_LUFS, AUDIO_MAX_TRUE_PEAK, AUDIO_LRA,
  13 |     COLOR_BG, FONT_BOLD, FONT_MONO,
  14 |     FFMPEG_TIMEOUT_FILTER,
  15 | )
  16 | 
  17 | logger = logging.getLogger(__name__)
  18 | 
  19 | BRAND_RED = "0xE8272B"
  20 | CARD_BG = "0x141419"
  21 | META_GRAY = "0x888888"
  22 | 
  23 | 
  24 | class XSpacesSegment(Segment):
  25 |     """X Spaces intelligence segment — branded visual with TTS narration."""
  26 |     criticality = 'optional'
  27 | 
  28 |     def render(self, spec: SegmentSpec, ctx: EpisodeContext,
  29 |                output_path: Path, idx: int) -> RenderedSegment:
  30 |         try:
  31 |             return self._render(spec, ctx, output_path, idx)
  32 |         except Exception as e:
  33 |             logger.exception(f'[x_spaces] exception: {e}')
  34 |             return self.filler_result(spec, ctx, output_path, str(e))
  35 | 
  36 |     def _render(self, spec: SegmentSpec, ctx: EpisodeContext,
  37 |                 output_path: Path, idx: int = 0) -> RenderedSegment:
  38 |         # Law 1: no content → filler
  39 |         if not spec.body:
  40 |             return self.filler_result(spec, ctx, output_path, 'no_x_spaces_content')
  41 | 
  42 |         # Get TTS audio
  43 |         tts = self._get_tts(spec, ctx, idx)
  44 |         if not tts or not tts.exists() or tts.stat().st_size < 1000:
  45 |             return self.filler_result(spec, ctx, output_path, 'no_tts_for_x_spaces')
  46 | 
  47 |         dur = ffprobe_duration(tts)
  48 |         if dur < 0.5:
  49 |             dur = 10.0
  50 | 
  51 |         tmp = output_path.with_suffix('.tmp.mp4')
  52 |         fg = self._build_filter_graph(spec)
  53 | 
  54 |         ok = run_ffmpeg([
  55 |             '-f', 'lavfi', '-i', f'color=c={COLOR_BG}:s={VIDEO_W}x{VIDEO_H}:r={VIDEO_FPS}',
  56 |             '-i', str(tts),
  57 |             '-filter_complex', fg,
  58 |             '-map', '[v_out]', '-map', '[a_out]',
  59 |             '-c:v', VIDEO_CODEC, '-crf', str(VIDEO_CRF), '-preset', 'medium',
  60 |             '-r', str(VIDEO_FPS), '-pix_fmt', VIDEO_PIX_FMT,
  61 |             '-c:a', AUDIO_CODEC, '-ar', str(AUDIO_SAMPLE_RATE),
  62 |             '-b:a', AUDIO_BITRATE, '-ac', str(AUDIO_CHANNELS),
  63 |             '-t', str(round(dur, 3)), '-movflags', '+faststart', str(tmp),
  64 |         ], 'x_spaces', FFMPEG_TIMEOUT_FILTER)
  65 | 
  66 |         if not ok or not tmp.exists() or tmp.stat().st_size < 1000:
  67 |             return self.filler_result(spec, ctx, output_path, 'x_spaces encode failed')
  68 | 
  69 |         passed, summary = ffprobe_contract(tmp)
  70 |         if not passed:
  71 |             tmp.unlink(missing_ok=True)
  72 |             return self.filler_result(spec, ctx, output_path, 'contract_failed')
  73 | 
  74 |         rename_ok = atomic_rename(tmp, output_path)
  75 |         if not rename_ok:
  76 |             tmp.unlink(missing_ok=True)
  77 |             return self.filler_result(spec, ctx, output_path, 'atomic_rename failed')
  78 |         actual = summary.get('duration', dur)
  79 |         logger.info(f'[x_spaces] OK ({actual:.1f}s)')
  80 |         return RenderedSegment(
  81 |             spec=spec, path=str(output_path), duration=actual,
  82 |             contract_passed=True, degraded=False, ffprobe_summary=summary,
  83 |         )
  84 | 
  85 |     def _get_tts(self, spec: SegmentSpec, ctx: EpisodeContext, idx: int = 0):
  86 |         """Get TTS audio: spec.tts_path first, then inline ElevenLabs."""
  87 |         tts = spec.tts()
  88 |         if tts and tts.exists() and tts.stat().st_size >= 1000:
  89 |             return tts
  90 | 
  91 |         # Inline ElevenLabs — follow cold_open.py pattern
  92 |         try:
  93 |             from ..network import http_post
  94 |             key = os.environ.get('ELEVENLABS_API_KEY', '')
  95 |             if not key:
  96 |                 return None
  97 |             voice_id = '1SM7GgM6IMuvQlz2BwM3'
  98 |             text = spec.body[:500]
  99 |             out_path = ctx.segment_dir() / f'xspaces_{idx}_tts.mp3'
 100 |             resp = http_post(
 101 |                 f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}',
 102 |                 headers={'xi-api-key': key, 'Content-Type': 'application/json'},
 103 |                 json_body={
 104 |                     'text': text,
 105 |                     'model_id': 'eleven_turbo_v2_5',
 106 |                     'voice_settings': {'stability': 0.5, 'similarity_boost': 0.5},
 107 |                 },
 108 |                 timeout=30,
 109 |             )
 110 |             if resp is None or len(resp.content) < 1000:
 111 |                 return None
 112 |             out_path.write_bytes(resp.content)
 113 |             return out_path
 114 |         except Exception as e:
 115 |             logger.warning(f'[x_spaces] inline TTS failed: {e}')
 116 |             return None
 117 | 
 118 |     def _build_filter_graph(self, spec: SegmentSpec) -> str:
 119 |         """Build branded X Spaces visual filter graph."""
 120 |         parts = [f'[0:v]scale={VIDEO_W}:{VIDEO_H},format={VIDEO_PIX_FMT}[bg]']
 121 | 
 122 |         # Top red eyebrow strip
 123 |         eyebrow = safe_text(spec.headline or 'X SPACES', 40)
 124 |         parts.append(
 125 |             f'[bg]drawbox=x=0:y=0:w={VIDEO_W}:h=80:color={BRAND_RED}:t=fill[bar]'
 126 |         )
 127 |         parts.append(
 128 |             f"[bar]drawtext=fontfile={FONT_BOLD}:text='{eyebrow}':"
 129 |             f"fontcolor=white:fontsize=32:x=40:y=24[top]"
 130 |         )
 131 | 
 132 |         # Main content: transcript excerpt
 133 |         body_text = safe_text(spec.body or '', 200)
 134 |         parts.append(
 135 |             f"[top]drawtext=fontfile={FONT_MONO}:text='{body_text}':"
 136 |             f"fontcolor=white:fontsize=22:x=60:y=140:line_spacing=8[mid]"
 137 |         )
 138 | 
 139 |         # Bottom attribution strip
 140 |         btc_str = safe_text(f'BTC {spec.btc_price}', 30) if spec.btc_price and spec.btc_price != 'N/A' else ''
 141 |         source_attr = safe_text('via X Spaces // Protocol Pulse', 60)
 142 |         parts.append(
 143 |             f"[mid]drawbox=x=0:y={VIDEO_H - 80}:w={VIDEO_W}:h=80:"
 144 |             f"color={CARD_BG}:t=fill[bot]"
 145 |         )
 146 |         parts.append(
 147 |             f"[bot]drawtext=fontfile={FONT_MONO}:text='{source_attr}':"
 148 |             f"fontcolor={META_GRAY}:fontsize=18:x=40:y={VIDEO_H - 52}[v_out]"
 149 |         )
 150 | 
 151 |         # Audio processing
 152 |         parts.append(
 153 |             f'[1:a]aformat=channel_layouts=stereo:sample_rates={AUDIO_SAMPLE_RATE},'
 154 |             f'loudnorm=I={AUDIO_TARGET_LUFS}:TP={AUDIO_MAX_TRUE_PEAK}:LRA={AUDIO_LRA}:linear=true,'
 155 |             f'alimiter=limit={AUDIO_LIMITER}:attack=5:release=50[a_out]'
 156 |         )
 157 | 
 158 |         return ';'.join(parts)
 159 | 
```

### File: video_pipeline_v3/utils/spaces_pipeline.py (160 lines)
```
   1 | #!/usr/bin/env python3
   2 | """
   3 | spaces_pipeline.py — Bridge between x_spaces_scraper and assembler_v2.
   4 | 
   5 | Reads transcript cache from x_spaces_scraper/cache/ and returns
   6 | formatted segment data for video injection.
   7 | 
   8 | V3: Strict transcript truth — only audio_replay/live_capture sources.
   9 | context_only rejected entirely at this bridge level.
  10 | """
  11 | import json
  12 | import logging
  13 | import os
  14 | import re
  15 | import time
  16 | from pathlib import Path
  17 | 
  18 | logger = logging.getLogger(__name__)
  19 | 
  20 | CACHE_DIR = Path(__file__).parent.parent.parent / "x_spaces_scraper" / "cache"
  21 | 
  22 | 
  23 | def score_transcript(transcript: dict) -> int:
  24 |     """
  25 |     Score 0-100 for video injection priority.
  26 |     - Controversy/named entity keywords: +25
  27 |     - Data/metrics (numbers, %): +20
  28 |     - Named entity + prediction language: +20
  29 |     - Breaking/urgent reference: +10
  30 |     - Length bonus: 150-300w +5, 300-600w +10, 600w+ +15
  31 |     Max: 100
  32 |     """
  33 |     text = transcript.get("transcript", transcript.get("text", "")).lower()
  34 |     score = 0
  35 | 
  36 |     # Controversy / named entity keywords
  37 |     controversy_kws = [
  38 |         "saylor", "blackrock", "sec", "gensler", "etf", "ban", "regulation",
  39 |         "institutional", "congress", "fed", "powell", "inflation", "hack",
  40 |         "exploit", "lawsuit", "fraud", "arrest",
  41 |     ]
  42 |     if any(kw in text for kw in controversy_kws):
  43 |         score += 25
  44 | 
  45 |     # Data / metrics (numbers, %)
  46 |     if re.search(r'\d+\.?\d*\s*%', text) or re.search(r'\$\d+', text) or re.search(r'\d{4,}', text):
  47 |         score += 20
  48 | 
  49 |     # Named entity + prediction language
  50 |     prediction_kws = ["predict", "forecast", "expect", "will reach", "target", "by 20"]
  51 |     entity_kws = ["bitcoin", "btc", "lightning", "mining", "hashrate"]
  52 |     has_prediction = any(kw in text for kw in prediction_kws)
  53 |     has_entity = any(kw in text for kw in entity_kws)
  54 |     if has_prediction and has_entity:
  55 |         score += 20
  56 | 
  57 |     # Breaking / urgent
  58 |     if "breaking" in text or "urgent" in text or "just announced" in text:
  59 |         score += 10
  60 | 
  61 |     # Length bonus
  62 |     wc = len(text.split())
  63 |     if wc >= 600:
  64 |         score += 15
  65 |     elif wc >= 300:
  66 |         score += 10
  67 |     elif wc >= 150:
  68 |         score += 5
  69 | 
  70 |     return min(score, 100)
  71 | 
  72 | 
  73 | def get_latest_spaces_segment(max_age_hours: float = 4.0):
  74 |     """
  75 |     Scan x_spaces_scraper/cache/ for the highest-quality usable transcript
  76 |     written within the last max_age_hours.
  77 | 
  78 |     Returns a dict compatible with assembler_v2 SegmentSpec, or None if nothing fresh.
  79 | 
  80 |     Rules:
  81 |     - Only return transcripts with usable=True AND source in (audio_replay, live_capture)
  82 |     - Reject context_only entirely (usable=False always in this bridge)
  83 |     - Reject transcripts older than max_age_hours
  84 |     - Return highest impact_score among candidates
  85 |     - If max_age_hours=0, always return None (used in tests)
  86 |     """
  87 |     if max_age_hours <= 0:
  88 |         return None
  89 | 
  90 |     if not CACHE_DIR.exists():
  91 |         return None
  92 | 
  93 |     best = None
  94 |     best_impact = -1
  95 |     now = time.time()
  96 |     max_age_s = max_age_hours * 3600
  97 | 
  98 |     for item in CACHE_DIR.glob("transcript_*.json"):
  99 |         try:
 100 |             mtime = item.stat().st_mtime
 101 |             age = now - mtime
 102 |             if age > max_age_s:
 103 |                 continue
 104 | 
 105 |             data = json.loads(item.read_text())
 106 | 
 107 |             # Normalize old cache format
 108 |             if "text" in data and "transcript" not in data:
 109 |                 data["transcript"] = data["text"]
 110 | 
 111 |             # Strict source truth: only audio_replay / live_capture
 112 |             source = data.get("source", "")
 113 |             if source not in ("audio_replay", "live_capture"):
 114 |                 continue
 115 | 
 116 |             # Must be marked usable
 117 |             if not data.get("usable", False):
 118 |                 continue
 119 | 
 120 |             impact = score_transcript(data)
 121 |             if impact > best_impact:
 122 |                 best_impact = impact
 123 |                 best = data
 124 |                 best["_mtime"] = mtime
 125 |                 best["_impact"] = impact
 126 |         except (json.JSONDecodeError, OSError):
 127 |             continue
 128 | 
 129 |     if best is None:
 130 |         return None
 131 | 
 132 |     # Build TTS text: first 500 words, cleaned
 133 |     transcript_text = best.get("transcript", best.get("text", ""))
 134 |     words = transcript_text.split()[:500]
 135 |     tts_text = " ".join(words)
 136 |     # Strip HTML tags and special chars
 137 |     tts_text = re.sub(r'<[^>]+>', '', tts_text)
 138 |     tts_text = re.sub(r'[^\w\s.,!?\'-]', '', tts_text)
 139 | 
 140 |     return {
 141 |         "segment_type": "x_spaces",
 142 |         "space_id": best.get("space_id", ""),
 143 |         "host": best.get("host", best.get("speaker", "unknown")),
 144 |         "title": best.get("title", best.get("space_title", "X Space")),
 145 |         "transcript": transcript_text[:2000],
 146 |         "source": best.get("source", "unknown"),
 147 |         "word_count": len(transcript_text.split()),
 148 |         "quality_score": best.get("quality_score", 0.0),
 149 |         "impact_score": best["_impact"],
 150 |         "speakers": best.get("speakers", []),
 151 |         "tts_text": tts_text,
 152 |         "eyebrow": "LIVE X SPACES SIGNAL",
 153 |         "cached_at": best["_mtime"],
 154 |     }
 155 | 
 156 | 
 157 | if __name__ == "__main__":
 158 |     seg = get_latest_spaces_segment()
 159 |     print("SPACES SEGMENT:", json.dumps(seg, indent=2) if seg else "None")
 160 | 
```

---



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
