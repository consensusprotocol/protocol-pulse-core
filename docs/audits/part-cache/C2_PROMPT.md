# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: part-cache
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GPT4O — CYCLE 1 OUTPUT
## SECTION 1: CORRECTNESS

### Main User Flow
1. **Initialization and Argument Parsing**: The script begins by parsing command-line arguments to determine the mode of operation (test, skip-scan, fast-test, reuse-content) [lines 1580-1590].
2. **Process Locking**: A file lock is used to prevent multiple instances of the script from running simultaneously [lines 1592-1598].
3. **Pipeline Execution**: The `run_pipeline` function orchestrates the entire video production process [lines 522-1549].
   - **BTC Price Fetching**: Retrieves the current Bitcoin price using two external APIs [lines 142-161].
   - **Channel Scanning**: Scans partner channels for new videos or uses cached transcripts [lines 672-698].
   - **Clip Selection**: Selects clips from scanned videos, with a fallback mechanism for quality assurance [lines 707-849].
   - **Clip Extraction**: Extracts video clips using `yt-dlp` [lines 771-879].
   - **Mood Classification and Music Selection**: Determines the mood of the episode and selects appropriate music [lines 880-945].
   - **Script Generation**: Generates the host dialogue script [lines 1033-1076].
   - **TTS Generation**: Converts the script into audio using ElevenLabs TTS [lines 1077-1087].
   - **Video Assembly**: Assembles the final video from clips and audio [lines 1140-1155].
   - **Quality Checks**: Performs preflight and post-render quality checks [lines 1158-1188, 1289-1308].
   - **Output Generation**: Generates additional outputs like shorts, thumbnails, chapters, podcasts, and newsletters [lines 1191-1236].
   - **Verification**: Verifies the final video output [lines 1239-1288].
   - **Quality Gate and Auto-Upload**: Evaluates the quality score and decides on auto-upload [lines 1391-1444].
   - **Stage Brief and Format Multiplier**: Generates a stage brief and launches secondary format generation [lines 1446-1520].
   - **Health Check and Notifications**: Sends notifications based on the health check results [lines 1521-1547].

### Issues
- **Silent Failures**: Several `try/except` blocks suppress exceptions without logging detailed errors, potentially hiding critical issues (e.g., lines 1030, 1306).
- **Concurrency**: The use of a file lock prevents multiple instances but does not handle concurrent requests within the same instance, which could lead to race conditions.
- **Edge Cases**: The script does not handle the case where no clips are selected or extracted, which could lead to a failed episode production [lines 740, 873].

## SECTION 2: LAW COMPLIANCE

- **Compliant**: The code adheres to the specified technology stack and does not use prohibited technologies (e.g., Three.js, WebGL).
- **Partial Compliance**: The requirement for every DB query on a sort/filter column to have an index is not applicable as there are no direct DB queries in the provided code.
- **Violation**: The code does not explicitly mention compliance with any specific governing laws, which should be clarified.

## SECTION 3: SECURITY

- **SQL Injection**: Not applicable as there are no raw SQL queries.
- **Authentication Bypasses**: Not applicable as there are no routes or web services exposed.
- **Rate Limiting**: External API calls (e.g., BTC price fetching) lack rate limiting, which could exhaust API limits [lines 142-161].
- **Secrets in Code**: The Resend API key is fetched from environment variables, which is a good practice [line 203].
- **Unvalidated Input**: The script does not handle invalid or malformed inputs from external APIs, which could lead to unexpected behavior.

## SECTION 4: FRONTEND QUALITY

- **UI Compliance**: Not applicable as the code is backend-focused.
- **Dynamic Values**: The script dynamically fetches BTC prices and other data, avoiding hardcoded values.
- **Error Handling**: Error states are logged but not always handled gracefully, especially in async operations [e.g., line 1030].
- **World-Class Look**: Not applicable as there is no frontend UI to evaluate.

## SECTION 5: BACKEND QUALITY

- **DB Operations**: Not applicable as there are no DB operations.
- **API Calls**: Lack of retries and graceful degradation for external API calls [lines 142-161].
- **Cron Job Handling**: The script uses a file lock to prevent duplicate runs, which is a good practice [lines 1592-1598].
- **Memory Leaks**: Potential for memory leaks with large objects not being cleaned up, especially in the case of failed operations.
- **Logging**: Errors are logged, but more context could be provided for easier debugging [e.g., line 1030].

## SECTION 6: WORLD-CLASS GAP ANALYSIS

- **User Experience**: A more interactive and user-friendly interface for monitoring the pipeline's progress would enhance the user experience.
- **Error Reporting**: Implementing a centralized error reporting system would help in quickly identifying and resolving issues.
- **Scalability**: Introducing asynchronous processing and better concurrency handling would improve scalability for handling more concurrent users.

## SEC

## GROK — CYCLE 1 OUTPUT
### CODE AUDIT REPORT: PROTOCOL PULSE — CODE AUDIT PACKAGE (part-cache, main branch)

**Reviewer: GPT-4o**

Below is a detailed forensic review of the provided codebase for `daily_producer.py` and `feature_flags.json`. I have followed the structure and requirements outlined in the task, focusing on correctness, compliance, security, quality, and actionable improvements.

---

### SECTION 1: CORRECTNESS

**Main User Flow Analysis (Step-by-Step):**
The `daily_producer.py` script is a comprehensive pipeline for producing daily video content for Protocol Pulse, involving scanning YouTube channels, selecting clips, generating scripts, producing audio, assembling videos, and handling post-production tasks like quality checks and uploads. Below is a step-by-step analysis of the main flow in `run_pipeline()` (lines 522-1551):

1. **Initialization (Lines 522-590):** The pipeline initializes with mode flags (test, fast-test, skip-scan) and clears VRAM for GPU usage. It also checks for resumable state via checkpoints (lines 540-554). **Correctness Issue:** The VRAM clearing (lines 530-537) lacks error logging context if `torch` is unavailable or fails, which could silently fail in production.
2. **Content Lock/Reuse (Lines 601-657):** If `--reuse-content` is enabled, the pipeline skips content generation and reuses locked content. **Correctness Issue:** If locked content is corrupted or incomplete, there’s no validation before reuse (line 610), risking pipeline failure without clear error messaging.
3. **BTC Price Fetch (Lines 662-669):** Fetches Bitcoin price from APIs with fallback. **Correctness Issue:** No retry mechanism for API failures beyond a single timeout (lines 145-160), which could result in `$N/A` being used silently in production during transient network issues.
4. **Channel Scanning (Lines 672-698):** Scans YouTube channels for videos or uses cached transcripts if `--skip-scan` is set. **Correctness Issue:** No validation of cached transcript integrity (lines 677-690), risking stale or malformed data being used.
5. **Clip Selection and Extraction (Lines 707-873):** Selects clips using Claude API or hardcoded logic in fast-test mode, then extracts them using `yt-dlp`. **Correctness Issue:** Fallback selection for low-quality clips (lines 794-850) could loop indefinitely if no suitable clips are found, and there’s no timeout or cap on retries.
6. **Script Generation and TTS (Lines 1033-1088):** Generates host dialogue and converts text to speech via ElevenLabs. **Correctness Issue:** No fallback for TTS failures (line 1081), meaning a single failed audio line could halt the pipeline without graceful degradation.
7. **Video Assembly and QC (Lines 1141-1290):** Assembles the video and runs pre-flight and post-render quality checks. **Correctness Issue:** Pre-flight QC fixes (lines 1185-1187) modify the video in-place without a backup, risking data loss if the fix fails.
8. **Shorts, Thumbnails, Chapters, etc. (Lines 1192-1238):** Generates additional assets. **Correctness Issue:** No error handling for thumbnail generation failures (line 1208), which could silently skip critical assets.
9. **Quality Gate and Upload (Lines 1392-1445):** Computes a quality score and uploads to YouTube if thresholds are met. **Correctness Issue:** Quality score computation (line 1395) lacks fallback if `compute_quality_score()` fails, potentially blocking uploads without notice.
10. **Format Multiplier and Alerts (Lines 1493-1521):** Launches secondary format generation as a detached process and sends alerts. **Correctness Issue:** Detached subprocess for format multiplier (line 1507) lacks monitoring or error reporting, risking silent failures of secondary formats.

**Additional Correctness Issues:**
- **Race Conditions:** The use of `/tmp/render_checkpoint.json` (line 59) and file locks (line 1595) for process synchronization could lead to race conditions if multiple instances write simultaneously, as `fcntl.flock` is not guaranteed to be atomic across all filesystems.
- **Edge Cases:** Empty or malformed input from APIs (e.g., `get_btc_price()` at line 142) isn’t robustly handled beyond returning `$N/A`, which could propagate bad data through the pipeline.
- **Silent Failures:** Many `try/except` blocks (e.g., line 116) simply `pass` without logging, making debugging production issues difficult.

---

### SECTION 2: LAW COMPLIANCE

Since no specific "GOVERNING LAWS" were provided in the audit package under the "GOVERNING LAWS" section (it’s empty), I will assume compliance is to be evaluated against implied standards based on the technology stack and purpose. If specific laws were intended, they are missing from the input. Below are assessments based on common pipeline requirements and the provided context:

- **Load Handling for ~1000 Concurrent Users (Technology Stack):** **PARTIAL COMPLIANCE.** The code uses file-based locking (line 1595) to prevent multiple pipeline runs, but there’s no evidence of handling concurrent 

## GEMINI — CYCLE 1 OUTPUT
Here is a forensic code review of the `part-cache` feature.

### SECTION 1: CORRECTNESS

The overall pipeline logic is a straightforward, sequential process that is mostly correct. However, there are several significant logic errors and potential failures.

-   **CRITICAL FLAW: Checkpoint/Resume Logic is Broken.** The `_read_checkpoint()` function (line 120) correctly reads the last completed step, and this is called at the start of `run_pipeline` (line 540). However, the `resume_step` variable is **never used to actually skip steps**. The logic at lines 541-553 only uses it to log a message and potentially set `skip_scan=True`. The pipeline execution then proceeds from the very beginning (Step 1). This completely defeats the purpose of the "resume-on-crash" feature mentioned in the comments (line 69). The `--reuse-content` flag implements a similar but separate logic path correctly, but the primary checkpoint system is non-functional.

-   **Potential Resource Leak:** The Space Tap feature at lines 1012-1018 uses `threading` with a `join(timeout=120)`. If the target function `_fetch_spaces` hangs indefinitely (e.g., due to a network issue or a bug in the scraper), the main thread will correctly time out and continue. However, the hung `_st_t` thread cannot be killed and will continue to exist in the background, consuming resources. If this happens on multiple runs, it could lead to a gradual exhaustion of resources on the server. Using `multiprocessing.Process` would be safer, as a process can be reliably terminated.

-   **Minor Logic Error:** In the fallback clip selection logic (lines 794-851), a fallback clip `fc` is checked against `used_channels` and `tried_video_ids` *before* being added to the extraction attempt. If the extraction `extract_all({"clips": [fc]}, clip_dir)` then fails, `tried_video_ids` is updated (line 839), but `used_channels` is not. A subsequent fallback clip from the same channel could be attempted, even though that channel might be the source of the problem (e.g., region-locked, private). This is a minor edge case but could lead to inefficient retries.

-   **Silent Failure:** In `get_btc_price` (line 142), if both CoinGecko and mempool.space APIs fail, the function returns "$N/A". This is passed downstream and may be rendered directly into the video's cold open (line 170) or thumbnail (line 1212) without raising a more significant alert that a key piece of data is missing. While graceful, this might not be the desired behavior for a premium intelligence product.

### SECTION 2: LAW COMPLIANCE

The "GOVERNING LAWS" section was not provided in the prompt. However, based on code comments that refer to internal "laws", compliance is as follows:

-   **SOLO HOST law (line 168):** COMPLIANT. The `_build_fast_test_script` function correctly assigns all dialogue to a single host.
-   **PIPELINE_LAWS: 8-15 min (line 243):** PARTIAL. There is an inconsistency. The post-render health check at line 244 validates a duration of `480-900s` (8-15 minutes). However, the pre-flight QC check at line 400 validates a duration of `420-900s` (7-15 minutes). These ranges should be identical and defined as a shared constant.
-   **CONTENT LOCK LAW (line 556):** COMPLIANT. The logic at lines 558-564 correctly preserves the TTS cache when the `reuse-content` flag is active.
-   **FORMAT MULTIPLIER LAWS (lines 1493-1494):** COMPLIANT. The code correctly checks for a successful render before launching the multiplier (line 1495) and correctly launches it as a detached subprocess (lines 1507-1512).

### SECTION 3: SECURITY

The code is a command-line script for internal use, which significantly reduces the attack surface. Security posture is strong for its intended environment.

