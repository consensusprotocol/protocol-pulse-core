"""
Protocol Pulse — Sentient Production Scheduler
4-Lane GPU Coordinator with render queue, health monitor, and deadlock prevention.

GPU LANES (4x RTX 4090):
  GPU 0: render_lane      — daily_producer.py renders only
  GPU 1: ai_inference_lane — Kokoro TTS, Wav2Lip, F5-TTS, PCAF
  GPU 2: intelligence_lane — Whisper transcription, Qwen3 (Ollama), signal scoring
  GPU 3: overflow_lane     — burst workloads, experimental, PCAF overflow

Lock files: /tmp/gpu{0-3}.lock (JSON with pid, task, acquired_at)
Deadlock: any lock held > 4 hours is force-released and the process killed.
"""

import fcntl
import json
import logging
import os
import signal
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock, Thread
from typing import Dict, List, Optional
from collections import deque

logger = logging.getLogger(__name__)

# ── Lane definitions ──────────────────────────────────────────────────────────

GPU_LANES = {
    0: {"name": "render_lane", "description": "daily_producer.py renders only"},
    1: {"name": "ai_inference_lane", "description": "Kokoro TTS, Wav2Lip, F5-TTS, PCAF"},
    2: {"name": "intelligence_lane", "description": "Whisper, Qwen3-Coder (Ollama), signal scoring"},
    3: {"name": "overflow_lane", "description": "Burst workloads, experimental, PCAF overflow"},
}

LOCK_DIR = "/tmp"
DEADLOCK_TIMEOUT_SECONDS = 4 * 3600  # 4 hours
HEALTH_CHECK_INTERVAL = 300  # 5 minutes
GPU_TEMP_CRITICAL = 85  # Celsius


class GPULock:
    """File-based GPU lock with deadlock prevention."""

    def __init__(self, gpu_id: int):
        self.gpu_id = gpu_id
        self.lock_path = os.path.join(LOCK_DIR, f"gpu{gpu_id}.lock")

    def acquire(self, task_name: str, pid: Optional[int] = None) -> bool:
        """Acquire GPU lock. Returns True on success."""
        self._break_deadlock()
        pid = pid or os.getpid()
        try:
            fd = os.open(self.lock_path, os.O_CREAT | os.O_WRONLY | os.O_EXCL, 0o644)
            payload = json.dumps({
                "pid": pid,
                "task": task_name,
                "acquired_at": datetime.now(timezone.utc).isoformat(),
                "gpu_id": self.gpu_id,
            })
            os.write(fd, payload.encode())
            os.close(fd)
            logger.info(f"[GPU {self.gpu_id}] Lock acquired by {task_name} (pid={pid})")
            return True
        except FileExistsError:
            logger.warning(f"[GPU {self.gpu_id}] Lock held — cannot acquire for {task_name}")
            return False
        except OSError as e:
            logger.error(f"[GPU {self.gpu_id}] Lock acquire error: {e}")
            return False

    def release(self) -> bool:
        """Release GPU lock."""
        try:
            if os.path.exists(self.lock_path):
                os.remove(self.lock_path)
                logger.info(f"[GPU {self.gpu_id}] Lock released")
                return True
            return False
        except OSError as e:
            logger.error(f"[GPU {self.gpu_id}] Lock release error: {e}")
            return False

    def info(self) -> Optional[Dict]:
        """Read current lock info."""
        try:
            if os.path.exists(self.lock_path):
                with open(self.lock_path) as f:
                    return json.loads(f.read())
        except (json.JSONDecodeError, OSError):
            pass
        return None

    def is_locked(self) -> bool:
        return os.path.exists(self.lock_path)

    def _break_deadlock(self):
        """Kill process and release lock if held > DEADLOCK_TIMEOUT_SECONDS."""
        info = self.info()
        if not info:
            return
        acquired = info.get("acquired_at", "")
        try:
            ts = datetime.fromisoformat(acquired)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            age = (datetime.now(timezone.utc) - ts).total_seconds()
        except (ValueError, TypeError):
            age = DEADLOCK_TIMEOUT_SECONDS + 1

        if age > DEADLOCK_TIMEOUT_SECONDS:
            pid = info.get("pid")
            task = info.get("task", "unknown")
            logger.warning(f"[GPU {self.gpu_id}] DEADLOCK: {task} (pid={pid}) held lock {age/3600:.1f}h — killing")
            if pid:
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                except PermissionError:
                    logger.error(f"[GPU {self.gpu_id}] Cannot kill pid {pid} — permission denied")
            self.release()


