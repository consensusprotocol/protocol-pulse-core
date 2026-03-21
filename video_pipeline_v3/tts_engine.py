#!/usr/bin/env python3
"""TTS Engine V10 — Dual-host local TTS pipeline.
Host 1: Kokoro af_heart (female) — setup/bridge.
Host 2: Chatterbox TTS PBX (male) — react/wrap.
Fallback: ElevenLabs per-line. TTS_PROVIDER=local (default) or elevenlabs.
Generates per-line audio with 0.3s silence gaps."""
import os, sys, json, subprocess, tempfile, time, struct, shutil, logging
from pathlib import Path

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

from relay import get_key

logger = logging.getLogger(__name__)

# ── LOCAL TTS BACKENDS ──────────────────────────────────────────────────────
_KOKORO_PIPELINE = None
_KOKORO_BACKEND = None
_KOKORO_INSTANCE = None
_F5_MODEL = None
_BIGVGAN_MODEL = None
_CHATTERBOX_MODEL = None
_PROSODY_CACHE = {}  # hash(text) -> prosody-planned text


def _init_kokoro():
    """Lazy-initialize Kokoro (PyTorch first, ONNX fallback)."""
    global _KOKORO_PIPELINE, _KOKORO_BACKEND, _KOKORO_INSTANCE
    if _KOKORO_BACKEND is not None:
        return _KOKORO_BACKEND
    try:
        from kokoro import KPipeline
        _KOKORO_PIPELINE = KPipeline(lang_code='a')
        _KOKORO_BACKEND = "pytorch"
        logger.info("[TTS/Kokoro] Backend: PyTorch")
        return "pytorch"
    except Exception as e_pt:
        logger.warning(f"[TTS/Kokoro] PyTorch failed: {e_pt} — trying ONNX")
    try:
        from kokoro_onnx import Kokoro as _KokoroONNX
        _VOICES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "voices")
        _onnx_model = os.path.join(_VOICES_DIR, "kokoro-v0_19.onnx")
        _onnx_voices = os.path.join(_VOICES_DIR, "voices-v1.0.bin")
        if not os.path.exists(_onnx_model):
            logger.info("[TTS/Kokoro] Downloading ONNX model files...")
            subprocess.run([
                "python3", "-c",
                "from huggingface_hub import hf_hub_download; "
                f"hf_hub_download('hexgrad/Kokoro-82M', 'kokoro-v0_19.onnx', local_dir='{_VOICES_DIR}'); "
                f"hf_hub_download('hexgrad/Kokoro-82M', 'voices-v1.0.bin', local_dir='{_VOICES_DIR}')"
            ], timeout=300)
        _KOKORO_INSTANCE = _KokoroONNX(_onnx_model, _onnx_voices)
        _KOKORO_BACKEND = "onnx"
        logger.info("[TTS/Kokoro] Backend: ONNX")
        return "onnx"
    except Exception as e_onnx:
        logger.error(f"[TTS/Kokoro] Both backends failed: {e_onnx}")
        _KOKORO_BACKEND = "unavailable"
        return "unavailable"


def _init_f5():
    """Lazy-initialize fine-tuned F5-TTS model."""
    global _F5_MODEL
    if _F5_MODEL is not None:
        return True
    ckpt = os.path.join(os.path.dirname(os.path.abspath(__file__)), "voices", "pbx_voice.pt")
    if not os.path.exists(ckpt):
        logger.warning(f"[TTS/F5] Fine-tuned checkpoint missing: {ckpt}")
        return False
    try:
        from f5_tts.api import F5TTS
        _F5_MODEL = F5TTS(model="F5TTS_v1_Base", ckpt_file=ckpt, device="cuda:1")
        logger.info(f"[TTS/F5] Fine-tuned model loaded: {ckpt}")
        return True
    except Exception as e:
        logger.error(f"[TTS/F5] Failed to load checkpoint: {e}")
        return False


def _init_chatterbox():
    """Lazy-initialize Chatterbox TTS on cuda:0."""
    global _CHATTERBOX_MODEL
    if _CHATTERBOX_MODEL is not None:
        return True
    try:
        from chatterbox.tts import ChatterboxTTS
        _CHATTERBOX_MODEL = ChatterboxTTS.from_pretrained(device="cuda:0")
        logger.info("[TTS/Chatterbox] Model loaded on cuda:0")
        return True
    except Exception as e:
        logger.error(f"[TTS/Chatterbox] Failed to load: {e}")
        return False


def _init_bigvgan():
    """Lazy-initialize BigVGAN2 44kHz vocoder on cuda:1."""
    global _BIGVGAN_MODEL
    if _BIGVGAN_MODEL is not None:
        return True
    try:
        import bigvgan as _bv
        _BIGVGAN_MODEL = _bv.BigVGAN.from_pretrained(
            "nvidia/bigvgan_v2_44khz_128band_512x",
            use_cuda_kernel=False,
        )
        _BIGVGAN_MODEL = _BIGVGAN_MODEL.eval().to("cuda:1")
        logger.info("[TTS/BigVGAN2] 44kHz vocoder loaded on cuda:1")
        return True
    except Exception as e:
        logger.error(f"[TTS/BigVGAN2] Init failed: {e}")
        return False


def _bigvgan_upsample(wav_path_24k: str) -> str:
    """Upsample 24kHz WAV to 44kHz via BigVGAN2. Returns path to 44kHz WAV.
    Graceful fallback: returns original path if BigVGAN2 fails."""
    if not _init_bigvgan():
        return wav_path_24k
    try:
        import torch
        import soundfile as sf
        import librosa
        wav_data, sr = sf.read(wav_path_24k)
        if sr != 24000:
            wav_data = librosa.resample(wav_data, orig_sr=sr, target_sr=24000)
        # BigVGAN expects mel spectrogram input — compute from audio
        import torchaudio
        wav_tensor = torch.FloatTensor(wav_data).unsqueeze(0).to("cuda:1")
        # Use torchaudio to compute mel spectrogram matching BigVGAN's expected input
        mel_transform = torchaudio.transforms.MelSpectrogram(
            sample_rate=24000, n_fft=2048, hop_length=256, n_mels=128,
            f_min=0, f_max=12000,
        ).to("cuda:1")
        mel = mel_transform(wav_tensor)
        mel = torch.log(torch.clamp(mel, min=1e-5))
        with torch.inference_mode():
            wav_out = _BIGVGAN_MODEL(mel)
        wav_np = wav_out.squeeze().cpu().numpy()
        out_path = wav_path_24k.replace(".wav", ".44k.wav")
        sf.write(out_path, wav_np, 44100)
        logger.info(f"[TTS/BigVGAN2] Upsampled {wav_path_24k} → {out_path}")
        return out_path
    except Exception as e:
        logger.warning(f"[TTS/BigVGAN2] Upsample failed: {e} — using 24kHz")
        return wav_path_24k


