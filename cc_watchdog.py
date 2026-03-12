#!/usr/bin/env python3
"""
cc_watchdog.py — Universal CC Session Watchdog
Monitors all active CC sessions every 60s.
Detects stalls, restarts them, logs everything.
Runs as a persistent daemon in tmux:watchdog
"""
import subprocess, time, os, json, re
from datetime import datetime

BASE = '/home/ultron/protocol_pulse'
LOG = f'{BASE}/logs/watchdog.log'
DISCORD_WEBHOOK = None  # add later if wanted

# Sessions to monitor: name → prompt file (for restart)
WATCHED = {
    'smart_loop':       {'type': 'python',  'cmd': 'python3 smart_render_loop.py', 'log': 'video_pipeline_v3/logs/smart_loop_run3.log', 'critical': True},
    'sovereignty_stack':{'type': 'cc',      'prompt': 'docs/cc_sovereignty_stack.md', 'critical': False},
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
    last_status = time.time()
    
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
            last_status = now

if __name__ == '__main__':
    main()
