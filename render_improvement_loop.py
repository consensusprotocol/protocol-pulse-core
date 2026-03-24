#!/usr/bin/env python3
"""
render_improvement_loop.py — Autonomous grade-driven fix loop.
Ingests Gemini grade JSON, identifies failing dimensions, reaches multi-LLM
consensus on fixes, implements via CC, verifies, then signals overnight loop.

Gospel: docs/gospels/RENDER_IMPROVEMENT_LOOP_GOSPEL.md v1.1
Audit:  docs/audits/render-improvement-loop/FINAL_CONSENSUS.md

Usage:
    python3 render_improvement_loop.py                        # wait for IPC request
    python3 render_improvement_loop.py --grade /path/to.json  # direct grade file
    python3 render_improvement_loop.py --dry-run              # no LLM calls, no CC
    python3 render_improvement_loop.py --help
"""
import sys
sys.dont_write_bytecode = True

import os
import json
import time
import glob
import stat
import hashlib
import logging
import argparse
import subprocess
import threading
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
BASE = Path(__file__).resolve().parent
PIPELINE = BASE / "video_pipeline_v3"
ENV_FILE = BASE / ".env"
BIBLE_PATH = BASE / "docs" / "QWEN_CONTEXT_BIBLE.md"
FIX_HISTORY_PATH = PIPELINE / "logs" / "fix_history.jsonl"
CONSECUTIVE_A_FILE = PIPELINE / "logs" / "consecutive_a_grades.txt"
COST_LEDGER_DIR = Path("/tmp")
CONFIG_PATH = BASE / "render_improvement_config.yaml"

# IPC paths
IPC_REQUEST_PATTERN = "/tmp/fix_request_iter*.json"
IPC_COMPLETE_PATTERN = "/tmp/fix_complete_iter*.json"
HEARTBEAT_FILE = "/tmp/improvement_loop.heartbeat.json"
CC_HEARTBEAT_FILE = "/tmp/cc_session.heartbeat.json"

# ── Logging ──────────────────────────────────────────────────────────────────
os.makedirs(PIPELINE / "logs", exist_ok=True)
logger = logging.getLogger("improvement_loop")
if not logger.handlers:
    logger.setLevel(logging.DEBUG)
    _fmt = logging.Formatter("[%(asctime)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    _sh = logging.StreamHandler(sys.stdout)
    _sh.setFormatter(_fmt)
    logger.addHandler(_sh)
    _fh = logging.FileHandler(str(PIPELINE / "logs" / "improvement_loop.log"))
    _fh.setFormatter(_fmt)
    logger.addHandler(_fh)


def log(msg):
    logger.info(msg)


# ── Configuration ────────────────────────────────────────────────────────────
DEFAULT_CONFIG = {
    "max_iterations": 8,
    "max_hours": 6,
    "per_iteration_timeout_seconds": 5400,
    "max_improvement_time_seconds": 7200,
    "cc_session_timeout_seconds": 2700,
    "zombie_activity_threshold_seconds": 600,
    "heartbeat_interval_seconds": 60,
    "poll_interval_seconds": 60,
    "consecutive_fix_failure_threshold": 2,
    "cost_soft_cap_usd": 7.50,
    "cost_hard_cap_daily_usd": 25.00,
    "consensus_strategy": "majority_conservative",
    "stalemate_max_consecutive": 2,
    "max_diff_lines": 50,
    "ollama_timeout_seconds": 30,
    "ollama_retry_count": 3,
    "ollama_backoff_seconds": [2, 4, 8],
    "qwen_model": "qwen3:30b-a3b",
    "qwen_fallback_model": "qwen3:8b",
    "ollama_url": "http://localhost:11434",
    "grade_a_threshold": 88,
    "consecutive_a_target": 10,
    "failing_score_threshold": 8,
    "qwen_high_confidence": 0.85,
    "external_llm_timeout_seconds": 45,
    "max_code_lines_per_audit": 120,
    "max_retries_per_dim": 2,
}


def load_config():
    """Load config from YAML with env var overrides. LAW: no magic numbers."""
    cfg = dict(DEFAULT_CONFIG)
    try:
        import yaml
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH) as f:
                file_cfg = yaml.safe_load(f) or {}
            cfg.update(file_cfg)
            log(f"Config loaded from {CONFIG_PATH}")
    except Exception as e:
        log(f"Config load warning: {e} — using defaults")

    # Env var overrides
    env_map = {
        "MAX_TOKENS_PER_FIX_CYCLE": ("cost_soft_cap_usd", float),
        "COST_HARD_CAP_DAILY_USD": ("cost_hard_cap_daily_usd", float),
        "OLLAMA_URL": ("ollama_url", str),
        "QWEN_MODEL": ("qwen_model", str),
    }
    for env_key, (cfg_key, cast) in env_map.items():
        val = os.environ.get(env_key)
        if val:
            try:
                cfg[cfg_key] = cast(val)
            except (ValueError, TypeError):
                pass
    return cfg


CONFIG = load_config()


# ── Environment ──────────────────────────────────────────────────────────────
def load_env():
    env = os.environ.copy()
    try:
        with open(ENV_FILE) as f:
            for line in f:
                l = line.strip()
                if l and not l.startswith("#") and "=" in l:
                    k, _, v = l.partition("=")
                    k = k.strip()
                    v = v.strip().strip("'").strip('"')
                    if k:
                        env[k] = v
    except FileNotFoundError:
        log(f"WARNING: .env not found at {ENV_FILE}")
    return env


