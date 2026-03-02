"""
Article Generator — Mining Intel Writer
=========================================
Generates original Protocol Pulse "Mining Intel" articles using
extracted data. NEVER plagiarizes — uses data to write original analysis
in Protocol Pulse's sharp, analytical voice.
"""

import json
import logging
import requests
from datetime import datetime, timezone

from relay import get_key

logger = logging.getLogger(__name__)

MINING_INTEL_SYSTEM = """You are a senior Bitcoin mining analyst writing for Protocol Pulse — a Bitcoin intelligence platform read by sophisticated miners, traders, and institutional investors.

VOICE: Sharp, analytical, slightly provocative. Data-first. No hand-holding, no "what is Bitcoin mining." Your readers run mining operations, manage hashrate, and trade based on mining economics.

STYLE RULES:
- Lead with the most surprising or important data point
- Every claim backed by a specific number
- Include at least one insight the source data DIDN'T explicitly state
- Reference Protocol Pulse's own perspective
- Mention data sources naturally: "According to Blockware Intelligence's latest research..." or "mempool.space data shows..."
- NEVER copy sentences from source newsletters — write ORIGINAL analysis
- Connect mining metrics to broader market implications

MANDATORY 6-SECTION STRUCTURE:
1. <div class="tldr-section"><h3>TL;DR</h3><ul><li>Bullet 1</li><li>Bullet 2</li><li>Bullet 3</li></ul></div>
2. <h2>The Report</h2> — Lead with key data, 400-600 words of factual reporting
3. <h2>Exclusive Data Analysis</h2> — Mining economics deep-dive, 200-300 words
4. <h2>The Bitcoin Lens</h2> — Sovereignty/freedom angle on mining, 200-300 words
5. <h2>Transactor Intelligence</h2> — Actionable insights for miners and traders, 150-200 words
6. <h2>Sources</h2> — List of data sources used

MINIMUM: 1200 words total, all 6 sections required."""

ARTICLE_PROMPT_TEMPLATE = """Write a "Mining Intel" article for Protocol Pulse.

TODAY'S DATE: {date}

=== VERIFIED LIVE DATA (use these exact numbers) ===
{live_data_block}

=== NEWSLETTER INTELLIGENCE (from Blockware Intelligence) ===
{newsletter_block}

=== MARKET CONTEXT ===
- BTC Price: ${btc_price:,.0f} ({btc_change:+.1f}% 24h)
- Fear & Greed Index: {fng_value} ({fng_label})
- Block Height: {block_height:,}

=== KEY INSIGHTS FROM SOURCE ===
{insights_block}

=== MARKET STRUCTURE ===
{market_structure_block}

=== TOP MINING POOLS (7-day) ===
{pools_block}

ARTICLE REQUIREMENTS:
1. Headline: Punchy, specific, number-driven. Max 80 characters.
2. Subtitle: One-line summary adding context to the headline.
3. Body: Full HTML article following the 6-section structure above.
4. Category: "Mining Intel"
5. NEVER copy sentences from the Blockware newsletter — write ORIGINAL analysis
6. ALWAYS attribute data: "According to Blockware Intelligence..." or "mempool.space data confirms..."
7. Include at least one insight the source data didn't mention (your own analysis)
8. Tags should include relevant topics (mining, hashrate, difficulty, asic, etc.)

Respond in JSON format:
{{
    "title": "Headline here",
    "subtitle": "Subtitle here",
    "body_html": "Full HTML article content (all 6 sections)",
    "category": "Mining Intel",
    "tags": ["mining", "hashrate", ...],
    "cover_image_query": "search query for Pexels cover image",
    "sources": ["Blockware Intelligence", "mempool.space", ...],
    "seo_title": "SEO-optimized title (max 60 chars)",
    "seo_description": "SEO meta description (max 155 chars)"
}}"""