def prosody_plan(text: str, host: int = 2) -> str:
    """Add natural delivery markers via Claude Haiku pre-processor.
    Cached by text hash. Returns original text if API fails."""
    import hashlib
    h = hashlib.sha256(text.encode()).hexdigest()[:16]
    if h in _PROSODY_CACHE:
        return _PROSODY_CACHE[h]
    api_key = _get_cached_key("ANTHROPIC_API_KEY")
    if not api_key or not HAS_REQUESTS:
        return text
    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 512,
                "system": (
                    "You are a speech prosody director. Rewrite the input line with natural "
                    "delivery markers: [pause:0.1], [pause:0.2], [emphasis], [breath]. Use "
                    "sparingly — max 3 markers per sentence. For Bitcoin news: add [pause:0.15] "
                    "after key price levels, [emphasis] on sovereign/freedom/signal, [breath] at "
                    "long clause boundaries. Return ONLY the rewritten line, nothing else."
                ),
                "messages": [{"role": "user", "content": text}],
            },
            timeout=10,
        )
        if resp.status_code == 200:
            result = resp.json()["content"][0]["text"].strip()
            _PROSODY_CACHE[h] = result
            logger.info(f"[TTS/Prosody] Planned: {text[:40]}… → {result[:40]}…")
            return result
        logger.warning(f"[TTS/Prosody] API {resp.status_code}")
    except Exception as e:
        logger.warning(f"[TTS/Prosody] Failed: {e}")
    return text


PBX_VOICE_ID = "HmUVvDlHsEz0m3eUGLgu"

_PBX_VOICE = {
    "voice_id": PBX_VOICE_ID,
    "name": "PBX",
    "model_id": "eleven_turbo_v2_5",
    "speed": 1.2,  # Render20: +10% from 1.10, capped at ElevenLabs max 1.2
    "voice_settings": {
        "stability": 0.55,
        "similarity_boost": 0.80,
        "style": 0.15,
        "use_speaker_boost": True,
    },
}

# ── LOCAL TTS VOICE CONFIG ──────────────────────────────────────────────────
VOICES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "voices")
PBX_CHECKPOINT = os.path.join(VOICES_DIR, "pbx_voice.pt")
PBX_REFERENCE_CLIP = os.path.join(VOICES_DIR, "pbx_reference.wav")
KOKORO_HOST1_VOICE = "af_heart"
KOKORO_HOST2_VOICE = "am_adam"   # fallback when F5 checkpoint unavailable
F5_SPEED = 1.1
KOKORO_SPEED_H1 = 1.0
KOKORO_SPEED_H2 = 1.1

_ERYN_VOICE = {
    "voice_id": "kdnRe2koJdOK4Ovxn2DI",
    "name": "Eryn",
    "model_id": "eleven_turbo_v2_5",
    "speed": 1.0,
    "voice_settings": {
        "stability": 0.55,
        "similarity_boost": 0.80,
        "style": 0.15,
        "use_speaker_boost": True,
    },
}
# Dual-host: HOST_1 = Eryn/af_heart (female), HOST_2 = PBX (fine-tuned F5 / ElevenLabs fallback)
VOICES = {
    1: _ERYN_VOICE,
    2: _PBX_VOICE,
}

def _get_tts_provider() -> str:
    """TTS provider selector.
    'local'      → Kokoro af_heart (host1) + Chatterbox PBX (host2) + ElevenLabs fallback
    'elevenlabs' → ElevenLabs only (emergency override, preserves single-host Option A)
    """
    val = os.environ.get("TTS_PROVIDER", "local").lower().strip()
    if val not in ("local", "elevenlabs"):
        logger.warning(f"[TTS] Unknown TTS_PROVIDER='{val}', defaulting to 'local'")
        return "local"
    return val


_KEY_CACHE: dict = {}

def _get_cached_key(name: str) -> str:
    if name not in _KEY_CACHE:
        k = get_key(name)
        if k:
            _KEY_CACHE[name] = k.strip()
    return _KEY_CACHE.get(name, "")


def ffprobe_duration(path: str) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path],
        capture_output=True, text=True,
    )
    try:
        return float(r.stdout.strip())
    except Exception:
        logger.warning(f"[TTS] ffprobe_duration failed for {path}")
        return -1.0


def _generate_silence(output_path: str, duration: float) -> bool:
    """Generate a silent audio file."""
    r = subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i",
         f"anullsrc=r=48000:cl=stereo", "-t", str(duration),
         "-c:a", "aac", "-b:a", "192k", output_path],
        capture_output=True, text=True, timeout=30,
    )
    return r.returncode == 0 and os.path.exists(output_path)


def _mp3_to_m4a(mp3_path: str, m4a_path: str) -> bool:
    # Issue 7: atempo=1.08 post-processing gives effective 1.3x speed (1.2 ElevenLabs × 1.08)
    r = subprocess.run(
        ["ffmpeg", "-y", "-i", mp3_path,
         "-af", "atempo=1.08",
         "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k", m4a_path],
        capture_output=True, text=True, timeout=120,
    )
    return r.returncode == 0 and os.path.exists(m4a_path)


MAX_CHUNK_CHARS = 500  # ElevenLabs safe chunk size
SILENCE_GAP = 0.3  # seconds between speakers

# Voice mode overrides per segment type (applied to whichever host speaks)
VOICE_MODES = {
    "cold_open":       {"stability": 0.45, "similarity_boost": 0.80, "style": 0.18},
    "setup":           {"stability": 0.55, "similarity_boost": 0.80, "style": 0.15},
    "react":           {"stability": 0.55, "similarity_boost": 0.80, "style": 0.15},
    "bridge":          {"stability": 0.52, "similarity_boost": 0.80, "style": 0.15},
    "social_segment":  {"stability": 0.50, "similarity_boost": 0.78, "style": 0.18},
    "wrap":            {"stability": 0.50, "similarity_boost": 0.78, "style": 0.20},
}


