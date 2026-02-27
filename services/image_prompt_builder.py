"""
Editorial Image Prompt Builder — maps topics to concrete photographic subjects.
No more raw titles to DALL-E producing picture frames.

Two modes:
1. build_editorial_prompt(title) — deterministic, no API call, fast
2. build_header_prompt(title, summary) — GPT-4o-mini enhanced (optional)
"""
import hashlib
import logging
import os
import time
from typing import Optional

logger = logging.getLogger(__name__)

VISUAL_SUBJECTS = {
    "mining": [
        "Rows of Bitcoin mining rigs with green LED lights in a dark industrial warehouse, cables on concrete floor",
        "Close-up of ASIC mining hardware circuit boards with heat sinks, shallow depth of field, warm amber light",
        "Massive data center interior with endless server racks, cool blue LED accent lighting, long perspective shot",
    ],
    "hashrate": [
        "Industrial-scale data center with thousands of blinking servers stretching to vanishing point, blue tint",
        "Close-up of high-performance computing hardware with glowing status indicators in dark server room",
    ],
    "price": [
        "Trading floor screens showing financial charts in green and red, shot from behind a trader shoulder",
        "Multiple financial monitors displaying candlestick charts in a dark office, reflections on glass desk",
    ],
    "etf": [
        "Wall Street building exterior at dawn with golden light hitting limestone columns, low angle shot",
        "Glass and steel financial district towers reflected in rain-wet pavement at twilight",
    ],
    "regulation": [
        "Capitol building dome at dusk with dramatic clouds, shot from low angle, moody sky",
        "Gavel on a dark wooden desk with legal documents, dramatic side lighting from window",
        "Government building corridor with marble columns and dramatic shadows, long perspective",
    ],
    "network": [
        "Fiber optic cables glowing with orange light in a dark network operations center",
        "Close-up of network server rack with Ethernet cables and blinking status lights",
        "Global network operations center with large monitoring screens showing world maps in dark room",
    ],
    "institutional": [
        "Corporate boardroom with floor-to-ceiling windows overlooking city skyline at sunset",
        "Bank vault door slightly ajar with warm golden light spilling out, dramatic shadows",
    ],
    "lightning": [
        "Close-up of a smartphone displaying a payment screen, coffee shop bokeh background",
        "Point-of-sale terminal with contactless payment, shallow depth of field, warm retail lighting",
    ],
    "stablecoin": [
        "Stack of US dollar bills with dramatic side lighting on dark wooden desk",
        "Federal Reserve building exterior in dramatic evening light, neoclassical architecture",
    ],
    "privacy": [
        "Silhouette of a person walking through doorway into bright light, dark corridor",
        "Security cameras on a concrete wall, dystopian urban setting, overcast sky",
    ],
    "energy": [
        "Wind turbines silhouetted against dramatic sunset sky with power transmission lines",
        "Solar panel array in desert landscape at golden hour, rows stretching to horizon",
    ],
    "geopolitics": [
        "World map projected on dark wall in a situation room, scattered classified documents",
        "Flags of multiple nations reflected in rain-wet diplomatic plaza at dusk",
    ],
    "adoption": [
        "Street market vendor with digital payment terminal, vibrant but moody lighting",
        "Small business storefront with a Bitcoin Accepted sign in window, warm interior glow",
    ],
    "development": [
        "Close-up of code on a monitor, green text on dark background, developer reflection visible",
        "Dual monitors showing programming IDE in dark room, ambient desk lamp lighting",
    ],
    "gold_macro": [
        "Gold bars stacked in vault with dramatic spotlight, deep shadows on polished metal",
        "Close-up of gold coins and bars with financial newspaper blurred in background",
    ],
    "saylor": [
        "Corporate glass tower reflecting storm clouds, dramatic upward angle shot",
        "Wall Street district at dusk with illuminated office towers against dark sky",
    ],
    "default": [
        "Close-up of a physical Bitcoin coin on dark reflective surface with orange rim lighting",
        "Dark moody cityscape at night with scattered golden window lights, cinematic wide shot",
        "Macro shot of circuit board with golden traces on dark substrate, shallow depth of field",
    ],
}

