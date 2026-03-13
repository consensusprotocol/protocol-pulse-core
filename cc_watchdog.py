#!/usr/bin/env python3
"""
cc_watchdog.py — Universal CC Session Watchdog
Monitors all active CC sessions every 60s.
Detects stalls, restarts them, logs everything.
Also monitors: grade trends, TTS health, GPU utilization, render throughput.
Runs as a persistent daemon in tmux:watchdog
"""
import subprocess, time, os, json, re, urllib.request, glob
from datetime import datetime

BASE = '/home/ultron/protocol_pulse'
LOG = f'{BASE}/logs/watchdog.log'
LESSONS_FILE = f'{BASE}/PIPELINE_LESSONS.md'

import sys
sys.path.insert(0, BASE)
from utils.notify import notify, notify_critical

# Sessions to monitor: name → prompt file (for restart)
WATCHED = {
    'gpu_orchestrator': {'type': 'python',  'cmd': 'python3 dual_gpu_orchestrator.py', 'log': 'logs/orchestrator.log', 'critical': True},
    'flask_main':       {'type': 'service', 'cmd': 'bash run_flask.sh',             'critical': True},
    'video_server':     {'type': 'service', 'cmd': 'python3 video_file_server.py',  'critical': True},
}

# Stall detection: if pane output hasn't changed in N seconds, it's stalled
STALL_TIMEOUT = {
    'cc':      600,   # 10 min — CC can think for a while, but not 10 min silently
    'python':  300,   # 5 min  — render loop should be logging regularly
    'service': 120,   # 2 min  — services should respond
}

os.makedirs(f'{BASE}/logs', exist_ok=True)
pane_snapshots = {}   # session_name → (last_content, last_change_time)
restart_counts = {}   # session_name → count
MAX_RESTARTS = 3

def log(msg):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f'[{ts}] {msg}'
    print(line, flush=True)
    with open(LOG, 'a') as f:
        f.write(line + '\n')

def session_alive(name):
    return subprocess.run(f'tmux has-session -t {name} 2>/dev/null',
                         shell=True).returncode == 0

def get_pane(name):
    r = subprocess.run(f'tmux capture-pane -t {name} -p 2>/dev/null',
                      shell=True, capture_output=True, text=True)
    # Strip blank lines and ANSI codes
    lines = [re.sub(r'\x1b\[[0-9;]*m', '', l) for l in r.stdout.split('\n') if l.strip()]
    return '\n'.join(lines[-15:])  # last 15 non-empty lines

def is_stalled(name, stype):
    content = get_pane(name)
    now = time.time()
    timeout = STALL_TIMEOUT.get(stype, 300)
    
    prev_content, prev_time = pane_snapshots.get(name, (None, now))
    
    if content != prev_content:
        pane_snapshots[name] = (content, now)
        return False  # actively changing
    
    elapsed = now - prev_time
    if elapsed > timeout:
        return True, elapsed
    return False

def detect_cc_stuck(name):
    """CC-specific stall patterns"""
    content = get_pane(name)
    stuck_patterns = [
        'bypass permissions on',  # sitting at prompt, not working
        'ctrl+g to edit in Vim',  # waiting for input
        'Pasted text #1',         # got paste but didn't process it
    ]
    # If ONLY these patterns and nothing else in last 5 lines — it's stuck
    last_lines = content.split('\n')[-5:]
    last_text = ' '.join(last_lines)
    has_work = any(x in last_text for x in ['Reading', 'Writing', 'Bash', 'Creating', '✓', '⎽', 'TokenCount'])
    is_idle = any(p in last_text for p in stuck_patterns)
    return is_idle and not has_work

def restart_cc_session(name, config):
    count = restart_counts.get(name, 0) + 1
    restart_counts[name] = count
    if count > MAX_RESTARTS:
        log(f'WATCHDOG: {name} hit max restarts ({MAX_RESTARTS}) — NOT restarting. Manual intervention needed.')
        return False
    
    log(f'WATCHDOG: Restarting stalled CC session {name} (restart #{count})')
    subprocess.run(f'tmux kill-session -t {name} 2>/dev/null', shell=True)
    time.sleep(3)
    
    prompt_file = config.get('prompt')
    if prompt_file and os.path.exists(f'{BASE}/{prompt_file}'):
        subprocess.run(
            f'tmux new-session -d -s {name} "cd {BASE} && unset ANTHROPIC_API_KEY && claude --dangerously-skip-permissions"',
            shell=True
        )
        time.sleep(12)
        # Send as a proper Claude instruction, not a paste
        subprocess.run(
            f'tmux send-keys -t {name} "Execute the build task defined in {prompt_file}. Read that file first using the Read tool, then complete every step." Enter',
            shell=True
        )
        log(f'WATCHDOG: {name} restarted with prompt from {prompt_file}')
        return True
    return False