def _chunk_text(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list:
    if len(text) <= max_chars:
        return [text]
    raw = text.replace("! ", "!\x00").replace(". ", ".\x00").replace("? ", "?\x00")
    sentences = raw.split("\x00")
    chunks, current = [], ""
    for sent in sentences:
        if len(current) + len(sent) + 1 <= max_chars:
            current = f"{current} {sent}".strip() if current else sent
        else:
            if current:
                chunks.append(current)
            current = sent
    if current:
        chunks.append(current)
    return [c for c in chunks if c.strip()]


def expand_numbers_for_tts(text: str) -> str:
    """Round 2 Fix 1: Full num2words preprocessing — converts ALL numbers >999 to spoken form.

    Previous version used manual thousand/million/billion templates which caused garbled
    speech on numbers like "1,056 EH/s" or "$74,000". Now uses num2words for natural
    spoken-word output: "$74,000" → "seventy-four thousand dollars".
    """
    import re as _re
    try:
        from num2words import num2words as _n2w
    except ImportError:
        logger.warning("[TTS] num2words not installed — falling back to basic expansion")
        return _expand_numbers_basic(text)

    # Issue 12: Year detection BEFORE general number expansion
    # 4-digit numbers 1600-2099 not preceded by $ or currency → spoken as years
    def _year_to_words(y: int) -> str:
        """Convert year number to spoken form: 1602→sixteen oh two, 2024→twenty twenty-four."""
        if 2000 <= y <= 2009:
            return f"two thousand {_n2w(y - 2000) if y > 2000 else ''}".strip()
        if 2010 <= y <= 2099:
            return f"twenty {_n2w(y - 2000)}"
        hi = y // 100
        lo = y % 100
        hi_word = _n2w(hi)
        if lo == 0:
            return f"{hi_word} hundred"
        elif lo < 10:
            return f"{hi_word} oh {_n2w(lo)}"
        else:
            return f"{hi_word} {_n2w(lo)}"

    def _year_sub(m):
        val = int(m.group(0))
        return _year_to_words(val)
    # Match 1600-2099 NOT preceded by $ or digits
    text = _re.sub(r'(?<!\$)(?<!\d)\b(1[6-9]\d{2}|20[0-9]\d)\b(?!\s*(?:EH|TH|PH|dollars|percent|%|K\b))', _year_sub, text)

    # Dollar + billion/million shorthand first: $308 billion → "three hundred and eight billion dollars"
    def _dollar_scale(m):
        num_str = m.group(1)
        scale = m.group(2).lower()
        try:
            val = float(num_str)
            spoken = _n2w(val) if val != int(val) else _n2w(int(val))
            return f"{spoken} {scale} dollars"
        except Exception:
            return m.group(0)
    text = _re.sub(r'\$(\d+(?:\.\d+)?)\s*([Bb]illion|[Mm]illion|[Tt]rillion)', _dollar_scale, text)

    # Dollar amounts: $74,000 → "seventy-four thousand dollars"
    def _dollar(m):
        val_str = m.group(1).replace(",", "")
        try:
            val = int(float(val_str))
            if val > 999:
                return f"{_n2w(val)} dollars"
            return f"{val} dollars"
        except Exception:
            return m.group(0)
    text = _re.sub(r'\$([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?)', _dollar, text)

    # Hashrate units BEFORE plain numbers (so "1,056 EH/s" is caught here)
    def _hashrate(m):
        val_str = m.group(1).replace(",", "")
        unit = m.group(2)
        unit_map = {"EH": "exahashes", "TH": "terahashes", "PH": "petahashes"}
        try:
            val = float(val_str)
            spoken = _n2w(val) if val != int(val) else _n2w(int(val))
            return f"{spoken} {unit_map.get(unit, unit)} per second"
        except Exception:
            return m.group(0)
    text = _re.sub(r'([0-9]{1,3}(?:,[0-9]{3})*(?:\.\d+)?)\s*(EH|TH|PH)/?s', _hashrate, text)

    # Percentages: 42% → "forty-two percent"
    def _pct(m):
        val_str = m.group(1)
        try:
            val = float(val_str)
            if val == int(val):
                return f"{_n2w(int(val))} percent"
            # 8.4% → "eight point four percent"
            whole = int(val)
            frac = val_str.split('.')[1] if '.' in val_str else ''
            if frac:
                frac_spoken = ' '.join(_n2w(int(d)) for d in frac)
                return f"{_n2w(whole)} point {frac_spoken} percent"
            return f"{_n2w(int(val))} percent"
        except Exception:
            return m.group(0)
    text = _re.sub(r'([\d.]+)%', _pct, text)

    # Large plain numbers with commas: 70,015 → "seventy thousand and fifteen"
    def _plain_num(m):
        val_str = m.group(0).replace(",", "")
        try:
            val = int(val_str)
            if val > 999:
                return _n2w(val)
            return m.group(0)
        except Exception:
            return m.group(0)
    text = _re.sub(r'\b\d{1,3}(?:,\d{3})+\b', _plain_num, text)

    # Billion/million shorthand in text (no dollar): 1.2 billion → "one point two billion"
    def _scale(m):
        val_str = m.group(1)
        scale = m.group(2).lower()
        try:
            val = float(val_str)
            spoken = _n2w(val) if val != int(val) else _n2w(int(val))
            return f"{spoken} {scale}"
        except Exception:
            return m.group(0)
    text = _re.sub(r'(\d+(?:\.\d+)?)\s*([Bb]illion|[Mm]illion|[Tt]rillion)', _scale, text)

    # K shorthand: 74K → "seventy-four thousand"
    def _k(m):
        try:
            val = float(m.group(1))
            return _n2w(int(val * 1000))
        except Exception:
            return m.group(0)
    text = _re.sub(r'(\d+(?:\.\d+)?)[Kk]\b', _k, text)

    # Standalone large numbers without commas (e.g. 74000)
    def _bare_num(m):
        try:
            val = int(m.group(0))
            if val > 999:
                return _n2w(val)
            return m.group(0)
        except Exception:
            return m.group(0)
    text = _re.sub(r'\b\d{4,}\b', _bare_num, text)

    # Issue 6: Strip commas and "and" from num2words output to prevent micro-pauses
    text = _re.sub(r'(\w),\s', r'\1 ', text)  # remove commas in spoken numbers
    text = _re.sub(r'\band\b\s*', '', text)  # remove "and" (e.g. "one hundred and fifty" → "one hundred fifty")
    text = _re.sub(r'\s{2,}', ' ', text)  # collapse double spaces

    return text


def _expand_numbers_basic(text: str) -> str:
    """Fallback number expansion without num2words (original logic)."""
    import re as _re

    def _dollar(m):
        val_str = m.group(1).replace(",", "")
        try:
            val = int(float(val_str))
        except ValueError:
            return m.group(0)
        if val >= 1_000_000_000:
            return f"{val/1_000_000_000:.1f} billion dollars".replace(".0 ", " ")
        if val >= 1_000_000:
            return f"{val/1_000_000:.1f} million dollars".replace(".0 ", " ")
        if val >= 1_000:
            b = val // 1000
            r = val % 1000
            if r == 0:
                return f"{b} thousand dollars"
            return f"{b} thousand {r} dollars"
        return f"{val} dollars"

    text = _re.sub(r'\$(\d+(?:\.\d+)?)\s*[Bb]illion', lambda m: f"{m.group(1)} billion dollars", text)
    text = _re.sub(r'\$(\d+(?:\.\d+)?)\s*[Mm]illion', lambda m: f"{m.group(1)} million dollars", text)
    text = _re.sub(r'\$([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?)', _dollar, text)

    def _plain_num(m):
        val_str = m.group(0).replace(",", "")
        try:
            val = int(val_str)
        except ValueError:
            return m.group(0)
        if val >= 1_000_000_000:
            return f"{val/1_000_000_000:.1f} billion".replace(".0 ", " ")
        if val >= 1_000_000:
            return f"{val/1_000_000:.1f} million".replace(".0 ", " ")
        if val >= 10_000:
            b = val // 1000
            r = val % 1000
            if r == 0:
                return f"{b} thousand"
            return f"{b} thousand {r}"
        return m.group(0)
    text = _re.sub(r'\b\d{1,3}(?:,\d{3})+\b', _plain_num, text)

    def _pct(m):
        return m.group(1).replace(".", " point ") + " percent"
    text = _re.sub(r'([\d.]+)%', _pct, text)

    text = _re.sub(r'(\d+(?:\.\d+)?)\s*EH/?s', lambda m: f"{m.group(1)} exahash per second", text)
    text = _re.sub(r'(\d+(?:\.\d+)?)\s*TH/?s', lambda m: f"{m.group(1)} terahash per second", text)
    text = _re.sub(r'(\d+(?:\.\d+)?)\s*PH/?s', lambda m: f"{m.group(1)} petahash per second", text)
    text = _re.sub(r'(\d+(?:\.\d+)?)\s*[Bb]illion', lambda m: f"{m.group(1)} billion", text)
    text = _re.sub(r'(\d+(?:\.\d+)?)\s*[Mm]illion', lambda m: f"{m.group(1)} million", text)

    def _k(m):
        val = float(m.group(1))
        if val == int(val):
            return f"{int(val)} thousand"
        return f"{val} thousand"
    text = _re.sub(r'(\d+(?:\.\d+)?)[Kk]\b', _k, text)

    return text


TTS_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tts_cache")



# ── Bitcoin Ecosystem Pronunciation Map ────────────────────────────────────
# ElevenLabs renders these phonetic substitutions naturally.
# Longer/more specific entries first to avoid partial replacements.
PRONUNCIATION_MAP = {
    # Satoshi
    "Satoshi Nakamoto": "sah TOE shee nah kah MOE toe",
    "Satoshi": "sah TOE shee",
    "Nakamoto": "nah kah MOE toe",
    # Saylor
    "Michael Saylor": "Michael Sayler",
    "Saylor": "Sayler",
    # Lyn Alden
    "Lyn Alden": "Lin AWL-den",
    # Lummis
    "Cynthia Lummis": "SIN-thee-ah LUM-iss",
    "Lummis": "LUM-iss",
    # Brunell
    "Natalie Brunell": "Natalie Brunelle",
    "Brunell": "Brunelle",
    # Preston Pysh
    "Preston Pysh": "Preston PISH",
    "Pysh": "PISH",
    # Max Keiser
    "Max Keiser": "MAX KY-zer",
    "Keiser": "KY-zer",
    # Nayib Bukele
    "Nayib Bukele": "NYE-eeb boo-KEH-leh",
    "Bukele": "boo-KEH-leh",
    # Saifedean Ammous
    "Saifedean Ammous": "sy-feh-DEAN AH-moos",
    "Saifedean": "sy-feh-DEAN",
    "Ammous": "AH-moos",
    # Robert Breedlove
    "Robert Breedlove": "Robert BREED love",
    "Breedlove": "BREED love",
    # Alex Gladstein
    "Alex Gladstein": "AL-ex GLAD-steen",
    "Gladstein": "GLAD-steen",
    # Knut Svanholm
    "Knut Svanholm": "kuh-NOOT SVAHN-holm",
    "Svanholm": "SVAHN-holm",
    # Luke Dashjr
    "Luke Dashjr": "LUKE DASH-junior",
    "Dashjr": "DASH-junior",
    # Andreas Antonopoulos
    "Andreas Antonopoulos": "ahn-DRAY-us an-TON-oh-POO-lus",
    "Antonopoulos": "an-TON-oh-POO-lus",
    "Andreas": "ahn-DRAY-us",
    # Charlie Shrem
    "Charlie Shrem": "CHAR-lee SHREM",
    "Shrem": "SHREM",
    # Lawrence Lepard
    "Lawrence Lepard": "LAW-rents leh-PARD",
    "Larry Lepard": "LAIR-ee leh-PARD",
    "Lepard": "leh-PARD",
    # Erik Voorhees
    "Erik Voorhees": "AIR-ik VOR-hees",
    "Voorhees": "VOR-hees",
    # Gabor Gurbacs
    "Gabor Gurbacs": "GAH-bor GUR-bacs",
    "Gurbacs": "GUR-bacs",
    # Gary Gensler
    "Gary Gensler": "GAIR-ee GENZ-ler",
    "Gensler": "GENZ-ler",
    # Jerome Powell
    "Jerome Powell": "jeh-ROME POW-ul",
    "Powell": "POW-ul",
    # CJ Konstantinos
    "CJ Konstantinos": "see-JAY kon-stan-TEE-nos",
    "Konstantinos": "kon-stan-TEE-nos",
    # Bob Iaccino
    "Bob Iaccino": "BOB ee-ah-CHEE-no",
    "Iaccino": "ee-ah-CHEE-no",
    # Alex Stanczyk
    "Alex Stanczyk": "AL-ex STAN-chik",
    "Stanczyk": "STAN-chik",
    # Matt Odell
    "Matt Odell": "MAT OH-dell",
    "Odell": "OH-dell",
    # Marty Bent
    "Marty Bent": "MAR-tee BENT",
    # Willy Woo
    "Willy Woo": "WIL-ee WOO",
    # Technical terms
    "EH/s": "exahashes per second",
    "TH/s": "terahashes per second",
    "PH/s": "petahashes per second",
    "UTXO": "you-tee-ex-oh",
    "HODL": "HODDLE",
    "blockchain": "blockchain",
    "halving": "HAV-ing",
    "SegWit": "SEG-wit",
    "Segwit": "SEG-wit",
    "hodl": "HODDLE",
    "mempool": "mem-pool",
    "multisig": "MUL-tee-sig",
    "satoshis": "sah-TOH-sheez",
    "MicroStrategy": "MY-crow-STRAT-uh-jee",
    "Coinbase": "KOYN-base",
    "Binance": "BY-nance",
    "Chainalysis": "CHAIN-uh-LY-sis",
    # Issue 10: BTC → Bitcoin spoken form
    "BTC": "Bitcoin",
}


def _expand_handle(handle: str) -> str:
    """Issue 11: Convert @handle to spoken form.
    CamelCase → separate words, underscores → spaces, ALL CAPS → spelled out."""
    import re as _re
    name = handle.lstrip("@")
    # ALL CAPS (like TFTC, WBD) → spelled out with dashes
    if name.isupper() and len(name) <= 6:
        return "at " + "-".join(name)
    # Split camelCase: MaxKeiser → Max Keiser
    name = _re.sub(r'([a-z])([A-Z])', r'\1 \2', name)
    # Split underscores
    name = name.replace("_", " ")
    return "at " + name


# Known handles with correct spoken forms
_HANDLE_PRONUNCIATIONS = {
    "@maxkeiser": "at Max Kaiser",
    "@prestopysh": "at Preston Pish",
    "@tftc": "at T-F-T-C",
    "@wbd": "at W-B-D",
    "@saborchain": "at Sabor Chain",
}


_ORDINAL_MAP = {
    "1st": "first", "2nd": "second", "3rd": "third", "4th": "fourth",
    "5th": "fifth", "6th": "sixth", "7th": "seventh", "8th": "eighth",
    "9th": "ninth", "10th": "tenth", "11th": "eleventh", "12th": "twelfth",
    "13th": "thirteenth", "14th": "fourteenth", "15th": "fifteenth",
    "16th": "sixteenth", "17th": "seventeenth", "18th": "eighteenth",
    "19th": "nineteenth", "20th": "twentieth", "21st": "twenty-first",
    "22nd": "twenty-second", "23rd": "twenty-third", "24th": "twenty-fourth",
    "25th": "twenty-fifth", "26th": "twenty-sixth", "27th": "twenty-seventh",
    "28th": "twenty-eighth", "29th": "twenty-ninth", "30th": "thirtieth",
    "31st": "thirty-first",
}


def _expand_ordinals(text: str) -> str:
    """Pre-process ordinal numbers (e.g. '27th') to spoken form to prevent TTS splitting."""
    import re as _re
    def _ordinal_sub(m):
        key = m.group(0).lower()
        return _ORDINAL_MAP.get(key, m.group(0))
    return _re.sub(r'\b\d{1,2}(?:st|nd|rd|th)\b', _ordinal_sub, text, flags=_re.IGNORECASE)


def apply_pronunciation_map(text: str) -> str:
    """Replace names/terms with phonetic versions ElevenLabs renders correctly.
    Processes longer entries first to avoid partial replacements."""
    import re
    # Pre-process ordinals before pronunciation map
    text = _expand_ordinals(text)
    # Issue 11: Pre-process @handles before pronunciation map
    def _handle_sub(m):
        raw = m.group(0).lower()
        if raw in _HANDLE_PRONUNCIATIONS:
            return _HANDLE_PRONUNCIATIONS[raw]
        return _expand_handle(m.group(0))
    text = re.sub(r'@[A-Za-z0-9_]+', _handle_sub, text)

    # Sort by length descending so longer matches take priority
    for written, phonetic in sorted(PRONUNCIATION_MAP.items(), key=lambda x: -len(x[0])):
        # Word-boundary aware replacement (case-insensitive)
        pattern = re.compile(r'\b' + re.escape(written) + r'\b', re.IGNORECASE)
        text = pattern.sub(phonetic, text)
    return text


def _trim_trailing_silence(audio_path: str) -> None:
    """Round 2 Fix 2: Trim trailing silence/vowel-stretch from TTS output.

    Detects if the last 0.5s is significantly quieter than the body (trailing off)
    and trims it to avoid the stretched-vowel artifact common in ElevenLabs output.
    """
    try:
        import re as _re
        # Measure RMS of last 0.5s vs body
        result = subprocess.run(
            ["ffmpeg", "-i", audio_path, "-af",
             "silencedetect=noise=-35dB:d=0.15", "-f", "null", "-"],
            capture_output=True, text=True, timeout=15,
        )
        # Find silence at end of file
        dur = ffprobe_duration(audio_path)
        if dur <= 1.0:
            return
        silences = [float(m.group(1)) for m in
                    _re.finditer(r"silence_start: ([\d.]+)", result.stderr)]
        if not silences:
            return
        last_silence = silences[-1]
        # If silence starts within last 0.5s, trim there
        if dur - last_silence <= 0.5 and last_silence > dur * 0.8:
            trimmed = audio_path + ".trimmed.m4a"
            trim_ok = subprocess.run(
                ["ffmpeg", "-y", "-i", audio_path,
                 "-t", f"{last_silence + 0.05:.3f}",
                 "-c:a", "aac", "-ar", "48000", "-b:a", "192k", trimmed],
                capture_output=True, text=True, timeout=15,
            )
            if trim_ok.returncode == 0 and os.path.exists(trimmed) and os.path.getsize(trimmed) > 5000:
                os.replace(trimmed, audio_path)
                logger.info(f"[TTS] Trimmed trailing silence: {dur:.2f}s → {last_silence + 0.05:.2f}s")
            elif os.path.exists(trimmed):
                os.remove(trimmed)
    except Exception as e:
        logger.debug(f"[TTS] Trailing silence trim skipped: {e}")


def _tts_cache_key(text: str, voice_id: str, segment_type: str) -> str:
    """SHA256 hash of text+voice+segment_type → stable cache key."""
    import hashlib
    payload = f"{voice_id}:{segment_type}:{text}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def _tts_cache_get(cache_key: str, output_path: str) -> bool:
    """Return True if valid cached file exists and passes validation."""
    cache_file = os.path.join(TTS_CACHE_DIR, f"{cache_key}.m4a")
    if os.path.exists(cache_file) and os.path.getsize(cache_file) > 10240:
        shutil.copy2(cache_file, output_path)
        try:
            validate_tts_output(output_path)
            return True
        except RuntimeError:
            logger.warning(f"[TTS] Corrupt cache deleted: {cache_file}")
            try:
                os.remove(cache_file)
                os.remove(output_path)
            except Exception:
                pass
    return False


def _tts_cache_put(cache_key: str, audio_path: str) -> None:
    """Save audio to TTS cache for future runs."""
    import shutil
    os.makedirs(TTS_CACHE_DIR, exist_ok=True)
    cache_file = os.path.join(TTS_CACHE_DIR, f"{cache_key}.m4a")
    if not os.path.exists(cache_file):
        shutil.copy2(audio_path, cache_file)


def _tts_generate_silence_fallback(text: str, output_path: str) -> bool:
    """HARD FAIL: silence fallback is no longer allowed.

    Previously generated silent AAC as a last resort, masking total TTS failure.
    This caused downstream black frames and F-grade renders that QC scored 94/100.
    Now raises RuntimeError so the pipeline fails fast instead of rendering garbage.
    """
    snippet = (text[:80] + "...") if len(text) > 80 else text
    raise RuntimeError(
        f"TTS FATAL: ElevenLabs + pyttsx3 both failed. Refusing to render silence. "
        f"Text: \"{snippet}\". Fix the TTS provider before re-running."
    )


def tts_kokoro(text: str, output_path: str, voice: str = "af_heart",
               speed: float = 1.0) -> bool:
    """Generate TTS via Kokoro GPU inference. Output: M4A 48kHz AAC 192k."""
    backend = _init_kokoro()
    if backend == "unavailable":
        return False
    try:
        import soundfile as sf
        import numpy as np
        wav_tmp = output_path + ".kokoro.wav"
        if backend == "pytorch":
            samples_list = []
            for _, _, audio in _KOKORO_PIPELINE(text, voice=voice, speed=speed):
                samples_list.append(audio)
            if not samples_list:
                return False
            audio_np = np.concatenate(samples_list) if len(samples_list) > 1 else samples_list[0]
            sf.write(wav_tmp, audio_np, 24000)
        else:
            samples, sr = _KOKORO_INSTANCE.create(text, voice=voice, speed=speed, lang="en-us")
            sf.write(wav_tmp, samples, sr)

        if not os.path.exists(wav_tmp) or os.path.getsize(wav_tmp) < 1000:
            return False
        # Direct encode: 24kHz WAV → 48kHz AAC (no BigVGAN2 — causes double-vocoding)
        r = subprocess.run([
            "ffmpeg", "-y", "-i", wav_tmp,
            "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k", output_path
        ], capture_output=True, text=True, timeout=60)
        try:
            if os.path.exists(wav_tmp):
                os.remove(wav_tmp)
        except Exception:
            pass
        ok = r.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 5000
        if ok:
            logger.info(f"[TTS/Kokoro] OK: {ffprobe_duration(output_path):.2f}s, voice={voice}")
        return ok
    except Exception as e:
        logger.error(f"[TTS/Kokoro] Exception: {e}")
        return False


def tts_chatterbox(text: str, output_path: str, exaggeration: float = 0.4,
                    cfg_weight: float = 0.5) -> bool:
    """Generate TTS using Chatterbox for PBX (Host 2).

    Chatterbox produces clean audio — no post-processing EQ needed.
    Output: M4A 48kHz AAC 192k.
    """
    if not _init_chatterbox():
        logger.warning("[TTS/Chatterbox] Model not loaded")
        return False

    try:
        import torchaudio
        wav_tmp = output_path + ".cb.wav"

        wav = _CHATTERBOX_MODEL.generate(text, exaggeration=exaggeration,
                                          cfg_weight=cfg_weight)
        torchaudio.save(wav_tmp, wav, 24000)

        if not os.path.exists(wav_tmp) or os.path.getsize(wav_tmp) < 1000:
            logger.error("[TTS/Chatterbox] Zero output from inference")
            return False

        # Convert WAV to M4A (48kHz AAC 192k)
        r = subprocess.run([
            "ffmpeg", "-y", "-i", wav_tmp,
            "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k", output_path
        ], capture_output=True, text=True, timeout=60)

        try:
            if os.path.exists(wav_tmp):
                os.remove(wav_tmp)
        except Exception:
            pass

        ok = r.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 5000
        if ok:
            logger.info(f"[TTS/Chatterbox] OK: {ffprobe_duration(output_path):.2f}s (PBX)")
        return ok
    except Exception as e:
        logger.error(f"[TTS/Chatterbox] Exception: {e}")
        return False


def tts_local(text: str, output_path: str, host: int = 1,
              segment_type: str = "") -> bool:
    """Primary TTS dispatcher — local GPU inference with per-line ElevenLabs fallback.

    Host 1 → Kokoro af_heart → ElevenLabs Eryn fallback
    Host 2 → Chatterbox PBX → Kokoro am_adam → ElevenLabs PBX fallback
    """
    text = expand_numbers_for_tts(text)
    text = apply_pronunciation_map(text)
    # Prosody planner: add natural delivery markers before TTS
    text = prosody_plan(text, host=host)
    try:
        _oracle_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "oracle")
        if _oracle_path not in sys.path:
            sys.path.insert(0, _oracle_path)
        from oracle_dialogue_engine import normalize_pronunciation
        text = normalize_pronunciation(text)
    except Exception as _e:
        logger.warning(f"[TTS/Local] normalize_pronunciation unavailable: {_e}")

    cache_key = _tts_cache_key(text, f"local_h{host}", segment_type)
    if _tts_cache_get(cache_key, output_path):
        print(f"  [tts/local] Cache HIT (host{host}): {text[:50]}")
        return True

    start_t = time.time()
    ok = False

    if host == 1:
        ok = tts_kokoro(text, output_path, voice=KOKORO_HOST1_VOICE, speed=KOKORO_SPEED_H1)
        if not ok:
            logger.warning("[TTS/Local] Kokoro host1 FAILED → ElevenLabs Eryn fallback")
            ok = tts_elevenlabs(text, output_path, host=1, segment_type=segment_type)
    else:
        ok = tts_chatterbox(text, output_path)
        if not ok:
            logger.warning("[TTS/Local] Chatterbox FAILED → Kokoro am_adam")
            ok = tts_kokoro(text, output_path, voice=KOKORO_HOST2_VOICE, speed=KOKORO_SPEED_H2)
        if not ok:
            logger.warning("[TTS/Local] Kokoro host2 FAILED → ElevenLabs PBX fallback")
            ok = tts_elevenlabs(text, output_path, host=2, segment_type=segment_type)

    if ok and os.path.exists(output_path):
        _trim_trailing_silence(output_path)
        validate_tts_output(output_path)
        _tts_cache_put(cache_key, output_path)
        elapsed = time.time() - start_t
        dur = ffprobe_duration(output_path)
        print(f"  [tts/local] host{host} OK: {dur:.1f}s audio in {elapsed:.1f}s wall ← {text[:50]}")

    return ok


