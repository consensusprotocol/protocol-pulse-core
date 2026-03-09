"""
Market Briefing Room — Briefing Service (F2)

Handles:
 - Script generation via Claude API
 - HeyGen video creation and polling
 - DB persistence (MarketBriefing model)
 - Cost guard: max 3 videos per hour
"""

import logging
import os
import time
from datetime import datetime, timedelta, timezone

import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HEYGEN_API_BASE = "https://api.heygen.com"
SARAH_AVATAR_ID = "d259c335741f4fc0b061e04c59388b4e"
SARAH_VOICE_ID = "5f745b3db0db43739f31499f4f0aedd6"   # Claire Lawson — Broadcaster

HEYGEN_POLL_INTERVAL = 10   # seconds between status checks
HEYGEN_POLL_TIMEOUT = 300   # seconds before giving up
HEYGEN_MAX_RETRIES = 2      # LAW 2: max 2 API attempts per briefing
COST_GUARD_WINDOW_HOURS = 1
COST_GUARD_MAX_PER_WINDOW = 3

BRIEFING_TITLES = {
    'pre_market': 'Pre-Market Brief',
    'open': 'Market Open Brief',
    'close': 'Market Close Brief',
}

# ---------------------------------------------------------------------------
# Script prompts — Claude generates these at runtime (LAW 5)
# ---------------------------------------------------------------------------

