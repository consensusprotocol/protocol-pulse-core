#!/usr/bin/env python3
"""
ElevenLabs Pronunciation Dictionary Manager.

Creates/updates a pronunciation dictionary for Protocol Pulse TTS.
Replaces the fragile regex PRONUNCIATION_MAP in tts_engine.py with
server-side rules that ElevenLabs applies before synthesis.

Usage:
    python3 scripts/update_pronunciation.py              # Create/replace full dictionary
    python3 scripts/update_pronunciation.py --add "word=pronunciation"  # Add single rule
    python3 scripts/update_pronunciation.py --list        # List current rules
    python3 scripts/update_pronunciation.py --test "fiat satoshis"  # Generate test clip
"""
import argparse
import json
import os
import sys
import time

import requests

# ── Config ────────────────────────────────────────────────────────────────────
DICT_NAME = "protocol_pulse_btc"
DICT_DESCRIPTION = "Bitcoin ecosystem pronunciations for Protocol Pulse TTS"
DICT_ID_FILE = os.path.join(os.path.dirname(__file__), ".pronunciation_dict_id.json")
BASE_URL = "https://api.elevenlabs.io/v1"


def _get_key():
    key = os.getenv("ELEVENLABS_API_KEY")
    if not key:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
        key = os.getenv("ELEVENLABS_API_KEY")
    if not key:
        print("ERROR: ELEVENLABS_API_KEY not set")
        sys.exit(1)
    return key


def _headers(key):
    return {"xi-api-key": key, "Content-Type": "application/json"}


def _save_dict_id(dict_id, version_id):
    with open(DICT_ID_FILE, "w") as f:
        json.dump({"dictionary_id": dict_id, "version_id": version_id}, f, indent=2)
    print(f"  Saved dict ID to {DICT_ID_FILE}")


def _load_dict_id():
    if os.path.exists(DICT_ID_FILE):
        with open(DICT_ID_FILE) as f:
            return json.load(f)
    return None


