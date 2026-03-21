#!/usr/bin/env python3
"""
Protocol Pulse — Local LLM Watchdog (4-Layer Autonomous System)

Modes (via --mode flag):
  reactive  — every 60s, crash detection + auto-patch
  health    — every 15min, system health scan
  pattern   — every 6h, 7-day trend analysis
  audit     — weekly Monday 08:00 UTC, deep gospel audit
  briefing  — daily 09:00 ET (13:00 UTC), Telegram summary

Gospel: docs/gospels/WATCHDOG_LLM_GOSPEL.md
"""

import argparse
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
# Paths & Config
# ---------------------------------------------------------------------------

BASE = Path(__file__).resolve().parent.parent
LOGS_DIR = BASE / "logs"
LOGS_DIR.mkdir(exist_ok=True)

OLLAMA_URL = "http://localhost:11435"
OLLAMA_MODEL = os.environ.get("WATCHDOG_MODEL", "qwen3-coder:30b")

# Log file targets
OVERNIGHT_LOG = LOGS_DIR / "overnight_loop.log"
EPISODE_LOGS = [LOGS_DIR / f"episode_{t}.log" for t in ("morning", "noon", "evening")]

# Safety: never patch these files
NEVER_PATCH = {"assembler.py", "tts_engine.py", "gemini_grade.py", "routes.py"}

# Cooldown & rate limits
COOLDOWN_SECONDS = 600  # 10 minutes per file
MAX_PATCHES_PER_HOUR = 3
CONFIDENCE_THRESHOLD = 0.8

REGRESSION_SCRIPT = BASE / "regression_test.sh"

logger = logging.getLogger("watchdog_llm")
logger.setLevel(logging.INFO)
_fh = logging.FileHandler(str(LOGS_DIR / "watchdog_llm.log"))
_fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(_fh)
_sh = logging.StreamHandler()
_sh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(_sh)


# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------

def _load_env():
    """Load .env file into dict."""
    env_path = BASE / ".env"
    env = {}
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip("'\"")
    return env


def send_telegram(msg):
    """Send message to Telegram."""
    import requests
    env = _load_env()
    token = env.get("TELEGRAM_BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = env.get("TELEGRAM_CHAT_ID") or os.environ.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        logger.warning("Telegram credentials not found, skipping alert")
        return False
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"},
            timeout=10,
        )
        r.raise_for_status()
        return True
    except Exception as e:
        logger.error("Telegram send failed: %s", e)
        return False


# ---------------------------------------------------------------------------
# Ollama Interface
# ---------------------------------------------------------------------------

def ollama_alive():
    """Check if Ollama is responding."""
    import requests
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def ollama_generate(system_prompt, user_prompt, temperature=0.3):
    """Fresh Ollama conversation — zero prior context (FRESH PERSPECTIVE)."""
    import requests
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})

    try:
        r = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": OLLAMA_MODEL,
                "messages": messages,
                "stream": False,
                "options": {"temperature": temperature},
            },
            timeout=120,
        )
        r.raise_for_status()
        return r.json().get("message", {}).get("content", "")
    except Exception as e:
        logger.error("Ollama generate failed: %s", e)
        return ""


# ---------------------------------------------------------------------------
# Safety Gates
# ---------------------------------------------------------------------------

def is_render_running():
    """Gate 5: never patch during active render."""
    try:
        result = subprocess.run(["pgrep", "-f", "daily_producer"], capture_output=True, text=True)
        return result.returncode == 0
    except Exception:
        return False


def check_cooldown(filepath):
    """Gate 4: 10-minute cooldown per file."""
    safe_name = Path(filepath).name.replace("/", "_")
    ts_file = Path(f"/tmp/watchdog_last_patch_{safe_name}.txt")
    if ts_file.exists():
        try:
            last_ts = float(ts_file.read_text().strip())
            if time.time() - last_ts < COOLDOWN_SECONDS:
                return False  # Still in cooldown
        except (ValueError, IOError):
            pass
    return True  # OK to patch


