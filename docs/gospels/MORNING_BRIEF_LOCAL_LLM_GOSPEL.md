# GOSPEL: MORNING BRIEF LOCAL LLM
# Version 1.0 | March 2026 | Status: NOT MIGRATED ❌

## CURRENT STATE
morning_brief.py calls claude-haiku-4-5-20251001.
Runs twice daily: 6am ET (morning_brief_cron) + 4pm ET (noon_brief_cron).
Each run: 1 API call, ~2000 tokens in, ~800 tokens out.
Cost: ~$0.004/run × 2 = ~$0.008/day. Small but unnecessary.

## WHAT IT DOES
Synthesizes raw intelligence (BTC price, FNG, hashrate, Nitter tweets,
Nostr signals, macro headlines) into a structured morning_intelligence_brief.json.
This brief drives: tweet_machine, stage_broadcast, article generation angles.
It is the daily intelligence heartbeat of the entire platform.

## MODEL MIGRATION
FROM: claude-haiku-4-5-20251001 (API)
TO:   Qwen3-Coder:30b via Ollama port 11435 (local, free)
FALLBACK: Claude Haiku API if Ollama unavailable

## FILES
Service: ~/protocol_pulse/services/morning_brief.py
Output:  ~/protocol_pulse/data/intelligence/morning_intelligence_brief.json
Crons:   0 10 * * * (6am ET), 0 20 * * * (4pm ET)

## OUTPUT SCHEMA (must remain identical after migration)
{
  "generated_at": ISO timestamp,
  "date": "Day, Month DD, YYYY",
  "btc_price": "$XX,XXX",
  "btc_change_24h": "X.XX%",
  "fng": "Sentiment (score/100)",
  "dominant_narratives": [list of 3 strings],
  "trending_language": [list of 6-8 phrases],
  "top_tweets": [list of tweet objects],
  "macro_context": string,
  "signal_summary": string,
  "sentiment": "bullish|bearish|uncertain|neutral"
}
Schema is frozen — downstream services depend on exact field names.

## MIGRATION RULES
1. Same prompt, same output schema — only the API endpoint changes
2. Add output validation: if any required field missing → retry once → API fallback
3. Log which model generated each brief: brief["generated_by"] = "local_llm" | "claude_haiku"
4. If brief.json is older than 8 hours and Ollama is down: use stale brief + log warning

## QUALITY VALIDATION AFTER MIGRATION
Run both local and API versions on same input for 3 days.
Compare: narrative count, trending phrase quality, sentiment accuracy.
If local quality < API quality on any dimension: keep API for that field.

## WHAT NEVER CHANGES
- Output schema is frozen — never add or remove top-level fields without updating all consumers
- Never generate brief without real BTC price data (not estimated)
- Cron frequency must not change
