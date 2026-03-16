#!/usr/bin/env python3
import os, time, subprocess, json, urllib.request
BASE = "/home/ultron/protocol_pulse"
def load_env():
    env = {}
    try:
        for line in open(f"{BASE}/.env"):
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    except: pass
    return env
ENV = load_env()
def tg(msg):
    tok = ENV.get("TELEGRAM_BOT_TOKEN","")
    chat = ENV.get("TELEGRAM_CHAT_ID","")
    if not tok or not chat: return
    try:
        payload = json.dumps({"chat_id":chat,"text":f"🔧 {msg}"}).encode()
        req = urllib.request.Request(f"https://api.telegram.org/bot{tok}/sendMessage",
            data=payload, headers={"Content-Type":"application/json"})
        urllib.request.urlopen(req, timeout=10)
    except: pass
def get_last_commit():
    r = subprocess.run(["git","-C",BASE,"log","--oneline","-1"], capture_output=True, text=True)
    return r.stdout.strip()
tg("CC round3 monitor started — 8 fixes in progress")
last_commit = get_last_commit()
start = time.time()
while True:
    time.sleep(30)
    elapsed = int(time.time() - start)
    new_commit = get_last_commit()
    if new_commit != last_commit:
        tg(f"✅ CC round3 committed:\n{new_commit[:70]}\nLaunching proof_render4...")
        time.sleep(5)
        subprocess.run(["tmux","kill-session","-t","proof_render4"], capture_output=True)
        subprocess.run(["tmux","new-session","-d","-s","proof_render4","-x","220","-y","50"])
        subprocess.run(["tmux","send-keys","-t","proof_render4",
            "unset ANTHROPIC_API_KEY && cd ~/protocol_pulse/video_pipeline_v3 && "
            "CUDA_VISIBLE_DEVICES=0 python3 daily_producer.py 2>&1 | "
            "tee ~/protocol_pulse/logs/proof_render4.log", "Enter"])
        tg("🎬 proof_render4 launched")
        break
    if elapsed % 300 == 0 and elapsed > 0:
        pane = subprocess.run(["tmux","capture-pane","-t","cc_round3","-p"],
            capture_output=True, text=True).stdout
        lines = [l for l in pane.split("\n") if l.strip()][-2:]
        tg(f"CC working ({elapsed//60}min):\n" + "\n".join(lines))
    if elapsed > 3600:
        tg("⚠️ CC round3 >60min — check tmux:cc_round3")
        break
