Read ~/protocol_pulse/docs/gospels/WATCHDOG_LLM_GOSPEL.md first. Then read ~/protocol_pulse/PIPELINE_LAWS.md.

Build the Protocol Pulse local LLM watchdog. All shell commands. No GUI.

SYSTEM: Ultron, Ubuntu 22.04, 4x RTX 4090. Ollama at /usr/local/bin/ollama. Python 3.10.
GOSPEL: ~/protocol_pulse/docs/gospels/WATCHDOG_LLM_GOSPEL.md

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 1 — START OLLAMA ON GPU 2 ONLY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Kill any existing ollama process. Start fresh on GPU 2:
  pkill -f "ollama serve" 2>/dev/null; sleep 2
  CUDA_VISIBLE_DEVICES=2 OLLAMA_HOST=127.0.0.1:11435 ollama serve &
  sleep 5

Test it responds:
  curl -s http://localhost:11435/api/tags

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 2 — PULL MODEL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Try Qwen3-Coder first:
  OLLAMA_HOST=127.0.0.1:11435 ollama pull qwen3-coder:30b

If qwen3-coder:30b not available (model not found), fall back to:
  OLLAMA_HOST=127.0.0.1:11435 ollama pull qwen2.5-coder:32b

Record which model was pulled. Use it for all subsequent steps.

Verify loaded:
  OLLAMA_HOST=127.0.0.1:11435 ollama list

Test inference:
  OLLAMA_HOST=127.0.0.1:11435 ollama run {MODEL} "print a 3-line python hello world" --nowordwrap

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 3 — BUILD local_watchdog.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
File: ~/protocol_pulse/services/local_watchdog.py

The watchdog must:
1. Read WATCHDOG_LLM_GOSPEL.md for all rules
2. Tail overnight_loop.log (last 50 lines)
3. Detect crash patterns:
   - "KeyError" → CLASS A
   - "Traceback" + "daily_producer" → CLASS B  
   - "exit: -15" + "FATAL" → CLASS B
   - "Render failed" 3x in a row → CLASS B
   - "GRADE: F" → CLASS B
   - loop process dead → CLASS B
4. For CLASS A/B: call local Ollama with diagnosis prompt
5. Parse diagnosis: affected file, proposed patch (unified diff format)
6. Apply patch with subprocess
7. Run regression_test.sh
8. If 0 FAILs: commit patch + restart loop + Telegram success
9. If any FAILs: revert with git checkout + Telegram alert
10. For CLASS C: Telegram alert only, never patch

SAFETY GATES (hard-coded, never configurable):
- Check pgrep daily_producer before patching — skip if running
- Cooldown: write timestamp to /tmp/watchdog_last_patch_{file}.txt, skip if <600s ago
- Max patches per hour: read /tmp/watchdog_patch_count_{hour}.txt, abort if >=3
- NEVER patch: assembler.py, tts_engine.py, gemini_grade.py, routes.py

TELEGRAM function:
  def send_telegram(msg):
      load .env → TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID
      POST https://api.telegram.org/bot{TOKEN}/sendMessage

OLLAMA diagnosis prompt template:
  system: "You are a Python/FFmpeg expert debugging a video production pipeline.
           Analyze the crash log and return ONLY valid JSON:
           {diagnosis: str, affected_file: str, patch_diff: str, confidence: float}"
  user: "CRASH LOG:\n{last_50_lines}\n\nFILE CONTENT:\n{affected_file_content}"

Parse JSON response. If confidence < 0.8 → skip auto-patch, alert only.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 4 — STAGE BROADCAST OFFLOAD
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
In ~/protocol_pulse/services/stage_broadcast_service.py:
Add a LOCAL_LLM_URL = "http://localhost:11435" config at top.

Modify _generate_script() to try local Ollama FIRST:
  - POST http://localhost:11435/api/generate
  - model: {pulled_model_name}
  - Same prompt as before
  - timeout: 15s
  - If local fails (timeout/error): fall back to Claude Haiku API
  - Log which path was used: local vs api

This makes broadcast scripts free when watchdog model is running.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 5 — SYSTEMD SERVICE FOR OLLAMA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Create /etc/systemd/system/ollama-watchdog.service:
  [Unit]
  Description=Ollama Watchdog LLM on GPU 2
  After=network.target

  [Service]
  User=ultron
  Environment=CUDA_VISIBLE_DEVICES=2
  Environment=OLLAMA_HOST=127.0.0.1:11435
  ExecStart=/usr/local/bin/ollama serve
  Restart=always
  RestartSec=10

  [Install]
  WantedBy=multi-user.target

Enable and start:
  sudo systemctl daemon-reload
  sudo systemctl enable ollama-watchdog
  sudo systemctl start ollama-watchdog

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 6 — CRON + TEST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Add to crontab:
  */1 * * * * python3 /home/ultron/protocol_pulse/services/local_watchdog.py >> /home/ultron/protocol_pulse/logs/watchdog_llm.log 2>&1

Test full cycle:
  python3 ~/protocol_pulse/services/local_watchdog.py

Should output: system state assessment, no crashes detected or crash+diagnosis.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMMIT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
git add services/local_watchdog.py services/stage_broadcast_service.py
git commit -m "feat(watchdog): local LLM watchdog on GPU 2 — Qwen3/Qwen2.5-Coder, auto-diagnose+patch CLASS A/B crashes, Telegram alerts, stage broadcast local offload"
git push

DO NOT touch: assembler.py, tts_engine.py, gemini_grade.py, overnight_render_loop.py, routes.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADDITIONAL REQUIREMENT — 4-LAYER AUTONOMOUS SYSTEM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
The watchdog is NOT just a crash responder. It has 4 independent check layers.
Read the FRESH PERSPECTIVE SYSTEM section of the gospel carefully.

Implement all 4 layers in local_watchdog.py:

def run_reactive_check():     # Called every 60s via cron - crash response
def run_health_scan():        # Called every 15min - system health 
def run_pattern_analysis():   # Called every 6h - trend detection
def run_weekly_audit():       # Called Monday 08:00 UTC - deep review

def send_daily_briefing():    # Called 09:00 ET - morning Telegram summary

Each function uses a FRESH Ollama conversation with zero prior context.
Each function is independently triggered via separate cron entries:
  */1  * * * * python3 .../local_watchdog.py --mode reactive
  */15 * * * * python3 .../local_watchdog.py --mode health
  0 */6 * * * python3 .../local_watchdog.py --mode pattern
  0 8 * * 1   python3 .../local_watchdog.py --mode audit
  0 13 * * *  python3 .../local_watchdog.py --mode briefing

main() reads sys.argv[1] --mode flag to route to correct function.