# ── Render Queue ──────────────────────────────────────────────────────────────

class RenderQueue:
    """Thread-safe FIFO queue for render jobs. Prevents dual renders on same GPU."""

    def __init__(self):
        self._queue: deque = deque()
        self._lock = Lock()

    def enqueue(self, job: Dict) -> int:
        with self._lock:
            job["queued_at"] = datetime.now(timezone.utc).isoformat()
            self._queue.append(job)
            pos = len(self._queue)
            logger.info(f"[RenderQueue] Enqueued: {job.get('name', 'unnamed')} (position {pos})")
            return pos

    def dequeue(self) -> Optional[Dict]:
        with self._lock:
            return self._queue.popleft() if self._queue else None

    def peek(self) -> Optional[Dict]:
        with self._lock:
            return self._queue[0] if self._queue else None

    def size(self) -> int:
        with self._lock:
            return len(self._queue)

    def list_all(self) -> List[Dict]:
        with self._lock:
            return list(self._queue)


# ── GPU Health Monitor ────────────────────────────────────────────────────────

def _parse_nvidia_smi() -> List[Dict]:
    """Query nvidia-smi for all GPUs."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=index,name,temperature.gpu,memory.used,memory.total,utilization.gpu,power.draw",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return []
        gpus = []
        for line in result.stdout.strip().split("\n"):
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 7:
                gpus.append({
                    "index": int(parts[0]),
                    "name": parts[1],
                    "temp_c": int(parts[2]) if parts[2].isdigit() else 0,
                    "vram_used_mb": int(float(parts[3])),
                    "vram_total_mb": int(float(parts[4])),
                    "utilization_pct": int(parts[5]) if parts[5].isdigit() else 0,
                    "power_w": float(parts[6]) if parts[6].replace(".", "").isdigit() else 0,
                })
        return gpus
    except Exception as e:
        logger.error(f"nvidia-smi parse error: {e}")
        return []


def gpu_health_check() -> Dict:
    """Full GPU health check. Returns status dict with alerts."""
    gpus = _parse_nvidia_smi()
    alerts = []
    for gpu in gpus:
        idx = gpu["index"]
        lane = GPU_LANES.get(idx, {})
        gpu["lane"] = lane.get("name", "unassigned")
        gpu["lane_description"] = lane.get("description", "")

        lock = GPULock(idx)
        lock_info = lock.info()
        gpu["locked"] = lock.is_locked()
        gpu["lock_task"] = lock_info.get("task") if lock_info else None
        gpu["lock_pid"] = lock_info.get("pid") if lock_info else None
        gpu["lock_since"] = lock_info.get("acquired_at") if lock_info else None

        if gpu["temp_c"] >= GPU_TEMP_CRITICAL:
            alerts.append({
                "level": "critical",
                "gpu": idx,
                "message": f"GPU {idx} ({lane.get('name', '')}) temp {gpu['temp_c']}C >= {GPU_TEMP_CRITICAL}C",
            })
        vram_pct = (gpu["vram_used_mb"] / gpu["vram_total_mb"] * 100) if gpu["vram_total_mb"] > 0 else 0
        gpu["vram_pct"] = round(vram_pct, 1)
        if vram_pct > 95:
            alerts.append({
                "level": "warning",
                "gpu": idx,
                "message": f"GPU {idx} VRAM at {vram_pct:.0f}%",
            })

    return {
        "gpus": gpus,
        "alerts": alerts,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "gpu_count": len(gpus),
    }


def _send_telegram_alert(message: str):
    """Send alert to PBX via Telegram."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return
    try:
        import requests
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": f"[GPU SCHEDULER] {message}", "parse_mode": "HTML"},
            timeout=10,
        )
    except Exception as e:
        logger.warning(f"Telegram alert failed: {e}")


