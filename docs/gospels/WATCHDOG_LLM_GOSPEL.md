# PROTOCOL PULSE — LOCAL WATCHDOG LLM GOSPEL
# Version 1.0 | March 2026
# GOSPEL STATUS: Read before ANY watchdog modification

## MISSION
An always-on local LLM that monitors the Protocol Pulse render pipeline,
diagnoses crashes, proposes patches, and auto-applies ONLY after all tests pass.
Zero API cost. Zero token dependency. Zero blind patching.

## HARDWARE ALLOCATION
- GPU 0: Kokoro TTS (render pipeline) — NEVER TOUCH
- GPU 1: F5-TTS / BigVGAN2 (render pipeline) — NEVER TOUCH  
- GPU 2: Qwen3-Coder-30B A3B MoE — Watchdog PRIMARY (always-on, 18GB)
- GPU 3: Reserved — escalation burst only, not always loaded

## MODEL
Primary: Qwen3-Coder-30B A3B Instruct (MoE)
  - Pull: ollama pull qwen3-coder:30b
  - VRAM: ~18GB (Q4) on GPU 2 only
  - Speed: 73-87 tok/s — diagnosis in <5s
  - Strength: SWE-Bench 50.3%, best single-GPU code repair
Fallback: qwen2.5-coder:32b (if qwen3 unavailable)

## BACKEND
Ollama (NOT vLLM) — reasons:
  - Already installed at /usr/local/bin/ollama
  - Simple REST API at localhost:11434
  - Per-GPU CUDA device env: CUDA_VISIBLE_DEVICES=2 ollama serve
  - Hot model keeps loaded — sub-second cold start after first load

## WATCHDOG SERVICE
File: ~/protocol_pulse/services/local_watchdog.py
Cron: */1 * * * * (every 60 seconds)
Tmux: runs in tmux session "watchdog_llm"

## MONITORING TARGETS (priority order)
1. overnight_loop.log — primary crash source
2. daily_producer.py stderr — script generation failures  
3. GPU VRAM (nvidia-smi) — OOM detection
4. Disk space — prevent full-disk kills
5. gunicorn/Flask — site health

## CRASH CLASSIFICATION (what watchdog diagnoses)
CLASS A — Auto-patchable (safe):
  - KeyError in script_writer.py — string escape issue
  - ImportError — missing module, install it
  - FileNotFoundError — missing path, create it
  - SyntaxError — broken f-string or indentation

CLASS B — Patch + test (auto-apply only on test pass):
  - Traceback in daily_producer.py — logic errors
  - LUFS/forensics failures — ffmpeg filter issues
  - TTS failures — voice model errors

CLASS C — Alert only, never auto-patch:
  - assembler.py crashes — too complex, too risky
  - tts_engine.py crashes — GPU state involved
  - routes.py crashes — live site, requires human
  - Any crash affecting >1 file simultaneously

## SAFETY GATES (NON-NEGOTIABLE)
Gate 1: diagnosis confidence >= 0.8 before attempting patch
Gate 2: bash regression_test.sh must show 0 FAILs after patch
Gate 3: if test fails → revert patch immediately → Telegram alert
Gate 4: never patch same file twice in 10 minutes (cooldown)
Gate 5: never patch during active render (daily_producer.py running)
Gate 6: max 3 auto-patches per hour total system-wide

## TELEGRAM ALERTS
Send to: TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID from .env
Alert on:
  - Crash detected (always)
  - Patch applied (always)
  - Patch reverted (always)  
  - Test failure (always)
  - Class C crash (always)
  - Render loop dead >15 min (always)
Format: "🔴 CRASH: {type} in {file}
📋 {diagnosis}
✅ PATCH: {applied/not}
🧪 TESTS: {pass/fail}"

## STAGE BROADCAST OFFLOAD (cost saving)
stage_broadcast_service.py currently calls Claude Haiku every 5 min.
Watchdog service also handles: generate local scripts for broadcast segments
  using Qwen local model instead of API calls.
Saves ~$2-3/day at current broadcast frequency.

## FILE PATHS
Service: ~/protocol_pulse/services/local_watchdog.py
Config: ~/protocol_pulse/config/watchdog_config.json
Log: ~/protocol_pulse/logs/watchdog_llm.log
Patch history: ~/protocol_pulse/logs/watchdog_patches.jsonl
Ollama service: CUDA_VISIBLE_DEVICES=2 ollama serve (started on boot via systemd)

## WHAT WATCHDOG NEVER DOES
- Never modifies PIPELINE_LAWS.md or any gospel doc
- Never touches assembler.py, tts_engine.py, gemini_grade.py
- Never commits without regression_test.sh = 0 FAILs
- Never patches during render (check pgrep daily_producer first)
- Never runs on GPU 0 or GPU 1
- Never makes external API calls (local inference only)
- Never patches the watchdog itself
