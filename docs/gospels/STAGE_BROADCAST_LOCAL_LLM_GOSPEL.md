# GOSPEL: STAGE BROADCAST LOCAL LLM
# Version 1.0 | March 2026 | Status: LIVE ✅

## STATUS: OPERATIONAL
Local LLM path confirmed firing as of 2026-03-21 21:25 UTC.
"Script generated via LOCAL LLM" in broadcast_service.log.

## WHAT IT DOES
Generates 2-3 sentence spoken broadcast scripts for the Stage anchor (Eryn)
for 7 segment types: PRICE_ALERT, THOUGHT_LEADER, SPACE_TAP, ARTICLE_TEASER,
METRICS_PULSE, NOSTR_SIGNAL, FILLER_INSIGHT.
Fires every 5 minutes via cron. ~288 potential script calls/day.

## MODEL CHAIN
PRIMARY:  Qwen3-Coder:30b via Ollama at http://localhost:11435 (GPU 2, free)
FALLBACK: Claude Haiku API (only when Ollama down or times out)
TIMEOUT:  25 seconds for local, 10 seconds for API

## FILES
Service:  ~/protocol_pulse/services/stage_broadcast_service.py
Config:   LOCAL_LLM_URL = "http://localhost:11435" (line 41)
Model:    LOCAL_LLM_MODEL = "qwen3-coder:30b" (line 42)
Log:      ~/protocol_pulse/logs/broadcast_service.log

## VOICE CONTRACT (non-negotiable)
- Eryn: calm authority, data-driven, sovereign Bitcoin perspective
- 2-3 sentences only. Present tense.
- No markdown. No hashtags. No em dashes.
- End with forward signal (what to watch), not a summary

## QUALITY GATE
Output rejected if:
- Length < 30 characters
- Contains markdown (# or ** or -)
- Starts with "I " or "As an AI"
On rejection: fall back to API, log "LOCAL_REJECTED: {reason}"

## COST SAVINGS
Before: ~288 Claude Haiku calls/day = ~$0.26/day
After:  $0.00/day (local inference)
Annual saving: ~$95

## MONITORING
Check local path is firing:
  grep "LOCAL LLM\|LOCAL_REJECTED\|fallback" ~/protocol_pulse/logs/broadcast_service.log | tail -20

## WHAT NEVER CHANGES
- Fallback to API must always exist — never hard-fail on Ollama outage
- Segment types and queue schema are frozen — do not add types without updating STAGE_BROADCAST_GOSPEL.md
- Cron frequency: */2 * * * * (every 2 minutes)
