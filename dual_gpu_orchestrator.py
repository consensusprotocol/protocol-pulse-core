#!/usr/bin/env python3
"""
DUAL-GPU CONTINUOUS RENDER ORCHESTRATOR
========================================
Replaces smart_render_loop.py as the top-level runner.

GPU 0 ("stable"):      runs render-stable branch code.  CUDA_VISIBLE_DEVICES=0
GPU 1 ("experimental"): runs main branch code.           CUDA_VISIBLE_DEVICES=1

Both run simultaneously. Each GPU restarts immediately after finishing.
If GPU 1 beats GPU 0, promote main → render-stable.

Launch:
  tmux new-session -d -s gpu_orchestrator \
    "cd ~/protocol_pulse && python3 dual_gpu_orchestrator.py 2>&1 | tee logs/orchestrator.log"
"""
import os
import sys
import json
import glob
import time
import signal
import shutil
import subprocess
import threading
import re
from datetime import datetime

sys.path.insert(0, '/home/ultron/protocol_pulse')
from utils.notify import notify, notify_critical

BASE = '/home/ultron/protocol_pulse'
PIPELINE = f'{BASE}/video_pipeline_v3'
LESSONS_FILE = f'{BASE}/PIPELINE_LESSONS.md'
BEST_GRADE_FILE = f'{BASE}/logs/best_grade.json'

os.makedirs(f'{BASE}/logs', exist_ok=True)
os.makedirs(f'{PIPELINE}/output/gpu0', exist_ok=True)
os.makedirs(f'{PIPELINE}/output/gpu1', exist_ok=True)

# ─── LOGGING ──────────────────────────────────────────────────────────────────

def log(msg, gpu_id=None):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    prefix = f"[GPU{gpu_id}]" if gpu_id is not None else "[ORCH]"
    line = f"[{ts}] {prefix} {msg}"
    print(line, flush=True)
    # Also write to per-GPU or orchestrator log
    if gpu_id is not None:
        log_path = f'{BASE}/logs/gpu{gpu_id}_render.log'
    else:
        log_path = f'{BASE}/logs/orchestrator.log'
    try:
        with open(log_path, 'a') as f:
            f.write(line + '\n')
    except Exception:
        pass


def load_env():
    """Load .env file into a dict merged with current env."""
    env = os.environ.copy()
    try:
        with open(f'{BASE}/.env') as f:
            for line in f:
                l = line.strip()
                if l and not l.startswith('#') and '=' in l:
                    k, _, v = l.partition('=')
                    env[k.strip()] = v.strip().strip("'").strip('"')
    except Exception:
        pass
    return env


# ─── SYSTEM 4: AUDIT-OR-DIE GATE ─────────────────────────────────────────────

def require_audit_before_change(changed_files):
    """Block code changes without a passing audit log."""
    pipeline_files = [f for f in changed_files
                      if 'video_pipeline_v3' in f or 'smart_render' in f]
    if not pipeline_files:
        return True  # non-pipeline changes are fine

    audit_dir = f'{BASE}/docs/audits'
    audit_logs = []
    for ext in ('*.md', '*.log'):
        audit_logs.extend(glob.glob(f'{audit_dir}/**/{ext}', recursive=True))
        audit_logs.extend(glob.glob(f'{audit_dir}/{ext}'))

    if not audit_logs:
        msg = ("AUDIT REQUIRED: no audit logs found in docs/audits/. "
               "Run: python3 utils/cross_llm_audit.py --feature video-audio-fix")
        notify_critical(f"🚫 AUDIT GATE BLOCKED: {msg}")
        raise RuntimeError(msg)

    newest_audit = max(audit_logs, key=os.path.getmtime)
    audit_age_hours = (time.time() - os.path.getmtime(newest_audit)) / 3600
    if audit_age_hours > 24:
        msg = (f"AUDIT STALE: newest audit is {audit_age_hours:.1f}h old. "
               "Re-run: python3 utils/cross_llm_audit.py --feature video-audio-fix")
        notify_critical(f"🚫 AUDIT GATE BLOCKED: {msg}")
        raise RuntimeError(msg)

    log(f"Audit gate passed: {os.path.basename(newest_audit)} is {audit_age_hours:.1f}h old")
    return True


# ─── GRADING (extracted from gemini_grade.py) ────────────────────────────────

