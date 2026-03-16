#!/usr/bin/env python3
"""
tg_watcher.py — Perpetual Telegram status reporter for Protocol Pulse.
Runs independently of the render loop. Reports on everything.
"""
import os, time, glob, json, re, subprocess, urllib.request
from datetime import datetime

BASE     = '/home/ultron/protocol_pulse'
PIPELINE = f'{BASE}/video_pipeline_v3'
LOGS     = f'{BASE}/logs'

def load_env():
    env = {}
    try:
        for line in open(f'{BASE}/.env'):
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                k, v = line.split('=', 1)
                env[k.strip()] = v.strip()
    except Exception:
        pass
    return env

ENV = load_env()

def tg(msg):
    token = ENV.get('TELEGRAM_BOT_TOKEN', '')
    chat  = ENV.get('TELEGRAM_CHAT_ID', '')
    if not token or not chat:
        return
    try:
        payload = json.dumps({'chat_id': chat, 'text': f'📡 {msg}'}).encode()
        req = urllib.request.Request(
            f'https://api.telegram.org/bot{token}/sendMessage',
            data=payload, headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f'TG fail: {e}')

def get_render_procs():
    r = subprocess.run(['pgrep', '-f', 'daily_producer.py'], capture_output=True, text=True)
    return [p.strip() for p in r.stdout.strip().split() if p.strip()]

def get_loop_alive():
    r = subprocess.run(['pgrep', '-f', 'autonomous_render_loop'], capture_output=True, text=True)
    return bool(r.stdout.strip())

def today_mp4s():
    date = datetime.now().strftime('%Y-%m-%d')
    files = [f for f in glob.glob(f'{PIPELINE}/output/{date}/pulse_check_*.mp4')
             if '.mp4.' not in os.path.basename(f)]
    return sorted(files)

def get_latest_grade():
    try:
        scores = re.findall(r'TOTAL[:\s]+(\d+)/100', open(f'{LOGS}/grade_report.log').read())
        if scores: return int(scores[-1])
    except Exception:
        pass
    try:
        return json.load(open(f'{LOGS}/best_grade.json')).get('score', 0)
    except Exception:
        return None

def get_loop_iter():
    try:
        lines = open(f'{LOGS}/autonomous_loop.log').readlines()
        for line in reversed(lines):
            m = re.search(r'ITER (\d+)', line)
            if m: return int(m.group(1))
    except Exception:
        pass
    return None

def get_proof_stage():
    try:
        import glob as _g
        logs = sorted(_g.glob(f'{LOGS}/proof_render*.log'), key=os.path.getmtime)
        latest = logs[-1] if logs else f'{LOGS}/proof_render.log'
        lines = open(latest).readlines()
        for line in reversed(lines):
            line = line.strip()
            if line and not line.startswith('[scanner]'):
                return line[:120]
    except Exception:
        pass
    return None