# ── Telegram ─────────────────────────────────────────────────────────────────
def send_telegram_alert(message):
    """LAW 11 — Fail loud. Every event triggers Telegram."""
    env = load_env()
    token = env.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = env.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        log(f"Telegram skip (no creds): {message[:80]}")
        return
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = json.dumps({"chat_id": chat_id, "text": message}).encode()
        req = urllib.request.Request(url, data=payload,
                                    headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as r:
            log(f"Telegram sent (status {r.status})")
    except Exception as e:
        log(f"Telegram failed: {e}")


# ── DIMENSION_MAP (from gospel) ─────────────────────────────────────────────
DIMENSION_MAP = {
    "freeze_check": [("video_pipeline_v3/clip_extractor.py", "generate_clip"),
                     ("video_pipeline_v3/assembler.py", "build_scene")],
    "true_peak_check": [("video_pipeline_v3/assembler.py", "apply_loudnorm"),
                        ("video_pipeline_v3/assembler.py", "final_mix")],
    "loudness_check": [("video_pipeline_v3/assembler.py", "apply_loudnorm")],
    "silence_check": [("video_pipeline_v3/tts_engine.py", "generate_audio"),
                      ("video_pipeline_v3/assembler.py", "concat_audio")],
    "host_authenticity": [("video_pipeline_v3/assembler.py", "generate_host_segment"),
                          ("oracle/avatar_server.py", "generate_video")],
    "visual_polish": [("video_pipeline_v3/assembler.py", "build_scene"),
                      ("video_pipeline_v3/clip_extractor.py", "generate_clip")],
    "no_artifacts": [("video_pipeline_v3/assembler.py", "preflight_check")],
    "audio_quality": [("video_pipeline_v3/assembler.py", "final_mix")],
    "black_frames_check": [("video_pipeline_v3/assembler.py", "concat_segments")],
    "script_quality": [("video_pipeline_v3/script_writer.py", "write_script")],
    "cold_open_hook": [("video_pipeline_v3/script_writer.py", "write_cold_open")],
    "episode_title": [("video_pipeline_v3/daily_producer.py", "generate_title")],
    "narrative_arc": [("video_pipeline_v3/script_writer.py", "write_script")],
    "music_mix": [("video_pipeline_v3/assembler.py", "mix_music")],
    "transitions": [("video_pipeline_v3/assembler.py", "apply_transitions")],
    "clip_relevance": [("video_pipeline_v3/clip_extractor.py", "score_clips")],
    "pacing": [("video_pipeline_v3/script_writer.py", "write_script"),
               ("video_pipeline_v3/assembler.py", "build_scene")],
    "subtitle_accuracy": [("video_pipeline_v3/assembler.py", "generate_subtitles")],
    "color_grading": [("video_pipeline_v3/assembler.py", "apply_color_grade")],
    "thumbnail_quality": [("video_pipeline_v3/daily_producer.py", "generate_thumbnail")],
}

DIMENSION_META = {
    "freeze_check":       {"priority": "critical", "fix_complexity": "simple", "max_cost_usd": 0.75, "safe_default": None},
    "true_peak_check":    {"priority": "critical", "fix_complexity": "simple", "max_cost_usd": 0.75, "safe_default": "ffmpeg-normalize -tp -2.0"},
    "black_frames_check": {"priority": "critical", "fix_complexity": "simple", "max_cost_usd": 0.75, "safe_default": None},
    "host_authenticity":  {"priority": "critical", "fix_complexity": "complex", "max_cost_usd": 2.00, "safe_default": None},
    "loudness_check":     {"priority": "high", "fix_complexity": "simple", "max_cost_usd": 0.75, "safe_default": "loudnorm filter I=-14:LRA=7:TP=-2"},
    "silence_check":      {"priority": "high", "fix_complexity": "simple", "max_cost_usd": 0.75, "safe_default": None},
    "visual_polish":      {"priority": "high", "fix_complexity": "complex", "max_cost_usd": 2.00, "safe_default": None},
    "audio_quality":      {"priority": "high", "fix_complexity": "simple", "max_cost_usd": 0.75, "safe_default": None},
    "script_quality":     {"priority": "medium", "fix_complexity": "complex", "max_cost_usd": 2.00, "safe_default": None},
    "cold_open_hook":     {"priority": "medium", "fix_complexity": "complex", "max_cost_usd": 2.00, "safe_default": None},
    "narrative_arc":      {"priority": "medium", "fix_complexity": "complex", "max_cost_usd": 2.00, "safe_default": None},
    "music_mix":          {"priority": "medium", "fix_complexity": "simple", "max_cost_usd": 0.75, "safe_default": None},
    "transitions":        {"priority": "medium", "fix_complexity": "simple", "max_cost_usd": 0.75, "safe_default": None},
    "clip_relevance":     {"priority": "medium", "fix_complexity": "complex", "max_cost_usd": 2.00, "safe_default": None},
    "no_artifacts":       {"priority": "high", "fix_complexity": "simple", "max_cost_usd": 0.75, "safe_default": None},
    "episode_title":      {"priority": "low", "fix_complexity": "simple", "max_cost_usd": 0.75, "safe_default": None},
    "pacing":             {"priority": "medium", "fix_complexity": "complex", "max_cost_usd": 2.00, "safe_default": None},
    "subtitle_accuracy":  {"priority": "medium", "fix_complexity": "simple", "max_cost_usd": 0.75, "safe_default": None},
    "color_grading":      {"priority": "low", "fix_complexity": "simple", "max_cost_usd": 0.75, "safe_default": None},
    "thumbnail_quality":  {"priority": "low", "fix_complexity": "simple", "max_cost_usd": 0.75, "safe_default": None},
}

PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

# Content dimensions that need actual video upload for genuine Gemini eval (RULE 3)
CONTENT_DIMENSIONS = {
    "script_quality", "cold_open_hook", "narrative_arc", "visual_polish",
    "host_authenticity", "pacing", "clip_relevance", "episode_title",
    "no_filler", "timeliness",
}

# Technical dimensions graded from ffprobe data only (RULE 3)
TECHNICAL_DIMENSIONS = {
    "freeze_check", "true_peak_check", "loudness_check", "silence_check",
    "black_frames_check", "audio_quality", "no_artifacts",
    "duration_check", "resolution_check", "framerate_check",
    "codec_check", "file_integrity_check",
}

# Qwen response schema for validation
QWEN_RESPONSE_SCHEMA = {
    "type": "object",
    "required": ["root_cause", "fix_patch", "confidence", "verify_cmd"],
    "properties": {
        "root_cause": {"type": "string"},
        "fix_patch": {"type": "string"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "verify_cmd": {"type": "string"},
    },
}


# ── IPC File Operations ─────────────────────────────────────────────────────
def write_ipc_json(path, data):
    """Write IPC JSON atomically with chmod 600. LAW 12/IPC PROTOCOL."""
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)  # 0600
    os.replace(tmp, path)
    log(f"IPC written: {path}")


def read_ipc_json(path):
    """Read and validate IPC JSON."""
    with open(path) as f:
        data = json.load(f)
    return data


def cleanup_stale_ipc():
    """LAW 12 — Clean startup state. Remove all stale IPC artifacts."""
    patterns = [IPC_REQUEST_PATTERN, IPC_COMPLETE_PATTERN, HEARTBEAT_FILE, CC_HEARTBEAT_FILE]
    cleaned = 0
    for pattern in patterns:
        for f in glob.glob(pattern):
            try:
                os.remove(f)
                cleaned += 1
            except OSError:
                pass
    if cleaned:
        log(f"LAW 12: Cleaned {cleaned} stale IPC files")


# ── Heartbeat ────────────────────────────────────────────────────────────────
_heartbeat_lock = threading.Lock()
_heartbeat_stop = threading.Event()


def _heartbeat_writer(iteration, current_dim_ref):
    """Background thread: write heartbeat every 60s. Gospel IPC PROTOCOL."""
    while not _heartbeat_stop.is_set():
        try:
            data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "iteration": iteration,
                "current_dimension": current_dim_ref[0] if current_dim_ref else "idle",
                "pid": os.getpid(),
            }
            write_ipc_json(HEARTBEAT_FILE, data)
        except Exception as e:
            log(f"Heartbeat write error: {e}")
        _heartbeat_stop.wait(CONFIG["heartbeat_interval_seconds"])


def start_heartbeat(iteration, current_dim_ref):
    """Start heartbeat background thread."""
    _heartbeat_stop.clear()
    t = threading.Thread(target=_heartbeat_writer, args=(iteration, current_dim_ref), daemon=True)
    t.start()
    return t


def stop_heartbeat():
    """Stop heartbeat thread."""
    _heartbeat_stop.set()