# ── Full pronunciation ruleset ────────────────────────────────────────────────
# These use "alias" type — ElevenLabs reads the alias text instead of the original.
# For proper names, alias is more reliable than IPA phonemes with this model.
RULES = [
    # === Names: People ===
    {"string_to_replace": "Satoshi Nakamoto", "type": "alias", "alias": "sah TOE shee nah kah MOE toe"},
    {"string_to_replace": "Satoshi", "type": "alias", "alias": "sah TOE shee"},
    {"string_to_replace": "Nakamoto", "type": "alias", "alias": "nah kah MOE toe"},
    {"string_to_replace": "Saylor", "type": "alias", "alias": "Sayler"},
    {"string_to_replace": "Michael Saylor", "type": "alias", "alias": "Michael Sayler"},
    {"string_to_replace": "Lyn Alden", "type": "alias", "alias": "Lin Allden"},
    {"string_to_replace": "Cynthia Lummis", "type": "alias", "alias": "SIN-thee-ah LUM-iss"},
    {"string_to_replace": "Lummis", "type": "alias", "alias": "LUM-iss"},
    {"string_to_replace": "Natalie Brunell", "type": "alias", "alias": "Natalie Brunelle"},
    {"string_to_replace": "Brunell", "type": "alias", "alias": "Brunelle"},
    {"string_to_replace": "Preston Pysh", "type": "alias", "alias": "Preston PISH"},
    {"string_to_replace": "Pysh", "type": "alias", "alias": "PISH"},
    {"string_to_replace": "Max Keiser", "type": "alias", "alias": "MAX KY-zer"},
    {"string_to_replace": "Keiser", "type": "alias", "alias": "KY-zer"},
    {"string_to_replace": "Nayib Bukele", "type": "alias", "alias": "NYE-eeb boo-KEH-leh"},
    {"string_to_replace": "Bukele", "type": "alias", "alias": "boo-KEH-leh"},
    {"string_to_replace": "Saifedean Ammous", "type": "alias", "alias": "Sigh-fuh-dean Ah-moose"},
    {"string_to_replace": "Saifedean", "type": "alias", "alias": "Sigh-fuh-dean"},
    {"string_to_replace": "Ammous", "type": "alias", "alias": "Ah-moose"},
    {"string_to_replace": "Robert Breedlove", "type": "alias", "alias": "Robert BREED love"},
    {"string_to_replace": "Breedlove", "type": "alias", "alias": "BREED love"},
    {"string_to_replace": "Alex Gladstein", "type": "alias", "alias": "AL-ex GLAD-steen"},
    {"string_to_replace": "Gladstein", "type": "alias", "alias": "GLAD-steen"},
    {"string_to_replace": "Knut Svanholm", "type": "alias", "alias": "kuh-NOOT SVAHN-holm"},
    {"string_to_replace": "Svanholm", "type": "alias", "alias": "SVAHN-holm"},
    {"string_to_replace": "Luke Dashjr", "type": "alias", "alias": "LUKE DASH-junior"},
    {"string_to_replace": "Dashjr", "type": "alias", "alias": "DASH-junior"},
    {"string_to_replace": "Andreas Antonopoulos", "type": "alias", "alias": "ahn-DRAY-us an-TON-oh-POO-lus"},
    {"string_to_replace": "Antonopoulos", "type": "alias", "alias": "an-TON-oh-POO-lus"},
    {"string_to_replace": "Andreas", "type": "alias", "alias": "ahn-DRAY-us"},
    {"string_to_replace": "Charlie Shrem", "type": "alias", "alias": "CHAR-lee SHREM"},
    {"string_to_replace": "Shrem", "type": "alias", "alias": "SHREM"},
    {"string_to_replace": "Lawrence Lepard", "type": "alias", "alias": "LAW-rents leh-PARD"},
    {"string_to_replace": "Larry Lepard", "type": "alias", "alias": "LAIR-ee leh-PARD"},
    {"string_to_replace": "Lepard", "type": "alias", "alias": "leh-PARD"},
    {"string_to_replace": "Erik Voorhees", "type": "alias", "alias": "AIR-ik VOR-hees"},
    {"string_to_replace": "Voorhees", "type": "alias", "alias": "VOR-hees"},
    {"string_to_replace": "Gabor Gurbacs", "type": "alias", "alias": "GAH-bor GUR-bacs"},
    {"string_to_replace": "Gurbacs", "type": "alias", "alias": "GUR-bacs"},
    {"string_to_replace": "Gary Gensler", "type": "alias", "alias": "GAIR-ee GENZ-ler"},
    {"string_to_replace": "Gensler", "type": "alias", "alias": "GENZ-ler"},
    {"string_to_replace": "Jerome Powell", "type": "alias", "alias": "jeh-ROME Pahl"},
    {"string_to_replace": "Powell", "type": "alias", "alias": "Pahl"},
    {"string_to_replace": "CJ Konstantinos", "type": "alias", "alias": "see-JAY kon-stan-TEE-nos"},
    {"string_to_replace": "Konstantinos", "type": "alias", "alias": "kon-stan-TEE-nos"},
    {"string_to_replace": "Bob Iaccino", "type": "alias", "alias": "BOB ee-ah-CHEE-no"},
    {"string_to_replace": "Iaccino", "type": "alias", "alias": "ee-ah-CHEE-no"},
    {"string_to_replace": "Alex Stanczyk", "type": "alias", "alias": "AL-ex STAN-chik"},
    {"string_to_replace": "Stanczyk", "type": "alias", "alias": "STAN-chik"},
    {"string_to_replace": "Matt Odell", "type": "alias", "alias": "MAT OH-dell"},
    {"string_to_replace": "Odell", "type": "alias", "alias": "OH-dell"},
    # === Acronyms & Technical ===
    {"string_to_replace": "ETFs", "type": "alias", "alias": "E.T.F.s"},
    {"string_to_replace": "ETF", "type": "alias", "alias": "E.T.F."},
    {"string_to_replace": "BTC", "type": "alias", "alias": "Bitcoin"},
    {"string_to_replace": "DeFi", "type": "alias", "alias": "dee-FYE"},
    {"string_to_replace": "defi", "type": "alias", "alias": "dee-FYE"},
    {"string_to_replace": "UTXO", "type": "alias", "alias": "you-tee-ex-oh"},
    {"string_to_replace": "SegWit", "type": "alias", "alias": "SEG-wit"},
    {"string_to_replace": "Segwit", "type": "alias", "alias": "SEG-wit"},
    {"string_to_replace": "EH/s", "type": "alias", "alias": "exahashes per second"},
    {"string_to_replace": "TH/s", "type": "alias", "alias": "terahashes per second"},
    {"string_to_replace": "PH/s", "type": "alias", "alias": "petahashes per second"},
    # === Pronunciation fixes ===
    {"string_to_replace": "fiat", "type": "alias", "alias": "FY-at"},
    {"string_to_replace": "Fiat", "type": "alias", "alias": "Fy-at"},
    {"string_to_replace": "FIAT", "type": "alias", "alias": "FY-AT"},
    {"string_to_replace": "HODL", "type": "alias", "alias": "HODDLE"},
    {"string_to_replace": "hodl", "type": "alias", "alias": "HODDLE"},
    {"string_to_replace": "satoshis", "type": "alias", "alias": "sats"},
    {"string_to_replace": "halving", "type": "alias", "alias": "HAV-ing"},
    {"string_to_replace": "mempool", "type": "alias", "alias": "mem-pool"},
    {"string_to_replace": "multisig", "type": "alias", "alias": "MUL-tee-sig"},
    {"string_to_replace": "MicroStrategy", "type": "alias", "alias": "Strategy"},
    {"string_to_replace": "Coinbase", "type": "alias", "alias": "Coin base"},
    {"string_to_replace": "Binance", "type": "alias", "alias": "BY-nance"},
    {"string_to_replace": "Kraken", "type": "alias", "alias": "KRAH-ken"},
    {"string_to_replace": "Bitfinex", "type": "alias", "alias": "Bit FY-nex"},
    {"string_to_replace": "Bitstamp", "type": "alias", "alias": "Bit stamp"},
    {"string_to_replace": "Bybit", "type": "alias", "alias": "BY-bit"},
    {"string_to_replace": "OKX", "type": "alias", "alias": "oh-kay-ex"},
    {"string_to_replace": "Gemini", "type": "alias", "alias": "JEM-in-eye"},
    {"string_to_replace": "BitMEX", "type": "alias", "alias": "Bit-mex"},
    {"string_to_replace": "dYdX", "type": "alias", "alias": "dee-why-dee-ex"},    {"string_to_replace": "Chainalysis", "type": "alias", "alias": "CHAIN-uh-LY-sis"},
    {"string_to_replace": "on-chain", "type": "alias", "alias": "on chain"},
    {"string_to_replace": "satoshi zaps", "type": "alias", "alias": "sat zaps"},
    {"string_to_replace": "Satoshi zaps", "type": "alias", "alias": "sat zaps"},
    {"string_to_replace": "regulatory", "type": "alias", "alias": "REG-you-luh-tory"},
]