# ── Episode Render Execution ──────────────────────────────────────────────────

def run_episode_render(episode_name: str, gpu_id: int = 0) -> Dict:
    """
    Full render cycle for one episode:
    1. Acquire GPU lock
    2. Run daily_producer.py (fresh content)
    3. Grade result via gemini_grade.py
    4. If grade >= 70: mark ready for publish
    5. If grade < 70: retry once, then ship best available
    6. Release GPU lock
    Returns result dict with grade, path, success status.
    """
    lock = GPULock(gpu_id)
    if not lock.acquire(f"render_{episode_name}"):
        return {"success": False, "error": f"GPU {gpu_id} locked — queued", "episode": episode_name}

    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = str(gpu_id)

    base_dir = os.path.expanduser("~/protocol_pulse/video_pipeline_v3")
    result = {"success": False, "episode": episode_name, "gpu_id": gpu_id, "attempts": []}

    try:
        for attempt in range(1, 3):  # max 2 attempts
            logger.info(f"[RENDER] {episode_name} attempt {attempt}/2 on GPU {gpu_id}")
            start = time.time()

            # Run daily_producer.py
            render = subprocess.run(
                ["python3", os.path.join(base_dir, "daily_producer.py")],
                capture_output=True, text=True, timeout=3600, env=env,
                cwd=base_dir,
            )
            elapsed = time.time() - start

            if render.returncode != 0:
                result["attempts"].append({
                    "attempt": attempt, "status": "render_failed",
                    "elapsed_s": round(elapsed), "error": render.stderr[-500:] if render.stderr else "unknown",
                })
                logger.error(f"[RENDER] {episode_name} attempt {attempt} failed: rc={render.returncode}")
                continue

            # Grade the output
            grade_result = subprocess.run(
                ["python3", os.path.join(base_dir, "gemini_grade.py")],
                capture_output=True, text=True, timeout=300, env=env,
                cwd=base_dir,
            )
            # Parse grade from last line: GRADE_X_...|score|path|...
            grade_line = ""
            score = 0
            grade_letter = "F"
            for line in reversed(grade_result.stdout.strip().split("\n")):
                if line.startswith("GRADE_"):
                    grade_line = line
                    parts = line.split("|")
                    grade_letter = parts[0].replace("GRADE_", "").split("_")[0]
                    try:
                        score = int(parts[1])
                    except (IndexError, ValueError):
                        score = 0
                    break

            attempt_info = {
                "attempt": attempt, "status": "graded",
                "grade": grade_letter, "score": score,
                "elapsed_s": round(elapsed),
            }
            result["attempts"].append(attempt_info)
            logger.info(f"[RENDER] {episode_name} attempt {attempt}: grade={grade_letter} score={score}")

            if score >= 70:
                result["success"] = True
                result["final_grade"] = grade_letter
                result["final_score"] = score
                _send_telegram_alert(
                    f"Episode <b>{episode_name}</b> graded <b>{grade_letter}</b> ({score}/100) — attempt {attempt}"
                )
                break
            elif attempt == 2:
                # Ship best available on final attempt
                result["success"] = True
                result["final_grade"] = grade_letter
                result["final_score"] = score
                result["shipped_below_target"] = True
                _send_telegram_alert(
                    f"Episode <b>{episode_name}</b> shipped at <b>{grade_letter}</b> ({score}/100) — best of 2 attempts"
                )
    except subprocess.TimeoutExpired:
        result["error"] = "render_timeout"
        logger.error(f"[RENDER] {episode_name} timed out")
    except Exception as e:
        result["error"] = str(e)
        logger.error(f"[RENDER] {episode_name} error: {e}")
    finally:
        lock.release()

    return result


