#!/usr/bin/env python3
"""
autonomous_render_loop.py - Perpetual self-healing render loop.
Target: 5 consecutive Grade A (>=90) renders. No time limit.
"""
import subprocess, time, os, sys, json, re, glob, signal
from datetime import datetime

BASE         = '/home/ultron/protocol_pulse'
PIPELINE     = f'{BASE}/video_pipeline_v3'
LOGS         = f'{BASE}/logs'
LOG_FILE     = f'{LOGS}/autonomous_loop.log'
GRADE_LOG    = f'{LOGS}/grade_report.log'
BEST_GRADE   = f'{LOGS}/best_grade.json'
OUTPUT_BASE  = f'{PIPELINE}/output'
GEMINI_GRADE_FILE   = f'{PIPELINE}/logs/v6_gemini_grade.json'
RENDER_TIMEOUT      = 1200
CC_REPAIR_TIMEOUT   = 600
TARGET_A            = 5
os.makedirs(LOGS, exist_ok=True)

# ── env / telegram ────────────────────────────────────────────────────────────
def load_env():
    env = {}
    try:
        for line in open(f'{BASE}/.env'):
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                k, v = line.split('=', 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    except Exception:
        pass
    return env

ENV = load_env()

def log(msg):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f'[{ts}] {msg}'
    print(line, flush=True)
    with open(LOG_FILE, 'a') as f:
        f.write(line + '\n')

def telegram(msg):
    token = ENV.get('TELEGRAM_BOT_TOKEN', '')
    chat  = ENV.get('TELEGRAM_CHAT_ID', '')
    if not token or not chat:
        log(f'[TG SKIP] {msg}')
        return
    try:
        import urllib.request
        payload = json.dumps({'chat_id': chat, 'text': f'LOOP: {msg}'}).encode()
        req = urllib.request.Request(
            f'https://api.telegram.org/bot{token}/sendMessage',
            data=payload, headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        log(f'TG fail: {e}')

# ── known fixes ───────────────────────────────────────────────────────────────
def _r(p):
    return open(p).read()
def _w(p, c):
    open(p, 'w').write(c)

def fix_voice_modes(_):
    p = f'{PIPELINE}/tts_engine.py'; c = _r(p)
    if 'VOICE_MODES = {' in c: return True
    anchor = 'SILENCE_GAP = 0.3  # seconds between speakers'
    if anchor not in c: return False
    _w(p, c.replace(anchor, anchor + '\n\nVOICE_MODES = {\n'
        '    "cold_open":       {"stability": 0.45, "similarity_boost": 0.80, "style": 0.18},\n'
        '    "setup":           {"stability": 0.55, "similarity_boost": 0.80, "style": 0.15},\n'
        '    "react":           {"stability": 0.55, "similarity_boost": 0.80, "style": 0.15},\n'
        '    "bridge":          {"stability": 0.52, "similarity_boost": 0.80, "style": 0.15},\n'
        '    "social_segment":  {"stability": 0.50, "similarity_boost": 0.78, "style": 0.18},\n'
        '    "wrap":            {"stability": 0.50, "similarity_boost": 0.78, "style": 0.20},\n'
        '}', 1))
    return True

def fix_silence_gap(_):
    p = f'{PIPELINE}/tts_engine.py'; c = _r(p)
    if 'SILENCE_GAP' in c: return True
    anchor = 'MAX_CHUNK_CHARS = 500'
    if anchor not in c: return False
    _w(p, c.replace(anchor, anchor + '\nSILENCE_GAP = 0.3  # seconds between speakers', 1))
    return True

def fix_max_chunk(_):
    p = f'{PIPELINE}/tts_engine.py'; c = _r(p)
    if 'MAX_CHUNK_CHARS' in c: return True
    anchor = '_KEY_CACHE: dict = {}'
    if anchor not in c: return False
    _w(p, c.replace(anchor, 'MAX_CHUNK_CHARS = 500\n' + anchor, 1))
    return True

def fix_key_cache(_):
    p = f'{PIPELINE}/tts_engine.py'; c = _r(p)
    n = c.count('_KEY_CACHE: dict = {}')
    if n <= 1: return True
    idx = c.index('_KEY_CACHE: dict = {}')
    rest = c[idx + len('_KEY_CACHE: dict = {}'):].replace('_KEY_CACHE: dict = {}', '', n - 1)
    _w(p, c[:idx] + '_KEY_CACHE: dict = {}' + rest)
    return True

def fix_module(err):
    m = re.search(r"No module named '([^']+)'", err)
    if not m: return False
    mod = m.group(1).split('.')[0]
    return subprocess.run([sys.executable, '-m', 'pip', 'install', mod,
                           '--break-system-packages', '-q'],
                          capture_output=True).returncode == 0

def fix_missing_dir(err):
    m = re.search(r"No such file or directory: '([^']+)'", err)
    if not m: return False
    parent = os.path.dirname(m.group(1))
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)
        return True
    return False

KNOWN_FIXES = [
    (re.compile(r"NameError: name 'VOICE_MODES'"),     fix_voice_modes,  'Inject VOICE_MODES'),
    (re.compile(r"NameError: name 'SILENCE_GAP'"),     fix_silence_gap,  'Inject SILENCE_GAP'),
    (re.compile(r"NameError: name 'MAX_CHUNK_CHARS'"), fix_max_chunk,    'Inject MAX_CHUNK_CHARS'),
    (re.compile(r"NameError: name '_KEY_CACHE'"),      fix_key_cache,    'Dedup _KEY_CACHE'),
    (re.compile(r"No module named '"),                 fix_module,       'pip install'),
    (re.compile(r"No such file or directory"),         fix_missing_dir,  'mkdir'),
]

def diagnose_and_fix(error_output):
    for pattern, fn, desc in KNOWN_FIXES:
        if pattern.search(error_output):
            log(f'KNOWN FIX: {desc}')
            try:
                if fn(error_output):
                    log(f'Fix applied: {desc}')
                    return True, desc
                log(f'Fix anchor missing: {desc}')
            except Exception as e:
                log(f'Fix exception: {e}')
    return False, None

# ── CC auto-repair ────────────────────────────────────────────────────────────
def cc_auto_repair(error_output, iteration):
    session = f'cc_fix_{iteration}'
    log(f'CC repair: {session}')
    telegram(f'Error iter {iteration} - CC auto-repair spawned')

    # Extract Gemini critical failure lines for the CC prompt
    critical_lines = []
    for line in error_output.strip().split('\n'):
        if any(kw in line for kw in ['!!', 'CRITICAL', 'FAIL', 'critical_failure', 'GRADE_']):
            critical_lines.append(line.strip())
    gemini_failures = '\n'.join(critical_lines[:30]) if critical_lines else ''

    broken = 'tts_engine.py'
    matches = [f for f in re.findall(r'File "([^"]+\.py)"', error_output) if 'video_pipeline_v3' in f]
    if matches:
        broken = os.path.basename(matches[-1])

    snippet = error_output.strip().split('\n')
    idx = None
    for i, l in enumerate(snippet):
        if any(x in l for x in ['Traceback', 'Error:', 'NameError']):
            idx = i
    err_snippet = '\n'.join(snippet[max(0, (idx or 0) - 2):(idx or 0) + 12]) if idx is not None else '\n'.join(snippet[-12:])

    laws = ''
    try:
        laws = open(f'{BASE}/PIPELINE_LAWS.md').read()[:2000]
    except Exception:
        pass

    prompt = (
        f'AUTONOMOUS REPAIR - do not ask questions, fix and commit.\n\n'
        f'ERROR (iter {iteration}):\n{err_snippet}\n\n'
        + (f'GEMINI QUALITY FAILURES:\n{gemini_failures}\n\n' if gemini_failures else '')
        + f'BROKEN FILE: video_pipeline_v3/{broken}\n\n'
        f'LAWS:\n{laws}\n\n'
        f'STEPS:\n'
        f'1. Read traceback, open video_pipeline_v3/{broken}, find root cause\n'
        f'2. Surgical fix - no regex on whole files\n'
        f'3. python3 -m py_compile video_pipeline_v3/{broken}\n'
        f'4. python3 video_pipeline_v3/preflight.py --no-tts\n'
        f'5. git add video_pipeline_v3/{broken} && git commit -m "autofix(iter{iteration})" && git push origin main\n'
        f'6. echo AUTOFIX_COMPLETE\n\n'
        f'No clarifying questions. Do not stop until AUTOFIX_COMPLETE.'
    )

    prompt_file = f'/tmp/cc_prompt_{iteration}.txt'
    with open(prompt_file, 'w') as f:
        f.write(prompt)

    subprocess.run(f'tmux kill-session -t {session} 2>/dev/null', shell=True)
    time.sleep(1)
    subprocess.run(f'tmux new-session -d -s {session} -x 220 -y 50', shell=True)
    subprocess.run(
        f"tmux send-keys -t {session} "
        f"'cd {BASE} && unset ANTHROPIC_API_KEY && cat {prompt_file} | claude --dangerously-skip-permissions' Enter",
        shell=True)

    start = time.time()
    last = ''
    while time.time() - start < CC_REPAIR_TIMEOUT:
        time.sleep(15)
        pane = subprocess.run(f'tmux capture-pane -t {session} -p 2>/dev/null',
                              shell=True, capture_output=True, text=True).stdout
        if 'AUTOFIX_COMPLETE' in pane:
            log(f'CC repair done: {session}')
            telegram(f'CC repair complete iter {iteration}')
            subprocess.run(f'tmux kill-session -t {session} 2>/dev/null', shell=True)
            return True
        lines = [l.strip() for l in pane.split('\n') if l.strip()]
        if lines and lines[-1] != last:
            log(f'CC[{session}]: {lines[-1][:100]}')
            last = lines[-1]
        alive = subprocess.run(f'tmux has-session -t {session} 2>/dev/null', shell=True)
        if alive.returncode != 0:
            log(f'CC session {session} died')
            return False

    log(f'CC repair timeout')
    subprocess.run(f'tmux kill-session -t {session} 2>/dev/null', shell=True)
    return False

# ── utilities ─────────────────────────────────────────────────────────────────
def kill_renders():
    r = subprocess.run(['pgrep', '-f', 'daily_producer.py'], capture_output=True, text=True)
    for pid in r.stdout.strip().split():
        try:
            os.kill(int(pid), signal.SIGTERM)
            log(f'Killed PID {pid}')
        except Exception:
            pass
    if r.stdout.strip():
        time.sleep(3)

def clear_pycache():
    subprocess.run(f'find {PIPELINE} -name __pycache__ -type d -exec rm -rf {{}} + 2>/dev/null', shell=True)
    log('Pycache cleared')

def run_preflight():
    r = subprocess.run([sys.executable, f'{PIPELINE}/preflight.py', '--no-tts'],
                       capture_output=True, text=True, cwd=PIPELINE)
    if r.returncode != 0:
        log(f'PREFLIGHT FAIL:\n{(r.stdout+r.stderr)[-400:]}')
        return False
    log('Preflight PASSED')
    return True

def today_dir():
    return f'{OUTPUT_BASE}/{datetime.now().strftime("%Y-%m-%d")}'

def find_mp4(after_ts=None):
    files = [f for f in glob.glob(f'{today_dir()}/pulse_check_*.mp4')
             if '.mp4.' not in os.path.basename(f)]
    if after_ts:
        files = [f for f in files if os.path.getmtime(f) >= after_ts]
    return sorted(files)[-1] if files else None

def get_grade():
    return run_gemini_grade()[0]

def run_gemini_grade():
    """Run gemini_grade.py as subprocess, return (score, full_output) or (0, error_msg)."""
    grade_script = f'{PIPELINE}/gemini_grade.py'
    log('Running Gemini grading subprocess...')
    try:
        r = subprocess.run(
            [sys.executable, grade_script],
            capture_output=True, text=True, cwd=PIPELINE, timeout=300)
        combined = (r.stdout or '') + '\n' + (r.stderr or '')
        log(f'Gemini grade exit={r.returncode}')
        # Parse GRADE_X_PASS|score| or GRADE_X_FAIL|score|
        m = re.search(r'GRADE_[A-F]_(PASS|FAIL)\|(\d+)\|', combined)
        if m:
            score = int(m.group(2))
            log(f'Gemini parsed score={score} ({m.group(0)})')
            return score, combined
        log(f'Gemini output did not match expected pattern, falling back to JSON')
    except subprocess.TimeoutExpired:
        log('Gemini grade subprocess timed out (300s)')
        combined = 'TIMEOUT: gemini_grade.py exceeded 300s'
    except Exception as e:
        log(f'Gemini grade subprocess error: {e}')
        combined = str(e)
    # Fallback: read the JSON grade file
    try:
        data = json.load(open(GEMINI_GRADE_FILE))
        score = data.get('overall_score', 0)
        log(f'Fallback grade from JSON: {score}')
        return score, combined
    except Exception:
        log('No fallback grade available')
        return 0, combined

def launch_render():
    log_path = f'{LOGS}/render_{int(time.time())}.log'
    env = os.environ.copy()
    env.pop('ANTHROPIC_API_KEY', None)  # force relay to read fresh .env
    env['CUDA_VISIBLE_DEVICES'] = '0'
    render_start = time.time()
    with open(log_path, 'w') as logf:
        proc = subprocess.Popen(
            [sys.executable, f'{PIPELINE}/daily_producer.py'],
            cwd=PIPELINE, env=env, stdout=logf, stderr=subprocess.STDOUT)
    import shutil as _sh
    free_gb = _sh.disk_usage('/home/ultron').free / 1024**3
    if free_gb < 3.0:
        telegram(f'DISK CRITICAL: {free_gb:.1f}GB free — loop paused')
        time.sleep(300)
        return
    log(f'Render PID {proc.pid}')
    while True:
        time.sleep(10)
        ret = proc.poll()
        elapsed = time.time() - render_start
        if ret is not None:
            out = open(log_path).read()
            log(f'Render exit={ret} elapsed={elapsed:.0f}s')
            return ret == 0, out, ret, render_start
        if elapsed > RENDER_TIMEOUT:
            log(f'TIMEOUT {RENDER_TIMEOUT}s - killing')
            proc.terminate(); time.sleep(3); proc.kill()
            return False, open(log_path).read(), -1, render_start
        if find_mp4(after_ts=render_start):
            try: proc.wait(timeout=30)
            except subprocess.TimeoutExpired: proc.terminate()
            return True, open(log_path).read(), 0, render_start

# ── main ──────────────────────────────────────────────────────────────────────
def main():
    iteration   = 0
    consec_a    = 0
    best        = get_grade()
    unk_streak  = 0

    log('=' * 60)
    log('PERPETUAL LOOP STARTED - target 5x Grade A - no time limit')
    log(f'CC auto-repair enabled | starting best={best}/100')
    log('=' * 60)
    telegram(f'Perpetual loop started. Best so far: {best}/100. Target: 5x Grade A.')

    kill_renders()
    clear_pycache()

    while True:
        iteration += 1
        log(f'\n{"="*60}')
        log(f'ITER {iteration} | consec_A={consec_a}/{TARGET_A} | best={best}')
        log('='*60)

        # preflight
        pf_fails = 0
        while not run_preflight():
            pf_fails += 1
            clear_pycache()
            time.sleep(5)
            if pf_fails >= 3:
                r = subprocess.run([sys.executable, f'{PIPELINE}/preflight.py', '--no-tts'],
                                   capture_output=True, text=True, cwd=PIPELINE)
                cc_auto_repair(r.stdout + r.stderr, iteration)
                clear_pycache()
                pf_fails = 0

        # Archive any existing MP4 so find_mp4() only detects genuinely new renders
        existing = glob.glob(f'{today_dir()}/pulse_check_*.mp4')
        existing = [f for f in existing if '.mp4.' not in os.path.basename(f)]
        for old_mp4 in existing:
            archived = old_mp4.replace('pulse_check_', 'archived_iter_prev_')
            try: os.rename(old_mp4, archived)
            except Exception: pass

        success, output, exit_code, render_start = launch_render()

        mp4 = find_mp4(after_ts=render_start)
        if mp4:
            grade, gemini_output = run_gemini_grade()
            if grade > best:
                best = grade
            log(f'VIDEO: {os.path.basename(mp4)} | grade={grade}/100')
            telegram(f'Video produced! Grade: {grade}/100 | iter={iteration} | consec_A={consec_a}')
            if grade >= 90:
                consec_a += 1
                log(f'GRADE A! {consec_a}/{TARGET_A}')
                telegram(f'GRADE A #{consec_a}/{TARGET_A}! Score={grade}/100')
                if consec_a >= TARGET_A:
                    log('MISSION COMPLETE: 5x Grade A!')
                    telegram(f'PIPELINE STABLE: 5x Grade A! Final score: {grade}/100')
                    return
            else:
                consec_a = 0
                log(f'Below 90 — sending Gemini report to CC for repair')
                cc_auto_repair(gemini_output, iteration)
            unk_streak = 0
            kill_renders()
            clear_pycache()
            time.sleep(15)
            continue

        # crash
        lines = output.strip().split('\n')
        idx = None
        for i, l in enumerate(lines):
            if any(x in l for x in ['Traceback','Error:','NameError','TypeError']):
                idx = i
        snippet = '\n'.join(lines[max(0,(idx or 0)-2):(idx or 0)+12]) if idx else '\n'.join(lines[-12:])
        log(f'CRASH:\n{snippet}')

        fixed, desc = diagnose_and_fix(output)
        if fixed:
            unk_streak = 0
        else:
            unk_streak += 1
            log(f'Unknown error #{unk_streak} - spawning CC')
            cc_auto_repair(output, iteration)
            if unk_streak >= 10:
                telegram(f'LOOP STOPPED: {unk_streak} consecutive crashes. Fix issue then restart manually.')
                log('HARD STOP: 5 consecutive unknown errors')
                return
            elif unk_streak >= 3:
                telegram(f'WARNING: {unk_streak} consecutive errors')

        clear_pycache()
        kill_renders()
        time.sleep(10)

if __name__ == '__main__':
    main()
