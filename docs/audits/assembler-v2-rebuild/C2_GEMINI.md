# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
## Feature: assembler-v2-rebuild

This is my second and final review of the `assembler-v2-rebuild` codebase, incorporating the findings from all AI models in Cycle 1.

---

### 1. WHAT DID THEY CATCH THAT YOU MISSED?

In my first review, I correctly identified the sequential rendering bottleneck and the potential for silent failures in concatenation. However, the other models surfaced several more critical and subtle issues that I overlooked.

*   **`threading.Lock` Race Condition (Gemini):** This was the most critical finding I missed. Gemini correctly pointed out that a `threading.Lock` offers no protection between separate processes (e.g., Gunicorn workers). My analysis failed to consider the multi-process deployment context mentioned in the tech stack, leading me to incorrectly assess the cache lock as merely a potential bottleneck rather than a critical race condition that will lead to corrupted cache files and API "thundering herd" problems.
*   **Massive Code Duplication Bypassing `encode_segment` (All Models):** While I noticed some inconsistencies, I failed to grasp the scale and systemic nature of this problem. The consensus report (U3) correctly identifies this as a "massive" issue. Multiple segments re-implement their own less-robust encoding logic, forgoing the superior temp-file, contract-checking, and emergency fallback features of the central `encode_segment` function. This is a major quality and correctness failure that I underestimated.
*   **Silent Dropping of Segments (GPT-4O):** GPT-4O correctly identified a critical failure path where `Segment.filler_result()` can return a `RenderedSegment` with `path=None` if even the emergency filler fails. The concatenation logic in `episode.py` then silently skips this segment. I missed this, and it represents a major correctness flaw where a final video can be produced missing required content.
*   **Double-Counting Degraded Segments (GPT-4O):** I completely missed the logic bug in `NarrationSegment` where `ctx.mark_degraded()` is called just before `self.filler_result()`, which *also* calls `ctx.mark_degraded()`. This directly corrupts the metrics used for the final verdict.
*   **Lack of API Rate Limiting (All Models):** The consensus (U1) unanimously flagged the absence of rate limiting on ElevenLabs API calls. This is a significant operational and financial risk (cost overruns, API key suspension) that I did not flag in my initial review.

### 2. WHERE DO YOU AGREE OR DISAGREE?

I have reviewed the key findings from the other models and the consensus report.

*   **U1: Rate Limiting on ElevenLabs API is Absent:** **Strongly Agree.** This is a critical operational oversight. Unbounded, un-throttled calls to a third-party metered API are a recipe for failure, either through cost overruns or API key suspension. This must be fixed.
*   **U2: Hardcoded ElevenLabs `voice_id` Magic String:** **Agree.** A straightforward quality-of-life and maintenance improvement.
*   **U3: Massive Encode Path Duplication:** **Strongly Agree.** This is the single largest architectural flaw in the codebase. It multiplies the surface area for bugs, creates inconsistent error handling, and makes the system brittle. Refactoring all segments to use `encode_segment` is paramount.
*   **Gemini: Race Condition in Metrics Caching:** **Strongly Agree.** This is a P0, critical correctness bug. The use of `threading.Lock` is fundamentally wrong for the described multi-process environment. This will fail under load. A file-based lock (e.g., `filelock` library) or a proper external cache (Redis) is required.
*   **GPT-4O: `filler_result()` can leave no output file:** **Strongly Agree.** This is a severe silent failure mode. The system's contract should be that if a segment render is attempted, *some* video file for that duration is produced, even if it's just black frames. Silently omitting it from the final product is unacceptable.
*   **GPT-4O: Preflight ordering bug:** **Partially Agree.** GPT-4O is correct that the disk space check in `preflight.py` is performed on the parent `output_dir` before the episode-specific `workdir` is created. While technically less precise, in most common deployment scenarios (e.g., a single Docker volume), this check is sufficient. It's a minor correctness issue, but not a critical bug. I would classify it as a low-priority improvement.

### 3. NEW FINDINGS FROM THIS REVIEW

After synthesizing the Cycle 1 findings and re-examining the code, I have identified additional issues:

*   **Duplicated TTS Generation Logic:** The logic for making on-demand ElevenLabs API calls is duplicated across `social.py` (line 98), `signal_active.py` (line 191), and `x_spaces_segment.py` (line 100). This logic should be extracted into a single helper function. This new helper would also be the ideal place to implement the missing rate limiting (U1).
*   **Brittle Playwright Chromium Discovery:** The `_find_chromium` method in `social.py` (lines 124-145) uses a series of fallbacks, including globbing user cache directories (`~/.cache/ms-playwright/...`). This is extremely brittle and environment-dependent, making deployments unpredictable. The system should rely on a single, explicit environment variable for the Chromium path and fail preflight if it's not present and valid. The fallback to `drawtext` is good, but relying on fragile discovery mechanisms to avoid it is an operational risk.
*   **Inconsistent `ffprobe` Usage:** `helpers.py` centralizes `ffprobe` calls for duration and stream info, but `ffmpeg_core/probe.py` uses `subprocess.run` directly for its QC probes (LUFS, black frames, silence). This direct usage also involves brittle `stderr` parsing via string-splitting and regex, which could easily break with future FFmpeg versions. All `ffprobe`/`ffmpeg -af ... -f null` calls should be standardized through a more robust helper that can handle JSON output where available.

