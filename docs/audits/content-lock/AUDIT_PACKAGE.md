# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: content-lock
# Branch: main
# Generated: 2026-03-24 13:57 UTC
# Purpose: Pre-merge quality gate. 3 independent AI models will review this.
# You are one of: Gemini 2.5 Pro / GPT-4o / Grok-3
# Other top AI models will also review this same code. Put your best work forward.

---

## WHAT THIS FEATURE DOES
(see gospel)

---

## GOVERNING LAWS (this code MUST comply with every law below — flag any violation)


---

## TECHNOLOGY STACK
- Python 3.12, Flask 3.x, SQLite via SQLAlchemy ORM
- Ubuntu 24.04 on Ultron server (2x RTX 4090, 93GB RAM)
- All UI animations: CSS/SVG only — NO Three.js, no WebGL, no Canvas
- External services: ElevenLabs TTS, HeyGen avatars, Wav2Lip GPU lip-sync
- ~1000 concurrent users at peak — every route must handle load
- Every DB query on a sort/filter column MUST have an index

---

## THE CODE (every new and modified file)

### File: video_pipeline_v3/daily_producer.py (1526 lines)
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
 523 |                  fast_test: bool = False) -> bool:
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
 556 |     tts_cache = os.path.join(BASE, "tts_cache")
 557 |     shutil.rmtree(tts_cache, ignore_errors=True)
 558 |     os.makedirs(tts_cache, exist_ok=True)
 559 |     logger.info("TTS cache wiped")
 560 | 
 561 |     ts = datetime.now(timezone.utc)
 562 |     date_str = ts.strftime("%Y%m%d")
 563 |     time_str = ts.strftime("%Y%m%d_%H%M%S")
 564 | 
 565 |     if test_mode:
 566 |         run_dir = os.path.join(BASE, "output", f"test_{time_str}")
 567 |     else:
 568 |         run_dir = os.path.join(BASE, "output", ts.strftime("%Y-%m-%d"))
 569 | 
 570 |     os.makedirs(run_dir, exist_ok=True)
 571 |     final_video = os.path.join(run_dir, f"pulse_check_{date_str}.mp4")
 572 |     timing = {}
 573 |     t_pipeline_start = time.time()
 574 | 
 575 |     # Ensure music directory exists
 576 |     ensure_music_dir()
 577 | 
 578 |     # Log feature flags at startup
 579 |     flags = load_flags()
 580 |     logger.info(f"Feature flags: {json.dumps(flags)}")
 581 | 
 582 |     # Telegram alert at pipeline start
 583 |     if is_enabled("telegram_alerts"):
 584 |         alert_pipeline_start(date_str, test_mode)
 585 | 
 586 |     print("\n" + "=" * 70)
 587 |     print(f"  PULSE CHECK V5 — CLIP-FIRST PIPELINE")
 588 |     mode_label = "FAST TEST " if fast_test else ("TEST " if test_mode else "")
 589 |     print(f"  {mode_label}Run {time_str}")
 590 |     print(f"  Output: {run_dir}")
 591 |     print(f"  Music: {'YES' if has_music() else 'no (skipped gracefully)'}")
 592 |     print("=" * 70)
 593 | 
 594 |     # ── Step 1: BTC PRICE ─────────────────────────────────────────────────
 595 |     print("\n[STEP 1/12] FETCHING BTC PRICE...")
 596 |     t0 = time.time()
 597 |     btc_price = get_btc_price()
 598 |     print(f"  BTC: {btc_price}")
 599 |     timing["1_price"] = round(time.time() - t0, 2)
 600 |     write_render_context(1, "ok", btc_price=btc_price)
 601 | 
 602 |     # ── Step 2: SCAN CHANNELS ─────────────────────────────────────────────
 603 |     print("\n[STEP 2/12] SCANNING PARTNER CHANNELS...")
 604 |     t0 = time.time()
 605 |     if skip_scan:
 606 |         # Load cached transcripts from transcript dir
 607 |         import glob
 608 |         transcript_dir = os.path.join(BASE, "transcripts")
 609 |         videos = []
 610 |         for tf in sorted(glob.glob(os.path.join(transcript_dir, "*.json")))[:60]:
 611 |             with open(tf) as f:
 612 |                 data = json.load(f)
 613 |                 videos.append({
 614 |                     "video_id": data.get("video_id", ""),
 615 |                     "title": data.get("title", ""),
 616 |                     "channel": data.get("channel", ""),
 617 |                     "duration": data.get("duration", 0),
 618 |                     "upload_date": "",
 619 |                     "url": f"https://www.youtube.com/watch?v={data.get('video_id', '')}",
 620 |                     "transcript_text": data.get("text", ""),
 621 |                     "timestamped_text": data.get("timestamped_text", ""),
 622 |                 })
 623 |         print(f"  Loaded {len(videos)} cached transcripts")
 624 |     else:
 625 |         whisper_model = "tiny" if test_mode else "base"
 626 |         videos = scan_all_channels(model_size=whisper_model)
 627 |         print(f"  Scanned: {len(videos)} videos with transcripts")
 628 |     timing["2_scan"] = round(time.time() - t0, 2)
 629 |     write_render_context(2, "ok")
 630 | 
 631 |     if not videos:
 632 |         print("\n  [FAIL] No videos found — cannot produce episode")
 633 |         _write_timing_report(run_dir, timing, t_pipeline_start, success=False)
 634 |         if is_enabled("telegram_alerts"):
 635 |             alert_pipeline_failure(date_str, "scan", "No videos found")
 636 |         return False
 637 | 
 638 |     # ── Step 3: SELECT BEST CLIPS ─────────────────────────────────────────
 639 |     if fast_test:
 640 |         print("\n[STEP 3/12] SELECTING CLIPS (fast-test: first 2, no Claude)...")
 641 |         t0 = time.time()
 642 |         # Build minimal selections from cached videos without calling Claude
 643 |         fast_clips = []
 644 |         for i, v in enumerate(videos[:2], 1):
 645 |             text = v.get("transcript_text", "")
 646 |             fast_clips.append({
 647 |                 "rank": i,
 648 |                 "video_id": v["video_id"],
 649 |                 "channel": v.get("channel", ""),
 650 |                 "title": v.get("title", ""),
 651 |                 "quote": text[:100] if text else "No transcript",
 652 |                 "why": "fast-test auto-select",
 653 |                 "start_seconds": 60,
 654 |                 "end_seconds": 90,
 655 |             })
 656 |         selections = {"clips": fast_clips}
 657 |         clips = fast_clips
 658 |         print(f"  Auto-selected: {len(clips)} clips (no API call)")
 659 |         timing["3_select"] = round(time.time() - t0, 2)
 660 |     else:
 661 |         print("\n[STEP 3/12] SELECTING BEST CLIPS (Claude)...")
 662 |         t0 = time.time()
 663 |         selections = select_clips(videos)
 664 |         clips = selections.get("clips", [])
 665 |         print(f"  Selected: {len(clips)} clips")
 666 |         for c in clips:
 667 |             print(f"    #{c['rank']}: [{c.get('channel','')}] {c.get('quote','')[:50]}...")
 668 |         timing["3_select"] = round(time.time() - t0, 2)
 669 | 
 670 |     if not clips:
 671 |         print("\n  [FAIL] No clips selected — cannot produce episode")
 672 |         _write_timing_report(run_dir, timing, t_pipeline_start, success=False)
 673 |         if is_enabled("telegram_alerts"):
 674 |             alert_pipeline_failure(date_str, "select", "No clips selected")
 675 |         return False
 676 | 
 677 |     # In test mode, use only top 2 clips
 678 |     if not fast_test and test_mode and len(clips) > 2:
 679 |         selections["clips"] = clips[:2]
 680 |         clips = selections["clips"]
 681 |         print(f"  [test] Truncated to {len(clips)} clips")
 682 | 
 683 |     # Save selections
 684 |     sel_path = os.path.join(run_dir, "selections.json")
 685 |     with open(sel_path, "w") as f:
 686 |         json.dump(selections, f, indent=2)
 687 | 
 688 |     # ── Step 3b: Select independent montage clips (Qwen, free) ──────────
 689 |     print("\n[STEP 3b] SELECTING MONTAGE CLIPS (local Qwen)...")
 690 |     try:
 691 |         from clip_selector import select_montage_clips
 692 |         montage_selections = select_montage_clips(videos)
 693 |         montage_clips_sel = montage_selections.get("clips", [])
 694 |         montage_sel_path = os.path.join(run_dir, "montage_selections.json")
 695 |         with open(montage_sel_path, "w") as f:
 696 |             json.dump(montage_selections, f, indent=2)
 697 |         print(f"  Montage: {len(montage_clips_sel)} independent clips selected")
 698 |     except Exception as e:
 699 |         print(f"  Montage selection failed ({e}) — montage will reuse Pulse Check clips")
 700 |         montage_selections = None
 701 | 
 702 |     # ── Step 4: EXTRACT CLIPS ─────────────────────────────────────────────
 703 |     print("\n[STEP 4/12] EXTRACTING CLIPS (yt-dlp with original audio)...")
 704 |     t0 = time.time()
 705 |     # FIX 2: Wipe clips/ dir completely to prevent stale files from prior renders
 706 |     clip_dir = os.path.join(run_dir, "clips")
 707 |     if os.path.exists(clip_dir):
 708 |         shutil.rmtree(clip_dir)
 709 |         logger.info(f"  Wiped stale clips dir: {clip_dir}")
 710 |     os.makedirs(clip_dir, exist_ok=True)
 711 |     # Also wipe stale pip_preview files from work dir
 712 |     work_dir = os.path.join(run_dir, "work")
 713 |     if os.path.exists(work_dir):
 714 |         import glob as _pip_glob
 715 |         for stale_pip in _pip_glob.glob(os.path.join(work_dir, "pip_preview_*.mp4")):
 716 |             try:
 717 |                 os.remove(stale_pip)
 718 |             except OSError:
 719 |                 pass
 720 |         logger.info("  Wiped stale pip_preview files from work/")
 721 |     extracted_clips = extract_all(selections, clip_dir)
 722 |     print(f"  Extracted: {len(extracted_clips)}/{len(clips)} clips")
 723 | 
 724 |     # ── Quality-aware fallback: retry with ranked alternates ──────────
 725 |     if not test_mode and not fast_test and len(extracted_clips) < 5:
 726 |         used_video_ids = {info["video_id"] for info in extracted_clips.values()}
 727 |         used_channels = {info["channel"] for info in extracted_clips.values()}
 728 |         tried_video_ids = {c["video_id"] for c in clips} | used_video_ids
 729 | 
 730 |         remaining = [v for v in videos
 731 |                      if v["video_id"] not in tried_video_ids
 732 |                      and v.get("channel", "") not in used_channels]
 733 | 
 734 |         if remaining:
 735 |             need = 5 - len(extracted_clips)
 736 |             logger.info(
 737 |                 f"[extractor] Only {len(extracted_clips)}/5 clips passed quality "
 738 |                 f"— selecting fallbacks from {len(remaining)} candidates (need {need})"
 739 |             )
 740 |             fallback_sel = select_clips(remaining)
 741 |             fallback_clips = fallback_sel.get("clips", [])
 742 | 
 743 |             max_rank = max(extracted_clips.keys()) if extracted_clips else 0
 744 |             for fc in fallback_clips:
 745 |                 if len(extracted_clips) >= 5:
 746 |                     break
 747 |                 fc_ch = fc.get("channel", "")
 748 |                 fc_vid = fc.get("video_id", "")
 749 |                 if fc_ch in used_channels or fc_vid in tried_video_ids:
 750 |                     continue
 751 |                 max_rank += 1
 752 |                 fc["rank"] = max_rank
 753 |                 logger.info(
 754 |                     f"[extractor] Clip failed quality — trying fallback candidate "
 755 |                     f"#{max_rank} [{fc_ch}] from selections"
 756 |                 )
 757 |                 fb_result = extract_all({"clips": [fc]}, clip_dir)
 758 |                 if fb_result:
 759 |                     for r, info in fb_result.items():
 760 |                         extracted_clips[r] = info
 761 |                         used_video_ids.add(info["video_id"])
 762 |                         used_channels.add(info["channel"])
 763 |                         tried_video_ids.add(fc_vid)
 764 |                         selections["clips"].append(fc)
 765 |                         logger.info(
 766 |                             f"[extractor] Fallback clip #{r} passed quality — "
 767 |                             f"{info['channel']} ({info['duration']:.1f}s)"
 768 |                         )
 769 |                 else:
 770 |                     tried_video_ids.add(fc_vid)
 771 |                     logger.warning(
 772 |                         f"[extractor] Fallback [{fc_ch}] also failed quality — trying next"
 773 |                     )
 774 | 
 775 |             # Update clips list and re-save selections
 776 |             clips = selections.get("clips", [])
 777 |             with open(sel_path, "w") as f:
 778 |                 json.dump(selections, f, indent=2)
 779 |             logger.info(f"[extractor] After fallback: {len(extracted_clips)}/5 clips")
 780 |         else:
 781 |             logger.warning("[extractor] No fallback candidates — all channels/videos exhausted")
 782 | 
 783 |     if not test_mode:
 784 |         _unique_ch = len({info.get("channel", f"unk_{i}") for i, info in enumerate(extracted_clips.values())})
 785 |         if len(extracted_clips) < 3 or _unique_ch < 2:
 786 |             logger.critical(
 787 |                 f"[PIPELINE] HARD FAIL: Need 5 clips from 5 unique channels, "
 788 |                 f"got {len(extracted_clips)} clips from {_unique_ch} channels."
 789 |             )
 790 |             return False
 791 |     for rank, info in sorted(extracted_clips.items()):
 792 |         print(f"    #{rank}: {info['channel']} — {info['duration']:.1f}s")
 793 |     timing["4_extract"] = round(time.time() - t0, 2)
 794 | 
 795 |     # ── Step 4m: Extract montage clips ───────────────────────────────────
 796 |     if montage_selections and montage_selections.get("clips"):
 797 |         print("\n[STEP 4m] EXTRACTING MONTAGE CLIPS...")
 798 |         try:
 799 |             extract_montage_all(montage_selections, clip_dir)
 800 |             print(f"  Montage clips extracted to {clip_dir}")
 801 |         except Exception as e:
 802 |             print(f"  Montage extraction failed ({e}) — skipping")
 803 | 
 804 |     if not extracted_clips:
 805 |         print("\n  [FAIL] No clips extracted — cannot produce episode")
 806 |         _write_timing_report(run_dir, timing, t_pipeline_start, success=False)
 807 |         if is_enabled("telegram_alerts"):
 808 |             alert_pipeline_failure(date_str, "extract", "No clips extracted")
 809 |         return False
 810 | 
 811 |     # ── Step 4b: MOOD CLASSIFICATION + MUSIC SELECTION ──────────────────
 812 |     import glob as _glob
 813 |     import random as _random
 814 | 
 815 |     def classify_episode_mood(script_text: str) -> str:
 816 |         """Classify episode mood from clip quotes."""
 817 |         moods = {"tense": 0, "confident": 0, "contemplative": 0, "upbeat": 0, "edge": 0}
 818 |         lower = script_text.lower()
 819 |         if any(w in lower for w in ["crash", "sell", "breaking", "emergency", "plunge", "war"]):
 820 |             moods["tense"] += 3
 821 |         if any(w in lower for w in ["bullish", "ath", "record", "buying", "accumul"]):
 822 |             moods["confident"] += 3
 823 |         if any(w in lower for w in ["philosoph", "long-term", "decade", "future", "think about"]):
 824 |             moods["contemplative"] += 2
 825 |         if any(w in lower for w in ["community", "fun", "meme", "laugh", "celebrate"]):
 826 |             moods["upbeat"] += 2
 827 |         if any(w in lower for w in ["controversial", "scam", "fraud", "attack", "fight"]):
 828 |             moods["edge"] += 2
 829 |         best = max(moods, key=moods.get)
 830 |         return best if moods[best] > 0 else "confident"
 831 | 
 832 |     def select_music_bed(mood: str, music_dir: str) -> str:
 833 |         # Sprint 1.10: Randomize music, avoid repeating last track
 834 |         last_track_file = os.path.join(music_dir, ".last_track.txt")
 835 |         last_track = ""
 836 |         if os.path.exists(last_track_file):
 837 |             try:
 838 |                 last_track = open(last_track_file).read().strip()
 839 |             except Exception:
 840 |                 pass
 841 | 
 842 |         tracks = _glob.glob(os.path.join(music_dir, f"{mood}_*.mp3"))
 843 |         if not tracks:
 844 |             tracks = _glob.glob(os.path.join(music_dir, "confident_*.mp3"))
 845 |         if not tracks:
 846 |             # Get all tracks except reserved ones
 847 |             all_tracks = _glob.glob(os.path.join(music_dir, "*.mp3"))
 848 |             tracks = [t for t in all_tracks
 849 |                       if os.path.basename(t) not in ("pp_outro.mp3", "pp_background.mp3",
 850 |                                                        "pp_intro.mp3", "pp_transition.mp3")]
 851 |         if not tracks:
 852 |             return ""
 853 | 
 854 |         # Avoid repeating last track
 855 |         if last_track and len(tracks) > 1:
 856 |             tracks = [t for t in tracks if os.path.basename(t) != last_track] or tracks
 857 | 
 858 |         chosen = _random.choice(tracks)
 859 |         try:
 860 |             with open(last_track_file, "w") as f:
 861 |                 f.write(os.path.basename(chosen))
 862 |         except Exception:
 863 |             pass
 864 |         return chosen
 865 | 
 866 |     def select_intro_music(music_dir: str) -> str:
 867 |         tracks = _glob.glob(os.path.join(music_dir, "intro_*.mp3"))
 868 |         return _random.choice(tracks) if tracks else ""
 869 | 
 870 |     # Classify mood from clip quotes
 871 |     clip_quotes = " ".join(c.get("quote", "") + " " + c.get("why", "") for c in clips)
 872 |     episode_mood = classify_episode_mood(clip_quotes)
 873 |     music_dir = os.path.join(BASE, "assets", "music")
 874 |     music_bed = select_music_bed(episode_mood, music_dir)
 875 |     intro_music = select_intro_music(music_dir)
 876 |     print(f"  Mood: {episode_mood} | Music: {os.path.basename(music_bed) if music_bed else 'default'}")
 877 | 
 878 |     # ── Step 4c: LIVE SIGNALS ─────────────────────────────────────────────
 879 |     live_context = ""
 880 |     live_signals_path = os.path.join(BASE, "data", "intelligence", "live_signals.json")
 881 |     try:
 882 |         if os.path.exists(live_signals_path):
 883 |             with open(live_signals_path) as f:
 884 |                 live_data = json.load(f)
 885 |             from datetime import timezone as _tz
 886 |             now = datetime.now(_tz.utc) if hasattr(datetime, 'now') else datetime.utcnow()
 887 |             active_streams = []
 888 |             for s in live_data.get("live_streams", []):
 889 |                 # Only include streams from last 6 hours
 890 |                 started = s.get("started_at", "")
 891 |                 try:
 892 |                     started_dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
 893 |                     age_hours = (now - started_dt).total_seconds() / 3600
 894 |                     if age_hours > 6:
 895 |                         continue
 896 |                 except (ValueError, AttributeError):
 897 |                     continue
 898 |                 source = s.get("source", "youtube_live")
 899 |                 channel = s.get("channel", "unknown")
 900 |                 title = s.get("title", "")
 901 |                 topics = ", ".join(s.get("topics", []))
 902 |                 sentiment = s.get("current_sentiment", 50)
 903 |                 sentiment_label = "bullish" if sentiment > 60 else "bearish" if sentiment < 40 else "neutral"
 904 |                 active_streams.append(
 905 |                     f"- {channel} ({source}): \"{title}\" — topics: {topics}, sentiment: {sentiment_label} ({sentiment})"
 906 |                 )
 907 |             if active_streams:
 908 |                 live_context = "\n".join(active_streams)
 909 |                 print(f"  Live signals: {len(active_streams)} active streams in last 6 hours")
 910 |                 for line in active_streams:
 911 |                     print(f"    {line}")
 912 |             else:
 913 |                 print("  Live signals: no active streams in last 6 hours")
 914 |     except Exception as e:
 915 |         logger.warning(f"Live signals read failed: {e}")
 916 | 
 917 |     # ── Step 5a: Fetch social posts + Space Tap BEFORE script generation ──
 918 |     # Social posts: fetch once, sort by likes desc, pass to script_writer
 919 |     sorted_social = []
 920 |     try:
 921 |         from utils.social_fetcher import get_todays_social_posts
 922 |         sorted_social = get_todays_social_posts(max_posts=5)
 923 |         if sorted_social:
 924 |             sorted_social.sort(key=lambda p: p.get("likes", 0), reverse=True)
 925 |             for si, sp in enumerate(sorted_social):
 926 |                 logger.info(f"SOCIAL ORDER: #{si}: @{sp.get('handle', '?')} — {sp.get('text', '')[:40]}")
 927 |     except Exception as e:
 928 |         logger.warning(f"Social posts fetch failed: {e}")
 929 | 
 930 |     # Space Tap: fetch X Spaces clips BEFORE script generation so LLM can write dialogue
 931 |     print("[STEP 5a] SPACE TAP -- LIVE X SPACES INTERCEPT...")
 932 |     try:
 933 |         import importlib.util
 934 |         _spaces_scraper_path = os.path.join(
 935 |             os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
 936 |             "x_spaces_scraper", "scraper.py"
 937 |         )
 938 |         if os.path.exists(_spaces_scraper_path):
 939 |             _spec = importlib.util.spec_from_file_location("x_spaces_scraper", _spaces_scraper_path)
 940 |             _mod = importlib.util.module_from_spec(_spec)
 941 |             _spec.loader.exec_module(_mod)
 942 |             # Hard 120s timeout — Whisper can hang forever without this
 943 |             import threading as _st_thread
 944 |             _st_result = [None]
 945 |             def _fetch_spaces(): _st_result[0] = _mod.get_best_space_clips(max_clips=3)
 946 |             _st_t = _st_thread.Thread(target=_fetch_spaces, daemon=True)
 947 |             _st_t.start(); _st_t.join(timeout=120)
 948 |             if _st_t.is_alive():
 949 |                 logger.warning("[SpaceTap] get_best_space_clips timed out (120s) — skipping")
 950 |                 _st = None
 951 |             else:
 952 |                 _st = _st_result[0]
 953 |             if _st and _st.get("clips"):
 954 |                 selections["space_tap_clips"] = _st["clips"]
 955 |                 print(f"  Space Tap: {len(_st['clips'])} clips from {_st.get('spaces_count', 0)} spaces")
 956 |             else:
 957 |                 print("  Space Tap: no live spaces — segment skipped")
 958 |         else:
 959 |             print("  Space Tap: scraper not installed — segment skipped")
 960 |     except Exception as _ste:
 961 |         logger.error(f"Space Tap fetch error: {type(_ste).__name__}: {_ste}")
 962 |         print(f"  Space Tap: skipped ({_ste})")
 963 | 
 964 |     # ── Step 5: GENERATE SCRIPT ───────────────────────────────────────────
 965 |     if fast_test:
 966 |         print("\n[STEP 5/12] GENERATING SCRIPT (fast-test: hardcoded, no Claude)...")
 967 |         t0 = time.time()
 968 |         script = _build_fast_test_script(extracted_clips, btc_price)
 969 |         timing["5_script"] = round(time.time() - t0, 2)
 970 |     else:
 971 |         print("\n[STEP 5/12] GENERATING HOST DIALOGUE (Claude)...")
 972 |         t0 = time.time()
 973 |         script = generate_from_clips(selections, btc_price=btc_price,
 974 |                                      live_context=live_context,
 975 |                                      social_posts_sorted=sorted_social)
 976 |         timing["5_script"] = round(time.time() - t0, 2)
 977 | 
 978 |     # Attach social posts to script for assembler (single source of truth)
 979 |     if sorted_social:
 980 |         script["social_posts"] = sorted_social
 981 | 
 982 |     # Re-read dialogue AFTER all mutations (Space Tap entries may be in script)
 983 |     dialogue = script.get("dialogue", [])
 984 |     speech_lines = [d for d in dialogue if d.get("host") in (1, 2, "1", "2")]
 985 |     clip_markers = [d for d in dialogue if d.get("host") in ("CLIP", "SPACE_CLIP")]
 986 |     social_seg_count = sum(1 for d in dialogue if d.get("type") == "social_segment")
 987 |     space_tap_count = sum(1 for d in dialogue if d.get("host") == "SPACE_CLIP"
 988 |                          or (d.get("type") or "").startswith("space_tap"))
 989 |     print(f"  Title: {script.get('episode_title', 'Untitled')}")
 990 |     print(f"  Dialogue: {len(speech_lines)} speech + {len(clip_markers)} clips")
 991 |     print(f"  SOCIAL segments: {social_seg_count} (input tweets: {len(sorted_social)})")
 992 |     print(f"  SPACE TAP entries: {space_tap_count} (input clips: {len(selections.get('space_tap_clips', []))})")
 993 |     if sorted_social and social_seg_count == 0:
 994 |         logger.error("SOCIAL SEGMENT ABSENT despite having tweet data — check script_writer enforcement")
 995 |     if selections.get("space_tap_clips") and space_tap_count == 0:
 996 |         logger.error("SPACE TAP ABSENT despite having clip data — check script_writer enforcement")
 997 | 
 998 |     # Save script
 999 |     script_path = os.path.join(run_dir, "script.json")
