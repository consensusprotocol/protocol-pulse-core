"""
Nostr Post Capture
===================
Fetches notable Nostr posts from relays and renders branded screenshot cards.
Soft dependency — pipeline continues if relays are unreachable.

Uses websocket-client for relay connections (NIP-01 protocol).
"""
import json
import logging
import textwrap
import time
from pathlib import Path
from typing import List, Optional

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger("NostrCapture")

# Relays to query
RELAYS = [
    "wss://relay.damus.io",
    "wss://nos.lol",
    "wss://relay.nostr.band",
]

# Monitored pubkeys (hex)
MONITORED_PUBKEYS = {
    "a341f45ff9758f570a21b000c17d4e53a3a497c8397f26c0e6d61e5acffc7a98": "Michael Saylor",
    "82341f882b6eabcd2ba7f1ef90aad961cf074af15b9ef44a09f9d2a8fbfbe6a2": "Jack Dorsey",
    "04c915daefee38317fa734444acee390a8269fe5810b2241e5e6dd343dfbecc9": "Matt Odell",
    "3bf0c63fcb93463407af97a5e5ee64fa883d107ef9e558472c4eb9aaaefa459d": "Fiatjaf",
    "84dee6e676e5bb67b4ad4e042cf70cbd8681155db535942fcc6a0533858a7240": "Edward Snowden",
    "eb587556d32b8179a9197e7b024e00402038b427d5786ccd3c58b4d63d5c8f4f": "Lyn Alden",
    "83e8237f7e733956c3a9dae5eb4fd9a7a503871828d26a68036d1f403706c965": "Jeff Booth",
}

# Design
W, H = 1920, 1080
BG_COLOR = (12, 10, 20)
CARD_BG = (24, 20, 38)
PURPLE = (130, 80, 220)
WHITE = (255, 255, 255)
GRAY = (156, 163, 175)
FONT_SANS_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"


