"""
Tweet Card Renderer
====================
Generates branded tweet images for video overlays.
3 fallback levels — always produces an image:

1. Primary: Pillow-rendered branded card (1920x1080)
2. Secondary: Puppeteer screenshot + watermark (if available)
3. Tertiary: Simple white-text-on-dark card (always works)
"""
import os
import json
import logging
import textwrap
from pathlib import Path
from typing import Optional

logger = logging.getLogger("TweetCardRenderer")

# Brand colors
BG_COLOR = (18, 18, 24)        # Dark background
TEXT_COLOR = (255, 255, 255)    # White text
ACCENT_COLOR = (220, 38, 38)   # PP red
HANDLE_COLOR = (156, 163, 175) # Gray for handles
CARD_SIZE = (1920, 1080)


class TweetCardRenderer:
    """Render tweet images with 3 fallback levels."""

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def render(self, tweet: dict, index: int = 0) -> Optional[str]:
        """
        Render a tweet card. Returns output path or None.
        Tries: Pillow → Puppeteer → Simple fallback.
        """
        output_path = self.output_dir / f"tweet_card_{index:02d}.png"

        # Level 1: Pillow branded card
        result = self._render_pillow(tweet, output_path)
        if result:
            return str(result)

        # Level 2: Puppeteer screenshot (if available)
        result = self._render_puppeteer(tweet, output_path)
        if result:
            return str(result)

        # Level 3: Simple text card (always works)
        result = self._render_simple(tweet, output_path)
        if result:
            return str(result)

        logger.error(f"  All render levels failed for tweet from {tweet.get('author_handle', '?')}")
        return None

    def _render_pillow(self, tweet: dict, output_path: Path) -> Optional[Path]:
        """Level 1: Full branded card via Pillow."""
        try:
            from PIL import Image, ImageDraw, ImageFont

            img = Image.new("RGB", CARD_SIZE, BG_COLOR)
            draw = ImageDraw.Draw(img)

            # Try to load fonts, fallback to default
            try:
                font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
                font_text = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 40)
                font_handle = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
                font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
            except (OSError, IOError):
                try:
                    font_large = ImageFont.truetype("arial.ttf", 48)
                    font_text = ImageFont.truetype("arial.ttf", 40)
                    font_handle = ImageFont.truetype("arial.ttf", 32)
                    font_small = ImageFont.truetype("arial.ttf", 24)
                except (OSError, IOError):
                    font_large = ImageFont.load_default()
                    font_text = font_large
                    font_handle = font_large
                    font_small = font_large

            # Red accent line (left side)
            draw.rectangle([0, 0, 8, CARD_SIZE[1]], fill=ACCENT_COLOR)

            # Author info
            author = tweet.get("author_name", "")
            handle = tweet.get("author_handle", "")
            y = 120

            draw.text((80, y), author, fill=TEXT_COLOR, font=font_large)
            y += 65
            draw.text((80, y), handle, fill=HANDLE_COLOR, font=font_handle)
            y += 80

            # Tweet text — word wrap
            text = tweet.get("text", "")
            wrapped = textwrap.fill(text, width=55)
            lines = wrapped.split("\n")[:8]  # Max 8 lines

            for line in lines:
                draw.text((80, y), line, fill=TEXT_COLOR, font=font_text)
                y += 55

            # Engagement stats at bottom
            likes = tweet.get("likes", 0)
            rts = tweet.get("retweets", 0)
            stats = f"♥ {likes:,}    ⟲ {rts:,}"
            draw.text((80, CARD_SIZE[1] - 100), stats, fill=HANDLE_COLOR, font=font_handle)

            # PP watermark
            draw.text((CARD_SIZE[0] - 350, CARD_SIZE[1] - 60),
                       "PROTOCOL PULSE", fill=(80, 80, 100), font=font_small)

            img.save(str(output_path), "PNG")
            logger.info(f"  Tweet card rendered (Pillow): {output_path.name}")
            return output_path

        except ImportError:
            logger.debug("  Pillow not available, trying fallback")
            return None
        except Exception as e:
            logger.warning(f"  Pillow render failed: {e}")
            return None

    def _render_puppeteer(self, tweet: dict, output_path: Path) -> Optional[Path]:
        """Level 2: Puppeteer screenshot + watermark."""
        try:
            import subprocess
            # Check if puppeteer/chromium available
            result = subprocess.run(["which", "chromium"], capture_output=True, timeout=5)
            if result.returncode != 0:
                result = subprocess.run(["which", "google-chrome"], capture_output=True, timeout=5)
                if result.returncode != 0:
                    return None

            # Build minimal HTML for screenshot
            html = f"""<html><body style="background:#121218;color:white;font-family:sans-serif;
            padding:60px;width:1800px;height:960px;">
            <div style="border-left:8px solid #dc2626;padding-left:40px;">
            <h2>{tweet.get('author_name', '')}</h2>
            <p style="color:#9ca3af;">{tweet.get('author_handle', '')}</p>
            <p style="font-size:36px;line-height:1.5;">{tweet.get('text', '')}</p>
            </div></body></html>"""

            html_path = output_path.with_suffix(".html")
            html_path.write_text(html)

            browser = result.stdout.decode().strip()
            subprocess.run([
                browser, "--headless", "--disable-gpu",
                f"--screenshot={output_path}",
                "--window-size=1920,1080",
                str(html_path)
            ], capture_output=True, timeout=15)

            html_path.unlink(missing_ok=True)

            if output_path.exists() and output_path.stat().st_size > 1000:
                logger.info(f"  Tweet card rendered (Puppeteer): {output_path.name}")
                return output_path

            return None

        except Exception as e:
            logger.debug(f"  Puppeteer render failed: {e}")
            return None

    def _render_simple(self, tweet: dict, output_path: Path) -> Optional[Path]:
        """Level 3: Simple text card. Always works if any image library exists."""
        try:
            from PIL import Image, ImageDraw, ImageFont

            img = Image.new("RGB", CARD_SIZE, BG_COLOR)
            draw = ImageDraw.Draw(img)

            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
            except (OSError, IOError):
                font = ImageFont.load_default()

            # Simple centered text
            text = tweet.get("text", "")
            author = tweet.get("author_handle", "")
            wrapped = textwrap.fill(text, width=50)

            y = 200
            for line in wrapped.split("\n")[:10]:
                draw.text((100, y), line, fill=TEXT_COLOR, font=font)
                y += 50

            draw.text((100, y + 40), f"— {author}", fill=HANDLE_COLOR, font=font)

            img.save(str(output_path), "PNG")
            logger.info(f"  Tweet card rendered (simple): {output_path.name}")
            return output_path

        except ImportError:
            logger.error("  No image rendering library available")
            return None
        except Exception as e:
            logger.error(f"  Simple render failed: {e}")
            return None
