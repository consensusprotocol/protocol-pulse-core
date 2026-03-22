Read ~/protocol_pulse/PIPELINE_LAWS.md first. Then read ~/protocol_pulse/services/content_generator.py lines 1080-1120 (the validate_article_for_publish function).

TASK: Wire the local Qwen3-Coder LLM as an article quality gate before any article is published. A fact_checker service already exists but uses external APIs. We want a LOCAL quality gate that runs on every article using Ollama on port 11435.

LOCAL LLM: http://localhost:11435, model qwen3-coder:30b (already running on GPU 2)
TARGET: ~/protocol_pulse/services/article_quality_gate.py (NEW FILE)
INTEGRATION POINT: ~/protocol_pulse/services/automation.py line ~268 where art.published = True

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 1 — UNDERSTAND THE PUBLISH FLOW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Read ~/protocol_pulse/services/automation.py lines 220-290.
Identify exactly where art.published = True is set.
This is the insertion point for the quality gate.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 2 — BUILD article_quality_gate.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Create ~/protocol_pulse/services/article_quality_gate.py

The gate must check every article against these rules via local Qwen:

RULE 1 — FACTUAL CLAIMS (most important)
  Scan for specific numbers/statistics. Flag any that are:
  - BTC price claims outside $50k-$200k range (current realistic range)
  - Hashrate claims outside 500-2000 EH/s range
  - Percentage claims over 1000% or under -99%
  - Named people saying things they likely never said

RULE 2 — CONTENT QUALITY
  Flag if article:
  - Is under 200 words
  - Contains "As an AI language model" or similar AI tells
  - Has more than 3 consecutive sentences starting with "Bitcoin"
  - Contains hashtags (#)
  - Contains broken links or [PLACEHOLDER] text

RULE 3 — BITCOIN ALIGNMENT
  Flag if article:
  - Promotes altcoins as superior to Bitcoin
  - Uses "crypto" as primary framing (not Bitcoin-native)
  - Contains obvious price prediction hype ("will reach $1M by...")

GATE FUNCTION:
def check_article(title: str, content: str, summary: str = "") -> dict:
    """
    Returns: {
        "approved": bool,
        "score": int (0-100),
        "flags": list[str],
        "source": "local_llm" | "fallback_approve"
    }
    """
    # Build prompt for local Qwen
    prompt = f"""You are a Bitcoin journalism quality auditor for Protocol Pulse.
Review this article and return ONLY valid JSON. No markdown.

ARTICLE TITLE: {title}
ARTICLE CONTENT (first 1500 chars): {content[:1500]}

Check for:
1. Factual impossibilities (BTC price outside $50k-$200k, hashrate outside 500-2000 EH/s)
2. AI generation tells ("As an AI", "[PLACEHOLDER]", excessive repetition)
3. Altcoin promotion or anti-Bitcoin framing
4. Broken or placeholder content
5. Overall quality score

Return exactly:
{{"approved": true/false, "score": 0-100, "flags": ["list of issues found or empty"]}}

If article is acceptable Bitcoin content with no major issues, approved=true, score 70-100.
If article has factual impossibilities or AI tells, approved=false."""

    try:
        import requests
        resp = requests.post("http://localhost:11435/api/chat", json={
            "model": "qwen3-coder:30b",
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": 0.1}  # Low temp for consistent gating
        }, timeout=30)
        resp.raise_for_status()
        raw = resp.json().get("message", {}).get("content", "")
        # Parse JSON from response
        import re, json
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            result = json.loads(match.group())
            result["source"] = "local_llm"
            return result
    except Exception as e:
        logging.warning(f"Article quality gate failed: {e} — auto-approving")

    # Fallback: approve if local LLM unavailable (never block publishing due to gate failure)
    return {"approved": True, "score": 75, "flags": [], "source": "fallback_approve"}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 3 — WIRE INTO AUTOMATION.PY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
In automation.py, find where art.published = True is set (around line 268).

Before that line, add:
    # Local LLM quality gate
    from services.article_quality_gate import check_article
    gate_result = check_article(art.title or "", art.content or "", art.summary or "")
    if not gate_result["approved"]:
        logging.warning(f"QUALITY GATE BLOCKED article {art.id}: score={gate_result['score']} flags={gate_result['flags']}")
        art.published = False
        art.tags = (art.tags or "") + " [QUALITY_GATE_BLOCKED]"
        db.session.commit()
        continue  # Skip to next article
    else:
        logging.info(f"QUALITY GATE PASSED article {art.id}: score={gate_result['score']} source={gate_result['source']}")

CRITICAL: The gate must NEVER block publishing if the local LLM is unavailable.
The fallback_approve ensures articles always publish if Qwen is down.
Gate failure = silent approval, never a hard block.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 4 — TEST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Test gate directly:
python3 -c "
from services.article_quality_gate import check_article
# Test 1: Good article
r = check_article('Bitcoin Hashrate Hits Record 950 EH/s', 'Bitcoin network hashrate reached 950 EH/s today as miners...')
print('GOOD:', r)
# Test 2: Bad article
r = check_article('Bitcoin will hit 10 million dollars', 'As an AI language model, Bitcoin price will reach $10,000,000 by tomorrow...')
print('BAD:', r)
"

Both should return JSON. Good article: approved=True. Bad article: approved=False.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 5 — ADD SCORE TO ARTICLE MODEL (optional if column exists)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Check if Article model has a quality_score column:
python3 -c "from models import Article; print([c.name for c in Article.__table__.columns])"

If quality_score column exists: save gate_result["score"] to art.quality_score
If not: skip this step, log only

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMMIT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
git add services/article_quality_gate.py services/automation.py
git commit -m "feat(articles): local LLM quality gate — Qwen3-Coder reviews every article before publish, blocks AI tells + factual impossibilities, auto-approves on gate failure"
git push

DO NOT touch: assembler.py, tts_engine.py, routes.py, overnight_render_loop.py, models.py
IMPORTANT SPEC UPDATE: REAL-TIME CONTEXT INJECTION
The local Qwen has NO real-time data. Inject today's BTC price from morning brief.

In check_article(), before building prompt, load brief:
    from pathlib import Path
    brief_path = Path("/home/ultron/protocol_pulse/data/intelligence/morning_intelligence_brief.json")
    today_btc, today_fng = "unknown", "unknown"
    try:
        import json as _j
        brief = _j.loads(brief_path.read_text())
        today_btc = brief.get("btc_price", "unknown")
        today_fng = brief.get("fng", "unknown")
    except Exception:
        pass

Add to prompt:
    f"TODAY'S KNOWN DATA (validate claims against this):\n"
    f"  BTC Price: {today_btc}\n  Fear & Greed: {today_fng}\n"
    f"  BTC price claims deviating >20% from above are suspicious.\n\n"

WHAT GATE CHECKS: AI tells, BTC price vs today's known, hashrate range, altcoin promo, broken content.
WHAT IT DOES NOT CHECK: specific on-chain stats, named quotes, breaking news accuracy.