1000 |     with open(script_path, "w") as f:
1001 |         json.dump(script, f, indent=2)
1002 | 
1003 |     write_render_context(5, "ok",
1004 |                          episode_title=script.get("episode_title", ""),
1005 |                          social_posts_count=len(sorted_social),
1006 |                          space_tap_available=bool(selections.get("space_tap_clips")))
1007 | 
1008 |     # ── Step 6: TTS ───────────────────────────────────────────────────────
1009 |     print("\n[STEP 6/12] GENERATING PBX NARRATION AUDIO (ElevenLabs)...")
1010 |     t0 = time.time()
1011 |     audio_dir = os.path.join(run_dir, "audio")
1012 |     audio_data = generate_dialogue_audio(dialogue, audio_dir)
1013 |     successful = sum(1 for l in audio_data.get("lines", [])
1014 |                      if l.get("path") and os.path.exists(l.get("path", "")))
1015 |     print(f"  Audio: {successful}/{len(speech_lines)} lines")
1016 |     print(f"  Duration: {audio_data.get('total_duration', 0):.1f}s")
1017 |     timing["6_tts"] = round(time.time() - t0, 2)
1018 |     write_render_context(6, "ok", tts_provider="elevenlabs")
1019 | 
1020 |     # ── Step 6b: BUILD MANIFEST ─────────────────────────────────────────
1021 |     print("\n[STEP 6b/12] BUILDING EPISODE MANIFEST...")
1022 |     t0 = time.time()
1023 |     try:
1024 |         from manifest_builder import build_manifest
1025 |         episode_manifest = build_manifest(
1026 |             script, audio_data, extracted_clips, run_dir,
1027 |             music_bed=music_bed, btc_price=btc_price,
1028 |         )
1029 |         print(f"  Manifest: {episode_manifest.get('total_segments', 0)} segments, "
1030 |               f"~{episode_manifest.get('total_duration_estimate', 0):.0f}s estimated")
1031 |     except Exception as e:
1032 |         logger.warning(f"Manifest build failed (non-blocking): {e}")
1033 |         episode_manifest = {}
1034 |     timing["6b_manifest"] = round(time.time() - t0, 2)
1035 | 
1036 |     # ── Step 6c: PREFLIGHT CHECK ─────────────────────────────────────────
1037 |     manifest_json_path = os.path.join(run_dir, "episode_manifest.json")
1038 |     if os.path.exists(manifest_json_path):
1039 |         print("\n[STEP 6c/12] PREFLIGHT QC CHECK...")
1040 |         t0 = time.time()
1041 |         try:
1042 |             from qc_pipeline import preflight_check
1043 |             pf_passed, pf_errors, pf_warnings = preflight_check(manifest_json_path)
1044 |             print(f"  Preflight: {'PASS' if pf_passed else 'FAIL'} — "
1045 |                   f"{len(pf_errors)} errors, {len(pf_warnings)} warnings")
1046 |         except Exception as e:
1047 |             logger.warning(f"Preflight check failed (non-blocking): {e}")
1048 |         timing["6c_preflight"] = round(time.time() - t0, 2)
1049 | 
1050 |     # ── Step 7: ASSEMBLE ──────────────────────────────────────────────────
1051 |     print("\n[STEP 7/12] ASSEMBLING VIDEO...")
1052 |     t0 = time.time()
1053 |     result = assemble_episode(script, audio_data, extracted_clips, final_video,
1054 |                               btc_price=btc_price, music_bed=music_bed,
1055 |                               intro_music=intro_music)
1056 |     timing["7_assemble"] = round(time.time() - t0, 2)
1057 | 
1058 |     if not result or not os.path.exists(final_video):
1059 |         print("\n  [FAIL] Assembly failed")
1060 |         write_render_context(7, "fail", error="Video assembly failed or no output file")
1061 |         _write_timing_report(run_dir, timing, t_pipeline_start, success=False)
1062 |         if is_enabled("telegram_alerts"):
1063 |             alert_pipeline_failure(date_str, "assemble", "Video assembly failed")
1064 |         return False
1065 |     write_render_context(7, "ok")
1066 | 
1067 |     # ── Step 7b: PRE-FLIGHT QC (Grade A Guarantee) ───────────────────────
1068 |     print("\n[STEP 7b] PRE-FLIGHT QC...")
1069 |     t0 = time.time()
1070 |     for pf_attempt in range(1, MAX_PREFLIGHT_ATTEMPTS + 1):
1071 |         logger.info(f"[PREFLIGHT] Attempt {pf_attempt}/{MAX_PREFLIGHT_ATTEMPTS}")
1072 |         print(f"  Preflight attempt {pf_attempt}/{MAX_PREFLIGHT_ATTEMPTS}")
1073 |         qc = run_preflight_qc(final_video)
1074 | 
1075 |         if qc["passed"]:
1076 |             print("  [PREFLIGHT] PASSED — proceeding to grading")
1077 |             logger.info("[PREFLIGHT] PASSED — sending to grading")
1078 |             break
1079 | 
1080 |         logger.warning(f"[PREFLIGHT] FAILED: {qc['issues']}")
1081 |         print(f"  [PREFLIGHT] FAILED: {qc['issues']}")
1082 |         write_render_context("7b", "fail", error=str(qc["issues"]))
1083 | 
1084 |         if pf_attempt == MAX_PREFLIGHT_ATTEMPTS:
1085 |             logger.error("[PREFLIGHT] Max attempts reached — sending anyway")
1086 |             print("  [PREFLIGHT] Max attempts — sending to grading anyway")
1087 |             if is_enabled("telegram_alerts"):
1088 |                 from utils.telegram_alerts import send_alert
1089 |                 send_alert(
1090 |                     f"PREFLIGHT: {qc['issues']} — sending to grading anyway",
1091 |                     level="warning",
1092 |                 )
1093 |             break
1094 | 
1095 |         # Apply targeted fixes
1096 |         _apply_preflight_fixes(final_video, qc)
1097 | 
1098 |     timing["7b_preflight_qc"] = round(time.time() - t0, 2)
1099 |     write_render_context("7b", "ok" if qc["passed"] else "warn")
1100 | 
1101 |     # ── Step 8: SHORTS ────────────────────────────────────────────────────
1102 |     print("\n[STEP 8/12] GENERATING SHORTS (avatar)...")
1103 |     t0 = time.time()
1104 |     shorts_dir = os.path.join(run_dir, "shorts")
1105 |     shorts = generate_shorts(script, shorts_dir, btc_price=btc_price,
1106 |                              max_shorts=3 if not test_mode else 1)
1107 |     print(f"  Shorts: {len(shorts)}")
1108 |     timing["8_shorts"] = round(time.time() - t0, 2)
1109 | 
1110 |     # ── Step 9: THUMBNAIL ─────────────────────────────────────────────────
1111 |     print("\n[STEP 9/12] GENERATING THUMBNAIL (MMA Central style)...")
1112 |     t0 = time.time()
1113 |     thumb_data = script.get("thumbnail", {})
1114 |     top_quote = ""
1115 |     if clips:
1116 |         top_quote = clips[0].get("quote", "")
1117 |     thumb_path = os.path.join(run_dir, "thumbnail.png")
1118 |     generate_thumbnail(
1119 |         thumb_data.get("headline", script.get("episode_title", "PULSE CHECK")),
1120 |         thumb_data.get("subtext", ""),
1121 |         thumb_path,
1122 |         btc_price=btc_price,
1123 |         top_quote=top_quote,
1124 |     )
1125 |     timing["9_thumbnail"] = round(time.time() - t0, 2)
1126 | 
1127 |     # ── Step 10: CHAPTERS ─────────────────────────────────────────────────
1128 |     print("\n[STEP 10/12] GENERATING CHAPTERS...")
1129 |     t0 = time.time()
1130 |     chapters_path = os.path.join(run_dir, "chapters.txt")
1131 |     generate_chapters(script, audio_data, chapters_path)
1132 |     timing["10_chapters"] = round(time.time() - t0, 2)
1133 | 
1134 |     # ── Step 11: PODCAST + NEWSLETTER ─────────────────────────────────────
1135 |     print("\n[STEP 11/12] PODCAST AUDIO + NEWSLETTER...")
1136 |     t0 = time.time()
1137 |     podcast_path = os.path.join(run_dir, "podcast.mp3")
1138 |     extract_podcast_audio(final_video, podcast_path)
1139 | 
1140 |     email_html = generate_email_html(
1141 |         script.get("episode_title", "Pulse Check"),
1142 |         segments_summary=script.get("segments_summary", []),
1143 |         btc_price=btc_price,
1144 |     )
1145 |     newsletter_path = os.path.join(run_dir, "newsletter.html")
1146 |     save_newsletter_html(email_html, newsletter_path)
1147 |     timing["11_podcast_newsletter"] = round(time.time() - t0, 2)
1148 | 
1149 |     # ── Step 12: VERIFY ───────────────────────────────────────────────────
1150 |     print("\n[STEP 12/12] VERIFYING OUTPUT...")
1151 |     t0 = time.time()
1152 |     passed = verify_video(final_video)
1153 | 
1154 |     # Final AV sync validation
1155 |     final_offset = check_av_sync(final_video)
1156 |     print(f"  Final AV sync offset: {final_offset:+.3f}s")
1157 |     if abs(final_offset) > 0.05:
1158 |         logger.error(f"FINAL OUTPUT SYNC FAILED: {final_offset:+.3f}s > 0.05s — nuclear re-encode")
1159 |         nuclear_tmp = final_video + ".nuclear.mp4"
1160 |         nuclear_cmd = subprocess.run([
1161 |             "ffmpeg", "-y",
1162 |             "-fflags", "+genpts+igndts",
1163 |             "-i", final_video,
1164 |             "-c:v", "libx264", "-preset", "medium",
1165 |             "-b:v", "8M", "-minrate", "5M", "-maxrate", "10M", "-bufsize", "15M",
1166 |             "-r", "30", "-vsync", "cfr",
1167 |             "-vf", "setpts=PTS-STARTPTS,format=yuv420p",
1168 |             "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
1169 |             "-af", "asetpts=PTS-STARTPTS,aresample=async=1",
1170 |             "-movflags", "+faststart",
1171 |             nuclear_tmp,
1172 |         ], capture_output=True, text=True, timeout=600)
1173 |         if nuclear_cmd.returncode == 0 and os.path.exists(nuclear_tmp):
1174 |             os.replace(nuclear_tmp, final_video)
1175 |             recheck = check_av_sync(final_video)
1176 |             print(f"  Nuclear re-encode done. New offset: {recheck:+.3f}s")
1177 |         elif os.path.exists(nuclear_tmp):
1178 |             os.remove(nuclear_tmp)
1179 | 
1180 |     # Final bitrate validation
1181 |     br_result = subprocess.run(
1182 |         ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", final_video],
1183 |         capture_output=True, text=True,
1184 |     )
1185 |     try:
1186 |         br_info = json.loads(br_result.stdout)
1187 |         bitrate = int(br_info.get("format", {}).get("bit_rate", 0))
1188 |         print(f"  Final bitrate: {bitrate / 1_000_000:.1f} Mbps")
1189 |         if bitrate < 3_000_000:
1190 |             logger.error(f"FINAL OUTPUT QUALITY FAILED: {bitrate / 1_000_000:.1f}Mbps < 3Mbps")
1191 |     except Exception:
1192 |         pass
1193 | 
1194 |     timing["12_verify"] = round(time.time() - t0, 2)
1195 |     write_render_context(12, "ok" if passed else "fail",
1196 |                          error="verify failed" if not passed else None)
1197 | 
1198 |     # ── Step 12b: POST-RENDER QC (blocking — P1 Fix 6) ─────────────────
1199 |     print("\n[STEP 12b] POST-RENDER QC...")
1200 |     t0 = time.time()
1201 |     qc_passed = True
1202 |     try:
1203 |         from qc_pipeline import post_render_qc, save_qc_report
1204 |         manifest_json_path = os.path.join(run_dir, "episode_manifest.json")
1205 |         qc_report = post_render_qc(final_video, manifest_json_path)
1206 |         save_qc_report(qc_report, run_dir)
1207 |         qc_passed = qc_report.get("passed", False)
1208 |         print(f"  QC: {'PASS' if qc_passed else 'FAIL'}")
1209 |         for check, val in qc_report.get("checks", {}).items():
1210 |             status = "PASS" if val else ("FAIL" if val is not None else "SKIP")
1211 |             print(f"    [{status}] {check}")
1212 |         if not qc_passed:
1213 |             logger.error("Post-render QC FAILED — render is not broadcast-ready")
1214 |             write_render_context("12b", "fail", error="Post-render QC failed")
1215 |     except Exception as e:
1216 |         logger.warning(f"Post-render QC exception: {e}")
1217 |         qc_passed = False
1218 |     timing["12b_qc"] = round(time.time() - t0, 2)
1219 | 
1220 |     # ── Summary ──────────────────────────────────────────────────────────
1221 |     timing["total"] = round(time.time() - t_pipeline_start, 2)
1222 | 
1223 |     # Video stats
1224 |     r = subprocess.run(
1225 |         ["ffprobe", "-v", "quiet", "-print_format", "json",
1226 |          "-show_format", "-show_streams", final_video],
1227 |         capture_output=True, text=True,
1228 |     )
1229 |     try:
1230 |         info = json.loads(r.stdout)
1231 |         fmt = info.get("format", {})
1232 |         streams = info.get("streams", [])
1233 |         vid = next((s for s in streams if s.get("codec_type") == "video"), {})
1234 |         aud = next((s for s in streams if s.get("codec_type") == "audio"), {})
1235 |         dur = float(fmt.get("duration", 0))
1236 |         sz = int(fmt.get("size", 0)) / 1024 / 1024
1237 |         timing["video_duration"] = round(dur, 1)
1238 |         timing["video_size_mb"] = round(sz, 1)
1239 |     except Exception:
1240 |         vid, aud, dur, sz = {}, {}, 0, 0
1241 | 
1242 |     print("\n" + "=" * 70)
1243 |     print(f"  PULSE CHECK V5 — {'SUCCESS' if passed else 'COMPLETE (warnings)'}")
1244 |     print(f"  Title:    {script.get('episode_title', 'Untitled')}")
1245 |     print(f"  Video:    {vid.get('width')}x{vid.get('height')} {vid.get('codec_name')} {dur:.1f}s")
1246 |     print(f"  Audio:    {aud.get('codec_name')} {aud.get('sample_rate')}Hz")
1247 |     print(f"  Size:     {sz:.1f}MB")
1248 |     print(f"  Clips:    {len(extracted_clips)} real YouTube clips with original audio")
1249 |     print(f"  Shorts:   {len(shorts)}")
1250 |     print(f"  Music:    {'layered' if has_music() else 'none (graceful skip)'}")
1251 | 
1252 |     outputs = {
1253 |         "video": final_video,
1254 |         "shorts": [s for s in shorts],
1255 |         "thumbnail": thumb_path,
1256 |         "chapters": chapters_path,
1257 |         "podcast": podcast_path,
1258 |         "newsletter": newsletter_path,
1259 |         "script": script_path,
1260 |         "selections": sel_path,
1261 |     }
1262 | 
1263 |     print(f"\n  OUTPUT FILES:")
1264 |     for name, path in outputs.items():
1265 |         if isinstance(path, list):
1266 |             for p in path:
1267 |                 exists = "Y" if os.path.exists(p) else "N"
1268 |                 print(f"    [{exists}] {os.path.basename(p)}")
1269 |         else:
1270 |             exists = "Y" if os.path.exists(path) else "N"
1271 |             print(f"    [{exists}] {os.path.basename(path)}")
1272 | 
1273 |     print(f"\n  TIMING:")
1274 |     for step, secs in timing.items():
1275 |         if step not in ("video_duration", "video_size_mb"):
1276 |             print(f"    {step:25s}: {secs:.1f}s")
1277 |     print(f"\n  Output: {run_dir}")
1278 |     print("=" * 70)
1279 | 
1280 |     _write_timing_report(run_dir, timing, t_pipeline_start, success=passed)
1281 | 
1282 |     # Save manifest
1283 |     manifest = {
1284 |         "version": "v5",
1285 |         "episode_title": script.get("episode_title", ""),
1286 |         "btc_price": btc_price,
1287 |         "test_mode": test_mode,
1288 |         "timestamp": time_str,
1289 |         "clips_used": [
1290 |             {"rank": r, "channel": info.get("channel", ""), "video_id": info.get("video_id", "")}
1291 |             for r, info in sorted(extracted_clips.items())
1292 |         ],
1293 |         "outputs": {k: (v if isinstance(v, list) else [v]) for k, v in outputs.items()},
1294 |         "timing": timing,
1295 |         "success": passed,
1296 |     }
1297 |     manifest_path = os.path.join(run_dir, "manifest.json")
1298 |     with open(manifest_path, "w") as f:
1299 |         json.dump(manifest, f, indent=2)
1300 | 
1301 |     # ── Step 13: QUALITY GATE + AUTO-UPLOAD ────────────────────────────────
1302 |     print("\n[STEP 13] QUALITY GATE...")
1303 |     t0 = time.time()
1304 |     quality_score = compute_quality_score(manifest_path, video_path=final_video)
1305 |     print(f"  {format_score_report(quality_score)}")
1306 |     manifest["quality_score"] = quality_score
1307 | 
1308 |     if is_enabled("youtube_auto_upload") and should_upload(quality_score):
1309 |         from utils.youtube_upload import upload_episode as yt_upload, build_description, build_tags
1310 |         # Build YouTube metadata
1311 |         ep_title = script.get("episode_title", "Pulse Check")
1312 |         yt_title = f"Bitcoin Daily Brief — {ts.strftime('%b %d, %Y')} | Protocol Pulse"
1313 |         chapters_text = ""
1314 |         if os.path.exists(chapters_path):
1315 |             with open(chapters_path) as f:
1316 |                 chapters_text = f.read()
1317 |         yt_description = build_description(
1318 |             summary=f"{ep_title}\n\nBTC Price: {btc_price}",
1319 |             chapters_text=chapters_text,
1320 |             clips=clips,
1321 |         )
1322 |         topics = [c.get("channel", "") for c in clips]
1323 |         yt_tags = build_tags(topics)
1324 | 
1325 |         print(f"  Uploading to YouTube (unlisted)...")
1326 |         upload_result = yt_upload(
1327 |             final_video, yt_title, yt_description,
1328 |             tags=yt_tags, thumbnail_path=thumb_path, privacy="unlisted",
1329 |         )
1330 |         print(f"  Upload result: {upload_result.get('status')}")
1331 |         if upload_result.get("url"):
1332 |             print(f"  URL: {upload_result['url']}")
1333 |         manifest["upload_result"] = upload_result
1334 |         if is_enabled("telegram_alerts") and upload_result.get("url"):
1335 |             alert_upload_success(date_str, upload_result["url"])
1336 |     elif quality_score < 85:
1337 |         logger.warning(f"QUALITY HOLD: Score {quality_score} < 85. Episode held for review.")
1338 |         hold_path = os.path.join(run_dir, "HOLD_FOR_REVIEW.txt")
1339 |         with open(hold_path, "w") as f:
1340 |             f.write(f"Quality score: {quality_score}/100\n")
1341 |             f.write(f"Threshold: 85\n")
1342 |             f.write(f"Reason: Below quality threshold\n")
1343 |             f.write(f"Episode: {script.get('episode_title', '')}\n")
1344 |             f.write(f"Video: {final_video}\n")
1345 |         manifest["held_for_review"] = True
1346 |         if is_enabled("telegram_alerts"):
1347 |             alert_quality_hold(date_str, quality_score)
1348 |     else:
1349 |         logger.info("YouTube auto-upload disabled in feature flags")
1350 | 
1351 |     # Write final manifest with quality score
1352 |     with open(manifest_path, "w") as f:
1353 |         json.dump(manifest, f, indent=2)
1354 |     timing["13_quality_gate"] = round(time.time() - t0, 2)
1355 | 
1356 |     # ── Step 14: STAGE BRIEF (post Grade-A render) ─────────────────────────
1357 |     if quality_score >= 85:
1358 |         try:
1359 |             from generate_stage_brief import generate_brief
1360 |             print("\n[STEP 14] GENERATING STAGE BRIEF...")
1361 |             t0 = time.time()
1362 |             brief_path = generate_brief(run_dir)
1363 |             if brief_path:
1364 |                 logger.info(f"Stage brief generated: {brief_path}")
1365 |                 print(f"  Stage brief: {brief_path}")
1366 |                 manifest["stage_brief"] = brief_path
1367 |             else:
1368 |                 logger.warning("Stage brief returned None")
1369 |                 print("  Stage brief: skipped (returned None)")
1370 |             timing["14_stage_brief"] = round(time.time() - t0, 2)
1371 |         except Exception as e:
1372 |             logger.warning(f"Stage brief generation failed (non-fatal): {e}")
1373 |             print(f"  Stage brief failed (non-fatal): {e}")
1374 |             timing["14_stage_brief"] = 0
1375 |     else:
1376 |         logger.info(f"Skipping stage brief — quality score {quality_score} < 85")
1377 | 
1378 |     # Save episode performance data (V17)
1379 |     try:
1380 |         from utils.analytics_store import save_episode_performance
1381 |         perf_data = {
1382 |             "date": ts.strftime("%Y-%m-%d"),
1383 |             "episode_title": script.get("episode_title", ""),
1384 |             "channels_used": [c.get("channel", "") for c in manifest.get("clips_used", [])],
1385 |             "quality_score": manifest.get("quality_score", 0),
1386 |             "clips_count": len(manifest.get("clips_used", [])),
1387 |             "duration_seconds": round(timing.get("video_duration", 0), 1),
1388 |             "bitrate_mbps": round(timing.get("video_size_mb", 0) * 8 / max(timing.get("video_duration", 1), 1), 1),
1389 |             "av_sync_offset": round(final_offset, 3),
1390 |             "music_mood": episode_mood,
1391 |             "test_mode": test_mode,
1392 |         }
1393 |         save_episode_performance(date_str, perf_data)
1394 |     except Exception as e:
1395 |         logger.warning(f"Performance data save failed: {e}")
1396 | 
1397 |     # Telegram success alert
1398 |     if is_enabled("telegram_alerts") and passed:
1399 |         alert_pipeline_success(date_str, quality_score,
1400 |                                timing.get("video_duration", 0), final_video)
1401 | 
1402 |     # ── Step 14: FORMAT MULTIPLIER (V22) ───────────────────────────────────
1403 |     # LAW 1: Only runs AFTER episode is fully rendered and QC-passed.
1404 |     # LAW 2: Runs as a detached subprocess — never blocks or delays the main render.
1405 |     if is_enabled("multi_format_output") and passed:
1406 |         print("\n[STEP 14] FORMAT MULTIPLIER — launching secondary formats...")
1407 |         try:
1408 |             fmt_script = os.path.join(BASE, "format_multiplier.py")
1409 |             fmt_args = [
1410 |                 sys.executable, fmt_script,
1411 |                 "--manifest", manifest_path,
1412 |                 "--video", final_video,
1413 |             ]
1414 |             if test_mode:
1415 |                 fmt_args.append("--test")
1416 |             # Detached subprocess: does not block main pipeline return
1417 |             fmt_proc = subprocess.Popen(
1418 |                 fmt_args,
1419 |                 stdout=open(os.path.join(run_dir, "format_multiplier.log"), "w"),
1420 |                 stderr=subprocess.STDOUT,
1421 |                 start_new_session=True,  # detach from parent process group
1422 |             )
1423 |             print(f"  Format multiplier launched (PID {fmt_proc.pid}) — 5 formats running in background")
1424 |             print(f"  Log: {run_dir}/format_multiplier.log")
1425 |             manifest["format_multiplier_pid"] = fmt_proc.pid
1426 |         except Exception as e:
1427 |             logger.warning(f"Format multiplier launch failed (non-blocking): {e}")
1428 |     elif not is_enabled("multi_format_output"):
1429 |         logger.info("multi_format_output feature flag is disabled — skipping format multiplier")
1430 | 
1431 |     # ── Post-render health check + Resend notification ─────────────────────
1432 |     hc_passed = True  # default for test mode; overridden below for production
1433 |     if not test_mode:
1434 |         hc_passed, hc_errors = _post_render_health_check(final_video)
1435 |         dur_s = timing.get("video_duration", 0)
1436 |         size_mb = timing.get("video_size_mb", 0)
1437 |         dur_min = int(dur_s // 60)
1438 |         dur_sec = int(dur_s % 60)
1439 |         if passed and hc_passed:
1440 |             _send_resend_alert(
1441 |                 f"Pulse Check rendered: {dur_min}m {dur_sec}s, {size_mb:.0f}MB",
1442 |                 f"Episode: {script.get('episode_title', 'Untitled')}\n"
1443 |                 f"Duration: {dur_min}m {dur_sec}s\n"
1444 |                 f"Size: {size_mb:.1f}MB\n"
1445 |                 f"Quality: {quality_score}/100\n"
1446 |                 f"Video: {final_video}",
1447 |             )
1448 |         else:
1449 |             _send_resend_alert(
1450 |                 "ALERT: Pulse Check render issues detected",
1451 |                 f"Episode: {script.get('episode_title', 'Untitled')}\n"
1452 |                 f"Pipeline passed: {passed}\n"
1453 |                 f"Health check passed: {hc_passed}\n"
1454 |                 f"Errors: {hc_errors}\n"
1455 |                 f"Video: {final_video}",
1456 |             )
1457 | 
1458 |     success = passed and hc_passed and qc_passed
1459 |     if success:
1460 |         _clear_checkpoint()  # P0 Fix 3: clear checkpoint on success
1461 |     return success
1462 | 
1463 | 
1464 | def _write_timing_report(run_dir: str, timing: dict, t_start: float, success: bool):
1465 |     report_path = os.path.join(run_dir, "timing_report.txt")
1466 |     ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
1467 |     lines = [
1468 |         "PULSE CHECK V5 — Timing Report",
1469 |         f"Generated: {ts}",
1470 |         f"Status: {'SUCCESS' if success else 'FAILED'}",
1471 |         "",
1472 |         "STEP TIMINGS:",
1473 |     ]
1474 |     for step, val in timing.items():
1475 |         if step in ("video_duration", "video_size_mb"):
1476 |             continue
1477 |         lines.append(f"  {step:<25}: {val:.1f}s")
1478 |     lines += [
1479 |         "",
1480 |         "OUTPUT STATS:",
1481 |         f"  video_duration_s     : {timing.get('video_duration', 'N/A')}",
1482 |         f"  video_size_mb        : {timing.get('video_size_mb', 'N/A')}",
1483 |         f"  total_wall_time_s    : {time.time() - t_start:.1f}",
1484 |     ]
1485 |     with open(report_path, "w") as f:
1486 |         f.write("\n".join(lines) + "\n")
1487 | 
1488 | 
1489 | def main():
1490 |     parser = argparse.ArgumentParser(
1491 |         description="Pulse Check V5 — Clip-First Video Producer")
1492 |     parser.add_argument("--test", action="store_true",
1493 |                         help="Test mode: fewer clips, truncated, test output dir")
1494 |     parser.add_argument("--skip-scan", action="store_true",
1495 |                         help="Skip channel scanning, use cached transcripts")
1496 |     parser.add_argument("--fast-test", action="store_true",
1497 |                         help="Fast test: no API calls (Claude/scan), hardcoded script, <3 min render")
1498 |     args = parser.parse_args()
1499 | 
1500 |     # P0 Fix 1: flock process lock — prevent duplicate producers
1501 |     lock_file = open("/tmp/daily_producer.lock", "w")
1502 |     try:
1503 |         fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
1504 |     except IOError:
1505 |         logger.error("Another daily_producer is already running. Exiting.")
1506 |         sys.exit(1)
1507 | 
1508 |     success = run_pipeline(test_mode=args.test, skip_scan=args.skip_scan,
1509 |                            fast_test=args.fast_test)
1510 | 
1511 |     fcntl.flock(lock_file, fcntl.LOCK_UN)
1512 |     # ── Post-render: fire tweet machine from morning brief ──────────────
1513 |     try:
1514 |         import subprocess as _sp
1515 |         _sp.Popen(["python3", "/home/ultron/protocol_pulse/services/tweet_machine.py"],
1516 |                   stdout=open("/home/ultron/protocol_pulse/logs/tweet_machine.log", "a"),
1517 |                   stderr=subprocess.STDOUT)
1518 |         print("  Tweet machine: fired (async)")
1519 |     except Exception as _te:
1520 |         print(f"  Tweet machine: skipped ({_te})")
1521 |     sys.exit(0 if success else 1)
1522 | 
1523 | 
1524 | if __name__ == "__main__":
1525 |     main()
1526 | 
```

### File: overnight_render_loop.py (859 lines)
```
   1 | #!/usr/bin/env python3
   2 | """
   3 | overnight_render_loop.py - Autonomous video engine perfection loop.
   4 | Max 8 iterations, max 6 hours. Each: render -> forensics -> Gemini grade -> CC fix -> repeat.
   5 | Grade A = stop and lock WINNER_RECIPE.json.
   6 | 
   7 | Production modes:
   8 |   python3 overnight_render_loop.py              # single cycle (for cron)
   9 |   python3 overnight_render_loop.py --daemon     # continuous loop, runs at 08:00 ET daily
  10 |   python3 overnight_render_loop.py --dry-run    # startup checks only, no render
  11 |   python3 overnight_render_loop.py --help       # show args
  12 | 
  13 | Cron entry:
  14 |   0 12 * * * cd /home/ultron/protocol_pulse && python3 overnight_render_loop.py >> /tmp/overnight_loop.log 2>&1
  15 | """
  16 | import sys; sys.dont_write_bytecode=True
  17 | import os, sys, json, subprocess, time, re, urllib.request, argparse, logging, shutil, tempfile
  18 | import html as _html
  19 | import threading
  20 | from datetime import datetime, timezone, timedelta
  21 | from pathlib import Path
  22 | 
  23 | # ── Rate limiter (audit P0-U1) ────────────────────────────────
  24 | _rate_lock = threading.Lock()
  25 | _rate_calls = []  # list of timestamps
  26 | RATE_LIMIT_CALLS_PER_MINUTE = int(os.getenv("RATE_LIMIT_CALLS_PER_MINUTE", "20"))
  27 | 
  28 | 
  29 | def _rate_limit_wait():
  30 |     """Token-bucket rate limiter for external API calls. Blocks if limit exceeded."""
  31 |     with _rate_lock:
  32 |         now = time.time()
  33 |         _rate_calls[:] = [t for t in _rate_calls if now - t < 60]
  34 |         if len(_rate_calls) >= RATE_LIMIT_CALLS_PER_MINUTE:
  35 |             wait = 60 - (now - _rate_calls[0])
  36 |             if wait > 0:
  37 |                 logging.getLogger('overnight_loop').warning(
  38 |                     f"Rate limit hit ({RATE_LIMIT_CALLS_PER_MINUTE}/min) — waiting {wait:.1f}s"
  39 |                 )
  40 |                 time.sleep(wait)
  41 |         _rate_calls.append(time.time())
  42 | 
  43 | BASE = os.path.dirname(os.path.abspath(__file__))
  44 | PIPELINE = os.path.join(BASE, 'video_pipeline_v3')
  45 | ENV_FILE = os.path.join(BASE, '.env')
  46 | LOG = os.path.join(PIPELINE, 'logs', 'overnight_loop.log')
  47 | RECIPE_FILE = os.path.join(PIPELINE, 'logs', 'WINNER_RECIPE.json')
  48 | HEARTBEAT_FILE = os.path.join(BASE, 'logs', 'loop_heartbeat.json')
  49 | ELEVENLABS_QUOTA_SENTINEL = os.path.join(BASE, 'logs', 'elevenlabs_quota_exhausted')
  50 | TTS_SCRIPT = os.path.join(PIPELINE, 'tts_local.py')
  51 | FORENSICS_TIMEOUT = 600  # 10-minute hard timeout for entire forensics
  52 | MAX_ITERATIONS = 8
  53 | MAX_HOURS = 6
  54 | RETRY_WAIT_SECONDS = 1800  # 30 minutes
  55 | MAX_ATTEMPTS_PER_CYCLE = 2
  56 | CONSECUTIVE_GRADE_FAILURES_THRESHOLD = int(os.getenv("CONSECUTIVE_GRADE_FAILURES_THRESHOLD", "3"))
  57 | CONSECUTIVE_RENDER_ABSENT_THRESHOLD = int(os.getenv("CONSECUTIVE_RENDER_ABSENT_THRESHOLD", "3"))
  58 | 
  59 | # Required env vars — fail fast if missing (audit P1-X5)
  60 | REQUIRED_ENV_VARS = ["GEMINI_API_KEY"]  # others are soft-checked at startup
  61 | 
  62 | os.makedirs(os.path.join(PIPELINE, 'logs'), exist_ok=True)
  63 | os.makedirs(os.path.join(BASE, 'logs'), exist_ok=True)
  64 | 
  65 | # ── Logging ───────────────────────────────────────────────────────
  66 | logger = logging.getLogger('overnight_loop')
  67 | if not logger.handlers:
  68 |     logger.setLevel(logging.DEBUG)
  69 |     _fmt = logging.Formatter('[%(asctime)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
  70 |     _sh = logging.StreamHandler(sys.stdout)
  71 |     _sh.setFormatter(_fmt)
  72 |     logger.addHandler(_sh)
  73 |     _fh = logging.FileHandler(LOG)
  74 |     _fh.setFormatter(_fmt)
  75 |     logger.addHandler(_fh)
  76 | 
  77 | 
  78 | def log(msg):
  79 |     """Backward-compat wrapper."""
  80 |     logger.info(msg)
  81 | 
  82 | 
  83 | def load_env():
  84 |     env = os.environ.copy()
  85 |     env['CUDA_VISIBLE_DEVICES'] = '0'  # Pin pipeline to GPU 0 -- avatar_server owns GPU 1
  86 |     try:
  87 |         with open(ENV_FILE) as f:
  88 |             for line in f:
  89 |                 l = line.strip()
  90 |                 if l and not l.startswith('#') and '=' in l:
  91 |                     k, _, v = l.partition('=')
  92 |                     k = k.strip(); v = v.strip().strip("'").strip('"')
  93 |                     if k: env[k] = v
  94 |     except FileNotFoundError:
  95 |         log(f"CRITICAL: .env file not found at {ENV_FILE}")
  96 |     except Exception as e:
  97 |         log(f"WARNING: .env load failed: {e}")
  98 |     # Validate required env vars (audit P1-X5)
  99 |     missing = [k for k in REQUIRED_ENV_VARS if not env.get(k, '').strip()]
 100 |     if missing:
 101 |         log(f"CRITICAL: Required env vars missing after .env load: {missing}")
 102 |     return env
 103 | 
 104 | 
 105 | def run(cmd, timeout=7200, env=None):
 106 |     try:
 107 |         return subprocess.run(cmd, shell=True, capture_output=True, text=True,
 108 |                              timeout=timeout, env=env or load_env(), cwd=PIPELINE)
 109 |     except subprocess.TimeoutExpired:
 110 |         log(f"TIMEOUT after {timeout}s: {str(cmd)[:80]}")
 111 |         r = subprocess.CompletedProcess(cmd, returncode=-1)
 112 |         r.stdout = ""
 113 |         r.stderr = f"TIMEOUT after {timeout}s"
 114 |         return r
 115 |     except Exception as e:
 116 |         log(f"run() error: {e} cmd={str(cmd)[:80]}")
 117 |         r = subprocess.CompletedProcess(cmd, returncode=-1)
 118 |         r.stdout = ""
 119 |         r.stderr = str(e)
 120 |         return r
 121 | 
 122 | 
 123 | # ── Startup checks ────────────────────────────────────────────────
 124 | def startup_checks():
 125 |     """Verify environment before any render. Returns True if all pass."""
 126 |     ok = True
 127 | 
 128 |     # FFmpeg available
 129 |     try:
 130 |         r = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=10)
 131 |         if r.returncode != 0:
 132 |             log("STARTUP FAIL: ffmpeg returned non-zero")
 133 |             ok = False
 134 |         else:
 135 |             ver = r.stdout.split('\n')[0] if r.stdout else '?'
 136 |             log(f"FFmpeg: {ver}")
 137 |     except FileNotFoundError:
 138 |         log("STARTUP FAIL: ffmpeg not found in PATH")
 139 |         ok = False
 140 |     except Exception as e:
 141 |         log(f"STARTUP FAIL: ffmpeg check error: {e}")
 142 |         ok = False
 143 | 
 144 |     # tmux + claude binary validation (audit U2)
 145 |     for binary in ['tmux', 'claude']:
 146 |         if not shutil.which(binary):
 147 |             log(f"STARTUP FAIL: {binary} not found in PATH")
 148 |             ok = False
 149 |         else:
 150 |             log(f"{binary}: found")
 151 | 
 152 |     # Gemini API key check (audit UI-7)
 153 |     env = load_env()
 154 |     if not env.get('GEMINI_API_KEY', '').strip():
 155 |         log("STARTUP FAIL: GEMINI_API_KEY not set")
 156 |         ok = False
 157 |     else:
 158 |         log("GEMINI_API_KEY: present")
 159 | 
 160 |     # Python path includes pipeline
 161 |     if PIPELINE not in sys.path:
 162 |         sys.path.insert(0, PIPELINE)
 163 |     log(f"Pipeline dir: {PIPELINE} (exists={os.path.isdir(PIPELINE)})")
 164 |     if not os.path.isdir(PIPELINE):
 165 |         log("STARTUP FAIL: video_pipeline_v3 directory missing")
 166 |         ok = False
 167 | 
 168 |     # Output directory writable
 169 |     out_dir = os.path.join(PIPELINE, 'output')
 170 |     os.makedirs(out_dir, exist_ok=True)
 171 |     test_file = os.path.join(out_dir, '.write_test')
 172 |     try:
 173 |         with open(test_file, 'w') as f:
 174 |             f.write('ok')
 175 |         os.remove(test_file)
 176 |         log(f"Output dir writable: {out_dir}")
 177 |     except Exception as e:
 178 |         log(f"STARTUP FAIL: output dir not writable: {e}")
 179 |         ok = False
 180 | 
 181 |     # TTS provider check — TTS_PROVIDER env var takes ABSOLUTE precedence (FIX: TTS LOCK)
 182 |     tts_provider_env = env.get('TTS_PROVIDER', '').lower().strip()
 183 |     local_tts = os.path.exists(TTS_SCRIPT)
 184 |     elevenlabs_key = bool(env.get('ELEVENLABS_API_KEY', '').strip())
 185 |     quota_exhausted = os.path.exists(ELEVENLABS_QUOTA_SENTINEL)
 186 | 
 187 |     if tts_provider_env == 'elevenlabs':
 188 |         # Explicit env override — NEVER fall back to local even if tts_local.py exists
 189 |         if elevenlabs_key and not quota_exhausted:
 190 |             log("TTS provider: ElevenLabs (TTS_PROVIDER=elevenlabs, env var override)")
 191 |         elif elevenlabs_key and quota_exhausted:
 192 |             log("WARNING: TTS_PROVIDER=elevenlabs but quota sentinel exists")
 193 |         else:
 194 |             log("STARTUP FAIL: TTS_PROVIDER=elevenlabs but no ELEVENLABS_API_KEY")
 195 |             ok = False
 196 |     elif local_tts:
 197 |         log("TTS provider: LOCAL (tts_local.py found)")
 198 |     elif elevenlabs_key and not quota_exhausted:
 199 |         log("TTS provider: ElevenLabs (API key present)")
 200 |     elif elevenlabs_key and quota_exhausted:
 201 |         log("WARNING: ElevenLabs key present but quota sentinel exists")
 202 |     else:
 203 |         log("WARNING: No TTS provider found (no local TTS, no ElevenLabs key)")
 204 | 
 205 |     if not local_tts and not elevenlabs_key:
 206 |         log("STARTUP FAIL: No TTS provider available")
 207 |         ok = False
 208 | 
 209 |     return ok
 210 | 
 211 | 
 212 | # ── Heartbeat ─────────────────────────────────────────────────────
 213 | _total_episodes = 0
 214 | _consecutive_failures = 0
 215 | _counter_lock = threading.Lock()  # Guard global counters (audit P1-M1)
 216 | 
 217 | 
 218 | def write_heartbeat(verdict, duration_s):
 219 |     """Write heartbeat JSON atomically after every cycle."""
 220 |     global _total_episodes, _consecutive_failures
 221 |     with _counter_lock:
 222 |         if verdict == "PASS":
 223 |             _total_episodes += 1
 224 |             _consecutive_failures = 0
 225 |         elif verdict == "ERROR":
 226 |             _consecutive_failures += 1
 227 |         elif verdict == "HOLD":
 228 |             _consecutive_failures += 1
 229 |         elif verdict == "DEGRADED":
 230 |             _total_episodes += 1
 231 |             _consecutive_failures = 0
 232 | 
 233 |     heartbeat = {
 234 |         "last_run": datetime.now(timezone.utc).isoformat(),
 235 |         "last_verdict": verdict,
 236 |         "last_duration": round(duration_s, 1),
 237 |         "total_episodes": _total_episodes,
 238 |         "consecutive_failures": _consecutive_failures,
 239 |     }
 240 |     try:
 241 |         # Atomic write via temp file + rename (audit UI-6)
 242 |         tmp_path = HEARTBEAT_FILE + '.tmp'
 243 |         with open(tmp_path, 'w') as f:
 244 |             json.dump(heartbeat, f, indent=2)
 245 |         os.replace(tmp_path, HEARTBEAT_FILE)
 246 |         log(f"Heartbeat written: {verdict} | failures={_consecutive_failures}")
 247 |     except Exception as e:
 248 |         log(f"WARNING: heartbeat write failed: {e}")
 249 | 
 250 |     # Telegram alert on 3+ consecutive failures
 251 |     if _consecutive_failures >= 3:
 252 |         send_telegram_alert(
 253 |             f"Protocol Pulse loop: {_consecutive_failures} consecutive failures\n"
 254 |             f"Last verdict: {verdict}\n"
 255 |             f"Time: {heartbeat['last_run']}"
 256 |         )
 257 | 
 258 | 
 259 | def send_telegram_alert(message):
 260 |     """Send alert via Telegram if bot token + chat ID are configured."""
 261 |     env = load_env()
 262 |     token = env.get('TELEGRAM_BOT_TOKEN', '').strip()
 263 |     chat_id = env.get('TELEGRAM_CHAT_ID', '').strip()
 264 |     if not token or not chat_id:
 265 |         log("Telegram alert skipped: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")
 266 |         return
 267 |     try:
 268 |         url = f"https://api.telegram.org/bot{token}/sendMessage"
 269 |         # Use plain text to avoid HTML injection from dynamic content (audit UI-3)
 270 |         payload = json.dumps({"chat_id": chat_id, "text": message}).encode()
 271 |         req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
 272 |         with urllib.request.urlopen(req, timeout=15) as r:
 273 |             log(f"Telegram alert sent (status {r.status})")
 274 |     except Exception as e:
 275 |         log(f"Telegram alert failed: {e}")
 276 | 
 277 | 
 278 | # ── TTS provider awareness ────────────────────────────────────────
 279 | def check_tts_ready():
 280 |     """Check TTS availability before render. Returns (ready, provider_name).
 281 |     TTS_PROVIDER env var takes ABSOLUTE precedence — never fall back to local
 282 |     if TTS_PROVIDER=elevenlabs (FIX: TTS LOCK).
 283 |     """
 284 |     env = load_env()
 285 |     tts_provider_env = env.get('TTS_PROVIDER', '').lower().strip()
 286 | 
 287 |     # TTS_PROVIDER=elevenlabs takes absolute precedence over tts_local.py on disk
 288 |     if tts_provider_env == 'elevenlabs':
 289 |         if not env.get('ELEVENLABS_API_KEY', '').strip():
 290 |             return False, "none (TTS_PROVIDER=elevenlabs but no API key)"
 291 |         if os.path.exists(ELEVENLABS_QUOTA_SENTINEL):
 292 |             log("ElevenLabs quota sentinel exists — skipping render")
 293 |             return False, "elevenlabs (quota exhausted)"
 294 |         return True, "ElevenLabs (env override)"
 295 | 
 296 |     # Default: check local first, then ElevenLabs
 297 |     local_tts = os.path.exists(TTS_SCRIPT)
 298 |     if local_tts:
 299 |         return True, "local (Kokoro/F5-TTS)"
 300 | 
 301 |     if not env.get('ELEVENLABS_API_KEY', '').strip():
 302 |         return False, "none"
 303 | 
 304 |     if os.path.exists(ELEVENLABS_QUOTA_SENTINEL):
 305 |         log("ElevenLabs quota sentinel exists — skipping render")
 306 |         return False, "elevenlabs (quota exhausted)"
 307 | 
 308 |     return True, "ElevenLabs"
 309 | 
 310 | 
 311 | def gemini_call(prompt, max_tokens=8000):
 312 |     """Call Gemini API with retry + exponential backoff (audit U4)."""
 313 |     env = load_env()
 314 |     key = env.get('GEMINI_API_KEY', '')
 315 |     url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent?key={key}'
 316 |     payload = {'contents': [{'parts': [{'text': prompt}]}],
 317 |                'generationConfig': {'maxOutputTokens': max_tokens, 'temperature': 0.05}}
 318 |     data = json.dumps(payload).encode()
 319 | 
 320 |     backoff = [5, 15, 45]
 321 |     last_err = None
 322 |     for attempt in range(3):
 323 |         _rate_limit_wait()  # audit P0-U1: rate limit external API calls
 324 |         try:
 325 |             req = urllib.request.Request(url, data=data,
 326 |                                         headers={'Content-Type': 'application/json'})
 327 |             with urllib.request.urlopen(req, timeout=120) as r:
 328 |                 d = json.loads(r.read())
 329 |                 parts = d['candidates'][0]['content'].get('parts', [])
 330 |                 return next((p['text'] for p in parts if 'text' in p), None)
 331 |         except (urllib.error.HTTPError, urllib.error.URLError, KeyError, json.JSONDecodeError) as e:
 332 |             last_err = e
 333 |             if attempt < 2:
 334 |                 wait = backoff[attempt]
 335 |                 log(f"Gemini API attempt {attempt+1} failed ({type(e).__name__}: {e}), retrying in {wait}s...")
 336 |                 time.sleep(wait)
 337 |             else:
 338 |                 log(f"Gemini API all 3 attempts failed. Last error: {e}")
 339 |         except Exception as e:
 340 |             last_err = e
 341 |             log(f"Gemini API unexpected error: {e}")
 342 |             break
 343 |     return None
 344 | 
 345 | 
 346 | def run_render(iteration):
 347 |     log(f"RENDER START iteration {iteration}")
 348 |     run("rm -rf tts_cache/ && mkdir -p tts_cache/")
 349 |     log("TTS cache wiped")
 350 |     env = load_env()
 351 |     render_start = time.time()
 352 |     r = run("python3 daily_producer.py --skip-scan", timeout=14400, env=env)
 353 |     log(f"Render exit: {r.returncode}")
 354 |     import glob
 355 |     today = datetime.now().strftime('%Y-%m-%d')
 356 |     candidates = []
 357 |     for pat in [f'output/{today}/*.mp4']:  # today-only — no stale fallback
 358 |         for f in glob.glob(os.path.join(PIPELINE, pat)):
 359 |             if any(x in f for x in ['.bgl_audio', '.intro_mus', '.concat_raw', '.music_mixed', '.whoosh', '.norm']):
 360 |                 continue
 361 |             if not any(x in f for x in ['music_mixed', 'concat_raw', '.norm', 'whoosh']):
 362 |                 # Only accept files produced after render started (audit U3)
 363 |                 if os.path.getmtime(f) >= render_start:
 364 |                     candidates.append((os.path.getmtime(f), f))
 365 |     candidates.sort(reverse=True)
 366 |     out = candidates[0][1] if candidates else None
 367 |     if out:
 368 |         log(f"Output: {out} ({os.path.getsize(out)//1048576}MB)")
 369 |         # Validate render output with ffprobe (audit P2-X3)
 370 |         try:
 371 |             probe = subprocess.run(
 372 |                 ["ffprobe", "-v", "error", "-show_entries", "format=duration",
 373 |                  "-of", "default=noprint_wrappers=1:nokey=1", out],
 374 |                 capture_output=True, text=True, timeout=30
 375 |             )
 376 |             if probe.returncode != 0 or not probe.stdout.strip():
 377 |                 log(f"WARNING: ffprobe rejected output file — corrupt or invalid: {out}")
 378 |                 out = None
 379 |         except Exception as e:
 380 |             log(f"WARNING: ffprobe validation failed: {e}")
 381 |     else:
 382 |         log("FATAL: no output file produced by this render")
 383 |     return out, r.stdout + r.stderr
 384 | 
 385 | 
 386 | def _run_forensics_inner(video):
 387 |     """Inner forensics logic — called within a thread timeout wrapper."""
 388 |     res = {}
 389 |     r = run(f'ffprobe -v quiet -print_format json -show_format -show_streams "{video}"')
 390 |     try:
 391 |         p = json.loads(r.stdout)
 392 |         fmt = p.get('format', {}); streams = p.get('streams', [])
 393 |         res['duration'] = float(fmt.get('duration', 0))
 394 |         res['filesize_mb'] = int(fmt.get('size', 0)) / 1048576
 395 |         v = next((s for s in streams if s.get('codec_type') == 'video'), {})
 396 |         a = next((s for s in streams if s.get('codec_type') == 'audio'), {})
 397 |         res['width'] = v.get('width', 0); res['height'] = v.get('height', 0)
 398 |         fps_str = v.get('r_frame_rate', '0/1')
 399 |         if '/' in fps_str:
 400 |             num, den = fps_str.split('/', 1)
 401 |             res['fps'] = float(num) / float(den) if float(den) != 0 else 0
 402 |         else:
 403 |             res['fps'] = float(fps_str) if fps_str else 0
 404 |         res['vcodec'] = v.get('codec_name', '?'); res['acodec'] = a.get('codec_name', '?')
 405 |     except Exception as e:
 406 |         log(f"WARNING: ffprobe parse error: {e}")
 407 |     r = run(f'ffmpeg -i "{video}" -vf "blackdetect=d=0.3:pix_th=0.10" -an -f null - 2>&1', timeout=300)
 408 |     segs = re.findall(r'black_start:([\d.]+).*?black_end:([\d.]+).*?black_duration:([\d.]+)', r.stderr+r.stdout)
 409 |     dur = res.get('duration', 0)
 410 |     res['black_mid_count'] = len([(s,e,d) for s,e,d in segs if float(s)>2 and float(e)<dur-2])
 411 |     r = run(f'ffmpeg -i "{video}" -af "ebur128=peak=true" -f null - 2>&1', timeout=120)
 412 |     out = r.stderr + r.stdout
 413 |     im = re.search(r'I:\s*([-\d.]+)\s*LUFS', out)
 414 |     tp = re.search(r'True peak.*?([-\d.]+)\s*dBFS', out)
 415 |     res['integrated_lufs'] = float(im.group(1)) if im else None
 416 |     res['true_peak_dbfs'] = float(tp.group(1)) if tp else None
 417 |     # FIX: freeze threshold n=0.003 (was 0.001 — too sensitive for bg_loop transitions)
 418 |     r = run(f'ffmpeg -i "{video}" -vf "freezedetect=n=0.003:d=1.0" -an -f null - 2>&1', timeout=300)
 419 |     res['freeze_count'] = len(re.findall(r'freeze_start', r.stderr+r.stdout))
 420 | 
 421 |     # TTS ARTIFACT CHECK — run in isolated subprocess with hard 45s timeout
 422 |     # Prevents WhisperModel from blocking forensics pipeline
 423 |     tts_artifacts = []
 424 |     tmp_path = None
 425 |     try:
 426 |         tmp_fd, tmp_path = tempfile.mkstemp(suffix='.wav')
 427 |         os.close(tmp_fd)
 428 |         subprocess.run(['ffmpeg', '-y', '-i', video, '-t', '60', '-ar', '16000',
 429 |                  '-ac', '1', tmp_path], capture_output=True, timeout=30)
 430 |         checker = (
 431 |             "import sys, json\n"
 432 |             "from faster_whisper import WhisperModel\n"
 433 |             "model = WhisperModel('tiny', device='cpu', compute_type='int8')\n"
 434 |             "segs, _ = model.transcribe(sys.argv[1], language='en')\n"
 435 |             "t = ' '.join(s.text for s in segs).lower()\n"
 436 |             "bad = ['pause','breath','emphasis','break colon','slash','open bracket','close bracket']\n"
 437 |             "print(json.dumps([w for w in bad if w in t]))\n"
 438 |         )
 439 |         r = subprocess.run(['python3', '-c', checker, tmp_path],
 440 |                     capture_output=True, text=True, timeout=45)
 441 |         if r.returncode == 0 and r.stdout.strip():
 442 |             tts_artifacts = json.loads(r.stdout.strip())
 443 |     except Exception as _e:
 444 |         log(f"TTS artifact check skipped: {_e}")
 445 |     finally:
 446 |         # Guaranteed cleanup (audit M3)
 447 |         if tmp_path and os.path.exists(tmp_path):
 448 |             try:
 449 |                 os.unlink(tmp_path)
 450 |             except OSError:
 451 |                 pass
 452 |     res['tts_artifacts'] = tts_artifacts
 453 |     if tts_artifacts:
 454 |         log(f"TTS ARTIFACT ALERT: narrator reading markers aloud: {tts_artifacts}")
 455 |     log(f"Forensics: {res.get('duration',0):.0f}s {res.get('width')}x{res.get('height')} "
 456 |         f"LUFS={res.get('integrated_lufs')} TP={res.get('true_peak_dbfs')} "
 457 |         f"black={res.get('black_mid_count')} freeze={res.get('freeze_count')}")
 458 |     return res
 459 | 
 460 | 
 461 | def run_forensics(video):
 462 |     """Run forensics with a 10-minute hard thread timeout (task issue #1).
 463 |     If forensics hangs, returns {} so the loop can continue to grading."""
 464 |     log("Running forensics...")
 465 |     result_holder = [None]
 466 |     error_holder = [None]
 467 | 
 468 |     def _target():
 469 |         try:
 470 |             result_holder[0] = _run_forensics_inner(video)
 471 |         except Exception as e:
 472 |             error_holder[0] = e
 473 | 
 474 |     t = threading.Thread(target=_target, daemon=True)
 475 |     t.start()
 476 |     t.join(timeout=FORENSICS_TIMEOUT)
 477 | 
 478 |     if t.is_alive():
 479 |         log(f"WARNING: Forensics exceeded {FORENSICS_TIMEOUT}s hard timeout — returning empty result")
 480 |         return {}
 481 | 
 482 |     if error_holder[0]:
 483 |         log(f"WARNING: Forensics thread raised: {error_holder[0]}")
 484 |         return {}
 485 | 
 486 |     return result_holder[0] or {}
 487 | 
 488 | 
 489 | def grade_with_gemini(video, forensics, render_log):
 490 |     log("Calling Gemini for 24-dimension grade...")
 491 |     prompt = f"""Grade this Protocol Pulse Bitcoin show episode across 24 dimensions.
 492 | Only award Grade A if you would genuinely be proud to publish it as world-class Bitcoin media.
 493 | 
 494 | FORENSICS:
 495 | - Duration: {forensics.get('duration',0):.1f}s ({forensics.get('duration',0)/60:.1f}min)
 496 | - Resolution: {forensics.get('width')}x{forensics.get('height')} @ {forensics.get('fps',0):.1f}fps
 497 | - Codec: {forensics.get('vcodec')} + {forensics.get('acodec')}
 498 | - Loudness: {forensics.get('integrated_lufs')} LUFS (target -16 to -14)
 499 | - True Peak: {forensics.get('true_peak_dbfs')} dBFS (must be <= -1.0)
 500 | - Black frames (mid): {forensics.get('black_mid_count',0)} (0 = perfect)
 501 | - Freeze frames: {forensics.get('freeze_count',0)} (0 = perfect)
 502 | 
 503 | RENDER LOG (last 200 lines):
 504 | {chr(10).join(render_log.splitlines()[-200:])}
 505 | 
 506 | RUBRIC (24 dimensions, Grade A = score >= 88, zero critical failures):
 507 | Technical (40%): duration, resolution, fps, loudness, true_peak, black_frames, silence, freezes, codec, file_integrity
 508 | Content (35%): clip_relevance, script_quality, cold_open, narrative_arc, host_authenticity, episode_title, no_filler, timeliness
 509 | Production (25%): music_mix, transitions, visual_polish, no_artifacts, audio_quality, pacing
 510 | 
 511 | Respond ONLY with raw JSON (no fences):
 512 | {{"grade":"A|B|C|D|F","overall_score":0-100,"broadcast_ready":true|false,
 513 | "dimensions":{{"duration_check":{{"score":0-10,"note":""}},"resolution_check":{{"score":0-10,"note":""}},"framerate_check":{{"score":0-10,"note":""}},"loudness_check":{{"score":0-10,"note":""}},"true_peak_check":{{"score":0-10,"note":""}},"black_frames_check":{{"score":0-10,"note":""}},"silence_check":{{"score":0-10,"note":""}},"freeze_check":{{"score":0-10,"note":""}},"codec_check":{{"score":0-10,"note":""}},"file_integrity_check":{{"score":0-10,"note":""}},"clip_relevance":{{"score":0-10,"note":""}},"script_quality":{{"score":0-10,"note":""}},"cold_open_hook":{{"score":0-10,"note":""}},"narrative_arc":{{"score":0-10,"note":""}},"host_authenticity":{{"score":0-10,"note":""}},"episode_title":{{"score":0-10,"note":""}},"no_filler":{{"score":0-10,"note":""}},"timeliness":{{"score":0-10,"note":""}},"music_mix":{{"score":0-10,"note":""}},"transitions":{{"score":0-10,"note":""}},"visual_polish":{{"score":0-10,"note":""}},"no_artifacts":{{"score":0-10,"note":""}},"audio_quality":{{"score":0-10,"note":""}},"pacing":{{"score":0-10,"note":""}}}},
 514 | "critical_failures":[],"warnings":[],"strengths":[],"targeted_fix_instructions":"Precise instructions for CC session to fix only failing dimensions - file, function, lines.",
 515 | "verdict":"One punchy sentence"}}"""
 516 |     text = gemini_call(prompt, 8000)
 517 |     if not text: return None
 518 |     clean = text.strip()
 519 |     for fence in ['```json', '```']:
 520 |         if fence in clean:
 521 |             clean = clean.split(fence)[1].split('```')[0].strip()
 522 |     try: return json.loads(clean)
 523 |     except json.JSONDecodeError as e: log(f"JSON parse fail: {e} — {clean[:200]}"); return None
 524 | 
 525 | 
 526 | def fire_cc_fix(iteration, grade_result):
 527 |     """P0 Fix 2: No more CC self-healing from the render loop.
 528 |     CLASS A/B: log failure details for Qwen watchdog to handle.
 529 |     CLASS C: log + Telegram alert + stop iteration. Let the watchdog decide.
 530 |     """
 531 |     failures = grade_result.get('critical_failures', [])
 532 |     dims = grade_result.get('dimensions', {})
 533 |     failing = [(k, v['score'], v.get('note','')) for k,v in dims.items()
 534 |                if isinstance(v.get('score'), int) and v['score'] < 7]
 535 |     failing.sort(key=lambda x: x[1])
 536 |     grade = grade_result.get('grade', 'F')
 537 |     score = grade_result.get('overall_score', 0)
 538 |     verdict = grade_result.get('verdict', '')
 539 | 
 540 |     # Write fix spec for the watchdog (Qwen) to pick up
 541 |     pf = os.path.join(PIPELINE, f'logs/cc_fix_iter{iteration}.md')
 542 |     spec = (
 543 |         f"# PIPELINE FIX NEEDED - ITERATION {iteration} - GRADE {grade} ({score}/100)\n"
 544 |         f"VERDICT: {verdict}\n"
 545 |         f"CRITICAL FAILURES: {chr(10).join(f'- {f}' for f in failures) or 'None'}\n"
 546 |         f"FAILING DIMS (<7/10): {chr(10).join(f'- {k}: {s}/10 - {n[:80]}' for k,s,n in failing[:8]) or 'None'}\n"
 547 |         f"FIX INSTRUCTIONS: {grade_result.get('targeted_fix_instructions','')}\n"
 548 |     )
 549 |     with open(pf, 'w') as f:
 550 |         f.write(spec)
 551 |     log(f"Fix spec written to {pf} — watchdog will handle repair")
 552 | 
 553 |     # Telegram alert so human/watchdog can decide
 554 |     send_telegram_alert(
 555 |         f"Pulse Check iter {iteration}: Grade {grade} ({score}/100)\n"
 556 |         f"Verdict: {verdict}\n"
 557 |         f"Failing: {', '.join(k for k,s,n in failing[:5])}\n"
 558 |         f"Fix spec: {pf}\n"
 559 |         f"Waiting for watchdog or manual fix."
 560 |     )
 561 | 
 562 |     # Brief pause before next iteration — no CC session spawn
 563 |     time.sleep(30)
 564 | 
 565 | 
 566 | def run_single_render():
 567 |     """Execute one full perfection loop (up to MAX_ITERATIONS). Returns verdict string."""
 568 |     log("="*60)
 569 |     log(f"OVERNIGHT LOOP START | max {MAX_ITERATIONS} iters | max {MAX_HOURS}h")
 570 |     log("="*60)
 571 |     # P0 Fix 5: Resume from saved state if available
 572 |     start_iter, start = _load_render_state()
 573 |     grade_result = {}
 574 |     final_verdict = "ERROR"
 575 |     _consecutive_no_output = 0  # audit P1-M3: track render-absent streaks
 576 |     _consecutive_grade_fail = 0  # audit P0-U2: track grade failure streaks
 577 | 
 578 |     for iteration in range(start_iter, MAX_ITERATIONS+1):
 579 |         if (time.time()-start)/3600 >= MAX_HOURS:
 580 |             log(f"TIME LIMIT ({MAX_HOURS}h). Stopping."); break
 581 |         log(f"\n{'='*60}\nITERATION {iteration}/{MAX_ITERATIONS}\n{'='*60}")
 582 |         _save_render_state(iteration, start)  # P0 Fix 5
 583 |         video, rlog = run_render(iteration)
 584 |         if not video:
 585 |             _consecutive_no_output += 1
 586 |             if _consecutive_no_output >= CONSECUTIVE_RENDER_ABSENT_THRESHOLD:
 587 |                 log(f"ABORT: {_consecutive_no_output} consecutive renders produced no output — stopping loop")
 588 |                 send_telegram_alert(
 589 |                     f"PIPELINE ABORT: {_consecutive_no_output} consecutive renders produced no output file. "
 590 |                     f"Iteration {iteration}/{MAX_ITERATIONS}. Manual investigation required."
 591 |                 )
 592 |                 break
 593 |             log("Render failed, skipping"); time.sleep(60); continue
 594 |         _consecutive_no_output = 0  # reset on successful output
 595 |         # Forensics with 10-min hard timeout (task issue #1)
 596 |         forensics = run_forensics(video)
 597 |         # Grade ALWAYS fires after forensics — even if forensics returned {} (task issue main)
 598 |         try:
 599 |             grade_result = grade_with_gemini(video, forensics, rlog)
 600 |         except Exception as _ge:
 601 |             log(f"Grading failed (non-fatal): {_ge}")
 602 |             grade_result = None
 603 |         if not grade_result:
 604 |             _consecutive_grade_fail += 1
 605 |             if _consecutive_grade_fail >= CONSECUTIVE_GRADE_FAILURES_THRESHOLD:
 606 |                 log(f"ABORT: {_consecutive_grade_fail} consecutive grade failures — grading system is broken")
 607 |                 send_telegram_alert(
 608 |                     f"PIPELINE ABORT: {_consecutive_grade_fail} consecutive grade failures. "
 609 |                     f"Gemini grading unavailable. Manual investigation required."
 610 |                 )
 611 |                 break
 612 |             # Fallback: run gemini_grade.py directly as subprocess (task issue #2)
 613 |             log("grade_with_gemini failed — running gemini_grade.py directly")
 614 |             try:
 615 |                 r = subprocess.run(
 616 |                     ["python3", "gemini_grade.py", video],
 617 |                     capture_output=True, text=True, timeout=300, cwd=PIPELINE
 618 |                 )
 619 |                 # Parse both PASS and FAIL lines
 620 |                 if "GRADE_" in (r.stdout or ''):
 621 |                     for line in r.stdout.splitlines():
 622 |                         if line.startswith("GRADE_"):
 623 |                             # Format: GRADE_A_PASS|95|path|verdict or GRADE_B_FAIL|72|path|verdict
 624 |                             parts = line.split("|", 3)  # maxsplit=3 (audit M4)
 625 |                             if len(parts) < 2:
 626 |                                 log(f"Unexpected grade line format: {line!r}")
 627 |                                 continue
 628 |                             grade_tag = parts[0]  # e.g. GRADE_A_PASS
 629 |                             tag_parts = grade_tag.split("_")
 630 |                             grade_letter = tag_parts[1] if len(tag_parts) > 1 else "F"
 631 |                             try:
 632 |                                 score_val = int(parts[1])
 633 |                             except (ValueError, IndexError):
 634 |                                 score_val = 0
 635 |                             grade_result = {
 636 |                                 "grade": grade_letter,
 637 |                                 "overall_score": score_val,
 638 |                                 "broadcast_ready": grade_letter == "A",
 639 |                                 "verdict": parts[3] if len(parts) > 3 else "",
 640 |                                 "dimensions": {},
 641 |                                 "critical_failures": []
 642 |                             }
 643 |                             log(f"Fallback grade: {grade_letter} ({score_val}/100)")
 644 |                             break
 645 |             except Exception as _ge2:
 646 |                 log(f"Fallback grading also failed: {_ge2}")
 647 |             if not grade_result:
 648 |                 log("All grading failed, skipping iteration"); continue
 649 |         _consecutive_grade_fail = 0  # reset on successful grade
 650 |         gf = os.path.join(PIPELINE, f'logs/grade_iter{iteration}.json')
 651 |         with open(gf, 'w') as f: json.dump(grade_result, f, indent=2)
 652 |         grade = grade_result.get('grade','F')
 653 |         score = grade_result.get('overall_score', 0)
 654 |         broadcast = grade_result.get('broadcast_ready', False)
 655 |         # Explicit GRADE: logging after every grade result (task issue #4)
 656 |         log(f"GRADE: {grade} | SCORE: {score}/100 | BROADCAST: {broadcast}")
 657 |         log(f"GRADE: iteration={iteration} grade={grade} score={score} broadcast={broadcast}")
 658 |         log(f"VERDICT: {grade_result.get('verdict','')}")
 659 |         for dim, data in grade_result.get('dimensions',{}).items():
 660 |             s = data.get('score','?')
 661 |             flag = ' ✓' if isinstance(s,int) and s>=8 else (' !!' if isinstance(s,int) and s<6 else '')
 662 |             log(f"  {dim:30s} {s}/10{flag}")
 663 |         if grade == 'A' and broadcast and score >= 88:
 664 |             log("*** GRADE A — LOCKING WINNER RECIPE ***")
 665 |             recipe = {'winner': True, 'iteration': iteration, 'timestamp': datetime.now().isoformat(),
 666 |                      'video': video, 'grade': grade, 'score': score,
 667 |                      'verdict': grade_result.get('verdict'), 'dimensions': grade_result.get('dimensions',{})}
 668 |             with open(RECIPE_FILE, 'w') as f: json.dump(recipe, f, indent=2)
 669 |             log(f"WINNER: {RECIPE_FILE}")
 670 |             final_verdict = "PASS"
 671 |             break
 672 |         elif grade in ('B', 'C') and broadcast:
 673 |             final_verdict = "DEGRADED"
 674 |         log(f"Grade {grade} - firing CC fix...")
 675 |         fire_cc_fix(iteration, grade_result)
 676 |     else:
 677 |         log("Max iterations reached without Grade A")
 678 |         with open(os.path.join(PIPELINE,'logs/overnight_diagnostic.json'),'w') as f:
 679 |             json.dump({'final_grade': grade_result}, f, indent=2)
 680 |         if final_verdict == "ERROR":
 681 |             final_verdict = "HOLD"
 682 | 
 683 |     log("OVERNIGHT LOOP COMPLETE")
 684 |     return final_verdict
 685 | 
 686 | 
 687 | def run_cycle():
 688 |     """Run a single render cycle with exception handling and retry logic."""
 689 |     cycle_start = time.time()
 690 | 
 691 |     # Check TTS before render
 692 |     tts_ready, tts_provider = check_tts_ready()
 693 |     log(f"TTS provider: {tts_provider}")
 694 |     if not tts_ready:
 695 |         log(f"[loop] TTS not available ({tts_provider}) — skipping cycle")
 696 |         write_heartbeat("ERROR", time.time() - cycle_start)
 697 |         return
 698 | 
 699 |     for attempt in range(1, MAX_ATTEMPTS_PER_CYCLE + 1):
 700 |         log(f"[loop] Attempt {attempt}/{MAX_ATTEMPTS_PER_CYCLE}")
 701 |         try:
 702 |             verdict = run_single_render()
 703 |         except Exception as e:
 704 |             logger.error(f"[loop] Render cycle exception: {e}", exc_info=True)
 705 |             verdict = "ERROR"
 706 | 
 707 |         if verdict in ("PASS", "DEGRADED"):
 708 |             write_heartbeat(verdict, time.time() - cycle_start)
 709 |             return
 710 | 
 711 |         # Failed — retry logic
 712 |         if attempt < MAX_ATTEMPTS_PER_CYCLE:
 713 |             log(f"[loop] Attempt {attempt} failed ({verdict}), waiting {RETRY_WAIT_SECONDS//60}min before retry...")
 714 |             time.sleep(RETRY_WAIT_SECONDS)
 715 |         else:
 716 |             log(f"[loop] All {MAX_ATTEMPTS_PER_CYCLE} attempts failed — waiting for next scheduled cycle")
 717 | 
 718 |     write_heartbeat(verdict, time.time() - cycle_start)
 719 | 
 720 | 
 721 | # ── Daemon mode ───────────────────────────────────────────────────
 722 | def sleep_until_next_8am_et():
 723 |     """Sleep until next 08:00 ET (12:00 UTC or 11:00 UTC during DST)."""
 724 |     from zoneinfo import ZoneInfo
 725 |     et = ZoneInfo("America/New_York")
 726 |     now = datetime.now(et)
 727 |     target = now.replace(hour=8, minute=0, second=0, microsecond=0)
 728 |     if target <= now:
 729 |         target += timedelta(days=1)
 730 |     wait = (target - now).total_seconds()
 731 |     log(f"[daemon] Sleeping {wait/3600:.1f}h until {target.isoformat()}")
 732 |     time.sleep(wait)
 733 | 
 734 | 
 735 | PIDFILE = os.path.join(BASE, 'logs', 'render_loop.pid')
 736 | RENDER_STATE_FILE = '/tmp/render_state.json'
 737 | 
 738 | 
 739 | def _save_render_state(iteration, start_time):
 740 |     """P0 Fix 5: Persist iteration + start_time across daemon restarts."""
 741 |     try:
 742 |         state = {
 743 |             "iteration": iteration,
 744 |             "start_time": start_time,
 745 |             "saved_at": datetime.now(timezone.utc).isoformat(),
 746 |         }
 747 |         with open(RENDER_STATE_FILE, 'w') as f:
 748 |             json.dump(state, f)
 749 |     except Exception as e:
 750 |         log(f"WARNING: save_render_state failed: {e}")
 751 | 
 752 | 
 753 | def _load_render_state():
 754 |     """P0 Fix 5: Load saved state. Returns (iteration, start_time) or (1, now)."""
 755 |     try:
 756 |         with open(RENDER_STATE_FILE) as f:
 757 |             state = json.load(f)
 758 |         saved_start = state.get("start_time", 0)
 759 |         saved_iter = state.get("iteration", 1)
 760 |         age_hours = (time.time() - saved_start) / 3600
 761 |         if age_hours < MAX_HOURS and saved_iter < MAX_ITERATIONS:
 762 |             log(f"Resuming from saved state: iteration={saved_iter}, age={age_hours:.1f}h")
 763 |             return saved_iter, saved_start
 764 |         else:
 765 |             log(f"Saved state too old ({age_hours:.1f}h) or exhausted (iter={saved_iter}) — starting fresh")
 766 |     except (FileNotFoundError, json.JSONDecodeError, KeyError):
 767 |         pass
 768 |     return 1, time.time()
 769 | 
 770 | 
 771 | def _acquire_singleton():
 772 |     """Prevent duplicate render loop instances. Checks for stale PID (audit UI-4)."""
 773 |     import fcntl
 774 |     # Check for stale PID before locking
 775 |     if os.path.exists(PIDFILE):
 776 |         try:
 777 |             with open(PIDFILE) as f:
 778 |                 old_pid = int(f.read().strip())
 779 |             os.kill(old_pid, 0)  # check if process is alive
 780 |         except (ValueError, ProcessLookupError, PermissionError):
 781 |             # Process is dead — stale lockfile, remove it
 782 |             log(f"Removing stale PID file (pid {old_pid if 'old_pid' in dir() else '?'} not running)")
 783 |             try:
 784 |                 os.remove(PIDFILE)
 785 |             except OSError:
 786 |                 pass
 787 |         except OSError:
 788 |             pass  # Process exists, let flock handle it
 789 | 
 790 |     fp = open(PIDFILE, 'w')
 791 |     try:
 792 |         fcntl.flock(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
 793 |     except OSError:
 794 |         log("ABORT: Another render loop instance is already running (pidfile locked)")
 795 |         sys.exit(1)
 796 |     fp.write(str(os.getpid()))
 797 |     fp.flush()
 798 |     # Keep fp open to hold the lock — do NOT close or the lock releases
 799 |     return fp
 800 | 
 801 | 
 802 | def main():
 803 |     parser = argparse.ArgumentParser(
 804 |         description="Protocol Pulse overnight render loop — production hardened",
 805 |         formatter_class=argparse.RawDescriptionHelpFormatter,
 806 |         epilog=(
 807 |             "Examples:\n"
 808 |             "  python3 overnight_render_loop.py              # single cycle\n"
 809 |             "  python3 overnight_render_loop.py --daemon      # continuous, 08:00 ET daily\n"
 810 |             "  python3 overnight_render_loop.py --dry-run     # startup checks only\n"
 811 |         )
 812 |     )
 813 |     parser.add_argument("--daemon", action="store_true", help="Run as continuous daemon (loop at 08:00 ET daily)")
 814 |     parser.add_argument("--dry-run", action="store_true", help="Run startup checks only, no render")
 815 |     args = parser.parse_args()
 816 | 
 817 |     # Singleton guard — prevent duplicate instances
 818 |     _lock_fp = _acquire_singleton()
 819 | 
 820 |     # Startup checks always run
 821 |     log("="*60)
 822 |     log("STARTUP CHECKS")
 823 |     log("="*60)
 824 |     if not startup_checks():
 825 |         log("STARTUP CHECKS FAILED — exiting")
 826 |         sys.exit(1)
 827 |     log("All startup checks passed")
 828 | 
 829 |     if args.dry_run:
 830 |         log("--dry-run mode: startup checks passed, exiting")
 831 |         sys.exit(0)
 832 | 
 833 |     # Load existing heartbeat state
 834 |     global _total_episodes, _consecutive_failures
 835 |     try:
 836 |         with open(HEARTBEAT_FILE) as f:
 837 |             hb = json.load(f)
 838 |             _total_episodes = hb.get('total_episodes', 0)
 839 |             _consecutive_failures = hb.get('consecutive_failures', 0)
 840 |         log(f"Heartbeat loaded: episodes={_total_episodes}, consecutive_failures={_consecutive_failures}")
 841 |     except (FileNotFoundError, json.JSONDecodeError):
 842 |         pass
 843 | 
 844 |     if args.daemon:
 845 |         log("DAEMON MODE — will loop at 08:00 ET daily")
 846 |         while True:
 847 |             verdict = run_cycle() or "DEGRADED"
 848 |             if verdict == "PASS":
 849 |                 sleep_until_next_8am_et()
 850 |             else:
 851 |                 log("[daemon] No Grade A — retrying in 30 min")
 852 |                 time.sleep(1800)
 853 |     else:
 854 |         run_cycle()
 855 | 
 856 | 
 857 | if __name__ == '__main__':
 858 |     main()
 859 | 
```

---

## YOUR REVIEW TASK

Perform a forensic code review. Be brutally honest. Cite line numbers.
There is no developer present. No ego to protect. Only quality matters.

### SECTION 1: CORRECTNESS
Walk through the main user flow step by step. Does the code do what it claims?
- Logic errors, wrong variable names, silent failures
- Race conditions (concurrent requests hitting same state)
- N+1 query problems (DB queries inside loops)
- Edge cases that will break in production (empty DB, API timeout, bad input)

### SECTION 2: LAW COMPLIANCE
For each LAW in the governing spec above, state: COMPLIANT / VIOLATION / PARTIAL
Cite specific line numbers for any violation or partial compliance.

### SECTION 3: SECURITY
- SQL injection (check raw queries and ORM filter() with user input)
- Authentication bypasses (routes that should require login but don't)
- Rate limiting gaps (can one user exhaust paid API limits?)
- Secrets in code (API keys, tokens, passwords hardcoded anywhere?)
- Unvalidated user input reaching DB, filesystem, or shell

### SECTION 4: FRONTEND QUALITY
- Does the UI match the spec layout exactly?
- Hardcoded values that should be dynamic (prices, counts, dates)
- Mobile viewport breakage
- JS errors that prevent page functioning
- Loading / error / empty state for every async operation — are all 3 handled?
- Does it look world-class? Or does it look like a rushed prototype?

### SECTION 5: BACKEND QUALITY
- DB operations: try/except with rollback on every write?
- External API calls: timeout + retry + graceful degradation on every call?
- Cron job: does it handle failure without crashing the service?
- Memory leaks: large objects created per-request without cleanup?
- Logging: are errors logged with enough context to debug production issues?

### SECTION 6: WORLD-CLASS GAP ANALYSIS
This is Protocol Pulse — a premium Bitcoin intelligence product.
What would Bloomberg Terminal, Coinbase Advanced, or Blockworks do differently?
What is genuinely missing that would make this impressive to a professional?
DO NOT pad this section. Only include changes with material impact.
If an area is already excellent, explicitly say so — that's equally important.

### SECTION 7: SCORES (0-100 each)
- Backend logic:    X/100
- Frontend/UI:      X/100
- Error handling:   X/100
- Security:         X/100
- Performance:      X/100
- Law compliance:   X/100
- World-class gap:  X/100 (100 = nothing missing, 0 = prototype quality)
- OVERALL:          X/100

### SECTION 8: PRIORITY ACTION PLAN
Every fix and improvement, sorted by impact. Be specific — cite file and line.
Format exactly as:
P0 CRITICAL | [what] | [file:line] | [why it will break production]
P1 HIGH     | [what] | [file:line] | [why it degrades quality]
P2 MEDIUM   | [what] | [file:line] | [enhancement that matters]
P3 LOW      | [what] | [file:line] | [polish]

### SECTION 9: THE ONE THING
If you could only tell the developer one thing to make this dramatically better,
what would it be? One sentence. Make it count.

### SECTION 10: FINAL VERDICT
In 2-3 sentences: is this code ready for production? What must change first?