-   **SQL Injection:** NOT APPLICABLE. No database interaction is present in the provided code.
-   **Authentication Bypasses:** NOT APPLICABLE. This is a CLI tool, not a web service.
-   **Rate Limiting:** The script is locked with `fcntl.flock` (line 1595), preventing multiple simultaneous runs from exhausting API quotas. This is effective process-level rate limiting.
-   **Secrets in Code:** COMPLIANT. The Resend API key is correctly loaded from an environment variable at line 203. There are no hardcoded secrets.
-   **Unvalidated Input:** COMPLIANT. The script uses `subprocess.run` and `subprocess.Popen` extensively, but all arguments passed to the shell are either static strings or internally generated, safe file paths. There is no clear path for user-influenced input to become part of a shell command, mitigating injection risks.

### SECTION 4: FRONTEND QUALITY

NOT APPLICABLE. No frontend code was provided for review.

### SECTION 5: BACKEND QUALITY

The script demonstrates a mature approach to quality and robustness in many areas, but has significant architectural flaws.

-   **External API Calls:** EXCELLENT. Calls like `get_btc_price` (line 142) include timeouts, try/except blocks, and fallback logic. This pattern of gracef

## CLAUDE'S CYCLE 1 CONSENSUS
# CONSENSUS REPORT — PART-CACHE — CYCLE 1
Generated: 2026-03-24 18:42
Models: gpt4o, grok, gemini

---

## SCORES

| Subsystem       | Gemini | GPT-4o | Grok | Consensus |
|-----------------|--------|--------|------|-----------|
| Backend Logic   | ~72    | 75     | ~72  | **73/100** |
| Frontend/UI     | N/A    | N/A    | N/A  | **N/A** |
| Error Handling  | ~60    | 65     | ~60  | **62/100** |
| Security        | ~78    | 70     | ~65  | **71/100** |
| Performance     | ~65    | 70     | ~65  | **67/100** |
| Law Compliance  | ~70    | 80     | ~70  | **73/100** |
| World-Class Gap | ~45    | 60     | ~50  | **52/100** |
| **OVERALL**     | ~65    | 70     | ~65  | **67/100** |

> Note: Gemini and Grok did not emit a formal score table; scores above are calibrated from their written severity assessments against GPT-4o's explicit scale. Consensus is a trimmed mean.

---

## UNANIMOUS FINDINGS (all 3 models agree — implement unconditionally)

### U1 — Silent `except` Blocks Swallow Errors
- **What:** Multiple `try/except` blocks catch exceptions and either `pass` silently or log without stack traces, making production debugging nearly impossible.
- **File/Lines:** `daily_producer.py` lines ~116, ~1030, ~1306, and scattered throughout.
- **Change:** Replace every bare `except: pass` and context-free `except Exception` with `logger.exception(...)` (which automatically includes the traceback). Never suppress without at minimum a `logger.warning` with the exception message.

### U2 — No Retry / Backoff on External API Calls
- **What:** All three models flagged that calls to CoinGecko, mempool.space, ElevenLabs, and YouTube (via yt-dlp) have at most a single timeout with no retry loop and no exponential backoff. A transient network blip kills the pipeline.
- **File/Lines:** `daily_producer.py` lines ~142–161 (`get_btc_price`), ~1081 (TTS), ~790 (yt-dlp).
- **Change:** Wrap every external HTTP call in a retry decorator (e.g., `tenacity.retry` with `stop=stop_after_attempt(3)`, `wait=wait_exponential(min=2, max=30)`). Surface final failure as a logged critical alert, not a silent `$N/A`.

### U3 — Unvalidated External API Responses Used Downstream
- **What:** Data returned from external APIs (BTC price, transcript content, clip metadata) is used directly in filenames, JSON parsing, and rendered content without validation. All three models noted this.
- **File/Lines:** `daily_producer.py` lines ~145–160, ~677–690.
- **Change:** Add schema validation (e.g., `pydantic` models or explicit `isinstance` + key-existence checks) before any API response is used. Reject and alert on malformed responses rather than propagating `None` or `$N/A` silently.

### U4 — Monolithic `run_pipeline()` Function (~1000 lines) Is Unmaintainable
- **What:** All three models independently identified the single 1000-line procedural function as an architectural liability — untestable, undebuggable, and fragile.
- **File/Lines:** `daily_producer.py` lines ~522–1549.
- **Change:** D

---

## ORIGINAL CODE (same code as Cycle 1)
## THE CODE (every new and modified file)

