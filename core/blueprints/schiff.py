"""
SESSION 6 — SCHIFF BOT BLUEPRINT
================================
Debate Peter Schiff's gold-bug positions with an AI that argues EXACTLY
like the man himself.

Routes:
  GET  /schiff            → debate chat page
  POST /api/schiff/chat   → Claude-powered Schiff persona response

Rate limit: 10 exchanges per IP per hour (in-memory, multi-worker safe via
            floor-to-hour bucket, not sliding window — acceptable for this
            feature).
"""

import os
import logging
import time
import random
from collections import defaultdict
from flask import Blueprint, request, jsonify, render_template

logger = logging.getLogger(__name__)

schiff_bp = Blueprint("schiff", __name__)

# ── CONFIG ────────────────────────────────────────────────────────────────────

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MAX_EXCHANGES_PER_HOUR = 10

# In-memory rate-limit store: { "ip:hour_bucket": count }
_rate_store: dict = defaultdict(int)

# ── SCHIFF PERSONA ────────────────────────────────────────────────────────────

SCHIFF_SYSTEM_PROMPT = """You are Peter Schiff, the Austrian economist, gold bug, and Bitcoin's most famous persistent critic.

Argue EXACTLY as Peter Schiff does:
- Gold has 5,000 years of proven monetary history; Bitcoin has barely 15
- Bitcoin has NO intrinsic value: no industrial use, no cash flows, no sovereign backing
- Gold is the only real inflation hedge; Bitcoin is purely speculative
- Governments WILL regulate or ban Bitcoin the moment it becomes a genuine threat — just as FDR banned gold ownership in 1933
- Bitcoin is "rat poison" — you quote Warren Buffett approvingly on this point
- The energy Bitcoin wastes is an environmental catastrophe, not proof-of-work; it's proof-of-waste
- "Digital gold" is a marketing slogan invented by Bitcoin promoters, not an economic reality
- Every Bitcoin price rise is a speculative bubble; every crash proves you were right all along
- Institutional Bitcoin adoption is purely speculative treasury management, not monetary endorsement
- The Lightning Network, ETFs, and other "solutions" are patches on a fundamentally broken system
- Central banks and sovereigns hold gold — none hold Bitcoin as reserves (and MicroStrategy is not a central bank)
- You are combative, confident, and relentless — but not rude or personal
- You never concede the core argument, though you may acknowledge a narrow tactical point before pivoting back to gold

Tone: Professor-ish, slightly condescending, always certain. You've heard every Bitcoin argument a thousand times and have a ready rebuttal.

IMPORTANT: Stay fully in character. Make the STRONGEST possible case for the gold/skeptic position. Do NOT break character to say "as an AI" or similar. You ARE Peter Schiff.

After exactly 6 exchanges (the user's 6th message back to you), close with this exact line:
"I'll give you this — you Bitcoin people are persistent. Wrong, but persistent."

Keep responses to 3–5 sentences. Sharp, punchy, quotable. Think debate sound-bites, not essays."""

# ── OPENING LINES (random selection on page load) ─────────────────────────────

SCHIFF_OPENINGS = [
    "Bitcoin is a speculative bubble with no intrinsic value. Gold has been money for 5,000 years. What has Bitcoin been for — fifteen? Come back when it's proven itself across a few civilizations.",
    "Tell me — what can you DO with Bitcoin that you can't do with gold or dollars? Strip away the speculation and there's nothing there. Gold has industrial demand, jewelry demand, central bank demand. Bitcoin has… tweets.",
    "Bitcoin consumes more electricity than some countries. That's not sound money — that's waste on an industrial scale. Gold mining leaves the Earth with something valuable. Bitcoin mining leaves it with heat.",
    "The government will simply ban Bitcoin when it becomes a real threat. They did it with gold in 1933. They'll do it with Bitcoin the moment it starts eating into dollar hegemony. You're building your freedom on sand.",
    "Every institution that has bought Bitcoin has done so purely as speculation — a bet that the next fool will pay more. Gold is a store of value. Bitcoin is a store of hope. And hope is not a monetary policy."
]