def restart_python_session(name, config):
    count = restart_counts.get(name, 0) + 1
    restart_counts[name] = count
    if count > MAX_RESTARTS:
        log(f'WATCHDOG: {name} hit max restarts — NOT restarting.')
        return False
    log(f'WATCHDOG: Restarting stalled python session {name} (restart #{count})')
    subprocess.run(f'tmux kill-session -t {name} 2>/dev/null', shell=True)
    time.sleep(3)
    cmd = config['cmd']
    log_file = config.get('log', f'logs/{name}.log')
    subprocess.run(
        f'tmux new-session -d -s {name} "cd {BASE} && {cmd} 2>&1 | tee {log_file}"',
        shell=True
    )
    log(f'WATCHDOG: {name} restarted')
    return True

def check_render_progress():
    """Special check: is the render loop making actual progress?"""
    log_file = f'{BASE}/video_pipeline_v3/logs/smart_loop_run3.log'
    if not os.path.exists(log_file):
        return 'no log yet'
    lines = open(log_file).readlines()
    # Find last grade
    grades = [l.strip() for l in lines if 'GRADE:' in l]
    iterations = [l.strip() for l in lines if 'ITERATION' in l and '/8' in l]
    last_grade = grades[-1] if grades else 'no grade yet'
    current_iter = iterations[-1] if iterations else 'iteration 1 running'
    return f'{current_iter} | {last_grade}'


def append_to_lessons(event_type, session, detail):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    line = "\n### WATCHDOG [" + ts + "] " + event_type + " - " + session + "\n" + str(detail) + "\n"
    try:
        with open(BASE + "/PIPELINE_LESSONS.md", "a") as fh:
            fh.write(line)
    except Exception as ex:
        log("LESSONS write error: " + str(ex))


def write_status_file():
    status = {
        'timestamp': datetime.now().isoformat(),
        'sessions': {},
        'render_progress': check_render_progress(),
    }
    for name in WATCHED:
        alive = session_alive(name)
        status['sessions'][name] = {
            'alive': alive,
            'restarts': restart_counts.get(name, 0),
        }
    with open(f'{BASE}/logs/watchdog_status.json', 'w') as f:
        json.dump(status, f, indent=2)


# ─── SYSTEM 5: CORRECTNESS MONITORS ──────────────────────────────────────────

def send_alert(message, critical=False):
    """Send alert via Telegram (and SMS if critical)."""
    try:
        if critical:
            notify_critical(f'[WATCHDOG] {message}')
        else:
            notify(f'[WATCHDOG] {message}')
        log(f'Alert sent: {message[:60]}')
    except Exception as e:
        log(f'Alert send failed: {e}')


def check_grade_trend():
    """Read last 3 grades. If all identical (stuck), alert."""
    grades = []
    for gpu_id in (0, 1):
        grade_file = f'{BASE}/logs/gpu{gpu_id}_grade.json'
        if os.path.exists(grade_file):
            try:
                data = json.load(open(grade_file))
                grades.append(data.get('score', 0))
            except Exception:
                pass

    # Also check the render log for recent grade entries
    for log_file in [f'{BASE}/logs/gpu0_render.log', f'{BASE}/logs/gpu1_render.log']:
        if os.path.exists(log_file):
            try:
                lines = open(log_file).readlines()
                for line in reversed(lines[-50:]):
                    m = re.search(r'Grade.*?(\d+)/100', line)
                    if m:
                        grades.append(int(m.group(1)))
                        if len(grades) >= 3:
                            break
            except Exception:
                pass

    if len(grades) >= 3:
        last3 = grades[-3:]
        if len(set(last3)) == 1:
            msg = f'GRADE STUCK: last 3 grades are all {last3[0]}/100. Pipeline may be stuck in a loop.'
            log(f'WATCHDOG: {msg}')
            append_to_lessons('GRADE-STUCK', 'orchestrator', msg)
            send_alert(msg)
            return True
    return False


