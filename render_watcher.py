#!/usr/bin/env python3
"""Watch for next completed render, send Telegram with serve URL, then exit."""
import os, time, glob, subprocess
from datetime import datetime, timedelta

BASE = "/home/ultron/protocol_pulse"
VIDEO_SERVER_PORT = 5100
POLL_INTERVAL = 30
MAX_WAIT = 7200  # 2 hours

def load_env():
    env = {}
    for line in open(os.path.join(BASE, ".env")):
        l = line.strip()
        if "=" in l and not l.startswith("#"):
            k, _, v = l.partition("=")
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env

def find_new_render(known):
    """Find pulse_check mp4s newer than what we already know about."""
    now = datetime.now()
    found = []
    for date_str in [now.strftime('%Y-%m-%d'), (now - timedelta(days=1)).strftime('%Y-%m-%d')]:
        d = os.path.join(BASE, "video_pipeline_v3/output", date_str)
        if not os.path.exists(d):
            continue
        for f in os.listdir(d):
            if f.endswith('.mp4') and 'pulse_check' in f and '.' not in f.replace('pulse_check_','').replace('.mp4',''):
                full = os.path.join(d, f)
                sz = os.path.getsize(full)
                if sz > 50_000_000 and full not in known:
                    found.append(full)
    return found

def send_telegram(token, chat_id, msg):
    import urllib.request as ur
    import json
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    ur.urlopen(ur.Request(url,
        data=json.dumps({"chat_id": chat_id, "text": msg, "parse_mode": "HTML"}).encode(),
        headers={"Content-Type": "application/json"}), timeout=10)

def get_grade(mp4_path):
    """Try to read grade from logs."""
    grade_log = os.path.join(BASE, "video_pipeline_v3/logs/grade_report.log")
    if not os.path.exists(grade_log):
        return "?"
    lines = open(grade_log).readlines()
    # Find last grade score
    for line in reversed(lines):
        if "Grade" in line and ("/" in line or "F" in line or "A" in line):
            return line.strip().split("]")[-1].strip()[:60]
    return "?"

env = load_env()
tok = env.get("TELEGRAM_BOT_TOKEN", "")
chat = env.get("TELEGRAM_CHAT_ID", "")

# Snapshot known renders at start
known = set()
for date_str in [datetime.now().strftime('%Y-%m-%d'), (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')]:
    d = os.path.join(BASE, "video_pipeline_v3/output", date_str)
    if os.path.exists(d):
        for f in os.listdir(d):
            if f.endswith('.mp4') and 'pulse_check' in f and '.' not in f.replace('pulse_check_','').replace('.mp4',''):
                known.add(os.path.join(d, f))

print(f"Watching... known renders: {len(known)}")
send_telegram(tok, chat, "👁 Render watcher active — will send video link when next render completes.")

start = time.time()
while time.time() - start < MAX_WAIT:
    new = find_new_render(known)
    if new:
        mp4 = new[0]
        fname = os.path.basename(mp4)
        sz_mb = os.path.getsize(mp4) / 1e6
        grade = get_grade(mp4)
        # Video server serves from output dirs
        url = f"https://video.protocolpulse.io/{fname}"
        # Also get direct serve via file server on 5100
        url2 = f"http://relay.protocolpulse.io:5100/output/{fname}"
        msg = (
            f"🎬 <b>New Render Ready</b>\n"
            f"File: <code>{fname}</code>\n"
            f"Size: {sz_mb:.0f}MB\n"
            f"Grade: {grade}\n\n"
            f"<b>Stream/Download:</b>\n"
            f"<a href='{url}'>{url}</a>"
        )
        send_telegram(tok, chat, msg)
        print(f"SENT: {fname} {sz_mb:.0f}MB")
        # Copy to a predictable path for easy access
        import shutil
        latest = os.path.join(BASE, "video_pipeline_v3/output/latest_render.mp4")
        shutil.copy2(mp4, latest)
        print(f"Copied to latest_render.mp4")
        break
    time.sleep(POLL_INTERVAL)
else:
    send_telegram(tok, chat, "⏰ Render watcher timed out after 2h — no new render detected.")
    print("Timed out")