def main():
    tg('🚀 TG Watcher started — will report every 30 min idle, 10 min when rendering')
    
    last_mp4s       = set(today_mp4s())
    last_grade      = get_latest_grade()
    last_iter       = get_loop_iter()
    last_render_pids= set(get_render_procs())
    loop_was_alive  = get_loop_alive()
    last_report_min = -1
    consecutive_dead= 0

    while True:
        time.sleep(60)
        now = datetime.now()
        minute = now.minute

        # ── New MP4 landed ──
        current_mp4s = set(today_mp4s())
        new_mp4s = current_mp4s - last_mp4s
        if new_mp4s:
            # Wait 90s for file to fully finish writing before alerting
            time.sleep(90)
            for mp4 in new_mp4s:
                size_mb = os.path.getsize(mp4) / 1024 / 1024
                grade = get_latest_grade()
                grade_str = f'{grade}/100' if grade is not None else 'grading...'
                tg(f'🎬 VIDEO LANDED\n{os.path.basename(mp4)}\n{size_mb:.0f}MB | Grade: {grade_str}')
            last_mp4s = current_mp4s
            last_grade = get_latest_grade()

        # ── Grade changed ──
        current_grade = get_latest_grade()
        if current_grade is not None and current_grade != last_grade and current_grade > 0:
            if last_grade is not None:
                emoji = '🏆' if current_grade >= 90 else '📊'
                tg(f'{emoji} Grade update: {current_grade}/100 (was {last_grade})')
            last_grade = current_grade

        # ── Render proc started/died ──
        current_pids = set(get_render_procs())
        new_pids = current_pids - last_render_pids
        died_pids = last_render_pids - current_pids
        if new_pids:
            tg(f'▶️ Render started — PID(s): {", ".join(new_pids)}')
        if died_pids and not current_pids:
            # All renders dead
            if not today_mp4s():
                tg(f'⚠️ Render process died — no video produced yet')
        last_render_pids = current_pids

        # ── Loop alive/dead changes ──
        loop_alive = get_loop_alive()
        if loop_was_alive and not loop_alive:
            tg('🔴 Autonomous loop DIED — not restarting (manual intervention needed)')
        elif not loop_was_alive and loop_alive:
            tg('🟢 Autonomous loop started')
        loop_was_alive = loop_alive

        # ── Iteration progress (when loop running) ──
        current_iter = get_loop_iter()
        if loop_alive and current_iter and current_iter != last_iter:
            tg(f'🔄 Loop iter {current_iter} | best grade: {last_grade or "none"}/100')
            last_iter = current_iter

        # ── GPU idle check (every 5 min) ──
        if minute % 5 == 0 and minute != last_report_min:
            try:
                import subprocess
                result = subprocess.run(['nvidia-smi','--query-gpu=utilization.gpu,temperature.gpu',
                    '--format=csv,noheader'], capture_output=True, text=True, timeout=5)
                gpu_lines = [l.strip() for l in result.stdout.strip().split('\n') if l.strip()]
                usages = []
                for line in gpu_lines:
                    parts = line.split(',')
                    if parts:
                        usages.append(int(parts[0].strip().replace(' %','')))
                # If renders active but all GPUs idle >10% for >10min - alert
                if get_render_procs() and all(u < 5 for u in usages):
                    if not hasattr(get_gpu_idle_start, '_t'):
                        get_gpu_idle_start._t = time.time()
                    elif time.time() - get_gpu_idle_start._t > 600:
                        tg(f'⚠️ GPU STALL — renders running but GPUs at {usages}% for >10min')
                        get_gpu_idle_start._t = time.time()
                else:
                    get_gpu_idle_start._t = time.time()
            except Exception:
                pass


        # ── ALERT 1: Key revocation (401 in any render log) ──
        try:
            import glob as _glob
            recent_logs = sorted(_glob.glob(f'{LOGS}/render_*.log'), key=os.path.getmtime)[-3:]
            for log in recent_logs:
                age = time.time() - os.path.getmtime(log)
                if age < 120:  # only check logs modified in last 2 min
                    content = open(log).read()
                    if 'HTTP/1.1 401 Unauthorized' in content or 'invalid x-api-key' in content:
                        tg(f'🔑 API KEY REVOKED — 401 detected in {os.path.basename(log)}\nGo to console.anthropic.com and generate a new key, then update ~/protocol_pulse/.env')
                        break
        except Exception:
            pass

        # ── ALERT 2: Clip selection failure ──
        try:
            for log in recent_logs:
                age = time.time() - os.path.getmtime(log)
                if age < 120:
                    content = open(log).read()
                    if 'No clips selected' in content or 'All LLM providers failed for clip selection' in content:
                        # find specific error
                        err = 'unknown'
                        if '401' in content: err = 'API key 401'
                        elif 'too long' in content or 'maximum' in content: err = 'prompt too long'
                        elif '403' in content: err = 'API key 403/revoked'
                        elif 'timeout' in content.lower(): err = 'timeout'
                        tg(f'🚫 CLIP SELECTION FAILED\nCause: {err}\nRender halted. Check ~/protocol_pulse/logs/{os.path.basename(log)}')
                        break
        except Exception:
            pass

        # ── ALERT 3: Render stall (running >25min, no progress) ──
        try:
            pids = get_render_procs()
            if pids:
                for pid in pids:
                    try:
                        import subprocess as _sp
                        proc_start = float(open(f'/proc/{pid}/stat').read().split()[21]) / 100
                        import resource
                        uptime = float(open('/proc/uptime').read().split()[0])
                        elapsed = uptime - (float(open('/proc/uptime').read().split()[0]) - proc_start)
                    except Exception:
                        pass
                # Check log modification time — only alert if render process is ACTIVE
                import glob as _gs
                logs = sorted(_gs.glob(f'{LOGS}/proof_render*.log'), key=os.path.getmtime)
                log_file = logs[-1] if logs else None
                active_pids = get_render_procs()
                if log_file and os.path.exists(log_file) and active_pids:
                    log_age = time.time() - os.path.getmtime(log_file)
                    last_line = open(log_file).readlines()[-1].strip()[:120]
                    # Only stall if log is stale AND last line is NOT a completion/pass line
                    completed = any(x in last_line for x in ['PASS', 'HOLD', 'QUALITY SCORE', 'Episode held', 'PIPELINE SUCCESS'])
                    if log_age > 1500 and not completed:
                        tg(f'⏰ RENDER STALL — process running but log not updated in {int(log_age//60)}min\nLast: {last_line}')
        except Exception:
            pass

        # ── ALERT 4: Spend cap sentinel ──
        try:
            sentinel = f'{LOGS}/ANTHROPIC_SPEND_CAP_HIT.flag'
            if os.path.exists(sentinel):
                tg(f'💸 ANTHROPIC SPEND CAP HIT\nPipeline paused on Anthropic. Check account at console.anthropic.com\nDelete {sentinel} after resolving.')
        except Exception:
            pass

        # ── 10-minute heartbeat ──
        # Heartbeat: every 10 min if rendering, every 30 min if idle
        is_rendering = bool(get_render_procs())
        heartbeat_interval = 10 if is_rendering else 240
        if minute % heartbeat_interval == 0 and minute != last_report_min:
            last_report_min = minute
            pids = get_render_procs()
            mp4_count = len(today_mp4s())
            stage = get_proof_stage()

            # Clean stage label
            if pids:
                # Map raw log line to readable step
                stage_map = [
                    ('STEP 1', 'Step 1/12 — BTC price'),
                    ('STEP 2', 'Step 2/12 — scanning channels'),
                    ('STEP 3', 'Step 3/12 — selecting clips'),
                    ('STEP 4', 'Step 4/12 — extracting clips'),
                    ('STEP 5', 'Step 5/12 — writing script'),
                    ('STEP 6', 'Step 6/12 — generating audio'),
                    ('STEP 7', 'Step 7/12 — assembling video'),
                    ('STEP 8', 'Step 8/12 — assembling video'),
                    ('STEP 9', 'Step 9/12 — assembling video'),
                    ('STEP 10', 'Step 10/12 — assembling video'),
                    ('STEP 11', 'Step 11/12 — shorts'),
                    ('STEP 12', 'Step 12/12 — quality gate'),
                    ('SOCIAL CARD', 'Step 10/12 — tweet cards'),
                    ('APEX V2', 'Step 10/12 — final mix'),
                    ('concat', 'Step 10/12 — final concat'),
                    ('SETUP', 'Step 7/12 — assembling video'),
                    ('Extracting', 'Step 4/12 — extracting clips'),
                    ('Sending', 'Step 3/12 — selecting clips'),
                    ('Transcript', 'Step 2/12 — scanning channels'),
                ]
                readable = 'rendering...'
                if stage:
                    for key, label in stage_map:
                        if key in stage:
                            readable = label
                            break
                render_line = f'🎬 Render active — {readable}'
            else:
                render_line = f'✅ Last render: {last_grade or "none"}/100' if last_grade else '⏸️ No renders'

            tg(f'💓 {now.strftime("%H:%M")}\n'
               f'{render_line}\n'
               f'Videos today: {mp4_count}\n'
               f'Best grade: {last_grade or "none"}/100')

if __name__ == '__main__':
    main()