def _format_live_data(intel: dict) -> str:
    """Format live data section for the prompt."""
    cm = intel.get("combined_metrics", {})
    ld = intel.get("live_data", {})
    lines = []

    if cm.get("hashrate_ehs"):
        lines.append(f"- Network Hashrate: {cm['hashrate_ehs']} EH/s")
    if cm.get("difficulty_t"):
        lines.append(f"- Current Difficulty: {cm['difficulty_t']}T")
    if cm.get("next_adjustment_pct") is not None:
        lines.append(f"- Next Difficulty Adjustment: {cm['next_adjustment_pct']:+.2f}%")
    if ld.get("adjustment_progress_pct"):
        lines.append(f"- Adjustment Progress: {ld['adjustment_progress_pct']}%")
    if ld.get("blocks_remaining"):
        lines.append(f"- Blocks Until Adjustment: {ld['blocks_remaining']}")
    if cm.get("fee_sat_vb"):
        lines.append(f"- Avg Transaction Fee: {cm['fee_sat_vb']} sat/vB")
    if ld.get("fee_fastest_sat_vb"):
        lines.append(f"- Fastest Fee: {ld['fee_fastest_sat_vb']} sat/vB")
    if ld.get("mempool_tx_count"):
        lines.append(f"- Mempool: {ld['mempool_tx_count']:,} unconfirmed txs")
    if cm.get("hashprice"):
        lines.append(f"- Hashprice: {cm['hashprice']}")
    if cm.get("miner_revenue_daily"):
        lines.append(f"- Daily Miner Revenue: {cm['miner_revenue_daily']}")
    if cm.get("energy_cost_avg"):
        lines.append(f"- Avg Energy Cost: {cm['energy_cost_avg']}")
    if cm.get("breakeven_cost"):
        lines.append(f"- ASIC Breakeven Cost: {cm['breakeven_cost']}")

    asic = cm.get("asic_prices", {})
    if asic and isinstance(asic, dict):
        for model, price in asic.items():
            if price and price != "null":
                lines.append(f"- ASIC {model.upper()} Price: {price}")

    return "\n".join(lines) if lines else "No live data available"


def _format_newsletter_block(intel: dict) -> str:
    """Format newsletter extraction for the prompt."""
    nl = intel.get("newsletter", {})
    if not nl or not nl.get("source"):
        return "No newsletter data available for this cycle."

    lines = [
        f"Source: {nl.get('source', 'N/A')}",
        f"Date: {nl.get('source_date', 'N/A')}",
        f"Title: {nl.get('source_title', 'N/A')}",
    ]

    if nl.get("source_url"):
        lines.append(f"URL: {nl['source_url']}")

    return "\n".join(lines)


def _format_insights(intel: dict) -> str:
    insights = intel.get("key_insights", [])
    if not insights:
        return "No specific insights extracted from newsletter."
    return "\n".join(f"- {i}" for i in insights)


def _format_market_structure(intel: dict) -> str:
    ms = intel.get("market_structure", {})
    if not ms:
        return "No market structure data available."
    lines = []
    for k, v in ms.items():
        if v and v != "null":
            lines.append(f"- {k.replace('_', ' ').title()}: {v}")
    return "\n".join(lines) if lines else "No market structure data available."


def _format_pools(intel: dict) -> str:
    pools = intel.get("live_data", {}).get("top_pools", [])
    if not pools:
        return "No pool data available."
    lines = []
    for p in pools:
        lines.append(f"- {p['name']}: {p['blocks']} blocks ({p['share_pct']}%)")
    return "\n".join(lines)