def grade_video(video_path, gpu_id):
    """Run gemini_grade.py against a specific video. Returns (grade, score)."""
    log(f"Grading: {video_path}", gpu_id)
    env = load_env()
    env['CUDA_VISIBLE_DEVICES'] = str(gpu_id)

    try:
        r = subprocess.run(
            ['python3', 'gemini_grade.py'],
            capture_output=True, text=True, timeout=300,
            cwd=PIPELINE, env=env
        )
        output = r.stdout + r.stderr

        # Parse GRADE_X_PASS|score or GRADE_X_FAIL|score
        m = re.search(r'GRADE_([A-F])_(PASS|FAIL)\|(\d+)', output)
        if m:
            grade, _, score = m.group(1), m.group(2), int(m.group(3))
            log(f"Grade: {grade} ({score}/100)", gpu_id)
            return grade, score

        # Fallback: Grade X ... N/100
        m = re.search(r'Grade\s+([A-F]).*?(\d+)/100', output)
        if m:
            grade, score = m.group(1), int(m.group(2))
            log(f"Grade (fallback parse): {grade} ({score}/100)", gpu_id)
            return grade, score

        log(f"Grade parse failed. Output tail: {output[-300:]}", gpu_id)
        return 'F', 0
    except subprocess.TimeoutExpired:
        log("Grading timed out (300s)", gpu_id)
        return 'F', 0
    except Exception as e:
        log(f"Grading error: {e}", gpu_id)
        return 'F', 0


def save_grade(gpu_id, grade, score, video_path):
    """Save grade to per-GPU JSON file."""
    data = {
        'grade': grade,
        'score': score,
        'video': video_path,
        'timestamp': datetime.now().isoformat(),
    }
    path = f'{BASE}/logs/gpu{gpu_id}_grade.json'
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
    return data


def get_gpu_grade(gpu_id):
    """Read the current grade for a GPU."""
    path = f'{BASE}/logs/gpu{gpu_id}_grade.json'
    if os.path.exists(path):
        try:
            return json.load(open(path))
        except Exception:
            pass
    return {'score': 0, 'grade': 'F'}


THROUGHPUT_FILE = f'{BASE}/logs/throughput.json'

