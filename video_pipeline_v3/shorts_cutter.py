#!/usr/bin/env python3
"""Shorts Cutter V5 — generate vertical 9:16 shorts using Oracle avatar.

Picks the 3 most quotable one-liners from host dialogue.
Uses the Oracle avatar server for lip-synced shorts.
Falls back to text-on-dark if avatar is unavailable.
"""
import json
import logging
import os
import subprocess
import tempfile
import time

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

logger = logging.getLogger("ShortsCutter")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[shorts] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

BASE = os.path.dirname(os.path.abspath(__file__))
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
AVATAR_SERVER = "http://localhost:8200"

# Jessica's voice for avatar
AVATAR_VOICE_ID = "cgSgspJ2msm6clMCkdW9"


def ffprobe_duration(path: str) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path],
        capture_output=True, text=True,
    )
    try:
        return float(r.stdout.strip())
    except Exception:
        return 0.0


def _avatar_available() -> bool:
    """Check if Oracle avatar server is running."""
    if not HAS_REQUESTS:
        return False
    try:
        r = requests.get(f"{AVATAR_SERVER}/health", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def create_avatar_short(text: str, headline: str, output_path: str,
                        btc_price: str = "", short_index: int = 0) -> str:
    """Generate a vertical short with avatar lip-syncing the text.

    1. Call avatar server to generate lip-synced video
    2. Resize/crop to 1080x1920 vertical
    3. Add branded overlay (title text, BTC price, branding)

    Falls back to text-on-dark if avatar server is unavailable.
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    # Try avatar server first
    if _avatar_available():
        logger.info(f"  Short #{short_index+1}: generating avatar video...")
        avatar_mp4 = output_path + ".avatar_raw.mp4"

        try:
            # Generate audio via ElevenLabs first, then send to avatar
            from relay import get_key
            from tts_engine import tts_elevenlabs

            tts_path = output_path + ".tts.m4a"
            if tts_elevenlabs(text, tts_path, host=1):
                # Read audio and send to avatar server
                import base64
                with open(tts_path, "rb") as f:
                    audio_b64 = base64.b64encode(f.read()).decode()

                resp = requests.post(
                    f"{AVATAR_SERVER}/generate",
                    json={
                        "audio_base64": audio_b64,
                        "content_type": "audio/mp4",
                        "enable_blinks": True,
                        "enable_head_movement": True,
                        "fps": 30,
                    },
                    timeout=120,
                )

                if resp.status_code == 200:
                    with open(avatar_mp4, "wb") as f:
                        f.write(resp.content)

                    if os.path.exists(avatar_mp4) and os.path.getsize(avatar_mp4) > 1000:
                        # Convert to vertical with overlays
                        result = _add_short_overlays(avatar_mp4, headline, output_path,
                                                      btc_price, short_index)
                        # Cleanup
                        for tmp in [avatar_mp4, tts_path]:
                            if os.path.exists(tmp):
                                try:
                                    os.remove(tmp)
                                except OSError:
                                    pass
                        if result:
                            return result
                else:
                    logger.warning(f"  Avatar server returned {resp.status_code}")

            # Cleanup TTS if avatar failed
            if os.path.exists(tts_path):
                try:
                    os.remove(tts_path)
                except OSError:
                    pass

        except Exception as e:
            logger.warning(f"  Avatar generation failed: {e}")

    # Fallback: TTS audio with text-on-dark vertical video
    logger.info(f"  Short #{short_index+1}: fallback (text-on-dark)...")
    return _create_text_short(text, headline, output_path, btc_price, short_index)


def _add_short_overlays(avatar_video: str, headline: str, output_path: str,
                         btc_price: str = "", short_index: int = 0) -> str:
    """Add branded overlays to avatar video and convert to 1080x1920 vertical."""
    dur = ffprobe_duration(avatar_video)
    if dur <= 0:
        return ""

    safe_headline = headline.replace("'", "").replace(":", " -").replace('"', '').replace("%", " pct")

    # Word-wrap headline for bottom overlay
    words = safe_headline.split()
    lines = []
    cur = ""
    for w in words:
        if len(cur) + len(w) + 1 > 28:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    lines = lines[:3]

    headline_filters = ""
    for i, line in enumerate(lines):
        y = 1500 + i * 55
        headline_filters += (
            f"drawtext=fontfile={FONT_BOLD}:text='{line}':"
            f"fontcolor=white:fontsize=42:borderw=3:bordercolor=black:"
            f"x=(w-text_w)/2:y={y},"
        )

    btc_text = btc_price.replace("'", "") if btc_price else ""
    btc_filter = ""
    if btc_text:
        btc_filter = (
            f"drawtext=fontfile={FONT_MONO}:text='BTC {btc_text}':"
            f"fontcolor=0xCC0000:fontsize=24:x=w-text_w-20:y=50,"
        )

    fg = (
        f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
        f"drawbox=x=0:y=0:w=1080:h=80:c=0x0A0A0A@0.7:t=fill,"
        f"drawtext=fontfile={FONT_BOLD}:text='PULSE CHECK':"
        f"fontcolor=white:fontsize=32:x=(w-text_w)/2:y=25,"
        f"{btc_filter}"
        f"{headline_filters}"
        f"drawbox=x=0:y=1820:w=1080:h=100:c=0x0A0A0A@0.8:t=fill,"
        f"drawtext=fontfile={FONT_MONO}:text='@ProtocolPulse':"
        f"fontcolor=0xCC0000:fontsize=28:x=(w-text_w)/2:y=1845,"
        f"format=yuv420p[v];\n"
        f"[0:a]loudnorm=I=-16:TP=-1.5:LRA=11[a]"
    )

    fd, fpath = tempfile.mkstemp(suffix=".txt")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(fg)
        cmd = [
            "ffmpeg", "-y", "-i", avatar_video,
            "-filter_complex_script", fpath,
            "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-crf", "22", "-preset", "fast",
            "-c:a", "aac", "-ar", "44100", "-b:a", "128k",
            "-t", str(min(dur, 59)),
            output_path,
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            logger.error(f"  Short overlay failed: {r.stderr[-300:]}")
            return ""
    finally:
        os.unlink(fpath)

    out_dur = ffprobe_duration(output_path)
    sz = os.path.getsize(output_path) // 1024
    logger.info(f"  Short #{short_index+1}: {out_dur:.1f}s, {sz}KB (avatar)")
    return output_path


def _create_text_short(text: str, headline: str, output_path: str,
                       btc_price: str = "", short_index: int = 0) -> str:
    """Fallback: generate a vertical short with TTS audio + text overlay on dark bg."""
    from tts_engine import tts_elevenlabs

    tts_path = output_path + ".tts.m4a"
    if not tts_elevenlabs(text, tts_path, host=1):
        logger.error(f"  TTS failed for short #{short_index+1}")
        return ""

    dur = ffprobe_duration(tts_path)
    if dur <= 0:
        return ""

    safe_text = text[:120].replace("'", "").replace('"', '').replace(":", " -").replace("%", " pct")
    safe_headline = headline[:60].replace("'", "").replace('"', '').replace(":", " -")

    # Word-wrap text
    words = safe_text.split()
    lines = []
    cur = ""
    for w in words:
        if len(cur) + len(w) + 1 > 30:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)

    text_filters = ""
    for i, line in enumerate(lines[:5]):
        y = 750 + i * 55
        text_filters += (
            f"drawtext=fontfile={FONT_BOLD}:text='{line}':"
            f"fontcolor=white:fontsize=40:borderw=2:bordercolor=black:"
            f"x=(w-text_w)/2:y={y},"
        )

    fg = (
        f"color=c=0x080808:s=1080x1920:d={dur}:r=30,"
        f"drawbox=x=0:y=0:w=1080:h=80:c=0x0A0A0A@0.7:t=fill,"
        f"drawtext=fontfile={FONT_BOLD}:text='PULSE CHECK':"
        f"fontcolor=white:fontsize=32:x=(w-text_w)/2:y=25,"
        f"{text_filters}"
        f"drawbox=x=0:y=1820:w=1080:h=100:c=0x0A0A0A@0.8:t=fill,"
        f"drawtext=fontfile={FONT_MONO}:text='@ProtocolPulse':"
        f"fontcolor=0xCC0000:fontsize=28:x=(w-text_w)/2:y=1845,"
        f"format=yuv420p[v];\n"
        f"[1:a]loudnorm=I=-16:TP=-1.5:LRA=11[a]"
    )

    fd, fpath = tempfile.mkstemp(suffix=".txt")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(fg)
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"color=c=0x080808:s=1080x1920:d={dur}:r=30",
            "-i", tts_path,
            "-filter_complex_script", fpath,
            "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-crf", "22", "-preset", "fast",
            "-c:a", "aac", "-ar", "44100", "-b:a", "128k",
            "-t", str(min(dur, 59)),
            output_path,
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            logger.error(f"  Short text fallback failed: {r.stderr[-300:]}")
            return ""
    finally:
        os.unlink(fpath)
        if os.path.exists(tts_path):
            try:
                os.remove(tts_path)
            except OSError:
                pass

    out_dur = ffprobe_duration(output_path)
    sz = os.path.getsize(output_path) // 1024
    logger.info(f"  Short #{short_index+1}: {out_dur:.1f}s, {sz}KB (text fallback)")
    return output_path


def generate_shorts(script: dict, output_dir: str, btc_price: str = "",
                    max_shorts: int = 3) -> list:
    """Generate vertical shorts from the script's best quotes.

    Uses shorts_quotes from the script, or picks from dialogue reactions.
    """
    os.makedirs(output_dir, exist_ok=True)

    # Get quotes for shorts
    quotes = script.get("shorts_quotes", [])
    if not quotes or len(quotes) < max_shorts:
        # Pick from dialogue reactions
        for entry in script.get("dialogue", []):
            if entry.get("type") in ("react", "wrap") and entry.get("host") in (1, 2, "1", "2"):
                text = entry.get("text", "")
                if 20 <= len(text) <= 150:
                    quotes.append(text)
            if len(quotes) >= max_shorts:
                break

    headlines = script.get("segments_summary", [])
    episode_title = script.get("episode_title", "Pulse Check")

    shorts = []
    for i, quote in enumerate(quotes[:max_shorts]):
        headline = headlines[i] if i < len(headlines) else episode_title
        short_path = os.path.join(output_dir, f"short_{i+1}.mp4")
        result = create_avatar_short(
            quote, headline, short_path,
            btc_price=btc_price, short_index=i,
        )
        if result:
            shorts.append(result)

    logger.info(f"Generated {len(shorts)}/{max_shorts} shorts")
    return shorts


if __name__ == "__main__":
    from script_writer import generate_sample_script
    script = generate_sample_script()
    out_dir = os.path.join(BASE, "output", "test_shorts_v5")
    shorts = generate_shorts(script, out_dir, btc_price="$97,000")
    print(f"Generated {len(shorts)} shorts")