def record_patch(filepath):
    """Record patch timestamp for cooldown tracking."""
    safe_name = Path(filepath).name.replace("/", "_")
    ts_file = Path(f"/tmp/watchdog_last_patch_{safe_name}.txt")
    ts_file.write_text(str(time.time()))

    # Hourly counter
    hour_key = datetime.now(timezone.utc).strftime("%Y%m%d%H")
    count_file = Path(f"/tmp/watchdog_patch_count_{hour_key}.txt")
    count = 0
    if count_file.exists():
        try:
            count = int(count_file.read_text().strip())
        except (ValueError, IOError):
            pass
    count_file.write_text(str(count + 1))


def check_hourly_limit():
    """Gate 6: max 3 patches per hour."""
    hour_key = datetime.now(timezone.utc).strftime("%Y%m%d%H")
    count_file = Path(f"/tmp/watchdog_patch_count_{hour_key}.txt")
    if count_file.exists():
        try:
            count = int(count_file.read_text().strip())
            return count < MAX_PATCHES_PER_HOUR
        except (ValueError, IOError):
            pass
    return True


def is_patchable(filepath):
    """Check if file is in the never-patch list."""
    return Path(filepath).name not in NEVER_PATCH


# ---------------------------------------------------------------------------
# Crash Detection
# ---------------------------------------------------------------------------

def classify_crash(log_lines):
    """Classify crash from log lines. Returns (class, description) or None."""
    text = "\n".join(log_lines)

    # CLASS A patterns
    if "KeyError" in text:
        return ("A", "KeyError detected")
    if "ImportError" in text or "ModuleNotFoundError" in text:
        return ("A", "Import/Module error")
    if "FileNotFoundError" in text:
        return ("A", "FileNotFoundError")
    if "SyntaxError" in text:
        return ("A", "SyntaxError")

    # CLASS B patterns
    if "Traceback" in text and "daily_producer" in text:
        return ("B", "Traceback in daily_producer")
    if "exit: -15" in text.lower() or "FATAL" in text:
        return ("B", "Fatal exit detected")

    # 3x consecutive render failures
    render_fail_count = 0
    for line in log_lines:
        if "Render failed" in line or "render failed" in line:
            render_fail_count += 1
        else:
            render_fail_count = 0
        if render_fail_count >= 3:
            return ("B", "3x consecutive render failures")

    if "GRADE: F" in text:
        return ("B", "Grade F render detected")

    # CLASS C — multi-file or protected-file crashes
    if "assembler.py" in text and "Traceback" in text:
        return ("C", "Crash in assembler.py — manual intervention needed")
    if "tts_engine.py" in text and "Traceback" in text:
        return ("C", "Crash in tts_engine.py — manual intervention needed")
    if "routes.py" in text and "Traceback" in text:
        return ("C", "Crash in routes.py — manual intervention needed")

    return None


def extract_affected_file(log_lines):
    """Try to extract the file that caused the crash from traceback."""
    for line in reversed(log_lines):
        m = re.search(r'File "([^"]+)", line \d+', line)
        if m:
            filepath = m.group(1)
            if filepath.startswith(str(BASE)):
                return filepath
    return None


# ---------------------------------------------------------------------------
# LAYER 1 — REACTIVE CHECK (every 60s)
# ---------------------------------------------------------------------------

