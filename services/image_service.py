# Protocol Pulse Editorial Image Service
# 90% Pexels stock photos, 10% Grok hyper-realistic (top articles with named people/brands only)
# Red/black brand overlay on all images for cohesive look

import os
import re
import time
import logging
import requests
import hashlib
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
from io import BytesIO

logger = logging.getLogger(__name__)

HEADERS_DIR = Path("static/images/headers")
HEADERS_DIR.mkdir(parents=True, exist_ok=True)

# Target size: 1200x630 (OpenGraph standard, works for SEO, Substack, social)
TARGET_WIDTH = 1200
TARGET_HEIGHT = 630

# Keywords that indicate a "top article" worthy of Grok generation
TOP_ARTICLE_INDICATORS = [
    'michael saylor',
    'elon musk',
    'trump',
    'biden',
    'powell',
    'gensler',
    'blackrock',
    'fidelity',
    'jpmorgan',
    'goldman sachs',
    'sec ',
    'fed ',
    'federal reserve',
    'congress',
    'senate',
    'white house',
    'breaking:',
    'exclusive:',
    'just in:',
]

class ImageGenerationService:
    """Pexels-first image service with Grok fallback for premium articles."""

    def __init__(self):
        self.pexels_key = os.environ.get("PEXELS_API_KEY", "")
        self.xai_key = os.environ.get("XAI_API_KEY", "")
        self.openai_key = os.environ.get("OPENAI_API_KEY", "")

        if self.pexels_key:
            logger.info("Image service initialized with Pexels (primary)")
        else:
            logger.warning(
                "PEXELS_API_KEY not set — image service will use fallbacks only"
            )

        if self.xai_key:
            logger.info(
                "Grok image generation available (secondary, top articles only)"
            )

    # ─── PUBLIC API ────────────────────────────────────────────────

    def generate_article_header_image(self,
                                      title,
                                      category=None,
                                      force_grok=False):
        """Generate a header image for an article.
        Returns: path string like '/static/images/headers/header_xxx.jpg'
        """
        safe_title = _safe_filename(title)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"header_{safe_title}_{timestamp}.jpg"
        filepath = HEADERS_DIR / filename

        # Priority: Grok (primary) -> DALL-E (secondary) -> Pexels KILLED
        # Every article gets a unique AI-generated image. No more stock photo repetition.
        image = None

        # 1. Grok (primary — hyper-realistic, unique per article)
        if self.xai_key:
            logger.info(f"Generating Grok image for: {title[:50]}")
            image = self._generate_grok_image(title)

        # 2. OpenAI DALL-E (fallback if Grok fails)
        if image is None and self.openai_key:
            logger.info(f"Grok failed, using DALL-E for: {title[:50]}")
            image = self._generate_openai_image(title)

        if image is None:
            logger.warning(f"All image sources failed for: {title[:50]}")
            image = self._generate_fallback_image(title)

        try:
            # Apply brand overlay and save
            image = _resize_and_crop(image, TARGET_WIDTH, TARGET_HEIGHT)
            image = _apply_brand_overlay(image)
            image.save(str(filepath), "JPEG", quality=85, optimize=True)
            result_path = f"/static/images/headers/{filename}"
            size_kb = filepath.stat().st_size // 1024
            logger.info(f"Saved header image: {result_path} ({size_kb}KB)")
            return result_path
        except Exception as save_err:
            logger.error(f"Image save failed: {save_err}")
            return "/static/images/default-header.png"

    # ─── PEXELS (PRIMARY — 90% of articles) ────────────────────────

    def _fetch_pexels_image(self, title, category=None):
        """Search Pexels for a relevant stock photo."""
        queries = _build_pexels_queries(title, category)

        for query in queries:
            try:
                resp = requests.get(
                    "https://api.pexels.com/v1/search",
                    headers={"Authorization": self.pexels_key},
                    params={
                        "query": query,
                        "per_page": 10,
                        "orientation": "landscape",
                        "size": "large",
                    },
                    timeout=10,
                )
                if resp.status_code != 200:
                    logger.warning(
                        f"Pexels returned {resp.status_code} for '{query}'")
                    continue

                photos = resp.json().get("photos", [])
                if not photos:
                    logger.info(
                        f"No Pexels results for '{query}', trying next query")
                    continue

                # Pick a photo deterministically based on title hash (avoids same photo)
                idx = int(hashlib.md5(title.encode()).hexdigest()[:8],
                          16) % len(photos)
                photo = photos[idx]
                img_url = photo.get("src", {}).get("landscape") or photo.get(
                    "src", {}).get("large2x")

                if not img_url:
                    continue

                img_resp = requests.get(img_url, timeout=15)
                if img_resp.status_code == 200:
                    img = Image.open(BytesIO(img_resp.content)).convert("RGB")
                    logger.info(
                        f"Pexels hit: '{query}' → {photo.get('photographer', 'unknown')}"
                    )
                    return img

            except Exception as e:
                logger.error(f"Pexels error for '{query}': {e}")
                continue

        return None

    # ─── GROK (SECONDARY — top articles with named entities only) ───

    def _generate_grok_image(self, title):
        """Use Grok/xAI for hyper-realistic editorial images on premium articles."""
        prompt = _build_grok_prompt(title)

        try:
            resp = requests.post(
                "https://api.x.ai/v1/images/generations",
                headers={
                    "Authorization": f"Bearer {self.xai_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "grok-imagine-image",
                    "prompt": prompt,
                    "n": 1,
                    "response_format": "b64_json",
                },
                timeout=60,
            )

            if resp.status_code != 200:
                logger.warning(
                    f"Grok image API returned {resp.status_code}: {resp.text[:200]}"
                )
                return None

            data = resp.json()
            b64 = data.get("data", [{}])[0].get("b64_json")
            if not b64:
                logger.warning("No b64_json in Grok response")
                return None

            import base64
            img = Image.open(BytesIO(base64.b64decode(b64))).convert("RGB")
            logger.info(f"Grok image generated: {img.size}")
            return img

        except Exception as e:
            logger.error(f"Grok image generation failed: {e}")
            return None

    # ─── OPENAI FALLBACK ────────────────────────────────────────────

    def _generate_openai_image(self, title):
        """Last resort: OpenAI DALL-E (no white frames, better prompt)."""
        prompt = (
            f"Editorial photograph for news article: {title[:100]}. "
            "Cinematic, dramatic lighting, dark moody tones with deep reds and blacks. "
            "Photojournalism style. NO text, NO logos, NO borders, NO frames, NO watermarks. "
            "Full bleed image, edge to edge. Hyper-realistic photography.")

        try:
            resp = requests.post(
                "https://api.openai.com/v1/images/generations",
                headers={
                    "Authorization": f"Bearer {self.openai_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-image-1",
                    "prompt": prompt,
                    "n": 1,
                    "size": "1536x1024"
                },
                timeout=60,
            )

            if resp.status_code != 200:
                # Try DALL-E 3
                resp = requests.post(
                    "https://api.openai.com/v1/images/generations",
                    headers={
                        "Authorization": f"Bearer {self.openai_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "dall-e-3",
                        "prompt": prompt,
                        "n": 1,
                        "size": "1792x1024",
                        "quality": "hd"
                    },
                    timeout=60,
                )

            if resp.status_code == 200:
                data = resp.json()
                # Handle both URL and b64 responses
                item = data.get("data", [{}])[0]
                if "b64_json" in item:
                    import base64
                    return Image.open(
                        BytesIO(base64.b64decode(
                            item["b64_json"]))).convert("RGB")
                elif "url" in item:
                    img_resp = requests.get(item["url"], timeout=15)
                    if img_resp.status_code == 200:
                        return Image.open(BytesIO(
                            img_resp.content)).convert("RGB")

        except Exception as e:
            logger.error(f"OpenAI image generation failed: {e}")

        return None

    # ─── PURE FALLBACK (no API needed) ──────────────────────────────

    def _generate_fallback_image(self, title):
        """Generate a branded placeholder if all APIs fail."""
        img = Image.new("RGB", (TARGET_WIDTH, TARGET_HEIGHT), (10, 10, 10))
        draw = ImageDraw.Draw(img)

        # Red gradient bar at bottom
        for y in range(TARGET_HEIGHT - 80, TARGET_HEIGHT):
            alpha = (y - (TARGET_HEIGHT - 80)) / 80.0
            r = int(180 * alpha)
            draw.line([(0, y), (TARGET_WIDTH, y)], fill=(r, 0, 0))

        # Red accent line
        draw.line([(50, TARGET_HEIGHT - 90),
                   (TARGET_WIDTH - 50, TARGET_HEIGHT - 90)],
                  fill=(220, 38, 38),
                  width=2)

        return img

