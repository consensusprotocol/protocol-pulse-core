#!/usr/bin/env python3
"""
pulse_watchdog.py - 2-minute render loop monitor with auto-restart.
Writes MORNING_VERDICT.txt so you get a 1-glance status on wake.
"""
import os, time, json, subprocess, glob, logging
from datetime import datetime

BASE     = os.path.expanduser("~/protocol_pulse")
PIPELINE = os.path.join(BASE, "video_pipeline_v3")
VERDICT  = os.path.join(BASE, "logs", "MORNING_VERDICT.txt")
WLOG     = os.path.join(BASE, "logs", "watchdog_pulse.log")
LOOP_LOG = os.path.join(PIPELINE, "logs", "overnight_loop.log")
WINNER   = os.path.join(PIPELINE, "logs", "WINNER_RECIPE.json")

logging.basicConfig(
    filename=WLOG, level=logging.INFO,
    format="[%(asctime)s] %(message)s", datefmt="%H:%M:%S"
)
log = logging.getLogger()

def w(msg):
    log.info(msg)
    print(msg, flush=True)

def run(cmd):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=20)
        return r.stdout.strip()
    except Exception:
        return ""

def loop_pid():
    return run("pgrep -f overnight_render_loop.py")

def newest_output_age_min():
    today = datetime.now().strftime("%Y-%m-%d")
    patterns = [
        os.path.join(PIPELINE, "output", today, "*.mp4"),
        os.path.join(PIPELINE, "output", today, "work", "*.mp4"),
        os.path.join(PIPELINE, "output", today, "audio", "*.m4a"),
    ]
    files = []
    for pat in patterns:
        files += [f for f in glob.glob(pat) if ".mp4." not in f]
    if not files:
        return 999
    newest = max(files, key=os.path.getmtime)
    return (time.time() - os.path.getmtime(newest)) / 60

def restart_loop():
    w("AUTO-RESTART: killing stale processes")
    run("pkill -f daily_producer 2>/dev/null")
    run("pkill -f overnight_render_loop 2>/dev/null")
    time.sleep(4)
    run("cd /home/ultron/protocol_pulse && git pull 2>&1 | tail -2")
    w("AUTO-RESTART: relaunching loop in avatar tmux session")
    run("tmux send-keys -t avatar C-c 2>/dev/null")
    time.sleep(2)
    run("tmux send-keys -t avatar 'cd ~/protocol_pulse && python3 overnight_render_loop.py --daemon' Enter")
    time.sleep(5)
    pid = loop_pid()
    if pid:
        w(f"AUTO-RESTART: success — PID {pid}")
    else:
        w("AUTO-RESTART: FAILED — manual intervention needed")

def write_verdict(status, note=""):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    out = []
    out.append("PROTOCOL PULSE MORNING VERDICT")
    out.append(f"Updated: {ts}")
    out.append("=" * 50)
    out.append("")
    out.append(f"STATUS: {status}")
    if note:
        out.append(f"NOTE: {note}")

    if os.path.exists(WINNER):
        with open(WINNER) as f:
            wr = json.load(f)
        out.append("")
        out.append(f"*** GRADE {wr.get('grade')} — {wr.get('score')}/100 — WINNER LOCKED ***")
        out.append(f"VIDEO: {wr.get('video')}")
    else:
        out.append("")
        out.append("WINNER_RECIPE: not yet — loop still running")

    out.append("")
    out.append("LAST LOOP LOG:")
    if os.path.exists(LOOP_LOG):
        with open(LOOP_LOG) as f:
            tail = f.readlines()[-10:]
        out += ["  " + l.rstrip() for l in tail]
    else:
        out.append("  No log yet")

    today = datetime.now().strftime("%Y-%m-%d")
    pat = os.path.join(PIPELINE, "output", today, "*.mp4")
    vids = [f for f in glob.glob(pat) if ".mp4." not in f]
    out.append("")
    out.append("LATEST VIDEO:")
    if vids:
        v = max(vids, key=os.path.getmtime)
        sz = run(f"du -h '{v}' | cut -f1")
        mt = run(f"stat -c '%y' '{v}' | cut -d'.' -f1")
        out.append(f"  {os.path.basename(v)} | {sz} | {mt}")
    else:
        out.append("  None yet for today")

    gpu = run("nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader")
    out.append("")
    out.append("GPU:")
    for g in gpu.splitlines():
        out.append(f"  {g}")

    out.append("")
    out.append("LIVE: tail -f ~/protocol_pulse/video_pipeline_v3/logs/overnight_loop.log")
    out.append("QUICK CHECK: cat ~/protocol_pulse/logs/MORNING_VERDICT.txt")

    with open(VERDICT, "w") as f:
        f.write("\n".join(out))

# ── MAIN ──────────────────────────────────────────────────────────
w("Pulse watchdog started — polling every 2 minutes")
w(f"Verdict: {VERDICT}")
write_verdict("STARTING", "Watchdog just launched")

restart_count = 0
last_restart  = 0

while True:
    try:
        pid    = loop_pid()
        age    = newest_output_age_min()
        winner = os.path.exists(WINNER)

        if winner:
            w("WINNER_RECIPE exists — Grade A achieved. Watchdog done.")
            write_verdict("COMPLETE — GRADE A", "Winner locked. Check WINNER_RECIPE.json.")
            break

        if not pid:
            w(f"LOOP DEAD. Last file {age:.0f}min ago. Restarting...")
            if time.time() - last_restart > 600:
                restart_loop()
                restart_count += 1
                last_restart = time.time()
                write_verdict(f"RESTARTED x{restart_count}", "Loop was dead, auto-restarted")
            else:
                write_verdict("DEAD — restart throttled", "Too soon since last restart")

        elif age > 30 and age < 990:
            w(f"STALL: no output for {age:.0f}min. PID={pid}. Restarting...")
            if time.time() - last_restart > 600:
                restart_loop()
                restart_count += 1
                last_restart = time.time()
                write_verdict(f"STALL RESTART x{restart_count}", f"No output for {age:.0f}min")
            else:
                write_verdict(f"STALLED", f"No output {age:.0f}min — restart throttled")

        else:
            status = f"RUNNING (PID {pid}, last output {age:.0f}min ago)"
            w(status)
            write_verdict("RUNNING", status)

    except Exception as e:
        w(f"Watchdog error: {e}")

    time.sleep(120)