def _font(path: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def fetch_notable_nostr(hours: int = 48, min_reactions: int = 3,
                        max_posts: int = 5, timeout_per_relay: int = 8) -> List[dict]:
    """
    Fetch notable Nostr posts from monitored pubkeys.

    Returns list of dicts:
        {author, pubkey, content, created_at, note_id, reactions}
    """
    import websocket

    since = int(time.time()) - (hours * 3600)
    authors = list(MONITORED_PUBKEYS.keys())

    all_events = {}

    for relay_url in RELAYS:
        try:
            logger.info(f"  Connecting to {relay_url}...")
            ws = websocket.create_connection(relay_url, timeout=timeout_per_relay)

            # Subscribe to kind 1 (text notes) from monitored authors
            sub_filter = {
                "kinds": [1],
                "authors": authors,
                "since": since,
            }
            ws.send(json.dumps(["REQ", "pulse_scan", sub_filter]))

            # Read events until EOSE or timeout
            start = time.time()
            while time.time() - start < timeout_per_relay:
                try:
                    ws.settimeout(3)
                    msg = ws.recv()
                    data = json.loads(msg)

                    if data[0] == "EVENT" and len(data) >= 3:
                        event = data[2]
                        event_id = event.get("id", "")
                        if event_id not in all_events:
                            all_events[event_id] = event

                    elif data[0] == "EOSE":
                        break

                except websocket.WebSocketTimeoutException:
                    break
                except Exception:
                    break

            ws.close()
            logger.info(f"  {relay_url}: {len(all_events)} events total")

        except Exception as e:
            logger.warning(f"  {relay_url}: connection failed — {e}")
            continue

    # Process events into structured posts
    posts = []
    for event_id, event in all_events.items():
        pubkey = event.get("pubkey", "")
        content = event.get("content", "").strip()
        created_at = event.get("created_at", 0)

        if not content or len(content) < 20:
            continue

        # Skip reply notes (have 'e' tags)
        tags = event.get("tags", [])
        is_reply = any(t[0] == "e" for t in tags if len(t) >= 2)
        if is_reply:
            continue

        author = MONITORED_PUBKEYS.get(pubkey, f"nostr:{pubkey[:12]}...")
        note_id = event_id

        posts.append({
            "author": author,
            "pubkey": pubkey,
            "content": content[:1000],
            "created_at": created_at,
            "note_id": note_id,
            "reactions": 0,  # Would need separate query for reaction count
            "source": "nostr",
        })

    # Sort by recency
    posts.sort(key=lambda p: p["created_at"], reverse=True)

    # Limit
    posts = posts[:max_posts]
    logger.info(f"  Nostr: {len(posts)} notable posts from {len(all_events)} events")
    return posts


def render_nostr_card(post: dict, output_path: str) -> Optional[str]:
    """
    Render a Nostr post as a branded 1920x1080 PNG card.
    Purple-themed (Nostr colors) with author info and content.
    """
    try:
        img = Image.new("RGB", (W, H), BG_COLOR)
        draw = ImageDraw.Draw(img)

        # Card background
        card_x, card_y = 200, 100
        card_w, card_h = W - 400, H - 200
        _draw_rounded_rect(draw, card_x, card_y, card_x + card_w, card_y + card_h,
                          radius=20, fill=CARD_BG)

        # Purple accent line at top
        draw.rectangle([card_x, card_y, card_x + card_w, card_y + 4], fill=PURPLE)

        font_name = _font(FONT_SANS_BOLD, 44)
        font_npub = _font(FONT_MONO, 22)
        font_text = _font(FONT_SANS, 36)
        font_badge = _font(FONT_SANS_BOLD, 22)
        font_wm = _font(FONT_MONO, 18)

        y = card_y + 50

        # Author name
        author = post.get("author", "Unknown")
        draw.text((card_x + 60, y), author, font=font_name, fill=WHITE)

        # "via Nostr" badge
        badge_text = "via Nostr"
        badge_bbox = font_badge.getbbox(badge_text)
        bw = badge_bbox[2] - badge_bbox[0]
        badge_x = card_x + card_w - bw - 80
        draw.rectangle([badge_x - 12, y + 5, badge_x + bw + 12, y + 38], fill=PURPLE)
        draw.text((badge_x, y + 8), badge_text, font=font_badge, fill=WHITE)

        y += 55

        # npub (truncated)
        pubkey = post.get("pubkey", "")
        npub_display = f"npub:{pubkey[:8]}...{pubkey[-4:]}" if len(pubkey) > 12 else pubkey
        draw.text((card_x + 60, y), npub_display, font=font_npub, fill=GRAY)
        y += 50

        # Divider
        draw.rectangle([card_x + 60, y, card_x + card_w - 60, y + 1], fill=(50, 45, 65))
        y += 25

        # Content with wrapping
        content = post.get("content", "")
        wrapped = textwrap.fill(content, width=52)
        lines = wrapped.split("\n")[:10]

        for line in lines:
            draw.text((card_x + 60, y), line, font=font_text, fill=WHITE)
            y += 48

        # Timestamp
        created_at = post.get("created_at", 0)
        if created_at:
            from datetime import datetime
            ts = datetime.utcfromtimestamp(created_at).strftime("%b %d, %Y at %H:%M UTC")
            draw.text((card_x + 60, card_y + card_h - 60), ts,
                     font=font_npub, fill=GRAY)

        # Red + purple accent lines at frame edges
        draw.rectangle([0, 0, W, 3], fill=PURPLE)
        draw.rectangle([0, H - 3, W, H], fill=PURPLE)

        # Watermark
        draw.text((W - 220, H - 35), "PULSE CHECK", font=font_wm, fill=(40, 35, 55))

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        img.save(output_path)
        logger.info(f"  Nostr card rendered: {post['author']}")
        return output_path

    except Exception as e:
        logger.error(f"  Nostr card render failed: {e}")
        return None


def _draw_rounded_rect(draw: ImageDraw.ImageDraw, x1: int, y1: int,
                       x2: int, y2: int, radius: int = 10,
                       fill: tuple = (0, 0, 0)):
    """Draw a rounded rectangle."""
    draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill)
    draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill)
    draw.pieslice([x1, y1, x1 + 2 * radius, y1 + 2 * radius], 180, 270, fill=fill)
    draw.pieslice([x2 - 2 * radius, y1, x2, y1 + 2 * radius], 270, 360, fill=fill)
    draw.pieslice([x1, y2 - 2 * radius, x1 + 2 * radius, y2], 90, 180, fill=fill)
    draw.pieslice([x2 - 2 * radius, y2 - 2 * radius, x2, y2], 0, 90, fill=fill)