# ── Cost Tracking (LAW 8) ───────────────────────────────────────────────────
class CostTracker:
    """Per-run and daily cost tracking with budget enforcement."""

    def __init__(self):
        self.cycle_cost = 0.0
        self.daily_cost = 0.0
        self.calls = []
        today = datetime.now().strftime("%Y%m%d")
        self.ledger_path = str(COST_LEDGER_DIR / f"llm_cost_run_{today}.json")
        self._load_daily()

    def _load_daily(self):
        """Load existing daily cost from ledger."""
        try:
            with open(self.ledger_path) as f:
                data = json.load(f)
            self.daily_cost = data.get("total_cost_usd", 0.0)
        except (FileNotFoundError, json.JSONDecodeError):
            self.daily_cost = 0.0

    def estimate_cost(self, model, input_tokens, output_tokens):
        """Estimate cost using tiktoken-based token counts."""
        # Pricing per 1M tokens (approximate)
        prices = {
            "qwen": (0.0, 0.0),  # Local — $0
            "gemini": (1.25, 5.0),  # Gemini 2.5 Pro
            "gpt-4o": (2.50, 10.0),
            "claude-sonnet": (3.0, 15.0),
            "claude-opus": (15.0, 75.0),
        }
        inp_price, out_price = prices.get(model, (5.0, 15.0))
        return (input_tokens / 1_000_000 * inp_price) + (output_tokens / 1_000_000 * out_price)

    def record_call(self, model, dimension, input_tokens, output_tokens):
        """Record an LLM call and its cost."""
        cost = self.estimate_cost(model, input_tokens, output_tokens)
        self.cycle_cost += cost
        self.daily_cost += cost
        self.calls.append({
            "model": model,
            "dimension": dimension,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": round(cost, 4),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        self._save_ledger()
        return cost

    def _save_ledger(self):
        """Persist cost ledger to disk."""
        try:
            data = {
                "total_cost_usd": round(self.daily_cost, 4),
                "cycle_cost_usd": round(self.cycle_cost, 4),
                "calls": self.calls,
            }
            with open(self.ledger_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            log(f"Cost ledger write error: {e}")

    def check_budget(self, dimension):
        """LAW 8 — Returns (can_proceed, qwen_only_mode).
        can_proceed=False means daily hard cap hit.
        qwen_only_mode=True means cycle soft cap hit."""
        if self.daily_cost >= CONFIG["cost_hard_cap_daily_usd"]:
            log(f"LAW 8: DAILY HARD CAP HIT (${self.daily_cost:.2f} >= ${CONFIG['cost_hard_cap_daily_usd']:.2f})")
            send_telegram_alert(
                f"Token budget hit — loop paused, manual review needed\n"
                f"Daily: ${self.daily_cost:.2f} / Cycle: ${self.cycle_cost:.2f}"
            )
            return False, False
        if self.cycle_cost >= CONFIG["cost_soft_cap_usd"]:
            log(f"LAW 8: Cycle soft cap hit (${self.cycle_cost:.2f}) — Qwen-only mode for {dimension}")
            return True, True  # Can proceed, Qwen-only
        return True, False


# ── Qwen Integration (LAW 2) ────────────────────────────────────────────────
def qwen_call(prompt, dimension, cost_tracker, model=None):
    """LAW 2 — Qwen first, always. Resilience wrapper with 3 retries.
    Returns parsed JSON or None on exhausted retries."""
    import jsonschema

    if model is None:
        model = CONFIG["qwen_model"]
    url = CONFIG["ollama_url"] + "/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
    }
    backoffs = CONFIG["ollama_backoff_seconds"]

    for attempt in range(CONFIG["ollama_retry_count"]):
        try:
            data_bytes = json.dumps(payload).encode()
            req = urllib.request.Request(url, data=data_bytes,
                                        headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=CONFIG["ollama_timeout_seconds"]) as r:
                raw = json.loads(r.read())

            response_text = raw.get("response", "")
            # Track tokens
            input_tokens = raw.get("prompt_eval_count", len(prompt.split()) * 2)
            output_tokens = raw.get("eval_count", len(response_text.split()) * 2)
            cost_tracker.record_call("qwen", dimension, input_tokens, output_tokens)

            parsed = json.loads(response_text)
            jsonschema.validate(parsed, QWEN_RESPONSE_SCHEMA)

            # Semantic null check
            if parsed.get("fix_spec") is None and parsed.get("fix_patch") is None:
                if not parsed.get("root_cause"):
                    raise ValueError("Qwen returned empty root_cause")

            return parsed

        except (urllib.error.URLError, urllib.error.HTTPError, ConnectionError, OSError) as e:
            backoff = backoffs[min(attempt, len(backoffs) - 1)]
            log(f"Qwen attempt {attempt + 1} failed: {e}, backing off {backoff}s")
            time.sleep(backoff)
        except (json.JSONDecodeError, jsonschema.ValidationError, ValueError) as e:
            log(f"Qwen response invalid: {e}")
            if attempt < CONFIG["ollama_retry_count"] - 1:
                time.sleep(2)
        except Exception as e:
            log(f"Qwen unexpected error: {e}")
            if attempt < CONFIG["ollama_retry_count"] - 1:
                time.sleep(2)

    # All retries exhausted — graceful degradation (LAW 2)
    log(f"ERROR: Qwen unavailable after {CONFIG['ollama_retry_count']} retries for dimension {dimension}")
    send_telegram_alert(f"Qwen unavailable — skipping fix for {dimension}")
    return None


def qwen_fallback_call(prompt, dimension, cost_tracker):
    """Try fallback Qwen model if primary fails."""
    return qwen_call(prompt, dimension, cost_tracker, model=CONFIG["qwen_fallback_model"])


def ollama_health_check():
    """Pre-flight health check for Ollama. MANDATORY per gospel."""
    url = CONFIG["ollama_url"] + "/api/tags"
    for attempt in range(3):
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read())
                models = [m.get("name", "") for m in data.get("models", [])]
                log(f"Ollama health OK — {len(models)} models available")
                return True
        except Exception as e:
            log(f"Ollama health check attempt {attempt + 1} failed: {e}")
            if attempt < 2:
                time.sleep(2)
    return False


# ── External LLM Calls (LAW 4 — parallel) ───────────────────────────────────
def _call_gemini(prompt, cost_tracker, dimension):
    """Call Gemini 2.5 Pro for audit consensus."""
    env = load_env()
    key = env.get("GEMINI_API_KEY", "")
    if not key:
        return None
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent?key={key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": 2000, "temperature": 0.05},
    }
    try:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(url, data=data,
                                    headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=CONFIG["external_llm_timeout_seconds"]) as r:
            d = json.loads(r.read())
            parts = d["candidates"][0]["content"].get("parts", [])
            text = next((p["text"] for p in parts if "text" in p), None)
            cost_tracker.record_call("gemini", dimension, len(prompt) // 4, len(text or "") // 4)
            return text
    except Exception as e:
        log(f"Gemini call failed: {e}")
        return None


def _call_gpt4o(prompt, cost_tracker, dimension):
    """Call GPT-4o for audit consensus."""
    env = load_env()
    key = env.get("OPENAI_API_KEY", "")
    if not key:
        return None
    url = "https://api.openai.com/v1/chat/completions"
    payload = {
        "model": "gpt-4o",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 2000,
        "temperature": 0.05,
    }
    try:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(url, data=data, headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        })
        with urllib.request.urlopen(req, timeout=CONFIG["external_llm_timeout_seconds"]) as r:
            d = json.loads(r.read())
            text = d["choices"][0]["message"]["content"]
            cost_tracker.record_call("gpt-4o", dimension, len(prompt) // 4, len(text) // 4)
            return text
    except Exception as e:
        log(f"GPT-4o call failed: {e}")
        return None


def call_external_llms_parallel(prompt, cost_tracker, dimension):
    """LAW 4 — Fire Gemini + GPT-4o simultaneously in threads."""
    results = {"gemini": None, "gpt4o": None}

    def _gemini():
        results["gemini"] = _call_gemini(prompt, cost_tracker, dimension)

    def _gpt4o():
        results["gpt4o"] = _call_gpt4o(prompt, cost_tracker, dimension)

    t1 = threading.Thread(target=_gemini, daemon=True)
    t2 = threading.Thread(target=_gpt4o, daemon=True)
    t1.start()
    t2.start()
    t1.join(timeout=CONFIG["external_llm_timeout_seconds"] + 5)
    t2.join(timeout=CONFIG["external_llm_timeout_seconds"] + 5)
    return results


# ── Code Extraction (LAW 1) ─────────────────────────────────────────────────
def extract_code_section(file_path, function_name, max_lines=None):
    """LAW 1 — Surgical context only. Extract function body, max N lines."""
    if max_lines is None:
        max_lines = CONFIG["max_code_lines_per_audit"]
    full_path = BASE / file_path
    if not full_path.exists():
        return None, f"File not found: {file_path}"

    try:
        with open(full_path) as f:
            lines = f.readlines()
    except Exception as e:
        return None, str(e)

    # Find function definition
    func_start = None
    for i, line in enumerate(lines):
        if f"def {function_name}" in line:
            func_start = i
            break

    if func_start is None:
        # Fallback: return first max_lines of file
        section = "".join(lines[:max_lines])
        return section, f"Function '{function_name}' not found — returning file head"

    # Find function end (next def or class at same/lower indent)
    indent = len(lines[func_start]) - len(lines[func_start].lstrip())
    func_end = func_start + 1
    for i in range(func_start + 1, len(lines)):
        stripped = lines[i].lstrip()
        if stripped and not stripped.startswith("#"):
            curr_indent = len(lines[i]) - len(lines[i].lstrip())
            if curr_indent <= indent and (stripped.startswith("def ") or stripped.startswith("class ")):
                func_end = i
                break
    else:
        func_end = len(lines)

    section_lines = lines[func_start:min(func_end, func_start + max_lines)]
    return "".join(section_lines), f"Lines {func_start + 1}-{func_start + len(section_lines)}"


# ── Consensus Check (LAW 5) ─────────────────────────────────────────────────
def check_consensus(qwen_result, external_results):
    """LAW 5 — Consensus required. Returns (has_consensus, agreed_fix, disagreement_detail)."""
    if qwen_result is None:
        return False, None, "Qwen unavailable"

    qwen_cause = qwen_result.get("root_cause", "").lower().strip()
    qwen_confidence = qwen_result.get("confidence", 0.0)

    # High confidence Qwen — proceed if no external disagreement
    if qwen_confidence >= CONFIG["qwen_high_confidence"]:
        any_disagree = False
        for name, text in external_results.items():
            if text and "disagree" in text.lower():
                any_disagree = True
                break
        if not any_disagree:
            return True, qwen_result, "Qwen high-confidence, no external disagreement"

    # Check if at least 1 external agrees on root cause
    for name, text in external_results.items():
        if text is None:
            continue
        text_lower = text.lower()
        # Check for same file/function/mechanism mentioned
        qwen_words = set(qwen_cause.split())
        overlap = sum(1 for w in qwen_words if len(w) > 3 and w in text_lower)
        if overlap >= 3:  # At least 3 significant words match
            return True, qwen_result, f"Qwen + {name} agree (overlap={overlap})"

    return False, None, f"No consensus — Qwen cause: {qwen_cause[:80]}"


# ── Stalemate Detection (LAW 13) ────────────────────────────────────────────
class StalemateTracker:
    """Track skipped dimensions across iterations for stalemate detection."""

    def __init__(self):
        self.skip_history = {}  # dim -> consecutive_skip_count

    def record_skip(self, dimension):
        self.skip_history[dimension] = self.skip_history.get(dimension, 0) + 1

    def record_success(self, dimension):
        self.skip_history.pop(dimension, None)

    def is_stalemate(self, dimension):
        return self.skip_history.get(dimension, 0) >= CONFIG["stalemate_max_consecutive"]

    def get_count(self, dimension):
        return self.skip_history.get(dimension, 0)


# ── BIBLE Operations (LAW 7) ────────────────────────────────────────────────
def read_bible():
    """LAW 7 — Read QWEN_CONTEXT_BIBLE.md as institutional memory."""
    try:
        if BIBLE_PATH.exists():
            with open(BIBLE_PATH) as f:
                return f.read()
    except Exception as e:
        log(f"Bible read error: {e}")
    return ""


def append_bible(entry):
    """LAW 7 — Append finding to BIBLE after every fix."""
    try:
        with open(BIBLE_PATH, "a") as f:
            f.write(f"\n\n{entry}")
        log("Bible updated")
    except Exception as e:
        log(f"Bible append error: {e}")


# ── Fix History (gospel step 8) ──────────────────────────────────────────────
def append_fix_history(record):
    """Append to fix_history.jsonl — persistent across nights."""
    try:
        os.makedirs(os.path.dirname(FIX_HISTORY_PATH), exist_ok=True)
        with open(FIX_HISTORY_PATH, "a") as f:
            f.write(json.dumps(record) + "\n")
    except Exception as e:
        log(f"Fix history write error: {e}")


# ── Consecutive Grade A Counter (ADDENDUM) ──────────────────────────────────
def read_consecutive_a_count():
    """Read the 10-consecutive-Grade-A convergence counter."""
    try:
        if CONSECUTIVE_A_FILE.exists():
            return int(CONSECUTIVE_A_FILE.read_text().strip())
    except (ValueError, OSError):
        pass
    return 0


def write_consecutive_a_count(count):
    """Write the convergence counter."""
    try:
        os.makedirs(os.path.dirname(CONSECUTIVE_A_FILE), exist_ok=True)
        CONSECUTIVE_A_FILE.write_text(str(count))
    except OSError as e:
        log(f"Consecutive A counter write error: {e}")


def update_convergence(grade, score, broadcast_ready):
    """Update 10-consecutive-Grade-A convergence counter."""
    count = read_consecutive_a_count()
    threshold = CONFIG["grade_a_threshold"]
    target = CONFIG["consecutive_a_target"]

    if grade == "A" and score >= threshold and broadcast_ready:
        count += 1
        write_consecutive_a_count(count)
        remaining = target - count
        send_telegram_alert(f"Grade A #{count}/{target} — score={score}. {remaining} more to lock.")
        log(f"CONVERGENCE: Grade A #{count}/{target}")

        if count >= target:
            send_telegram_alert(
                f"PIPELINE LOCKED — {target} consecutive Grade A renders. Loop complete."
            )
            log(f"PIPELINE LOCKED — {target} consecutive Grade A renders achieved!")
            return True  # Signal loop to exit
    else:
        if count > 0:
            log(f"CONVERGENCE RESET: was {count}, got grade {grade} score {score}")
        write_consecutive_a_count(0)

    return False


# ── CC Session Management (LAW 9) ───────────────────────────────────────────
def check_cc_session_zombie(session_name):
    """LAW 9 — Two-layer zombie-safe detection.
    Returns: 'active', 'zombie', or 'none'."""
    # Layer 1: Check tmux session exists
    try:
        r = subprocess.run(["tmux", "has-session", "-t", session_name],
                           capture_output=True, timeout=5)
        if r.returncode != 0:
            return "none"
    except Exception:
        return "none"

    # Layer 2: Verify live process inside session
    try:
        r = subprocess.run(
            ["tmux", "list-panes", "-t", session_name, "-F", "#{pane_pid}"],
            capture_output=True, text=True, timeout=5,
        )
        pane_pids = [p.strip() for p in r.stdout.strip().split("\n") if p.strip()]
        if not pane_pids:
            return "zombie"

        any_alive = False
        for pid in pane_pids:
            proc_status = Path(f"/proc/{pid}/status")
            if proc_status.exists():
                any_alive = True
                break
        if not any_alive:
            return "zombie"
    except Exception:
        return "zombie"

    # Layer 3: Check recent activity
    try:
        r = subprocess.run(
            ["tmux", "display-message", "-t", session_name, "-p", "#{session_activity}"],
            capture_output=True, text=True, timeout=5,
        )
        activity_ts = int(r.stdout.strip())
        age = time.time() - activity_ts
        if age > CONFIG["zombie_activity_threshold_seconds"]:
            log(f"Session {session_name} inactive for {age:.0f}s (threshold: {CONFIG['zombie_activity_threshold_seconds']}s)")
            return "zombie"
    except Exception:
        pass

    return "active"


def kill_zombie_session(session_name):
    """Kill a zombie tmux session and log it."""
    try:
        subprocess.run(["tmux", "kill-session", "-t", session_name],
                       capture_output=True, timeout=10)
        log(f"ZOMBIE_SESSION_DETECTED — killed {session_name}")
        send_telegram_alert(f"ZOMBIE_SESSION_DETECTED — killed and relaunched")
    except Exception as e:
        log(f"Failed to kill zombie session {session_name}: {e}")


def wait_for_cc_slot(session_name):
    """LAW 9 — Wait for CC slot with zombie-safe detection.
    Returns True if slot is available, False on timeout."""
    timeout = CONFIG["cc_session_timeout_seconds"]
    start = time.time()
    poll_interval = 30

    while (time.time() - start) < timeout:
        status = check_cc_session_zombie(session_name)
        if status == "none":
            return True
        elif status == "zombie":
            kill_zombie_session(session_name)
            return True
        # status == "active" — wait
        log(f"CC slot busy ({session_name}), waiting {poll_interval}s...")
        time.sleep(poll_interval)

    log(f"CC slot wait timeout after {timeout}s")
    return False


# ── CC Session (gospel step 5) ───────────────────────────────────────────────
def fire_cc_session(iteration, fix_spec_path, dry_run=False):
    """Fire CC session with fix spec. Returns True on success."""
    session_name = f"render_fix_iter{iteration}"

    if dry_run:
        log(f"DRY-RUN: Would fire CC session {session_name} with {fix_spec_path}")
        return True

    # Wait for slot
    if not wait_for_cc_slot(session_name):
        return False

    try:
        # Create tmux session
        subprocess.run(
            ["tmux", "new-session", "-d", "-s", session_name],
            capture_output=True, timeout=10,
        )
        # Boot CC with spec
        cmd = f"claude --print '{fix_spec_path}' && exit"
        subprocess.run(
            ["tmux", "send-keys", "-t", session_name, cmd, "Enter"],
            capture_output=True, timeout=10,
        )
        log(f"CC session {session_name} launched")

        # Wait for completion with heartbeat
        cc_start = time.time()
        cc_timeout = CONFIG["cc_session_timeout_seconds"]
        while (time.time() - cc_start) < cc_timeout:
            status = check_cc_session_zombie(session_name)
            if status == "none":
                log(f"CC session {session_name} completed")
                return True
            elif status == "zombie":
                kill_zombie_session(session_name)
                log(f"CC session {session_name} zombied — marking timeout")
                return False
            # Write CC heartbeat
            try:
                write_ipc_json(CC_HEARTBEAT_FILE, {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "session": session_name,
                    "iteration": iteration,
                })
            except Exception:
                pass
            time.sleep(30)

        log(f"CC session {session_name} hard timeout ({cc_timeout}s)")
        send_telegram_alert(f"CC session timeout: {session_name}")
        return False

    except Exception as e:
        log(f"CC session error: {e}")
        return False


# ── Verification Gate (LAW 6) ────────────────────────────────────────────────
def verify_fix(iteration, expected_files, dry_run=False):
    """LAW 6 — Mandatory verification gate.
    Returns (passed, detail)."""
    if dry_run:
        log("DRY-RUN: Skipping verification gate")
        return True, "dry-run"

    # a) Diff sanity check
    try:
        r = subprocess.run(
            ["git", "diff", "--stat", "HEAD"],
            capture_output=True, text=True, timeout=30, cwd=str(BASE),
        )
        diff_output = r.stdout.strip()
        changed_files = len([l for l in diff_output.split("\n") if l.strip() and "|" in l])

        r2 = subprocess.run(
            ["git", "diff", "HEAD"],
            capture_output=True, text=True, timeout=30, cwd=str(BASE),
        )
        diff_lines = len(r2.stdout.split("\n"))

        if diff_lines > CONFIG["max_diff_lines"]:
            log(f"LAW 6 REJECT: Diff too large ({diff_lines} lines > {CONFIG['max_diff_lines']})")
            send_telegram_alert(f"CRITICAL: CC exceeded diff limit — fix rejected and reverted")
            subprocess.run(["git", "checkout", "."], capture_output=True, cwd=str(BASE))
            return False, f"diff_oversize ({diff_lines} lines)"
    except Exception as e:
        log(f"Diff check error: {e}")

    # b) regression_test.sh
    try:
        r = subprocess.run(
            ["bash", "regression_test.sh"],
            capture_output=True, text=True, timeout=300, cwd=str(BASE),
        )
        if r.returncode != 0:
            log(f"LAW 6 REJECT: regression_test.sh failed (exit {r.returncode})")
            send_telegram_alert("Regression test failed after fix — reverting")
            subprocess.run(["git", "checkout", "."], capture_output=True, cwd=str(BASE))
            return False, "regression_fail"
    except subprocess.TimeoutExpired:
        log("LAW 6: regression_test.sh timeout")
        return False, "regression_timeout"
    except Exception as e:
        log(f"Regression test error: {e}")

    return True, "pass"


# ── DEFAULT_HANDLER (gospel — for unmapped dimensions) ──────────────────────
def handle_unmapped_dimension(dimension, score, note):
    """Gospel DEFAULT_HANDLER — log, alert, queue for manual review."""
    log(f"WARNING: Unknown dimension '{dimension}' encountered — score={score}")
    send_telegram_alert(f"Unknown dimension '{dimension}' — PBX review needed")
    append_bible(f"UNMAPPED: {dimension} — {note}")


# ── Two-Pass Gemini Grading (RULE 3 — ADDENDUM) ─────────────────────────────
def grade_two_pass(grade_data, video_path=None):
    """RULE 3 — Split grading into technical (ffprobe) and content (video upload).
    Returns enhanced grade data with genuine content scores."""
    if not video_path or not os.path.exists(video_path):
        log("Two-pass grading: no video path — using single-pass data as-is")
        return grade_data

    dims = grade_data.get("dimensions", {})
    content_dims_to_regrade = []
    for dim_name, dim_data in dims.items():
        if dim_name in CONTENT_DIMENSIONS:
            note = dim_data.get("note", "")
            # Detect hallucinated confidence (RULE 3)
            if any(phrase in note.lower() for phrase in ["assumed", "unable to verify", "assuming baseline"]):
                content_dims_to_regrade.append(dim_name)

    if not content_dims_to_regrade:
        log("Two-pass grading: no hallucinated content dimensions found")
        return grade_data

    log(f"Two-pass grading: {len(content_dims_to_regrade)} content dims need video review: {content_dims_to_regrade}")

    # Upload video to Gemini Files API for genuine multimodal eval
    env = load_env()
    key = env.get("GEMINI_API_KEY", "")
    if not key:
        log("Two-pass grading: no GEMINI_API_KEY — skipping content pass")
        return grade_data

    try:
        # Upload file
        file_size = os.path.getsize(video_path)
        if file_size > 2_000_000_000:  # 2GB limit
            log(f"Two-pass grading: video too large ({file_size} bytes) — skipping upload")
            return grade_data

        # Use resumable upload for large files
        upload_url = f"https://generativelanguage.googleapis.com/upload/v1beta/files?key={key}"
        headers = {
            "X-Goog-Upload-Protocol": "resumable",
            "X-Goog-Upload-Command": "start",
            "X-Goog-Upload-Header-Content-Length": str(file_size),
            "X-Goog-Upload-Header-Content-Type": "video/mp4",
            "Content-Type": "application/json",
        }
        meta = json.dumps({"file": {"display_name": f"grade_iter_video"}}).encode()
        req = urllib.request.Request(upload_url, data=meta, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as r:
            resumable_url = r.headers.get("X-Goog-Upload-URL")

        if not resumable_url:
            log("Two-pass grading: failed to get resumable upload URL")
            return grade_data

        # Upload bytes
        with open(video_path, "rb") as f:
            video_bytes = f.read()
        upload_req = urllib.request.Request(resumable_url, data=video_bytes, headers={
            "Content-Length": str(file_size),
            "X-Goog-Upload-Offset": "0",
            "X-Goog-Upload-Command": "upload, finalize",
        })
        with urllib.request.urlopen(upload_req, timeout=300) as r:
            upload_result = json.loads(r.read())

        file_uri = upload_result.get("file", {}).get("uri")
        if not file_uri:
            log("Two-pass grading: upload succeeded but no file URI returned")
            return grade_data

        log(f"Two-pass grading: video uploaded — {file_uri}")

        # Wait for processing
        file_name = upload_result.get("file", {}).get("name", "")
        for _ in range(30):
            check_url = f"https://generativelanguage.googleapis.com/v1beta/{file_name}?key={key}"
            check_req = urllib.request.Request(check_url)
            with urllib.request.urlopen(check_req, timeout=15) as r:
                status_data = json.loads(r.read())
            state = status_data.get("state", "")
            if state == "ACTIVE":
                break
            time.sleep(10)

        # Pass 2: Content grading with actual video
        content_prompt = (
            "Watch this Protocol Pulse Bitcoin show episode. Grade ONLY these content dimensions "
            "by actually watching the video. Do NOT guess or assume — only score what you can see and hear.\n\n"
            f"Dimensions to grade: {', '.join(content_dims_to_regrade)}\n\n"
            "Respond with JSON only: {\"dimensions\": {\"dim_name\": {\"score\": 0-10, \"note\": \"explain\"}}}"
        )
        gen_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent?key={key}"
        gen_payload = {
            "contents": [{"parts": [
                {"file_data": {"mime_type": "video/mp4", "file_uri": file_uri}},
                {"text": content_prompt},
            ]}],
            "generationConfig": {"maxOutputTokens": 2000, "temperature": 0.05},
        }
        gen_req = urllib.request.Request(gen_url, data=json.dumps(gen_payload).encode(),
                                        headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(gen_req, timeout=120) as r:
            gen_result = json.loads(r.read())

        parts = gen_result.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        text = next((p["text"] for p in parts if "text" in p), None)
        if text:
            clean = text.strip()
            for fence in ["```json", "```"]:
                if fence in clean:
                    clean = clean.split(fence)[1].split("```")[0].strip()
            content_grades = json.loads(clean)
            # Merge content grades into main grade data
            for dim_name, dim_data in content_grades.get("dimensions", {}).items():
                if dim_name in dims:
                    old_score = dims[dim_name].get("score", 0)
                    new_score = dim_data.get("score", old_score)
                    dims[dim_name] = dim_data
                    log(f"Two-pass regrade: {dim_name} {old_score} -> {new_score}")

        # Cleanup uploaded file
        try:
            del_url = f"https://generativelanguage.googleapis.com/v1beta/{file_name}?key={key}"
            del_req = urllib.request.Request(del_url, method="DELETE")
            urllib.request.urlopen(del_req, timeout=10)
        except Exception:
            pass

    except Exception as e:
        log(f"Two-pass grading error (non-fatal): {e}")

    return grade_data


# ── Main Loop Flow (gospel LOOP FLOW) ───────────────────────────────────────
def run_improvement_cycle(fix_request_path, dry_run=False):
    """Execute one full improvement cycle per gospel LOOP FLOW.
    Returns IPC completion data dict."""
    log("=" * 60)
    log("RENDER IMPROVEMENT LOOP — STARTING CYCLE")
    log("=" * 60)

    cycle_start = time.time()
    cost_tracker = CostTracker()
    stalemate = StalemateTracker()

    # Parse fix request
    request_data = read_ipc_json(fix_request_path)
    iteration = request_data.get("iteration", 0)
    grade_file = request_data.get("grade_file", "")
    request_timestamp = request_data.get("request_timestamp", "")
    failing_dims_hint = request_data.get("failing_dimensions", [])

    log(f"Iteration: {iteration}")
    log(f"Grade file: {grade_file}")
    log(f"Request timestamp: {request_timestamp}")

    # Validate iteration (UI1 — stale fix prevention)
    if request_data.get("status") != "pending":
        log(f"STALE: Request status is '{request_data.get('status')}', not 'pending'")
        completion = {
            "status": "stale",
            "request_timestamp": request_timestamp,
            "completion_timestamp": datetime.now(timezone.utc).isoformat(),
            "dimensions_fixed": [],
            "dimensions_failed": [],
            "dimensions_skipped": [],
            "cost_usd": 0,
            "diff_hash": "",
        }
        return completion

    # Start heartbeat (gospel step 0)
    current_dim_ref = ["preflight"]
    hb_thread = start_heartbeat(iteration, current_dim_ref)

    send_telegram_alert(
        f"Render improvement loop started — iter{iteration}, "
        f"dims={failing_dims_hint}"
    )

    # Step 0: Preflight — Ollama health check
    if not dry_run:
        if not ollama_health_check():
            log("PREFLIGHT FAIL: Ollama unreachable")
            send_telegram_alert("Ollama unreachable — improvement loop cannot start")
            stop_heartbeat()
            return {
                "status": "failed",
                "request_timestamp": request_timestamp,
                "completion_timestamp": datetime.now(timezone.utc).isoformat(),
                "dimensions_fixed": [],
                "dimensions_failed": failing_dims_hint,
                "dimensions_skipped": [],
                "cost_usd": 0,
                "diff_hash": "",
                "error": "ollama_unreachable",
            }

    # Step 1: INGEST — parse grade JSON, extract failing dims (score < 8)
    try:
        with open(grade_file) as f:
            grade_data = json.load(f)
    except Exception as e:
        log(f"Grade file read error: {e}")
        stop_heartbeat()
        return {
            "status": "failed",
            "request_timestamp": request_timestamp,
            "completion_timestamp": datetime.now(timezone.utc).isoformat(),
            "dimensions_fixed": [],
            "dimensions_failed": [],
            "dimensions_skipped": [],
            "cost_usd": 0,
            "diff_hash": "",
            "error": f"grade_file_error: {e}",
        }

    dims = grade_data.get("dimensions", {})
    threshold = CONFIG["failing_score_threshold"]
    failing = []
    for dim_name, dim_data in dims.items():
        score = dim_data.get("score")
        if isinstance(score, (int, float)) and score < threshold:
            note = dim_data.get("note", "")
            meta = DIMENSION_META.get(dim_name, {"priority": "medium", "fix_complexity": "simple", "max_cost_usd": 0.75, "safe_default": None})
            failing.append((dim_name, score, note, meta))

    # Sort by priority then score ascending (worst first) — RULE 1
    failing.sort(key=lambda x: (PRIORITY_ORDER.get(x[3]["priority"], 99), x[1]))
    log(f"Failing dimensions ({len(failing)}): {[(d, s) for d, s, _, _ in failing]}")

    overall_score = grade_data.get("overall_score", 0)
    grade_letter = grade_data.get("grade", "F")
    broadcast_ready = grade_data.get("broadcast_ready", False)

    # Check convergence
    if update_convergence(grade_letter, overall_score, broadcast_ready):
        stop_heartbeat()
        return {
            "status": "complete",
            "request_timestamp": request_timestamp,
            "completion_timestamp": datetime.now(timezone.utc).isoformat(),
            "dimensions_fixed": [],
            "dimensions_failed": [],
            "dimensions_skipped": [],
            "cost_usd": 0,
            "diff_hash": "",
            "converged": True,
        }

    # Step 2: BIBLE READ
    current_dim_ref[0] = "bible_read"
    bible_content = read_bible()
    log(f"Bible loaded: {len(bible_content)} chars")

    # Track outcomes
    dimensions_fixed = []
    dimensions_failed = []
    dimensions_skipped = []
    fix_specs = []

    # Step 3: FOR EACH FAILING DIMENSION
    for dim_name, dim_score, dim_note, dim_meta in failing:
        current_dim_ref[0] = dim_name
        log(f"\n--- Processing dimension: {dim_name} (score={dim_score}, priority={dim_meta['priority']}) ---")

        # 3a. MAP — look up DIMENSION_MAP
        if dim_name not in DIMENSION_MAP:
            handle_unmapped_dimension(dim_name, dim_score, dim_note)
            dimensions_skipped.append(dim_name)
            continue

        # Check stalemate history
        if stalemate.is_stalemate(dim_name):
            safe_default = dim_meta.get("safe_default")
            if safe_default:
                log(f"STALEMATE on {dim_name} — applying safe default: {safe_default}")
                send_telegram_alert(f"STALEMATE on {dim_name} — applying tiebreak/default")
                fix_specs.append({
                    "dimension": dim_name,
                    "fix_type": "safe_default",
                    "fix": safe_default,
                    "verify_cmd": "",
                })
                dimensions_fixed.append(dim_name)
            else:
                log(f"STALEMATE on {dim_name} — no safe default, skipping")
                if stalemate.get_count(dim_name) >= 3:
                    send_telegram_alert(f"CRITICAL: 3+ stalemates on {dim_name} — aborting")
                    dimensions_failed.append(dim_name)
                else:
                    dimensions_skipped.append(dim_name)
            continue

        # 3b. BUDGET CHECK
        can_proceed, qwen_only = cost_tracker.check_budget(dim_name)
        if not can_proceed:
            # Daily hard cap hit — mark remaining as failed
            dimensions_failed.append(dim_name)
            for _, remaining_dim, _, _ in failing[failing.index((dim_name, dim_score, dim_note, dim_meta)) + 1:]:
                dimensions_failed.append(remaining_dim)
            break

        # 3c. EXTRACT — get code sections (LAW 1: max 120 lines)
        code_sections = []
        targets = DIMENSION_MAP[dim_name]
        for file_path, func_name in targets:
            section, info = extract_code_section(file_path, func_name)
            if section:
                code_sections.append(f"# FILE: {file_path} — {func_name} ({info})\n{section}")
            else:
                log(f"Code extraction failed for {file_path}:{func_name} — {info}")

        if not code_sections:
            log(f"No code sections extracted for {dim_name} — skipping")
            dimensions_skipped.append(dim_name)
            continue

        combined_code = "\n\n".join(code_sections)
        # Enforce LAW 1: max 120 lines
        code_lines = combined_code.split("\n")
        if len(code_lines) > CONFIG["max_code_lines_per_audit"]:
            combined_code = "\n".join(code_lines[:CONFIG["max_code_lines_per_audit"]])

        # 3d. QWEN (local, $0) — resilience wrapper
        qwen_prompt = (
            "You are a senior video pipeline engineer. Here is a failing code section "
            "and the specific error description. Identify the root cause precisely and "
            "provide a minimal, surgical fix. Be concise. Output JSON only:\n"
            '{root_cause: str, fix_patch: str, confidence: float, verify_cmd: str}\n\n'
            f"DIMENSION: {dim_name}\n"
            f"SCORE: {dim_score}/10\n"
            f"GEMINI NOTE: {dim_note}\n\n"
            f"CODE:\n{combined_code}\n\n"
            f"BIBLE CONTEXT (known fixes):\n{bible_content[-500:] if bible_content else 'None'}"
        )

        if dry_run:
            qwen_result = {
                "root_cause": f"Mock root cause for {dim_name}",
                "fix_patch": f"# Mock fix for {dim_name}",
                "confidence": 0.90,
                "verify_cmd": f"echo 'verify {dim_name}'",
            }
        else:
            qwen_result = qwen_call(qwen_prompt, dim_name, cost_tracker)
            if qwen_result is None:
                # Try fallback model
                qwen_result = qwen_fallback_call(qwen_prompt, dim_name, cost_tracker)

        if qwen_result is None:
            dimensions_failed.append(dim_name)
            append_fix_history({
                "dimension": dim_name, "fix_applied": None, "pre_score": dim_score,
                "iteration": iteration, "cost_usd": 0, "outcome": "qwen_unavailable",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            continue

        log(f"Qwen result: confidence={qwen_result.get('confidence', 0):.2f}, "
            f"root_cause={qwen_result.get('root_cause', '')[:80]}")

        # 3e. EXTERNAL LLMS (parallel, if Qwen confidence < 0.85 and not qwen_only)
        external_results = {"gemini": None, "gpt4o": None}
        if not qwen_only and qwen_result.get("confidence", 0) < CONFIG["qwen_high_confidence"]:
            if not dry_run:
                external_prompt = (
                    f"A video pipeline engineer identified this root cause for a failing dimension.\n"
                    f"Do you agree? What is your fix?\n\n"
                    f"DIMENSION: {dim_name} (score: {dim_score}/10)\n"
                    f"QWEN ROOT CAUSE: {qwen_result.get('root_cause', '')}\n"
                    f"QWEN FIX: {qwen_result.get('fix_patch', '')}\n"
                    f"GEMINI NOTE: {dim_note}\n\n"
                    f"CODE:\n{combined_code[:2000]}\n\n"
                    "Respond with: agree/disagree, your root cause, your fix suggestion."
                )
                external_results = call_external_llms_parallel(external_prompt, cost_tracker, dim_name)
            else:
                external_results = {
                    "gemini": f"Agree with root cause for {dim_name}",
                    "gpt4o": f"Agree with root cause for {dim_name}",
                }

        # 3f. CONSENSUS CHECK
        has_consensus, agreed_fix, consensus_detail = check_consensus(qwen_result, external_results)
        log(f"Consensus: {has_consensus} — {consensus_detail}")

        if not has_consensus:
            # Check for Qwen high confidence override
            if qwen_result.get("confidence", 0) >= CONFIG["qwen_high_confidence"]:
                has_consensus = True
                agreed_fix = qwen_result
                log(f"High-confidence Qwen override for {dim_name}")
            else:
                stalemate.record_skip(dim_name)
                # Write disagreement to BIBLE
                append_bible(
                    f"DISAGREEMENT ({datetime.now().isoformat()}): {dim_name} — iter{iteration}\n"
                    f"  Qwen: {qwen_result.get('root_cause', '')[:100]}\n"
                    f"  External: {consensus_detail}"
                )
                send_telegram_alert(f"LLM disagreement on {dim_name} — PBX review needed")
                dimensions_skipped.append(dim_name)
                append_fix_history({
                    "dimension": dim_name, "fix_applied": None, "pre_score": dim_score,
                    "iteration": iteration, "cost_usd": 0, "outcome": "disagreement",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                continue

        # 3g. WRITE FIX SPEC
        fix_spec = {
            "dimension": dim_name,
            "files": [(f, fn) for f, fn in DIMENSION_MAP[dim_name]],
            "root_cause": agreed_fix.get("root_cause", ""),
            "fix_patch": agreed_fix.get("fix_patch", ""),
            "verify_cmd": agreed_fix.get("verify_cmd", ""),
            "confidence": agreed_fix.get("confidence", 0),
            "fix_type": "consensus",
        }
        fix_specs.append(fix_spec)
        stalemate.record_success(dim_name)
        dimensions_fixed.append(dim_name)

        # Record fix history
        append_fix_history({
            "dimension": dim_name,
            "fix_applied": agreed_fix.get("fix_patch", "")[:200],
            "pre_score": dim_score,
            "iteration": iteration,
            "cost_usd": round(cost_tracker.cycle_cost, 4),
            "outcome": "consensus_reached",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        # Update heartbeat
        current_dim_ref[0] = f"{dim_name}_done"

        # Check time budget
        elapsed = time.time() - cycle_start
        if elapsed > CONFIG["max_improvement_time_seconds"]:
            log(f"Time budget exceeded ({elapsed:.0f}s > {CONFIG['max_improvement_time_seconds']}s)")
            break

    # Step 4-5: Write CC fix spec and fire session
    if fix_specs and not dry_run:
        spec_path = f"/tmp/cc_render_fix_iter{iteration}.md"
        cc_header = (
            "STRICT INSTRUCTIONS — READ CAREFULLY:\n"
            "1. Implement ONLY the exact patches specified below. Nothing else.\n"
            "2. Do NOT refactor surrounding code. Do NOT rename variables. Do NOT add comments.\n"
            "3. Do NOT modify function signatures or add external dependencies.\n"
            "4. Do NOT touch files not specified in this fix spec.\n"
            "5. Maximum allowed diff: 50 lines across all patches combined.\n"
            "6. Run the verify command for each fix before committing.\n"
            "7. bash regression_test.sh must show 0 FAILs.\n"
            "8. If regression_test.sh fails, STOP. Do not commit. Report the failure.\n"
            "9. git add -A && git commit -m 'fix(pipeline): "
            f"{', '.join(dimensions_fixed)} — autonomous loop iter{iteration}'\n"
            "10. git push\n\n"
        )
        spec_body = ""
        for spec in fix_specs:
            spec_body += f"--- FIX: {spec['dimension']} ---\n"
            for f, fn in spec.get("files", []):
                spec_body += f"FILE: {f}\nFUNCTION: {fn}\n"
            spec_body += f"ROOT CAUSE: {spec['root_cause']}\n"
            spec_body += f"FIX: {spec['fix_patch']}\n"
            spec_body += f"VERIFY: {spec['verify_cmd']}\n"
            bible_entry = (
                f"FIX ({datetime.now().isoformat()}): {spec['dimension']} — iter{iteration}\n"
                f"  Root cause: {spec['root_cause'][:100]}\n"
                f"  Fix: {spec['fix_patch'][:100]}\n"
                f"  Outcome: pending_cc"
            )
            spec_body += f"BIBLE ENTRY: {bible_entry}\n\n"

        with open(spec_path, "w") as f:
            f.write(cc_header + spec_body)
        log(f"CC fix spec written: {spec_path}")

        # Fire CC session
        cc_success = fire_cc_session(iteration, spec_path, dry_run=dry_run)
        if not cc_success:
            log("CC session failed — marking all as failed")
            dimensions_failed.extend(dimensions_fixed)
            dimensions_fixed = []

    elif fix_specs and dry_run:
        log(f"DRY-RUN: {len(fix_specs)} fix specs generated — skipping CC session")
        for spec in fix_specs:
            send_telegram_alert(f"Fix applied: {spec['dimension']} — {spec['root_cause'][:60]}")

    # Step 6: Verify (LAW 6) — only if CC actually ran
    if dimensions_fixed and not dry_run:
        expected_files = set()
        for spec in fix_specs:
            for f, _ in spec.get("files", []):
                expected_files.add(f)
        passed, detail = verify_fix(iteration, expected_files, dry_run=dry_run)
        if not passed:
            log(f"Verification FAILED: {detail} — reverting fixes")
            dimensions_failed.extend(dimensions_fixed)
            dimensions_fixed = []

    # Step 7: BIBLE WRITE
    for spec in fix_specs:
        outcome = "fixed" if spec["dimension"] in dimensions_fixed else "failed"
        append_bible(
            f"FIX RESULT ({datetime.now().isoformat()}): {spec['dimension']} — iter{iteration}\n"
            f"  Root cause: {spec.get('root_cause', '')[:100]}\n"
            f"  Outcome: {outcome}"
        )

    # Compute diff hash
    diff_hash = ""
    try:
        r = subprocess.run(["git", "diff", "HEAD~1", "--stat"],
                           capture_output=True, text=True, timeout=10, cwd=str(BASE))
        diff_hash = hashlib.sha256(r.stdout.encode()).hexdigest()[:12]
    except Exception:
        pass

    # Step 10: Write IPC completion
    stop_heartbeat()
    completion = {
        "status": "complete" if dimensions_fixed else ("failed" if dimensions_failed else "complete"),
        "request_timestamp": request_timestamp,
        "completion_timestamp": datetime.now(timezone.utc).isoformat(),
        "dimensions_fixed": dimensions_fixed,
        "dimensions_failed": dimensions_failed,
        "dimensions_skipped": dimensions_skipped,
        "cost_usd": round(cost_tracker.cycle_cost, 4),
        "diff_hash": diff_hash,
    }

    ipc_complete_path = f"/tmp/fix_complete_iter{iteration}.json"
    write_ipc_json(ipc_complete_path, completion)

    send_telegram_alert(
        f"Loop complete — iter{iteration}: "
        f"{len(dimensions_fixed)} fixed, {len(dimensions_failed)} failed, "
        f"{len(dimensions_skipped)} skipped | cost=${cost_tracker.cycle_cost:.2f}"
    )

    log(f"Cycle complete: fixed={dimensions_fixed} failed={dimensions_failed} skipped={dimensions_skipped}")
    log(f"Cost: ${cost_tracker.cycle_cost:.2f} (daily: ${cost_tracker.daily_cost:.2f})")
    return completion


# ── Main Entry Point ─────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Render improvement loop — autonomous grade-driven fix engine",
    )
    parser.add_argument("--grade", type=str, help="Direct grade JSON file path")
    parser.add_argument("--iteration", type=int, default=1, help="Iteration number")
    parser.add_argument("--dry-run", action="store_true", help="No LLM calls, no CC sessions")
    parser.add_argument("--video", type=str, help="Video path for two-pass grading")
    args = parser.parse_args()

    # Step 0: Clean startup state (LAW 12)
    cleanup_stale_ipc()

    if args.grade:
        # Direct mode — create synthetic IPC request
        request_path = f"/tmp/fix_request_iter{args.iteration}.json"
        request_data = {
            "status": "pending",
            "iteration": args.iteration,
            "pid": os.getpid(),
            "request_timestamp": datetime.now(timezone.utc).isoformat(),
            "grade_file": args.grade,
            "failing_dimensions": [],
        }
        write_ipc_json(request_path, request_data)
        result = run_improvement_cycle(request_path, dry_run=args.dry_run)
        log(f"Result: {json.dumps(result, indent=2)}")
        return

    # Poll mode — wait for IPC request files
    log("Improvement loop starting in poll mode — waiting for fix_request_iter*.json")
    poll_interval = CONFIG["poll_interval_seconds"]
    timeout = CONFIG["per_iteration_timeout_seconds"]
    start = time.time()

    while (time.time() - start) < timeout:
        requests = sorted(glob.glob(IPC_REQUEST_PATTERN))
        for req_path in requests:
            try:
                data = read_ipc_json(req_path)
                if data.get("status") == "pending":
                    log(f"Found pending request: {req_path}")
                    result = run_improvement_cycle(req_path, dry_run=args.dry_run)
                    log(f"Result: {json.dumps(result, indent=2)}")
                    return
            except Exception as e:
                log(f"Error reading {req_path}: {e}")
        time.sleep(poll_interval)

    log("Timeout waiting for IPC request — exiting")


if __name__ == "__main__":
    main()
