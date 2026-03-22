Read ~/protocol_pulse/PIPELINE_LAWS.md and ~/protocol_pulse/docs/gospels/WATCHDOG_LLM_GOSPEL.md first.

TASK: Tune the stage broadcast local LLM pipeline so Qwen3-Coder on Ollama is reliably used instead of Claude Haiku API. The local path already exists but needs hardening.

TARGET FILE: ~/protocol_pulse/services/stage_broadcast_service.py
LOCAL LLM: http://localhost:11435, model qwen3-coder:30b
FALLBACK: Claude Haiku (only when Ollama is down)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INVESTIGATION FIRST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Test the local path right now:
   python3 -c "
   import requests
   resp = requests.post('http://localhost:11435/api/chat', json={
       'model': 'qwen3-coder:30b',
       'messages': [{'role':'user','content':'Say WORKING in one word'}],
       'stream': False
   }, timeout=20)
   print(resp.json().get('message',{}).get('content','FAILED'))
   "

2. Run the broadcast service and check logs to see if local or API path fires:
   python3 ~/protocol_pulse/services/stage_broadcast_service.py 2>&1 | grep -E "LOCAL|API|local|haiku|fallback|Script generated"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FIXES REQUIRED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FIX 1 — Increase local LLM timeout from 15s to 25s
The model needs warm-up time. 15s is too tight for first call after idle.
Find: timeout=15
Replace: timeout=25

FIX 2 — Improve the broadcast prompt quality for local model
The current prompt is just:
  "Segment type: {type}
Data: {json}
Generate a broadcast script..."
This is too sparse for Qwen. Improve it by adding the ANCHOR_SYSTEM context
and segment-specific instructions inline so Qwen knows the voice and format.

In _generate_script(), before calling _generate_script_local(), build a richer prompt:
  prompt = f"""You are Eryn, the Protocol Pulse Stage anchor.
Voice: calm authority, data-driven, sovereign Bitcoin perspective.
Speak in 2-3 sentences only. Present tense. No markdown. No hashtags. No em dashes.
End with a forward signal (what to watch), not a summary.

SEGMENT: {segment_type}
DATA: {json.dumps(context_data, indent=2)}

Write the spoken broadcast script now:"""

FIX 3 — Add local LLM usage metric to logs
After each _generate_script() call, log which path was used:
  logger.info("COST: script=%s source=%s", segment_type, "LOCAL" if local_result else "API")
This lets us track cost savings over time in watchdog_llm.log.

FIX 4 — Verify Qwen output quality gate
After getting local result, validate it is actually useful:
  - Length >= 30 characters
  - Does not contain markdown (no # or ** or -)
  - Does not start with "I " or "As an AI"
  If it fails any check, fall back to API and log: "LOCAL_REJECTED: {reason}"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TEST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Run: python3 ~/protocol_pulse/services/stage_broadcast_service.py 2>&1 | tail -20
Confirm logs show "Script generated via LOCAL LLM" at least once.
Confirm queue has new items: curl -s http://localhost:5000/api/stage/broadcast-queue | python3 -m json.tool | grep -E "type|queue_depth"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMMIT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
git add services/stage_broadcast_service.py
git commit -m "feat(broadcast): harden local LLM path — 25s timeout, richer prompt, output quality gate, cost logging"
git push

DO NOT touch: assembler.py, tts_engine.py, routes.py, overnight_render_loop.py