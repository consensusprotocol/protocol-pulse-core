"""
ASSEMBLE PULSE
===============
Voiceover generation via ElevenLabs and assembly manifest helpers.
Used by the intelligence pipeline to create narrated highlight reels.
"""

import os
import logging
from pathlib import Path
from typing import Optional
import requests

logger = logging.getLogger("AssemblePulse")

VOICEOVER_DIR = Path("data/video_engine/voiceovers")
VOICEOVER_DIR.mkdir(parents=True, exist_ok=True)

ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
ELEVENLABS_URL = "https://api.elevenlabs.io/v1/text-to-speech"


def generate_voiceover(text: str, output_name: str) -> Optional[Path]:
    """
    Generate a voiceover audio file using ElevenLabs.

    Args:
        text: The text to speak.
        output_name: Name for the output file (without extension).

    Returns:
        Path to the generated audio file, or None on failure.
    """
    if not ELEVENLABS_API_KEY:
        logger.warning("No ELEVENLABS_API_KEY set, skipping voiceover generation")
        return None

    output_path = VOICEOVER_DIR / f"{output_name}.mp3"

    if output_path.exists() and output_path.stat().st_size > 1000:
        logger.info(f"  Voiceover cached: {output_name}")
        return output_path

    try:
        resp = requests.post(
            f"{ELEVENLABS_URL}/{ELEVENLABS_VOICE_ID}",
            headers={
                "xi-api-key": ELEVENLABS_API_KEY,
                "Content-Type": "application/json"
            },
            json={
                "text": text,
                "model_id": "eleven_turbo_v2_5",
                "voice_settings": {
                    "stability": 0.6,
                    "similarity_boost": 0.8,
                    "style": 0.2,
                    "use_speaker_boost": True
                }
            },
            timeout=30
        )

        if resp.status_code == 200:
            output_path.write_bytes(resp.content)
            logger.info(f"  Voiceover generated: {output_name} ({len(resp.content) / 1024:.1f} KB)")
            return output_path
        else:
            logger.error(f"ElevenLabs error {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        logger.error(f"Voiceover generation failed: {e}")

    return None


def build_assembly_manifest(today: str, selected_highlights: list, date_display: str) -> dict:
    """
    Build the manifest dict to send to Ultron /assemble_advanced.

    Args:
        today: Date string (YYYY-MM-DD).
        selected_highlights: List of highlight dicts (must have clip_filename, voiceover_file, channel_name).
        date_display: Human-readable date for intro.

    Returns:
        Assembly manifest dict.
    """
    return {
        "output_name": f"pulse_check_{today}.mp4",
        "intro_voiceover": f"pulse_{today}_intro.mp3",
        "outro_voiceover": f"pulse_{today}_outro.mp3",
        "date_text": date_display,
        "segments": [
            {
                "clip": h.get("clip_filename", ""),
                "voiceover": h.get("voiceover_file", ""),
                "channel_name": h["channel_name"],
                "lower_third_text": h["channel_name"]
            }
            for h in selected_highlights if h.get("clip_filename")
        ]
    }


def get_intro_text(date_display: str, top_themes: list) -> str:
    """Generate intro voiceover text."""
    if top_themes:
        theme_str = " and ".join(top_themes[:2])
        return f"Welcome to your Pulse Check for {date_display}. Today's focus: {theme_str}."
    return f"Welcome to your Pulse Check for {date_display}. Here's what's making waves in Bitcoin."


def get_outro_text() -> str:
    """Generate outro voiceover text."""
    return "That's your Pulse Check for today. Stay sovereign, stack sats."


def get_transition_text(channel_name: str, narrator_intro: str = "") -> str:
    """Generate transition voiceover text between clips."""
    if narrator_intro:
        return narrator_intro
    return f"Here's {channel_name}."
