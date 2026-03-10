"""
Market Briefing Room — Briefing Service (F2) — Second Pass

P0-1: Idempotency check before inserting (same type + ET date)
P0-2: Single final DB commit — no intermediate commits
P0-3: Cost guard counts 'failed' status rows
P0-4: HeyGen generate accepts 200/201/202
P0-5: HeyGen API version constants — v2 for generate, v1 for poll (per HeyGen docs)
P1-4: Mempool stats + network data added to script inputs
P1-5: asia_data wired into pre_market prompt template
Unique-7: Word count check post Claude generation
P2-1: BTC price fallback to None (not 0.0)
"""

import logging
import os
import time
from datetime import datetime, timedelta, date

import pytz
import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# HeyGen API version constants (P0-5)
# HeyGen uses v2 for generation and v1 for status polling — this is documented.
# Both constants are pinned here so any future version bump is a one-line change.
# ---------------------------------------------------------------------------
HEYGEN_GENERATE_URL = "https://api.heygen.com/v2/video/generate"
HEYGEN_STATUS_URL   = "https://api.heygen.com/v1/video_status.get"

SARAH_AVATAR_ID = "d259c335741f4fc0b061e04c59388b4e"
SARAH_VOICE_ID  = "5f745b3db0db43739f31499f4f0aedd6"   # Claire Lawson — Broadcaster

HEYGEN_POLL_INTERVAL   = 10    # seconds between status checks
HEYGEN_POLL_TIMEOUT    = 300   # seconds before giving up
HEYGEN_MAX_RETRIES     = 2     # LAW 2: max 2 API attempts per briefing
COST_GUARD_WINDOW_HOURS = 1
COST_GUARD_MAX_PER_WINDOW = 3
SCRIPT_MAX_WORDS = 180         # LAW 5 cap (90s at ~120 WPM)

ET = pytz.timezone("America/New_York")

BRIEFING_TITLES = {
    'pre_market': 'Pre-Market Brief',
    'open': 'Market Open Brief',
    'close': 'Market Close Brief',
}

# ---------------------------------------------------------------------------
# Script prompts — Claude generates at runtime (LAW 5) — P1-5: asia_data wired
# ---------------------------------------------------------------------------

