#!/usr/bin/env python3
"""TTS Engine — Single PBX voice pipeline (V4.2).
All narration: ElevenLabs PBX HmUVvDlHsEz0m3eUGLgu.
Model: eleven_multilingual_v2 (gravitas for news anchor).
Speed: 1.2x (V4.2 — faster, more energetic).
"""
import os, sys, json, subprocess, tempfile, time, struct, shutil, logging, re, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# ── Rate limiter for ElevenLabs API (audit P0-U1) ─────────────────────────────
_el_rate_lock = threading.Lock()
_el_rate_calls = []
_EL_RATE_LIMIT = int(os.getenv("ELEVENLABS_RATE_LIMIT_PER_MINUTE", "30"))


def _elevenlabs_rate_limit():
    """Token-bucket rate limiter for ElevenLabs calls."""
    with _el_rate_lock:
        now = time.time()
        _el_rate_calls[:] = [t for t in _el_rate_calls if now - t < 60]
        if len(_el_rate_calls) >= _EL_RATE_LIMIT:
            wait = 60 - (now - _el_rate_calls[0])
            if wait > 0:
                logger.warning(f"[TTS] ElevenLabs rate limit hit ({_EL_RATE_LIMIT}/min) — waiting {wait:.1f}s")
                time.sleep(wait)
        _el_rate_calls.append(time.time())

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

from relay import get_key
try:
    from video_pipeline_v3.tts_normalizer import normalize as tts_normalize
except ImportError:
    from tts_normalizer import normalize as tts_normalize

logger = logging.getLogger(__name__)

# ── LOCAL TTS BACKENDS ──────────────────────────────────────────────────────
_PROSODY_CACHE = {}  # hash(text) -> prosody-planned text


def prosody_plan(text: str, host: int = 2) -> str:
    """Strip all [bracket] prosody markers and return clean text.
    Prosody injection disabled — markers caused TTS artifacts."""
    import re
    return re.sub(r'\[.*?\]', '', text).strip()


PBX_VOICE_ID = "HmUVvDlHsEz0m3eUGLgu"

_PBX_VOICE = {
    "voice_id": PBX_VOICE_ID,
    "name": "PBX",
    "model_id": "eleven_multilingual_v2",
    "speed": 1.20,
    "voice_settings": {
        "stability": 0.35,
        "similarity_boost": 0.90,
        "style": 0.30,
        "use_speaker_boost": True,
    },
}

# ── VOICE CONFIG (V4: Single PBX voice) ───────────────────────────────────
VOICES = {
    2: _PBX_VOICE,
}


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
SILENCE_GAP = 0.08  # seconds between lines — ElevenLabs has natural pauses built in

