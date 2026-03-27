"""
TTS Text Normalizer — Bitcoin/Finance pronunciation corrections.

Runs BEFORE Kokoro or ElevenLabs to fix mispronunciations of crypto/finance
terms, currency values, hash rate units, and technical acronyms.

Usage:
    from video_pipeline_v3.tts_normalizer import normalize
    clean = normalize("Bitcoin hit $1T at 500 EH/s on SHA-256")
"""

import re

# ---------------------------------------------------------------------------
# Currency: $1T, $1.5B, $200M, $10K  (with optional decimals)
# ---------------------------------------------------------------------------
_SCALE_MAP = {
    "T": "trillion",
    "B": "billion",
    "M": "million",
    "K": "thousand",
}

_ONES = {
    0: "zero", 1: "one", 2: "two", 3: "three", 4: "four",
    5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine",
    10: "ten", 11: "eleven", 12: "twelve", 13: "thirteen",
    14: "fourteen", 15: "fifteen", 16: "sixteen", 17: "seventeen",
    18: "eighteen", 19: "nineteen",
}
_TENS = {
    2: "twenty", 3: "thirty", 4: "forty", 5: "fifty",
    6: "sixty", 7: "seventy", 8: "eighty", 9: "ninety",
}


def _num_to_words(n: float) -> str:
    """Simple number-to-words for values typically seen in finance headlines."""
    if n == int(n):
        n = int(n)
    if isinstance(n, float):
        whole = int(n)
        frac = round(n - whole, 2)
        frac_str = str(frac)[2:]  # e.g. "5" from 0.5
        return f"{_int_to_words(whole)} point {' '.join(_int_to_words(int(d)) for d in frac_str)}"
    return _int_to_words(n)


def _int_to_words(n: int) -> str:
    if n < 0:
        return "negative " + _int_to_words(-n)
    if n < 20:
        return _ONES[n]
    if n < 100:
        t, o = divmod(n, 10)
        return _TENS[t] + ("-" + _ONES[o] if o else "")
    if n < 1000:
        h, rem = divmod(n, 100)
        return _ONES[h] + " hundred" + (" " + _int_to_words(rem) if rem else "")
    if n < 1_000_000:
        th, rem = divmod(n, 1000)
        return _int_to_words(th) + " thousand" + (" " + _int_to_words(rem) if rem else "")
    if n < 1_000_000_000:
        m, rem = divmod(n, 1_000_000)
        return _int_to_words(m) + " million" + (" " + _int_to_words(rem) if rem else "")
    if n < 1_000_000_000_000:
        b, rem = divmod(n, 1_000_000_000)
        return _int_to_words(b) + " billion" + (" " + _int_to_words(rem) if rem else "")
    t, rem = divmod(n, 1_000_000_000_000)
    return _int_to_words(t) + " trillion" + (" " + _int_to_words(rem) if rem else "")


def _expand_dollar_scale(m: re.Match) -> str:
    """$1T → one trillion dollars, $2.5B → two point five billion dollars."""
    num_str = m.group(1).replace(",", "")
    scale = m.group(2).upper()
    try:
        val = float(num_str)
        spoken = _num_to_words(val)
        return f"{spoken} {_SCALE_MAP[scale]} dollars"
    except (ValueError, KeyError):
        return m.group(0)


def _expand_bare_scale(m: re.Match) -> str:
    """1T (no $) → one trillion."""
    num_str = m.group(1).replace(",", "")
    scale = m.group(2).upper()
    try:
        val = float(num_str)
        spoken = _num_to_words(val)
        return f"{spoken} {_SCALE_MAP[scale]}"
    except (ValueError, KeyError):
        return m.group(0)


# ---------------------------------------------------------------------------
# Hash rate units
# ---------------------------------------------------------------------------
_HASHRATE_MAP = {
    "EH/s": "exa-hash per second",
    "TH/s": "tera-hash per second",
    "PH/s": "peta-hash per second",
    "GH/s": "giga-hash per second",
    "MH/s": "mega-hash per second",
}

