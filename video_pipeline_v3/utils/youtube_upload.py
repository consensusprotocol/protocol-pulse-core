"""YouTube Upload — resumable upload via YouTube Data API v3.

Requires OAuth2 tokens in config/youtube_tokens.json.
Run utils/setup_youtube_auth.py to configure.
"""
import json
import logging
import os
from datetime import datetime

logger = logging.getLogger("YouTubeUpload")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKENS_PATH = os.path.join(BASE, "config", "youtube_tokens.json")

MEANWHILE_LINK = "https://application.meanwhile.bm/start?referralCode=KKM73K"

DESCRIPTION_TEMPLATE = """{summary}

{chapters}

{show_notes}
---
Subscribe for daily Bitcoin intelligence: https://www.youtube.com/@ProtocolPulse?sub_confirmation=1

Meanwhile — Bitcoin-denominated life insurance:
{meanwhile_link}

Website: https://protocolpulse.io
Nostr: npub1protocolpulse
Twitter/X: @protocolpulse_

#Bitcoin #BTC #ProtocolPulse #DailyBrief #Cryptocurrency
"""

DEFAULT_TAGS = [
    "Bitcoin", "BTC", "cryptocurrency", "daily brief", "Protocol Pulse",
    "bitcoin news", "bitcoin today", "crypto news", "bitcoin analysis",
    "bitcoin price", "bitcoin update",
]


def _load_tokens() -> dict:
    """Load OAuth2 tokens from config file."""
    if not os.path.exists(TOKENS_PATH):
        return {}
    try:
        with open(TOKENS_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def _refresh_access_token(tokens: dict) -> str:
    """Refresh the OAuth2 access token using the refresh token."""
    import requests
    resp = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": tokens["client_id"],
        "client_secret": tokens["client_secret"],
        "refresh_token": tokens["refresh_token"],
        "grant_type": "refresh_token",
    }, timeout=30)
    if resp.status_code == 200:
        data = resp.json()
        tokens["access_token"] = data["access_token"]
        with open(TOKENS_PATH, "w") as f:
            json.dump(tokens, f, indent=2)
        return data["access_token"]
    logger.error(f"Token refresh failed: {resp.status_code} {resp.text[:200]}")
    return ""


def build_show_notes(clips: list) -> str:
    """Build SHOW NOTES section from clip data.

    Args:
        clips: List of clip dicts with channel, video_title, video_id keys.

    Returns:
        Formatted show notes string.
    """
    if not clips:
        return ""
    lines = ["--- SHOW NOTES ---", "Clips featured in this episode:"]
    for c in clips:
        channel = c.get("channel", "Unknown")
        title = c.get("video_title", c.get("title", "Untitled"))
        vid = c.get("video_id", "")
        url = f"https://www.youtube.com/watch?v={vid}" if vid else ""
        lines.append(f"  \u2022 {channel} \u2014 {title} \u2014 {url}")
    lines.append("")
    lines.append("Full episode transcripts and sources at protocolpulse.io")
    return "\n".join(lines)


def build_description(summary: str = "", chapters_text: str = "",
                      clips: list = None) -> str:
    """Build YouTube description from episode data."""
    show_notes = build_show_notes(clips or [])
    return DESCRIPTION_TEMPLATE.format(
        summary=summary or "Daily Bitcoin intelligence briefing from Protocol Pulse.",
        chapters=chapters_text or "",
        show_notes=show_notes,
        meanwhile_link=MEANWHILE_LINK,
    )


def build_tags(topics: list = None) -> list:
    """Build tag list with default + topic-specific tags."""
    tags = list(DEFAULT_TAGS)
    if topics:
        for topic in topics[:5]:
            tag = topic.strip()[:30]
            if tag and tag not in tags:
                tags.append(tag)
    return tags[:15]  # YouTube max ~500 chars, keep it safe


def upload_episode(video_path: str, title: str, description: str,
                   tags: list = None, thumbnail_path: str = "",
                   privacy: str = "unlisted") -> dict:
    """Upload episode to YouTube via resumable upload.

    Args:
        video_path: Path to the video file
        title: Video title
        description: Video description
        tags: List of tags
        thumbnail_path: Path to thumbnail image
        privacy: 'public', 'unlisted', or 'private'

    Returns:
        Dict with video_id, url, status, or error info
    """
    tokens = _load_tokens()
    if not tokens or not tokens.get("refresh_token"):
        logger.warning("No YouTube OAuth tokens. Run: python3 utils/setup_youtube_auth.py")
        return {
            "status": "no_auth",
            "message": "Run utils/setup_youtube_auth.py to configure YouTube OAuth2 tokens.",
        }

    if not os.path.exists(video_path):
        return {"status": "error", "message": f"Video not found: {video_path}"}

    try:
        import requests
    except ImportError:
        return {"status": "error", "message": "requests library not available"}

    # Refresh access token
    access_token = _refresh_access_token(tokens)
    if not access_token:
        return {"status": "error", "message": "Failed to refresh access token"}

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    # Step 1: Initialize resumable upload
    metadata = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": tags or DEFAULT_TAGS,
            "categoryId": "28",  # Science & Technology
            "defaultLanguage": "en",
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }

    init_url = (
        "https://www.googleapis.com/upload/youtube/v3/videos"
        "?uploadType=resumable&part=snippet,status"
    )

    resp = requests.post(init_url, headers=headers, json=metadata, timeout=30)
    if resp.status_code not in (200, 308):
        logger.error(f"Upload init failed: {resp.status_code} {resp.text[:300]}")
        return {"status": "error", "message": f"Upload init failed: {resp.status_code}"}

    upload_url = resp.headers.get("Location")
    if not upload_url:
        return {"status": "error", "message": "No upload URL in response"}

    # Step 2: Upload video content
    file_size = os.path.getsize(video_path)
    logger.info(f"Uploading {file_size / 1024 / 1024:.1f}MB to YouTube...")

    with open(video_path, "rb") as f:
        upload_headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "video/mp4",
            "Content-Length": str(file_size),
        }
        resp = requests.put(upload_url, headers=upload_headers, data=f, timeout=600)

    if resp.status_code not in (200, 201):
        logger.error(f"Upload failed: {resp.status_code} {resp.text[:300]}")
        return {"status": "error", "message": f"Upload failed: {resp.status_code}"}

    video_data = resp.json()
    video_id = video_data.get("id", "")

    logger.info(f"Upload complete: https://youtube.com/watch?v={video_id}")

    # Step 3: Set thumbnail (if provided)
    if thumbnail_path and os.path.exists(thumbnail_path) and video_id:
        thumb_url = (
            f"https://www.googleapis.com/upload/youtube/v3/thumbnails/set"
            f"?videoId={video_id}"
        )
        with open(thumbnail_path, "rb") as f:
            thumb_resp = requests.post(
                thumb_url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "image/png",
                },
                data=f,
                timeout=30,
            )
        if thumb_resp.status_code == 200:
            logger.info("Thumbnail set successfully")
        else:
            logger.warning(f"Thumbnail upload failed: {thumb_resp.status_code}")

    return {
        "status": "uploaded",
        "video_id": video_id,
        "url": f"https://youtube.com/watch?v={video_id}",
        "privacy": privacy,
    }