SCRIPT_PROMPTS = {
    'pre_market': (
        "You are Sarah, Protocol Pulse's market intelligence host.\n"
        "Generate a 90-second pre-market Bitcoin briefing. Maximum 180 words.\n"
        "Current BTC price: ${btc_price}\n"
        "Overnight Bitcoin developments: {top_headlines}\n"
        "Mempool status: {mempool_stats}\n"
        "Asian market session: {asia_data}\n\n"
        "Rules:\n"
        "- Open with the most important overnight development\n"
        "- State BTC price and overnight move\n"
        "- One forward-looking insight for the US session\n"
        "- Close with: \"Stay sovereign. I'm Sarah for Protocol Pulse.\"\n"
        "- No em dashes. No ellipses. No markdown. Plain spoken English.\n"
        "- Never mention competitor media outlets by name.\n"
        "- Output ONLY the spoken script. No stage directions. No brackets."
    ),
    'open': (
        "You are Sarah, Protocol Pulse's market intelligence host.\n"
        "Generate a 90-second market-open Bitcoin briefing. Maximum 180 words.\n"
        "Current BTC price: ${btc_price}\n"
        "Key developments this morning: {top_headlines}\n"
        "Mempool status: {mempool_stats}\n\n"
        "Rules:\n"
        "- Open with the single most important thing traders need to know right now\n"
        "- State the BTC price and whether it is holding key levels\n"
        "- Name one catalyst or risk event to watch during today's session\n"
        "- Close with: \"Stay sovereign. I'm Sarah for Protocol Pulse.\"\n"
        "- No em dashes. No ellipses. No markdown. Plain spoken English.\n"
        "- Never mention competitor media outlets by name.\n"
        "- Output ONLY the spoken script. No stage directions. No brackets."
    ),
    'close': (
        "You are Sarah, Protocol Pulse's market intelligence host.\n"
        "Generate a 90-second market-close Bitcoin briefing. Maximum 180 words.\n"
        "Today's BTC closing price: ${btc_price}\n"
        "Today's key developments: {top_headlines}\n"
        "Mempool status: {mempool_stats}\n\n"
        "Rules:\n"
        "- Open with a one-sentence summary of today's most important event\n"
        "- State the BTC closing price and what it means for the overall trend\n"
        "- One insight about what this means for Bitcoin going forward\n"
        "- Close with: \"Stay sovereign. I'm Sarah for Protocol Pulse.\"\n"
        "- No em dashes. No ellipses. No markdown. Plain spoken English.\n"
        "- Never mention competitor media outlets by name.\n"
        "- Output ONLY the spoken script. No stage directions. No brackets."
    ),
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _heygen_headers():
    key = os.environ.get("HEYGEN_API_KEY", "")
    return {
        "X-Api-Key": key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _get_btc_price():
    """Fetch live BTC price from Mempool.space with CoinGecko fallback.
    Returns float or None (P2-1: no fake 0.0 fallback).
    """
    try:
        resp = requests.get("https://mempool.space/api/v1/prices", timeout=5)
        if resp.status_code == 200:
            price = resp.json().get("USD")
            if price:
                return float(price)
    except Exception as exc:
        logger.warning("Mempool BTC price failed: %s", exc)
    try:
        resp = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": "bitcoin", "vs_currencies": "usd"},
            timeout=5,
        )
        if resp.status_code == 200:
            price = resp.json().get("bitcoin", {}).get("usd")
            if price:
                return float(price)
    except Exception as exc:
        logger.warning("CoinGecko BTC price fallback failed: %s", exc)
    logger.warning("BTC price unavailable from all sources")
    return None  # P2-1: return None, not 0.0


def _get_mempool_stats() -> str:
    """Fetch mempool congestion stats from Mempool.space (P1-4).
    Returns human-readable string for Claude prompt.
    """
    try:
        resp = requests.get("https://mempool.space/api/mempool", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            count = data.get("count", "unknown")
            vsize = data.get("vsize", 0)
            vsize_mb = round(vsize / 1_000_000, 1) if vsize else "unknown"
            # Fee rate from fee estimates
            fee_resp = requests.get(
                "https://mempool.space/api/v1/fees/recommended", timeout=5
            )
            fee_str = ""
            if fee_resp.status_code == 200:
                fees = fee_resp.json()
                fastest = fees.get("fastestFee", "?")
                fee_str = f", fastest fee {fastest} sat/vB"
            return (
                f"{count:,} unconfirmed transactions, {vsize_mb} MB backlog{fee_str}"
                if isinstance(count, int)
                else f"Mempool size: {vsize_mb} MB{fee_str}"
            )
    except Exception as exc:
        logger.warning("Mempool stats fetch failed: %s", exc)
    return "Mempool data unavailable"


def _get_network_data() -> str:
    """Fetch Bitcoin network stats (hashrate/difficulty) for Asia session context (P1-4)."""
    try:
        resp = requests.get(
            "https://mempool.space/api/v1/difficulty-adjustment", timeout=5
        )
        if resp.status_code == 200:
            data = resp.json()
            change_pct = data.get("difficultyChange", 0)
            blocks_remaining = data.get("remainingBlocks", "?")
            sign = "+" if change_pct >= 0 else ""
            return (
                f"Difficulty adjustment: {sign}{change_pct:.1f}% expected, "
                f"{blocks_remaining} blocks remaining in epoch"
            )
    except Exception as exc:
        logger.warning("Network data fetch failed: %s", exc)
    return "Network data unavailable"


def _get_top_headlines(limit: int = 3) -> str:
    """Pull recent published article titles from DB for context."""
    try:
        import models
        from app import app
        with app.app_context():
            articles = (
                models.Article.query
                .filter_by(published=True)
                .order_by(models.Article.created_at.desc())
                .limit(limit)
                .all()
            )
            if articles:
                return "; ".join(a.title for a in articles)
    except Exception as exc:
        logger.warning("Headline fetch failed: %s", exc)
    return "No recent headlines available."


def _generate_script(
    briefing_type: str,
    btc_price,
    headlines: str,
    mempool_stats: str,
    asia_data: str,
) -> str:
    """Call Claude API to generate spoken briefing script (LAW 5).

    Unique-7: word count enforced post-generation.
    """
    import anthropic

    prompt_template = SCRIPT_PROMPTS.get(briefing_type, SCRIPT_PROMPTS['open'])
    price_str = f"{btc_price:,.0f}" if btc_price is not None else "unavailable"

    prompt = prompt_template.format(
        btc_price=price_str,
        top_headlines=headlines,
        mempool_stats=mempool_stats,
        asia_data=asia_data,
    )

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=450,
        messages=[{"role": "user", "content": prompt}],
    )
    script = message.content[0].text.strip()

    # Enforce no em-dashes or ellipses per LAW 5
    script = script.replace("\u2014", ",").replace("\u2013", "-").replace("...", ".")

    # Unique-7: word count check
    word_count = len(script.split())
    if word_count > SCRIPT_MAX_WORDS:
        logger.warning(
            "Script exceeds %d words (%d words) — truncating at sentence boundary",
            SCRIPT_MAX_WORDS, word_count,
        )
        words = script.split()
        truncated = " ".join(words[:SCRIPT_MAX_WORDS])
        # Find last sentence boundary
        for punct in ('. ', '! ', '? '):
            last = truncated.rfind(punct)
            if last > 0:
                truncated = truncated[:last + 1]
                break
        script = truncated

    return script


def _heygen_generate(script: str, title: str) -> dict:
    """Submit video generation request to HeyGen.
    P0-4: Accept 200, 201, 202 as success.
    """
    payload = {
        "video_inputs": [
            {
                "character": {
                    "type": "avatar",
                    "avatar_id": SARAH_AVATAR_ID,
                    "avatar_style": "normal",
                },
                "voice": {
                    "type": "text",
                    "input_text": script,
                    "voice_id": SARAH_VOICE_ID,
                },
                "background": {
                    "type": "color",
                    "value": "#0a0a0a",
                },
            }
        ],
        "dimension": {"width": 1280, "height": 720},
        "aspect_ratio": "16:9",
        "title": title,
    }
    try:
        resp = requests.post(
            HEYGEN_GENERATE_URL,
            headers=_heygen_headers(),
            json=payload,
            timeout=30,
        )
        logger.debug("HeyGen generate response: %s", resp.status_code)
        # P0-4: accept 200, 201, 202
        if resp.status_code in (200, 201, 202):
            data = resp.json()
            video_id = data.get("data", {}).get("video_id")
            if video_id:
                return {"video_id": video_id}
            logger.error("HeyGen %s but no video_id in response: %s", resp.status_code, resp.text[:200])
        else:
            logger.error("HeyGen generate error %s: %s", resp.status_code, resp.text[:300])
    except Exception as exc:
        logger.error("HeyGen generate request failed: %s", exc)
    return {"error": "HeyGen generation failed"}


def _heygen_poll(video_id: str) -> dict:
    """Poll HeyGen until complete or timeout. Returns status dict."""
    deadline = time.time() + HEYGEN_POLL_TIMEOUT
    while time.time() < deadline:
        try:
            resp = requests.get(
                HEYGEN_STATUS_URL,
                headers=_heygen_headers(),
                params={"video_id": video_id},
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                status = data.get("status", "unknown")
                if status == "completed":
                    return {
                        "status": "completed",
                        "video_url": data.get("video_url"),
                        "thumbnail_url": data.get("thumbnail_url"),
                        "duration": data.get("duration"),
                    }
                elif status == "failed":
                    return {"status": "failed", "error": str(data)}
        except Exception as exc:
            logger.warning("HeyGen poll request error: %s", exc)
        time.sleep(HEYGEN_POLL_INTERVAL)
    return {"status": "timeout"}


def _get_et_date_str() -> str:
    """Return today's date in ET as YYYY-MM-DD string for idempotency key."""
    return datetime.now(ET).strftime("%Y-%m-%d")


def _check_cost_guard() -> bool:
    """Return True if within cost guard limits (max 3 video attempts/hour).
    P0-3: includes 'failed' in status filter — failed attempts consumed paid API calls.
    """
    try:
        import models
        from app import app
        with app.app_context():
            cutoff = datetime.utcnow() - timedelta(hours=COST_GUARD_WINDOW_HOURS)
            recent_count = (
                models.MarketBriefing.query
                .filter(
                    models.MarketBriefing.generated_at >= cutoff,
                    models.MarketBriefing.status.in_(
                        ['generating', 'completed', 'failed']  # P0-3: include failed
                    ),
                )
                .count()
            )
            if recent_count >= COST_GUARD_MAX_PER_WINDOW:
                logger.warning(
                    "COST GUARD: %d briefing attempts in last %dh — pausing",
                    recent_count, COST_GUARD_WINDOW_HOURS,
                )
                return False
    except Exception as exc:
        logger.warning("Cost guard check failed (allowing generation): %s", exc)
    return True


def _idempotency_check(briefing_type: str, et_date: str) -> bool:
    """P0-1: Return True if a non-failed briefing already exists for this slot+date.
    Caller should abort if True.
    """
    try:
        import models
        from app import app
        with app.app_context():
            existing = (
                models.MarketBriefing.query
                .filter(
                    models.MarketBriefing.briefing_type == briefing_type,
                    models.MarketBriefing.scheduled_date == et_date,
                    models.MarketBriefing.status.in_(['generating', 'completed']),
                )
                .first()
            )
            if existing:
                logger.info(
                    "Idempotency: briefing %s for %s already exists (id=%d, status=%s)",
                    briefing_type, et_date, existing.id, existing.status,
                )
                return True
    except Exception as exc:
        logger.warning("Idempotency check failed (proceeding): %s", exc)
    return False


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------

def generate_briefing(briefing_type: str) -> dict:
    """
    Full briefing generation pipeline.

    P0-2: Single final DB commit — no intermediate commits.
    P0-1: Idempotency check before insert.
    P0-3: Cost guard counts failed rows.
    """
    if briefing_type not in SCRIPT_PROMPTS:
        return {"success": False, "error": f"Unknown briefing_type: {briefing_type}"}

    et_date = _get_et_date_str()

    # P0-1: Idempotency
    if _idempotency_check(briefing_type, et_date):
        return {
            "success": False,
            "error": f"Briefing {briefing_type} for {et_date} already generating/completed",
        }

    # Cost guard (P0-3: counts failed too)
    if not _check_cost_guard():
        return {"success": False, "error": "Cost guard limit reached — max 3 attempts/hour"}

    import models
    from app import app, db

    today_label = datetime.now(ET).strftime("%b %-d, %Y")
    title = f"{BRIEFING_TITLES.get(briefing_type, 'Briefing')} — {today_label}"

    with app.app_context():
        # Create initial pending record — P0-2: this is the ONLY db.session.add
        briefing = models.MarketBriefing(
            title=title,
            briefing_type=briefing_type,
            scheduled_date=et_date,
            script_text="",
            status="pending",
            published=False,
        )
        try:
            db.session.add(briefing)
            db.session.flush()          # get briefing.id without committing
            briefing_id = briefing.id
        except Exception as exc:
            db.session.rollback()
            logger.error("DB initial flush failed: %s", exc)
            return {"success": False, "error": str(exc)}

        # -------------------------------------------------------------------
        # P0-2: All pipeline work runs here. ONE commit at end. ONE rollback on fail.
        # -------------------------------------------------------------------
        try:
            # Step 1: Fetch live data
            btc_price = _get_btc_price()
            mempool_stats = _get_mempool_stats()
            headlines = _get_top_headlines()
            asia_data = _get_network_data()      # P1-5: wired into pre_market prompt

            briefing.btc_price_at_generation = btc_price
            briefing.status = "generating"

            # Step 2: Generate script via Claude
            script = _generate_script(
                briefing_type, btc_price, headlines, mempool_stats, asia_data
            )
            briefing.script_text = script

            # Step 3: HeyGen — up to HEYGEN_MAX_RETRIES (LAW 2)
            heygen_result = None
            for attempt in range(1, HEYGEN_MAX_RETRIES + 1):
                logger.info(
                    "HeyGen attempt %d/%d for briefing %d",
                    attempt, HEYGEN_MAX_RETRIES, briefing_id,
                )
                gen_result = _heygen_generate(script, title)
                if "error" not in gen_result:
                    heygen_result = gen_result
                    break
                if attempt < HEYGEN_MAX_RETRIES:
                    time.sleep(5)

            if not heygen_result:
                raise RuntimeError("HeyGen generation failed after max retries")

            briefing.heygen_video_id = heygen_result["video_id"]

            # Step 4: Poll for completion
            poll_result = _heygen_poll(heygen_result["video_id"])
            if poll_result.get("status") != "completed":
                raise RuntimeError(
                    f"HeyGen poll result: {poll_result.get('status')} — "
                    f"{poll_result.get('error', '')}"
                )

            # Step 5: Finalize — P0-2: SINGLE commit here
            briefing.video_url = poll_result.get("video_url")
            briefing.thumbnail_url = poll_result.get("thumbnail_url")
            briefing.duration_seconds = poll_result.get("duration")
            briefing.status = "completed"
            briefing.published = True
            briefing.published_at = datetime.utcnow()

            db.session.commit()         # THE ONLY COMMIT

            logger.info(
                "Briefing %d (%s) completed — video: %s",
                briefing_id, briefing_type, briefing.video_url,
            )
            return {
                "success": True,
                "briefing_id": briefing_id,
                "video_url": briefing.video_url,
                "duration_seconds": briefing.duration_seconds,
            }

        except Exception as exc:
            # P0-2: single rollback path
            briefing.status = "failed"
            briefing.error_message = str(exc)[:500]
            try:
                db.session.commit()     # persist the failure record
            except Exception as commit_exc:
                db.session.rollback()
                logger.error("Failed to persist failure record: %s", commit_exc)
            logger.error("Briefing %d (%s) failed: %s", briefing_id, briefing_type, exc)
            return {"success": False, "briefing_id": briefing_id, "error": str(exc)}