def generate_article(intel: dict) -> dict | None:
    """
    Generate an original Mining Intel article from extracted intelligence.
    Returns article dict or None on failure.
    """
    api_key = get_key("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not available — cannot generate article")
        return None

    cm = intel.get("combined_metrics", {})
    ld = intel.get("live_data", {})

    btc_price = cm.get("btc_price_usd") or 0
    btc_change = ld.get("btc_24h_change_pct") or 0
    fng_value = ld.get("fear_greed_index") or 50
    fng_label = ld.get("fear_greed_label") or "Neutral"
    block_height = cm.get("block_height") or 0

    prompt = ARTICLE_PROMPT_TEMPLATE.format(
        date=datetime.now(timezone.utc).strftime("%B %d, %Y"),
        live_data_block=_format_live_data(intel),
        newsletter_block=_format_newsletter_block(intel),
        btc_price=btc_price if btc_price else 0,
        btc_change=btc_change if btc_change else 0,
        fng_value=fng_value,
        fng_label=fng_label,
        block_height=block_height if block_height else 0,
        insights_block=_format_insights(intel),
        market_structure_block=_format_market_structure(intel),
        pools_block=_format_pools(intel)
    )

    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 4000,
                "temperature": 0.7,
                "system": MINING_INTEL_SYSTEM,
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            },
            timeout=90
        )

        if resp.status_code != 200:
            logger.error(f"Claude generation failed: {resp.status_code} {resp.text[:300]}")
            return None

        result = resp.json()
        content_text = result["content"][0]["text"]

        # Parse JSON from response
        if "```" in content_text:
            content_text = content_text.split("```")[1]
            if content_text.startswith("json"):
                content_text = content_text[4:]
            content_text = content_text.strip()

        article = json.loads(content_text)

        # Validate required fields
        required = ["title", "body_html", "category"]
        for field in required:
            if not article.get(field):
                logger.error(f"Article missing required field: {field}")
                return None

        # Validate minimum length
        body = article.get("body_html", "")
        word_count = len(body.split())
        if word_count < 200:
            logger.warning(f"Article too short: {word_count} words (min 200)")

        article.setdefault("subtitle", "")
        article.setdefault("tags", ["mining", "hashrate"])
        article.setdefault("cover_image_query", "bitcoin mining facility")
        article.setdefault("sources", ["mempool.space"])
        article.setdefault("seo_title", article["title"][:60])
        article.setdefault("seo_description", article.get("subtitle", "")[:155])

        # Add metadata
        article["generated_at"] = datetime.now(timezone.utc).isoformat()
        article["word_count"] = word_count
        article["intel_date"] = intel.get("date", "")
        article["data_quality"] = intel.get("data_quality", "medium")

        logger.info(f"Generated article: '{article['title']}' ({word_count} words)")
        return article

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Claude article response: {e}")
        return None
    except Exception as e:
        logger.error(f"Article generation error: {e}")
        return None


def generate_snapshot_article(intel: dict) -> dict | None:
    """
    Generate a shorter "Mining Snapshot" article using only live data
    (no newsletter required). Used on non-newsletter days.
    """
    api_key = get_key("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not available")
        return None

    cm = intel.get("combined_metrics", {})
    ld = intel.get("live_data", {})

    btc_price = cm.get("btc_price_usd") or 0
    btc_change = ld.get("btc_24h_change_pct") or 0
    fng_value = ld.get("fear_greed_index") or 50
    fng_label = ld.get("fear_greed_label") or "Neutral"

    snapshot_prompt = f"""Write a concise "Mining Snapshot" article for Protocol Pulse. This is a quick daily update, NOT a deep-dive.

TODAY: {datetime.now(timezone.utc).strftime("%B %d, %Y")}

LIVE MINING DATA:
{_format_live_data(intel)}

MARKET:
- BTC: ${btc_price:,.0f} ({btc_change:+.1f}% 24h)
- Fear & Greed: {fng_value} ({fng_label})

TOP POOLS (7d):
{_format_pools(intel)}

Write a 400-600 word article. Use the standard 6-section structure but keep each section shorter.
Focus on what changed TODAY — any notable hashrate movements, fee spikes, difficulty trends, or pool shifts.

Respond in JSON:
{{
    "title": "Mining Snapshot: [key metric or event]",
    "subtitle": "Daily mining network status",
    "body_html": "Full HTML with 6 sections",
    "category": "Mining Intel",
    "tags": ["mining", "snapshot", "hashrate"],
    "cover_image_query": "bitcoin mining data center",
    "sources": ["mempool.space"],
    "seo_title": "...",
    "seo_description": "..."
}}"""

    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 3000,
                "temperature": 0.7,
                "system": MINING_INTEL_SYSTEM,
                "messages": [{"role": "user", "content": snapshot_prompt}]
            },
            timeout=90
        )

        if resp.status_code != 200:
            logger.error(f"Snapshot generation failed: {resp.status_code}")
            return None

        content_text = resp.json()["content"][0]["text"]
        if "```" in content_text:
            content_text = content_text.split("```")[1]
            if content_text.startswith("json"):
                content_text = content_text[4:]
            content_text = content_text.strip()

        article = json.loads(content_text)
        article["generated_at"] = datetime.now(timezone.utc).isoformat()
        article["word_count"] = len(article.get("body_html", "").split())
        article["is_snapshot"] = True

        logger.info(f"Generated snapshot: '{article['title']}'")
        return article

    except Exception as e:
        logger.error(f"Snapshot generation error: {e}")
        return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
    print("Article generator module loaded. Use generate_article(intel) or generate_snapshot_article(intel).")