def tts_preflight_local() -> bool:
    """Preflight for TTS_PROVIDER=local: verify Kokoro works, report F5 status."""
    test_text = "Bitcoin signal confirmed today."
    test_out = "/tmp/tts_preflight_local.m4a"
    try:
        ok = tts_kokoro(test_text, test_out, voice=KOKORO_HOST1_VOICE, speed=1.0)
        if not ok or not os.path.exists(test_out):
            raise RuntimeError("[TTS/Local] Kokoro preflight failed to generate audio")
        dur = ffprobe_duration(test_out)
        if dur < 0.5:
            raise RuntimeError(f"[TTS/Local] Kokoro output too short: {dur:.2f}s")
        logger.info(f"[TTS/Local] Kokoro preflight PASS: {dur:.2f}s")
        try:
            os.remove(test_out)
        except Exception:
            pass
        if os.path.exists(PBX_CHECKPOINT) and os.path.exists(PBX_REFERENCE_CLIP):
            logger.info("[TTS/Local] F5 ready: checkpoint + reference clip")
        elif os.path.exists(PBX_CHECKPOINT):
            logger.warning(f"[TTS/Local] F5 checkpoint found but reference clip missing: {PBX_REFERENCE_CLIP}")
        else:
            logger.warning("[TTS/Local] F5 checkpoint missing — host2 using Kokoro am_adam")
        return True
    except Exception as e:
        raise RuntimeError(f"[TTS/Local] Preflight FAILED: {e}")