def check_tts_health():
    """Fire a minimal ElevenLabs API test to verify TTS is working."""
    try:
        api_key = None
        for line in open(f'{BASE}/.env'):
            l = line.strip()
            if l.startswith('ELEVENLABS_API_KEY='):
                api_key = l.split('=', 1)[1].strip().strip("'").strip('"')
                break
        if not api_key:
            log('WATCHDOG: TTS health skip — no ELEVENLABS_API_KEY')
            return True

        # Quick voices list check (cheaper than generating audio)
        req = urllib.request.Request(
            'https://api.elevenlabs.io/v1/voices',
            headers={'xi-api-key': api_key, 'Accept': 'application/json'}
        )
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read())
        voice_count = len(data.get('voices', []))
        if voice_count > 0:
            return True
        else:
            msg = 'TTS HEALTH FAIL: ElevenLabs returned 0 voices'
            log(f'WATCHDOG: {msg}')
            append_to_lessons('TTS-HEALTH', 'tts', msg)
            return False
    except Exception as e:
        msg = f'TTS HEALTH FAIL: {e}'
        log(f'WATCHDOG: {msg}')
        append_to_lessons('TTS-HEALTH', 'tts', msg)
        return False


# Track GPU idle duration
_gpu_idle_since = {}  # gpu_id → timestamp when first seen at 0%

def check_gpu_utilization():
    """Check nvidia-smi. Alert if both GPUs at 0% for >10 minutes."""
    try:
        r = subprocess.run(
            ['nvidia-smi', '--query-gpu=index,utilization.gpu',
             '--format=csv,noheader,nounits'],
            capture_output=True, text=True, timeout=10
        )
        if r.returncode != 0:
            return

        now = time.time()
        all_idle = True
        for line in r.stdout.strip().split('\n'):
            parts = line.strip().split(',')
            if len(parts) >= 2:
                gpu_id = int(parts[0].strip())
                util = int(parts[1].strip())
                if util > 0:
                    all_idle = False
                    _gpu_idle_since.pop(gpu_id, None)
                elif gpu_id not in _gpu_idle_since:
                    _gpu_idle_since[gpu_id] = now

        if all_idle and len(_gpu_idle_since) >= 2:
            oldest_idle = min(_gpu_idle_since.values())
            idle_minutes = (now - oldest_idle) / 60
            if idle_minutes > 10:
                # Only alert if orchestrator is supposed to be running
                if session_alive('gpu_orchestrator'):
                    msg = f'GPU IDLE: Both GPUs at 0% for {idle_minutes:.0f} min while orchestrator is running'
                    log(f'WATCHDOG: {msg}')
                    append_to_lessons('GPU-IDLE', 'orchestrator', msg)
                    # Critical if idle for 2h+
                    if idle_minutes >= 120:
                        send_alert(msg, critical=True)
                    else:
                        send_alert(msg)
    except Exception as e:
        log(f'WATCHDOG: GPU check error: {e}')


# Track render throughput
_render_throughput = {'count': 0, 'window_start': time.time()}

def check_render_throughput():
    """Track renders/hour. Alert if below 1/hr while orchestrator runs."""
    global _render_throughput
    now = time.time()

    # Count renders by checking grade files' modification times
    current_count = 0
    for gpu_id in (0, 1):
        grade_file = f'{BASE}/logs/gpu{gpu_id}_grade.json'
        if os.path.exists(grade_file):
            try:
                data = json.load(open(grade_file))
                # Count if graded in last hour
                ts = data.get('timestamp', '')
                if ts:
                    grade_time = datetime.fromisoformat(ts)
                    age_s = (datetime.now() - grade_time).total_seconds()
                    if age_s < 3600:
                        current_count += 1
            except Exception:
                pass

    elapsed_hours = (now - _render_throughput['window_start']) / 3600
    if elapsed_hours >= 1.0:
        rph = current_count / max(elapsed_hours, 0.01)
        if rph < 1.0 and session_alive('gpu_orchestrator'):
            msg = f'LOW THROUGHPUT: {rph:.1f} renders/hour (expected >= 1). Check for stuck renders.'
            log(f'WATCHDOG: {msg}')
            append_to_lessons('LOW-THROUGHPUT', 'orchestrator', msg)
            send_alert(msg)
        # Reset window
        _render_throughput = {'count': 0, 'window_start': now}