# Voice mode overrides per segment type (applied to whichever host speaks)
VOICE_MODES = {
    "cold_open":       {"stability": 0.35, "similarity_boost": 0.90, "style": 0.30},
    "setup":           {"stability": 0.35, "similarity_boost": 0.90, "style": 0.30},
    "react":           {"stability": 0.35, "similarity_boost": 0.90, "style": 0.30},
    "bridge":          {"stability": 0.35, "similarity_boost": 0.90, "style": 0.30},
    "social_segment":  {"stability": 0.35, "similarity_boost": 0.90, "style": 0.30},
    "wrap":            {"stability": 0.35, "similarity_boost": 0.90, "style": 0.30},
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

    # Dollar abbreviations: $2B → "2 billion dollars", $5M → "5 million dollars"
    _abbr_scale_map = {"B": "billion", "M": "million", "T": "trillion", "K": "thousand"}
    def _dollar_abbr(m):
        num_str = m.group(1)
        scale_letter = m.group(2).upper()
        scale_word = _abbr_scale_map.get(scale_letter, scale_letter)
        try:
            val = float(num_str)
            spoken = _n2w(val) if val != int(val) else _n2w(int(val))
            return f"{spoken} {scale_word} dollars"
        except Exception:
            return f"{num_str} {scale_word} dollars"
    text = _re.sub(r'\$(\d+(?:\.\d+)?)\s*([BMTKbmtk])\b', _dollar_abbr, text)

    # Non-dollar abbreviations: 2B → "2 billion", 5M → "5 million"
    def _plain_abbr(m):
        num_str = m.group(1)
        scale_letter = m.group(2).upper()
        scale_word = _abbr_scale_map.get(scale_letter, scale_letter)
        try:
            val = float(num_str)
            spoken = _n2w(val) if val != int(val) else _n2w(int(val))
            return f"{spoken} {scale_word}"
        except Exception:
            return f"{num_str} {scale_word}"
    text = _re.sub(r'(?<!\$)(\d+(?:\.\d+)?)\s*([BMbm])\b(?![A-Za-z])', _plain_abbr, text)

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


# ── ElevenLabs Pronunciation Dictionary (server-side) ─────────────────────
# Replaces the regex PRONUNCIATION_MAP below. Dictionary rules are applied
# by ElevenLabs before synthesis — more reliable, no client-side text mutation.
# Managed via: python3 scripts/update_pronunciation.py
_PRONUNCIATION_DICT_CACHE = None

def _get_pronunciation_dict_locators():
    """Load pronunciation dictionary ID from scripts/.pronunciation_dict_id.json."""
    global _PRONUNCIATION_DICT_CACHE
    if _PRONUNCIATION_DICT_CACHE is not None:
        return _PRONUNCIATION_DICT_CACHE
    dict_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "..", "scripts", ".pronunciation_dict_id.json")
    try:
        with open(dict_file) as f:
            info = json.load(f)
        _PRONUNCIATION_DICT_CACHE = [{
            "pronunciation_dictionary_id": info["dictionary_id"],
            "version_id": info["version_id"],
        }]
        logger.info(f"[TTS] Pronunciation dictionary loaded: {info['dictionary_id']}")
    except (FileNotFoundError, KeyError, json.JSONDecodeError):
        _PRONUNCIATION_DICT_CACHE = []
        logger.info("[TTS] No pronunciation dictionary found — using regex fallback")
    return _PRONUNCIATION_DICT_CACHE


# ── Bitcoin Ecosystem Pronunciation Map (RETIRED — kept as fallback) ──────
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
    # Nick Szabo
    "Nick Szabo": "Nick SAY-bo",
    "Szabo": "SAY-bo",
    # Anthony Pompliano
    "Anthony Pompliano": "Anthony pahm-plee-AH-no",
    "Pompliano": "pahm-plee-AH-no",
    "Pomp": "Pomp",
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
    "Jerome Powell": "jeh-ROME Pahl",
    "Powell": "Pahl",
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
    # V4.2: Pronunciation fixes — acronyms and common mispronunciations
    "ETFs": "E-T-Fs",
    "ETF": "E-T-F",
    "fiat": "FY-at",
    "Fiat": "Fy-at",
    "FIAT": "FY-AT",
    "DeFi": "dee-FYE",
    "defi": "dee-FYE",
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
    "satoshis": "sats",
    "MicroStrategy": "My-crow-Strategy",
    "Coinbase": "Coin base",
    "Binance": "BY-nance",
    "Chainalysis": "CHAIN-uh-LY-sis",
    # Issue 10: BTC → Bitcoin spoken form
    "BTC": "Bitcoin",
    # Session fix: hyphen removal to prevent ElevenLabs stretch
    "on-chain": "on chain",
    # Session fix: written-out large numbers → numeral form for natural TTS
    "one and a half trillion": "1.5 trillion",
    "one-and-a-half trillion": "1.5 trillion",
    "one and a half billion": "1.5 billion",
    "one-and-a-half billion": "1.5 billion",
    "one and a half million": "1.5 million",
    "one-and-a-half million": "1.5 million",
    "two and a half trillion": "2.5 trillion",
    "two-and-a-half trillion": "2.5 trillion",
    "two and a half billion": "2.5 billion",
    "two-and-a-half billion": "2.5 billion",
    # V9 FIX 2: Acronyms — spelled out as individual letters
    "KYC": "K Y C",
    "AML": "A M L",
    "SEC": "S E C",
    "FBI": "F B I",
    "IMF": "I M F",
    "GDP": "G D P",
    "CPI": "C P I",
    "OTC": "O T C",
    "NFT": "N F T",
    "NFTs": "N F Ts",
    "DAO": "D A O",
    "DAOs": "D A Os",
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