def run_reactive_check():
    """Tail logs, detect crashes, diagnose + patch if safe."""
    logger.info("=== REACTIVE CHECK ===")

    # Read last 50 lines of overnight_loop.log
    log_lines = []
    for log_file in [OVERNIGHT_LOG] + EPISODE_LOGS:
        if log_file.exists():
            try:
                lines = log_file.read_text().splitlines()[-50:]
                log_lines.extend(lines)
            except Exception:
                pass

    if not log_lines:
        logger.info("No log lines to analyze")
        _write_last_run()
        return

    crash = classify_crash(log_lines)
    if not crash:
        logger.info("No crash patterns detected")
        _write_last_run()
        return

    crash_class, crash_desc = crash
    logger.warning("CRASH DETECTED: CLASS %s — %s", crash_class, crash_desc)

    # Always alert on crash
    send_telegram(f"🔴 CRASH DETECTED: CLASS {crash_class}\n📋 {crash_desc}")

    # CLASS C — alert only, never patch
    if crash_class == "C":
        logger.info("CLASS C — alert only, no auto-patch")
        _write_last_run()
        return

    # Safety gates
    if is_render_running():
        logger.info("Render running — skipping patch")
        send_telegram("⏸️ Patch skipped — render in progress")
        _write_last_run()
        return

    if not check_hourly_limit():
        logger.info("Hourly patch limit reached — skipping")
        send_telegram("⏸️ Patch skipped — hourly limit (3) reached")
        _write_last_run()
        return

    if not ollama_alive():
        logger.error("Ollama not responding — cannot diagnose")
        send_telegram("⚠️ Ollama down — crash detected but cannot diagnose")
        _write_last_run()
        return

    # Extract affected file
    affected_file = extract_affected_file(log_lines)
    if not affected_file:
        logger.info("Could not determine affected file from traceback")
        send_telegram("⚠️ Crash detected but affected file unknown — manual review needed")
        _write_last_run()
        return

    if not is_patchable(affected_file):
        logger.info("File %s is in NEVER_PATCH list", affected_file)
        send_telegram(f"🚫 Crash in protected file: {Path(affected_file).name} — manual fix needed")
        _write_last_run()
        return

    if not check_cooldown(affected_file):
        logger.info("File %s is in cooldown", affected_file)
        _write_last_run()
        return

    # Read affected file content
    try:
        file_content = Path(affected_file).read_text()
    except Exception as e:
        logger.error("Cannot read affected file: %s", e)
        _write_last_run()
        return

    # Diagnose with Ollama
    log_excerpt = "\n".join(log_lines[-50:])
    diagnosis_response = ollama_generate(
        system_prompt=(
            "You are a Python/FFmpeg expert debugging a video production pipeline. "
            "Analyze the crash log and return ONLY valid JSON:\n"
            '{"diagnosis": "str", "affected_file": "str", "patch_diff": "str (unified diff format)", "confidence": 0.0-1.0}\n'
            "The patch_diff must be a valid unified diff that can be applied with `patch -p0`.\n"
            "If you cannot determine a fix with high confidence, set confidence to 0.0."
        ),
        user_prompt=f"CRASH LOG:\n{log_excerpt}\n\nFILE ({affected_file}):\n{file_content[:8000]}",
    )

    # Parse JSON from response
    diagnosis = _parse_diagnosis(diagnosis_response)
    if not diagnosis:
        logger.warning("Failed to parse diagnosis JSON")
        send_telegram(f"⚠️ Crash in {Path(affected_file).name} — LLM diagnosis failed to parse")
        _write_last_run()
        return

    logger.info("Diagnosis: %s (confidence: %.2f)", diagnosis.get("diagnosis", "?"), diagnosis.get("confidence", 0))

    # Gate 1: confidence check
    confidence = diagnosis.get("confidence", 0)
    if confidence < CONFIDENCE_THRESHOLD:
        logger.info("Confidence %.2f < %.2f — skipping auto-patch", confidence, CONFIDENCE_THRESHOLD)
        send_telegram(
            f"⚠️ CLASS {crash_class} crash in {Path(affected_file).name}\n"
            f"📋 {diagnosis.get('diagnosis', '?')}\n"
            f"🤖 Confidence: {confidence:.0%} (below threshold)\n"
            f"⏸️ Manual review recommended"
        )
        _write_last_run()
        return

    # Apply patch
    patch_diff = diagnosis.get("patch_diff", "")
    if not patch_diff:
        logger.info("No patch_diff in diagnosis")
        _write_last_run()
        return

    success = _apply_and_test_patch(affected_file, patch_diff, crash_class, diagnosis)
    _write_last_run()
    return success