def validate_tts_output(path: str, min_size: int = 10240) -> None:
    """Validate TTS output file is real audio, not empty/corrupt.

    Raises RuntimeError if:
      - File doesn't exist
      - File < min_size bytes (10KB default)
      - ffprobe duration < 0.5s
    """
    if not os.path.exists(path):
        raise RuntimeError(f"TTS output missing: {path}")
    size = os.path.getsize(path)
    if size < min_size:
        raise RuntimeError(
            f"TTS output too small ({size} bytes < {min_size}): {path} — "
            f"ElevenLabs likely returned empty audio"
        )
    dur = ffprobe_duration(path)
    if dur < 0.5:
        raise RuntimeError(
            f"TTS output too short ({dur:.2f}s < 0.5s): {path} — "
            f"audio is effectively silent/corrupt"
        )


def tts_preflight_test() -> bool:
    """Preflight: call ElevenLabs with a 5-word test phrase, confirm >1000 bytes returned.
    Raises RuntimeError on failure so the pipeline aborts before wasting render time."""
    if not HAS_REQUESTS:
        raise RuntimeError("TTS preflight: 'requests' library not installed")
    key = _get_cached_key("ELEVENLABS_API_KEY")
    if not key:
        raise RuntimeError("TTS preflight: ELEVENLABS_API_KEY not available")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{PBX_VOICE_ID}"
    headers = {"xi-api-key": key, "Content-Type": "application/json"}
    body = {
        "text": "Bitcoin signal confirmed today.",
        "model_id": "eleven_turbo_v2_5",
        "voice_settings": {"stability": 0.55, "similarity_boost": 0.80, "style": 0.15},
    }
    try:
        r = requests.post(url, json=body, headers=headers, timeout=20)
        if r.status_code != 200:
            raise RuntimeError(f"TTS preflight: ElevenLabs returned HTTP {r.status_code}: {r.text[:200]}")
        if len(r.content) < 1000:
            raise RuntimeError(f"TTS preflight: ElevenLabs returned only {len(r.content)} bytes (need >1000)")
        logger.info(f"[TTS] Preflight PASS: PBX voice returned {len(r.content)} bytes")
        return True
    except requests.RequestException as e:
        raise RuntimeError(f"TTS preflight: ElevenLabs unreachable: {e}")