def create_dictionary(key):
    """Create a new pronunciation dictionary with all rules."""
    print(f"Creating dictionary '{DICT_NAME}' with {len(RULES)} rules...")
    url = f"{BASE_URL}/pronunciation-dictionaries/add-from-rules"
    body = {
        "name": DICT_NAME,
        "description": DICT_DESCRIPTION,
        "rules": RULES,
    }
    r = requests.post(url, json=body, headers=_headers(key), timeout=30)
    if r.status_code in (200, 201):
        data = r.json()
        dict_id = data.get("id")
        version_id = data.get("version_id")
        print(f"  Created: id={dict_id}, version={version_id}")
        _save_dict_id(dict_id, version_id)
        return dict_id, version_id
    else:
        print(f"  ERROR {r.status_code}: {r.text[:500]}")
        sys.exit(1)


def replace_rules(key, dict_id):
    """Replace all rules in an existing dictionary."""
    print(f"Replacing all rules in dictionary {dict_id}...")
    url = f"{BASE_URL}/pronunciation-dictionaries/{dict_id}/rules/set"
    body = {"rules": RULES}
    r = requests.post(url, json=body, headers=_headers(key), timeout=30)
    if r.status_code in (200, 201):
        data = r.json()
        version_id = data.get("version_id", "")
        print(f"  Updated: {len(RULES)} rules, version={version_id}")
        _save_dict_id(dict_id, version_id)
        return version_id
    else:
        print(f"  ERROR {r.status_code}: {r.text[:500]}")
        return None