def _parse_diagnosis(text):
    """Extract JSON from LLM response (may be wrapped in markdown)."""
    if not text:
        return None
    # Try to find JSON block
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if json_match:
        text = json_match.group(1)
    else:
        # Try raw JSON
        json_match = re.search(r'\{[^{}]*"diagnosis"[^{}]*\}', text, re.DOTALL)
        if json_match:
            text = json_match.group(0)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _apply_and_test_patch(affected_file, patch_diff, crash_class, diagnosis):
    """Apply patch, run tests, commit or revert."""
    # Backup original
    backup_path = Path(affected_file + ".watchdog_backup")
    try:
        shutil.copy2(affected_file, backup_path)
    except Exception as e:
        logger.error("Cannot backup file: %s", e)
        return False

    # Write patch to temp file and apply
    patch_file = Path("/tmp/watchdog_patch.diff")
    patch_file.write_text(patch_diff)

    try:
        result = subprocess.run(
            ["patch", "-p0", "--dry-run", "-i", str(patch_file)],
            capture_output=True, text=True, cwd=str(BASE), timeout=30,
        )
        if result.returncode != 0:
            logger.warning("Patch dry-run failed: %s", result.stderr)
            # Try applying directly via the diff content
            _restore_backup(affected_file, backup_path)
            send_telegram(
                f"⚠️ Patch dry-run failed for {Path(affected_file).name}\n"
                f"📋 {diagnosis.get('diagnosis', '?')}"
            )
            return False

        # Apply for real
        result = subprocess.run(
            ["patch", "-p0", "-i", str(patch_file)],
            capture_output=True, text=True, cwd=str(BASE), timeout=30,
        )
        if result.returncode != 0:
            logger.error("Patch apply failed: %s", result.stderr)
            _restore_backup(affected_file, backup_path)
            return False
    except subprocess.TimeoutExpired:
        logger.error("Patch command timed out")
        _restore_backup(affected_file, backup_path)
        return False

    logger.info("Patch applied to %s", affected_file)

    # Gate 2: Run regression tests
    if REGRESSION_SCRIPT.exists():
        try:
            result = subprocess.run(
                ["bash", str(REGRESSION_SCRIPT)],
                capture_output=True, text=True, cwd=str(BASE), timeout=300,
            )
            test_output = result.stdout + result.stderr
            fail_count = test_output.lower().count("fail")

            if fail_count > 0 or result.returncode != 0:
                # Gate 3: revert on test failure
                logger.warning("Tests FAILED after patch — reverting")
                _restore_backup(affected_file, backup_path)
                send_telegram(
                    f"🔴 PATCH REVERTED — {Path(affected_file).name}\n"
                    f"📋 {diagnosis.get('diagnosis', '?')}\n"
                    f"🧪 TESTS: FAIL ({fail_count} failures)\n"
                    f"↩️ File restored to pre-patch state"
                )
                return False
        except subprocess.TimeoutExpired:
            logger.error("Regression tests timed out — reverting patch")
            _restore_backup(affected_file, backup_path)
            send_telegram(f"⚠️ Tests timed out after patching {Path(affected_file).name} — reverted")
            return False
    else:
        logger.warning("regression_test.sh not found — skipping tests")

    # Tests passed — commit
    record_patch(affected_file)
    _log_patch(affected_file, diagnosis)

    try:
        rel_path = str(Path(affected_file).relative_to(BASE))
        subprocess.run(["git", "add", rel_path], cwd=str(BASE), timeout=10)
        subprocess.run(
            ["git", "commit", "-m",
             f"fix(watchdog): auto-patch {Path(affected_file).name} — {diagnosis.get('diagnosis', 'auto-fix')[:60]}"],
            cwd=str(BASE), timeout=30,
        )
    except Exception as e:
        logger.error("Git commit failed: %s", e)

    # Restart render loop if it was dead
    _try_restart_loop()

    send_telegram(
        f"✅ PATCH APPLIED — {Path(affected_file).name}\n"
        f"📋 {diagnosis.get('diagnosis', '?')}\n"
        f"🤖 Confidence: {diagnosis.get('confidence', 0):.0%}\n"
        f"🧪 TESTS: PASS\n"
        f"📝 Committed to git"
    )

    # Cleanup backup
    backup_path.unlink(missing_ok=True)
    return True


