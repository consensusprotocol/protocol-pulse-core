#!/usr/bin/env python3
"""GPU drop detector — logs the exact moment/state when a GPU falls off, so the
NEXT involuntary drop is a diagnosable event instead of a mystery.
Polls every 60s. On a drop, records timestamp, nvidia-smi error, what render
procs were running, GPU temps (from last good read), and lspci presence."""
import subprocess, time, os, json
from datetime import datetime

LOG = "/home/ultron/protocol_pulse/logs/gpu_drop_events.log"
os.makedirs(os.path.dirname(LOG), exist_ok=True)

def now(): return datetime.now().strftime("%Y-%m-%d %H:%M:%S ET")
def sh(c):
    try: return subprocess.run(c, shell=True, capture_output=True, text=True, timeout=20).stdout.strip()
    except Exception as e: return f"ERR:{e}"

def log(msg):
    line = f"[{now()}] {msg}"
    with open(LOG, "a") as f: f.write(line + "\n")
    print(line, flush=True)

log("gpu_watchdog started")
last_ok = True
while True:
    smi = sh("nvidia-smi --query-gpu=index,temperature.gpu,power.draw,utilization.gpu --format=csv,noheader")
    healthy = "Unable to determine" not in smi and "ERR" not in smi and smi.strip() != ""
    if healthy and not last_ok:
        log(f"RECOVERED. GPUs: {smi.replace(chr(10),' | ')}")
    if not healthy and last_ok:
        # a drop just happened — capture everything we can
        lspci = sh("lspci | grep -i nvidia")
        procs = sh("for p in /proc/[0-9]*; do c=$(tr '\\0' ' ' < $p/cmdline 2>/dev/null); "
                   "case \"$c\" in *daily_producer*|*wav2lip*|*boomers_clip*|*avatar_server*|*ffmpeg*) "
                   "echo \"${c:0:70}\";; esac; done")
        log("=== GPU DROP DETECTED ===")
        log(f"smi_error: {smi}")
        log(f"lspci_nvidia: {lspci.replace(chr(10),' | ')}")
        log(f"running_gpu_procs: {procs.replace(chr(10),' ; ') or 'none'}")
        log("=== power cycle required to recover; captured state above ===")
    last_ok = healthy
    time.sleep(60)