### 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| Correctness | 7.0/10 | **6.0/10** | The `threading.Lock` race condition and the silent segment dropping on filler failure are both critical correctness bugs I missed. They guarantee data corruption and incorrect outputs under load or in common failure scenarios. |
| Law Compliance | 9.0/10 | **9.0/10** | No change. The code remains highly compliant with the specified laws. |
| Security | 7.0/10 | **7.0/10** | No change. My initial assessment holds. The lack of rate limiting is a vulnerability against the service's budget/quota, which fits here. `safe_text` is good but remains a high-stakes single point of failure. |
| Backend Quality | 6.5/10 | **5.0/10** | The sheer scale of the `encode_segment` bypass and duplicated TTS logic, as highlighted by the other models, is a far more severe quality issue than I initially assessed. It signals a breakdown in architectural discipline. |
| Overall | 7.5/10 | **6.5/10** | The combination of a critical race condition, silent content-dropping failures, and severe architectural duplication forces a full point reduction. The system is functional but carries significant production risk. |

### 5. FINAL PRIORITY LIST

**P0: CRITICAL (Must fix before shipping; data corruption, silent failures, or major operational risk)**
1.  **Fix Metrics Cache Race Condition:** Replace `threading.Lock` with a process-safe alternative like a file-based lock or a centralized cache service (e.g., Redis). (`data_segment.py:85-91`, `state.py:37`)
2.  **Prevent Silent Segment Dropping:** `Segment.filler_result()` and `encode_segment()`'s filler logic must guarantee an output file is always written, even if it's an emergency black frame. If file creation is impossible, the entire episode render must halt immediately with an error. (`segments/base.py:58`, `ffmpeg_core/encode.py:41-56`, `episode.py:143`)
3.  **Implement API Rate Limiting:** Add a rate limiter (e.g., semaphore, token bucket) around all calls to the ElevenLabs API to prevent cost overruns and service suspension. (`segments/social.py:100`, `segments/signal_active.py:191`, `segments/x_spaces_segment.py:100`)

**P1: HIGH (High impact on correctness, robustness, or maintainability)**
1.  **Centralize All Encoding:** Refactor all segments (`cold_open`, `narration`, `partner_clip`, `data_segment`, etc.) to use the robust, central `ffmpeg_core/encode.py::encode_segment` function. This is the top priority for improving code quality and reliability. (Affects most `segments/*.py` files)
2.  **Fix Degraded Segment Double-Counting:** Remove the redundant `ctx.mark_degraded()` call in `NarrationSegment.render()` to ensure accurate verdict metrics. (`segments/narration.py:56`)
3.  **Centralize TTS Generation:** Create a single helper function for on-demand TTS generation. This function will encapsulate the API call, error handling, and the new rate limiting logic. (Refactor `social.py:87`, `signal_active.py:176`, `x_spaces_segment.py:85`)

**P2: MEDIUM (Important but less urgent quality improvements)**
1.  **Make Chromium Path Explicit:** Remove the brittle `_find_chromium` logic and require an environment variable for the executable path. Add a check to preflight to ensure it's set and valid. (`segments/social.py:124-145`)
2.  **Improve `preflight.py` Readability:** Reformat the file to adhere to basic PEP 8 standards (one statement per line, meaningful variable names). (`preflight.py:1-52`)
3.  **Extract Hardcoded Constants:** Move the hardcoded ElevenLabs voice ID to `constants.py`. (`segments/social.py:98`, `segments/signal_active.py:183`, `segments/x_spaces_segment.py:97`)
4.  **Fix Preflight Directory Check:** Adjust preflight logic to run *after* `EpisodeContext.create()` and check disk space in the actual `ctx.workdir`. (`episode.py:98`, `episode.py:108`)

### 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Refactor all segment render paths to use the central, robust `encode_segment` function, which eliminates vast code duplication and standardizes error handling and fallbacks across the entire pipeline.

### 7. PRODUCTION READY?

**No.**

The system in its current state is not production-ready. The combination of a critical race condition leading to data corruption (`P0.1`), a silent failure mode that can omit required content from the final video (`P0.2`), and unbounded external API calls creating financial and operational risk (`P0.3`) makes it unsafe to deploy.

**Conditions for production readiness:** All P0-critical issues on the priority list must be resolved.