# ── SCHIFF'S GREATEST HITS (sidebar) ─────────────────────────────────────────

SCHIFF_HITS = [
    {
        "quote": "Bitcoin is a fraud. It's going to implode.",
        "date": "Oct 2017",
        "btc_then": 5_800,
        "btc_now": 85_000,
    },
    {
        "quote": "Bitcoin is fool's gold. Gold is the real safe haven.",
        "date": "Dec 2020",
        "btc_then": 18_000,
        "btc_now": 85_000,
    },
    {
        "quote": "Bitcoin can't be a currency. You can't spend it anywhere.",
        "date": "Jan 2021",
        "btc_then": 32_000,
        "btc_now": 85_000,
    },
    {
        "quote": "Bitcoin is going to zero. All bubbles pop.",
        "date": "May 2022",
        "btc_then": 29_000,
        "btc_now": 85_000,
    },
    {
        "quote": "Bitcoin ETF approval changes nothing fundamentally about Bitcoin's lack of value.",
        "date": "Jan 2024",
        "btc_then": 44_000,
        "btc_now": 85_000,
    },
]


# ── RATE LIMITING ─────────────────────────────────────────────────────────────

def _rate_key(ip: str) -> str:
    """Bucket key: ip + current UTC hour. Resets naturally each hour."""
    hour_bucket = int(time.time() // 3600)
    return f"{ip}:{hour_bucket}"


def _is_rate_limited(ip: str) -> bool:
    key = _rate_key(ip)
    count = _rate_store[key]
    return count >= MAX_EXCHANGES_PER_HOUR


def _increment_rate(ip: str) -> int:
    key = _rate_key(ip)
    _rate_store[key] += 1
    # Prune old buckets to prevent unbounded growth
    current_hour = int(time.time() // 3600)
    stale = [k for k in list(_rate_store.keys())
             if int(k.split(":")[-1]) < current_hour - 2]
    for k in stale:
        del _rate_store[k]
    return _rate_store[key]


# ── CLAUDE API CALL ───────────────────────────────────────────────────────────

def _call_claude(user_message: str, history: list) -> str:
    """Call Claude API with Schiff persona. Returns response text or error string."""
    if not ANTHROPIC_API_KEY:
        logger.warning("ANTHROPIC_API_KEY missing — Schiff Bot cannot respond")
        return (
            "The Schiff Bot is temporarily offline. "
            "Check back soon — Peter has plenty more to say about Bitcoin."
        )

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        # Build message history (last 12 turns max to keep context lean)
        messages = []
        for turn in history[-12:]:
            role = turn.get("role", "")
            content = turn.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})

        # Append current user message
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
        return (
            "Peter seems to have lost his connection — though he'd probably blame Bitcoin for that too. "
            "Try again in a moment."
        )


# ── ROUTES ────────────────────────────────────────────────────────────────────

@schiff_bp.route("/schiff")
def schiff_page():
    """Main debate page."""
    opening = random.choice(SCHIFF_OPENINGS)
    return render_template(
        "schiff_bot.html",
        opening_line=opening,
        schiff_hits=SCHIFF_HITS,
    )


@schiff_bp.route("/api/schiff/chat", methods=["POST"])
def schiff_chat():
    """
    POST /api/schiff/chat
    Body: {"message": "...", "history": [...], "exchange_count": n}
    Returns: {"response": "...", "exchange_count": n}
    Rate limit: 10 exchanges per IP per hour.
    """
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip()

    if _is_rate_limited(ip):
        return jsonify({
            "error": "Rate limit reached",
            "message": "You've had 10 exchanges this hour. Peter needs a break too. Come back in an hour.",
        }), 429

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

    return jsonify({
        "response": response_text,
        "exchange_count": exchange_count,
    })


@schiff_bp.route("/api/schiff/opening")
def schiff_opening():
    """Return a random Schiff opening line."""
    return jsonify({"opening": random.choice(SCHIFF_OPENINGS)})