SCRIPT_PROMPTS = {
    'pre_market': (
        "You are Sarah, Protocol Pulse's market intelligence host.\n"
        "Generate a 90-second pre-market Bitcoin briefing (max 180 words).\n"
        "Current BTC price: ${btc_price}\n"
        "Overnight developments: {top_headlines}\n\n"
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
        "Generate a 90-second market-open Bitcoin briefing (max 180 words).\n"
        "Current BTC price: ${btc_price}\n"
        "Key developments this morning: {top_headlines}\n\n"
        "Rules:\n"
        "- Open with the single most important thing traders need to know right now\n"
        "- State the BTC price and whether it's holding key levels\n"
        "- Name one catalyst or risk event to watch during today's session\n"
        "- Close with: \"Stay sovereign. I'm Sarah for Protocol Pulse.\"\n"
        "- No em dashes. No ellipses. No markdown. Plain spoken English.\n"
        "- Never mention competitor media outlets by name.\n"
        "- Output ONLY the spoken script. No stage directions. No brackets."
    ),
    'close': (
        "You are Sarah, Protocol Pulse's market intelligence host.\n"
        "Generate a 90-second market-close Bitcoin briefing (max 180 words).\n"
        "Today's BTC closing price: ${btc_price}\n"
        "Today's key developments: {top_headlines}\n\n"
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


def _get_btc_price() -> float:
    """Fetch live BTC price from Mempool.space with fallback."""
    try:
        resp = requests.get(
            "https://mempool.space/api/v1/prices",
            timeout=5,
        )
        if resp.status_code == 200:
            return float(resp.json().get("USD", 0))
    except Exception as exc:
        logger.warning("BTC price fetch failed: %s", exc)
    try:
        resp = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": "bitcoin", "vs_currencies": "usd"},
            timeout=5,
        )
        if resp.status_code == 200:
            return float(resp.json().get("bitcoin", {}).get("usd", 0))
    except Exception as exc:
        logger.warning("CoinGecko fallback failed: %s", exc)
    return 0.0


def _get_top_headlines(limit: int = 3) -> str:
    """Pull recent published article titles from DB for context."""
    try:
        # Lazy import to avoid circular deps at module level
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


def _generate_script(briefing_type: str, btc_price: float, headlines: str) -> str:
    """Call Claude API to generate spoken briefing script."""
    import anthropic
    prompt_template = SCRIPT_PROMPTS.get(briefing_type, SCRIPT_PROMPTS['open'])
    price_str = f"{btc_price:,.0f}" if btc_price else "price unavailable"
    prompt = prompt_template.format(
        btc_price=price_str,
        top_headlines=headlines,
        asia_data="Asian markets closed mixed; see latest data.",
    )

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        script = message.content[0].text.strip()
        # Enforce no em-dashes or ellipses per LAW 5
        script = script.replace("\u2014", ",").replace("\u2013", "-").replace("...", ".")
        return script
    except Exception as exc:
        logger.error("Claude script generation failed: %s", exc)
        raise


def _heygen_generate(script: str, title: str) -> dict:
    """Submit video generation request to HeyGen. Returns {'video_id': str}."""
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
    resp = requests.post(
        f"{HEYGEN_API_BASE}/v2/video/generate",
        headers=_heygen_headers(),
        json=payload,
        timeout=30,
    )
    if resp.status_code == 200:
        data = resp.json()
        video_id = data.get("data", {}).get("video_id")
        if video_id:
            return {"video_id": video_id}
    logger.error("HeyGen generate error %s: %s", resp.status_code, resp.text[:300])
    return {"error": resp.text[:300]}


def _heygen_poll(video_id: str) -> dict:
    """Poll HeyGen until complete or timeout. Returns status dict."""
    deadline = time.time() + HEYGEN_POLL_TIMEOUT
    while time.time() < deadline:
        try:
            resp = requests.get(
                f"{HEYGEN_API_BASE}/v1/video_status.get",
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
            logger.warning("HeyGen poll error: %s", exc)
        time.sleep(HEYGEN_POLL_INTERVAL)
    return {"status": "timeout"}


def _check_cost_guard() -> bool:
    """Return True if within cost guard limits (max 3 videos per hour)."""
    try:
        import models
        from app import app
        with app.app_context():
            cutoff = datetime.utcnow() - timedelta(hours=COST_GUARD_WINDOW_HOURS)
            recent_count = (
                models.MarketBriefing.query
                .filter(
                    models.MarketBriefing.generated_at >= cutoff,
                    models.MarketBriefing.status.in_(['generating', 'completed']),
                )
                .count()
            )
            if recent_count >= COST_GUARD_MAX_PER_WINDOW:
                logger.warning(
                    "COST GUARD: %d briefings in last %dh — pausing generation",
                    recent_count, COST_GUARD_WINDOW_HOURS,
                )
                return False
    except Exception as exc:
        logger.warning("Cost guard check failed: %s", exc)
    return True


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------

def generate_briefing(briefing_type: str) -> dict:
    """
    Full briefing generation pipeline. Called by cron or manual trigger.

    Args:
        briefing_type: 'pre_market' | 'open' | 'close'

    Returns:
        dict with 'success', 'briefing_id', and 'error' (if any)
    """
    if briefing_type not in SCRIPT_PROMPTS:
        return {"success": False, "error": f"Unknown briefing_type: {briefing_type}"}

    # Cost guard check
    if not _check_cost_guard():
        return {"success": False, "error": "Cost guard limit reached — max 3 videos/hour"}

    # Lazy imports for app context
    import models
    from app import app, db

    with app.app_context():
        # Create pending record
        today = datetime.utcnow().strftime("%b %-d, %Y")
        title = f"{BRIEFING_TITLES.get(briefing_type, 'Briefing')} — {today}"

        briefing = models.MarketBriefing(
            title=title,
            briefing_type=briefing_type,
            script_text="",
            status="pending",
            published=False,
        )
        try:
            db.session.add(briefing)
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            logger.error("DB insert failed: %s", exc)
            return {"success": False, "error": str(exc)}

        briefing_id = briefing.id

        # Step 1: fetch live data
        btc_price = _get_btc_price()
        headlines = _get_top_headlines()
        briefing.btc_price_at_generation = btc_price

        # Step 2: generate script
        try:
            briefing.status = "generating"
            script = _generate_script(briefing_type, btc_price, headlines)
            briefing.script_text = script
            db.session.commit()
        except Exception as exc:
            briefing.status = "failed"
            briefing.error_message = f"Script gen failed: {exc}"
            db.session.commit()
            return {"success": False, "briefing_id": briefing_id, "error": str(exc)}

        # Step 3: HeyGen — attempt up to HEYGEN_MAX_RETRIES times (LAW 2)
        heygen_result = None
        for attempt in range(1, HEYGEN_MAX_RETRIES + 1):
            logger.info("HeyGen attempt %d/%d for briefing %d", attempt, HEYGEN_MAX_RETRIES, briefing_id)
            gen_result = _heygen_generate(script, title)
            if "error" not in gen_result:
                heygen_result = gen_result
                break
            if attempt < HEYGEN_MAX_RETRIES:
                time.sleep(5)

        if not heygen_result:
            briefing.status = "failed"
            briefing.error_message = "HeyGen generation failed after max retries"
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
            return {"success": False, "briefing_id": briefing_id, "error": briefing.error_message}

        video_id = heygen_result["video_id"]
        briefing.heygen_video_id = video_id

        try:
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            logger.warning("DB commit after HeyGen submit: %s", exc)

        # Step 4: Poll for completion
        poll_result = _heygen_poll(video_id)

        if poll_result.get("status") != "completed":
            briefing.status = "failed"
            briefing.error_message = f"HeyGen poll result: {poll_result.get('status')} — {poll_result.get('error', '')}"
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
            return {
                "success": False,
                "briefing_id": briefing_id,
                "error": briefing.error_message,
            }

        # Step 5: persist final data and publish
        briefing.video_url = poll_result.get("video_url")
        briefing.thumbnail_url = poll_result.get("thumbnail_url")
        briefing.duration_seconds = poll_result.get("duration")
        briefing.status = "completed"
        briefing.published = True
        briefing.published_at = datetime.utcnow()

        try:
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            logger.error("Final DB commit failed: %s", exc)
            return {"success": False, "briefing_id": briefing_id, "error": str(exc)}

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