def check_audit_staleness():
    """Alert if no new audit in docs/audits/ within 48 hours."""
    audit_dir = f'{BASE}/docs/audits'
    if not os.path.isdir(audit_dir):
        return
    audit_files = []
    for ext in ('*.md', '*.log'):
        audit_files.extend(glob.glob(f'{audit_dir}/**/{ext}', recursive=True))
        audit_files.extend(glob.glob(f'{audit_dir}/{ext}'))
    if not audit_files:
        msg = 'AUDIT STALE: No audit logs found in docs/audits/ at all.'
        log(f'WATCHDOG: {msg}')
        send_alert(msg)
        return
    newest = max(audit_files, key=os.path.getmtime)
    age_hours = (time.time() - os.path.getmtime(newest)) / 3600
    if age_hours > 48:
        msg = f'AUDIT STALE: newest audit is {age_hours:.0f}h old (>48h). Run cross_llm_audit.py.'
        log(f'WATCHDOG: {msg}')
        append_to_lessons('AUDIT-STALE', 'watchdog', msg)
        send_alert(msg)


def main():
    log('=' * 60)
    log('CC WATCHDOG STARTED — monitoring all active sessions')
    log('Sessions: ' + ', '.join(WATCHED.keys()))
    log('=' * 60)
    
    # Initial snapshot
    for name in WATCHED:
        if session_alive(name):
            pane_snapshots[name] = (get_pane(name), time.time())
    
    check_interval = 60  # seconds between checks
    status_interval = 300  # write status file every 5 min
    tts_interval = 600     # TTS health check every 10 min
    gpu_interval = 300     # GPU utilization check every 5 min
    audit_interval = 3600  # audit staleness check every hour
    last_status = time.time()
    last_tts_check = time.time()
    last_gpu_check = time.time()
    last_audit_check = time.time()

    while True:
        time.sleep(check_interval)
        now = time.time()

        for name, config in WATCHED.items():
            stype = config['type']

            if not session_alive(name):
                if config.get('critical'):
                    log(f'WATCHDOG: CRITICAL session {name} is DEAD')
                    if stype == 'python':
                        restart_python_session(name, config)
                    elif stype == 'cc':
                        restart_cc_session(name, config)
                continue

            # Check for stall
            stall = is_stalled(name, stype)
            if stall:
                elapsed = time.time() - pane_snapshots.get(name, (None, now))[1]
                log(f'WATCHDOG: {name} stalled for {elapsed:.0f}s')
                if stype == 'cc' and detect_cc_stuck(name):
                    log(f'WATCHDOG: CC-specific stall detected in {name} — restarting')
                    restart_cc_session(name, config)
                elif stype == 'python' and config.get('critical'):
                    restart_python_session(name, config)

            # Log a heartbeat every 5 min
            if now - last_status >= status_interval:
                content = get_pane(name)
                last_line = [l for l in content.split('\n') if l.strip()]
                last_line = last_line[-1] if last_line else '(empty)'
                log(f'HEARTBEAT {name}: {last_line[:80]}')

        if now - last_status >= status_interval:
            write_status_file()
            progress = check_render_progress()
            log(f'RENDER PROGRESS: {progress}')
            append_to_lessons('RENDER-HEARTBEAT', 'gpu_orchestrator', f'Progress: {progress}')
            # Grade trend + throughput checks every 5 min
            check_grade_trend()
            check_render_throughput()
            last_status = now

        # GPU utilization check every 5 min
        if now - last_gpu_check >= gpu_interval:
            check_gpu_utilization()
            last_gpu_check = now

        # TTS health check every 10 min
        if now - last_tts_check >= tts_interval:
            tts_ok = check_tts_health()
            if not tts_ok:
                send_alert('TTS HEALTH FAIL — ElevenLabs may be down')
            last_tts_check = now

        # Audit staleness check every hour
        if now - last_audit_check >= audit_interval:
            check_audit_staleness()
            last_audit_check = now

if __name__ == '__main__':
    main()