def strip_right_opener(text: str) -> str:
    """Strip narration that opens with 'Right' as the first word.

    Replaces with the second sentence, or removes the 'Right, ' prefix.
    """
    stripped = text.strip()
    if not stripped:
        return stripped
    # Match "Right," or "Right " or "Right." at the start (case-insensitive)
    if re.match(r'^[Rr]ight[\s,.\-—]+', stripped):
        # Try to find second sentence
        after = re.sub(r'^[Rr]ight[\s,.\-—]+', '', stripped).strip()
        if after:
            # Capitalize first letter
            return after[0].upper() + after[1:] if len(after) > 1 else after.upper()
        return stripped  # fallback: return original if nothing left
    return stripped


def _trim_trailing_mumble(audio_path: str) -> None:
    """Trim trailing artifact/mumble from ElevenLabs TTS output.

    Uses silenceremove to strip non-intelligible tail audio below -40dB
    in the last 0.3 seconds. Applied to every ElevenLabs clip.
    """
    try:
        dur = ffprobe_duration(audio_path)
        if dur <= 1.0:
            return
        trimmed = audio_path + ".mumble_trim.m4a"
        r = subprocess.run(
            ["ffmpeg", "-y", "-i", audio_path,
             "-af", "silenceremove=stop_periods=-1:stop_duration=0.3:stop_threshold=-40dB",
             "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k", trimmed],
            capture_output=True, text=True, timeout=15,
        )
        if r.returncode == 0 and os.path.exists(trimmed) and os.path.getsize(trimmed) > 5000:
            dur_after = ffprobe_duration(trimmed)
            # Sanity: don't trim more than 15% of audio
            if dur_after >= dur * 0.85:
                os.replace(trimmed, audio_path)
                if dur - dur_after > 0.05:
                    logger.info(f"[TTS] Trimmed trailing mumble: {dur:.2f}s → {dur_after:.2f}s")
            else:
                os.remove(trimmed)
        elif os.path.exists(trimmed):
            os.remove(trimmed)
    except Exception as e:
        logger.debug(f"[TTS] Trailing mumble trim skipped: {e}")


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


