#!/usr/bin/env python3
"""TTS Engine V7 — Dual-provider: ElevenLabs (default) + Inworld.
Host 1 (Deborah): VeCVR24o7g2y1IxLJzZs at 1.0x — female newscaster setup host.
Host 2 (PBX): HmUVvDlHsEz0m3eUGLgu at 1.2x — male contrarian react host.
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

# DUAL HOST: Deborah (HOST_1) + PBX (HOST_2)
# BANNED: Nicole/Chris/Eryn/Brian/Mark — kdnRe2koJdOK4Ovxn2DI (Eryn) banned Render20
PBX_VOICE_ID = "HmUVvDlHsEz0m3eUGLgu"

_NATASHA_VOICE = {
    "voice_id": "VeCVR24o7g2y1IxLJzZs",
    "name": "Deborah",
    "model_id": "eleven_turbo_v2_5",
    "speed": 1.0,
    "voice_settings": {
        "stability": 0.55,
        "similarity_boost": 0.80,
        "style": 0.30,
        "use_speaker_boost": True,
    },
}

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

VOICES = {
    1: _NATASHA_VOICE,   # HOST_1 → Eryn (female)
    2: _PBX_VOICE,       # HOST_2 → PBX (male) — replaces Mark
}

# ── INWORLD VOICE CONFIGS (set TTS_PROVIDER=inworld in .env to activate) ──
# Winners selected 2026-03-12: Lauren (sharp female) + Nate (authoritative male)
_LAUREN_INWORLD = {
    "voice_id": "Lauren",
    "name": "Lauren",
    "model_id": "inworld-tts-1.5-max",
    "speed": 1.0,
    "temperature": 0.5,
}
_NATE_INWORLD = {
    "voice_id": "Nate",
    "name": "Nate",
    "model_id": "inworld-tts-1.5-max",
    "speed": 1.0,
    "temperature": 0.5,
}
INWORLD_VOICES = {
    1: _LAUREN_INWORLD,
    2: _NATE_INWORLD,
}

def _get_tts_provider() -> str:
    """TTS provider locked to ElevenLabs per PIPELINE_LAWS."""
    val = os.environ.get("TTS_PROVIDER", "elevenlabs").lower().strip()
    if val != "elevenlabs":
        raise RuntimeError(
            f"[TTS] PIPELINE_LAWS violation: TTS_PROVIDER must be 'elevenlabs', got '{val}'. "
            "Inworld returns 0 bytes — never switch providers."
        )
    return "elevenlabs"


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
    r = subprocess.run(
        ["ffmpeg", "-y", "-i", mp3_path,
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
    "Satoshi Nakamoto": "Sah-TOH-shee Nah-kah-MOH-toh",
    "Satoshi": "Sah-TOH-shee",
    "Nakamoto": "Nah-kah-MOH-toh",
    # Saylor
    "Michael Saylor": "MY-kul SAY-lor",
    "Saylor": "SAY-lor",
    # Lyn Alden
    "Lyn Alden": "Lin AWL-den",
    # Lummis
    "Cynthia Lummis": "SIN-thee-ah LUM-iss",
    "Lummis": "LUM-iss",
    # Brunell
    "Natalie Brunell": "NAT-uh-lee broo-NELL",
    "Brunell": "broo-NELL",
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
    "Robert Breedlove": "ROB-ert BREED-love",
    "Breedlove": "BREED-love",
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
    "HODL": "HOD-ul",
    "halving": "HAV-ing",
    "SegWit": "SEG-wit",
    "Segwit": "SEG-wit",
    "mempool": "MEM-pool",
    "multisig": "MUL-tee-sig",
    "satoshis": "sah-TOH-sheez",
    "MicroStrategy": "MY-crow-STRAT-uh-jee",
    "Coinbase": "KOYN-base",
    "Binance": "BY-nance",
    "Chainalysis": "CHAIN-uh-LY-sis",
}


def apply_pronunciation_map(text: str) -> str:
    """Replace names/terms with phonetic versions ElevenLabs renders correctly.
    Processes longer entries first to avoid partial replacements."""
    import re
    # Sort by length descending so longer matches take priority
    for written, phonetic in sorted(PRONUNCIATION_MAP.items(), key=lambda x: -len(x[0])):
        # Word-boundary aware replacement (case-insensitive)
        pattern = re.compile(re.escape(written), re.IGNORECASE)
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


def tts_inworld(text: str, output_path: str, host: int = 1,
                segment_type: str = "narration") -> bool:
    """DISABLED: Inworld TTS banned per PIPELINE_LAWS (0-byte synthesis)."""
    raise RuntimeError(
        "Inworld TTS is disabled per PIPELINE_LAWS. TTS_PROVIDER must be 'elevenlabs'. "
        "Inworld synthesis returns 0 bytes — account not provisioned."
    )


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

    voice = VOICES.get(host, VOICES[1])
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

        for attempt in range(3):
            try:
                r = requests.post(url, json=body, headers=headers, timeout=90)
                if r.status_code == 200:
                    with open(mp3_tmp, "wb") as f:
                        f.write(r.content)
                    # Pre-validate: ElevenLabs sometimes returns empty/tiny responses
                    if os.path.getsize(mp3_tmp) < 1000:
                        print(f"  [tts] WARNING: ElevenLabs returned tiny file ({os.path.getsize(mp3_tmp)}B) for chunk {ci}, retrying...")
                        if attempt < 2:
                            time.sleep(2 ** attempt)
                            continue
                    success = True
                    break
                elif r.status_code == 429:
                    wait = 2 ** attempt
                    print(f"  [tts] Rate limited ({voice['name']}), waiting {wait}s...")
                    time.sleep(wait)
                else:
                    print(f"  [tts] HTTP {r.status_code} ({voice['name']}) attempt {attempt+1}: {r.text[:200]}")
                    if attempt < 2:
                        time.sleep(2 ** attempt)
            except Exception as e:
                print(f"  [tts] Error ({voice['name']}) attempt {attempt+1}: {e}")
                if attempt < 2:
                    time.sleep(2 ** attempt)

        if not success:
            for f in chunk_files:
                try:
                    os.remove(f)
                except Exception:
                    pass
            # P0.6 FIX: Fall back the ENTIRE text to pyttsx3 (not just this chunk).
            # Returning inside the chunk loop would abandon remaining chunks.
            print(f"  [tts] ElevenLabs failed for chunk {ci} — falling back entire text to pyttsx3")
            try:
                import pyttsx3
                _engine = pyttsx3.init()
                _engine.setProperty("rate", 150)
                wav_tmp = output_path + ".pyttsx3.wav"
                _engine.save_to_file(text, wav_tmp)  # full text, not just the failed chunk
                _engine.runAndWait()
                if os.path.exists(wav_tmp) and os.path.getsize(wav_tmp) > 1000:
                    ok = _mp3_to_m4a(wav_tmp, output_path)
                    try:
                        os.remove(wav_tmp)
                    except Exception:
                        pass
                    if ok:
                        print(f"  [tts] pyttsx3 fallback SUCCESS (full text)")
                        return True
            except Exception as pyttsx_err:
                print(f"  [tts] pyttsx3 unavailable: {pyttsx_err}")
            # Final fallback: generate silence so the segment still renders
            return _tts_generate_silence_fallback(text, output_path)
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

    # Only require ElevenLabs key if actually using ElevenLabs
    _active_provider = _get_tts_provider()
    if _active_provider == "elevenlabs":
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

        host_num = int(host) if host in (1, 2, "1", "2") else 1
        # Round 3 FIX 3B: First spoken segment MUST be PBX (opener)
        # Count non-CLIP lines processed so far to determine segment_index
        spoken_count = sum(1 for l in lines if l.get("host") != "CLIP")
        if spoken_count == 0 and host_num != 2:
            logger.info(f"[TTS] Segment 0 — forcing PBX opener (was host={host_num})")
            host_num = 2
        voice = VOICES.get(host_num, VOICES[1])
        segment_type = entry.get("type", "")
        line_path = os.path.join(output_dir, f"line_{i:03d}_{voice['name'].lower()}.m4a")

        mode_tag = f" [{segment_type}]" if segment_type and host_num == 1 else ""
        print(f"  [tts] Line {i:02d} ({voice['name']}{mode_tag}): {text[:60]}...")

        _provider = _get_tts_provider()
        # ElevenLabs only — Inworld disabled per PIPELINE_LAWS
        _tts_ok = tts_elevenlabs(text, line_path, host_num, segment_type=segment_type)
        if _tts_ok:
            dur = ffprobe_duration(line_path)
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
        else:
            print(f"  [tts] FAILED line {i} ({voice['name']})")
            lines.append({
                "path": None,
                "host": host_num,
                "duration": 0.0,
                "start": current_time,
                "text": text,
                "type": segment_type,
                "clip_rank": entry.get("clip_rank", 0),  # PiP FIX: preserve for assembler PiP lookup
            })

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