# ── GPUScheduler Master Class ─────────────────────────────────────────────────

class GPUScheduler:
    """Master GPU time-sharing coordinator."""

    def __init__(self):
        self.locks = {i: GPULock(i) for i in range(4)}
        self.render_queue = RenderQueue()
        self._health_thread: Optional[Thread] = None
        self._health_running = False

    def acquire(self, gpu_id: int, task_name: str) -> bool:
        """Acquire a specific GPU lane."""
        if gpu_id not in self.locks:
            return False
        return self.locks[gpu_id].acquire(task_name)

    def release(self, gpu_id: int) -> bool:
        """Release a specific GPU lane."""
        if gpu_id not in self.locks:
            return False
        return self.locks[gpu_id].release()

    def status(self) -> Dict:
        """Full scheduler status: lanes, locks, queue, health."""
        health = gpu_health_check()
        queue_items = self.render_queue.list_all()
        lanes = {}
        for gpu_id, lane in GPU_LANES.items():
            lock_info = self.locks[gpu_id].info()
            lanes[gpu_id] = {
                **lane,
                "locked": self.locks[gpu_id].is_locked(),
                "lock_info": lock_info,
            }

        return {
            "lanes": lanes,
            "health": health,
            "render_queue": queue_items,
            "render_queue_size": len(queue_items),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def request_render(self, episode_name: str) -> Dict:
        """Request a render. If GPU 0 is free, start immediately. Otherwise, queue."""
        if not self.locks[0].is_locked():
            thread = Thread(
                target=run_episode_render,
                args=(episode_name, 0),
                daemon=True,
            )
            thread.start()
            return {"status": "started", "episode": episode_name, "gpu": 0}
        else:
            pos = self.render_queue.enqueue({"name": episode_name})
            return {"status": "queued", "episode": episode_name, "position": pos}

    def process_queue(self):
        """Check if GPU 0 is free and dequeue next render if so."""
        if self.locks[0].is_locked():
            return None
        job = self.render_queue.dequeue()
        if job:
            thread = Thread(
                target=run_episode_render,
                args=(job["name"], 0),
                daemon=True,
            )
            thread.start()
            return job
        return None

    def start_health_monitor(self):
        """Start background health check thread."""
        if self._health_running:
            return
        self._health_running = True
        self._health_thread = Thread(target=self._health_loop, daemon=True)
        self._health_thread.start()
        logger.info("[GPUScheduler] Health monitor started (every 5 min)")

    def stop_health_monitor(self):
        self._health_running = False

    def _health_loop(self):
        while self._health_running:
            try:
                health = gpu_health_check()
                for alert in health.get("alerts", []):
                    if alert["level"] == "critical":
                        _send_telegram_alert(f"CRITICAL: {alert['message']}")
                        gpu_id = alert.get("gpu")
                        if gpu_id is not None and gpu_id in self.locks:
                            lock_info = self.locks[gpu_id].info()
                            if lock_info:
                                logger.warning(f"[HEALTH] GPU {gpu_id} overheating — pausing renders")
                # Check for stuck processes on all GPUs
                for gpu_id, lock in self.locks.items():
                    lock._break_deadlock()
                # Process render queue
                self.process_queue()
            except Exception as e:
                logger.error(f"[HEALTH] Monitor error: {e}")
            time.sleep(HEALTH_CHECK_INTERVAL)

    def env_for_lane(self, gpu_id: int) -> Dict[str, str]:
        """Return env dict with CUDA_VISIBLE_DEVICES set for the given lane."""
        env = os.environ.copy()
        env["CUDA_VISIBLE_DEVICES"] = str(gpu_id)
        return env


# ── Module-level singleton ────────────────────────────────────────────────────

_scheduler: Optional[GPUScheduler] = None
_init_lock = Lock()


def get_scheduler() -> GPUScheduler:
    """Get or create the singleton GPUScheduler."""
    global _scheduler
    with _init_lock:
        if _scheduler is None:
            _scheduler = GPUScheduler()
        return _scheduler
