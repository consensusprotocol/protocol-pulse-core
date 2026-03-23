#!/usr/bin/env python3
"""
Protocol Pulse — Local LLM Watchdog (4-Layer Autonomous System)
GPU 2: Qwen3-Coder-30B via Ollama on port 11435

Modes (each runs independently via cron):
  --mode reactive   : every 60s  — crash detection + auto-patch
  --mode health     : every 15m  — system health scan
  --mode pattern    : every 6h   — trend analysis over 7 days
  --mode audit      : Monday 08:00 UTC — weekly deep audit
  --mode briefing   : daily 13:00 UTC (09:00 ET) — Telegram daily summary

Gospel: docs/gospels/WATCHDOG_LLM_GOSPEL.md
"""

import argparse
import glob
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

BASE = Path(__file__).resolve().parent.parent
LOGS_DIR = BASE / "logs"
LOGS_DIR.mkdir(exist_ok=True)

LOG_FILE = LOGS_DIR / "watchdog_llm.log"
PATCH_LOG = LOGS_DIR / "watchdog_patches.jsonl"
OVERNIGHT_LOG = BASE / "video_pipeline_v3" / "logs" / "overnight_loop.log"
REGRESSION_SCRIPT = BASE / "regression_test.sh"

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

OLLAMA_URL = "http://127.0.0.1:11435"
MODEL = os.environ.get("WATCHDOG_MODEL", "qwen3-coder:30b")

# Files we NEVER patch — gospel law
NEVER_PATCH = {"assembler.py", "tts_engine.py", "gemini_grade.py", "routes.py"}

# Cooldown: 600s per file, max 3 patches/hour
COOLDOWN_SECONDS = 600
MAX_PATCHES_PER_HOUR = 3

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logger = logging.getLogger("watchdog")
logger.setLevel(logging.INFO)

_fh = logging.FileHandler(str(LOG_FILE))
_fh.setFormatter(logging.Formatter("%(asctime)s [WATCHDOG] %(levelname)s: %(message)s"))
logger.addHandler(_fh)

_sh = logging.StreamHandler()
_sh.setFormatter(logging.Formatter("%(asctime)s [WATCHDOG] %(levelname)s: %(message)s"))
logger.addHandler(_sh)

# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------

def _load_env():
    """Load .env file into os.environ."""
    env_path = BASE / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip().strip("'\""))


def send_telegram(msg):
    """Send a Telegram message. Returns True on success."""
    _load_env()
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        logger.warning("Telegram not configured — TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID missing")
        return False
    try:
        import requests
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"},
            timeout=10,
        )
        resp.raise_for_status()
        return True
    except Exception as e:
        logger.error("Telegram send failed: %s", e)
        return False

# ---------------------------------------------------------------------------
# Ollama Interface
# ---------------------------------------------------------------------------

def ollama_chat(system_prompt, user_prompt, temperature=0.3):
    """Fresh Ollama conversation — zero prior context (gospel: Fresh Perspective)."""
    import requests
    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "stream": False,
                "options": {"temperature": temperature},
            },
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json().get("message", {}).get("content", "").strip()
    except Exception as e:
        logger.error("Ollama call failed: %s", e)
        return None


def ollama_healthy():
    """Check if Ollama is responding."""
    import requests
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        return resp.status_code == 200
    except Exception:
        return False

# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def tail_file(path, n=50):
    """Read last n lines of a file."""
    p = Path(path)
    if not p.exists():
        return ""
    try:
        result = subprocess.run(
            ["tail", "-n", str(n), str(p)],
            capture_output=True, text=True, timeout=10,
        )
        return result.stdout
    except Exception:
        return ""


def read_file_content(path):
    """Read file content, capped at 200 lines."""
    try:
        lines = Path(path).read_text().splitlines()[:200]
        return "\n".join(lines)
    except Exception:
        return ""


