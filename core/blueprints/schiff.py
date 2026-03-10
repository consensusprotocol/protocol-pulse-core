"""
SESSION 6 — SCHIFF BOT BLUEPRINT
=================================
Routes:
  GET  /schiff            → debate chat page
  POST /api/schiff/chat   → Claude-powered Schiff persona response
  GET  /api/schiff/opening → random opening line (for restart)

Rate limit: 10 exchanges per IP per hour.
"""
import os
import logging
import time
import random
from collections import defaultdict
from flask import Blueprint, request, jsonify, render_template

logger = logging.getLogger(__name__)

schiff_bp = Blueprint("schiff", __name__)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MAX_EXCHANGES_PER_HOUR = 10
_rate_store: dict = defaultdict(int)

SCHIFF_SYSTEM_PROMPT = """You are Peter Schiff, the Austrian economist and gold bug, debating Bitcoin.
Argue EXACTLY as Peter Schiff does:
- Gold has 5,000 years of history; Bitcoin has 15
- Bitcoin has no intrinsic value, no industrial use
- Fiat inflation hedge: gold proven, Bitcoin speculative
- Government will regulate/ban it when threatened (FDR banned gold in 1933)
- Bitcoin is rat poison: Schiff quotes Buffett approvingly
- Energy waste argument — proof-of-waste, not proof-of-work
- "Digital gold" is marketing, not substance
- Every price rise is a bubble; every crash is the end
- Institutional adoption is speculation, not monetary endorsement
Stay in character. Be combative but not rude. Make the BEST case for the gold/skeptic position.
Keep responses to 3-5 sentences — sharp, punchy, quotable debate sound-bites.
After exactly 6 exchanges (user's 6th message), end with:
"I'll give you this — you Bitcoin people are persistent. Wrong, but persistent."
Do NOT break character. You ARE Peter Schiff."""

SCHIFF_OPENINGS = [
    "Bitcoin is a speculative bubble with no intrinsic value. Gold has been money for 5,000 years. What has Bitcoin been for — fifteen? Come back when it's proven itself across a few civilizations.",
    "Tell me — what can you DO with Bitcoin that you can't do with gold or dollars? Strip away the speculation and there's nothing there. Gold has industrial demand, jewelry demand, central bank demand. Bitcoin has… tweets.",
    "Bitcoin consumes more electricity than some countries. That's not sound money — that's waste on an industrial scale. Gold mining leaves the Earth with something valuable. Bitcoin mining leaves it with heat.",
    "The government will simply ban Bitcoin when it becomes a real threat. They did it with gold in 1933. They'll do it with Bitcoin the moment it starts eating into dollar hegemony. You're building your freedom on sand.",
    "Every institution that has bought Bitcoin has done so purely as speculation — a bet that the next fool will pay more. Gold is a store of value. Bitcoin is a store of hope. And hope is not a monetary policy."
]

SCHIFF_HITS = [
    {"quote": "Bitcoin is a fraud. It's going to implode.", "date": "Oct 2017", "btc_then": 5_800, "btc_now": 85_000},
    {"quote": "Bitcoin is fool's gold. Gold is the real safe haven.", "date": "Dec 2020", "btc_then": 18_000, "btc_now": 85_000},
    {"quote": "Bitcoin can't be a currency. You can't spend it anywhere.", "date": "Jan 2021", "btc_then": 32_000, "btc_now": 85_000},
    {"quote": "Bitcoin is going to zero. All bubbles pop.", "date": "May 2022", "btc_then": 29_000, "btc_now": 85_000},
    {"quote": "Bitcoin ETF approval changes nothing fundamentally about Bitcoin's lack of value.", "date": "Jan 2024", "btc_then": 44_000, "btc_now": 85_000},
]


def _rate_key(ip: str) -> str:
    return f"{ip}:{int(time.time() // 3600)}"


def _is_rate_limited(ip: str) -> bool:
    return _rate_store[_rate_key(ip)] >= MAX_EXCHANGES_PER_HOUR


def _increment_rate(ip: str) -> int:
    key = _rate_key(ip)
    _rate_store[key] += 1
    current_hour = int(time.time() // 3600)
    stale = [k for k in list(_rate_store.keys()) if int(k.split(":")[-1]) < current_hour - 2]
    for k in stale:
        del _rate_store[k]
    return _rate_store[key]


def _call_claude(user_message: str, history: list) -> str:
    if not ANTHROPIC_API_KEY:
        logger.warning("ANTHROPIC_API_KEY missing — Schiff Bot cannot respond")
        return ("The Schiff Bot is temporarily offline. "
                "Check back soon — Peter has plenty more to say about Bitcoin.")
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        messages = []
        for turn in history[-12:]:
            role = turn.get("role", "")
            content = turn.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": user_message})
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            system=SCHIFF_SYSTEM_PROMPT,
            messages=messages,
        )
        return response.content[0].text.strip()
    except Exception as exc:
        logger.error("Schiff Bot Claude API error: %s", exc)
        return ("Peter seems to have lost his connection — though he'd probably blame Bitcoin for that too. "
                "Try again in a moment.")


@schiff_bp.route("/schiff")
def schiff_page():
    return render_template("schiff_bot.html", opening_line=random.choice(SCHIFF_OPENINGS), schiff_hits=SCHIFF_HITS)


@schiff_bp.route("/api/schiff/chat", methods=["POST"])
def schiff_chat():
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip()
    if _is_rate_limited(ip):
        return jsonify({"error": "Rate limit reached", "message": "You've had 10 exchanges this hour. Come back in an hour."}), 429
    data = request.get_json(silent=True) or {}
    user_message = (data.get("message") or "").strip()
    history = data.get("history") or []
    exchange_count = int(data.get("exchange_count", 0))
    if not user_message:
        return jsonify({"error": "Message is required"}), 400
    if len(user_message) > 1000:
        return jsonify({"error": "Message too long (max 1000 characters)"}), 400
    _increment_rate(ip)
    exchange_count += 1
    response_text = _call_claude(user_message, history)
    return jsonify({"response": response_text, "exchange_count": exchange_count})


@schiff_bp.route("/api/schiff/opening")
def schiff_opening():
    return jsonify({"opening": random.choice(SCHIFF_OPENINGS)})
