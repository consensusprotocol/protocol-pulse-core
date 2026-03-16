"""
Oracle Intelligence Feed — reads live pipeline data + articles, generates briefing via Claude.
Renders briefing video through avatar_server /generate endpoint.
"""
import os, json, time, sqlite3, logging, threading, re, subprocess
from datetime import datetime, timedelta

logger = logging.getLogger("oracle_intelligence_feed")

ORACLE_DIR   = os.path.dirname(os.path.abspath(__file__))
DB_PATH      = os.path.join(ORACLE_DIR, "..", "instance", "protocol_pulse.db")
PIPELINE_DIR = os.path.join(ORACLE_DIR, "..", "video_pipeline_v3", "data", "intelligence")
DATA_DIR     = os.path.join(ORACLE_DIR, "..", "data", "intelligence")
CACHE_DIR    = os.path.join(ORACLE_DIR, "cache")
RESPONSES_DIR= os.path.join(CACHE_DIR, "responses")
BRIEF_PATH   = os.path.join(RESPONSES_DIR, "DAILY_BRIEF_LIVE.mp4")
RENDER_HELPER= os.path.join(ORACLE_DIR, "cache_render_helper.py")
REFRESH_INTERVAL = 3600  # 1 hour


# ── NUMBER NORMALIZER ──────────────────────────────────────────────────────
# ElevenLabs chokes on raw numbers. Convert everything to spoken English first.