# ─── HELPER FUNCTIONS ──────────────────────────────────────────────

def _safe_filename(title):
    """Convert title to safe filename."""
    safe = re.sub(r'[^\w\s-]', '', title)
    safe = re.sub(r'\s+', '_', safe).strip('_')
    return safe[:80]

def _is_top_article(title):
    """Check if article deserves Grok generation (named people/brands)."""
    lower = title.lower()
    return any(indicator in lower for indicator in TOP_ARTICLE_INDICATORS)

def _build_pexels_queries(title, category=None):
    """Build search queries from article title, most specific to most general."""
    queries = []

    # Extract key concepts
    lower = title.lower()

    # Topic-specific mappings
    topic_queries = {
        'mining': [
            'bitcoin mining facility', 'data center servers',
            'industrial computing'
        ],
        'etf': [
            'stock market trading floor', 'wall street financial',
            'investment portfolio'
        ],
        'regulation': [
            'government capitol building', 'legal gavel courtroom',
            'legislative chamber'
        ],
        'lightning': [
            'digital network connections', 'fiber optic cables',
            'electronic circuit board'
        ],
        'defi': [
            'blockchain technology abstract', 'digital finance network',
            'futuristic banking'
        ],
        'whale':
        ['ocean deep water', 'financial trading screens', 'stock market data'],
        'fed': [
            'federal reserve building', 'monetary policy finance',
            'central banking'
        ],
        'inflation': [
            'economic charts data', 'currency money finance',
            'financial markets'
        ],
        'adoption': [
            'global technology innovation', 'digital transformation',
            'modern city technology'
        ],
        'security': [
            'cybersecurity digital lock', 'encrypted data protection',
            'secure vault'
        ],
        'energy': [
            'renewable energy solar', 'power grid electricity',
            'industrial energy'
        ],
        'ai': [
            'artificial intelligence technology', 'futuristic computer',
            'neural network'
        ],
        'quantum': [
            'quantum computing technology', 'advanced processor chip',
            'scientific research lab'
        ],
        'cbdc': [
            'central bank digital', 'government finance technology',
            'monetary system'
        ],
        'halving':
        ['bitcoin gold scarcity', 'precious metals vault', 'digital gold'],
    }

    for keyword, pexels_queries in topic_queries.items():
        if keyword in lower:
            queries.extend(pexels_queries[:2])

    # Generic financial/tech queries based on category
    if category:
        cat_lower = category.lower()
        if cat_lower in ('bitcoin', 'breakingbitcoin'):
            queries.append('cryptocurrency technology dark')
        elif cat_lower == 'opinion':
            queries.append('editorial newspaper desk')
        elif cat_lower == 'macro':
            queries.append('global economy financial markets')

    # Fallback generic queries
    queries.extend([
        'financial technology dark',
        'digital economy abstract',
        'modern technology dark background',
    ])

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for q in queries:
        if q not in seen:
            seen.add(q)
            unique.append(q)

    return unique[:5]  # Max 5 queries to avoid rate limits