def gpu_vram():
    """Get GPU VRAM usage as list of dicts."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=index,memory.used,memory.total,utilization.gpu",
             "--format=csv,nounits,noheader"],
            capture_output=True, text=True, timeout=10,
        )
        gpus = []
        for line in result.stdout.strip().splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 4:
                gpus.append({
                    "index": int(parts[0]),
                    "vram_used_mb": int(parts[1]),
                    "vram_total_mb": int(parts[2]),
                    "utilization_pct": int(parts[3]),
                })
        return gpus
    except Exception:
        return []


def disk_free_gb():
    """Get free disk space in GB for the base directory."""
    try:
        stat = shutil.disk_usage(str(BASE))
        return round(stat.free / (1024 ** 3), 1)
    except Exception:
        return -1


def process_alive(name):
    """Check if a process matching name is running."""
    try:
        result = subprocess.run(["pgrep", "-f", name], capture_output=True, timeout=5)
        return result.returncode == 0
    except Exception:
        return False


def flask_alive():
    """Check if Flask is responding on localhost:5000."""
    import requests
    try:
        resp = requests.get("http://localhost:5000/", timeout=5)
        return resp.status_code < 500
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Safety Gates
# ---------------------------------------------------------------------------

def check_cooldown(filepath):
    """Return True if file is on cooldown (patched within last 600s)."""
    fname = Path(filepath).name
    stamp_file = Path(f"/tmp/watchdog_last_patch_{fname}.txt")
    if stamp_file.exists():
        try:
            last = float(stamp_file.read_text().strip())
            if time.time() - last < COOLDOWN_SECONDS:
                return True
        except (ValueError, IOError):
            pass
    return False


def record_patch(filepath):
    """Record patch timestamp for cooldown tracking."""
    fname = Path(filepath).name
    stamp_file = Path(f"/tmp/watchdog_last_patch_{fname}.txt")
    stamp_file.write_text(str(time.time()))


def patches_this_hour():
    """Count patches applied in the current hour."""
    hour_key = datetime.now(timezone.utc).strftime("%Y%m%d%H")
    count_file = Path(f"/tmp/watchdog_patch_count_{hour_key}.txt")
    if count_file.exists():
        try:
            return int(count_file.read_text().strip())
        except (ValueError, IOError):
            pass
    return 0


def increment_patch_count():
    """Increment the hourly patch counter."""
    hour_key = datetime.now(timezone.utc).strftime("%Y%m%d%H")
    count_file = Path(f"/tmp/watchdog_patch_count_{hour_key}.txt")
    current = patches_this_hour()
    count_file.write_text(str(current + 1))


def is_patchable(filepath):
    """Check all safety gates for patching a file."""
    fname = Path(filepath).name

    if fname in NEVER_PATCH:
        logger.info("GATE: %s is in NEVER_PATCH list — skipping", fname)
        return False

    if process_alive("daily_producer"):
        logger.info("GATE: daily_producer is running — skipping patch")
        return False

    if check_cooldown(filepath):
        logger.info("GATE: %s on cooldown — skipping", fname)
        return False

    if patches_this_hour() >= MAX_PATCHES_PER_HOUR:
        logger.info("GATE: max %d patches/hour reached — skipping", MAX_PATCHES_PER_HOUR)
        return False

    return True


# ---------------------------------------------------------------------------
# Crash Classification
# ---------------------------------------------------------------------------

def classify_crash(log_tail):
    """Classify crash from log lines. Returns (class, pattern_matched) or (None, None)."""
    lines = log_tail.strip()
    if not lines:
        return None, None

    # CLASS C — check protected files first (takes priority)
    for protected in NEVER_PATCH:
        if (f'File "' in lines and protected in lines and "Traceback" in lines):
            return "C", f"crash_in_{protected}"

    # Check for multi-file crashes (>1 unique repo file in traceback)
    file_matches = re.findall(r'File "([^"]*protocol_pulse[^"]*)"', lines)
    unique_files = set(Path(f).name for f in file_matches)
    # Remove __init__.py and test files from uniqueness check
    meaningful = {f for f in unique_files if f != "__init__.py" and not f.startswith("test_")}
    if len(meaningful) > 1:
        return "C", f"multi_file_crash({','.join(sorted(meaningful)[:3])})"

    # CLASS A patterns (safe auto-patch)
    if "KeyError" in lines:
        return "A", "KeyError"
    if "ImportError" in lines or "ModuleNotFoundError" in lines:
        return "A", "ImportError"
    if "FileNotFoundError" in lines:
        return "A", "FileNotFoundError"
    if "SyntaxError" in lines:
        return "A", "SyntaxError"

    # CLASS B patterns (patch + test)
    if "Traceback" in lines and "daily_producer" in lines:
        return "B", "Traceback+daily_producer"
    if "exit: -15" in lines and "FATAL" in lines:
        return "B", "exit:-15+FATAL"
    if "GRADE: F" in lines:
        return "B", "GRADE:F"

    # Check for 3x consecutive "Render failed"
    render_fails = re.findall(r"Render failed", lines)
    if len(render_fails) >= 3:
        return "B", "Render_failed_3x"

    return None, None


def extract_affected_file(log_tail):
    """Try to extract the crashing file from a traceback."""
    matches = re.findall(r'File "([^"]+)"', log_tail)
    # Filter to our repo files, exclude NEVER_PATCH
    repo_files = [
        m for m in matches
        if str(BASE) in m and Path(m).name not in NEVER_PATCH
    ]
    if repo_files:
        return repo_files[-1]  # Last file in traceback is usually the culprit
    return None


# ---------------------------------------------------------------------------
# Patch Engine
# ---------------------------------------------------------------------------

def diagnose_and_patch(log_tail, crash_class, pattern):
    """Use Ollama to diagnose crash, optionally apply patch."""
    affected_file = extract_affected_file(log_tail)

    if not affected_file:
        logger.info("Could not determine affected file from traceback")
        send_telegram(
            f"\U0001f534 <b>CRASH DETECTED</b> — CLASS {crash_class}\n"
            f"\U0001f4cb Pattern: {pattern}\n"
            f"\u26a0\ufe0f Could not identify affected file\n"
            f"\U0001f527 Manual intervention needed"
        )
        return

    fname = Path(affected_file).name

    # CLASS C — alert only
    if crash_class == "C":
        logger.info("CLASS C crash in %s — alert only, no patching", fname)
        send_telegram(
            f"\U0001f534 <b>CLASS C CRASH</b> in <code>{fname}</code>\n"
            f"\U0001f4cb Pattern: {pattern}\n"
            f"\u26a0\ufe0f Protected file — manual fix required\n"
            f"\U0001f4c2 {affected_file}"
        )
        return

    # Check safety gates
    if not is_patchable(affected_file):
        send_telegram(
            f"\U0001f534 <b>CLASS {crash_class} CRASH</b> in <code>{fname}</code>\n"
            f"\U0001f4cb Pattern: {pattern}\n"
            f"\U0001f6ab Safety gate blocked auto-patch\n"
            f"\U0001f527 Manual intervention needed"
        )
        return

    # Read affected file content
    file_content = read_file_content(affected_file)

    # Ask Ollama for diagnosis
    system_prompt = (
        "You are a Python/FFmpeg expert debugging a video production pipeline. "
        "Analyze the crash log and return ONLY valid JSON:\n"
        '{"diagnosis": "str", "affected_file": "str", "patch_diff": "str", "confidence": float}\n'
        "The patch_diff must be a unified diff that can be applied with `patch -p0`.\n"
        "If you cannot determine a fix with high confidence, set confidence to 0.0."
    )
    user_prompt = f"CRASH LOG:\n{log_tail}\n\nFILE CONTENT ({affected_file}):\n{file_content}"

    logger.info("Requesting Ollama diagnosis for %s...", fname)
    raw_response = ollama_chat(system_prompt, user_prompt)

    if not raw_response:
        send_telegram(
            f"\U0001f534 <b>CLASS {crash_class} CRASH</b> in <code>{fname}</code>\n"
            f"\U0001f4cb {pattern}\n"
            f"\u274c Ollama diagnosis failed — model unresponsive"
        )
        return

    # Parse JSON from response (may be wrapped in markdown code block)
    json_text = None
    # Try code block first
    code_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw_response, re.DOTALL)
    if code_match:
        json_text = code_match.group(1)
    else:
        # Try bare JSON
        json_match = re.search(r'\{[^{}]*"diagnosis"[^}]*\}', raw_response, re.DOTALL)
        if json_match:
            json_text = json_match.group()

    if not json_text:
        logger.warning("Could not parse JSON from Ollama response")
        send_telegram(
            f"\U0001f534 <b>CLASS {crash_class} CRASH</b> in <code>{fname}</code>\n"
            f"\U0001f4cb {pattern}\n"
            f"\u274c Ollama returned unparseable response"
        )
        return

    try:
        diagnosis = json.loads(json_text)
    except json.JSONDecodeError:
        logger.warning("JSON parse failed on Ollama response")
        send_telegram(
            f"\U0001f534 <b>CLASS {crash_class} CRASH</b> in <code>{fname}</code>\n"
            f"\U0001f4cb {pattern}\n"
            f"\u274c Ollama JSON malformed"
        )
        return

    confidence = float(diagnosis.get("confidence", 0))
    diag_text = diagnosis.get("diagnosis", "No diagnosis")
    patch_diff = diagnosis.get("patch_diff", "")

    logger.info("Diagnosis: %s (confidence: %.2f)", diag_text[:100], confidence)

    # Gate 1: confidence check
    if confidence < 0.8:
        logger.info("Confidence %.2f < 0.8 — skipping auto-patch", confidence)
        send_telegram(
            f"\U0001f534 <b>CLASS {crash_class} CRASH</b> in <code>{fname}</code>\n"
            f"\U0001f4cb {diag_text[:200]}\n"
            f"\U0001f3af Confidence: {confidence:.0%} (below 80% threshold)\n"
            f"\U0001f527 Manual fix recommended"
        )
        return

    if not patch_diff.strip():
        logger.info("No patch provided despite high confidence")
        send_telegram(
            f"\U0001f534 <b>CLASS {crash_class} CRASH</b> in <code>{fname}</code>\n"
            f"\U0001f4cb {diag_text[:200]}\n"
            f"\U0001f3af Confidence: {confidence:.0%}\n"
            f"\u26a0\ufe0f No patch diff provided"
        )
        return

    # Apply patch
    logger.info("Applying patch to %s...", fname)
    patch_file = Path("/tmp/watchdog_patch.diff")
    patch_file.write_text(patch_diff)

    try:
        result = subprocess.run(
            ["patch", "-p0", "--dry-run", "-i", str(patch_file)],
            capture_output=True, text=True, timeout=10, cwd=str(BASE),
        )
        if result.returncode != 0:
            logger.warning("Patch dry-run failed: %s", result.stderr)
            send_telegram(
                f"\U0001f534 <b>CLASS {crash_class} CRASH</b> in <code>{fname}</code>\n"
                f"\U0001f4cb {diag_text[:200]}\n"
                f"\u274c Patch dry-run failed\n"
                f"\U0001f527 Manual fix needed"
            )
            return

        # Apply for real
        result = subprocess.run(
            ["patch", "-p0", "-i", str(patch_file)],
            capture_output=True, text=True, timeout=10, cwd=str(BASE),
        )
        if result.returncode != 0:
            logger.error("Patch apply failed: %s", result.stderr)
            send_telegram(
                f"\U0001f534 <b>PATCH FAILED</b> for <code>{fname}</code>\n"
                f"\u274c {result.stderr[:200]}"
            )
            return
    except Exception as e:
        logger.error("Patch subprocess error: %s", e)
        return

    logger.info("Patch applied — running regression tests...")

    # Gate 2: regression test
    try:
        test_result = subprocess.run(
            ["bash", str(REGRESSION_SCRIPT)],
            capture_output=True, text=True, timeout=300, cwd=str(BASE),
        )
        test_output = test_result.stdout + test_result.stderr
        fail_count = len(re.findall(r"FAIL", test_output))
    except Exception as e:
        logger.error("Regression test error: %s", e)
        fail_count = 999

    if fail_count > 0:
        # Gate 3: revert on failure
        logger.warning("Regression tests failed (%d FAILs) — reverting patch", fail_count)
        subprocess.run(
            ["git", "checkout", "--", affected_file],
            capture_output=True, cwd=str(BASE),
        )
        send_telegram(
            f"\U0001f534 <b>PATCH REVERTED</b> for <code>{fname}</code>\n"
            f"\U0001f4cb {diag_text[:200]}\n"
            f"\U0001f9ea Regression: {fail_count} FAILs\n"
            f"\u21a9\ufe0f File reverted to pre-patch state"
        )
        return

    # Success — commit + record
    logger.info("All tests passed — committing patch")
    record_patch(affected_file)
    increment_patch_count()

    subprocess.run(
        ["git", "add", affected_file],
        capture_output=True, cwd=str(BASE),
    )
    commit_msg = f"fix(watchdog): auto-patch {fname} — {diag_text[:80]}"
    subprocess.run(
        ["git", "commit", "-m", commit_msg],
        capture_output=True, cwd=str(BASE),
    )

    # Log patch to JSONL
    patch_record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "crash_class": crash_class,
        "pattern": pattern,
        "file": affected_file,
        "diagnosis": diag_text,
        "confidence": confidence,
        "tests_passed": True,
    }
    with open(PATCH_LOG, "a") as f:
        f.write(json.dumps(patch_record) + "\n")

    # Restart render loop if it was dead
    if not process_alive("overnight_render_loop"):
        logger.info("Render loop is dead — attempting restart")
        subprocess.Popen(
            ["bash", "-c",
             f"cd {BASE} && nohup python3 overnight_render_loop.py "
             f">> {LOGS_DIR}/overnight_loop.log 2>&1 &"],
        )

    send_telegram(
        f"\u2705 <b>PATCH APPLIED</b> — <code>{fname}</code>\n"
        f"\U0001f4cb {diag_text[:200]}\n"
        f"\U0001f3af Confidence: {confidence:.0%}\n"
        f"\U0001f9ea Regression: ALL PASS\n"
        f"\U0001f4dd Committed: {commit_msg[:80]}"
    )


# ===================================================================
# LAYER 1 — REACTIVE CHECK (every 60s)
# ===================================================================

def run_reactive_check():
    """Tail overnight_loop.log, detect crashes, diagnose + patch."""
    logger.info("-- REACTIVE CHECK --")

    # Self-health: is Ollama alive?
    if not ollama_healthy():
        logger.error("Ollama not responding on %s", OLLAMA_URL)
        send_telegram(
            "\u26a0\ufe0f <b>WATCHDOG ALERT</b>: Ollama not responding on GPU 2 "
            "— self-restart attempted"
        )
        subprocess.Popen(
            ["bash", "-c",
             "CUDA_VISIBLE_DEVICES=2 OLLAMA_HOST=127.0.0.1:11435 "
             "/usr/local/bin/ollama serve &"],
        )
        return

    # Write last-run timestamp for self-health monitoring
    Path("/tmp/watchdog_last_run.txt").write_text(
        datetime.now(timezone.utc).isoformat()
    )

    # Check render loop alive
    loop_alive = process_alive("overnight_render_loop")

    # Tail the log
    log_tail = tail_file(OVERNIGHT_LOG, 50)
    # CRITICAL FIX: also scan producer_debug.log — KeyErrors live there not in loop log
    from pathlib import Path as _P
    producer_log = _P("/tmp/producer_debug.log")
    if producer_log.exists():
        producer_tail = tail_file(producer_log, 30)
        if "KeyError" in producer_tail or "Traceback" in producer_tail:
            log_tail = log_tail + chr(10) + producer_tail
    if not log_tail.strip():
        logger.info("No log content to analyze")
        if not loop_alive:
            logger.warning("Render loop is NOT running and no log activity")
            send_telegram(
                "\u26a0\ufe0f <b>WATCHDOG</b>: Render loop appears dead — no log activity\n"
                "Check manually: <code>pgrep -f overnight_render_loop</code>"
            )
        return

    # Classify
    crash_class, pattern = classify_crash(log_tail)
    if not crash_class:
        logger.info("No crash patterns detected — all clear")
        return

    logger.info("CRASH DETECTED: CLASS %s — %s", crash_class, pattern)
    diagnose_and_patch(log_tail, crash_class, pattern)


# ===================================================================
# LAYER 2 — PERIODIC HEALTH SCAN (every 15 min)
# ===================================================================

def run_health_scan():
    """Fresh system health check — reads everything from scratch."""
    logger.info("-- HEALTH SCAN --")

    checks = {}

    # Render loop alive?
    checks["render_loop"] = process_alive("overnight_render_loop")

    # Flask alive?
    checks["flask"] = flask_alive()

    # Ollama alive?
    checks["ollama"] = ollama_healthy()

    # GPU VRAM
    gpus = gpu_vram()
    checks["gpus"] = []
    for g in gpus:
        pct = round(g["vram_used_mb"] / g["vram_total_mb"] * 100, 1) if g["vram_total_mb"] > 0 else 0
        checks["gpus"].append({
            "index": g["index"],
            "used_mb": g["vram_used_mb"],
            "total_mb": g["vram_total_mb"],
            "pct": pct,
        })
        if g["index"] in (0, 1) and pct > 90:
            send_telegram(
                f"\u26a0\ufe0f <b>GPU {g['index']} VRAM HIGH</b>: {pct}% "
                f"({g['vram_used_mb']}MB / {g['vram_total_mb']}MB)"
            )

    # Disk space
    free_gb = disk_free_gb()
    checks["disk_free_gb"] = free_gb
    if 0 < free_gb < 200:
        send_telegram(f"\u26a0\ufe0f <b>LOW DISK</b>: {free_gb}GB free (threshold: 200GB)")

    # Last successful grade from loop log
    last_grade = "UNKNOWN"
    if OVERNIGHT_LOG.exists():
        try:
            result = subprocess.run(
                ["grep", "-oP", r"GRADE: [A-F]", str(OVERNIGHT_LOG)],
                capture_output=True, text=True, timeout=10,
            )
            grades = result.stdout.strip().splitlines()
            if grades:
                last_grade = grades[-1]
        except Exception:
            pass
    checks["last_grade"] = last_grade

    # Audio lines in TTS cache
    audio_pattern = str(BASE / "video_pipeline_v3" / "tts_cache" / "*.m4a")
    audio_count = len(glob.glob(audio_pattern))
    checks["audio_files_in_cache"] = audio_count

    # Patches in last 24h
    patches_24h = 0
    if PATCH_LOG.exists():
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        for line in PATCH_LOG.read_text().splitlines():
            try:
                rec = json.loads(line)
                if rec.get("timestamp", "") > cutoff:
                    patches_24h += 1
            except json.JSONDecodeError:
                pass
    checks["patches_24h"] = patches_24h

    logger.info(
        "Health: loop=%s flask=%s ollama=%s disk=%.0fGB grade=%s patches_24h=%d",
        checks["render_loop"], checks["flask"], checks["ollama"],
        free_gb, last_grade, patches_24h,
    )

    # Alert if critical services down
    issues = []
    if not checks["render_loop"]:
        issues.append("\u274c Render loop DOWN")
    if not checks["flask"]:
        issues.append("\u274c Flask DOWN")
    if not checks["ollama"]:
        issues.append("\u274c Ollama DOWN")

    if issues:
        send_telegram(
            "\u26a0\ufe0f <b>HEALTH SCAN ALERT</b>\n" + "\n".join(issues)
        )

    # Ask Ollama for health assessment (fresh context)
    if ollama_healthy():
        health_prompt = (
            f"System health snapshot:\n{json.dumps(checks, indent=2)}\n\n"
            "Briefly assess: any concerning patterns? One paragraph max."
        )
        assessment = ollama_chat(
            "You are a DevOps engineer monitoring a video production pipeline. Be concise.",
            health_prompt,
        )
        if assessment:
            logger.info("Health assessment: %s", assessment[:200])

    return checks


# ===================================================================
# LAYER 3 — PATTERN ANALYSIS (every 6 hours)
# ===================================================================

def run_pattern_analysis():
    """Analyze 7 days of logs for trends — fresh Ollama conversation."""
    logger.info("-- PATTERN ANALYSIS --")

    if not ollama_healthy():
        logger.error("Ollama not available for pattern analysis")
        return

    # Gather last 7 days of loop logs (tail 2000 lines)
    log_content = tail_file(OVERNIGHT_LOG, 2000)

    # Also check episode log files
    extra_logs = ""
    for logname in ["episode_morning.log", "episode_noon.log", "episode_evening.log"]:
        logpath = LOGS_DIR / logname
        if logpath.exists():
            extra_logs += f"\n--- {logname} ---\n" + tail_file(logpath, 500)

    # Read patch history
    patch_history = ""
    if PATCH_LOG.exists():
        patch_history = tail_file(PATCH_LOG, 100)

    analysis_prompt = (
        "Analyze these 7 days of render logs. Identify:\n"
        "1. Most frequent crash type and root cause\n"
        "2. Time-of-day patterns in failures\n"
        "3. Any silent degradation in grades\n"
        "4. Files that appear in >50% of crashes\n"
        "5. Recommended preventive fixes\n\n"
        f"OVERNIGHT LOOP LOG (last 2000 lines):\n{log_content[:8000]}\n\n"
        f"ADDITIONAL EPISODE LOGS:\n{extra_logs[:4000]}\n\n"
        f"PATCH HISTORY:\n{patch_history[:2000]}"
    )

    response = ollama_chat(
        "You are a senior SRE analyzing production pipeline logs. "
        "Focus on patterns and trends, not individual events. Be specific with data.",
        analysis_prompt,
    )

    if not response:
        logger.error("Pattern analysis failed — no Ollama response")
        return

    # Write analysis file
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    analysis_path = LOGS_DIR / f"watchdog_analysis_{date_str}.md"
    analysis_path.write_text(
        f"# Watchdog Pattern Analysis — {date_str}\n\n{response}\n"
    )
    logger.info("Analysis written to %s", analysis_path)

    # Check for P0 patterns
    if any(kw in response.lower() for kw in ["critical", "p0", "urgent", "data loss", "cascade"]):
        send_telegram(
            f"\U0001f4ca <b>PATTERN ANALYSIS — P0 FOUND</b>\n\n"
            f"{response[:800]}"
        )
    else:
        logger.info("No P0 patterns found in analysis")


# ===================================================================
# LAYER 4 — WEEKLY DEEP AUDIT (Monday 08:00 UTC)
# ===================================================================

def run_weekly_audit():
    """Deep audit: compare gospels vs actual behavior over 30 days."""
    logger.info("-- WEEKLY AUDIT --")

    if not ollama_healthy():
        logger.error("Ollama not available for weekly audit")
        return

    # Read gospels
    gospels_dir = BASE / "docs" / "gospels"
    gospel_content = ""
    if gospels_dir.exists():
        for gf in sorted(gospels_dir.glob("*.md")):
            text = gf.read_text()[:3000]
            gospel_content += f"\n--- {gf.name} ---\n{text}\n"

    # Pipeline laws
    laws_path = BASE / "PIPELINE_LAWS.md"
    laws_content = ""
    if laws_path.exists():
        laws_content = laws_path.read_text()[:4000]

    # Last 30 days log (tail 5000 lines)
    log_content = tail_file(OVERNIGHT_LOG, 5000)

    # Git log last 50 commits
    try:
        git_result = subprocess.run(
            ["git", "log", "--oneline", "-50"],
            capture_output=True, text=True, timeout=10, cwd=str(BASE),
        )
        git_log = git_result.stdout
    except Exception:
        git_log = "(unavailable)"

    # Patch history
    patch_history = ""
    if PATCH_LOG.exists():
        patch_history = PATCH_LOG.read_text()[-3000:]

    audit_prompt = (
        "You are auditing the Protocol Pulse pipeline. Read the gospel docs "
        "and compare against actual behavior in logs. Identify:\n"
        "1. Gospel violations (rules being broken)\n"
        "2. Technical debt accumulating\n"
        "3. Costs trending up or down\n"
        "4. Modules that have had >3 patches in 30 days (fragile code)\n"
        "5. Recommended refactors\n\n"
        f"GOSPEL DOCS:\n{gospel_content[:6000]}\n\n"
        f"PIPELINE LAWS:\n{laws_content[:4000]}\n\n"
        f"LOOP LOG (recent):\n{log_content[:6000]}\n\n"
        f"GIT LOG:\n{git_log[:2000]}\n\n"
        f"PATCH HISTORY:\n{patch_history[:2000]}"
    )

    response = ollama_chat(
        "You are a senior engineer auditing a production video pipeline. "
        "Compare documented rules against actual system behavior. Be specific.",
        audit_prompt,
    )

    if not response:
        logger.error("Weekly audit failed — no Ollama response")
        return

    # Write audit file
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    audit_path = LOGS_DIR / f"weekly_audit_{date_str}.md"
    audit_path.write_text(
        f"# Watchdog Weekly Audit — {date_str}\n\n{response}\n"
    )
    logger.info("Audit written to %s", audit_path)

    # Telegram with top findings
    send_telegram(
        f"\U0001f4cb <b>WEEKLY AUDIT — {date_str}</b>\n\n"
        f"{response[:800]}"
    )


# ===================================================================
# DAILY BRIEFING (09:00 ET / 13:00 UTC)
# ===================================================================

def send_daily_briefing():
    """Morning Telegram summary — gospel format."""
    logger.info("-- DAILY BRIEFING --")

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Last grade
    last_grade = "UNKNOWN"
    last_score = "?"
    last_time = "?"
    if OVERNIGHT_LOG.exists():
        try:
            result = subprocess.run(
                ["grep", "-P", r"GRADE:", str(OVERNIGHT_LOG)],
                capture_output=True, text=True, timeout=10,
            )
            lines = result.stdout.strip().splitlines()
            if lines:
                last_line = lines[-1]
                grade_match = re.search(r"GRADE:\s*([A-F])", last_line)
                if grade_match:
                    last_grade = grade_match.group(1)
                score_match = re.search(r"(\d+)/100", last_line)
                if score_match:
                    last_score = score_match.group(1)
                time_match = re.search(r"(\d{2}:\d{2})", last_line)
                if time_match:
                    last_time = time_match.group(1)
        except Exception:
            pass

    # Patches in 24h
    patches_24h = 0
    if PATCH_LOG.exists():
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        for line in PATCH_LOG.read_text().splitlines():
            try:
                rec = json.loads(line)
                if rec.get("timestamp", "") > cutoff:
                    patches_24h += 1
            except json.JSONDecodeError:
                pass

    # Disk
    free_gb = disk_free_gb()

    # GPU 2 VRAM
    gpu2_vram = "?"
    for g in gpu_vram():
        if g["index"] == 2:
            gpu2_vram = f"{g['vram_used_mb'] / 1024:.1f}GB"

    # Articles count today
    article_count = "?"
    db_path = BASE / "instance" / "protocol_pulse.db"
    if db_path.exists():
        try:
            import sqlite3
            conn = sqlite3.connect(str(db_path))
            today_start = datetime.now(timezone.utc).replace(
                hour=0, minute=0, second=0
            ).isoformat()
            row = conn.execute(
                "SELECT COUNT(*) FROM articles WHERE created_at > ?",
                (today_start,)
            ).fetchone()
            article_count = str(row[0]) if row else "0"
            conn.close()
        except Exception:
            pass

    # Alerts in 24h
    alert_count = 0
    if LOG_FILE.exists():
        try:
            result = subprocess.run(
                ["grep", "-c", "-E", "CRASH DETECTED|PATCH|ALERT", str(LOG_FILE)],
                capture_output=True, text=True, timeout=10,
            )
            alert_count = int(result.stdout.strip()) if result.stdout.strip() else 0
        except Exception:
            pass

    # Determine status
    issues = []
    if not process_alive("overnight_render_loop"):
        issues.append("render loop down")
    if not flask_alive():
        issues.append("Flask down")
    if not ollama_healthy():
        issues.append("Ollama down")

    status = "\u2705 All systems nominal" if not issues else f"\u274c Issues: {', '.join(issues)}"

    briefing = (
        f"\U0001f916 <b>WATCHDOG DAILY — {date_str}</b>\n"
        f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
        f"\U0001f3ac Render: {last_grade} ({last_score}/100) at {last_time}\n"
        f"\U0001f527 Patches applied: {patches_24h} (last 24h)\n"
        f"\U0001f4be Disk free: {free_gb}GB\n"
        f"\U0001f9e0 GPU 2 (Watchdog): {gpu2_vram} / 24GB\n"
        f"\U0001f4ca Articles generated: {article_count}\n"
        f"\u26a0\ufe0f Alerts: {alert_count}\n"
        f"{status}"
    )

    send_telegram(briefing)
    logger.info("Daily briefing sent")


# ===================================================================
# MAIN — route by --mode flag
# ===================================================================

def main():
    parser = argparse.ArgumentParser(description="Protocol Pulse Local LLM Watchdog")
    parser.add_argument(
        "--mode",
        choices=["reactive", "health", "pattern", "audit", "briefing"],
        default="reactive",
        help="Check layer to run",
    )
    args = parser.parse_args()

    logger.info("=" * 50)
    logger.info(
        "WATCHDOG RUN — mode=%s — %s",
        args.mode, datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )
    logger.info("=" * 50)

    if args.mode == "reactive":
        run_reactive_check()
    elif args.mode == "health":
        run_health_scan()
    elif args.mode == "pattern":
        run_pattern_analysis()
    elif args.mode == "audit":
        run_weekly_audit()
    elif args.mode == "briefing":
        send_daily_briefing()

    logger.info("WATCHDOG RUN COMPLETE — mode=%s", args.mode)


if __name__ == "__main__":
    main()