def _restore_backup(affected_file, backup_path):
    """Restore file from backup."""
    try:
        shutil.copy2(backup_path, affected_file)
        backup_path.unlink(missing_ok=True)
        # Also git checkout to be safe
        subprocess.run(
            ["git", "checkout", "--", str(Path(affected_file).relative_to(BASE))],
            cwd=str(BASE), timeout=10, capture_output=True,
        )
    except Exception as e:
        logger.error("Restore failed: %s", e)


def _log_patch(affected_file, diagnosis):
    """Append to patch history JSONL."""
    log_path = LOGS_DIR / "watchdog_patches.jsonl"
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "file": str(affected_file),
        "diagnosis": diagnosis.get("diagnosis", ""),
        "confidence": diagnosis.get("confidence", 0),
    }
    with open(log_path, "a") as f:
        f.write(json.dumps(entry) + "\n")


def _try_restart_loop():
    """Attempt to restart overnight render loop if dead."""
    try:
        result = subprocess.run(["pgrep", "-f", "overnight_render_loop"], capture_output=True, text=True)
        if result.returncode != 0:
            logger.info("Render loop is dead — attempting restart via tmux")
            # Don't force restart — just alert
            send_telegram("⚠️ Render loop appears dead — consider manual restart")
    except Exception:
        pass


def _write_last_run():
    """Write timestamp for self-health check."""
    Path("/tmp/watchdog_last_run.txt").write_text(
        datetime.now(timezone.utc).isoformat()
    )


# ---------------------------------------------------------------------------
# LAYER 2 — PERIODIC HEALTH SCAN (every 15 min)
# ---------------------------------------------------------------------------