def _build_grok_prompt(title):
    """Build a cinematic prompt for Grok image generation."""
    return (
        f"Hyper-realistic editorial photograph for the headline: '{title}'. "
        "Shot on a Canon EOS R5 with a 35mm lens. Dramatic cinematic lighting. "
        "Color palette: deep blacks, dark crimson reds, with touches of amber. "
        "Style: photojournalism meets film noir. "
        "NO text, NO typography, NO logos, NO coins, NO Bitcoin symbols. "
        "NO borders, NO frames, NO watermarks. Full bleed edge-to-edge. "
        "The image should tell the STORY behind the headline through visual metaphor. "
        "Mood: sophisticated, authoritative, like a TIME magazine cover photo."
    )

def _resize_and_crop(img, target_w, target_h):
    """Resize and center-crop to exact dimensions."""
    # Calculate aspect ratios
    img_ratio = img.width / img.height
    target_ratio = target_w / target_h

    if img_ratio > target_ratio:
        # Image is wider — fit height, crop width
        new_h = target_h
        new_w = int(target_h * img_ratio)
    else:
        # Image is taller — fit width, crop height
        new_w = target_w
        new_h = int(target_w / img_ratio)

    img = img.resize((new_w, new_h), Image.LANCZOS)

    # Center crop
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    img = img.crop((left, top, left + target_w, top + target_h))

    return img

def _apply_brand_overlay(img):
    """Apply subtle red/black brand overlay for cohesive look."""
    # Slightly darken the image
    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(0.75)

    # Boost contrast slightly
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.15)

    # Add subtle red tint via overlay
    overlay = Image.new("RGB", img.size, (40, 0, 0))
    img = Image.blend(img, overlay, alpha=0.08)

    # Add gradient vignette (darker edges)
    vignette = Image.new("L", img.size, 255)
    draw = ImageDraw.Draw(vignette)
    w, h = img.size
    for i in range(40):
        opacity = int(255 * (1 - i / 40.0) * 0.4)
        draw.rectangle([i, i, w - i - 1, h - i - 1], outline=opacity)

    # Apply vignette
    img_array = img.copy()
    r, g, b = img_array.split()
    r = Image.composite(r, Image.new("L", img.size, 0), vignette)
    g = Image.composite(g, Image.new("L", img.size, 0), vignette)
    b = Image.composite(b, Image.new("L", img.size, 0), vignette)
    img = Image.merge("RGB", (r, g, b))

    # Add thin red accent line at bottom
    draw = ImageDraw.Draw(img)
    draw.line([(0, h - 3), (w, h - 3)], fill=(220, 38, 38), width=2)

    return img

# Singleton instance (imported by other modules)
image_service = ImageGenerationService()

# Standalone function aliases (imported by other modules)
def generate_article_header_image(title, category=None):
    return image_service.generate_article_header_image(title, category)

def generate_opinion_header_image(title, category=None):
    return image_service.generate_article_header_image(title, category)