### File: video_pipeline_v3/daily_producer.py (1619 lines)
```
   1 | #!/usr/bin/env python3
   2 | """Daily Pulse Check Producer V5 — clip-first pipeline.
   3 | 
   4 | Real YouTube clips from partner channels, host dialogue around them,
   5 | music integration, cold open, avatar shorts.
   6 | 
   7 | Usage:
   8 |   python3 daily_producer.py               # Full daily episode
   9 |   python3 daily_producer.py --test        # Test mode (fewer clips, truncated)
  10 |   python3 daily_producer.py --skip-scan   # Use cached transcripts only
  11 |   python3 daily_producer.py --fast-test   # Fast test: no API calls, <3 min render
  12 | """
  13 | import sys; sys.dont_write_bytecode=True
  14 | import argparse
  15 | import fcntl
  16 | import json
  17 | import logging
  18 | import os
  19 | import shutil
  20 | import subprocess
  21 | import sys
  22 | import time
  23 | from datetime import datetime, timezone
  24 | 
  25 | BASE = os.path.dirname(os.path.abspath(__file__))
  26 | sys.path.insert(0, BASE)
  27 | 
  28 | from channel_scanner import scan_all_channels
  29 | from clip_selector import select_clips
  30 | from clip_extractor import extract_all, extract_montage_all, check_av_sync
  31 | from script_writer import generate_from_clips
  32 | from tts_engine import generate_dialogue_audio
  33 | from assembler import assemble_episode, verify_video
  34 | from shorts_cutter import generate_shorts
  35 | from thumbnail_gen import generate_thumbnail
  36 | from chapters import generate_chapters
  37 | from podcast_feed import extract_podcast_audio, generate_rss_item
  38 | from newsletter_embed import generate_email_html, save_newsletter_html
  39 | from music import ensure_music_dir, has_music, has_intro, has_outro
  40 | from utils.feature_flags import is_enabled, load_all as load_flags
  41 | from utils.quality_gate import compute_quality_score, should_upload, format_score_report
  42 | from utils.telegram_alerts import (
  43 |     alert_pipeline_start, alert_pipeline_success,
  44 |     alert_pipeline_failure, alert_quality_hold, alert_upload_success,
  45 | )
  46 | 
  47 | # Setup logging
  48 | logging.basicConfig(
  49 |     level=logging.INFO,
  50 |     format="%(message)s",
  51 | )
  52 | logger = logging.getLogger("Producer")
  53 | 
  54 | 
  55 | # ---------------------------------------------------------------------------
  56 | # Per-Render Context File (consumed by watchdog for CC repair specs)
  57 | # ---------------------------------------------------------------------------
  58 | 
  59 | CHECKPOINT_FILE = "/tmp/render_checkpoint.json"
  60 | 
  61 | 
  62 | def write_render_context(step, status, error=None, **extra):
  63 |     """Write/update /tmp/render_context_YYYYMMDD.json for watchdog consumption.
  64 | 
  65 |     Called after every pipeline step completes or fails. The watchdog reads this
  66 |     file to give Claude Code full context about what was being built when a crash
  67 |     occurred. See QWEN_CONTEXT_BIBLE.md Section 7.
  68 | 
  69 |     P0 Fix 3: Also writes step-level checkpoint for resume-on-crash.
  70 |     """
  71 |     ctx_path = f"/tmp/render_context_{datetime.now(timezone.utc).strftime('%Y%m%d')}.json"
  72 |     try:
  73 |         with open(ctx_path) as f:
  74 |             ctx = json.load(f)
  75 |     except Exception:
  76 |         ctx = {
  77 |             "episode_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
  78 |             "steps_completed": [],
  79 |             "steps_failed": [],
  80 |             "render_start_time": datetime.now(timezone.utc).isoformat(),
  81 |         }
  82 | 
  83 |     if status == "ok":
  84 |         if step not in ctx["steps_completed"]:
  85 |             ctx["steps_completed"].append(step)
  86 |         # P0 Fix 3: checkpoint for resume
  87 |         _write_checkpoint(step)
  88 |     else:
  89 |         ctx["steps_failed"].append({
  90 |             "step": step,
  91 |             "error": str(error)[:500],
  92 |             "timestamp": datetime.now(timezone.utc).isoformat(),
  93 |         })
  94 | 
  95 |     # Merge any extra context (episode_title, btc_price, clips, mood, etc.)
  96 |     for k, v in extra.items():
  97 |         ctx[k] = v
  98 | 
  99 |     try:
 100 |         with open(ctx_path, "w") as f:
 101 |             json.dump(ctx, f, indent=2)
 102 |     except Exception as e:
 103 |         logger.warning(f"write_render_context failed: {e}")
 104 | 
 105 | 
 106 | def _write_checkpoint(step):
 107 |     """Write last completed step number to checkpoint file."""
 108 |     try:
 109 |         data = {
 110 |             "last_completed_step": step,
 111 |             "timestamp": datetime.now(timezone.utc).isoformat(),
 112 |             "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
 113 |         }
 114 |         with open(CHECKPOINT_FILE, "w") as f:
 115 |             json.dump(data, f)
 116 |     except Exception:
 117 |         pass
 118 | 
 119 | 
 120 | def _read_checkpoint():
 121 |     """Read checkpoint. Returns last_completed_step (int) or 0 if none/stale."""
 122 |     try:
 123 |         with open(CHECKPOINT_FILE) as f:
 124 |             data = json.load(f)
 125 |         # Only resume if checkpoint is from today
 126 |         if data.get("date") != datetime.now(timezone.utc).strftime("%Y-%m-%d"):
 127 |             return 0
 128 |         return int(data.get("last_completed_step", 0))
 129 |     except Exception:
 130 |         return 0
 131 | 
 132 | 
 133 | def _clear_checkpoint():
 134 |     """Clear checkpoint after successful render."""
 135 |     try:
 136 |         if os.path.exists(CHECKPOINT_FILE):
 137 |             os.remove(CHECKPOINT_FILE)
 138 |     except OSError:
 139 |         pass
 140 | 
 141 | 
 142 | def get_btc_price() -> str:
 143 |     """Fetch current BTC price (CoinGecko primary + mempool.space fallback)."""
 144 |     try:
 145 |         import requests
 146 |         r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd", timeout=5)
 147 |         if r.status_code == 200:
 148 |             usd = r.json().get("bitcoin", {}).get("usd")
 149 |             if usd is not None:
 150 |                 return f"${usd:,.0f}"
 151 |     except Exception:
 152 |         pass
 153 |     try:
 154 |         import requests
 155 |         r = requests.get("https://mempool.space/api/v1/prices", timeout=5)
 156 |         if r.status_code == 200:
 157 |             usd = r.json().get("USD", 0)
 158 |             return f"${usd:,.0f}"
 159 |     except Exception:
 160 |         pass
 161 |     return "$N/A"  # Fallback - no hardcoded stale price
 162 | 
 163 | 
 164 | def _build_fast_test_script(clips_info: dict, btc_price: str) -> dict:
 165 |     """Build a minimal hardcoded script for fast-test mode (no Claude API call)."""
 166 |     dialogue = []
 167 |     # Cold open — PBX-only (host 2) per SOLO HOST law
 168 |     dialogue.append({
 169 |         "host": 2, "type": "cold_open",
 170 |         "text": f"[COLD_OPEN] Bitcoin at {btc_price}. Let's get into today's pulse check.",
 171 |     })
 172 |     # For each clip, add a setup + clip marker + react
 173 |     for rank, info in sorted(clips_info.items()):
 174 |         channel = info.get("channel", "Unknown")
 175 |         dialogue.append({
 176 |             "host": 2, "type": "setup",
 177 |             "text": f"[NARRATION] Here's what {channel} had to say.",
 178 |         })
 179 |         dialogue.append({
 180 |             "host": "CLIP", "type": "clip",
 181 |             "rank": rank, "source_id": info.get("video_id", ""),
 182 |         })
 183 |         dialogue.append({
 184 |             "host": 2, "type": "react",
 185 |             "text": "[NARRATION] Interesting take. Let's keep moving.",
 186 |         })
 187 |     # Wrap
 188 |     dialogue.append({
 189 |         "host": 2, "type": "wrap",
 190 |         "text": "[WARM] That's the pulse check for today. Stay sovereign.",
 191 |     })
 192 |     return {
 193 |         "episode_title": f"Fast Test — {btc_price}",
 194 |         "dialogue": dialogue,
 195 |         "thumbnail": {"headline": "FAST TEST", "subtext": btc_price},
 196 |     }
 197 | 
 198 | 
 199 | def _send_resend_alert(subject: str, body: str):
 200 |     """Send a non-blocking email alert via Resend."""
 201 |     try:
 202 |         import resend
 203 |         resend.api_key = os.environ.get("RESEND_API_KEY", "")
 204 |         if not resend.api_key:
 205 |             logger.warning("RESEND_API_KEY not set — skipping email alert")
 206 |             return
 207 |         resend.Emails.send({
 208 |             "from": "pulse@protocolpulse.io",
 209 |             "to": ["contact@consensusprotocol.org"],
 210 |             "subject": subject,
 211 |             "html": f"<pre>{body}</pre>",
 212 |         })
 213 |     except Exception as e:
 214 |         logger.warning(f"Resend alert failed: {e}")
 215 | 
 216 | 
 217 | def _post_render_health_check(video_path: str) -> tuple[bool, list[str]]:
 218 |     """Verify rendered video meets quality thresholds.
 219 | 
 220 |     Returns (passed, errors).
 221 |     """
 222 |     errors = []
 223 |     if not os.path.exists(video_path):
 224 |         return False, ["Video file does not exist"]
 225 | 
 226 |     # File size > 50MB
 227 |     size_mb = os.path.getsize(video_path) / (1024 * 1024)
 228 |     if size_mb < 50:
 229 |         errors.append(f"File size {size_mb:.1f}MB < 50MB minimum")
 230 | 
 231 |     # ffprobe checks
 232 |     try:
 233 |         probe = subprocess.run(
 234 |             ["ffprobe", "-v", "quiet", "-print_format", "json",
 235 |              "-show_format", "-show_streams", video_path],
 236 |             capture_output=True, text=True, timeout=30,
 237 |         )
 238 |         info = json.loads(probe.stdout)
 239 |         fmt = info.get("format", {})
 240 |         streams = info.get("streams", [])
 241 | 
 242 |         # Duration 480-900s (PIPELINE_LAWS: 8-15 min)
 243 |         duration = float(fmt.get("duration", 0))
 244 |         if duration < 480 or duration > 900:
 245 |             errors.append(f"Duration {duration:.0f}s outside 480-900s range (8-15 min law)")
 246 |         if duration <= 0:
 247 |             errors.append("ffprobe reports zero or negative duration — file likely corrupt")
 248 | 
 249 |         # Audio stream present
 250 |         audio_streams = [s for s in streams if s.get("codec_type") == "audio"]
 251 |         if not audio_streams:
 252 |             errors.append("No audio stream found")
 253 | 
 254 |         # Video stream present and decodable (audit P2-X3)
 255 |         video_streams = [s for s in streams if s.get("codec_type") == "video"]
 256 |         if not video_streams:
 257 |             errors.append("No video stream found")
 258 |     except Exception as e:
 259 |         errors.append(f"ffprobe failed: {e}")
 260 | 
 261 |     passed = len(errors) == 0
 262 |     if not passed:
 263 |         logger.critical(f"POST-RENDER HEALTH CHECK FAILED: {errors}")
 264 |         _send_resend_alert(
 265 |             "CRITICAL: Pulse Check render failed health check",
 266 |             f"Video: {video_path}\nErrors:\n" + "\n".join(f"  - {e}" for e in errors),
 267 |         )
 268 |     return passed, errors
 269 | 
 270 | 
 271 | import re as _re
 272 | 
 273 | # ---------------------------------------------------------------------------
 274 | # Pre-Flight QC — Grade A Guarantee
 275 | # ---------------------------------------------------------------------------
 276 | MAX_PREFLIGHT_ATTEMPTS = 3
 277 | 
 278 | _PREFLIGHT_LOG_DIR = os.path.join(BASE, "logs")
 279 | 
 280 | 
 281 | def _preflight_log(msg: str):
 282 |     """Append one line to preflight_YYYYMMDD.log."""
 283 |     os.makedirs(_PREFLIGHT_LOG_DIR, exist_ok=True)
 284 |     log_file = os.path.join(
 285 |         _PREFLIGHT_LOG_DIR,
 286 |         f"preflight_{datetime.now(timezone.utc).strftime('%Y%m%d')}.log",
 287 |     )
 288 |     ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
 289 |     with open(log_file, "a") as f:
 290 |         f.write(f"[{ts}] {msg}\n")
 291 | 
 292 | 
 293 | def run_preflight_qc(video_path: str) -> dict:
 294 |     """Run pre-flight QC checks on assembled video before grading.
 295 | 
 296 |     Returns {passed: bool, issues: list[str], metrics: dict}.
 297 | 
 298 |     Checks (all via ffprobe/ffmpeg, no LLM needed):
 299 |       1. FREEZE FRAMES — ffmpeg freezedetect n=0.003:d=1.5
 300 |       2. SILENCE GAPS  — ffmpeg silencedetect n=-50dB:d=0.8 (middle 80%)
 301 |       3. LOUDNESS      — ffmpeg ebur128 (integrated LUFS -17 to -12, TP <= -1.0)
 302 |       4. DURATION      — ffprobe (7-15 minutes)
 303 |       5. RESOLUTION    — ffprobe (1920x1080)
 304 |     """
 305 |     issues: list[str] = []
 306 |     metrics: dict = {}
 307 | 
 308 |     if not os.path.exists(video_path):
 309 |         return {"passed": False, "issues": ["Video file not found"], "metrics": {}}
 310 | 
 311 |     # ── 1. Freeze frames ──────────────────────────────────────────────────
 312 |     freeze_count = 0
 313 |     freeze_timestamps: list[float] = []
 314 |     try:
 315 |         r = subprocess.run(
 316 |             ["ffmpeg", "-i", video_path, "-vf", "freezedetect=n=0.003:d=1.5",
 317 |              "-f", "null", "-"],
 318 |             capture_output=True, text=True, timeout=300,
 319 |         )
 320 |         for m in _re.finditer(r"freeze_start:\s*([\d.]+)", r.stderr):
 321 |             freeze_timestamps.append(float(m.group(1)))
 322 |         freeze_count = len(freeze_timestamps)
 323 |     except Exception as e:
 324 |         logger.warning(f"[PREFLIGHT] freezedetect failed: {e}")
 325 |     metrics["freeze_frames"] = freeze_count
 326 |     metrics["freeze_timestamps"] = freeze_timestamps
 327 |     if freeze_count > 0:
 328 |         issues.append(f"freeze_frames={freeze_count} (max 0)")
 329 | 
 330 |     # ── 2. Silence gaps (middle 80% of video) ─────────────────────────────
 331 |     silence_gaps: list[dict] = []
 332 |     try:
 333 |         # Get duration first
 334 |         dur_r = subprocess.run(
 335 |             ["ffprobe", "-v", "error", "-show_entries", "format=duration",
 336 |              "-of", "default=noprint_wrappers=1:nokey=1", video_path],
 337 |             capture_output=True, text=True, timeout=30,
 338 |         )
 339 |         total_dur = float(dur_r.stdout.strip()) if dur_r.stdout.strip() else 0
 340 |         margin = total_dur * 0.10  # ignore first/last 10%
 341 | 
 342 |         r = subprocess.run(
 343 |             ["ffmpeg", "-i", video_path, "-af", "silencedetect=noise=-50dB:d=0.8",
 344 |              "-f", "null", "-"],
 345 |             capture_output=True, text=True, timeout=300,
 346 |         )
 347 |         for m in _re.finditer(
 348 |             r"silence_start:\s*([\d.]+).*?silence_end:\s*([\d.]+)",
 349 |             r.stderr, _re.DOTALL,
 350 |         ):
 351 |             start, end = float(m.group(1)), float(m.group(2))
 352 |             # Only count gaps in the middle 80%
 353 |             if start >= margin and end <= (total_dur - margin):
 354 |                 silence_gaps.append({"start": round(start, 2), "end": round(end, 2),
 355 |                                      "duration": round(end - start, 2)})
 356 |     except Exception as e:
 357 |         logger.warning(f"[PREFLIGHT] silencedetect failed: {e}")
 358 |     metrics["silence_gaps"] = len(silence_gaps)
 359 |     metrics["silence_details"] = silence_gaps
 360 |     if len(silence_gaps) > 0:
 361 |         issues.append(f"silence_gaps={len(silence_gaps)} (max 0 in middle 80%)")
 362 | 
 363 |     # ── 3. Loudness (ebur128) ─────────────────────────────────────────────
 364 |     lufs = None
 365 |     true_peak = None
 366 |     try:
 367 |         r = subprocess.run(
 368 |             ["ffmpeg", "-i", video_path, "-filter:a", "loudnorm=print_format=json",
 369 |              "-f", "null", "-"],
 370 |             capture_output=True, text=True, timeout=300,
 371 |         )
 372 |         json_start = r.stderr.rfind("{")
 373 |         json_end = r.stderr.rfind("}") + 1
 374 |         if json_start >= 0 and json_end > json_start:
 375 |             ln = json.loads(r.stderr[json_start:json_end])
 376 |             lufs = float(ln.get("input_i", -99))
 377 |             true_peak = float(ln.get("input_tp", 0))
 378 |     except Exception as e:
 379 |         logger.warning(f"[PREFLIGHT] loudness measurement failed: {e}")
 380 |     metrics["lufs"] = round(lufs, 1) if lufs is not None else None
 381 |     metrics["true_peak"] = round(true_peak, 1) if true_peak is not None else None
 382 |     if lufs is not None and (lufs < -17 or lufs > -12):
 383 |         issues.append(f"lufs={lufs:.1f} (target -17 to -12)")
 384 |     if true_peak is not None and true_peak > -1.0:
 385 |         issues.append(f"true_peak={true_peak:.1f}dBTP (max -1.0)")
 386 | 
 387 |     # ── 4. Duration ───────────────────────────────────────────────────────
 388 |     try:
 389 |         dur_r = subprocess.run(
 390 |             ["ffprobe", "-v", "error", "-show_entries", "format=duration",
 391 |              "-of", "default=noprint_wrappers=1:nokey=1", video_path],
 392 |             capture_output=True, text=True, timeout=30,
 393 |         )
 394 |         duration_s = float(dur_r.stdout.strip()) if dur_r.stdout.strip() else 0
 395 |     except Exception:
 396 |         duration_s = 0
 397 |     metrics["duration_s"] = round(duration_s, 1)
 398 |     dur_min = duration_s / 60
 399 |     metrics["duration_fmt"] = f"{int(dur_min)}m{int(duration_s % 60):02d}s"
 400 |     if duration_s < 420 or duration_s > 900:  # 7-15 min
 401 |         issues.append(f"duration={dur_min:.1f}min (target 7-15)")
 402 | 
 403 |     # ── 5. Resolution ─────────────────────────────────────────────────────
 404 |     width, height = 0, 0
 405 |     try:
 406 |         r = subprocess.run(
 407 |             ["ffprobe", "-v", "error", "-select_streams", "v:0",
 408 |              "-show_entries", "stream=width,height",
 409 |              "-of", "default=noprint_wrappers=1", video_path],
 410 |             capture_output=True, text=True, timeout=30,
 411 |         )
 412 |         for line in r.stdout.strip().splitlines():
 413 |             if line.startswith("width="):
 414 |                 width = int(line.split("=")[1])
 415 |             elif line.startswith("height="):
 416 |                 height = int(line.split("=")[1])
 417 |     except Exception:
 418 |         pass
 419 |     metrics["resolution"] = f"{width}x{height}"
 420 |     if width != 1920 or height != 1080:
 421 |         issues.append(f"resolution={width}x{height} (expected 1920x1080)")
 422 | 
 423 |     passed = len(issues) == 0
 424 |     _preflight_log(
 425 |         f"freeze_frames={freeze_count} silence_gaps={len(silence_gaps)} "
 426 |         f"lufs={metrics.get('lufs')} duration={metrics.get('duration_fmt')} "
 427 |         f"resolution={metrics.get('resolution')}"
 428 |     )
 429 |     _preflight_log(f"{'PASS' if passed else 'FAIL'}" + (f" — {issues}" if issues else " — proceeding to grading"))
 430 | 
 431 |     return {"passed": passed, "issues": issues, "metrics": metrics}
 432 | 
 433 | 
 434 | def _apply_preflight_fixes(video_path: str, qc: dict):
 435 |     """Apply targeted fixes for each preflight issue type.
 436 | 
 437 |     Modifies video_path IN-PLACE (via atomic rename).
 438 |     """
 439 |     issues_str = " ".join(qc.get("issues", []))
 440 | 
 441 |     # ── Freeze frame fix ──────────────────────────────────────────────────
 442 |     # Content-level freezes (static social cards / signal scenes) need
 443 |     # imperceptible temporal noise to break pixel-identical frames.
 444 |     # Plain CFR re-encode does NOT fix content-level freezes.
 445 |     if "freeze_frames" in issues_str:
 446 |         logger.info("[PREFLIGHT FIX] Re-encoding with temporal noise to break content-level freezes")
 447 |         tmp = video_path + ".freeze_fix.mp4"
 448 |         try:
 449 |             r = subprocess.run(
 450 |                 ["ffmpeg", "-y",
 451 |                  "-fflags", "+genpts+igndts+discardcorrupt",
 452 |                  "-i", video_path,
 453 |                  "-c:v", "libx264", "-preset", "medium",
 454 |                  "-b:v", "8M", "-minrate", "3.5M", "-maxrate", "10M", "-bufsize", "15M",
 455 |                  "-r", "30", "-vsync", "cfr",
 456 |                  "-vf", "noise=c0s=3:c0f=t,setpts=PTS-STARTPTS,format=yuv420p",
 457 |                  "-c:a", "copy",
 458 |                  "-movflags", "+faststart",
 459 |                  tmp],
 460 |                 capture_output=True, text=True, timeout=600,
 461 |             )
 462 |             if r.returncode == 0 and os.path.exists(tmp):
 463 |                 os.replace(tmp, video_path)
 464 |                 logger.info("[PREFLIGHT FIX] Freeze frame noise fix complete")
 465 |             elif os.path.exists(tmp):
 466 |                 os.remove(tmp)
 467 |         except Exception as e:
 468 |             logger.warning(f"[PREFLIGHT FIX] Freeze frame fix failed: {e}")
 469 |             if os.path.exists(tmp):
 470 |                 os.remove(tmp)
 471 | 
 472 |     # ── Silence gap fix ───────────────────────────────────────────────────
 473 |     if "silence_gaps" in issues_str:
 474 |         logger.info("[PREFLIGHT FIX] Filling silence gaps with fade bridge")
 475 |         tmp = video_path + ".silence_fix.mp4"
 476 |         try:
 477 |             r = subprocess.run(
 478 |                 ["ffmpeg", "-y", "-i", video_path,
 479 |                  "-c:v", "copy",
 480 |                  "-af", "silenceremove=stop_periods=-1:stop_duration=0.8:stop_threshold=-50dB,"
 481 |                         "apad=pad_dur=0.05",
 482 |                  "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
 483 |                  "-movflags", "+faststart",
 484 |                  tmp],
 485 |                 capture_output=True, text=True, timeout=300,
 486 |             )
 487 |             if r.returncode == 0 and os.path.exists(tmp):
 488 |                 os.replace(tmp, video_path)
 489 |                 logger.info("[PREFLIGHT FIX] Silence gap fix complete")
 490 |             elif os.path.exists(tmp):
 491 |                 os.remove(tmp)
 492 |         except Exception as e:
 493 |             logger.warning(f"[PREFLIGHT FIX] Silence fix failed: {e}")
 494 |             if os.path.exists(tmp):
 495 |                 os.remove(tmp)
 496 | 
 497 |     # ── Loudness fix ──────────────────────────────────────────────────────
 498 |     if "lufs=" in issues_str or "true_peak=" in issues_str:
 499 |         logger.info("[PREFLIGHT FIX] Applying loudnorm to fix loudness")
 500 |         tmp = video_path + ".loudnorm_fix.mp4"
 501 |         try:
 502 |             r = subprocess.run(
 503 |                 ["ffmpeg", "-y", "-i", video_path,
 504 |                  "-c:v", "copy",
 505 |                  "-af", "loudnorm=I=-14:TP=-2.0:LRA=7:linear=true",
 506 |                  "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
 507 |                  "-movflags", "+faststart",
 508 |                  tmp],
 509 |                 capture_output=True, text=True, timeout=300,
 510 |             )
 511 |             if r.returncode == 0 and os.path.exists(tmp):
 512 |                 os.replace(tmp, video_path)
 513 |                 logger.info("[PREFLIGHT FIX] Loudnorm fix complete")
 514 |             elif os.path.exists(tmp):
 515 |                 os.remove(tmp)
 516 |         except Exception as e:
 517 |             logger.warning(f"[PREFLIGHT FIX] Loudnorm fix failed: {e}")
 518 |             if os.path.exists(tmp):
 519 |                 os.remove(tmp)
 520 | 
 521 | 
 522 | def run_pipeline(test_mode: bool = False, skip_scan: bool = False,
 523 |                  fast_test: bool = False, reuse_content: bool = False) -> bool:
 524 |     # Fast test implies test + skip-scan
 525 |     if fast_test:
 526 |         test_mode = True
 527 |         skip_scan = True
 528 | 
 529 |     # P1 Fix 8: VRAM cleanup between renders
 530 |     try:
 531 |         import torch
 532 |         if torch.cuda.is_available():
 533 |             torch.cuda.empty_cache()
 534 |             torch.cuda.synchronize()
 535 |             logger.info("VRAM cleared")
 536 |     except Exception:
 537 |         pass
 538 | 
 539 |     # P0 Fix 3: Check checkpoint for resume
 540 |     resume_step = _read_checkpoint()
 541 |     if resume_step >= 4:
 542 |         logger.info(f"CHECKPOINT RESUME: last completed step={resume_step}, checking for resumable state")
 543 |         # Verify clips still exist before resuming
 544 |         today_dir = os.path.join(BASE, "output", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
 545 |         clips_dir = os.path.join(today_dir, "clips")
 546 |         if os.path.exists(clips_dir) and os.listdir(clips_dir):
 547 |             skip_scan = True
 548 |             logger.info(f"  Clips exist at {clips_dir} — will resume from step {resume_step + 1}")
 549 |         else:
 550 |             logger.info("  No clips found — starting fresh")
 551 |             resume_step = 0
 552 |     else:
 553 |         resume_step = 0
 554 | 
 555 |     # Wipe TTS cache before each run to prevent stale audio
 556 |     # CONTENT LOCK LAW: skip wipe when reusing locked content
 557 |     tts_cache = os.path.join(BASE, "tts_cache")
 558 |     if not reuse_content:
 559 |         shutil.rmtree(tts_cache, ignore_errors=True)
 560 |         os.makedirs(tts_cache, exist_ok=True)
 561 |         logger.info("TTS cache wiped")
 562 |     else:
 563 |         os.makedirs(tts_cache, exist_ok=True)
 564 |         logger.info("TTS cache preserved (reuse-content mode)")
 565 | 
 566 |     ts = datetime.now(timezone.utc)
 567 |     date_str = ts.strftime("%Y%m%d")
 568 |     time_str = ts.strftime("%Y%m%d_%H%M%S")
 569 | 
 570 |     if test_mode:
 571 |         run_dir = os.path.join(BASE, "output", f"test_{time_str}")
 572 |     else:
 573 |         run_dir = os.path.join(BASE, "output", ts.strftime("%Y-%m-%d"))
 574 | 
 575 |     os.makedirs(run_dir, exist_ok=True)
 576 |     final_video = os.path.join(run_dir, f"pulse_check_{date_str}.mp4")
 577 |     timing = {}
 578 |     t_pipeline_start = time.time()
 579 | 
 580 |     # Ensure music directory exists
 581 |     ensure_music_dir()
 582 | 
 583 |     # Log feature flags at startup
 584 |     flags = load_flags()
 585 |     logger.info(f"Feature flags: {json.dumps(flags)}")
 586 | 
 587 |     # Telegram alert at pipeline start
 588 |     if is_enabled("telegram_alerts"):
 589 |         alert_pipeline_start(date_str, test_mode)
 590 | 
 591 |     print("\n" + "=" * 70)
 592 |     print(f"  PULSE CHECK V5 — CLIP-FIRST PIPELINE")
 593 |     mode_label = "FAST TEST " if fast_test else ("TEST " if test_mode else "")
 594 |     print(f"  {mode_label}Run {time_str}")
 595 |     print(f"  Output: {run_dir}")
 596 |     print(f"  Music: {'YES' if has_music() else 'no (skipped gracefully)'}")
 597 |     print("=" * 70)
 598 | 
 599 | 
 600 |     # ── CONTENT LOCK: reuse locked content from previous iteration ────────
 601 |     if reuse_content:
 602 |         locked_dir = os.path.join(run_dir, "locked_content")
 603 |         locked_script = os.path.join(locked_dir, "script.json")
 604 |         locked_clips = os.path.join(locked_dir, "clips")
 605 |         locked_tts = os.path.join(locked_dir, "tts")
 606 |         locked_audio = os.path.join(locked_dir, "audio_data.json")
 607 |         locked_meta = os.path.join(locked_dir, "meta.json")
 608 | 
 609 |         if not os.path.exists(locked_script):
 610 |             logger.error(f"REUSE MODE FAILED: no locked content at {locked_dir}")
 611 |             print(f"  [FAIL] No locked content found at {locked_dir}")
 612 |             return False
 613 | 
 614 |         logger.info(f"REUSE MODE: skipping content fetch, using locked content from {locked_dir}")
 615 |         print(f"\n  *** CONTENT LOCK ACTIVE — reusing locked content from {locked_dir} ***")
 616 |         print("  Skipping Steps 1-6 (fetch/script/TTS)")
 617 | 
 618 |         with open(locked_script) as f:
 619 |             script = json.load(f)
 620 |         with open(locked_audio) as f:
 621 |             audio_data = json.load(f)
 622 | 
 623 |         # Load metadata (btc_price, music paths)
 624 |         meta = {}
 625 |         if os.path.exists(locked_meta):
 626 |             with open(locked_meta) as f:
 627 |                 meta = json.load(f)
 628 |         btc_price = meta.get("btc_price", "$0")
 629 |         music_bed = meta.get("music_bed", "")
 630 |         intro_music = meta.get("intro_music", "")
 631 | 
 632 |         # Build extracted_clips dict from locked clips directory
 633 |         extracted_clips = {}
 634 |         if os.path.exists(locked_clips):
 635 |             import glob as _lc_glob
 636 |             for clip_file in sorted(_lc_glob.glob(os.path.join(locked_clips, "*.mp4"))):
 637 |                 fname = os.path.basename(clip_file)
 638 |                 try:
 639 |                     rank = int(fname.split("_")[1])
 640 |                 except (IndexError, ValueError):
 641 |                     rank = len(extracted_clips) + 1
 642 |                 extracted_clips[rank] = {
 643 |                     "path": clip_file,
 644 |                     "video_id": fname,
 645 |                     "channel": "",
 646 |                     "duration": 0,
 647 |                 }
 648 | 
 649 |         # Restore TTS cache from locked copy
 650 |         if os.path.exists(locked_tts):
 651 |             for tts_file in os.listdir(locked_tts):
 652 |                 src = os.path.join(locked_tts, tts_file)
 653 |                 dst = os.path.join(tts_cache, tts_file)
 654 |                 if not os.path.exists(dst):
 655 |                     shutil.copy2(src, dst)
 656 | 
 657 |         dialogue = script.get("dialogue", [])
 658 |         print(f"  Loaded: script ({len(dialogue)} dialogue entries), "
 659 |               f"{len(extracted_clips)} clips, BTC={btc_price}")
 660 | 
 661 |     # ── Steps 1-6: Content generation (skipped in reuse mode) ─────────────
 662 |     if not reuse_content:
 663 |         # ── Step 1: BTC PRICE ─────────────────────────────────────────────────
 664 |         print("\n[STEP 1/12] FETCHING BTC PRICE...")
 665 |         t0 = time.time()
 666 |         btc_price = get_btc_price()
 667 |         print(f"  BTC: {btc_price}")
 668 |         timing["1_price"] = round(time.time() - t0, 2)
 669 |         write_render_context(1, "ok", btc_price=btc_price)
 670 | 
 671 |         # ── Step 2: SCAN CHANNELS ─────────────────────────────────────────────
 672 |         print("\n[STEP 2/12] SCANNING PARTNER CHANNELS...")
 673 |         t0 = time.time()
 674 |         if skip_scan:
 675 |             # Load cached transcripts from transcript dir
 676 |             import glob
 677 |             transcript_dir = os.path.join(BASE, "transcripts")
 678 |             videos = []
 679 |             for tf in sorted(glob.glob(os.path.join(transcript_dir, "*.json")))[:60]:
 680 |                 with open(tf) as f:
 681 |                     data = json.load(f)
 682 |                     videos.append({
 683 |                         "video_id": data.get("video_id", ""),
 684 |                         "title": data.get("title", ""),
 685 |                         "channel": data.get("channel", ""),
 686 |                         "duration": data.get("duration", 0),
 687 |                         "upload_date": "",
 688 |                         "url": f"https://www.youtube.com/watch?v={data.get('video_id', '')}",
 689 |                         "transcript_text": data.get("text", ""),
 690 |                         "timestamped_text": data.get("timestamped_text", ""),
 691 |                     })
 692 |             print(f"  Loaded {len(videos)} cached transcripts")
 693 |         else:
 694 |             whisper_model = "tiny" if test_mode else "base"
 695 |             videos = scan_all_channels(model_size=whisper_model)
 696 |             print(f"  Scanned: {len(videos)} videos with transcripts")
 697 |         timing["2_scan"] = round(time.time() - t0, 2)
 698 |         write_render_context(2, "ok")
 699 | 
 700 |         if not videos:
 701 |             print("\n  [FAIL] No videos found — cannot produce episode")
 702 |             _write_timing_report(run_dir, timing, t_pipeline_start, success=False)
 703 |             if is_enabled("telegram_alerts"):
 704 |                 alert_pipeline_failure(date_str, "scan", "No videos found")
 705 |             return False
 706 | 
 707 |         # ── Step 3: SELECT BEST CLIPS ─────────────────────────────────────────
 708 |         if fast_test:
 709 |             print("\n[STEP 3/12] SELECTING CLIPS (fast-test: first 2, no Claude)...")
 710 |             t0 = time.time()
 711 |             # Build minimal selections from cached videos without calling Claude
 712 |             fast_clips = []
 713 |             for i, v in enumerate(videos[:2], 1):
 714 |                 text = v.get("transcript_text", "")
 715 |                 fast_clips.append({
 716 |                     "rank": i,
 717 |                     "video_id": v["video_id"],
 718 |                     "channel": v.get("channel", ""),
 719 |                     "title": v.get("title", ""),
 720 |                     "quote": text[:100] if text else "No transcript",
 721 |                     "why": "fast-test auto-select",
 722 |                     "start_seconds": 60,
 723 |                     "end_seconds": 90,
 724 |                 })
 725 |             selections = {"clips": fast_clips}
 726 |             clips = fast_clips
 727 |             print(f"  Auto-selected: {len(clips)} clips (no API call)")
 728 |             timing["3_select"] = round(time.time() - t0, 2)
 729 |         else:
 730 |             print("\n[STEP 3/12] SELECTING BEST CLIPS (Claude)...")
 731 |             t0 = time.time()
 732 |             selections = select_clips(videos)
 733 |             clips = selections.get("clips", [])
 734 |             print(f"  Selected: {len(clips)} clips")
 735 |             for c in clips:
 736 |                 print(f"    #{c['rank']}: [{c.get('channel','')}] {c.get('quote','')[:50]}...")
 737 |             timing["3_select"] = round(time.time() - t0, 2)
 738 | 
 739 |         if not clips:
 740 |             print("\n  [FAIL] No clips selected — cannot produce episode")
 741 |             _write_timing_report(run_dir, timing, t_pipeline_start, success=False)
 742 |             if is_enabled("telegram_alerts"):
 743 |                 alert_pipeline_failure(date_str, "select", "No clips selected")
 744 |             return False
 745 | 
 746 |         # In test mode, use only top 2 clips
 747 |         if not fast_test and test_mode and len(clips) > 2:
 748 |             selections["clips"] = clips[:2]
 749 |             clips = selections["clips"]
 750 |             print(f"  [test] Truncated to {len(clips)} clips")
 751 | 
 752 |         # Save selections
 753 |         sel_path = os.path.join(run_dir, "selections.json")
 754 |         with open(sel_path, "w") as f:
 755 |             json.dump(selections, f, indent=2)
 756 | 
 757 |         # ── Step 3b: Select independent montage clips (Qwen, free) ──────────
 758 |         print("\n[STEP 3b] SELECTING MONTAGE CLIPS (local Qwen)...")
 759 |         try:
 760 |             from clip_selector import select_montage_clips
 761 |             montage_selections = select_montage_clips(videos)
 762 |             montage_clips_sel = montage_selections.get("clips", [])
 763 |             montage_sel_path = os.path.join(run_dir, "montage_selections.json")
 764 |             with open(montage_sel_path, "w") as f:
 765 |                 json.dump(montage_selections, f, indent=2)
 766 |             print(f"  Montage: {len(montage_clips_sel)} independent clips selected")
 767 |         except Exception as e:
 768 |             print(f"  Montage selection failed ({e}) — montage will reuse Pulse Check clips")
 769 |             montage_selections = None
 770 | 
 771 |         # ── Step 4: EXTRACT CLIPS ─────────────────────────────────────────────
 772 |         print("\n[STEP 4/12] EXTRACTING CLIPS (yt-dlp with original audio)...")
 773 |         t0 = time.time()
 774 |         # FIX 2: Wipe clips/ dir completely to prevent stale files from prior renders
 775 |         clip_dir = os.path.join(run_dir, "clips")
 776 |         if os.path.exists(clip_dir):
 777 |             shutil.rmtree(clip_dir)
 778 |             logger.info(f"  Wiped stale clips dir: {clip_dir}")
 779 |         os.makedirs(clip_dir, exist_ok=True)
 780 |         # Also wipe stale pip_preview files from work dir
 781 |         work_dir = os.path.join(run_dir, "work")
 782 |         if os.path.exists(work_dir):
 783 |             import glob as _pip_glob
 784 |             for stale_pip in _pip_glob.glob(os.path.join(work_dir, "pip_preview_*.mp4")):
 785 |                 try:
 786 |                     os.remove(stale_pip)
 787 |                 except OSError:
 788 |                     pass
 789 |             logger.info("  Wiped stale pip_preview files from work/")
 790 |         extracted_clips = extract_all(selections, clip_dir)
 791 |         print(f"  Extracted: {len(extracted_clips)}/{len(clips)} clips")
 792 | 
 793 |         # ── Quality-aware fallback: retry with ranked alternates ──────────
 794 |         if not test_mode and not fast_test and len(extracted_clips) < 5:
 795 |             used_video_ids = {info["video_id"] for info in extracted_clips.values()}
 796 |             used_channels = {info["channel"] for info in extracted_clips.values()}
 797 |             tried_video_ids = {c["video_id"] for c in clips} | used_video_ids
 798 | 
 799 |             remaining = [v for v in videos
 800 |                          if v["video_id"] not in tried_video_ids
 801 |                          and v.get("channel", "") not in used_channels]
 802 | 
 803 |             if remaining:
 804 |                 need = 5 - len(extracted_clips)
 805 |                 logger.info(
 806 |                     f"[extractor] Only {len(extracted_clips)}/5 clips passed quality "
 807 |                     f"— selecting fallbacks from {len(remaining)} candidates (need {need})"
 808 |                 )
 809 |                 fallback_sel = select_clips(remaining)
 810 |                 fallback_clips = fallback_sel.get("clips", [])
 811 | 
 812 |                 max_rank = max(extracted_clips.keys()) if extracted_clips else 0
 813 |                 for fc in fallback_clips:
 814 |                     if len(extracted_clips) >= 5:
 815 |                         break
 816 |                     fc_ch = fc.get("channel", "")
 817 |                     fc_vid = fc.get("video_id", "")
 818 |                     if fc_ch in used_channels or fc_vid in tried_video_ids:
 819 |                         continue
 820 |                     max_rank += 1
 821 |                     fc["rank"] = max_rank
 822 |                     logger.info(
 823 |                         f"[extractor] Clip failed quality — trying fallback candidate "
 824 |                         f"#{max_rank} [{fc_ch}] from selections"
 825 |                     )
 826 |                     fb_result = extract_all({"clips": [fc]}, clip_dir)
 827 |                     if fb_result:
 828 |                         for r, info in fb_result.items():
 829 |                             extracted_clips[r] = info
 830 |                             used_video_ids.add(info["video_id"])
 831 |                             used_channels.add(info["channel"])
 832 |                             tried_video_ids.add(fc_vid)
 833 |                             selections["clips"].append(fc)
 834 |                             logger.info(
 835 |                                 f"[extractor] Fallback clip #{r} passed quality — "
 836 |                                 f"{info['channel']} ({info['duration']:.1f}s)"
 837 |                             )
 838 |                     else:
 839 |                         tried_video_ids.add(fc_vid)
 840 |                         logger.warning(
 841 |                             f"[extractor] Fallback [{fc_ch}] also failed quality — trying next"
 842 |                         )
 843 | 
 844 |                 # Update clips list and re-save selections
 845 |                 clips = selections.get("clips", [])
 846 |                 with open(sel_path, "w") as f:
 847 |                     json.dump(selections, f, indent=2)
 848 |                 logger.info(f"[extractor] After fallback: {len(extracted_clips)}/5 clips")
 849 |             else:
 850 |                 logger.warning("[extractor] No fallback candidates — all channels/videos exhausted")
 851 | 
 852 |         if not test_mode:
 853 |             _unique_ch = len({info.get("channel", f"unk_{i}") for i, info in enumerate(extracted_clips.values())})
 854 |             if len(extracted_clips) < 3 or _unique_ch < 2:
 855 |                 logger.critical(
 856 |                     f"[PIPELINE] HARD FAIL: Need 5 clips from 5 unique channels, "
 857 |                     f"got {len(extracted_clips)} clips from {_unique_ch} channels."
 858 |                 )
 859 |                 return False
 860 |         for rank, info in sorted(extracted_clips.items()):
 861 |             print(f"    #{rank}: {info['channel']} — {info['duration']:.1f}s")
 862 |         timing["4_extract"] = round(time.time() - t0, 2)
 863 | 
 864 |         # ── Step 4m: Extract montage clips ───────────────────────────────────
 865 |         if montage_selections and montage_selections.get("clips"):
 866 |             print("\n[STEP 4m] EXTRACTING MONTAGE CLIPS...")
 867 |             try:
 868 |                 extract_montage_all(montage_selections, clip_dir)
 869 |                 print(f"  Montage clips extracted to {clip_dir}")
 870 |             except Exception as e:
 871 |                 print(f"  Montage extraction failed ({e}) — skipping")
 872 | 
 873 |         if not extracted_clips:
 874 |             print("\n  [FAIL] No clips extracted — cannot produce episode")
 875 |             _write_timing_report(run_dir, timing, t_pipeline_start, success=False)
 876 |             if is_enabled("telegram_alerts"):
 877 |                 alert_pipeline_failure(date_str, "extract", "No clips extracted")
 878 |             return False
 879 | 
 880 |         # ── Step 4b: MOOD CLASSIFICATION + MUSIC SELECTION ──────────────────
 881 |         import glob as _glob
 882 |         import random as _random
 883 | 
 884 |         def classify_episode_mood(script_text: str) -> str:
 885 |             """Classify episode mood from clip quotes."""
 886 |             moods = {"tense": 0, "confident": 0, "contemplative": 0, "upbeat": 0, "edge": 0}
 887 |             lower = script_text.lower()
 888 |             if any(w in lower for w in ["crash", "sell", "breaking", "emergency", "plunge", "war"]):
 889 |                 moods["tense"] += 3
 890 |             if any(w in lower for w in ["bullish", "ath", "record", "buying", "accumul"]):
 891 |                 moods["confident"] += 3
 892 |             if any(w in lower for w in ["philosoph", "long-term", "decade", "future", "think about"]):
 893 |                 moods["contemplative"] += 2
 894 |             if any(w in lower for w in ["community", "fun", "meme", "laugh", "celebrate"]):
 895 |                 moods["upbeat"] += 2
 896 |             if any(w in lower for w in ["controversial", "scam", "fraud", "attack", "fight"]):
 897 |                 moods["edge"] += 2
 898 |             best = max(moods, key=moods.get)
 899 |             return best if moods[best] > 0 else "confident"
 900 | 
 901 |         def select_music_bed(mood: str, music_dir: str) -> str:
 902 |             # Sprint 1.10: Randomize music, avoid repeating last track
 903 |             last_track_file = os.path.join(music_dir, ".last_track.txt")
 904 |             last_track = ""
 905 |             if os.path.exists(last_track_file):
 906 |                 try:
 907 |                     last_track = open(last_track_file).read().strip()
 908 |                 except Exception:
 909 |                     pass
 910 | 
 911 |             tracks = _glob.glob(os.path.join(music_dir, f"{mood}_*.mp3"))
 912 |             if not tracks:
 913 |                 tracks = _glob.glob(os.path.join(music_dir, "confident_*.mp3"))
 914 |             if not tracks:
 915 |                 # Get all tracks except reserved ones
 916 |                 all_tracks = _glob.glob(os.path.join(music_dir, "*.mp3"))
 917 |                 tracks = [t for t in all_tracks
 918 |                           if os.path.basename(t) not in ("pp_outro.mp3", "pp_background.mp3",
 919 |                                                            "pp_intro.mp3", "pp_transition.mp3")]
 920 |             if not tracks:
 921 |                 return ""
 922 | 
 923 |             # Avoid repeating last track
 924 |             if last_track and len(tracks) > 1:
 925 |                 tracks = [t for t in tracks if os.path.basename(t) != last_track] or tracks
 926 | 
 927 |             chosen = _random.choice(tracks)
 928 |             try:
 929 |                 with open(last_track_file, "w") as f:
 930 |                     f.write(os.path.basename(chosen))
 931 |             except Exception:
 932 |                 pass
 933 |             return chosen
 934 | 
 935 |         def select_intro_music(music_dir: str) -> str:
 936 |             tracks = _glob.glob(os.path.join(music_dir, "intro_*.mp3"))
 937 |             return _random.choice(tracks) if tracks else ""
 938 | 
 939 |         # Classify mood from clip quotes
 940 |         clip_quotes = " ".join(c.get("quote", "") + " " + c.get("why", "") for c in clips)
 941 |         episode_mood = classify_episode_mood(clip_quotes)
 942 |         music_dir = os.path.join(BASE, "assets", "music")
 943 |         music_bed = select_music_bed(episode_mood, music_dir)
 944 |         intro_music = select_intro_music(music_dir)
 945 |         print(f"  Mood: {episode_mood} | Music: {os.path.basename(music_bed) if music_bed else 'default'}")
 946 | 
 947 |         # ── Step 4c: LIVE SIGNALS ─────────────────────────────────────────────
 948 |         live_context = ""
 949 |         live_signals_path = os.path.join(BASE, "data", "intelligence", "live_signals.json")
 950 |         try:
 951 |             if os.path.exists(live_signals_path):
 952 |                 with open(live_signals_path) as f:
 953 |                     live_data = json.load(f)
 954 |                 from datetime import timezone as _tz
 955 |                 now = datetime.now(_tz.utc) if hasattr(datetime, 'now') else datetime.utcnow()
 956 |                 active_streams = []
 957 |                 for s in live_data.get("live_streams", []):
 958 |                     # Only include streams from last 6 hours
 959 |                     started = s.get("started_at", "")
 960 |                     try:
 961 |                         started_dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
 962 |                         age_hours = (now - started_dt).total_seconds() / 3600
 963 |                         if age_hours > 6:
 964 |                             continue
 965 |                     except (ValueError, AttributeError):
 966 |                         continue
 967 |                     source = s.get("source", "youtube_live")
 968 |                     channel = s.get("channel", "unknown")
 969 |                     title = s.get("title", "")
 970 |                     topics = ", ".join(s.get("topics", []))
 971 |                     sentiment = s.get("current_sentiment", 50)
 972 |                     sentiment_label = "bullish" if sentiment > 60 else "bearish" if sentiment < 40 else "neutral"
 973 |                     active_streams.append(
 974 |                         f"- {channel} ({source}): \"{title}\" — topics: {topics}, sentiment: {sentiment_label} ({sentiment})"
 975 |                     )
 976 |                 if active_streams:
 977 |                     live_context = "\n".join(active_streams)
 978 |                     print(f"  Live signals: {len(active_streams)} active streams in last 6 hours")
 979 |                     for line in active_streams:
 980 |                         print(f"    {line}")
 981 |                 else:
 982 |                     print("  Live signals: no active streams in last 6 hours")
 983 |         except Exception as e:
 984 |             logger.warning(f"Live signals read failed: {e}")
 985 | 
 986 |         # ── Step 5a: Fetch social posts + Space Tap BEFORE script generation ──
 987 |         # Social posts: fetch once, sort by likes desc, pass to script_writer
 988 |         sorted_social = []
 989 |         try:
 990 |             from utils.social_fetcher import get_todays_social_posts
 991 |             sorted_social = get_todays_social_posts(max_posts=5)
 992 |             if sorted_social:
 993 |                 sorted_social.sort(key=lambda p: p.get("likes", 0), reverse=True)
 994 |                 for si, sp in enumerate(sorted_social):
 995 |                     logger.info(f"SOCIAL ORDER: #{si}: @{sp.get('handle', '?')} — {sp.get('text', '')[:40]}")
 996 |         except Exception as e:
 997 |             logger.warning(f"Social posts fetch failed: {e}")
 998 | 
 999 |         # Space Tap: fetch X Spaces clips BEFORE script generation so LLM can write dialogue
1000 |         print("[STEP 5a] SPACE TAP -- LIVE X SPACES INTERCEPT...")
1001 |         try:
1002 |             import importlib.util
1003 |             _spaces_scraper_path = os.path.join(
1004 |                 os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
1005 |                 "x_spaces_scraper", "scraper.py"
1006 |             )
1007 |             if os.path.exists(_spaces_scraper_path):
1008 |                 _spec = importlib.util.spec_from_file_location("x_spaces_scraper", _spaces_scraper_path)
1009 |                 _mod = importlib.util.module_from_spec(_spec)
1010 |                 _spec.loader.exec_module(_mod)
1011 |                 # Hard 120s timeout — Whisper can hang forever without this
1012 |                 import threading as _st_thread
1013 |                 _st_result = [None]
1014 |                 def _fetch_spaces(): _st_result[0] = _mod.get_best_space_clips(max_clips=3)
1015 |                 _st_t = _st_thread.Thread(target=_fetch_spaces, daemon=True)
1016 |                 _st_t.start(); _st_t.join(timeout=120)
1017 |                 if _st_t.is_alive():
1018 |                     logger.warning("[SpaceTap] get_best_space_clips timed out (120s) — skipping")
1019 |                     _st = None
1020 |                 else:
1021 |                     _st = _st_result[0]
1022 |                 if _st and _st.get("clips"):
1023 |                     selections["space_tap_clips"] = _st["clips"]
1024 |                     print(f"  Space Tap: {len(_st['clips'])} clips from {_st.get('spaces_count', 0)} spaces")
1025 |                 else:
1026 |                     print("  Space Tap: no live spaces — segment skipped")
1027 |             else:
1028 |                 print("  Space Tap: scraper not installed — segment skipped")
1029 |         except Exception as _ste:
1030 |             logger.error(f"Space Tap fetch error: {type(_ste).__name__}: {_ste}")
1031 |             print(f"  Space Tap: skipped ({_ste})")
1032 | 
1033 |         # ── Step 5: GENERATE SCRIPT ───────────────────────────────────────────
1034 |         if fast_test:
1035 |             print("\n[STEP 5/12] GENERATING SCRIPT (fast-test: hardcoded, no Claude)...")
1036 |             t0 = time.time()
1037 |             script = _build_fast_test_script(extracted_clips, btc_price)
1038 |             timing["5_script"] = round(time.time() - t0, 2)
1039 |         else:
1040 |             print("\n[STEP 5/12] GENERATING HOST DIALOGUE (Claude)...")
1041 |             t0 = time.time()
1042 |             script = generate_from_clips(selections, btc_price=btc_price,
1043 |                                          live_context=live_context,
1044 |                                          social_posts_sorted=sorted_social)
1045 |             timing["5_script"] = round(time.time() - t0, 2)
1046 | 
1047 |         # Attach social posts to script for assembler (single source of truth)
1048 |         if sorted_social:
1049 |             script["social_posts"] = sorted_social
1050 | 
1051 |         # Re-read dialogue AFTER all mutations (Space Tap entries may be in script)
1052 |         dialogue = script.get("dialogue", [])
1053 |         speech_lines = [d for d in dialogue if d.get("host") in (1, 2, "1", "2")]
1054 |         clip_markers = [d for d in dialogue if d.get("host") in ("CLIP", "SPACE_CLIP")]
1055 |         social_seg_count = sum(1 for d in dialogue if d.get("type") == "social_segment")
1056 |         space_tap_count = sum(1 for d in dialogue if d.get("host") == "SPACE_CLIP"
1057 |                              or (d.get("type") or "").startswith("space_tap"))
1058 |         print(f"  Title: {script.get('episode_title', 'Untitled')}")
1059 |         print(f"  Dialogue: {len(speech_lines)} speech + {len(clip_markers)} clips")
1060 |         print(f"  SOCIAL segments: {social_seg_count} (input tweets: {len(sorted_social)})")
1061 |         print(f"  SPACE TAP entries: {space_tap_count} (input clips: {len(selections.get('space_tap_clips', []))})")
1062 |         if sorted_social and social_seg_count == 0:
1063 |             logger.error("SOCIAL SEGMENT ABSENT despite having tweet data — check script_writer enforcement")
1064 |         if selections.get("space_tap_clips") and space_tap_count == 0:
1065 |             logger.error("SPACE TAP ABSENT despite having clip data — check script_writer enforcement")
1066 | 
1067 |         # Save script
1068 |         script_path = os.path.join(run_dir, "script.json")
1069 |         with open(script_path, "w") as f:
1070 |             json.dump(script, f, indent=2)
1071 | 
1072 |         write_render_context(5, "ok",
1073 |                              episode_title=script.get("episode_title", ""),
1074 |                              social_posts_count=len(sorted_social),
1075 |                              space_tap_available=bool(selections.get("space_tap_clips")))
1076 | 
1077 |         # ── Step 6: TTS ───────────────────────────────────────────────────────
1078 |         print("\n[STEP 6/12] GENERATING PBX NARRATION AUDIO (ElevenLabs)...")
1079 |         t0 = time.time()
1080 |         audio_dir = os.path.join(run_dir, "audio")
1081 |         audio_data = generate_dialogue_audio(dialogue, audio_dir)
1082 |         successful = sum(1 for l in audio_data.get("lines", [])
1083 |                          if l.get("path") and os.path.exists(l.get("path", "")))
1084 |         print(f"  Audio: {successful}/{len(speech_lines)} lines")
1085 |         print(f"  Duration: {audio_data.get('total_duration', 0):.1f}s")
1086 |         timing["6_tts"] = round(time.time() - t0, 2)
1087 |         write_render_context(6, "ok", tts_provider="elevenlabs")
1088 | 
1089 |         # ── Step 6b: BUILD MANIFEST ─────────────────────────────────────────
1090 |         print("\n[STEP 6b/12] BUILDING EPISODE MANIFEST...")
1091 |         t0 = time.time()
1092 |         try:
1093 |             from manifest_builder import build_manifest
1094 |             episode_manifest = build_manifest(
1095 |                 script, audio_data, extracted_clips, run_dir,
1096 |                 music_bed=music_bed, btc_price=btc_price,
1097 |             )
1098 |             print(f"  Manifest: {episode_manifest.get('total_segments', 0)} segments, "
1099 |                   f"~{episode_manifest.get('total_duration_estimate', 0):.0f}s estimated")
1100 |         except Exception as e:
1101 |             logger.warning(f"Manifest build failed (non-blocking): {e}")
1102 |             episode_manifest = {}
1103 |         timing["6b_manifest"] = round(time.time() - t0, 2)
1104 | 
1105 |         # ── Step 6c: PREFLIGHT CHECK ─────────────────────────────────────────
1106 |         manifest_json_path = os.path.join(run_dir, "episode_manifest.json")
1107 |         if os.path.exists(manifest_json_path):
1108 |             print("\n[STEP 6c/12] PREFLIGHT QC CHECK...")
1109 |             t0 = time.time()
1110 |             try:
1111 |                 from qc_pipeline import preflight_check
1112 |                 pf_passed, pf_errors, pf_warnings = preflight_check(manifest_json_path)
1113 |                 print(f"  Preflight: {'PASS' if pf_passed else 'FAIL'} — "
1114 |                       f"{len(pf_errors)} errors, {len(pf_warnings)} warnings")
1115 |             except Exception as e:
1116 |                 logger.warning(f"Preflight check failed (non-blocking): {e}")
1117 |             timing["6c_preflight"] = round(time.time() - t0, 2)
1118 | 
1119 | 
1120 |         # ── CONTENT LOCK: save content for future iterations ──────────────
1121 |         locked_dir = os.path.join(run_dir, "locked_content")
1122 |         os.makedirs(locked_dir, exist_ok=True)
1123 |         script_lock_src = os.path.join(run_dir, "script.json")
1124 |         if os.path.exists(script_lock_src):
1125 |             shutil.copy2(script_lock_src, os.path.join(locked_dir, "script.json"))
1126 |         clip_dir = os.path.join(run_dir, "clips")
1127 |         if os.path.exists(clip_dir):
1128 |             shutil.copytree(clip_dir, os.path.join(locked_dir, "clips"), dirs_exist_ok=True)
1129 |         if os.path.exists(tts_cache) and os.listdir(tts_cache):
1130 |             shutil.copytree(tts_cache, os.path.join(locked_dir, "tts"), dirs_exist_ok=True)
1131 |         # Save audio_data for reuse
1132 |         with open(os.path.join(locked_dir, "audio_data.json"), "w") as f:
1133 |             json.dump(audio_data, f, indent=2)
1134 |         # Save metadata
1135 |         with open(os.path.join(locked_dir, "meta.json"), "w") as f:
1136 |             json.dump({"btc_price": btc_price, "music_bed": music_bed,
1137 |                         "intro_music": intro_music}, f, indent=2)
1138 |         logger.info(f"CONTENT LOCKED to {locked_dir} — subsequent iterations will reuse this")
1139 | 
1140 |     # ── Step 7: ASSEMBLE ──────────────────────────────────────────────────
1141 |     print("\n[STEP 7/12] ASSEMBLING VIDEO...")
1142 |     t0 = time.time()
1143 |     result = assemble_episode(script, audio_data, extracted_clips, final_video,
1144 |                               btc_price=btc_price, music_bed=music_bed,
1145 |                               intro_music=intro_music)
1146 |     timing["7_assemble"] = round(time.time() - t0, 2)
1147 | 
1148 |     if not result or not os.path.exists(final_video):
1149 |         print("\n  [FAIL] Assembly failed")
1150 |         write_render_context(7, "fail", error="Video assembly failed or no output file")
1151 |         _write_timing_report(run_dir, timing, t_pipeline_start, success=False)
1152 |         if is_enabled("telegram_alerts"):
1153 |             alert_pipeline_failure(date_str, "assemble", "Video assembly failed")
1154 |         return False
1155 |     write_render_context(7, "ok")
1156 | 
1157 |     # ── Step 7b: PRE-FLIGHT QC (Grade A Guarantee) ───────────────────────
1158 |     print("\n[STEP 7b] PRE-FLIGHT QC...")
1159 |     t0 = time.time()
1160 |     for pf_attempt in range(1, MAX_PREFLIGHT_ATTEMPTS + 1):
1161 |         logger.info(f"[PREFLIGHT] Attempt {pf_attempt}/{MAX_PREFLIGHT_ATTEMPTS}")
1162 |         print(f"  Preflight attempt {pf_attempt}/{MAX_PREFLIGHT_ATTEMPTS}")
1163 |         qc = run_preflight_qc(final_video)
1164 | 
1165 |         if qc["passed"]:
1166 |             print("  [PREFLIGHT] PASSED — proceeding to grading")
1167 |             logger.info("[PREFLIGHT] PASSED — sending to grading")
1168 |             break
1169 | 
1170 |         logger.warning(f"[PREFLIGHT] FAILED: {qc['issues']}")
1171 |         print(f"  [PREFLIGHT] FAILED: {qc['issues']}")
1172 |         write_render_context("7b", "fail", error=str(qc["issues"]))
1173 | 
1174 |         if pf_attempt == MAX_PREFLIGHT_ATTEMPTS:
1175 |             logger.error("[PREFLIGHT] Max attempts reached — sending anyway")
1176 |             print("  [PREFLIGHT] Max attempts — sending to grading anyway")
1177 |             if is_enabled("telegram_alerts"):
1178 |                 from utils.telegram_alerts import send_alert
1179 |                 send_alert(
1180 |                     f"PREFLIGHT: {qc['issues']} — sending to grading anyway",
1181 |                     level="warning",
1182 |                 )
1183 |             break
1184 | 
1185 |         # Apply targeted fixes
1186 |         _apply_preflight_fixes(final_video, qc)
1187 | 
1188 |     timing["7b_preflight_qc"] = round(time.time() - t0, 2)
1189 |     write_render_context("7b", "ok" if qc["passed"] else "warn")
1190 | 
1191 |     # ── Step 8: SHORTS ────────────────────────────────────────────────────
1192 |     print("\n[STEP 8/12] GENERATING SHORTS (avatar)...")
1193 |     t0 = time.time()
1194 |     shorts_dir = os.path.join(run_dir, "shorts")
1195 |     shorts = generate_shorts(script, shorts_dir, btc_price=btc_price,
1196 |                              max_shorts=3 if not test_mode else 1)
1197 |     print(f"  Shorts: {len(shorts)}")
1198 |     timing["8_shorts"] = round(time.time() - t0, 2)
1199 | 
1200 |     # ── Step 9: THUMBNAIL ─────────────────────────────────────────────────
1201 |     print("\n[STEP 9/12] GENERATING THUMBNAIL (MMA Central style)...")
1202 |     t0 = time.time()
1203 |     thumb_data = script.get("thumbnail", {})
1204 |     top_quote = ""
1205 |     if clips:
1206 |         top_quote = clips[0].get("quote", "")
1207 |     thumb_path = os.path.join(run_dir, "thumbnail.png")
1208 |     generate_thumbnail(
1209 |         thumb_data.get("headline", script.get("episode_title", "PULSE CHECK")),
1210 |         thumb_data.get("subtext", ""),
1211 |         thumb_path,
1212 |         btc_price=btc_price,
1213 |         top_quote=top_quote,
1214 |     )
1215 |     timing["9_thumbnail"] = round(time.time() - t0, 2)
1216 | 
1217 |     # ── Step 10: CHAPTERS ─────────────────────────────────────────────────
1218 |     print("\n[STEP 10/12] GENERATING CHAPTERS...")
1219 |     t0 = time.time()
1220 |     chapters_path = os.path.join(run_dir, "chapters.txt")
1221 |     generate_chapters(script, audio_data, chapters_path)
1222 |     timing["10_chapters"] = round(time.time() - t0, 2)
1223 | 
1224 |     # ── Step 11: PODCAST + NEWSLETTER ─────────────────────────────────────
1225 |     print("\n[STEP 11/12] PODCAST AUDIO + NEWSLETTER...")
1226 |     t0 = time.time()
1227 |     podcast_path = os.path.join(run_dir, "podcast.mp3")
1228 |     extract_podcast_audio(final_video, podcast_path)
1229 | 
1230 |     email_html = generate_email_html(
1231 |         script.get("episode_title", "Pulse Check"),
1232 |         segments_summary=script.get("segments_summary", []),
1233 |         btc_price=btc_price,
1234 |     )
1235 |     newsletter_path = os.path.join(run_dir, "newsletter.html")
1236 |     save_newsletter_html(email_html, newsletter_path)
1237 |     timing["11_podcast_newsletter"] = round(time.time() - t0, 2)
1238 | 
1239 |     # ── Step 12: VERIFY ───────────────────────────────────────────────────
1240 |     print("\n[STEP 12/12] VERIFYING OUTPUT...")
1241 |     t0 = time.time()
1242 |     passed = verify_video(final_video)
1243 | 
1244 |     # Final AV sync validation
1245 |     final_offset = check_av_sync(final_video)
1246 |     print(f"  Final AV sync offset: {final_offset:+.3f}s")
1247 |     if abs(final_offset) > 0.05:
1248 |         logger.error(f"FINAL OUTPUT SYNC FAILED: {final_offset:+.3f}s > 0.05s — nuclear re-encode")
1249 |         nuclear_tmp = final_video + ".nuclear.mp4"
1250 |         nuclear_cmd = subprocess.run([
1251 |             "ffmpeg", "-y",
1252 |             "-fflags", "+genpts+igndts",
1253 |             "-i", final_video,
1254 |             "-c:v", "libx264", "-preset", "medium",
1255 |             "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
1256 |             "-r", "30", "-vsync", "cfr",
1257 |             "-vf", "setpts=PTS-STARTPTS,format=yuv420p",
1258 |             "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
1259 |             "-af", "asetpts=PTS-STARTPTS,aresample=async=1",
1260 |             "-movflags", "+faststart",
1261 |             nuclear_tmp,
1262 |         ], capture_output=True, text=True, timeout=600)
1263 |         if nuclear_cmd.returncode == 0 and os.path.exists(nuclear_tmp):
1264 |             os.replace(nuclear_tmp, final_video)
1265 |             recheck = check_av_sync(final_video)
1266 |             print(f"  Nuclear re-encode done. New offset: {recheck:+.3f}s")
1267 |         elif os.path.exists(nuclear_tmp):
1268 |             os.remove(nuclear_tmp)
1269 | 
1270 |     # Final bitrate validation
1271 |     br_result = subprocess.run(
1272 |         ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", final_video],
1273 |         capture_output=True, text=True,
1274 |     )
1275 |     try:
1276 |         br_info = json.loads(br_result.stdout)
1277 |         bitrate = int(br_info.get("format", {}).get("bit_rate", 0))
1278 |         print(f"  Final bitrate: {bitrate / 1_000_000:.1f} Mbps")
1279 |         if bitrate < 3_000_000:
1280 |             logger.error(f"FINAL OUTPUT QUALITY FAILED: {bitrate / 1_000_000:.1f}Mbps < 3Mbps")
1281 |     except Exception:
1282 |         pass
1283 | 
1284 |     timing["12_verify"] = round(time.time() - t0, 2)
1285 |     write_render_context(12, "ok" if passed else "fail",
1286 |                          error="verify failed" if not passed else None)
1287 | 
1288 |     # ── Step 12b: POST-RENDER QC (blocking — P1 Fix 6) ─────────────────
1289 |     print("\n[STEP 12b] POST-RENDER QC...")
1290 |     t0 = time.time()
1291 |     qc_passed = True
1292 |     try:
1293 |         from qc_pipeline import post_render_qc, save_qc_report
1294 |         manifest_json_path = os.path.join(run_dir, "episode_manifest.json")
1295 |         qc_report = post_render_qc(final_video, manifest_json_path)
1296 |         save_qc_report(qc_report, run_dir)
1297 |         qc_passed = qc_report.get("passed", False)
1298 |         print(f"  QC: {'PASS' if qc_passed else 'FAIL'}")
1299 |         for check, val in qc_report.get("checks", {}).items():
1300 |             status = "PASS" if val else ("FAIL" if val is not None else "SKIP")
1301 |             print(f"    [{status}] {check}")
1302 |         if not qc_passed:
1303 |             logger.error("Post-render QC FAILED — render is not broadcast-ready")
1304 |             write_render_context("12b", "fail", error="Post-render QC failed")
1305 |     except Exception as e:
1306 |         logger.warning(f"Post-render QC exception: {e}")
1307 |         qc_passed = False
1308 |     timing["12b_qc"] = round(time.time() - t0, 2)
1309 | 
1310 |     # ── Summary ──────────────────────────────────────────────────────────
1311 |     timing["total"] = round(time.time() - t_pipeline_start, 2)
1312 | 
1313 |     # Video stats
1314 |     r = subprocess.run(
1315 |         ["ffprobe", "-v", "quiet", "-print_format", "json",
1316 |          "-show_format", "-show_streams", final_video],
1317 |         capture_output=True, text=True,
1318 |     )
1319 |     try:
1320 |         info = json.loads(r.stdout)
1321 |         fmt = info.get("format", {})
1322 |         streams = info.get("streams", [])
1323 |         vid = next((s for s in streams if s.get("codec_type") == "video"), {})
1324 |         aud = next((s for s in streams if s.get("codec_type") == "audio"), {})
1325 |         dur = float(fmt.get("duration", 0))
1326 |         sz = int(fmt.get("size", 0)) / 1024 / 1024
1327 |         timing["video_duration"] = round(dur, 1)
1328 |         timing["video_size_mb"] = round(sz, 1)
1329 |     except Exception:
1330 |         vid, aud, dur, sz = {}, {}, 0, 0
1331 | 
1332 |     print("\n" + "=" * 70)
1333 |     print(f"  PULSE CHECK V5 — {'SUCCESS' if passed else 'COMPLETE (warnings)'}")
1334 |     print(f"  Title:    {script.get('episode_title', 'Untitled')}")
1335 |     print(f"  Video:    {vid.get('width')}x{vid.get('height')} {vid.get('codec_name')} {dur:.1f}s")
1336 |     print(f"  Audio:    {aud.get('codec_name')} {aud.get('sample_rate')}Hz")
1337 |     print(f"  Size:     {sz:.1f}MB")
1338 |     print(f"  Clips:    {len(extracted_clips)} real YouTube clips with original audio")
1339 |     print(f"  Shorts:   {len(shorts)}")
1340 |     print(f"  Music:    {'layered' if has_music() else 'none (graceful skip)'}")
1341 | 
1342 |     outputs = {
1343 |         "video": final_video,
1344 |         "shorts": [s for s in shorts],
1345 |         "thumbnail": thumb_path,
1346 |         "chapters": chapters_path,
1347 |         "podcast": podcast_path,
1348 |         "newsletter": newsletter_path,
1349 |         "script": script_path,
1350 |         "selections": sel_path,
1351 |     }
1352 | 
1353 |     print(f"\n  OUTPUT FILES:")
1354 |     for name, path in outputs.items():
1355 |         if isinstance(path, list):
1356 |             for p in path:
1357 |                 exists = "Y" if os.path.exists(p) else "N"
1358 |                 print(f"    [{exists}] {os.path.basename(p)}")
1359 |         else:
1360 |             exists = "Y" if os.path.exists(path) else "N"
1361 |             print(f"    [{exists}] {os.path.basename(path)}")
1362 | 
1363 |     print(f"\n  TIMING:")
1364 |     for step, secs in timing.items():
1365 |         if step not in ("video_duration", "video_size_mb"):
1366 |             print(f"    {step:25s}: {secs:.1f}s")
1367 |     print(f"\n  Output: {run_dir}")
1368 |     print("=" * 70)
1369 | 
1370 |     _write_timing_report(run_dir, timing, t_pipeline_start, success=passed)
1371 | 
1372 |     # Save manifest
1373 |     manifest = {
1374 |         "version": "v5",
1375 |         "episode_title": script.get("episode_title", ""),
1376 |         "btc_price": btc_price,
1377 |         "test_mode": test_mode,
1378 |         "timestamp": time_str,
1379 |         "clips_used": [
1380 |             {"rank": r, "channel": info.get("channel", ""), "video_id": info.get("video_id", "")}
1381 |             for r, info in sorted(extracted_clips.items())
1382 |         ],
1383 |         "outputs": {k: (v if isinstance(v, list) else [v]) for k, v in outputs.items()},
1384 |         "timing": timing,
1385 |         "success": passed,
1386 |     }
1387 |     manifest_path = os.path.join(run_dir, "manifest.json")
1388 |     with open(manifest_path, "w") as f:
1389 |         json.dump(manifest, f, indent=2)
1390 | 
1391 |     # ── Step 13: QUALITY GATE + AUTO-UPLOAD ────────────────────────────────
1392 |     print("\n[STEP 13] QUALITY GATE...")
1393 |     t0 = time.time()
1394 |     quality_score = compute_quality_score(manifest_path, video_path=final_video)
1395 |     print(f"  {format_score_report(quality_score)}")
1396 |     manifest["quality_score"] = quality_score
1397 | 
1398 |     if is_enabled("youtube_auto_upload") and should_upload(quality_score):
1399 |         from utils.youtube_upload import upload_episode as yt_upload, build_description, build_tags
1400 |         # Build YouTube metadata
1401 |         ep_title = script.get("episode_title", "Pulse Check")
1402 |         yt_title = f"Bitcoin Daily Brief — {ts.strftime('%b %d, %Y')} | Protocol Pulse"
1403 |         chapters_text = ""
1404 |         if os.path.exists(chapters_path):
1405 |             with open(chapters_path) as f:
1406 |                 chapters_text = f.read()
1407 |         yt_description = build_description(
1408 |             summary=f"{ep_title}\n\nBTC Price: {btc_price}",
1409 |             chapters_text=chapters_text,
1410 |             clips=clips,
1411 |         )
1412 |         topics = [c.get("channel", "") for c in clips]
1413 |         yt_tags = build_tags(topics)
1414 | 
1415 |         print(f"  Uploading to YouTube (unlisted)...")
1416 |         upload_result = yt_upload(
1417 |             final_video, yt_title, yt_description,
1418 |             tags=yt_tags, thumbnail_path=thumb_path, privacy="unlisted",
1419 |         )
1420 |         print(f"  Upload result: {upload_result.get('status')}")
1421 |         if upload_result.get("url"):
1422 |             print(f"  URL: {upload_result['url']}")
1423 |         manifest["upload_result"] = upload_result
1424 |         if is_enabled("telegram_alerts") and upload_result.get("url"):
1425 |             alert_upload_success(date_str, upload_result["url"])
1426 |     elif quality_score < 85:
1427 |         logger.warning(f"QUALITY HOLD: Score {quality_score} < 85. Episode held for review.")
1428 |         hold_path = os.path.join(run_dir, "HOLD_FOR_REVIEW.txt")
1429 |         with open(hold_path, "w") as f:
1430 |             f.write(f"Quality score: {quality_score}/100\n")
1431 |             f.write(f"Threshold: 85\n")
1432 |             f.write(f"Reason: Below quality threshold\n")
1433 |             f.write(f"Episode: {script.get('episode_title', '')}\n")
1434 |             f.write(f"Video: {final_video}\n")
1435 |         manifest["held_for_review"] = True
1436 |         if is_enabled("telegram_alerts"):
1437 |             alert_quality_hold(date_str, quality_score)
1438 |     else:
1439 |         logger.info("YouTube auto-upload disabled in feature flags")
1440 | 
1441 |     # Write final manifest with quality score
1442 |     with open(manifest_path, "w") as f:
1443 |         json.dump(manifest, f, indent=2)
1444 |     timing["13_quality_gate"] = round(time.time() - t0, 2)
1445 | 
1446 |     # ── Step 14: STAGE BRIEF (post Grade-A render) ─────────────────────────
1447 |     if quality_score >= 85:
1448 |         try:
1449 |             from generate_stage_brief import generate_brief
1450 |             print("\n[STEP 14] GENERATING STAGE BRIEF...")
1451 |             t0 = time.time()
1452 |             brief_path = generate_brief(run_dir)
1453 |             if brief_path:
1454 |                 logger.info(f"Stage brief generated: {brief_path}")
1455 |                 print(f"  Stage brief: {brief_path}")
1456 |                 manifest["stage_brief"] = brief_path
1457 |             else:
1458 |                 logger.warning("Stage brief returned None")
1459 |                 print("  Stage brief: skipped (returned None)")
1460 |             timing["14_stage_brief"] = round(time.time() - t0, 2)
1461 |         except Exception as e:
1462 |             logger.warning(f"Stage brief generation failed (non-fatal): {e}")
1463 |             print(f"  Stage brief failed (non-fatal): {e}")
1464 |             timing["14_stage_brief"] = 0
1465 |     else:
1466 |         logger.info(f"Skipping stage brief — quality score {quality_score} < 85")
1467 | 
1468 |     # Save episode performance data (V17)
1469 |     try:
1470 |         from utils.analytics_store import save_episode_performance
1471 |         perf_data = {
1472 |             "date": ts.strftime("%Y-%m-%d"),
1473 |             "episode_title": script.get("episode_title", ""),
1474 |             "channels_used": [c.get("channel", "") for c in manifest.get("clips_used", [])],
1475 |             "quality_score": manifest.get("quality_score", 0),
1476 |             "clips_count": len(manifest.get("clips_used", [])),
1477 |             "duration_seconds": round(timing.get("video_duration", 0), 1),
1478 |             "bitrate_mbps": round(timing.get("video_size_mb", 0) * 8 / max(timing.get("video_duration", 1), 1), 1),
1479 |             "av_sync_offset": round(final_offset, 3),
1480 |             "music_mood": episode_mood,
1481 |             "test_mode": test_mode,
1482 |         }
1483 |         save_episode_performance(date_str, perf_data)
1484 |     except Exception as e:
1485 |         logger.warning(f"Performance data save failed: {e}")
1486 | 
1487 |     # Telegram success alert
1488 |     if is_enabled("telegram_alerts") and passed:
1489 |         alert_pipeline_success(date_str, quality_score,
1490 |                                timing.get("video_duration", 0), final_video)
1491 | 
1492 |     # ── Step 14: FORMAT MULTIPLIER (V22) ───────────────────────────────────
1493 |     # LAW 1: Only runs AFTER episode is fully rendered and QC-passed.
1494 |     # LAW 2: Runs as a detached subprocess — never blocks or delays the main render.
1495 |     if is_enabled("multi_format_output") and passed:
1496 |         print("\n[STEP 14] FORMAT MULTIPLIER — launching secondary formats...")
1497 |         try:
1498 |             fmt_script = os.path.join(BASE, "format_multiplier.py")
1499 |             fmt_args = [
1500 |                 sys.executable, fmt_script,
1501 |                 "--manifest", manifest_path,
1502 |                 "--video", final_video,
1503 |             ]
1504 |             if test_mode:
1505 |                 fmt_args.append("--test")
1506 |             # Detached subprocess: does not block main pipeline return
1507 |             fmt_proc = subprocess.Popen(
1508 |                 fmt_args,
1509 |                 stdout=open(os.path.join(run_dir, "format_multiplier.log"), "w"),
1510 |                 stderr=subprocess.STDOUT,
1511 |                 start_new_session=True,  # detach from parent process group
1512 |             )
1513 |             print(f"  Format multiplier launched (PID {fmt_proc.pid}) — 5 formats running in background")
1514 |             print(f"  Log: {run_dir}/format_multiplier.log")
1515 |             manifest["format_multiplier_pid"] = fmt_proc.pid
1516 |         except Exception as e:
1517 |             logger.warning(f"Format multiplier launch failed (non-blocking): {e}")
1518 |     elif not is_enabled("multi_format_output"):
1519 |         logger.info("multi_format_output feature flag is disabled — skipping format multiplier")
1520 | 
1521 |     # ── Post-render health check + Resend notification ─────────────────────
1522 |     hc_passed = True  # default for test mode; overridden below for production
1523 |     if not test_mode:
1524 |         hc_passed, hc_errors = _post_render_health_check(final_video)
1525 |         dur_s = timing.get("video_duration", 0)
1526 |         size_mb = timing.get("video_size_mb", 0)
1527 |         dur_min = int(dur_s // 60)
1528 |         dur_sec = int(dur_s % 60)
1529 |         if passed and hc_passed:
1530 |             _send_resend_alert(
1531 |                 f"Pulse Check rendered: {dur_min}m {dur_sec}s, {size_mb:.0f}MB",
1532 |                 f"Episode: {script.get('episode_title', 'Untitled')}\n"
1533 |                 f"Duration: {dur_min}m {dur_sec}s\n"
1534 |                 f"Size: {size_mb:.1f}MB\n"
1535 |                 f"Quality: {quality_score}/100\n"
1536 |                 f"Video: {final_video}",
1537 |             )
1538 |         else:
1539 |             _send_resend_alert(
1540 |                 "ALERT: Pulse Check render issues detected",
1541 |                 f"Episode: {script.get('episode_title', 'Untitled')}\n"
1542 |                 f"Pipeline passed: {passed}\n"
1543 |                 f"Health check passed: {hc_passed}\n"
1544 |                 f"Errors: {hc_errors}\n"
1545 |                 f"Video: {final_video}",
1546 |             )
1547 | 
1548 |     success = passed and hc_passed and qc_passed
1549 |     if success:
1550 |         _clear_checkpoint()  # P0 Fix 3: clear checkpoint on success
1551 |     return success
1552 | 
1553 | 
1554 | def _write_timing_report(run_dir: str, timing: dict, t_start: float, success: bool):
1555 |     report_path = os.path.join(run_dir, "timing_report.txt")
1556 |     ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
1557 |     lines = [
1558 |         "PULSE CHECK V5 — Timing Report",
1559 |         f"Generated: {ts}",
1560 |         f"Status: {'SUCCESS' if success else 'FAILED'}",
1561 |         "",
1562 |         "STEP TIMINGS:",
1563 |     ]
1564 |     for step, val in timing.items():
1565 |         if step in ("video_duration", "video_size_mb"):
1566 |             continue
1567 |         lines.append(f"  {step:<25}: {val:.1f}s")
1568 |     lines += [
1569 |         "",
1570 |         "OUTPUT STATS:",
1571 |         f"  video_duration_s     : {timing.get('video_duration', 'N/A')}",
1572 |         f"  video_size_mb        : {timing.get('video_size_mb', 'N/A')}",
1573 |         f"  total_wall_time_s    : {time.time() - t_start:.1f}",
1574 |     ]
1575 |     with open(report_path, "w") as f:
1576 |         f.write("\n".join(lines) + "\n")
1577 | 
1578 | 
1579 | def main():
1580 |     parser = argparse.ArgumentParser(
1581 |         description="Pulse Check V5 — Clip-First Video Producer")
1582 |     parser.add_argument("--test", action="store_true",
1583 |                         help="Test mode: fewer clips, truncated, test output dir")
1584 |     parser.add_argument("--skip-scan", action="store_true",
1585 |                         help="Skip channel scanning, use cached transcripts")
1586 |     parser.add_argument("--fast-test", action="store_true",
1587 |                         help="Fast test: no API calls (Claude/scan), hardcoded script, <3 min render")
1588 |     parser.add_argument("--reuse-content", action="store_true",
1589 |                         help="Skip Steps 1-6 (fetch/script/TTS), reuse locked content from previous run")
1590 |     args = parser.parse_args()
1591 | 
1592 |     # P0 Fix 1: flock process lock — prevent duplicate producers
1593 |     lock_file = open("/tmp/daily_producer.lock", "w")
1594 |     try:
1595 |         fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
1596 |     except IOError:
1597 |         logger.error("Another daily_producer is already running. Exiting.")
1598 |         sys.exit(1)
1599 | 
1600 |     success = run_pipeline(test_mode=args.test, skip_scan=args.skip_scan,
1601 |                            fast_test=args.fast_test,
1602 |                            reuse_content=args.reuse_content)
1603 | 
1604 |     fcntl.flock(lock_file, fcntl.LOCK_UN)
1605 |     # ── Post-render: fire tweet machine from morning brief ──────────────
1606 |     try:
1607 |         import subprocess as _sp
1608 |         _sp.Popen(["python3", "/home/ultron/protocol_pulse/services/tweet_machine.py"],
1609 |                   stdout=open("/home/ultron/protocol_pulse/logs/tweet_machine.log", "a"),
1610 |                   stderr=subprocess.STDOUT)
1611 |         print("  Tweet machine: fired (async)")
1612 |     except Exception as _te:
1613 |         print(f"  Tweet machine: skipped ({_te})")
1614 |     sys.exit(0 if success else 1)
1615 | 
1616 | 
1617 | if __name__ == "__main__":
1618 |     main()
1619 | 
```

### File: video_pipeline_v3/config/feature_flags.json (17 lines)
```
   1 | {
   2 |   "mood_music": true,
   3 |   "ad_read_filter": true,
   4 |   "channel_dedup": true,
   5 |   "silence_detection": true,
   6 |   "social_segment": true,
   7 |   "tweet_cards": true,
   8 |   "youtube_auto_upload": false,
   9 |   "telegram_alerts": false,
  10 |   "analytics_feedback": false,
  11 |   "breaking_news_detector": false,
  12 |   "sponsor_rotation": false,
  13 |   "remotion_visuals": false,
  14 |   "agent_dev_mode": false,
  15 |   "test_mode": false,
  16 |   "multi_format_output": false
  17 | }
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