def tts_elevenlabs(text: str, output_path: str, host: int = 1,
                   segment_type: str = "") -> bool:
    """Generate TTS for a single line using the specified host voice.

    Checks TTS cache first (hash of text+voice+segment_type). On cache hit,
    copies cached audio — no ElevenLabs API call. On miss, generates and caches.
    Falls back to pyttsx3 system TTS, then silence, on ElevenLabs quota/auth failure.
    """
    if not HAS_REQUESTS:
        # No requests lib — try pyttsx3 or silence
        return _tts_generate_silence_fallback(text, output_path)

    key = _get_cached_key("ELEVENLABS_API_KEY")
    if not key:
        return _tts_generate_silence_fallback(text, output_path)

    # Session 4 Fix 3: Expand numbers before TTS to prevent babbling
    text = expand_numbers_for_tts(text)
    # R25 FIX 7: Apply pronunciation map (Pysh→PISH, etc.) — was defined but never called
    text = apply_pronunciation_map(text)

    voice = VOICES.get(host, VOICES[2])  # All hosts → PBX
    # Check TTS cache first — avoid API call if same text+voice was generated before
    cache_key = _tts_cache_key(text, voice["voice_id"], segment_type)
    if _tts_cache_get(cache_key, output_path):
        print(f"  [tts] Cache HIT ({voice['name']}): {text[:50]}...")
        return True

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice['voice_id']}"
    headers = {"xi-api-key": key, "Content-Type": "application/json"}

    # Apply voice mode overrides based on segment type (both hosts)
    voice_settings = dict(voice["voice_settings"])
    if segment_type in VOICE_MODES:
        mode = VOICE_MODES[segment_type]
        for k, v in mode.items():
            if k != "speed":
                voice_settings[k] = v

    chunks = _chunk_text(text)
    chunk_files = []

    for ci, chunk in enumerate(chunks):
        body = {
            "text": chunk,
            "model_id": voice["model_id"],
            "voice_settings": voice_settings,
        }
        # Add speed parameter from voice config (host-specific)
        speed = voice.get("speed", 1.0)
        if speed != 1.0:
            body["speed"] = speed
        mp3_tmp = output_path + f".chunk{ci}.mp3"
        success = False

        # FIX iter1: Increase retries from 3 to 5 with longer backoff to survive
        # transient ElevenLabs outages that were causing grade failures
        max_retries = 5
        for attempt in range(max_retries):
            try:
                r = requests.post(url, json=body, headers=headers, timeout=90)
                if r.status_code == 200:
                    with open(mp3_tmp, "wb") as f:
                        f.write(r.content)
                    # Pre-validate: ElevenLabs sometimes returns empty/tiny responses
                    if os.path.getsize(mp3_tmp) < 1000:
                        print(f"  [tts] WARNING: ElevenLabs returned tiny file ({os.path.getsize(mp3_tmp)}B) for chunk {ci}, retrying...")
                        if attempt < max_retries - 1:
                            time.sleep(2 ** attempt)
                            continue
                    success = True
                    break
                elif r.status_code == 429:
                    wait = min(2 ** (attempt + 1), 30)  # cap at 30s
                    print(f"  [tts] Rate limited ({voice['name']}), waiting {wait}s...")
                    time.sleep(wait)
                else:
                    print(f"  [tts] HTTP {r.status_code} ({voice['name']}) attempt {attempt+1}: {r.text[:200]}")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
            except Exception as e:
                print(f"  [tts] Error ({voice['name']}) attempt {attempt+1}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)

        if not success:
            for f in chunk_files:
                try:
                    os.remove(f)
                except Exception:
                    pass
            logger.error(f"[tts] ElevenLabs failed after {max_retries} retries for chunk {ci} — returning False")
            return False
        chunk_files.append(mp3_tmp)

    # Single chunk
    if len(chunk_files) == 1:
        ok = _mp3_to_m4a(chunk_files[0], output_path)
        try:
            os.remove(chunk_files[0])
        except Exception:
            pass
        if ok and os.path.exists(output_path):
            _trim_trailing_silence(output_path)  # Round 2 Fix 2: trim vowel-stretch artifacts
            validate_tts_output(output_path)
            _tts_cache_put(cache_key, output_path)
        return ok

    # Multi-chunk concat
    concat_list = output_path + ".concat.txt"
    mp3_combined = output_path + ".combined.mp3"
    with open(concat_list, "w") as f:
        for p in chunk_files:
            f.write(f"file '{os.path.abspath(p)}'\n")
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
         "-c", "copy", mp3_combined],
        capture_output=True, text=True,
    )
    ok = _mp3_to_m4a(mp3_combined, output_path)
    for f in chunk_files + [concat_list, mp3_combined]:
        try:
            if os.path.exists(f):
                os.remove(f)
        except Exception:
            pass
    if ok and os.path.exists(output_path):
        _trim_trailing_silence(output_path)  # Round 2 Fix 2: trim vowel-stretch artifacts
        validate_tts_output(output_path)
        _tts_cache_put(cache_key, output_path)
    return ok


