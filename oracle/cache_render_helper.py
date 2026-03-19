#!/usr/bin/env python3
"""
Cache Render Helper — standalone TTS + Wav2Lip pipeline for cache pre-generation.
Usage: python3 cache_render_helper.py --text "Hello world" --out cache/responses/GREETING.mp4
"""

import os
import sys
import argparse
import tempfile
import subprocess
import time
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("cache_render_helper")

ORACLE_DIR = os.path.dirname(os.path.abspath(__file__))
VOICE_ID = "cgSgspJ2msm6clMCkdW9"  # Jessica (ElevenLabs fallback)

_KOKORO_PIPELINE = None


def _init_kokoro():
    """Lazy-init Kokoro KPipeline for af_heart."""
    global _KOKORO_PIPELINE
    if _KOKORO_PIPELINE is not None:
        return True
    try:
        from kokoro import KPipeline
        _KOKORO_PIPELINE = KPipeline(lang_code='a')
        logger.info("[CACHE_TTS] Kokoro af_heart pipeline loaded")
        return True
    except Exception as e:
        logger.warning(f"[CACHE_TTS] Kokoro init failed: {e}")
        return False


def get_elevenlabs_key():
    key = os.environ.get("ELEVENLABS_API_KEY", "")
    if not key:
        env_path = os.path.join(ORACLE_DIR, "..", ".env")
        if os.path.exists(env_path):
            for line in open(env_path):
                if line.startswith("ELEVENLABS_API_KEY="):
                    key = line.strip().split("=", 1)[1].strip().strip("\"'")
    return key


def tts_elevenlabs(text, voice_id=VOICE_ID):
    """Call ElevenLabs TTS, return mp3 bytes."""
    import requests
    api_key = get_elevenlabs_key()
    if not api_key:
        raise ValueError("ELEVENLABS_API_KEY not found")
    resp = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
        headers={"xi-api-key": api_key, "Content-Type": "application/json"},
        json={
            "text": text,
            "model_id": "eleven_turbo_v2_5",
            "voice_settings": {"stability": 0.45, "similarity_boost": 0.75, "style": 0.20},
        },
        timeout=60,
    )
    if resp.status_code != 200:
        raise Exception(f"ElevenLabs error {resp.status_code}: {resp.text[:200]}")
    return resp.content


def tts(text, voice_id=VOICE_ID):
    """Primary: Kokoro af_heart -> WAV bytes. Fallback: ElevenLabs -> MP3 bytes."""
    # Try Kokoro first
    if _init_kokoro():
        try:
            import numpy as np
            import soundfile as sf
            samples_list = []
            for _, _, audio in _KOKORO_PIPELINE(text, voice="af_heart", speed=1.0):
                samples_list.append(audio)
            if samples_list:
                audio_np = np.concatenate(samples_list) if len(samples_list) > 1 else samples_list[0]
                wav_tmp = tempfile.mktemp(suffix=".wav")
                sf.write(wav_tmp, audio_np, 24000)
                with open(wav_tmp, "rb") as f:
                    wav_bytes = f.read()
                try:
                    os.remove(wav_tmp)
                except OSError:
                    pass
                if len(wav_bytes) > 1000:
                    logger.info(f"[CACHE_TTS] Kokoro OK: {len(wav_bytes)} bytes")
                    return wav_bytes
        except Exception as e:
            logger.warning(f"[CACHE_TTS] Kokoro FAILED: {e} → ElevenLabs fallback")
    # Fallback: ElevenLabs
    logger.info("[CACHE_TTS] Using ElevenLabs fallback")
    return tts_elevenlabs(text, voice_id)


def render(text, out_path, voice_id=VOICE_ID):
    """Full pipeline: TTS -> wav -> avatar_server /generate -> save mp4."""
    t0 = time.time()

    # Step 1: TTS (Kokoro primary, ElevenLabs fallback)
    logger.info(f"TTS for {len(text)} chars...")
    audio_bytes = tts(text, voice_id)
    logger.info(f"TTS done: {len(audio_bytes)} bytes in {time.time()-t0:.1f}s")

    # Step 2: Call avatar_server /generate endpoint (it handles Wav2Lip internally)
    import requests
    import base64

    # Detect content type: Kokoro returns WAV (RIFF header), ElevenLabs returns MP3
    audio_b64 = base64.b64encode(audio_bytes).decode()
    content_type = "audio/wav" if audio_bytes[:4] == b"RIFF" else "audio/mpeg"

    resp = requests.post(
        "http://localhost:8200/generate",
        json={
            "audio_base64": audio_b64,
            "content_type": content_type,
            "enable_head_movement": True,
            "fps": 30,
        },
        timeout=120,
    )

    if resp.status_code != 200:
        raise Exception(f"Avatar server error {resp.status_code}: {resp.text[:200]}")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(resp.content)

    duration = resp.headers.get("X-Duration", "?")
    proc_time = resp.headers.get("X-Processing-Time", "?")
    logger.info(f"Rendered {out_path} — duration={duration}s, processing={proc_time}s, total={time.time()-t0:.1f}s")
    return out_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cache render helper")
    parser.add_argument("--text", required=True, help="Text to render")
    parser.add_argument("--out", required=True, help="Output mp4 path")
    parser.add_argument("--voice", default=VOICE_ID, help="ElevenLabs voice ID")
    args = parser.parse_args()

    render(args.text, args.out, args.voice)