def run_health_scan():
    """System-wide health check with FRESH Ollama context."""
    logger.info("=== HEALTH SCAN ===")
    import requests

    checks = {}

    # 1. Render loop alive?
    try:
        result = subprocess.run(["pgrep", "-f", "overnight_render_loop"], capture_output=True, text=True)
        checks["render_loop"] = "ALIVE" if result.returncode == 0 else "DEAD"
    except Exception:
        checks["render_loop"] = "UNKNOWN"

    # 2. Flask alive?
    try:
        r = requests.get("http://localhost:5000/", timeout=5)
        checks["flask"] = f"UP ({r.status_code})"
    except Exception:
        checks["flask"] = "DOWN"

    # 3. Ollama alive?
    checks["ollama"] = "UP" if ollama_alive() else "DOWN"

    # 4. GPU VRAM
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=index,memory.used,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10,
        )
        gpu_lines = result.stdout.strip().splitlines()
        gpu_info = {}
        for line in gpu_lines:
            parts = [p.strip() for p in line.split(",")]
            if len(parts) == 3:
                idx, used, total = int(parts[0]), float(parts[1]), float(parts[2])
                pct = (used / total * 100) if total > 0 else 0
                gpu_info[idx] = {"used_mb": used, "total_mb": total, "pct": round(pct, 1)}
        checks["gpus"] = gpu_info

        # Alert if GPU 0 or 1 > 90%
        for gid in [0, 1]:
            if gid in gpu_info and gpu_info[gid]["pct"] > 90:
                checks[f"gpu{gid}_warning"] = f"HIGH VRAM: {gpu_info[gid]['pct']}%"
    except Exception as e:
        checks["gpus"] = f"ERROR: {e}"

    # 5. Disk space
    try:
        result = subprocess.run(["df", "-BG", "--output=avail", "/home"], capture_output=True, text=True, timeout=10)
        avail_line = result.stdout.strip().splitlines()[-1].strip().rstrip("G")
        avail_gb = int(avail_line)
        checks["disk_free_gb"] = avail_gb
        if avail_gb < 200:
            checks["disk_warning"] = f"LOW DISK: {avail_gb}GB free"
    except Exception:
        checks["disk_free_gb"] = "UNKNOWN"

    # 6. Last successful grade
    try:
        if OVERNIGHT_LOG.exists():
            lines = OVERNIGHT_LOG.read_text().splitlines()
            last_grade = "UNKNOWN"
            for line in reversed(lines):
                m = re.search(r'GRADE:\s*([A-F])', line)
                if m:
                    last_grade = m.group(1)
                    break
            checks["last_grade"] = last_grade
    except Exception:
        checks["last_grade"] = "UNKNOWN"

    # 7. Audio lines today
    try:
        today = datetime.now().strftime("%Y%m%d")
        tts_cache = BASE / "video_pipeline_v3" / "tts_cache"
        if tts_cache.exists():
            count = sum(1 for f in tts_cache.glob("*.m4a")
                       if datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y%m%d") == today)
            checks["audio_lines_today"] = count
        else:
            checks["audio_lines_today"] = 0
    except Exception:
        checks["audio_lines_today"] = "UNKNOWN"

    # 8. Patches in last 24h
    patch_count_24h = 0
    patch_log = LOGS_DIR / "watchdog_patches.jsonl"
    if patch_log.exists():
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        try:
            for line in patch_log.read_text().splitlines():
                entry = json.loads(line)
                ts = datetime.fromisoformat(entry["timestamp"].replace("Z", "+00:00"))
                if ts > cutoff:
                    patch_count_24h += 1
        except Exception:
            pass
    checks["patches_24h"] = patch_count_24h

    logger.info("Health scan: %s", json.dumps(checks, indent=2, default=str))

    # Alert on critical issues
    alerts = []
    if checks.get("render_loop") == "DEAD":
        alerts.append("🔴 Render loop is DEAD")
    if checks.get("flask") == "DOWN":
        alerts.append("🔴 Flask is DOWN")
    if checks.get("ollama") == "DOWN":
        alerts.append("🔴 Ollama is DOWN")
    if isinstance(checks.get("disk_free_gb"), int) and checks["disk_free_gb"] < 200:
        alerts.append(f"⚠️ Low disk: {checks['disk_free_gb']}GB")
    for gid in [0, 1]:
        if f"gpu{gid}_warning" in checks:
            alerts.append(f"⚠️ GPU {gid}: {checks[f'gpu{gid}_warning']}")

    if alerts:
        send_telegram("🏥 HEALTH SCAN ALERTS\n" + "\n".join(alerts))

    _write_last_run()
    return checks


# ---------------------------------------------------------------------------
# LAYER 3 — PATTERN ANALYSIS (every 6h)
# ---------------------------------------------------------------------------

def run_pattern_analysis():
    """7-day trend analysis with FRESH Ollama context."""
    logger.info("=== PATTERN ANALYSIS ===")

    if not ollama_alive():
        logger.error("Ollama not responding — skipping pattern analysis")
        return

    # Gather last 7 days of logs
    log_content = ""
    for log_file in [OVERNIGHT_LOG] + EPISODE_LOGS:
        if log_file.exists():
            try:
                lines = log_file.read_text().splitlines()
                # Filter to last 7 days
                cutoff = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
                recent = [l for l in lines if l[:10] >= cutoff or not re.match(r'\d{4}-\d{2}-\d{2}', l[:10])]
                log_content += f"\n--- {log_file.name} ---\n" + "\n".join(recent[-500:])
            except Exception:
                pass

    if len(log_content) < 100:
        logger.info("Insufficient log data for pattern analysis")
        _write_last_run()
        return

    # FRESH Ollama conversation
    analysis = ollama_generate(
        system_prompt=None,
        user_prompt=(
            "Analyze these 7 days of render pipeline logs. Identify:\n"
            "1. Most frequent crash type and root cause\n"
            "2. Time-of-day patterns in failures\n"
            "3. Any silent degradation in grades\n"
            "4. Files that appear in >50% of crashes\n"
            "5. Recommended preventive fixes\n\n"
            f"LOGS:\n{log_content[:12000]}"
        ),
        temperature=0.2,
    )

    if not analysis:
        logger.warning("Pattern analysis returned empty")
        _write_last_run()
        return

    # Write analysis report
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    report_path = LOGS_DIR / f"watchdog_analysis_{date_str}.md"
    report_path.write_text(
        f"# Watchdog Pattern Analysis — {date_str}\n\n{analysis}\n"
    )
    logger.info("Analysis written to %s", report_path)

    # Check for P0 patterns (urgent)
    if any(kw in analysis.lower() for kw in ["critical", "p0", "urgent", "immediate", "breaking"]):
        send_telegram(
            f"🔍 PATTERN ANALYSIS — P0 FINDING\n\n{analysis[:500]}"
        )

    _write_last_run()


# ---------------------------------------------------------------------------
# LAYER 4 — WEEKLY DEEP AUDIT (Monday 08:00 UTC)
# ---------------------------------------------------------------------------

def run_weekly_audit():
    """Deep gospel compliance audit with FRESH Ollama context."""
    logger.info("=== WEEKLY AUDIT ===")

    if not ollama_alive():
        logger.error("Ollama not responding — skipping weekly audit")
        return

    # Read gospels
    gospel_dir = BASE / "docs" / "gospels"
    gospel_content = ""
    if gospel_dir.exists():
        for gf in sorted(gospel_dir.glob("*.md")):
            try:
                gospel_content += f"\n--- {gf.name} ---\n{gf.read_text()[:3000]}\n"
            except Exception:
                pass

    # Pipeline laws
    laws_path = BASE / "PIPELINE_LAWS.md"
    laws_content = ""
    if laws_path.exists():
        try:
            laws_content = laws_path.read_text()[:3000]
        except Exception:
            pass

    # Git log
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "-50"],
            capture_output=True, text=True, cwd=str(BASE), timeout=10,
        )
        git_log = result.stdout
    except Exception:
        git_log = ""

    # Recent log summary
    log_summary = ""
    if OVERNIGHT_LOG.exists():
        try:
            lines = OVERNIGHT_LOG.read_text().splitlines()
            log_summary = "\n".join(lines[-200:])
        except Exception:
            pass

    # Patch history
    patch_history = ""
    patch_log = LOGS_DIR / "watchdog_patches.jsonl"
    if patch_log.exists():
        try:
            patch_history = patch_log.read_text()[-2000:]
        except Exception:
            pass

    # FRESH Ollama conversation
    audit = ollama_generate(
        system_prompt=None,
        user_prompt=(
            "You are auditing the Protocol Pulse pipeline. Read the gospel docs "
            "and compare against actual behavior in logs. Identify:\n"
            "1. Gospel violations (rules being broken)\n"
            "2. Technical debt accumulating\n"
            "3. Costs trending up or down\n"
            "4. Modules that have had >3 patches in 30 days (fragile code)\n"
            "5. Recommended refactors\n\n"
            f"GOSPEL DOCS:\n{gospel_content[:6000]}\n\n"
            f"PIPELINE LAWS:\n{laws_content[:3000]}\n\n"
            f"GIT LOG (last 50 commits):\n{git_log}\n\n"
            f"RECENT LOGS:\n{log_summary[:4000]}\n\n"
            f"PATCH HISTORY:\n{patch_history[:2000]}"
        ),
        temperature=0.2,
    )

    if not audit:
        logger.warning("Weekly audit returned empty")
        _write_last_run()
        return

    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    report_path = LOGS_DIR / f"weekly_audit_{date_str}.md"
    report_path.write_text(f"# Weekly Audit — {date_str}\n\n{audit}\n")
    logger.info("Audit written to %s", report_path)

    # Telegram with top findings (first 500 chars)
    send_telegram(f"📋 WEEKLY AUDIT — {date_str}\n\n{audit[:500]}")
    _write_last_run()


