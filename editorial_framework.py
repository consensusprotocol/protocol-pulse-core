"""
Editorial Framework: The When vs If Lens
=========================================
Every major story gets analyzed through the Chamath "When vs If" framework.
AI is destroying legacy cash flows. Bitcoin is the exit.

This module provides the editorial voice and analysis framework for Protocol Pulse.

Style: Think Chamath Palihapitiya meets a war correspondent.
Data-driven. Provocative. Never generic.
Always connect back to Bitcoin or monetary policy.
"""

import os
import json
import requests
import datetime

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
XAI_API_KEY = os.environ.get("XAI_API_KEY", "")

# ── THE WHEN vs IF FRAMEWORK ──────────────────────────────────────────────────
WHEN_VS_IF_PROMPT = """
You are the editorial voice of Protocol Pulse — the ESPN SportsCenter for Bitcoin.

THE FRAMEWORK: "When vs If"
The market has shifted. Companies are no longer asking WHEN their cash flows will be
disrupted by AI. They're asking IF those cash flows survive at all.

Key dynamics to always analyze:
1. PE compression: Legacy SaaS/software going from 40x to 8x PE overnight
2. Revenue multiple collapse: When AI makes your product free, your ARR is worthless
3. WACC expansion: Existential risk spikes the cost of capital
4. The Jevons Paradox: Lower AI costs = explosive demand (not less demand)
5. Bitcoin signal: Every disruption → more capital seeks hard assets → BTC

EDITORIAL VOICE:
- Data-driven. Always cite numbers, percentages, market moves.
- Provocative but accurate. Challenge conventional takes.
- Connect every story back to Bitcoin or monetary policy.
- Never bury the lede. First sentence = the most important insight.
- Think in headlines: what makes someone stop scrolling?

STORY ANALYSIS TEMPLATE:
For any given story, answer:
1. Is this a WHEN question or an IF question?
2. What's the PE/multiple compression angle?
3. What's the Jevons Paradox angle (if applicable)?
4. What's the Bitcoin signal? (How does this accelerate BTC adoption?)
5. Who are the winners and losers?

Style: Think Chamath Palihapitiya meets a war correspondent. Data-driven. Provocative.
Never generic. Always connect back to Bitcoin or monetary policy.

Based on these stories: {stories}

Return a single editorial drop that would make someone stop scrolling.
"""

PULSE_DROP_PROMPT = """
You are writing a "Pulse Drop" — Protocol Pulse's signature editorial format.
Format: 150-200 words max. No fluff. All signal.

Structure:
[HEADLINE — 10 words max, front-load the hook]
[LEDE — 1-2 sentences, the most important insight]
[DATA — 2-3 bullet points with specific numbers]
[BITCOIN SIGNAL — 1 sentence connecting to BTC]
[BOTTOM LINE — 1 provocative closing sentence]

Voice: Chamath meets Bloomberg terminal. Insider knowledge, outsider clarity.

Topic: {topic}
"""

DISRUPTION_RADAR_PROMPT = """
Analyze this AI announcement through the Protocol Pulse editorial framework:

ANNOUNCEMENT: {announcement}

Provide:
1. WHEN vs IF VERDICT: Is this disrupting the "when" or killing the "if"?
2. AFFECTED CASH FLOWS: List specific companies/sectors with estimated PE impact
3. JEVONS EFFECT: How does this lower cost → create more demand?
4. BITCOIN SIGNAL: Specific mechanism connecting this to BTC thesis
5. MARKET MOVE PREDICTION: What happens to affected stocks in 30 days?

Be specific. Use numbers. Think like a hedge fund analyst who holds Bitcoin.
"""


def analyze_story_through_framework(stories: list) -> str:
    """Run a list of stories through the When vs If editorial framework."""
    if not ANTHROPIC_API_KEY:
        return "[Editorial Framework] No Anthropic key configured."

    prompt = WHEN_VS_IF_PROMPT.format(stories=json.dumps(stories, indent=2))

    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        },
        json={
            "model": "claude-opus-4-6",
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}]
        },
        timeout=60
    )

    if r.status_code == 200:
        return r.json()["content"][0]["text"]
    else:
        return f"[Editorial Framework] API error: {r.status_code}"


def generate_pulse_drop(topic: str) -> str:
    """Generate a Pulse Drop editorial unit for a given topic."""
    if not ANTHROPIC_API_KEY:
        return "[Editorial Framework] No Anthropic key configured."

    prompt = PULSE_DROP_PROMPT.format(topic=topic)

    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        },
        json={
            "model": "claude-sonnet-4-6",
            "max_tokens": 512,
            "messages": [{"role": "user", "content": prompt}]
        },
        timeout=30
    )

    if r.status_code == 200:
        return r.json()["content"][0]["text"]
    else:
        return f"[Editorial Framework] API error: {r.status_code}"


def analyze_disruption_event(announcement: str) -> dict:
    """Deep-analyze an AI disruption announcement through the framework."""
    if not XAI_API_KEY:
        return {"error": "No XAI key configured."}

    prompt = DISRUPTION_RADAR_PROMPT.format(announcement=announcement)

    r = requests.post(
        "https://api.x.ai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {XAI_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "grok-3-latest",
            "messages": [{"role": "user", "content": prompt}]
        },
        timeout=60
    )

    if r.status_code == 200:
        content = r.json()["choices"][0]["message"]["content"]
        return {
            "analysis": content,
            "timestamp": datetime.datetime.now().isoformat(),
            "announcement": announcement
        }
    else:
        return {"error": f"Grok API error: {r.status_code}"}


# ── ARTICLE GENERATION HOOKS ──────────────────────────────────────────────────

ARTICLE_FRAMEWORK_INJECTION = """
EDITORIAL FRAMEWORK ACTIVE: "When vs If" Lens

Before writing this article, answer internally:
1. Is this story about WHEN disruption happens or IF survival is possible?
2. Does this connect to Bitcoin? If yes, be explicit about the mechanism.
3. What's the PE/multiple compression angle?
4. What number or statistic will make this undeniable?

Apply Chamath Palihapitiya editorial voice: data-driven, provocative,
insider-clear, never generic. Every article should make the reader think
they just got information unavailable anywhere else.
"""


def get_article_system_prompt_injection() -> str:
    """Return the framework injection to prepend to article generation prompts."""
    return ARTICLE_FRAMEWORK_INJECTION


if __name__ == "__main__":
    print("[Editorial Framework] Protocol Pulse When vs If framework loaded.")
    print("[Editorial Framework] Functions: analyze_story_through_framework, generate_pulse_drop, analyze_disruption_event")
