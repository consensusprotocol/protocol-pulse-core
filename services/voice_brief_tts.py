"""
Voice Brief TTS — Kokoro af_heart (Eryn) for Twilio voice calls.
Generates MP3 audio from text, with ElevenLabs PBX fallback.
"""
import os
import sys
import subprocess
import logging
import numpy as np

logger = logging.getLogger(__name__)

# Lazy-loaded Kokoro pipeline
_kokoro_pipeline = None
_kokoro_ready = None  # None=untried, True/False


def _init_kokoro():
    """Initialize Kokoro PyTorch pipeline (lazy, one-shot)."""
    global _kokoro_pipeline, _kokoro_ready
    if _kokoro_ready is not None:
        return _kokoro_ready
    try:
        from kokoro import KPipeline
        _kokoro_pipeline = KPipeline(lang_code='a')
        _kokoro_ready = True
        logger.info("[voice_brief_tts] Kokoro PyTorch initialized")
        return True
    except Exception as e:
        logger.warning("[voice_brief_tts] Kokoro init failed: %s", e)
        _kokoro_ready = False
        return False


def _generate_kokoro(text: str, output_path: str, voice: str = 'af_heart',
                     speed: float = 1.0) -> bool:
    """Synthesize text with Kokoro, encode to MP3 via ffmpeg."""
    if not _init_kokoro():
        return False
    try:
        import soundfile as sf
        samples_list = []
        for _, _, audio in _kokoro_pipeline(text, voice=voice, speed=speed):
            samples_list.append(audio)
        if not samples_list:
            return False
        audio_np = np.concatenate(samples_list) if len(samples_list) > 1 else samples_list[0]
        wav_tmp = output_path + '.kokoro.wav'
        sf.write(wav_tmp, audio_np, 24000)
        if not os.path.exists(wav_tmp) or os.path.getsize(wav_tmp) < 500:
            return False
        # Encode WAV → MP3 (Twilio needs standard format)
        r = subprocess.run([
            'ffmpeg', '-y', '-i', wav_tmp,
            '-ar', '44100', '-ac', '1', '-b:a', '128k', output_path
        ], capture_output=True, text=True, timeout=60)
        try:
            os.remove(wav_tmp)
        except OSError:
            pass
        ok = r.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 1000
        if ok:
            logger.info("[voice_brief_tts] Kokoro OK: %s", output_path)
        return ok
    except Exception as e:
        logger.error("[voice_brief_tts] Kokoro error: %s", e)
        return False


def _generate_elevenlabs(text: str, output_path: str) -> bool:
    """Fallback: ElevenLabs PBX voice."""
    try:
        import requests as req
        api_key = os.getenv('ELEVENLABS_API_KEY', '')
        if not api_key:
            logger.error("[voice_brief_tts] No ELEVENLABS_API_KEY for fallback")
            return False
        voice_id = 'HmUVvDlHsEz0m3eUGLgu'  # PBX
        url = f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}'
        resp = req.post(url, json={
            'text': text,
            'model_id': 'eleven_turbo_v2_5',
            'voice_settings': {
                'stability': 0.55,
                'similarity_boost': 0.80,
            },
        }, headers={
            'xi-api-key': api_key,
            'Accept': 'audio/mpeg',
        }, timeout=30)
        if resp.status_code != 200:
            logger.error("[voice_brief_tts] ElevenLabs %d: %s", resp.status_code, resp.text[:200])
            return False
        with open(output_path, 'wb') as f:
            f.write(resp.content)
        ok = os.path.getsize(output_path) > 1000
        if ok:
            logger.info("[voice_brief_tts] ElevenLabs fallback OK: %s", output_path)
        return ok
    except Exception as e:
        logger.error("[voice_brief_tts] ElevenLabs error: %s", e)
        return False


def generate_voice_audio(text: str, output_path: str, voice: str = 'af_heart') -> str:
    """Generate voice audio from text. Returns output_path on success, raises on total failure.

    Primary: Kokoro af_heart (local GPU)
    Fallback: ElevenLabs PBX voice
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    if _generate_kokoro(text, output_path, voice=voice):
        return output_path

    logger.warning("[voice_brief_tts] Kokoro failed, trying ElevenLabs fallback")
    if _generate_elevenlabs(text, output_path):
        return output_path

    raise RuntimeError(f"All TTS backends failed for: {text[:80]}")
