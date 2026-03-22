# GOSPEL: SUBSTACK DIGEST LOCAL LLM
# Version 1.0 | March 2026 | Status: NEEDS AUDIT ⚠️

## CURRENT STATE
substack_daily_digest.py queries published articles from DB directly.
No direct LLM call found in the file — it may use template-based generation
or call through a shared service. Run forensic audit before building.

AUDIT COMMAND:
  python3 ~/protocol_pulse/services/substack_daily_digest.py 2>&1 | head -30
  grep -n "call\|generate\|llm\|api\|model" ~/protocol_pulse/services/substack_daily_digest.py

## WHAT IT SHOULD DO
Generate a daily Substack digest email that:
1. Selects 3-5 top articles from today (by read_count + quality_score)
2. Writes a 2-sentence editorial summary for each article
3. Adds an opening paragraph with today's dominant narrative
4. Adds a closing line from PBX perspective
5. Publishes via Substack API (already wired)

## MODEL (target state)
PRIMARY:  Qwen3-Coder:30b via Ollama port 11435 (local, free)
FALLBACK: Claude Sonnet if Ollama down
WHEN:     Daily at 5pm ET cron

## DIGEST STRUCTURE (frozen schema)
Opening:  1 paragraph, today's dominant narrative from morning brief
Articles: 3-5 articles, each with title + 2-sentence editorial summary
Closing:  1 sentence PBX sign-off. Always ends with "Stay sovereign."
CTA:      Link to protocolpulse.io

## VOICE FOR SUMMARIES
- Written as if PBX summarized it for you
- No marketing language
- One specific data point per summary
- Present tense
- No hashtags. No emoji.

## FILES
Service: ~/protocol_pulse/services/substack_daily_digest.py
Cron:    0 21 * * * (5pm ET = 21:00 UTC)
Log:     ~/protocol_pulse/logs/substack_digest.log

## QUALITY GATE (before publish)
- Minimum 3 articles selected (if fewer available: skip digest that day)
- Opening paragraph > 50 words
- Each summary > 30 words
- No [PLACEHOLDER] text
- No hallucinated article titles (verify against DB)

## WHAT NEVER CHANGES
- Substack API credentials stay in .env, never hardcoded
- Never publish digest if no articles were published today
- Always include protocolpulse.io link
- Closing line always includes "Stay sovereign"
