#!/usr/bin/env python3
"""
render_watchdog.py — watches render_patch.log, auto-launches overnight_render_loop.py on PASS.
Writes verdict to ~/protocol_pulse/logs/render_watchdog.log.
"""
import time, os, subprocess, sys
from datetime import datetime

LOG = os.path.expanduser("~/protocol_pulse/logs/render_patch.log")
WDG = os.path.expanduser("~/protocol_pulse/logs/render_watchdog.log")
PP  = os.path.expanduser("~/protocol_pulse")

def wlog(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(WDG, "a") as f:
        f.write(line + "\n")

wlog("Watchdog started — monitoring render_patch.log")

seen_lines = 0
deadline = time.time() + 7200  # 2h max

while time.time() < deadline:
    time.sleep(15)
    try:
        with open(LOG) as f:
            lines = f.readlines()
    except FileNotFoundError:
        wlog("Log not found yet, waiting...")
        continue

    new_lines = lines[seen_lines:]
    seen_lines = len(lines)

    for line in new_lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Detect PASS
        if "QUALITY GATE" in stripped or "QC:" in stripped:
            wlog(f"QC LINE: {stripped}")
        
        if any(x in stripped for x in ["PASS", "Grade A", "Grade B", "90/100", "91/100", "92/100", "93/100", "94/100", "95/100", "96/100", "97/100", "98/100", "99/100", "100/100"]):
            if "no_dead_air" not in stripped and "FAIL" not in stripped:
                wlog(f"PASS SIGNAL: {stripped}")

        # Detect SUCCESS + no dead_air failure = PASS
        if "PULSE CHECK V5 — SUCCESS" in stripped:
            # Wait a moment for QC to complete
            time.sleep(45)
            try:
                with open(LOG) as f:
                    full = f.read()
                if "no_dead_air" in full and "[FAIL] no_dead_air" in full:
                    wlog("VERDICT: FAIL — dead air still present (patch may not have applied)")
                    wlog("Check assembler.py line 769 manually.")
                    sys.exit(1)
                elif "HOLD (threshold" in full:
                    wlog("VERDICT: FAIL — quality below threshold (check QC report)")
                    sys.exit(1)
                else:
                    wlog("VERDICT: PASS — launching overnight_render_loop.py --daemon")
                    result = subprocess.run(
                        ["python3", "overnight_render_loop.py", "--daemon"],
                        cwd=PP, capture_output=True, text=True, timeout=30
                    )
                    wlog(f"Overnight loop stdout: {result.stdout.strip()}")
                    wlog(f"Overnight loop stderr: {result.stderr.strip()}")
                    wlog("DONE — overnight loop launched.")
                    sys.exit(0)
            except Exception as e:
                wlog(f"ERROR during verdict: {e}")
                sys.exit(1)

        # Hard FAIL states
        if any(x in stripped for x in ["Traceback", "PIPELINE ABORTED", "FATAL", "pipeline failed"]):
            wlog(f"FATAL: {stripped}")
            sys.exit(1)

wlog("TIMEOUT — render took >2h, check manually.")
sys.exit(1)