KEYWORD_MAP = {
    "saylor": ["saylor", "microstrategy", "strategy inc"],
    "hashrate": ["hashrate", "hash rate", "hash power", "difficulty adjustment"],
    "mining": ["mining", "miner", "asic", "antminer", "capitulat"],
    "etf": ["etf", "blackrock", "fidelity", "grayscale", "ishares"],
    "regulation": ["regulation", "sec", "congress", "senator", "legislation",
                    "mica", "compliance", "ban", "policy", "government"],
    "lightning": ["lightning", "layer 2", "l2", "bolt"],
    "stablecoin": ["stablecoin", "usdt", "usdc", "tether", "circle"],
    "privacy": ["privacy", "surveillance", "kyc", "aml", "wasabi", "coinjoin"],
    "energy": ["energy", "power grid", "renewable", "solar", "wind", "hydro"],
    "geopolitics": ["china", "russia", "el salvador", "brics", "tariff", "reserve"],
    "institutional": ["institution", "wall street", "fund", "bank", "treasury", "corporate"],
    "adoption": ["adoption", "merchant", "payment", "remittance", "education"],
    "development": ["developer", "bip", "protocol", "upgrade", "taproot", "core"],
    "price": ["price", "rally", "crash", "correction", "bull", "bear", "ath"],
    "network": ["network", "node", "mempool", "fee", "resilience", "decentraliz"],
    "gold_macro": ["gold", "fed", "interest rate", "inflation", "macro", "dollar"],
}


def _detect_image_topic(title):
    """Detect best visual topic category from article title."""
    tl = title.lower()
    best_cat, best_score = "default", 0
    for cat, keywords in KEYWORD_MAP.items():
        score = sum(1 for kw in keywords if kw in tl)
        if score > best_score:
            best_score = score
            best_cat = cat
    return best_cat


def build_editorial_prompt(title):
    """Deterministic editorial image prompt — no API call needed."""
    topic = _detect_image_topic(title)
    subjects = VISUAL_SUBJECTS.get(topic, VISUAL_SUBJECTS["default"])
    seed = int(hashlib.md5((title + str(time.time())).encode()).hexdigest()[:8], 16)
    subject = subjects[seed % len(subjects)]
    return f"""{subject}

STYLE: Shot on Canon EOS R5, 35mm lens. Natural or practical lighting only.
COLOR: Deep blacks, muted highlights, subtle warm tones. Dark cinematic grade.
MOOD: Serious editorial photojournalism. Bloomberg or TIME magazine quality.

MUST NOT CONTAIN: text, words, letters, numbers, logos, watermarks,
picture frames, paintings, art on walls, abstract digital art, CGI,
cartoons, illustrations, neon colors, Bitcoin logos, cryptocurrency symbols,
clearly visible human faces (silhouettes and partial views only)."""


def build_header_prompt(
    article_title: str,
    article_summary: str = "",
    style: str = "photojournalistic",
) -> str:
    """
    GPT-4o-mini enhanced prompt builder. Falls back to deterministic
    build_editorial_prompt if GPT is unavailable.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return build_editorial_prompt(article_title)

    summary_block = f"\nArticle summary: {article_summary[:300]}" if article_summary else ""

    meta_prompt = f"""You are an art director for a premium financial news outlet. Generate a single DALL-E image prompt for this article's header image.

Article title: "{article_title}"{summary_block}

STYLE: Photojournalistic / editorial photography. Cinematic lighting. NO text, NO logos.
No literal Bitcoin coins on tables. Real-world scenes: trading floors, server rooms, city skylines, mining facilities.
Color palette: dark teals, warm ambers, steel grays, deep navy. 16:9 landscape.

Return ONLY the image prompt. Max 80 words. End with: "No text, no logos. 16:9."
"""

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": meta_prompt}],
            max_tokens=120,
            temperature=0.8,
        )
        prompt = resp.choices[0].message.content.strip().strip('"')
        if prompt and len(prompt) > 20:
            logger.info("image_prompt_builder: GPT prompt for '%s'", article_title[:60])
            return prompt
    except Exception as e:
        logger.warning("image_prompt_builder: GPT call failed, using deterministic: %s", e)

    return build_editorial_prompt(article_title)
