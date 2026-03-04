#!/usr/bin/env python3
"""HeyGen API client for Protocol Pulse avatar video generation."""
import os
import json
import time
import requests
from typing import Optional

HEYGEN_API_BASE = "https://api.heygen.com/v2"
HEYGEN_V1_BASE = "https://api.heygen.com/v1"

# Avatar IDs
SARAH_AVATAR_ID = "d259c335741f4fc0b061e04c59388b4e"  # Photo Avatar III — $1/min
PBX_AVATAR_ID = "3be8ed14b0954b898f4127836c21f6cc"

# Voice IDs (HeyGen built-in)
SARAH_VOICE_ID = "5f745b3db0db43739f31499f4f0aedd6"  # Claire Lawson — Broadcaster
PBX_VOICE_ID = "054af44a167344d0af2722fdfef08d17"     # Thanos — Broadcaster


def _get_api_key():
    key = os.environ.get("HEYGEN_API_KEY")
    if not key:
        env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
        if os.path.exists(env_path):
            for line in open(env_path):
                if line.startswith("HEYGEN_API_KEY="):
                    key = line.strip().split("=", 1)[1].strip('"').strip("'")
    return key


def _headers():
    return {
        "X-Api-Key": _get_api_key(),
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def generate_avatar_video(
    text: str,
    avatar_id: str = SARAH_AVATAR_ID,
    voice_id: Optional[str] = None,
    title: str = "Oracle Briefing",
    width: int = 1920,
    height: int = 1080,
    test: bool = False,
) -> dict:
    """Generate an avatar video via HeyGen API.

    Returns: {"video_id": str, "status": str} on success
    """
    voice_config = {
        "type": "text",
        "input_text": text,
        "voice_id": voice_id or SARAH_VOICE_ID,
    }

    payload = {
        "video_inputs": [
            {
                "character": {
                    "type": "avatar",
                    "avatar_id": avatar_id,
                    "avatar_style": "normal",
                },
                "voice": voice_config,
            }
        ],
        "dimension": {"width": width, "height": height},
        "test": test,
    }

    resp = requests.post(
        f"{HEYGEN_API_BASE}/video/generate",
        headers=_headers(),
        json=payload,
        timeout=30,
    )

    if resp.status_code == 200:
        data = resp.json()
        return {
            "video_id": data.get("data", {}).get("video_id"),
            "status": "processing",
        }
    else:
        print(f"  [heygen] Error {resp.status_code}: {resp.text[:200]}")
        return {"error": resp.text, "status": "failed"}


def check_video_status(video_id: str) -> dict:
    """Check the status of a HeyGen video generation."""
    resp = requests.get(
        f"{HEYGEN_V1_BASE}/video_status.get",
        headers=_headers(),
        params={"video_id": video_id},
        timeout=15,
    )

    if resp.status_code == 200:
        data = resp.json().get("data", {})
        return {
            "status": data.get("status"),
            "video_url": data.get("video_url"),
            "thumbnail_url": data.get("thumbnail_url"),
            "duration": data.get("duration"),
        }
    return {"status": "unknown", "error": resp.text}


def wait_for_video(
    video_id: str, timeout: int = 300, poll_interval: int = 10
) -> dict:
    """Poll until video is ready or timeout."""
    start = time.time()
    while time.time() - start < timeout:
        status = check_video_status(video_id)
        if status["status"] == "completed":
            return status
        elif status["status"] == "failed":
            print(f"  [heygen] Video generation failed: {status}")
            return status
        time.sleep(poll_interval)
    return {"status": "timeout"}


def download_video(video_url: str, output_path: str) -> bool:
    """Download the completed video to local path."""
    try:
        resp = requests.get(video_url, stream=True, timeout=60)
        if resp.status_code == 200:
            with open(output_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            return os.path.exists(output_path)
    except Exception as e:
        print(f"  [heygen] Download error: {e}")
    return False


def generate_and_download(
    text: str,
    output_path: str,
    avatar_id: str = SARAH_AVATAR_ID,
    voice_id: Optional[str] = None,
    title: str = "Oracle Briefing",
    test: bool = False,
) -> Optional[str]:
    """Full pipeline: generate -> wait -> download. Returns output path or None."""
    print(
        f"  [heygen] Generating: {title} ({len(text)} chars, avatar={avatar_id[:8]}...)"
    )

    result = generate_avatar_video(text, avatar_id, voice_id, title, test=test)
    if "error" in result:
        return None

    video_id = result["video_id"]
    print(f"  [heygen] Video ID: {video_id} — waiting for render...")

    status = wait_for_video(video_id, timeout=300)
    if status["status"] != "completed":
        print(f"  [heygen] Failed: {status}")
        return None

    print(f"  [heygen] Completed! Duration: {status.get('duration')}s — downloading...")

    if download_video(status["video_url"], output_path):
        size_mb = os.path.getsize(output_path) / 1024 / 1024
        print(f"  [heygen] Saved: {output_path} ({size_mb:.1f} MB)")
        return output_path

    return None


def list_voices() -> list:
    """List available HeyGen voices."""
    resp = requests.get(
        f"{HEYGEN_V1_BASE}/voice.list",
        headers=_headers(),
        timeout=15,
    )
    if resp.status_code == 200:
        data = resp.json().get("data", {})
        # v1 returns "list", v2 returns "voices"
        return data.get("voices", data.get("list", []))
    return []


def list_avatars() -> list:
    """List available HeyGen avatars."""
    resp = requests.get(
        f"{HEYGEN_V1_BASE}/avatar.list",
        headers=_headers(),
        timeout=15,
    )
    if resp.status_code == 200:
        return resp.json().get("data", {}).get("avatars", [])
    return []


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "voices":
        voices = list_voices()
        for v in voices[:30]:
            print(
                f"{v.get('voice_id', '?')} | {v.get('name', '?')} | "
                f"{v.get('language', '?')} | {v.get('gender', '?')}"
            )
    elif len(sys.argv) > 1 and sys.argv[1] == "avatars":
        avatars = list_avatars()
        for a in avatars[:20]:
            print(
                f"{a.get('avatar_id', '?')} | {a.get('avatar_name', '?')} | "
                f"{a.get('gender', '?')}"
            )
    else:
        print("Usage: python3 heygen_client.py [voices|avatars]")