# ---------------------------------------------------------------------------
# Technical terms
# ---------------------------------------------------------------------------
_TERM_MAP = {
    "SHA-256": "S-H-A 256",
    "SHA256": "S-H-A 256",
    "exahash": "exa-hash",
    "Exahash": "exa-hash",
    "EXAHASH": "exa-hash",
    "exahashes": "exa-hashes",
    "Exahashes": "exa-hashes",
    "EXAHASHES": "exa-hashes",
    "petahash": "peta-hash",
    "petahashes": "peta-hashes",
    "terahash": "tera-hash",
    "terahashes": "tera-hashes",
    "gigahash": "giga-hash",
    "megahash": "mega-hash",
    "kWh": "kilowatt hour",
    "MWh": "megawatt hour",
    "GWh": "gigawatt hour",
    "HODL": "hodl",
    "hodl": "hodl",
    "DeFi": "dee-fi",
    "dApps": "dee-apps",
    "ETF": "E-T-F",
    "ETFs": "E-T-Fs",
    "SEC": "S-E-C",
    "ASIC": "ay-sick",
    "ASICs": "ay-sicks",
    "PoW": "proof of work",
    "PoS": "proof of stake",
    "CBDC": "C-B-D-C",
    "CBDCs": "C-B-D-Cs",
    "AML": "A-M-L",
    "KYC": "K-Y-C",
    "NFT": "N-F-T",
    "NFTs": "N-F-Ts",
    "DCA": "D-C-A",
    "ATH": "all time high",
    "ATL": "all time low",
    "FUD": "fud",
    "FOMO": "foe-moe",
}

# ---------------------------------------------------------------------------
# Ordinals
# ---------------------------------------------------------------------------
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


# ============================= MAIN ENTRY =================================

def normalize(text: str) -> str:
    """Normalize Bitcoin/finance text for TTS pronunciation.

    Applies all substitution rules in correct order:
    1. Dollar + scale abbreviations ($1T, $2.5B, $200M)
    2. Bare scale abbreviations (1T, 2B without $)
    3. Hash rate units (EH/s, TH/s, PH/s)
    4. Technical terms & acronyms (SHA-256, kWh, HODL, ETF)
    5. BTC → Bitcoin (standalone)
    6. sats → satoshis
    7. Ordinals (1st → first)
    """
    # 1. Dollar + scale: $1T, $2.5B, $200M, $10K
    text = re.sub(
        r'\$\s*([\d,.]+)\s*([TBMKtbmk])\b',
        _expand_dollar_scale,
        text
    )

    # 2. Bare scale (no dollar sign): 47K, 2B — word boundary after scale letter
    #    Avoid matching things like "T1" or mid-word
    text = re.sub(
        r'\b([\d,.]+)\s*([TBMKtbmk])\b',
        _expand_bare_scale,
        text
    )

    # 3. Hash rate units — match with optional number prefix
    for unit, spoken in _HASHRATE_MAP.items():
        text = re.sub(
            r'(?i)\b' + re.escape(unit) + r'\b',
            spoken,
            text
        )

    # 4. Technical terms (longest first to avoid partial matches)
    for term, spoken in sorted(_TERM_MAP.items(), key=lambda x: -len(x[0])):
        text = re.sub(r'\b' + re.escape(term) + r'\b', spoken, text)

    # 5. BTC → Bitcoin (standalone, case-sensitive for the acronym)
    text = re.sub(r'\bBTC\b', 'Bitcoin', text)

    # 6. sats → satoshis (lowercase, standalone)
    text = re.sub(r'\bsats\b', 'satoshis', text, flags=re.IGNORECASE)

    # 7. Ordinals
    def _ordinal_sub(m):
        return _ORDINAL_MAP.get(m.group(0).lower(), m.group(0))
    text = re.sub(r'\b\d{1,2}(?:st|nd|rd|th)\b', _ordinal_sub, text, flags=re.IGNORECASE)

    # Clean up any double spaces
    text = re.sub(r'  +', ' ', text).strip()

    return text


# Public alias for convenience
normalize_text = normalize