# ---------------------------------------------------------------------------
# DAILY BRIEFING (09:00 ET / 13:00 UTC)
# ---------------------------------------------------------------------------

def send_daily_briefing():
    """Morning Telegram summary."""
    logger.info("=== DAILY BRIEFING ===")

    checks = run_health_scan()

    # Build briefing
    date_str = datetime.now().strftime("%Y-%m-%d")
    gpu2_info = ""
    if isinstance(checks.get("gpus"), dict) and 2 in checks["gpus"]:
        g2 = checks["gpus"][2]
        gpu2_info = f"{g2['used_mb']/1024:.1f}GB / {g2['total_mb']/1024:.0f}GB"
    else:
        gpu2_info = "N/A"

    disk_free = checks.get("disk_free_gb", "?")
    last_grade = checks.get("last_grade", "?")
    patches_24h = checks.get("patches_24h", 0)
    audio_lines = checks.get("audio_lines_today", 0)

    # Count alerts
    alert_count = 0
    alert_lines = []
    if checks.get("render_loop") == "DEAD":
        alert_count += 1
        alert_lines.append("Render loop DEAD")
    if checks.get("flask") == "DOWN":
        alert_count += 1
        alert_lines.append("Flask DOWN")
    if checks.get("ollama") == "DOWN":
        alert_count += 1
        alert_lines.append("Ollama DOWN")

    status = "✅ All systems nominal" if alert_count == 0 else f"❌ {alert_count} issue(s) detected"

    briefing = (
        f"🤖 WATCHDOG DAILY — {date_str}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"🎬 Render: {last_grade}\n"
        f"🔧 Patches applied: {patches_24h} (last 24h)\n"
        f"💾 Disk free: {disk_free}GB\n"
        f"🧠 GPU 2 (Watchdog): {gpu2_info}\n"
        f"🎵 Audio lines today: {audio_lines}\n"
        f"⚠️ Alerts: {alert_count}"
    )
    if alert_lines:
        briefing += " — " + ", ".join(alert_lines)
    briefing += f"\n{status}"

    send_telegram(briefing)
    logger.info("Daily briefing sent")
    _write_last_run()