def update_throughput():
    """Write throughput stats to logs/throughput.json for GitHub Actions heartbeat."""
    try:
        with render_stats_lock:
            now = time.time()
            data = {
                'last_render_epoch': now,
                'last_render_iso': datetime.now().isoformat(),
                'renders_gpu0': render_stats[0]['count'],
                'renders_gpu1': render_stats[1]['count'],
            }
            for gid in (0, 1):
                s = render_stats[gid]
                elapsed_h = (now - s['start_time']) / 3600 if s['start_time'] else 0
                data[f'renders_per_hour_gpu{gid}'] = round(s['count'] / max(elapsed_h, 0.01), 2)
                data[f'last_grade_gpu{gid}'] = s.get('last_grade', 'N/A')
                data[f'last_score_gpu{gid}'] = s.get('last_score', 0)

        with open(THROUGHPUT_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        log(f"Throughput write error: {e}")


# ─── RENDER LOGIC ────────────────────────────────────────────────────────────

def find_latest_video(output_subdir=None):
    """Find the most recent pulse_check MP4."""
    search_base = PIPELINE
    if output_subdir:
        search_base = f'{PIPELINE}/output/{output_subdir}'

    candidates = []
    for root, dirs, files in os.walk(search_base):
        for f in files:
            if (f.endswith('.mp4') and 'pulse_check' in f
                    and not any(x in f for x in ['music_mixed', 'concat_raw', '.norm', 'whoosh', 'placeholder'])):
                full = os.path.join(root, f)
                candidates.append((os.path.getmtime(full), full))

    # Also check the date-based output dirs
    today = datetime.now().strftime('%Y-%m-%d')
    for pat in [f'output/{today}/*.mp4', 'output/*.mp4']:
        for f in glob.glob(f'{PIPELINE}/{pat}'):
            if (f.endswith('.mp4') and 'pulse_check' in f
                    and not any(x in f for x in ['music_mixed', 'concat_raw', '.norm', 'whoosh', 'placeholder'])):
                candidates.append((os.path.getmtime(f), f))

    candidates.sort(reverse=True)
    return candidates[0][1] if candidates else None


def kill_stale_daemons():
    """Kill stale channel_daemon.py processes."""
    try:
        subprocess.run(['pkill', '-f', 'channel_daemon.py'],
                       capture_output=True, timeout=10)
    except Exception:
        pass


def wipe_tts_cache():
    """Clear TTS cache between renders."""
    cache_dir = f'{PIPELINE}/tts_cache'
    shutil.rmtree(cache_dir, ignore_errors=True)
    os.makedirs(cache_dir, exist_ok=True)


def run_render(gpu_id, branch=None):
    """Run a single render on the specified GPU. Returns video path or None."""
    log(f"Starting render (branch={branch or 'current'})", gpu_id)

    kill_stale_daemons()
    wipe_tts_cache()

    env = load_env()
    env['CUDA_VISIBLE_DEVICES'] = str(gpu_id)
    env['GPU_ID'] = str(gpu_id)
    env['OUTPUT_SUBDIR'] = f'gpu{gpu_id}'

    # If branch specified, checkout in a temporary worktree
    worktree_dir = None
    cwd = PIPELINE

    if branch:
        worktree_dir = f'/tmp/gpu{gpu_id}_render_worktree'
        # Clean up any existing worktree
        try:
            subprocess.run(
                ['git', 'worktree', 'remove', '--force', worktree_dir],
                capture_output=True, cwd=BASE, timeout=30
            )
        except Exception:
            pass
        shutil.rmtree(worktree_dir, ignore_errors=True)

        # Check if branch exists
        branch_exists = subprocess.run(
            ['git', 'rev-parse', '--verify', branch],
            capture_output=True, cwd=BASE
        ).returncode == 0

        if branch_exists:
            try:
                r = subprocess.run(
                    ['git', 'worktree', 'add', worktree_dir, branch],
                    capture_output=True, text=True, cwd=BASE, timeout=60
                )
                if r.returncode == 0:
                    cwd = f'{worktree_dir}/video_pipeline_v3'
                    # Symlink .env so worktree has API keys
                    wt_env = f'{worktree_dir}/.env'
                    if not os.path.exists(wt_env):
                        try:
                            os.symlink('/home/ultron/protocol_pulse/.env', wt_env)
                        except Exception:
                            import shutil as _shutil
                            _shutil.copy('/home/ultron/protocol_pulse/.env', wt_env)
                    log(f"Using worktree at {worktree_dir} (branch {branch})", gpu_id)
                else:
                    log(f"Worktree creation failed: {r.stderr[:200]}. Using main.", gpu_id)
                    worktree_dir = None
                    cwd = PIPELINE
            except Exception as e:
                log(f"Worktree error: {e}. Using main.", gpu_id)
                worktree_dir = None
                cwd = PIPELINE
        else:
            log(f"Branch {branch} doesn't exist yet. Using main.", gpu_id)
            worktree_dir = None
            cwd = PIPELINE

    render_log = f'{BASE}/logs/gpu{gpu_id}_render.log'
    start_time = time.time()

    try:
        r = subprocess.run(
            ['python3', 'daily_producer.py', '--skip-scan'],
            capture_output=True, text=True, timeout=7200,
            cwd=cwd, env=env
        )
        elapsed = time.time() - start_time
        with open(render_log, 'w') as f:
            f.write(r.stdout + r.stderr)
        log(f"Render done in {elapsed:.0f}s, exit={r.returncode}", gpu_id)
    except subprocess.TimeoutExpired:
        log("Render TIMED OUT (7200s)", gpu_id)
        return None
    except Exception as e:
        log(f"Render CRASHED: {e}", gpu_id)
        return None
    finally:
        # Clean up worktree
        if worktree_dir and os.path.exists(worktree_dir):
            try:
                subprocess.run(
                    ['git', 'worktree', 'remove', '--force', worktree_dir],
                    capture_output=True, cwd=BASE, timeout=30
                )
            except Exception:
                pass

    video = find_latest_video()
    if video:
        log(f"Output: {video} ({os.path.getsize(video) // 1048576}MB)", gpu_id)
    else:
        log("No output video found", gpu_id)
    return video


# ─── PROMOTION LOGIC ─────────────────────────────────────────────────────────

def try_promote(new_score, gpu_id):
    """Call promote_to_stable.sh if the experimental GPU beat stable."""
    log(f"Attempting promotion with score {new_score}", gpu_id)
    try:
        r = subprocess.run(
            ['bash', 'promote_to_stable.sh', str(new_score)],
            capture_output=True, text=True, timeout=120, cwd=BASE
        )
        output = r.stdout + r.stderr
        log(f"Promotion result: {output.strip()}", gpu_id)

        if r.returncode == 0:
            # Log to PIPELINE_LESSONS.md
            ts = datetime.now().strftime('%Y-%m-%d %H:%M')
            with open(LESSONS_FILE, 'a') as f:
                f.write(f"\n### ORCHESTRATOR [{ts}] GPU1 PROMOTED to render-stable\n")
                f.write(f"Score: {new_score}/100 — experimental beat stable.\n\n---\n")
            return True
    except Exception as e:
        log(f"Promotion error: {e}", gpu_id)
    return False


# ─── GPU WORKER ──────────────────────────────────────────────────────────────

# Track render counts and grades for throughput monitoring
render_stats = {
    0: {'count': 0, 'last_grade': None, 'last_score': 0, 'start_time': None},
    1: {'count': 0, 'last_grade': None, 'last_score': 0, 'start_time': None},
}
render_stats_lock = threading.Lock()


def gpu_worker(gpu_id, branch=None):
    """Continuous render loop for one GPU. Never returns unless killed."""
    role = "STABLE" if gpu_id == 0 else "EXPERIMENTAL"
    log(f"Worker started — role={role}, branch={branch or 'main'}", gpu_id)

    with render_stats_lock:
        render_stats[gpu_id]['start_time'] = time.time()

    iteration = 0
    consecutive_failures = 0

    while True:
        iteration += 1
        log(f"--- Iteration {iteration} ---", gpu_id)

        try:
            # Check audit gate for experimental GPU code changes
            if gpu_id == 1:
                try:
                    # Get list of changed files vs render-stable
                    r = subprocess.run(
                        ['git', 'diff', '--name-only', 'render-stable..main'],
                        capture_output=True, text=True, cwd=BASE, timeout=10
                    )
                    if r.returncode == 0 and r.stdout.strip():
                        changed = r.stdout.strip().split('\n')
                        require_audit_before_change(changed)
                except RuntimeError as e:
                    log(f"AUDIT GATE BLOCKED: {e}", gpu_id)
                    log("Sleeping 5 min before retry...", gpu_id)
                    time.sleep(300)
                    continue
                except Exception:
                    pass  # git diff failed (no render-stable branch yet) — continue

            # Render
            video = run_render(gpu_id, branch=branch)

            if not video:
                consecutive_failures += 1
                log(f"No video output (failure #{consecutive_failures})", gpu_id)
                if consecutive_failures >= 3:
                    log("3 consecutive failures — sleeping 120s", gpu_id)
                    time.sleep(120)
                    consecutive_failures = 0
                else:
                    time.sleep(30)
                continue

            consecutive_failures = 0

            # Grade
            grade, score = grade_video(video, gpu_id)
            save_grade(gpu_id, grade, score, video)

            with render_stats_lock:
                render_stats[gpu_id]['count'] += 1
                render_stats[gpu_id]['last_grade'] = grade
                render_stats[gpu_id]['last_score'] = score

            # Update throughput.json after every render
            update_throughput()

            # Promotion check: GPU 1 (experimental) tries to beat GPU 0 (stable)
            if gpu_id == 1 and score > 0:
                gpu0_data = get_gpu_grade(0)
                gpu0_score = gpu0_data.get('score', 0)
                if score > gpu0_score:
                    log(f"GPU1 ({score}) > GPU0 ({gpu0_score}) — attempting promotion", gpu_id)
                    try_promote(score, gpu_id)
                else:
                    log(f"GPU1 ({score}) <= GPU0 ({gpu0_score}) — no promotion", gpu_id)

        except Exception as e:
            error_str = str(e)
            log(f"WORKER ERROR: {error_str}", gpu_id)

            # OOM detection
            if 'out of memory' in error_str.lower() or 'OOM' in error_str:
                log("OOM detected — waiting 30s for GPU memory to clear", gpu_id)
                notify(f"⚠️ GPU{gpu_id} OOM — waiting 30s before restart")
                time.sleep(30)
            else:
                time.sleep(10)

        # Brief pause between iterations to avoid thrashing
        log(f"Iteration {iteration} complete. Restarting immediately.", gpu_id)


# ─── MAIN ORCHESTRATOR ───────────────────────────────────────────────────────

def ensure_render_stable_branch():
    """Create render-stable branch if it doesn't exist."""
    r = subprocess.run(
        ['git', 'rev-parse', '--verify', 'render-stable'],
        capture_output=True, cwd=BASE
    )
    if r.returncode != 0:
        log("Creating render-stable branch from current main")
        subprocess.run(
            ['git', 'branch', 'render-stable'],
            capture_output=True, cwd=BASE
        )
        log("render-stable branch created")
    else:
        log("render-stable branch exists")


def ensure_best_grade_file():
    """Create best_grade.json if missing."""
    if not os.path.exists(BEST_GRADE_FILE):
        os.makedirs(os.path.dirname(BEST_GRADE_FILE), exist_ok=True)
        with open(BEST_GRADE_FILE, 'w') as f:
            json.dump({'score': 0, 'promoted_at': 'never'}, f, indent=2)
        log("Created best_grade.json with score=0")


def main():
    log("=" * 70)
    log("DUAL-GPU CONTINUOUS RENDER ORCHESTRATOR — STARTING")
    log(f"GPU 0: STABLE (render-stable branch)")
    log(f"GPU 1: EXPERIMENTAL (main branch)")
    log(f"Both GPUs run FOREVER until killed.")
    log("=" * 70)

    # Pre-flight
    ensure_render_stable_branch()
    ensure_best_grade_file()
    kill_stale_daemons()

    # Start GPU workers in threads
    gpu0_thread = threading.Thread(
        target=gpu_worker, args=(0, 'render-stable'),
        name='gpu0-stable', daemon=True
    )
    gpu1_thread = threading.Thread(
        target=gpu_worker, args=(1, None),  # None = use main/current
        name='gpu1-experimental', daemon=True
    )

    gpu0_thread.start()
    # Stagger start by 30s to avoid resource contention
    time.sleep(30)
    gpu1_thread.start()

    log("Both GPU workers launched. Monitoring...")

    notify("🚀 Dual-GPU Orchestrator STARTED — GPU0 stable, GPU1 experimental")

    # Main thread: monitor and report
    try:
        while True:
            time.sleep(300)  # Report every 5 minutes
            with render_stats_lock:
                for gid in (0, 1):
                    s = render_stats[gid]
                    elapsed_h = (time.time() - s['start_time']) / 3600 if s['start_time'] else 0
                    rph = s['count'] / max(elapsed_h, 0.01)
                    log(f"GPU{gid}: {s['count']} renders, {rph:.1f}/hr, "
                        f"last={s['last_grade']}({s['last_score']})")

            # Update throughput.json
            update_throughput()

            # Check threads are alive
            if not gpu0_thread.is_alive():
                log("GPU0 thread DIED — restarting")
                notify("⚠️ GPU0 worker thread died — restarting")
                gpu0_thread = threading.Thread(
                    target=gpu_worker, args=(0, 'render-stable'),
                    name='gpu0-stable', daemon=True
                )
                gpu0_thread.start()

            if not gpu1_thread.is_alive():
                log("GPU1 thread DIED — restarting")
                notify("⚠️ GPU1 worker thread died — restarting")
                gpu1_thread = threading.Thread(
                    target=gpu_worker, args=(1, None),
                    name='gpu1-experimental', daemon=True
                )
                gpu1_thread.start()

            # Both dead at same time = critical
            if not gpu0_thread.is_alive() and not gpu1_thread.is_alive():
                notify_critical("🚨 BOTH GPU workers dead — orchestrator restarting both")

    except KeyboardInterrupt:
        log("Keyboard interrupt — shutting down gracefully")
        notify("⏹️ Orchestrator stopped (keyboard interrupt)")
        sys.exit(0)
    except Exception as e:
        log(f"ORCHESTRATOR CRASH: {e} — restarting main loop")
        notify_critical(f"🚨 Orchestrator crashed: {e}")
        # Self-restart
        time.sleep(5)
        main()


if __name__ == '__main__':
    main()