def _num_to_words(n):
    """Convert integer to English words. Handles 0-999,999,999."""
    if n < 0: return "negative " + _num_to_words(-n)
    if n == 0: return "zero"
    ones = ["","one","two","three","four","five","six","seven","eight","nine",
            "ten","eleven","twelve","thirteen","fourteen","fifteen","sixteen",
            "seventeen","eighteen","nineteen"]
    tens = ["","","twenty","thirty","forty","fifty","sixty","seventy","eighty","ninety"]
    if n < 20: return ones[n]
    if n < 100: return tens[n//10] + ("" if n%10==0 else "-"+ones[n%10])
    if n < 1000:
        rest = n % 100
        return ones[n//100] + " hundred" + ("" if rest==0 else " " + _num_to_words(rest))
    if n < 1_000_000:
        t = n // 1000; r = n % 1000
        return _num_to_words(t) + " thousand" + ("" if r==0 else " " + _num_to_words(r))
    if n < 1_000_000_000:
        t = n // 1_000_000; r = n % 1_000_000
        return _num_to_words(t) + " million" + ("" if r==0 else " " + _num_to_words(r))
    t = n // 1_000_000_000; r = n % 1_000_000_000
    return _num_to_words(t) + " billion" + ("" if r==0 else " " + _num_to_words(r))


def _float_to_words(s):
    """Turn '83421.50' -> 'eighty-three thousand four hundred twenty-one point five zero'"""
    parts = s.split(".")
    integer_part = _num_to_words(int(parts[0].replace(",","")))
    if len(parts) == 1 or all(c=="0" for c in parts[1]):
        return integer_part
    decimal_words = " ".join(_num_to_words(int(d)) for d in parts[1])
    return integer_part + " point " + decimal_words


def normalize_for_tts(text):
    """
    Convert numbers, prices, percentages, units to spoken English.
    This prevents ElevenLabs from mispronouncing raw numeric tokens.
    """
    # $1,234,567.89 -> "one million two hundred thirty-four thousand five hundred sixty-seven dollars"
    def replace_price(m):
        raw = m.group(1).replace(",","")
        try:
            val = float(raw)
            if val >= 1000:
                return _float_to_words(raw) + " dollars"
            else:
                return _float_to_words(raw) + " dollars"
        except: return m.group(0)
    text = re.sub(r"\$([\d,]+(?:\.\d+)?)", replace_price, text)

    # 83.5% -> "eighty-three point five percent"
    def replace_pct(m):
        try: return _float_to_words(m.group(1)) + " percent"
        except: return m.group(0)
    text = re.sub(r"([\d,]+(?:\.\d+)?)%", replace_pct, text)

    # 634 EH/s -> "six hundred thirty-four exahashes per second"
    text = re.sub(r"(\d+(?:\.\d+)?)\s*EH/s",
        lambda m: _float_to_words(m.group(1)) + " exahashes per second", text)
    text = re.sub(r"(\d+(?:\.\d+)?)\s*TH/s",
        lambda m: _float_to_words(m.group(1)) + " terahashes per second", text)
    text = re.sub(r"([\d,]+(?:\.\d+)?)\s*BTC",
        lambda m: _float_to_words(m.group(1).replace(",","")) + " Bitcoin", text)
    text = re.sub(r"(\d+(?:\.\d+)?)\s*sats",
        lambda m: _float_to_words(m.group(1)) + " satoshis", text)
    text = re.sub(r"(\d+(?:\.\d+)?)\s*[Kk]\b",
        lambda m: _float_to_words(str(int(float(m.group(1))*1000))) + "", text)

    # Remaining bare numbers >= 1000 with commas: 83,421 -> "eighty-three thousand..."
    def replace_large(m):
        raw = m.group(0).replace(",","")
        try:
            n = int(raw)
            if n >= 1000: return _num_to_words(n)
            return m.group(0)
        except: return m.group(0)
    text = re.sub(r"\b\d{1,3}(?:,\d{3})+\b", replace_large, text)

    # 4-digit numbers: 2024 (years keep as-is), prices spell out
    # Simple bare integers 100-9999
    def replace_medium(m):
        raw = m.group(0)
        try:
            n = int(raw)
            # Don't convert years
            if 1900 <= n <= 2100: return raw
            if n >= 100: return _num_to_words(n)
            return raw
        except: return raw
    text = re.sub(r"\b(\d{3,4})\b", replace_medium, text)

    return text


# ── DATA SOURCES ───────────────────────────────────────────────────────────

def _get_anthropic_key():
    key = os.environ.get("ANTHROPIC_API_KEY","")
    if not key:
        env_path = os.path.join(ORACLE_DIR,"..","/.env")
        env_path2 = os.path.join(ORACLE_DIR,"..",".env")
        for ep in [env_path, env_path2]:
            if os.path.exists(ep):
                for line in open(ep):
                    if line.startswith("ANTHROPIC_API_KEY="):
                        key = line.strip().split("=",1)[1].strip().strip("\"'")
    return key


def _get_recent_articles(limit=5):
    if not os.path.exists(DB_PATH): return []
    cutoff = (datetime.utcnow() - timedelta(hours=72)).isoformat()
    try:
        conn = sqlite3.connect(DB_PATH, timeout=5)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT title, summary, published_at FROM articles "
            "WHERE published_at > ? ORDER BY published_at DESC LIMIT ?",
            (cutoff, limit)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"[INTEL] DB error: {e}")
        return []


def _get_pipeline_sentiment():
    """Read live sentiment + signals from video pipeline intelligence files."""
    result = {}
    for fname, key in [
        ("sentiment.json","sentiment"),
        ("live_signals.json","live_signals"),
        ("narrative_context.json","narrative"),
    ]:
        path = os.path.join(PIPELINE_DIR, fname)
        if os.path.exists(path):
            try:
                with open(path) as f:
                    result[key] = json.load(f)
            except: pass

    # Also read our own daily_signals
    ds_path = os.path.join(DATA_DIR, "daily_signals.json")
    if os.path.exists(ds_path):
        try:
            with open(ds_path) as f:
                result["daily_signals"] = json.load(f)
        except: pass

    return result


def _get_btc_price():
    """Fetch live BTC price from Coinbase."""
    import requests as _req
    try:
        r = _req.get("https://api.coinbase.com/v2/prices/BTC-USD/spot", timeout=5)
        if r.ok:
            raw = r.json()["data"]["amount"]
            # Parse and normalize
            price_float = float(raw)
            return price_float, normalize_for_tts(f"${raw}")
    except: pass
    return None, None


def _build_context_summary(articles, sentiment_data, price_float, price_spoken):
    """Build a structured context string for Claude."""
    lines = []

    if price_float:
        lines.append(f"BTC PRICE: {price_spoken}")

    # Pipeline sentiment
    sent = sentiment_data.get("sentiment",{}).get("data",{})
    if sent:
        overall = sent.get("overall",{})
        score = overall.get("score","?")
        label = overall.get("label","?")
        lines.append(f"MARKET SENTIMENT: {label} (score {score}/100)")
        breakdown = sent.get("breakdown",{})
        for k,v in breakdown.items():
            if isinstance(v,dict) and v.get("score"):
                lines.append(f"  {k}: {v.get('label','?')} ({v.get('score',0)})")

    # Narrative from pipeline
    narr = sentiment_data.get("narrative",{})
    if narr.get("episode_narrative"):
        lines.append(f"NARRATIVE: {narr['episode_narrative']}")

    # Daily signals
    daily = sentiment_data.get("daily_signals",{})
    topics = daily.get("topics",[])
    if topics:
        topic_strs = [f"{t['topic']} ({t['sentiment']}, velocity {t['velocity_score']})" for t in topics[:4]]
        lines.append(f"TRENDING TOPICS: {', '.join(topic_strs)}")

    # Live streams
    ls = sentiment_data.get("live_signals",{}).get("live_streams",[])
    if ls:
        lines.append(f"LIVE STREAMS: {len(ls)} active — {ls[0].get('title','')} on {ls[0].get('channel','')}")

    # Articles
    if articles:
        lines.append("RECENT HEADLINES:")
        for a in articles[:4]:
            title = a.get("title","")
            summ = a.get("summary","")[:80] if a.get("summary") else ""
            lines.append(f"  - {title}" + (f": {summ}" if summ else ""))

    return "\n".join(lines)


def _generate_briefing_text(articles, sentiment_data, price_float, price_spoken):
    """Call Claude Haiku to write the Oracle verbal briefing."""
    import requests
    api_key = _get_anthropic_key()
    if not api_key:
        logger.error("[INTEL] No ANTHROPIC_API_KEY")
        return None

    context = _build_context_summary(articles, sentiment_data, price_float, price_spoken)

    prompt = (
        "You are the Oracle, Protocol Pulse's Bitcoin intelligence AI. "
        "Write a 25-second verbal briefing (MAX 60 words) in first person based on this live data.\n"
        "RULES:\n"
        "- Write ALL numbers as words. Never use digits. Example: write 'eighty-three thousand dollars' not '$83,000'.\n"
        "- Write percentages as words: 'twenty-seven percent bearish' not '27% bearish'.\n"
        "- Direct, confident, no filler words. Sound like a human analyst.\n"
        "- End with ONE question to the viewer: ask if they want to go deeper on any topic.\n"
        "- Never use markdown. Plain sentences only.\n\n"
        f"LIVE DATA:\n{context}"
    )

    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": api_key, "anthropic-version":"2023-06-01","content-type":"application/json"},
        json={"model":"claude-haiku-4-5-20251001","max_tokens":180,
              "messages":[{"role":"user","content":prompt}]},
        timeout=30,
    )
    if resp.status_code != 200:
        logger.error(f"[INTEL] Claude error {resp.status_code}: {resp.text[:200]}")
        return None

    text = resp.json()["content"][0]["text"]
    # Final safety pass: normalize any digits Claude slipped through
    return normalize_for_tts(text)


