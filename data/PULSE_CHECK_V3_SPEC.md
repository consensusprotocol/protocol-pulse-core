# PULSE CHECK VIDEO PRODUCTION SYSTEM — V3
## Intelligence-First Architecture
### Date: February 24, 2026

---

# NORTH STAR PRINCIPLE

> **Monitor ALL channels → Score ALL content → Select TOP moments → Produce 6 videos + feed newsletter/tweets**

This is not just a video pipeline. It's a **Bitcoin content intelligence system** that:
1. Monitors your entire partner network daily
2. Transcribes and analyzes everything
3. Curates the best moments for video
4. Feeds ALL intelligence to articles, newsletter, and social posts

---

# TABLE OF CONTENTS
1. [Architecture Overview](#architecture-overview)
2. [Config-Driven Channel Management](#config-driven-channels)
3. [Intelligence Pipeline](#intelligence-pipeline)
4. [Daily Output Strategy](#daily-output)
5. [Ultron API Server (v3)](#ultron-api-v3)
6. [Replit Orchestrator (v3)](#replit-orchestrator-v3)
7. [Advanced Video Assembly](#advanced-assembly)
8. [Vertical Shorts Pipeline](#vertical-shorts)
9. [Multi-Platform Distribution](#distribution)
10. [Admin Dashboard](#dashboard)
11. [Automation & Scheduling](#automation)
12. [Environment & Infrastructure](#infrastructure)
13. [Deployment Checklist](#deployment)
14. [Agent Instructions](#agent-instructions)

---

# ARCHITECTURE OVERVIEW

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              REPLIT (Intelligence Hub)                           │
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │  CONFIG: config/partner_channels.json                                     │   │
│  │  - Dynamically loaded, no code changes needed                            │   │
│  │  - Add/remove channels anytime                                           │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐  ┌──────────────┐   │
│  │  intelligence/  │  │  video_engine/ │  │  distribution/ │  │  dashboard/  │   │
│  │  daily_scan.py  │  │  orchestrator  │  │  twitter.py    │  │  app.py      │   │
│  │  score_all.py   │  │  assembler.py  │  │  youtube.py    │  │  templates/  │   │
│  │  select_top.py  │  │  verticals.py  │  │  rumble.py     │  │              │   │
│  └────────┬───────┘  └────────┬───────┘  └────────┬───────┘  └──────────────┘   │
│           │                   │                    │                             │
│  ┌────────▼───────────────────▼────────────────────▼─────────────────────────┐   │
│  │  ultron_client.py — Unified HTTP client with auth, retries, streaming     │   │
│  └────────────────────────────────┬──────────────────────────────────────────┘   │
│                                   │                                              │
│  ┌────────────────────────────────▼──────────────────────────────────────────┐   │
│  │  pipeline_state.py — SQLite state machine                                 │   │
│  │  Tables: runs, channel_scans, highlights, distributions                   │   │
│  │  Enables: crash recovery, resume, audit trail, analytics                  │   │
│  └───────────────────────────────────────────────────────────────────────────┘   │
│                                   │                                              │
│  ┌────────────────────────────────▼──────────────────────────────────────────┐   │
│  │  intel_outputs/ — Intelligence feeds to other systems                     │   │
│  │  - daily_intel.json → Article generator                                   │   │
│  │  - tweet_queue.json → X automation                                        │   │
│  │  - newsletter_digest.json → Newsletter engine                             │   │
│  └───────────────────────────────────────────────────────────────────────────┘   │
│                                   │                                              │
└───────────────────────────────────┼──────────────────────────────────────────────┘
                         Cloudflare Tunnel
                    (video.protocolpulse.io)
                                   │
┌──────────────────────────────────▼──────────────────────────────────────────────┐
│                         ULTRON (GPU Worker)                                      │
│                      (Dual RTX 4090 GPUs)                                       │
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │  api_server.py — Flask API on port 5100                                  │   │
│  │                                                                           │   │
│  │  Intelligence endpoints:                                                  │   │
│  │  POST /batch_download_audio  — Download audio from multiple videos       │   │
│  │  POST /batch_transcribe      — Queue multiple transcriptions             │   │
│  │                                                                           │   │
│  │  Video production endpoints:                                              │   │
│  │  POST /download_video        — yt-dlp video download                     │   │
│  │  POST /extract_clip          — FFmpeg GPU clip extraction                │   │
│  │  POST /assemble_advanced     — Multi-track assembly w/ graphics          │   │
│  │  POST /generate_vertical     — 9:16 crop + overlay for shorts            │   │
│  │                                                                           │   │
│  │  Utility endpoints:                                                       │   │
│  │  GET  /job/:id               — Unified job status                        │   │
│  │  GET  /health                — Server health + GPU stats                 │   │
│  │  POST /cleanup               — Purge old files                           │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

# CONFIG-DRIVEN CHANNELS

## File: config/partner_channels.json

No more hardcoded channels. Add/remove anytime without code changes.

```json
{
  "version": "2026-02-24",
  "settings": {
    "max_channels_per_run": 20,
    "top_clips_for_video": 5,
    "min_hook_score": 60,
    "clip_duration_min": 15,
    "clip_duration_max": 25
  },
  "channels": [
    {
      "name": "Bitcoin Magazine",
      "channel_id": "UCni7PAlyNS0_12H-26DJJ3w",
      "handle": "@BitcoinMagazine",
      "priority": "high",
      "enabled": true,
      "tags": ["news", "mainstream"]
    },
    {
      "name": "Simply Bitcoin",
      "channel_id": "UCGVzBOpeNmwta_-3H5BXMTQ",
      "handle": "@SimplyBitcoin",
      "priority": "high",
      "enabled": true,
      "tags": ["daily", "commentary"]
    },
    {
      "name": "The Bitcoin Layer",
      "channel_id": "UCunzl2Fy5HXTK3UtW0srhEQ",
      "handle": "@TheBitcoinLayer",
      "priority": "high",
      "enabled": true,
      "tags": ["macro", "analysis"]
    },
    {
      "name": "Coin Bureau",
      "channel_id": "UCqK_GSMbpiV8spgD3ZGloSw",
      "handle": "@CoinBureau",
      "priority": "medium",
      "enabled": true,
      "tags": ["education", "news"]
    },
    {
      "name": "Anthony Pompliano",
      "channel_id": "UCcgOOeLdesqSxSGwn9Yf8kA",
      "handle": "@AnthonyPompliano",
      "priority": "high",
      "enabled": true,
      "tags": ["interviews", "macro"]
    },
    {
      "name": "Swan Bitcoin",
      "channel_id": "UCmUjsfd2EgLevH3s5J9FHWA",
      "handle": "@SwanBitcoin",
      "priority": "medium",
      "enabled": true,
      "tags": ["education", "adoption"]
    },
    {
      "name": "Robert Breedlove",
      "channel_id": "UC7FiJ4qN3BhKfG9If-jC3cQ",
      "handle": "@Breedlove22",
      "priority": "medium",
      "enabled": true,
      "tags": ["philosophy", "deep"]
    },
    {
      "name": "Preston Pysh",
      "channel_id": "UCY6Kx8GvMmQRhX8PZeFvPKg",
      "handle": "@PrestonPysh",
      "priority": "high",
      "enabled": true,
      "tags": ["macro", "investing"]
    },
    {
      "name": "What Bitcoin Did",
      "channel_id": "UCLnQ34ZBSjy2JQjeRudFEDw",
      "handle": "@WhatBitcoinDid",
      "priority": "high",
      "enabled": true,
      "tags": ["interviews", "news"]
    },
    {
      "name": "Stephan Livera",
      "channel_id": "UCpY4T6vkhWuOBnVkB9AjVpg",
      "handle": "@StephanLivera",
      "priority": "medium",
      "enabled": true,
      "tags": ["technical", "interviews"]
    },
    {
      "name": "TFTC",
      "channel_id": "UCM7YkvLyjhGd2MNBKBzTEPg",
      "handle": "@TFTC21",
      "priority": "medium",
      "enabled": true,
      "tags": ["mining", "technical"]
    },
    {
      "name": "Bitcoin Fundamentals",
      "channel_id": "UCc4Rz_T9Sb1w5rqqo9pL1Og",
      "handle": "@saborskis",
      "priority": "medium",
      "enabled": true,
      "tags": ["education", "onboarding"]
    },
    {
      "name": "Natalie Brunell",
      "channel_id": "UCuH-a6rRVOOXWjMxR7U6eBA",
      "handle": "@natabordeleau",
      "priority": "medium",
      "enabled": true,
      "tags": ["interviews", "mainstream"]
    },
    {
      "name": "BTC Sessions",
      "channel_id": "UChzLnWVsl3puKQwc5PoO6Zg",
      "handle": "@BTCSessions",
      "priority": "medium",
      "enabled": true,
      "tags": ["tutorials", "education"]
    }
  ]
}
```

## File: services/config_loader.py

```python
"""
CONFIG LOADER
==============
Load and validate partner channels config.
Hot-reload support for runtime updates.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict
from datetime import datetime

logger = logging.getLogger("ConfigLoader")

CONFIG_PATH = Path("config/partner_channels.json")
_config_cache = None
_config_mtime = None


def load_channels_config(force_reload: bool = False) -> Dict:
    """Load channels config with caching and hot-reload support."""
    global _config_cache, _config_mtime
    
    if not CONFIG_PATH.exists():
        logger.error(f"Config file not found: {CONFIG_PATH}")
        return {"channels": [], "settings": {}}
    
    current_mtime = CONFIG_PATH.stat().st_mtime
    
    if not force_reload and _config_cache and _config_mtime == current_mtime:
        return _config_cache
    
    try:
        config = json.loads(CONFIG_PATH.read_text())
        _config_cache = config
        _config_mtime = current_mtime
        logger.info(f"Loaded config v{config.get('version', 'unknown')} with {len(config.get('channels', []))} channels")
        return config
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return {"channels": [], "settings": {}}


def get_enabled_channels() -> List[Dict]:
    """Get only enabled channels, sorted by priority."""
    config = load_channels_config()
    channels = [c for c in config.get("channels", []) if c.get("enabled", True)]
    
    # Sort by priority: high > medium > low
    priority_order = {"high": 0, "medium": 1, "low": 2}
    channels.sort(key=lambda c: priority_order.get(c.get("priority", "medium"), 1))
    
    return channels


def get_settings() -> Dict:
    """Get pipeline settings from config."""
    config = load_channels_config()
    return config.get("settings", {
        "max_channels_per_run": 20,
        "top_clips_for_video": 5,
        "min_hook_score": 60,
        "clip_duration_min": 15,
        "clip_duration_max": 25
    })


def add_channel(channel: Dict) -> bool:
    """Add a new channel to config."""
    config = load_channels_config(force_reload=True)
    
    # Check for duplicate
    existing = [c for c in config["channels"] if c["channel_id"] == channel["channel_id"]]
    if existing:
        logger.warning(f"Channel already exists: {channel['name']}")
        return False
    
    config["channels"].append(channel)
    config["version"] = datetime.now().strftime("%Y-%m-%d")
    CONFIG_PATH.write_text(json.dumps(config, indent=2))
    
    load_channels_config(force_reload=True)
    logger.info(f"Added channel: {channel['name']}")
    return True


def toggle_channel(channel_id: str, enabled: bool) -> bool:
    """Enable or disable a channel."""
    config = load_channels_config(force_reload=True)
    
    for channel in config["channels"]:
        if channel["channel_id"] == channel_id:
            channel["enabled"] = enabled
            CONFIG_PATH.write_text(json.dumps(config, indent=2))
            load_channels_config(force_reload=True)
            logger.info(f"Channel {channel['name']} {'enabled' if enabled else 'disabled'}")
            return True
    
    return False
```

---

# INTELLIGENCE PIPELINE

The key insight: **Scan everything, score everything, select the best.**

## Daily Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│  PHASE 1: SCAN (parallel on Ultron)                                     │
│  ─────────────────────────────────────                                  │
│  For each enabled channel:                                              │
│    1. Fetch latest video metadata (yt-dlp --flat-playlist)             │
│    2. Download audio (if video is < 24h old)                           │
│    3. Transcribe with Faster-Whisper                                    │
│                                                                         │
│  Output: transcripts/ folder with all daily transcripts                 │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
┌────────────────────────────────────▼────────────────────────────────────┐
│  PHASE 2: ANALYZE (Grok-3)                                              │
│  ─────────────────────────────                                          │
│  For each transcript:                                                   │
│    1. Find best 15-25 second moment                                     │
│    2. Score viral potential (1-100)                                     │
│    3. Extract key quote + narrator intro                                │
│    4. Generate tweet-worthy one-liner                                   │
│    5. Tag themes (macro, adoption, technical, etc.)                     │
│                                                                         │
│  Output: daily_intel.json with ALL channel analysis                     │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
┌────────────────────────────────────▼────────────────────────────────────┐
│  PHASE 3: SELECT (top N by score)                                       │
│  ──────────────────────────────────                                     │
│  1. Rank all highlights by hook_score                                   │
│  2. Take top 5-7 (configurable)                                         │
│  3. Ensure diversity (no more than 2 from same channel)                 │
│  4. Balance themes if possible                                          │
│                                                                         │
│  Output: selected_highlights.json for video production                  │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
┌────────────────────────────────────▼────────────────────────────────────┐
│  PHASE 4: PRODUCE (Ultron GPU)                                          │
│  ─────────────────────────────────                                      │
│  1. Download full videos for selected clips                             │
│  2. Extract clips                                                       │
│  3. Generate voiceovers (ElevenLabs)                                    │
│  4. Assemble horizontal highlight reel                                  │
│  5. Generate 5 vertical shorts                                          │
│                                                                         │
│  Output: pulse_check_YYYY-MM-DD.mp4 + 5 shorts                         │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
┌────────────────────────────────────▼────────────────────────────────────┐
│  PHASE 5: DISTRIBUTE + FEED                                             │
│  ─────────────────────────────────────                                  │
│  Video distribution:                                                    │
│    - X/Twitter (horizontal)                                             │
│    - YouTube (horizontal + shorts)                                      │
│    - TikTok, IG Reels (shorts)                                         │
│                                                                         │
│  Intelligence feeds (for other systems):                                │
│    - daily_intel.json → Article generator picks topics                 │
│    - tweet_queue.json → Auto-queue viral quotes as tweets              │
│    - newsletter_digest.json → Daily email highlights                   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

# DAILY OUTPUT

## Video Content (6 pieces)

| # | Type | Format | Duration | Platforms |
|---|------|--------|----------|-----------|
| 1 | Horizontal Highlight Reel | 16:9 (1920×1080) | 1:45-2:00 | X, YouTube, Rumble |
| 2-6 | Vertical Shorts (×5) | 9:16 (1080×1920) | 15-30s each | TikTok, IG Reels, YT Shorts |

## Intelligence Feeds

### daily_intel.json (for articles/newsletter)
```json
{
  "date": "2026-02-24",
  "channels_scanned": 14,
  "highlights": [
    {
      "channel": "Bitcoin Magazine",
      "video_title": "...",
      "key_quote": "...",
      "hook_score": 92,
      "themes": ["adoption", "institutional"],
      "tweet_text": "...",
      "used_in_video": true
    }
  ],
  "themes_today": ["macro uncertainty", "ETF flows", "mining difficulty"],
  "top_quote": "..."
}
```

### tweet_queue.json (for X automation)
```json
{
  "date": "2026-02-24",
  "tweets": [
    {
      "text": "\"Bitcoin doesn't care about your timeline.\" — @BitcoinMagazine\n\nToday's Pulse Check 🔴",
      "schedule": "2026-02-24T14:00:00Z",
      "type": "quote",
      "source_channel": "Bitcoin Magazine"
    }
  ]
}
```

---

# ULTRON API SERVER (v3)

## File: ~/video_engine/api_server.py

Key V3 additions:
- **Batch operations** for scanning multiple channels
- **Priority queue** for transcription jobs
- **Parallel processing** with job pools

```python
"""
ULTRON VIDEO ENGINE API v3
===========================
Intelligence-first video processing server.
Supports batch operations for scanning entire channel networks.
"""

import os
import subprocess
import json
import logging
import logging.handlers
import threading
import uuid
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, request, jsonify, send_file
import torch

app = Flask(__name__)

# --- Logging ---
LOG_DIR = Path.home() / "video_engine" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
handler = logging.handlers.RotatingFileHandler(
    LOG_DIR / "api_server.log", maxBytes=10_000_000, backupCount=5
)
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
logging.basicConfig(level=logging.INFO, handlers=[handler, logging.StreamHandler()])
logger = logging.getLogger("UltronAPI")

# --- Directories ---
WORK_DIR = Path.home() / "video_engine"
DIRS = {
    "clips": WORK_DIR / "clips",
    "shorts": WORK_DIR / "shorts",
    "temp": WORK_DIR / "temp",
    "audio": WORK_DIR / "audio",
    "transcripts": WORK_DIR / "transcripts",
    "jobs": WORK_DIR / "jobs",
    "voiceovers": WORK_DIR / "voiceovers",
    "assets": WORK_DIR / "assets",
    "output": WORK_DIR / "output",
    "thumbnails": WORK_DIR / "thumbnails",
}
for d in DIRS.values():
    d.mkdir(parents=True, exist_ok=True)

# --- Auth ---
API_TOKEN = os.environ.get("ULTRON_API_TOKEN", "")

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if API_TOKEN:
            token = request.headers.get("Authorization", "").replace("Bearer ", "")
            if token != API_TOKEN:
                return jsonify({"error": "unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated

# --- Thread Pool for Batch Operations ---
executor = ThreadPoolExecutor(max_workers=4)

# --- Job System ---
def create_job(job_type: str, metadata: dict = None) -> str:
    job_id = str(uuid.uuid4())[:12]
    job_data = {
        "job_id": job_id,
        "type": job_type,
        "status": "queued",
        "created_at": datetime.utcnow().isoformat(),
        "metadata": metadata or {}
    }
    (DIRS["jobs"] / f"{job_id}.json").write_text(json.dumps(job_data))
    return job_id

def update_job(job_id: str, **kwargs):
    job_file = DIRS["jobs"] / f"{job_id}.json"
    if job_file.exists():
        job = json.loads(job_file.read_text())
        job.update(kwargs)
        job["updated_at"] = datetime.utcnow().isoformat()
        job_file.write_text(json.dumps(job))

def get_job(job_id: str) -> dict:
    job_file = DIRS["jobs"] / f"{job_id}.json"
    if job_file.exists():
        return json.loads(job_file.read_text())
    return None

# --- Whisper Model (lazy load) ---
whisper_model = None
whisper_lock = threading.Lock()

def get_whisper_model():
    global whisper_model
    with whisper_lock:
        if whisper_model is None:
            logger.info("Loading Faster-Whisper model...")
            from faster_whisper import WhisperModel
            whisper_model = WhisperModel("medium", device="cuda", compute_type="float16")
            logger.info("Faster-Whisper model loaded on GPU")
    return whisper_model

# --- Helper Functions ---
def download_audio_sync(video_id: str) -> dict:
    """Synchronous audio download for batch operations."""
    output_path = DIRS["audio"] / f"{video_id}.mp3"
    
    if output_path.exists() and output_path.stat().st_size > 10000:
        return {"success": True, "video_id": video_id, "cached": True, 
                "size_mb": round(output_path.stat().st_size / 1024 / 1024, 2)}
    
    try:
        result = subprocess.run(
            ["yt-dlp", "-x", "--audio-format", "mp3", "--audio-quality", "0",
             "-o", str(DIRS["audio"] / f"{video_id}.%(ext)s"),
             f"https://www.youtube.com/watch?v={video_id}"],
            capture_output=True, text=True, timeout=300
        )
        if output_path.exists():
            return {"success": True, "video_id": video_id,
                    "size_mb": round(output_path.stat().st_size / 1024 / 1024, 2)}
        return {"success": False, "video_id": video_id, "error": result.stderr[:200]}
    except Exception as e:
        return {"success": False, "video_id": video_id, "error": str(e)}


def transcribe_sync(video_id: str) -> dict:
    """Synchronous transcription for batch operations."""
    audio_path = DIRS["audio"] / f"{video_id}.mp3"
    transcript_file = DIRS["transcripts"] / f"{video_id}.json"
    
    if transcript_file.exists():
        return {"success": True, "video_id": video_id, "cached": True}
    
    if not audio_path.exists():
        return {"success": False, "video_id": video_id, "error": "Audio not found"}
    
    try:
        model = get_whisper_model()
        segments, info = model.transcribe(str(audio_path), language="en", beam_size=5)
        all_segments = [{"start": round(s.start, 2), "end": round(s.end, 2), 
                        "text": s.text.strip()} for s in segments]
        text = " ".join([s["text"] for s in all_segments])
        
        result = {
            "text": text, 
            "segments": all_segments, 
            "video_id": video_id,
            "duration": info.duration, 
            "language": info.language
        }
        transcript_file.write_text(json.dumps(result))
        
        return {"success": True, "video_id": video_id, 
                "chars": len(text), "segments": len(all_segments)}
    except Exception as e:
        logger.error(f"Transcription error for {video_id}: {e}")
        return {"success": False, "video_id": video_id, "error": str(e)}


# ========================================================================
# BATCH ENDPOINTS (for intelligence pipeline)
# ========================================================================

@app.route("/batch_download_audio", methods=["POST"])
@require_auth
def batch_download_audio():
    """
    Download audio from multiple videos in parallel.
    
    Input: {"video_ids": ["abc123", "def456", ...]}
    Returns: {"job_id": "...", "status": "started", "count": N}
    """
    data = request.json
    video_ids = data.get("video_ids", [])
    
    if not video_ids:
        return jsonify({"error": "video_ids required"}), 400
    
    job_id = create_job("batch_download", {"video_ids": video_ids, "count": len(video_ids)})
    
    def run_batch():
        results = []
        update_job(job_id, status="processing", progress=0)
        
        # Use thread pool for parallel downloads
        futures = {executor.submit(download_audio_sync, vid): vid for vid in video_ids}
        
        for i, future in enumerate(as_completed(futures)):
            result = future.result()
            results.append(result)
            update_job(job_id, progress=int((i + 1) / len(video_ids) * 100))
        
        successes = sum(1 for r in results if r.get("success"))
        update_job(job_id, status="complete", results=results,
                  successes=successes, failures=len(video_ids) - successes)
    
    threading.Thread(target=run_batch, daemon=True).start()
    return jsonify({"job_id": job_id, "status": "started", "count": len(video_ids)})


@app.route("/batch_transcribe", methods=["POST"])
@require_auth
def batch_transcribe():
    """
    Transcribe multiple videos sequentially (GPU is the bottleneck).
    
    Input: {"video_ids": ["abc123", "def456", ...]}
    Returns: {"job_id": "...", "status": "started", "count": N}
    """
    data = request.json
    video_ids = data.get("video_ids", [])
    
    if not video_ids:
        return jsonify({"error": "video_ids required"}), 400
    
    job_id = create_job("batch_transcribe", {"video_ids": video_ids, "count": len(video_ids)})
    
    def run_batch():
        results = []
        update_job(job_id, status="processing", progress=0)
        
        # Sequential transcription (GPU can only do one at a time efficiently)
        for i, video_id in enumerate(video_ids):
            result = transcribe_sync(video_id)
            results.append(result)
            update_job(job_id, progress=int((i + 1) / len(video_ids) * 100),
                      current_video=video_id)
            logger.info(f"Batch transcribe {i+1}/{len(video_ids)}: {video_id} — "
                       f"{'OK' if result.get('success') else 'FAIL'}")
        
        successes = sum(1 for r in results if r.get("success"))
        update_job(job_id, status="complete", results=results,
                  successes=successes, failures=len(video_ids) - successes)
    
    threading.Thread(target=run_batch, daemon=True).start()
    return jsonify({"job_id": job_id, "status": "started", "count": len(video_ids)})


@app.route("/get_transcripts", methods=["POST"])
@require_auth
def get_transcripts():
    """
    Fetch multiple transcripts at once.
    
    Input: {"video_ids": ["abc123", "def456", ...]}
    Returns: {"transcripts": {"abc123": {...}, "def456": {...}}}
    """
    data = request.json
    video_ids = data.get("video_ids", [])
    
    transcripts = {}
    for video_id in video_ids:
        transcript_file = DIRS["transcripts"] / f"{video_id}.json"
        if transcript_file.exists():
            transcripts[video_id] = json.loads(transcript_file.read_text())
    
    return jsonify({"transcripts": transcripts, "found": len(transcripts), 
                    "requested": len(video_ids)})


# ========================================================================
# STANDARD ENDPOINTS (existing functionality)
# ========================================================================

@app.route("/health", methods=["GET"])
def health():
    gpu_info = []
    if torch.cuda.is_available():
        for i in range(torch.cuda.device_count()):
            gpu_info.append({
                "index": i,
                "name": torch.cuda.get_device_name(i),
                "memory_allocated_gb": round(torch.cuda.memory_allocated(i) / 1e9, 2),
                "memory_total_gb": round(torch.cuda.get_device_properties(i).total_mem / 1e9, 2),
            })
    return jsonify({
        "status": "ok",
        "hostname": os.uname().nodename,
        "gpu_count": len(gpu_info),
        "gpus": gpu_info,
        "version": "3.0-intelligence",
        "timestamp": datetime.utcnow().isoformat()
    })


@app.route("/job/<job_id>", methods=["GET"])
def job_status(job_id):
    job = get_job(job_id)
    if job:
        return jsonify(job)
    return jsonify({"error": "job not found"}), 404


@app.route("/download_audio", methods=["POST"])
@require_auth
def download_audio():
    data = request.json
    video_id = data.get("video_id")
    if not video_id:
        return jsonify({"error": "video_id required"}), 400
    result = download_audio_sync(video_id)
    if result.get("success"):
        return jsonify(result)
    return jsonify(result), 500


@app.route("/download_video", methods=["POST"])
@require_auth
def download_video():
    data = request.json
    video_id = data.get("video_id")
    quality = data.get("quality", "720")
    if not video_id:
        return jsonify({"error": "video_id required"}), 400

    output_path = DIRS["temp"] / f"{video_id}.mp4"

    if output_path.exists() and output_path.stat().st_size > 100000:
        return jsonify({
            "success": True, "path": str(output_path),
            "cached": True, "size_mb": round(output_path.stat().st_size / 1024 / 1024, 2)
        })

    try:
        result = subprocess.run(
            ["yt-dlp", "-f", f"best[height<={quality}]",
             "--merge-output-format", "mp4",
             "-o", str(output_path),
             f"https://www.youtube.com/watch?v={video_id}"],
            capture_output=True, text=True, timeout=600
        )
        if output_path.exists():
            return jsonify({
                "success": True, "path": str(output_path),
                "size_mb": round(output_path.stat().st_size / 1024 / 1024, 2)
            })
        return jsonify({"error": "Download failed", "stderr": result.stderr[:500]}), 500
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Download timed out"}), 504


@app.route("/transcribe_async", methods=["POST"])
@require_auth
def transcribe_async():
    data = request.json
    video_id = data.get("video_id")
    if not video_id:
        return jsonify({"error": "video_id required"}), 400

    audio_path = DIRS["audio"] / f"{video_id}.mp3"
    if not audio_path.exists():
        return jsonify({"error": f"Audio not found: {video_id}"}), 404

    transcript_file = DIRS["transcripts"] / f"{video_id}.json"
    if transcript_file.exists():
        return jsonify({"status": "complete", "video_id": video_id, "cached": True})

    job_id = create_job("transcription", {"video_id": video_id})
    
    def run_transcribe():
        result = transcribe_sync(video_id)
        if result.get("success"):
            update_job(job_id, status="complete", **result)
        else:
            update_job(job_id, status="error", error=result.get("error"))
    
    threading.Thread(target=run_transcribe, daemon=True).start()
    return jsonify({"status": "started", "job_id": job_id, "video_id": video_id})


@app.route("/transcript/<video_id>", methods=["GET"])
def get_transcript(video_id):
    transcript_file = DIRS["transcripts"] / f"{video_id}.json"
    if transcript_file.exists():
        return jsonify(json.loads(transcript_file.read_text()))
    return jsonify({"error": "Transcript not found"}), 404


@app.route("/extract_clip", methods=["POST"])
@require_auth
def extract_clip():
    data = request.json
    video_id = data.get("video_id")
    start_time = data.get("start_time", 0)
    end_time = data.get("end_time", 60)
    output_name = data.get("output_name", f"clip_{video_id}")

    video_path = DIRS["temp"] / f"{video_id}.mp4"
    output_path = DIRS["clips"] / f"{output_name}.mp4"

    if not video_path.exists():
        return jsonify({"error": f"Video not found: {video_id}"}), 404

    if output_path.exists() and output_path.stat().st_size > 10000:
        return jsonify({
            "success": True, "path": str(output_path),
            "cached": True, "size_mb": round(output_path.stat().st_size / 1024 / 1024, 2)
        })

    duration = end_time - start_time
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(max(0, start_time - 0.5)),
        "-i", str(video_path),
        "-t", str(duration + 1),
        "-c:v", "h264_nvenc", "-preset", "fast", "-b:v", "4M",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        str(output_path)
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, timeout=120)
        if output_path.exists() and output_path.stat().st_size > 1000:
            return jsonify({
                "success": True, "path": str(output_path),
                "size_mb": round(output_path.stat().st_size / 1024 / 1024, 2)
            })
        return jsonify({"error": "Extraction failed", "stderr": result.stderr.decode()[:500]}), 500
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Clip extraction timed out"}), 504


# ========================================================================
# ASSEMBLY ENDPOINTS (keeping existing V2 functionality)
# ========================================================================

@app.route("/assemble_advanced", methods=["POST"])
@require_auth
def assemble_advanced():
    """Advanced assembly with voiceovers, lower-thirds, transitions."""
    manifest = request.json
    if not manifest or not manifest.get("segments"):
        return jsonify({"error": "manifest with segments required"}), 400

    job_id = create_job("assembly", {"output_name": manifest.get("output_name", "pulse_check.mp4")})
    
    # Import the assembly function (keeping it modular)
    from advanced_assembly import do_advanced_assembly
    threading.Thread(target=do_advanced_assembly, args=(job_id, manifest, DIRS), daemon=True).start()
    
    return jsonify({"status": "started", "job_id": job_id})


@app.route("/generate_vertical", methods=["POST"])
@require_auth
def generate_vertical():
    """Generate 9:16 vertical short from horizontal clip."""
    params = request.json
    if not params or not params.get("clip"):
        return jsonify({"error": "clip required"}), 400
    
    job_id = create_job("vertical", {"clip": params["clip"]})
    
    from vertical_generator import do_vertical_gen
    threading.Thread(target=do_vertical_gen, args=(job_id, params, DIRS), daemon=True).start()
    
    return jsonify({"status": "started", "job_id": job_id})


# ========================================================================
# FILE MANAGEMENT
# ========================================================================

@app.route("/upload_voiceover", methods=["POST"])
@require_auth
def upload_voiceover():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    f = request.files["file"]
    filename = request.form.get("filename", f.filename)
    output_path = DIRS["voiceovers"] / filename
    f.save(output_path)
    return jsonify({"success": True, "path": str(output_path), "size": output_path.stat().st_size})


@app.route("/upload_asset", methods=["POST"])
@require_auth
def upload_asset():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    f = request.files["file"]
    filename = request.form.get("filename", f.filename)
    output_path = DIRS["assets"] / filename
    f.save(output_path)
    return jsonify({"success": True, "path": str(output_path), "size": output_path.stat().st_size})


@app.route("/download/<path:filename>", methods=["GET"])
def download_file(filename):
    file_path = DIRS["output"] / filename
    if file_path.exists():
        return send_file(file_path, as_attachment=True)
    return jsonify({"error": "File not found"}), 404


@app.route("/download_short/<filename>", methods=["GET"])
def download_short(filename):
    file_path = DIRS["shorts"] / filename
    if file_path.exists():
        return send_file(file_path, as_attachment=True)
    return jsonify({"error": "File not found"}), 404


@app.route("/list_output", methods=["GET"])
def list_output():
    files = []
    for f in sorted(DIRS["output"].glob("*.mp4"), key=lambda x: x.stat().st_mtime, reverse=True):
        files.append({"name": f.name, "size_mb": round(f.stat().st_size / 1024 / 1024, 2),
                       "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat()})
    return jsonify({"files": files})


@app.route("/disk", methods=["GET"])
def disk_usage():
    usage = {}
    for name, path in DIRS.items():
        total_bytes = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
        file_count = sum(1 for f in path.rglob("*") if f.is_file())
        usage[name] = {"size_mb": round(total_bytes / 1024 / 1024, 1), "files": file_count}
    total = shutil.disk_usage(str(WORK_DIR))
    return jsonify({
        "directories": usage,
        "disk_total_gb": round(total.total / 1e9, 1),
        "disk_used_gb": round(total.used / 1e9, 1),
        "disk_free_gb": round(total.free / 1e9, 1),
    })


@app.route("/cleanup", methods=["POST"])
@require_auth
def cleanup():
    days = request.json.get("days", 7)
    cutoff = datetime.now() - timedelta(days=days)
    removed = 0
    for dir_name in ["temp", "audio", "clips", "shorts", "voiceovers", "jobs"]:
        for f in DIRS[dir_name].glob("*"):
            if f.is_file() and datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
                f.unlink()
                removed += 1
    logger.info(f"Cleanup: removed {removed} files older than {days} days")
    return jsonify({"removed": removed, "days": days})


if __name__ == "__main__":
    print("Loading Faster-Whisper model...")
    get_whisper_model()
    print(f"\n{'='*60}")
    print("ULTRON VIDEO ENGINE API v3 — INTELLIGENCE MODE")
    print(f"Port: 5100")
    print(f"Auth: {'enabled' if API_TOKEN else 'DISABLED'}")
    print(f"{'='*60}\n")
    app.run(host="0.0.0.0", port=5100, threaded=True)
```

---

# REPLIT ORCHESTRATOR (v3)

## File: services/video_engine/intelligence_pipeline.py

The new brain of the system.

```python
"""
INTELLIGENCE PIPELINE v3
=========================
Monitor ALL → Analyze ALL → Select TOP → Produce + Feed

This is the daily driver that:
1. Scans all enabled channels
2. Transcribes everything
3. Analyzes with Grok to find best moments
4. Selects top 5-7 for video
5. Produces horizontal + vertical content
6. Outputs intelligence feeds for other systems
"""

import os
import json
import logging
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import requests

from services.config_loader import get_enabled_channels, get_settings
from services.video_engine.ultron_client import ultron
from services.video_engine.pipeline_state import (
    create_run, update_channel, update_run, get_run,
    get_incomplete_channels, get_completed_channels,
    ChannelStage, RunStage
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
logger = logging.getLogger("IntelligencePipeline")

# Output directories
INTEL_DIR = Path("data/video_engine/intel")
OUTPUT_DIR = Path("data/video_engine/output")
SHORTS_DIR = Path("data/video_engine/shorts")
VOICEOVER_DIR = Path("data/video_engine/voiceovers")

for d in [INTEL_DIR, OUTPUT_DIR, SHORTS_DIR, VOICEOVER_DIR]:
    d.mkdir(parents=True, exist_ok=True)


class IntelligencePipeline:
    """
    The daily intelligence and video production pipeline.
    """
    
    def __init__(self):
        self.today = datetime.now().strftime("%Y-%m-%d")
        self.date_display = datetime.now().strftime("%B %d, %Y")
        self.run_id = f"intel_{self.today}_{datetime.now().strftime('%H%M%S')}"
        self.settings = get_settings()
        self.channels = get_enabled_channels()
        
        # Will be populated during run
        self.all_highlights = []
        self.selected_highlights = []
    
    def get_latest_video(self, channel: Dict) -> Optional[Dict]:
        """Get latest video from a YouTube channel."""
        try:
            cmd = [
                "yt-dlp", "--flat-playlist", "--playlist-items", "1",
                "--print", '{"id": "%(id)s", "title": "%(title)s", "duration": %(duration)s, "upload_date": "%(upload_date)s"}',
                f"https://www.youtube.com/channel/{channel['channel_id']}/videos"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.stdout.strip():
                video = json.loads(result.stdout.strip())
                # Check if video is recent (within 48 hours)
                if video.get("upload_date"):
                    upload_date = datetime.strptime(video["upload_date"], "%Y%m%d")
                    if datetime.now() - upload_date > timedelta(days=2):
                        logger.info(f"  [{channel['name']}] Latest video is >48h old, skipping")
                        return None
                return video
        except Exception as e:
            logger.error(f"  [{channel['name']}] Error fetching video: {e}")
        return None
    
    def analyze_with_grok(self, transcript: str, channel: Dict, video_title: str) -> Optional[Dict]:
        """
        Use Grok to analyze transcript and find best moment.
        Returns highlight data + tweet text + themes.
        """
        grok_key = os.environ.get("XAI_API_KEY")
        if not grok_key:
            logger.error("No XAI_API_KEY")
            return None
        
        settings = self.settings
        
        prompt = f"""You are a Bitcoin content curator for "Pulse Check," a daily highlight show.

Analyze this transcript from {channel['name']} and identify the SINGLE BEST {settings['clip_duration_min']}-{settings['clip_duration_max']} second moment.

VIDEO TITLE: {video_title}
CHANNEL TAGS: {', '.join(channel.get('tags', []))}

CRITERIA (ranked by importance):
1. Bold prediction or controversial take that will stop scrolling
2. Surprising statistic, data point, or revelation
3. Emotionally charged, passionate delivery
4. Clean, quotable statement (no mid-sentence cuts)
5. Bitcoin-specific insight (not generic crypto/altcoin content)

RULES:
- Clip MUST be {settings['clip_duration_min']}-{settings['clip_duration_max']} seconds
- Start/end on sentence boundaries
- Moment must be self-contained (understandable without context)
- Avoid price speculation, focus on fundamentals/adoption/macro

Transcript (with timestamps):
{transcript[:12000]}

Respond with ONLY valid JSON:
{{
    "start_time": <float>,
    "end_time": <float>,
    "key_quote": "<most quotable line, max 150 chars>",
    "hook_score": <int 1-100, viral potential>,
    "narrator_intro": "<1 sentence to set up this clip for AI host>",
    "vertical_caption": "<punchy text for vertical overlay, max 60 chars>",
    "tweet_text": "<standalone tweet version of this insight, include channel credit, max 250 chars>",
    "themes": [<list of 1-3 theme tags like "macro", "adoption", "mining", "regulation", "technical">],
    "summary": "<2-3 sentence summary of the key insight for newsletter>"
}}"""

        try:
            resp = requests.post(
                "https://api.x.ai/v1/chat/completions",
                headers={"Authorization": f"Bearer {grok_key}", "Content-Type": "application/json"},
                json={"model": "grok-3", "messages": [{"role": "user", "content": prompt}], "temperature": 0.3},
                timeout=90
            )
            
            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"]
                
                # Extract JSON from response
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]
                
                result = json.loads(content.strip())
                
                # Validate and adjust duration
                duration = result.get("end_time", 0) - result.get("start_time", 0)
                if duration < settings['clip_duration_min']:
                    result["end_time"] = result["start_time"] + settings['clip_duration_min'] + 5
                elif duration > settings['clip_duration_max'] + 10:
                    result["end_time"] = result["start_time"] + settings['clip_duration_max']
                
                return result
            else:
                logger.error(f"Grok API error {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            logger.error(f"Grok analysis error: {e}")
        return None
    
    def phase1_scan_all(self) -> List[Dict]:
        """
        PHASE 1: Scan all enabled channels.
        Download audio and transcribe everything.
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"PHASE 1: SCANNING {len(self.channels)} CHANNELS")
        logger.info(f"{'='*60}\n")
        
        # Get latest videos from all channels
        videos_to_process = []
        
        for channel in self.channels:
            video = self.get_latest_video(channel)
            if video:
                videos_to_process.append({
                    "channel": channel,
                    "video": video
                })
                logger.info(f"  ✓ [{channel['name']}] {video.get('title', 'Unknown')[:50]}...")
            else:
                logger.info(f"  ✗ [{channel['name']}] No recent video")
        
        if not videos_to_process:
            logger.warning("No videos to process!")
            return []
        
        logger.info(f"\n  Found {len(videos_to_process)} videos to process")
        
        # Batch download audio on Ultron
        video_ids = [v["video"]["id"] for v in videos_to_process]
        
        logger.info(f"\n  Batch downloading {len(video_ids)} audio files...")
        download_job = ultron.batch_download_audio(video_ids)
        if download_job:
            download_result = ultron.poll_job(download_job, max_wait=600, interval=10)
            logger.info(f"  Audio download: {download_result.get('successes', 0)}/{len(video_ids)} succeeded")
        
        # Batch transcribe on Ultron
        logger.info(f"\n  Batch transcribing {len(video_ids)} videos...")
        transcribe_job = ultron.batch_transcribe(video_ids)
        if transcribe_job:
            transcribe_result = ultron.poll_job(transcribe_job, max_wait=1800, interval=15)
            logger.info(f"  Transcription: {transcribe_result.get('successes', 0)}/{len(video_ids)} succeeded")
        
        # Fetch all transcripts
        transcripts = ultron.get_transcripts(video_ids)
        
        # Attach transcripts to video data
        for item in videos_to_process:
            vid = item["video"]["id"]
            if vid in transcripts:
                item["transcript"] = transcripts[vid]
        
        return videos_to_process
    
    def phase2_analyze_all(self, videos: List[Dict]) -> List[Dict]:
        """
        PHASE 2: Analyze all transcripts with Grok.
        Score every video for viral potential.
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"PHASE 2: ANALYZING {len(videos)} TRANSCRIPTS")
        logger.info(f"{'='*60}\n")
        
        all_highlights = []
        
        for item in videos:
            channel = item["channel"]
            video = item["video"]
            transcript = item.get("transcript", {})
            
            if not transcript.get("text"):
                logger.warning(f"  [{channel['name']}] No transcript, skipping")
                continue
            
            # Build timestamped transcript for Grok
            segments = transcript.get("segments", [])
            timestamped = "\n".join([f"[{s['start']:.1f}s] {s['text']}" for s in segments])
            
            logger.info(f"  Analyzing: {channel['name']}...")
            highlight = self.analyze_with_grok(timestamped, channel, video.get("title", ""))
            
            if highlight:
                highlight["channel_name"] = channel["name"]
                highlight["channel_handle"] = channel.get("handle", "")
                highlight["video_id"] = video["id"]
                highlight["video_title"] = video.get("title", "")
                highlight["channel_tags"] = channel.get("tags", [])
                
                all_highlights.append(highlight)
                logger.info(f"    → Score: {highlight.get('hook_score', 0)} | "
                           f"Quote: {highlight.get('key_quote', '')[:50]}...")
            else:
                logger.warning(f"    → Analysis failed")
        
        self.all_highlights = all_highlights
        return all_highlights
    
    def phase3_select_top(self, highlights: List[Dict]) -> List[Dict]:
        """
        PHASE 3: Select top N highlights for video.
        Ensures diversity (max 2 per channel) and quality threshold.
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"PHASE 3: SELECTING TOP CLIPS")
        logger.info(f"{'='*60}\n")
        
        settings = self.settings
        min_score = settings.get("min_hook_score", 60)
        top_n = settings.get("top_clips_for_video", 5)
        
        # Filter by minimum score
        qualified = [h for h in highlights if h.get("hook_score", 0) >= min_score]
        logger.info(f"  {len(qualified)}/{len(highlights)} meet minimum score ({min_score})")
        
        # Sort by score
        qualified.sort(key=lambda x: x.get("hook_score", 0), reverse=True)
        
        # Select with diversity constraint (max 2 per channel)
        selected = []
        channel_counts = {}
        
        for h in qualified:
            channel = h["channel_name"]
            if channel_counts.get(channel, 0) >= 2:
                continue
            
            selected.append(h)
            channel_counts[channel] = channel_counts.get(channel, 0) + 1
            
            if len(selected) >= top_n:
                break
        
        logger.info(f"\n  Selected {len(selected)} clips for video:")
        for i, h in enumerate(selected):
            logger.info(f"    {i+1}. [{h['channel_name']}] Score: {h['hook_score']} — {h['key_quote'][:40]}...")
        
        self.selected_highlights = selected
        return selected
    
    def phase4_produce_video(self, selected: List[Dict]) -> Dict:
        """
        PHASE 4: Produce horizontal highlight reel + vertical shorts.
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"PHASE 4: PRODUCING VIDEO CONTENT")
        logger.info(f"{'='*60}\n")
        
        # Download full videos for selected clips
        logger.info("  Downloading full videos for clips...")
        for h in selected:
            result = ultron.download_video(h["video_id"])
            if result and result.get("success"):
                logger.info(f"    ✓ {h['channel_name']}")
            else:
                logger.warning(f"    ✗ {h['channel_name']} download failed")
        
        # Extract clips
        logger.info("\n  Extracting clips...")
        for i, h in enumerate(selected):
            clip_name = f"pulse_{self.today}_{h['channel_name'].replace(' ', '_')}"
            result = ultron.extract_clip(
                h["video_id"],
                h["start_time"],
                h["end_time"],
                clip_name
            )
            if result and result.get("success"):
                h["clip_path"] = result.get("path", "")
                h["clip_filename"] = f"{clip_name}.mp4"
                logger.info(f"    ✓ Clip {i+1}: {h['channel_name']}")
            else:
                logger.warning(f"    ✗ Clip {i+1}: {h['channel_name']} failed")
        
        # Generate voiceovers
        logger.info("\n  Generating voiceovers...")
        from services.video_engine.assemble_pulse import generate_voiceover
        
        # Intro
        top_theme = self._get_top_theme(selected)
        intro_text = f"Welcome to your Pulse Check for {self.date_display}. {top_theme}"
        intro_path = generate_voiceover(intro_text, f"pulse_{self.today}_intro")
        if intro_path:
            ultron.upload_voiceover(str(intro_path), f"pulse_{self.today}_intro.mp3")
        
        # Transitions
        for i, h in enumerate(selected):
            trans_text = h.get("narrator_intro", f"Here's {h['channel_name']}.")
            trans_path = generate_voiceover(trans_text, f"pulse_{self.today}_trans_{i}")
            if trans_path:
                ultron.upload_voiceover(str(trans_path), f"pulse_{self.today}_trans_{i}.mp3")
                h["voiceover_file"] = f"pulse_{self.today}_trans_{i}.mp3"
        
        # Outro
        outro_text = "That's your Pulse Check for today. Stay sovereign, stack sats."
        outro_path = generate_voiceover(outro_text, f"pulse_{self.today}_outro")
        if outro_path:
            ultron.upload_voiceover(str(outro_path), f"pulse_{self.today}_outro.mp3")
        
        # Assemble horizontal video
        logger.info("\n  Assembling horizontal highlight reel...")
        manifest = {
            "output_name": f"pulse_check_{self.today}.mp4",
            "intro_voiceover": f"pulse_{self.today}_intro.mp3",
            "outro_voiceover": f"pulse_{self.today}_outro.mp3",
            "tag_video": "tag.mp4",
            "segments": [
                {
                    "clip": h.get("clip_filename", ""),
                    "voiceover": h.get("voiceover_file", ""),
                    "channel_name": h["channel_name"],
                    "lower_third_text": h["channel_name"]
                }
                for h in selected if h.get("clip_filename")
            ]
        }
        
        assembly_job = ultron.assemble_advanced(manifest)
        horizontal_result = None
        if assembly_job:
            horizontal_result = ultron.poll_job(assembly_job, max_wait=600, interval=10)
            if horizontal_result and horizontal_result.get("status") == "complete":
                # Download to Replit
                ultron.download_output(f"pulse_check_{self.today}.mp4", str(OUTPUT_DIR))
                logger.info(f"    ✓ Horizontal reel complete")
        
        # Generate vertical shorts
        logger.info("\n  Generating vertical shorts...")
        shorts = []
        for i, h in enumerate(selected):
            if not h.get("clip_filename"):
                continue
            
            params = {
                "clip": h["clip_filename"],
                "output_name": f"short_{self.today}_{h['channel_name'].replace(' ', '_')}.mp4",
                "channel_name": h["channel_name"],
                "caption_text": h.get("vertical_caption", h.get("key_quote", "")[:60])
            }
            
            job_id = ultron.generate_vertical(params)
            if job_id:
                result = ultron.poll_job(job_id, max_wait=180, interval=5)
                if result and result.get("status") == "complete":
                    ultron.download_short(params["output_name"], str(SHORTS_DIR))
                    shorts.append(params["output_name"])
                    logger.info(f"    ✓ Short {i+1}: {h['channel_name']}")
        
        return {
            "horizontal": f"pulse_check_{self.today}.mp4",
            "shorts": shorts,
            "clips_used": len([h for h in selected if h.get("clip_filename")])
        }
    
    def phase5_output_intel(self) -> Dict:
        """
        PHASE 5: Output intelligence feeds for other systems.
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"PHASE 5: GENERATING INTELLIGENCE FEEDS")
        logger.info(f"{'='*60}\n")
        
        # Daily intel (for articles/newsletter)
        daily_intel = {
            "date": self.today,
            "channels_scanned": len(self.channels),
            "videos_analyzed": len(self.all_highlights),
            "clips_produced": len(self.selected_highlights),
            "highlights": [
                {
                    "channel": h["channel_name"],
                    "channel_handle": h.get("channel_handle", ""),
                    "video_title": h.get("video_title", ""),
                    "video_id": h.get("video_id", ""),
                    "key_quote": h.get("key_quote", ""),
                    "hook_score": h.get("hook_score", 0),
                    "themes": h.get("themes", []),
                    "summary": h.get("summary", ""),
                    "tweet_text": h.get("tweet_text", ""),
                    "used_in_video": h in self.selected_highlights
                }
                for h in self.all_highlights
            ],
            "themes_today": self._aggregate_themes(),
            "top_quote": self.selected_highlights[0].get("key_quote", "") if self.selected_highlights else ""
        }
        
        intel_path = INTEL_DIR / f"daily_intel_{self.today}.json"
        intel_path.write_text(json.dumps(daily_intel, indent=2))
        logger.info(f"  ✓ daily_intel.json ({len(self.all_highlights)} highlights)")
        
        # Tweet queue
        tweets = []
        for h in self.all_highlights:
            if h.get("tweet_text"):
                tweets.append({
                    "text": h["tweet_text"],
                    "source_channel": h["channel_name"],
                    "hook_score": h.get("hook_score", 0),
                    "themes": h.get("themes", [])
                })
        
        tweet_path = INTEL_DIR / f"tweet_queue_{self.today}.json"
        tweet_path.write_text(json.dumps({"date": self.today, "tweets": tweets}, indent=2))
        logger.info(f"  ✓ tweet_queue.json ({len(tweets)} tweets)")
        
        # Newsletter digest
        newsletter = {
            "date": self.today,
            "date_display": self.date_display,
            "themes": self._aggregate_themes(),
            "top_highlights": [
                {
                    "channel": h["channel_name"],
                    "quote": h.get("key_quote", ""),
                    "summary": h.get("summary", "")
                }
                for h in sorted(self.all_highlights, key=lambda x: x.get("hook_score", 0), reverse=True)[:7]
            ],
            "video_link": f"https://youtube.com/watch?v=PLACEHOLDER_{self.today}"
        }
        
        newsletter_path = INTEL_DIR / f"newsletter_digest_{self.today}.json"
        newsletter_path.write_text(json.dumps(newsletter, indent=2))
        logger.info(f"  ✓ newsletter_digest.json")
        
        return {
            "daily_intel": str(intel_path),
            "tweet_queue": str(tweet_path),
            "newsletter_digest": str(newsletter_path)
        }
    
    def _get_top_theme(self, highlights: List[Dict]) -> str:
        """Generate a theme summary for the intro."""
        themes = self._aggregate_themes()
        if themes:
            return f"Today's focus: {', '.join(themes[:2])}."
        return "Here's what's making waves in Bitcoin."
    
    def _aggregate_themes(self) -> List[str]:
        """Aggregate and count themes across all highlights."""
        theme_counts = {}
        for h in self.all_highlights:
            for theme in h.get("themes", []):
                theme_counts[theme] = theme_counts.get(theme, 0) + 1
        
        sorted_themes = sorted(theme_counts.items(), key=lambda x: x[1], reverse=True)
        return [t[0] for t in sorted_themes[:5]]
    
    def run(self) -> Dict:
        """Execute the full intelligence pipeline."""
        logger.info(f"\n{'='*70}")
        logger.info(f"  PULSE CHECK INTELLIGENCE PIPELINE")
        logger.info(f"  Date: {self.today}")
        logger.info(f"  Run ID: {self.run_id}")
        logger.info(f"  Channels: {len(self.channels)}")
        logger.info(f"{'='*70}\n")
        
        # Check Ultron
        health = ultron.health_check()
        if health.get("status") != "ok":
            logger.error(f"Ultron offline: {health}")
            return {"error": "Ultron offline"}
        logger.info(f"Ultron: {health.get('gpu_count', 0)} GPUs online")
        
        # Phase 1: Scan all channels
        videos = self.phase1_scan_all()
        if not videos:
            return {"error": "No videos to process"}
        
        # Phase 2: Analyze all transcripts
        highlights = self.phase2_analyze_all(videos)
        if not highlights:
            return {"error": "No highlights found"}
        
        # Phase 3: Select top clips
        selected = self.phase3_select_top(highlights)
        if not selected:
            return {"error": "No clips met quality threshold"}
        
        # Phase 4: Produce video content
        video_result = self.phase4_produce_video(selected)
        
        # Phase 5: Output intelligence feeds
        intel_result = self.phase5_output_intel()
        
        # Summary
        result = {
            "status": "complete",
            "run_id": self.run_id,
            "date": self.today,
            "channels_scanned": len(self.channels),
            "videos_analyzed": len(self.all_highlights),
            "clips_selected": len(self.selected_highlights),
            "video": video_result,
            "intel": intel_result
        }
        
        logger.info(f"\n{'='*70}")
        logger.info(f"  PIPELINE COMPLETE")
        logger.info(f"  Scanned: {len(self.channels)} channels")
        logger.info(f"  Analyzed: {len(self.all_highlights)} videos")
        logger.info(f"  Produced: {video_result.get('clips_used', 0)} clips")
        logger.info(f"  Shorts: {len(video_result.get('shorts', []))}")
        logger.info(f"{'='*70}\n")
        
        return result


if __name__ == "__main__":
    pipeline = IntelligencePipeline()
    result = pipeline.run()
    print(json.dumps(result, indent=2))
```

---

# AGENT INSTRUCTIONS

## For Claude Code / OpenHands / Aider

When implementing this system, follow these phases:

### Phase 1: Infrastructure Setup

```
TASK: Set up Ultron API server v3

1. SSH into Ultron:
   ssh ultron

2. Navigate to video engine:
   cd ~/video_engine

3. Backup existing api_server.py:
   cp api_server.py api_server.py.backup

4. Create new api_server.py with v3 code from this spec

5. Create helper modules:
   - advanced_assembly.py (extract assembly logic)
   - vertical_generator.py (extract vertical logic)

6. Install any missing dependencies:
   pip install flask faster-whisper torch yt-dlp

7. Restart the service:
   sudo systemctl restart video-engine

8. Verify health:
   curl https://video.protocolpulse.io/health
```

### Phase 2: Replit Configuration

```
TASK: Set up config-driven channel system

1. Create config directory:
   mkdir -p config

2. Create config/partner_channels.json with channel list

3. Create services/config_loader.py

4. Test config loading:
   python -c "from services.config_loader import get_enabled_channels; print(len(get_enabled_channels()))"
```

### Phase 3: Intelligence Pipeline

```
TASK: Implement intelligence pipeline

1. Create services/video_engine/intelligence_pipeline.py

2. Update ultron_client.py with batch methods:
   - batch_download_audio()
   - batch_transcribe()
   - get_transcripts()

3. Create intel output directory:
   mkdir -p data/video_engine/intel

4. Test pipeline (dry run):
   python -m services.video_engine.intelligence_pipeline
```

### Phase 4: Dashboard & Automation

```
TASK: Add dashboard and scheduling

1. Create/update dashboard:
   services/video_engine/dashboard/app.py
   services/video_engine/dashboard/templates/dashboard.html

2. Create scheduler:
   services/video_engine/scheduler.py

3. Wire into main app

4. Test dashboard:
   python -m services.video_engine.dashboard.app
```

### Phase 5: Distribution

```
TASK: Implement multi-platform distribution

1. Update pulse_distributor.py with:
   - Twitter horizontal post
   - YouTube horizontal upload
   - YouTube Shorts upload

2. Add environment variables for each platform

3. Test distribution (dry run with ENABLE_* = false)
```

---

# ENVIRONMENT VARIABLES

```bash
# === Ultron Connection ===
ULTRON_HOST=video.protocolpulse.io
ULTRON_IP=104.16.230.132
ULTRON_API_TOKEN=<generate-strong-token>

# === AI Services ===
XAI_API_KEY=xai-xxxxx
ELEVENLABS_API_KEY=xxxxx
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM

# === Twitter/X ===
TWITTER_API_KEY=xxxxx
TWITTER_API_SECRET=xxxxx
TWITTER_ACCESS_TOKEN=xxxxx
TWITTER_ACCESS_TOKEN_SECRET=xxxxx
ENABLE_TWEETS=false

# === YouTube ===
YOUTUBE_CLIENT_ID=xxxxx
YOUTUBE_CLIENT_SECRET=xxxxx
YOUTUBE_REFRESH_TOKEN=xxxxx
ENABLE_YT_PULSE=false
ENABLE_YT_SHORTS=false

# === Scheduling ===
PULSE_RUN_HOUR=10
PULSE_RUN_TZ=America/New_York
```

---

# DEPLOYMENT CHECKLIST

## Ultron Setup
- [ ] Update api_server.py to v3
- [ ] Create helper modules (advanced_assembly.py, vertical_generator.py)
- [ ] Set ULTRON_API_TOKEN environment variable
- [ ] Restart video-engine service
- [ ] Verify /health endpoint returns v3

## Replit Setup
- [ ] Create config/partner_channels.json
- [ ] Create services/config_loader.py
- [ ] Create services/video_engine/intelligence_pipeline.py
- [ ] Update services/video_engine/ultron_client.py with batch methods
- [ ] Create data/video_engine/intel directory
- [ ] Set all environment variables
- [ ] Test pipeline with single channel first

## First Run
- [ ] Run pipeline manually: `python -m services.video_engine.intelligence_pipeline`
- [ ] Verify intel outputs in data/video_engine/intel/
- [ ] Verify video outputs in data/video_engine/output/
- [ ] Check Ultron disk usage after run

## Automation
- [ ] Set up APScheduler in scheduler.py
- [ ] Configure run time (default 10 AM ET)
- [ ] Enable dashboard for monitoring
- [ ] Set up alerting for failures (optional: Telegram/Discord)

---

**END OF SPEC V3**
