Read ~/protocol_pulse/PIPELINE_LAWS.md first.
Read ~/protocol_pulse/docs/gospels/MORNING_BRIEF_LOCAL_LLM_GOSPEL.md.

TASK: Migrate morning_brief.py from Claude Haiku API to local Qwen3-Coder:30b.
This is a structured data synthesis task — input is raw JSON signals, 
output is a structured JSON brief. Perfect for Qwen. Zero quality risk.

FILE: ~/protocol_pulse/services/morning_brief.py
LOCAL LLM: http://localhost:11435, model qwen3-coder:30b
FALLBACK: Claude Haiku (existing call_claude_haiku() — keep intact)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INVESTIGATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Read ~/protocol_pulse/services/morning_brief.py in full.
Understand: build_prompt(), call_claude_haiku(), main() flow.
Note the exact JSON output schema — it must be preserved exactly.
The schema has these required fields: generated_at, date, btc_price, btc_change_24h,
fng, dominant_narratives, trending_language, sentiment, sentiment_reasoning,
top_accounts_active, recommended_tweet_angles, topics_to_avoid,
engagement_patterns, protocol_pulse_voice_guidance, key_stats_today

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CHANGE REQUIRED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Add new function call_local_llm(prompt: str) -> dict:
    """Call local Qwen3 via Ollama. Returns parsed brief dict or empty dict."""
    import requests, re
    try:
        resp = requests.post("http://localhost:11435/api/chat", json={
            "model": "qwen3-coder:30b",
            "messages": [
                {"role": "system", "content": "You are a Bitcoin intelligence analyst. Return ONLY valid JSON. No markdown. No preamble. No explanation."},
                {"role": "user", "content": prompt}
            ],
            "stream": False,
            "options": {"temperature": 0.3}
        }, timeout=60)
        resp.raise_for_status()
        raw = resp.json().get("message", {}).get("content", "")
        raw = raw.strip()
        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = re.sub(r"^```[a-z]*\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)
        result = json.loads(raw.strip())
        logger.info("Brief generated via LOCAL LLM")
        return result
    except Exception as e:
        logger.warning(f"Local LLM brief failed: {e}")
        return {}

Modify main() to:
    # Try local first
    logger.info("Calling local Qwen3...")
    brief = call_local_llm(prompt)
    
    # Validate required fields
    required = ["dominant_narratives", "trending_language", "sentiment", "recommended_tweet_angles"]
    if not brief or not all(k in brief for k in required):
        logger.warning("Local brief incomplete, falling back to Claude Haiku")
        brief = call_claude_haiku(prompt)
    
    # Tag which model generated it
    if brief:
        brief["generated_by"] = "local_llm" if brief.get("dominant_narratives") else "claude_haiku"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TEST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
python3 ~/protocol_pulse/services/morning_brief.py
cat ~/protocol_pulse/data/intelligence/morning_intelligence_brief.json | python3 -m json.tool | head -30
Verify: all required fields present, generated_by = "local_llm", valid JSON.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMMIT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
git add services/morning_brief.py
git commit -m "feat(morning_brief): local Qwen3 primary, Claude Haiku fallback, generated_by field tracking"
git push

DO NOT touch: tweet_machine.py, image_of_the_day.py, routes.py, oracle_briefing/