def generate_dialogue_audio(dialogue: list, output_dir: str) -> dict:
    """Generate audio for the entire dual-host dialogue.

    Args:
        dialogue: List of {host: 1|2|"CLIP", text: "..."}
        output_dir: Directory for audio files

    Returns:
        {
            "lines": [{"path": str, "host": int, "duration": float, "start": float}, ...],
            "full": str,  # path to concatenated full audio
            "total_duration": float,
        }
    """
    os.makedirs(output_dir, exist_ok=True)

    _active_provider = _get_tts_provider()
    if _active_provider == "local":
        tts_preflight_local()
    else:
        key = _get_cached_key("ELEVENLABS_API_KEY")
        if not key:
            raise RuntimeError("ELEVENLABS_API_KEY not available. Cannot generate audio.")

    silence_path = os.path.join(output_dir, "silence.m4a")
    _generate_silence(silence_path, SILENCE_GAP)

    lines = []
    parts_for_concat = []
    current_time = 0.0

    for i, entry in enumerate(dialogue):
        host = entry.get("host")
        text = entry.get("text", "")

        # Skip CLIP markers — they don't have audio but DO advance the timeline
        if host == "CLIP":
            clip_duration = float(entry.get("duration", 30.0))  # use actual duration or default 30s
            lines.append({
                "path": None,
                "host": "CLIP",
                "duration": clip_duration,  # record actual duration, not hardcoded 0.0
                "start": current_time,
                "source": entry.get("source", ""),
                "query": entry.get("query", ""),
                "text": text,
            })
            current_time += clip_duration  # advance timeline so subsequent audio is correctly offset
            continue

        _provider = _get_tts_provider()
        if _provider == "local":
            host_num = host if host in (1, 2) else 2
        else:
            host_num = 2   # ElevenLabs: single-host Option A preserved
        voice = VOICES[host_num]
        segment_type = entry.get("type", "")
        line_path = os.path.join(output_dir, f"line_{i:03d}_{voice['name'].lower()}.m4a")

        mode_tag = f" [{segment_type}]" if segment_type and host_num == 1 else ""
        print(f"  [tts] Line {i:02d} ({voice['name']}{mode_tag}): {text[:60]}...")

        _provider = _get_tts_provider()
        if _provider == "local":
            _tts_ok = tts_local(text, line_path, host_num, segment_type=segment_type)
        else:
            _tts_ok = tts_elevenlabs(text, line_path, host_num, segment_type=segment_type)
        if _tts_ok:
            if not os.path.exists(line_path) or os.path.getsize(line_path) < 1000:
                logger.warning(f"[tts] Line {i} zero/tiny audio — writing silence")
                _tts_ok = False
            else:
                dur = ffprobe_duration(line_path)
                if dur < 0.5 and len(text) > 10:
                    logger.warning(f"[tts] Line {i} too short ({dur:.2f}s) — writing silence")
                    _tts_ok = False
        if not _tts_ok:
            # Degrade gracefully: write 3s silence so assembler can continue
            logger.error(f"[tts] TTS failed line {i} — writing silence")
            subprocess.run([
                "ffmpeg", "-y", "-f", "lavfi",
                "-i", "anullsrc=r=48000:cl=stereo",
                "-t", "3", "-c:a", "aac", "-b:a", "192k", line_path
            ], capture_output=True)
            dur = 3.0

        lines.append({
            "path": line_path,
            "host": host_num,
            "duration": dur,
            "start": current_time,
            "text": text,
            "type": segment_type,
            "clip_rank": entry.get("clip_rank", 0),  # PiP FIX: preserve for assembler PiP lookup
        })
        parts_for_concat.append(line_path)
        current_time += dur

        # Add silence gap between speakers (not after last line, not before CLIP)
        next_entry = dialogue[i + 1] if i < len(dialogue) - 1 else None
        if next_entry is not None and next_entry.get("host") != "CLIP":
            parts_for_concat.append(silence_path)
            current_time += SILENCE_GAP

    # Concatenate all lines into full audio
    full_path = os.path.join(output_dir, "full_dialogue.m4a")
    if parts_for_concat:
        concat_file = os.path.join(output_dir, "dialogue_concat.txt")
        with open(concat_file, "w") as f:
            for p in parts_for_concat:
                f.write(f"file '{os.path.abspath(p)}'\n")
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_file,
             "-c", "copy", full_path],
            capture_output=True, text=True,
        )
        if os.path.exists(concat_file):
            os.remove(concat_file)

    # Guard: full_dialogue.m4a must not be zero-byte or tiny
    if os.path.exists(full_path):
        full_size = os.path.getsize(full_path)
        if full_size < 10240:
            raise RuntimeError(
                f"full_dialogue.m4a is {full_size} bytes (<10KB) — "
                f"FFmpeg concat produced empty/corrupt audio. Aborting before render."
            )

    total_dur = ffprobe_duration(full_path) if os.path.exists(full_path) else current_time
    successful = sum(1 for l in lines if l["path"] and os.path.exists(l.get("path", "")))

    print(f"\n  [tts] Dialogue audio: {successful}/{len(dialogue)} lines, {total_dur:.1f}s total")

    # ── Per-host TTS validation: catch silent hosts BEFORE render starts ──
    host_stats = {}  # {host_num: {"total": N, "ok": N}}
    for l in lines:
        h = l.get("host")
        if h == "CLIP":
            continue
        if h not in host_stats:
            host_stats[h] = {"total": 0, "ok": 0}
        host_stats[h]["total"] += 1
        if l.get("path") and os.path.exists(l.get("path", "")):
            host_stats[h]["ok"] += 1

    for h, stats in host_stats.items():
        voice_name = VOICES.get(h, {}).get("name", f"Host{h}")
        if stats["ok"] == 0 and stats["total"] > 0:
            raise RuntimeError(
                f"TTS FATAL: {voice_name} (host {h}) has 0/{stats['total']} successful lines. "
                f"All audio is missing/silent. Aborting before render."
            )
        if stats["total"] > 0 and stats["ok"] / stats["total"] < 0.5:
            raise RuntimeError(
                f"TTS FATAL: {voice_name} (host {h}) has only {stats['ok']}/{stats['total']} "
                f"successful lines (<50%). Too many failures to produce a quality render."
            )

    return {
        "lines": lines,
        "full": full_path if os.path.exists(full_path) else None,
        "total_duration": total_dur,
    }


# Legacy compatibility — V3 pipeline used generate_all_audio
def generate_all_audio(script: dict, output_dir: str) -> dict:
    """Legacy wrapper: converts V4 dialogue script to audio paths dict."""
    if "dialogue" in script:
        return generate_dialogue_audio(script["dialogue"], output_dir)
    # V3 fallback
    raise RuntimeError("V4 pipeline requires dialogue-format script")


if __name__ == "__main__":
    from script_writer import generate_script
    style = sys.argv[1] if len(sys.argv) > 1 else "default"
    script = generate_script(style=style)
    base = os.path.dirname(os.path.abspath(__file__))
    audio_dir = os.path.join(base, "output", "audio_test")
    result = generate_dialogue_audio(script["dialogue"], audio_dir)
    print(json.dumps(
        {k: v for k, v in result.items() if k != "lines"},
        indent=2,
    ))