def _trim_leading_silence(audio_path: str) -> None:
    """Remove leading silence (<-40dB) from TTS output.

    ElevenLabs often pads 0.1-0.2s silence at the start of each clip.
    This accumulates across lines, creating noticeable gaps in the final mix.
    Uses ffmpeg silenceremove filter to strip sub-40dB audio from the start.
    """
    try:
        dur_before = ffprobe_duration(audio_path)
        if dur_before <= 0.5:
            return
        trimmed = audio_path + ".ltrimmed.m4a"
        r = subprocess.run(
            ["ffmpeg", "-y", "-i", audio_path,
             "-af", "silenceremove=start_periods=1:start_silence=0.03:start_threshold=-40dB",
             "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k", trimmed],
            capture_output=True, text=True, timeout=15,
        )
        if r.returncode == 0 and os.path.exists(trimmed) and os.path.getsize(trimmed) > 5000:
            dur_after = ffprobe_duration(trimmed)
            if dur_after >= dur_before * 0.7:  # sanity: don't trim more than 30%
                os.replace(trimmed, audio_path)
                if dur_before - dur_after > 0.02:
                    logger.info(f"[TTS] Trimmed leading silence: {dur_before:.3f}s → {dur_after:.3f}s")
            else:
                os.remove(trimmed)
        elif os.path.exists(trimmed):
            os.remove(trimmed)
    except Exception as e:
        logger.debug(f"[TTS] Leading silence trim skipped: {e}")


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
        "model_id": _PBX_VOICE["model_id"],
        "voice_settings": dict(_PBX_VOICE["voice_settings"]),
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

    # BUG 1 FIX: Strip [DATA], [WARM], [SETUP] etc bracket tags before TTS synthesis
    # These tags are for script structure — narrator should never read them aloud
    text = re.sub(r'^\s*\[[A-Z_]+\]\s*', '', text).strip()
    # Session fix: Never start narration with "Right" as opening word
    text = strip_right_opener(text)
    # Bitcoin/finance pronunciation normalizer (runs first)
    text = tts_normalize(text)
    # Session 4 Fix 3: Expand numbers before TTS to prevent babbling
    text = expand_numbers_for_tts(text)
    # R25 FIX 7: Regex pronunciation map RETIRED — replaced by ElevenLabs
    # Pronunciation Dictionary (id=LK24Dt58S40g429DUG9C). Server-side rules are
    # more reliable and don't break caching. See scripts/update_pronunciation.py.
    # Kept as fallback: uncomment if dictionary is deleted.
    # text = apply_pronunciation_map(text)

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

    # ElevenLabs Pronunciation Dictionary — server-side rules for names/terms
    _pron_dict_locators = _get_pronunciation_dict_locators()

    for ci, chunk in enumerate(chunks):
        body = {
            "text": chunk,
            "model_id": voice["model_id"],
            "voice_settings": voice_settings,
        }
        if _pron_dict_locators:
            body["pronunciation_dictionary_locators"] = _pron_dict_locators
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
            _elevenlabs_rate_limit()  # audit P0-U1
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
            _trim_leading_silence(output_path)
            _trim_trailing_silence(output_path)
            _trim_trailing_mumble(output_path)
            # RETRY: ElevenLabs sometimes returns empty audio - retry up to 3 times
            _validate_attempts = 0
            while _validate_attempts < 3:
                try:
                    validate_tts_output(output_path)
                    break  # success
                except RuntimeError as _ve:
                    _validate_attempts += 1
                    log.warning(f'TTS validate fail attempt {_validate_attempts}/3: {_ve}')
                    if _validate_attempts >= 3:
                        raise
                    import time as _t; _t.sleep(3 * _validate_attempts)
                    # Retry the ElevenLabs call
                    try:
                        import os as _os; _os.remove(output_path)
                    except: pass
                    tts_elevenlabs(text, output_path, host_num, segment_type=segment_type)
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
        capture_output=True, text=True, timeout=120,
    )
    ok = _mp3_to_m4a(mp3_combined, output_path)
    for f in chunk_files + [concat_list, mp3_combined]:
        try:
            if os.path.exists(f):
                os.remove(f)
        except Exception:
            pass
    if ok and os.path.exists(output_path):
        _trim_leading_silence(output_path)
        _trim_trailing_silence(output_path)
        _trim_trailing_mumble(output_path)
        validate_tts_output(output_path)
        _tts_cache_put(cache_key, output_path)
    return ok


def _synthesize_line(i: int, entry: dict, output_dir: str, provider: str = "elevenlabs") -> dict:
    """Synthesize a single dialogue line via ElevenLabs PBX.

    Returns metadata dict with path, duration, host, tts_ok flag.
    """
    text = entry.get("text", "")

    # V4: Single PBX voice — all narration is host 2
    host_num = 2
    voice = VOICES[host_num]
    segment_type = entry.get("type", "")
    line_path = os.path.join(output_dir, f"line_{i:03d}_{voice['name'].lower()}.m4a")

    print(f"  [tts] Line {i:02d} (PBX): {text[:60]}...")

    _tts_ok = tts_elevenlabs(text, line_path, host_num, segment_type=segment_type)
    dur = 0.0

    # Validate output
    if _tts_ok:
        if not os.path.exists(line_path) or os.path.getsize(line_path) < 1000:
            logger.warning(f"[tts] Line {i} zero/tiny audio")
            _tts_ok = False
        else:
            dur = ffprobe_duration(line_path)
            if dur < 0.5 and len(text) > 10:
                logger.warning(f"[tts] Line {i} too short ({dur:.2f}s)")
                _tts_ok = False

    if not _tts_ok:
        raise RuntimeError(
            f"TTS FATAL: ElevenLabs PBX failed for line {i}. "
            f"Text: \"{text[:80]}...\". Refusing to render silence."
        )

    return {
        "index": i,
        "path": line_path,
        "host": host_num,
        "duration": dur,
        "text": text,
        "type": segment_type,
        "tts_ok": True,
        "clip_rank": entry.get("clip_rank", 0),
    }