def add_rule(key, word, pronunciation):
    """Add a single rule to the existing dictionary."""
    info = _load_dict_id()
    if not info:
        print("No dictionary exists. Run without --add first to create one.")
        sys.exit(1)
    dict_id = info["dictionary_id"]
    url = f"{BASE_URL}/pronunciation-dictionaries/{dict_id}/rules/add"
    rule = {"string_to_replace": word, "type": "alias", "alias": pronunciation}
    r = requests.post(url, json={"rules": [rule]}, headers=_headers(key), timeout=30)
    if r.status_code in (200, 201):
        data = r.json()
        version_id = data.get("version_id", "")
        _save_dict_id(dict_id, version_id)
        print(f"  Added: '{word}' → '{pronunciation}' (version={version_id})")
    else:
        print(f"  ERROR {r.status_code}: {r.text[:500]}")


def list_rules():
    """List rules from the saved dictionary."""
    info = _load_dict_id()
    if not info:
        print("No dictionary created yet.")
        return
    print(f"Dictionary: {info['dictionary_id']} (version: {info['version_id']})")
    print(f"\nLocal rules ({len(RULES)}):")
    for r in RULES:
        print(f"  {r['string_to_replace']:30s} → {r['alias']}")


def test_pronunciation(key, text):
    """Generate a test TTS clip using the pronunciation dictionary."""
    info = _load_dict_id()
    if not info:
        print("No dictionary created yet. Run without flags first.")
        sys.exit(1)

    voice_id = "HmUVvDlHsEz0m3eUGLgu"  # PBX
    url = f"{BASE_URL}/text-to-speech/{voice_id}"
    body = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "pronunciation_dictionary_locators": [
            {
                "pronunciation_dictionary_id": info["dictionary_id"],
                "version_id": info["version_id"],
            }
        ],
    }
    print(f"Generating TTS with dictionary: '{text}'")
    r = requests.post(url, json=body, headers=_headers(key), timeout=60)
    if r.status_code == 200:
        out = "/tmp/test_pronunciation.mp3"
        with open(out, "wb") as f:
            f.write(r.content)
        size = os.path.getsize(out)
        print(f"  Generated: {out} ({size:,} bytes)")
        return out
    else:
        print(f"  ERROR {r.status_code}: {r.text[:500]}")
        return None


def main():
    parser = argparse.ArgumentParser(description="ElevenLabs Pronunciation Dictionary Manager")
    parser.add_argument("--add", help="Add rule: 'word=pronunciation'")
    parser.add_argument("--list", action="store_true", help="List current rules")
    parser.add_argument("--test", help="Test TTS with dictionary (provide text)")
    args = parser.parse_args()

    key = _get_key()

    if args.list:
        list_rules()
        return

    if args.test:
        test_pronunciation(key, args.test)
        return

    if args.add:
        if "=" not in args.add:
            print("Usage: --add 'word=pronunciation'")
            sys.exit(1)
        word, pron = args.add.split("=", 1)
        add_rule(key, word.strip(), pron.strip())
        return

    # Default: create or update full dictionary
    info = _load_dict_id()
    if info:
        replace_rules(key, info["dictionary_id"])
    else:
        create_dictionary(key)

    print(f"\nDone. {len(RULES)} pronunciation rules active.")
    print("To test: python3 scripts/update_pronunciation.py --test 'Bitcoin fiat satoshis HODL'")


if __name__ == "__main__":
    main()
