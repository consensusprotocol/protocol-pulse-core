"""
Data Extractor — Intelligence Parser
======================================
Extracts structured mining data from newsletter HTML content
using Claude API for reliable parsing. Also enriches with live
mempool.space data.
"""

import json
import logging
import re
from datetime import datetime, timezone

from relay import get_key

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """You are a Bitcoin mining data extraction specialist. Extract ALL quantitative data and key insights from this newsletter content.

Return a JSON object with this exact structure:
{
    "metrics": {
        "hashrate": "value with unit or null",
        "difficulty": "current value or null",
        "next_difficulty_adjustment": "estimated % change or null",
        "hashprice": "$/PH/day or null",
        "btc_price_at_publish": "$ value or null",
        "avg_tx_fee": "sat/vB or null",
        "miner_revenue_daily": "$ value or null",
        "asic_prices": {
            "s21": "$ or null",
            "s19": "$ or null",
            "other": "any other ASIC prices mentioned"
        },
        "energy_cost_avg": "$/kWh or null",
        "breakeven_cost": "$/kWh for latest gen or null"
    },
    "key_insights": [
        "Insight 1 — specific, data-backed",
        "Insight 2 — specific, data-backed",
        "Insight 3 — specific, data-backed"
    ],
    "market_structure": {
        "miner_reserves": "trending up/down/flat or null",
        "miner_selling_pressure": "increasing/decreasing/stable or null",
        "exchange_flows": "net inflow/outflow or null",
        "otc_desk_activity": "elevated/normal/low or null",
        "public_miner_outlook": "bullish/bearish/neutral or null"
    },
    "notable_events": [
        "Any significant events mentioned (new facilities, regulations, etc.)"
    ],
    "data_quality": "high/medium/low — how much concrete data was in the source"
}

Extract ONLY what is explicitly stated. Use null for anything not mentioned.
Do NOT invent or estimate values."""


def _strip_html(html: str) -> str:
    """Strip HTML tags for text extraction."""
    text = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def extract_from_newsletter(newsletter: dict) -> dict:
    """
    Use Claude to extract structured data from newsletter HTML content.
    Returns structured mining intelligence dict.
    """
    if not newsletter or not newsletter.get("content_html"):
        logger.info("No newsletter content to extract from")
        return _empty_extraction()

    api_key = get_key("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not available — cannot extract")
        return _empty_extraction()

    # Strip HTML and truncate to avoid token limits
    text = _strip_html(newsletter["content_html"])
    if len(text) > 12000:
        text = text[:12000] + "... [truncated]"

    try:
        import requests
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 2000,
                "temperature": 0.1,
                "messages": [
                    {"role": "user", "content": f"{EXTRACTION_PROMPT}\n\n=== NEWSLETTER CONTENT ===\n\nTitle: {newsletter.get('title', '')}\nDate: {newsletter.get('date', '')}\n\n{text}"}
                ]
            },
            timeout=60
        )

        if resp.status_code != 200:
            logger.error(f"Claude extraction failed: {resp.status_code} {resp.text[:200]}")
            return _empty_extraction()

        result = resp.json()
        content_text = result["content"][0]["text"]

        # Parse JSON from response (handle markdown code blocks)
        if "```" in content_text:
            content_text = content_text.split("```")[1]
            if content_text.startswith("json"):
                content_text = content_text[4:]
            content_text = content_text.strip()

        extracted = json.loads(content_text)
        extracted["source"] = newsletter.get("source", "Blockware Intelligence")
        extracted["source_date"] = newsletter.get("date", "")
        extracted["source_title"] = newsletter.get("title", "")
        extracted["source_url"] = newsletter.get("url", "")
        extracted["extraction_method"] = "claude"

        logger.info(f"Extracted {len(extracted.get('key_insights', []))} insights from newsletter")
        return extracted

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Claude extraction response: {e}")
        return _empty_extraction()
    except Exception as e:
        logger.error(f"Extraction error: {e}")
        return _empty_extraction()


