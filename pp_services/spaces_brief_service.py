"""
X Spaces Intelligence Brief — Voice Delivery Service

Pulls top clips from get_best_space_clips(), generates a 60-second
narrated intelligence report, synthesizes via Kokoro af_heart (Eryn)
with ElevenLabs PBX fallback, delivers via Twilio call with <Play> verb.

Cron: 00 7 * * * (after morning brief)
"""
from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

BRIEF_DIR = Path("/tmp")
MAX_CLIPS = 3


# ── Script Generation ────────────────────────────────────────────────────────

def generate_spaces_brief_script(max_clips: int = MAX_CLIPS) -> str:
    """Pull top X Space clips and build a 60-second narration script.

    Returns the script text or raises on failure.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "x_spaces_scraper"))
    from scraper import get_best_space_clips

    result = get_best_space_clips(max_clips=max_clips)
    if not result or not result.get("clips"):
        raise RuntimeError("No X Spaces clips available in the last 24 hours")

    clips = result["clips"][:max_clips]

    # Build per-clip lines
    lines = []
    for i, clip in enumerate(clips, 1):
        speaker = clip.get("host_name") or clip.get("host_handle") or f"Speaker {i}"
        title = clip.get("space_title") or "an X Space"
        text = (clip.get("text") or "").strip()
        # Trim to ~2 sentences max for brevity
        if len(text) > 200:
            text = text[:197].rsplit(" ", 1)[0] + "..."
        lines.append(f"Signal {i}, {speaker} from {title}: {text}")

    # Aggregate sentiment from scores
    avg_score = sum(c.get("score", 0) for c in clips) / len(clips)
    if avg_score >= 15:
        sentiment = "Bullish"
    elif avg_score >= 8:
        sentiment = "Neutral"
    else:
        sentiment = "Bearish"

    script = (
        f"Protocol Pulse X Spaces Intelligence. "
        f"{len(clips)} signals from the last 24 hours. "
        + " ".join(lines)
        + f" Overall sentiment across Bitcoin X Spaces: {sentiment}. "
        + "Stay sovereign."
    )
    return script


# ── TTS Synthesis ────────────────────────────────────────────────────────────

def synthesize_brief(script: str, date_str: str | None = None) -> Path:
    """Synthesize the script to MP3 via Kokoro af_heart (local GPU).

    Falls back to ElevenLabs PBX voice if Kokoro fails.
    Returns the path to the output MP3.
    """
    if not date_str:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    out_path = BRIEF_DIR / f"spaces_brief_{date_str}.mp3"

    from pp_services.voice_brief_tts import generate_voice_audio
    try:
        generate_voice_audio(script, str(out_path), voice='af_heart')
        logger.info("Spaces brief synthesized (Kokoro): %s (%d bytes)", out_path, out_path.stat().st_size)
        return out_path
    except RuntimeError:
        raise
    except Exception as e:
        logger.error("voice_brief_tts failed: %s", e)
        raise RuntimeError(f"All TTS engines failed for spaces brief: {e}")


# ── Twilio Delivery ──────────────────────────────────────────────────────────

def deliver_via_call(date_str: str | None = None) -> dict:
    """Place a Twilio call that plays the pre-synthesized MP3 brief.

    Requires the Flask app to be serving /api/media/spaces-brief/<date>.
    """
    from pp_services.twilio_service import get_client, _from_number, send_sms

    if not date_str:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    pbx_number = os.environ.get("PBX_PHONE_NUMBER")
    if not pbx_number:
        raise RuntimeError("PBX_PHONE_NUMBER not set")

    base_url = os.environ.get("PROTOCOL_PULSE_BASE_URL", "https://protocolpulse.io")
    audio_url = f"{base_url}/api/media/spaces-brief/{date_str}"

    # Generate Kokoro outro audio via voice_brief_tts
    from pp_services.voice_brief_tts import generate_voice_audio
    import uuid as _uuid
    outro_filename = f"spaces_outro_{_uuid.uuid4().hex}.mp3"
    outro_path = f"/tmp/satomi_briefs/{outro_filename}"
    try:
        generate_voice_audio("End of X Spaces brief. Stay sovereign.", outro_path)
        outro_url = f"{base_url}/api/media/brief-audio/{outro_filename}"
    except Exception as e:
        logger.warning("Outro TTS failed, skipping outro: %s", e)
        outro_url = None

    twiml = f'<Response><Pause length="1"/><Play>{audio_url}</Play>'
    if outro_url:
        twiml += f'<Pause length="1"/><Play>{outro_url}</Play>'
    twiml += '</Response>'

    try:
        call = get_client().calls.create(
            twiml=twiml,
            from_=_from_number(),
            to=pbx_number,
            timeout=120,
        )
        logger.info("Spaces brief call initiated: %s to %s", call.sid, pbx_number)
        call_ok = True
    except Exception as e:
        logger.error("Spaces brief call failed: %s", e)
        call_ok = False

    # SMS fallback with script excerpt
    sms_ok = False
    brief_path = BRIEF_DIR / f"spaces_brief_{date_str}.mp3"
    if brief_path.exists():
        sms_ok = send_sms(
            pbx_number,
            f"[PROTOCOL PULSE] X Spaces brief ready: {audio_url}"
        )

    return {
        "success": call_ok or sms_ok,
        "call_delivered": call_ok,
        "sms_delivered": sms_ok,
        "audio_url": audio_url,
        "date": date_str,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ── Main Entry Point ─────────────────────────────────────────────────────────

def generate_and_deliver_spaces_brief() -> dict:
    """Full pipeline: generate script → synthesize → deliver via call."""
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    logger.info("=== X Spaces Brief Pipeline Start ===")

    # Step 1: Generate script
    script = generate_spaces_brief_script()
    logger.info("Script generated (%d chars): %s...", len(script), script[:120])

    # Step 2: Synthesize audio
    audio_path = synthesize_brief(script, date_str)
    logger.info("Audio synthesized: %s", audio_path)

    # Step 3: Deliver via Twilio call
    result = deliver_via_call(date_str)
    result["script_length"] = len(script)
    result["audio_path"] = str(audio_path)

    logger.info("=== X Spaces Brief Pipeline Complete: %s ===", result)
    return result


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

    # Load .env
    from pathlib import Path as _P
    env_path = _P(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

    import argparse
    parser = argparse.ArgumentParser(description="X Spaces Intelligence Brief")
    parser.add_argument("--script-only", action="store_true", help="Generate script only, no TTS or delivery")
    parser.add_argument("--no-call", action="store_true", help="Generate + synthesize but skip Twilio call")
    args = parser.parse_args()

    if args.script_only:
        script = generate_spaces_brief_script()
        print("SCRIPT:", script)
    elif args.no_call:
        script = generate_spaces_brief_script()
        print("SCRIPT:", script[:300])
        path = synthesize_brief(script)
        print("AUDIO:", path)
    else:
        result = generate_and_deliver_spaces_brief()
        print("RESULT:", result)