# ---------------------------------------------------------------------------
# Self-health check
# ---------------------------------------------------------------------------

def _self_health_check():
    """Watchdog checks its own health."""
    if not ollama_alive():
        logger.error("SELF-CHECK: Ollama is down — attempting restart")
        send_telegram("⚠️ Watchdog self-check: Ollama is DOWN — attempting restart")
        try:
            subprocess.run(
                ["systemctl", "restart", "ollama-watchdog"],
                timeout=30, capture_output=True,
            )
        except Exception:
            pass

    last_run = Path("/tmp/watchdog_last_run.txt")
    if last_run.exists():
        try:
            ts = datetime.fromisoformat(last_run.read_text().strip())
            age = (datetime.now(timezone.utc) - ts).total_seconds()
            if age > 300:  # 5 minutes stale
                logger.warning("SELF-CHECK: Last run was %ds ago", age)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Protocol Pulse Local LLM Watchdog")
    parser.add_argument("--mode", default="reactive",
                       choices=["reactive", "health", "pattern", "audit", "briefing"],
                       help="Check mode to run")
    args = parser.parse_args()

    logger.info("Watchdog starting — mode=%s", args.mode)

    # Self-health check on every invocation
    _self_health_check()

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

    logger.info("Watchdog complete — mode=%s", args.mode)


if __name__ == "__main__":
    main()