def enrich_with_live_data(extracted: dict, mempool_data: dict, btc_price: dict,
                          fng: dict, pools: dict) -> dict:
    """
    Combine newsletter extraction with live mempool/market data.
    Live data takes precedence for real-time metrics.
    """
    intel = {
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "compiled_at": datetime.now(timezone.utc).isoformat(),
        "newsletter": extracted,
        "live_data": {},
        "combined_metrics": {}
    }

    # Live hashrate
    hr = mempool_data.get("hashrate", {})
    if hr:
        intel["live_data"]["hashrate_ehs"] = hr.get("ehs")

    # Live difficulty
    diff = mempool_data.get("difficulty", {})
    if diff:
        intel["live_data"]["difficulty_t"] = diff.get("trillion")

    # Difficulty adjustment
    adj = mempool_data.get("difficulty_adjustment", {})
    if adj:
        intel["live_data"]["next_adjustment_pct"] = adj.get("estimated_change_pct")
        intel["live_data"]["adjustment_progress_pct"] = adj.get("progress_pct")
        intel["live_data"]["blocks_remaining"] = adj.get("remaining_blocks")

    # Block height
    intel["live_data"]["block_height"] = mempool_data.get("block_height")

    # Fees
    fees = mempool_data.get("avg_fee", {})
    if fees:
        intel["live_data"]["fee_fastest_sat_vb"] = fees.get("fastest")
        intel["live_data"]["fee_hour_sat_vb"] = fees.get("hour")
        intel["live_data"]["fee_economy_sat_vb"] = fees.get("economy")

    # Mempool
    mp = mempool_data.get("mempool_size", {})
    if mp:
        intel["live_data"]["mempool_tx_count"] = mp.get("count")
        intel["live_data"]["mempool_total_fee_btc"] = mp.get("total_fee_btc")

    # BTC price
    intel["live_data"]["btc_price_usd"] = btc_price.get("usd")
    intel["live_data"]["btc_24h_change_pct"] = btc_price.get("change_24h_pct")

    # Fear & Greed
    intel["live_data"]["fear_greed_index"] = fng.get("value")
    intel["live_data"]["fear_greed_label"] = fng.get("classification")

    # Mining pools
    if pools.get("pools"):
        intel["live_data"]["top_pools"] = pools["pools"][:5]
        intel["live_data"]["pool_total_blocks_1w"] = pools.get("total_blocks")

    # Combined metrics: prefer live data, fall back to newsletter
    newsletter_metrics = extracted.get("metrics", {})
    intel["combined_metrics"] = {
        "hashrate_ehs": intel["live_data"].get("hashrate_ehs") or newsletter_metrics.get("hashrate"),
        "difficulty_t": intel["live_data"].get("difficulty_t") or newsletter_metrics.get("difficulty"),
        "next_adjustment_pct": intel["live_data"].get("next_adjustment_pct") or newsletter_metrics.get("next_difficulty_adjustment"),
        "btc_price_usd": intel["live_data"].get("btc_price_usd") or newsletter_metrics.get("btc_price_at_publish"),
        "fee_sat_vb": intel["live_data"].get("fee_hour_sat_vb") or newsletter_metrics.get("avg_tx_fee"),
        "block_height": intel["live_data"].get("block_height"),
        "fear_greed": intel["live_data"].get("fear_greed_index"),
        "hashprice": newsletter_metrics.get("hashprice"),
        "miner_revenue_daily": newsletter_metrics.get("miner_revenue_daily"),
        "asic_prices": newsletter_metrics.get("asic_prices"),
        "energy_cost_avg": newsletter_metrics.get("energy_cost_avg"),
        "breakeven_cost": newsletter_metrics.get("breakeven_cost"),
    }

    # Carry forward qualitative insights
    intel["key_insights"] = extracted.get("key_insights", [])
    intel["market_structure"] = extracted.get("market_structure", {})
    intel["notable_events"] = extracted.get("notable_events", [])
    intel["data_quality"] = extracted.get("data_quality", "medium")
    intel["sources_used"] = ["mempool.space", "CoinGecko", "Alternative.me"]
    if extracted.get("source"):
        intel["sources_used"].insert(0, extracted["source"])

    return intel


def _empty_extraction() -> dict:
    return {
        "metrics": {},
        "key_insights": [],
        "market_structure": {},
        "notable_events": [],
        "data_quality": "low",
        "extraction_method": "none",
        "source": None,
        "source_date": None,
        "source_title": None,
        "source_url": None
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
    # Test with dummy newsletter
    sample = {
        "date": "2026-03-02",
        "title": "Test Newsletter",
        "content_html": "<p>Bitcoin hashrate reached 850 EH/s this week.</p>",
        "source": "Test"
    }
    result = extract_from_newsletter(sample)
    print(json.dumps(result, indent=2))