def _get_fallback_briefing_text(price_float, price_spoken):
    today = datetime.utcnow().strftime("%B %d, %Y")
    price_str = price_spoken if price_spoken else "price data unavailable"
    return normalize_for_tts(
        f"Today is {today}. Bitcoin is currently trading at {price_str}. "
        "I am monitoring all on-chain signals, macro developments, and geopolitical events in real time. "
        "The network hashrate remains near all-time highs. "
        "Social sentiment is mixed across retail and institutional players. "
        "No major breaking events to report at this moment, but I am watching the feeds. "
        "Would you like me to go deeper on any specific area — price action, mining, or macro?"
    )


def _render_brief(text):
    os.makedirs(RESPONSES_DIR, exist_ok=True)
    try:
        logger.info(f"[INTEL] Rendering brief ({len(text)} chars)...")
        t0 = time.time()
        result = subprocess.run(
            ["python3", RENDER_HELPER, "--text", text, "--out", BRIEF_PATH],
            capture_output=True, text=True, timeout=180, cwd=ORACLE_DIR,
        )
        elapsed = time.time() - t0
        if result.returncode != 0:
            logger.error(f"[INTEL] Render failed: {result.stderr[-300:]}")
            return False
        logger.info(f"[INTEL] Brief rendered in {elapsed:.1f}s")
        return True
    except Exception as e:
        logger.error(f"[INTEL] Render error: {e}")
        return False


def refresh_daily_brief():
    price_float, price_spoken = _get_btc_price()
    articles = _get_recent_articles(5)
    sentiment_data = _get_pipeline_sentiment()

    logger.info(f"[INTEL] Refreshing — {len(articles)} articles, price={price_float}, sentiment keys={list(sentiment_data.keys())}")

    if articles or sentiment_data:
        text = _generate_briefing_text(articles, sentiment_data, price_float, price_spoken)
    else:
        text = None

    if not text:
        logger.warning("[INTEL] Using price fallback")
        text = _get_fallback_briefing_text(price_float, price_spoken)

    return _render_brief(text)


def get_daily_brief():
    if os.path.exists(BRIEF_PATH) and os.path.getsize(BRIEF_PATH) > 0:
        return BRIEF_PATH
    return None


def start_intelligence_feed():
    def _loop():
        try: refresh_daily_brief()
        except Exception as e: logger.error(f"[INTEL] Initial: {e}")
        while True:
            time.sleep(REFRESH_INTERVAL)
            try: refresh_daily_brief()
            except Exception as e: logger.error(f"[INTEL] Loop: {e}")

    t = threading.Thread(target=_loop, daemon=True)
    t.start()
    logger.info(f"[INTEL] Intelligence feed started (interval={REFRESH_INTERVAL}s)")