def generate_dialogue_audio(dialogue: list, output_dir: str) -> dict:
    """Generate audio for PBX single-voice dialogue.

    Pre-generates ALL TTS lines in parallel via ThreadPoolExecutor to eliminate
    sequential API latency stacking. Then assembles timeline and concatenates.

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

    # V9 FIX 8: REMOVED forced PBX sign-off injection.
    # The script writer generates a natural closing — forced injection was cutting it off.

    # V4: Always ElevenLabs PBX
    key = _get_cached_key("ELEVENLABS_API_KEY")
    if not key:
        raise RuntimeError("ELEVENLABS_API_KEY not available. Cannot generate audio.")

    silence_path = os.path.join(output_dir, "silence.m4a")
    if not _generate_silence(silence_path, SILENCE_GAP):
        raise RuntimeError("Failed to generate inter-line silence gap audio")

    # ── Phase 1: Parallel TTS pre-generation ──
    tts_jobs = []
    clip_entries = {}

    for i, entry in enumerate(dialogue):
        if entry.get("host") in ("CLIP", "SPACE_CLIP"):
            clip_entries[i] = entry
        else:
            tts_jobs.append((i, entry))

    # 4 workers for ElevenLabs (rate-safe)
    max_workers = 4
    tts_results = {}

    if tts_jobs:
        print(f"  [tts] Pre-generating {len(tts_jobs)} PBX lines in parallel (workers={max_workers})...")
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(_synthesize_line, idx, entry, output_dir): idx
                for idx, entry in tts_jobs
            }
            for future in as_completed(futures):
                idx = futures[future]
                try:
                    result = future.result()
                    tts_results[result["index"]] = result
                except Exception as e:
                    logger.error(f"[tts] Parallel TTS line {idx} failed: {e}")
                    raise

    # ── Phase 2: Assemble timeline in original order ──
    lines = []
    parts_for_concat = []
    current_time = 0.0

    for i, entry in enumerate(dialogue):
        host = entry.get("host")
        text = entry.get("text", "")

        if host in ("CLIP", "SPACE_CLIP"):
            clip_duration = float(entry.get("duration", 30.0))
            lines.append({
                "path": None,
                "host": host,
                "duration": clip_duration,
                "start": current_time,
                "source": entry.get("source", ""),
                "query": entry.get("query", ""),
                "text": text,
            })
            current_time += clip_duration
            continue

        result = tts_results[i]
        dur = result["duration"]

        lines.append({
            "path": result["path"],
            "host": result["host"],
            "duration": dur,
            "start": current_time,
            "text": text,
            "type": result["type"],
            "tts_ok": result["tts_ok"],
            "clip_rank": result.get("clip_rank", 0),
        })
        parts_for_concat.append(result["path"])
        current_time += dur

        # Add silence gap between lines (not after last line, not before CLIP)
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
        concat_result = subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_file,
             "-c", "copy", full_path],
            capture_output=True, text=True,
        )
        if concat_result.returncode != 0:
            logger.error(f"[tts] FFmpeg concat failed: {concat_result.stderr[:500]}")
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
    successful = sum(1 for l in lines if l.get("tts_ok", False))

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
        if l.get("tts_ok", False):
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
