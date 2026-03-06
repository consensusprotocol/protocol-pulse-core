import re
from typing import Dict, List

DOMAIN_LEXICON: Dict[str, List[str]] = {
    "bitcoin": ["B", "IH", "T", "K", "OY", "N"],
    "bitcoiner": ["B", "IH", "T", "K", "OY", "N", "ER"],
    "bitcoins": ["B", "IH", "T", "K", "OY", "N", "Z"],
    "satoshi": ["S", "AH", "T", "OW", "SH", "IY"],
    "satoshis": ["S", "AH", "T", "OW", "SH", "IY", "Z"],
    "nakamoto": ["N", "AA", "K", "AH", "M", "OW", "T", "OW"],
    "hashrate": ["HH", "AE", "SH", "R", "EY", "T"],
    "mempool": ["M", "EH", "M", "P", "UW", "L"],
    "utxo": ["Y", "UW", "T", "IY", "EH", "K", "S", "OW"],
    "taproot": ["T", "AE", "P", "R", "UW", "T"],
    "segwit": ["S", "EH", "G", "W", "IH", "T"],
    "lightning": ["L", "AY", "T", "N", "IH", "NG"],
    "halving": ["HH", "AE", "V", "IH", "NG"],
    "ordinal": ["AO", "R", "D", "AH", "N", "AH", "L"],
    "ordinals": ["AO", "R", "D", "AH", "N", "AH", "L", "Z"],
    "inscription": ["IH", "N", "S", "K", "R", "IH", "P", "SH", "AH", "N"],
    "coinbase": ["K", "OY", "N", "B", "EY", "S"],
    "blockspace": ["B", "L", "AA", "K", "S", "P", "EY", "S"],
    "blockware": ["B", "L", "AA", "K", "W", "EH", "R"],
    "compass": ["K", "AH", "M", "P", "AH", "S"],
    "difficulty": ["D", "IH", "F", "AH", "K", "AH", "L", "T", "IY"],
    "onchain": ["AA", "N", "CH", "EY", "N"],
    "on-chain": ["AA", "N", "CH", "EY", "N"],
    "macro": ["M", "AE", "K", "R", "OW"],
    "deflationary": ["D", "IH", "F", "L", "EY", "SH", "AH", "N", "EH", "R", "IY"],
    "custody": ["K", "AH", "S", "T", "AH", "D", "IY"],
    "multisig": ["M", "AH", "L", "T", "IY", "S", "IH", "G"],
    "coinjoin": ["K", "OY", "N", "JH", "OY", "N"],
    "miner": ["M", "AY", "N", "ER"],
    "miners": ["M", "AY", "N", "ER", "Z"],
    "exahash": ["EH", "K", "S", "AH", "HH", "AE", "SH"],
    "exahashes": ["EH", "K", "S", "AH", "HH", "AE", "SH", "IH", "Z"],
    "treasury": ["T", "R", "EH", "ZH", "ER", "IY"],
    "protocol": ["P", "R", "OW", "T", "AH", "K", "AO", "L"],
    "pulse": ["P", "AH", "L", "S"],
    "oracle": ["AO", "R", "AH", "K", "AH", "L"],
    "etf": ["IY", "T", "IY", "EH", "F"],
    "btc": ["B", "IY", "T", "IY", "S", "IY"],
    "xbt": ["EH", "K", "S", "B", "IY", "T", "IY"],
    "pbx": ["P", "IY", "B", "IY", "EH", "K", "S"],
    "hodl": ["HH", "AO", "D", "AH", "L"],
    "asic": ["EY", "S", "IH", "K"],
    "runes": ["R", "UW", "N", "Z"],
    "schnorr": ["SH", "N", "AO", "R"],
    "tapscript": ["T", "AE", "P", "S", "K", "R", "IH", "P", "T"],
    "psbt": ["P", "IY", "EH", "S", "B", "IY", "T", "IY"],
    "miniscript": ["M", "IH", "N", "IH", "S", "K", "R", "IH", "P", "T"],
    "covenants": ["K", "AH", "V", "AH", "N", "AH", "N", "T", "S"],
    "timelock": ["T", "AY", "M", "L", "AO", "K"],
    "blockchain": ["B", "L", "AO", "K", "CH", "EY", "N"],
    "sovereignty": ["S", "AO", "V", "R", "AH", "N", "T", "IY"],
    "cypherpunk": ["S", "AY", "F", "ER", "P", "AH", "NG", "K"],
    "nocoiner": ["N", "OW", "K", "OY", "N", "ER"],
    "hashpower": ["HH", "AE", "SH", "P", "AW", "ER"],
    "stacking": ["S", "T", "AE", "K", "IH", "NG"],
    "plebs": ["P", "L", "EH", "B", "Z"],
    "saylor": ["S", "EY", "L", "ER"],
    "blackrock": ["B", "L", "AE", "K", "R", "AO", "K"],
    "coldcard": ["K", "OW", "L", "D", "K", "AO", "R", "D"],
    "multisig": ["M", "AH", "L", "T", "IY", "S", "IH", "G"],
    "hashribbons": ["HH", "AE", "SH", "R", "IH", "B", "AH", "N", "Z"],
    "blockheight": ["B", "L", "AA", "K", "HH", "AY", "T"],
    "nonce": ["N", "AA", "N", "S"],
    "merkle": ["M", "ER", "K", "AH", "L"],
    "consensus": ["K", "AH", "N", "S", "EH", "N", "S", "AH", "S"],
    "hashbrown": ["HH", "AE", "SH", "B", "R", "AW", "N"],
    "sats": ["S", "AE", "T", "S"],
}

COMMON_WORDS: Dict[str, List[str]] = {
    "the": ["DH", "AH"], "a": ["AH"], "an": ["AE", "N"],
    "and": ["AE", "N", "D"], "of": ["AH", "V"], "for": ["F", "AO", "R"],
    "is": ["IH", "Z"], "are": ["AA", "R"], "you": ["Y", "UW"],
    "your": ["Y", "AO", "R"], "what": ["W", "AH", "T"],
    "this": ["DH", "IH", "S"], "that": ["DH", "AE", "T"],
    "with": ["W", "IH", "TH"], "just": ["JH", "AH", "S", "T"],
    "live": ["L", "AY", "V"], "price": ["P", "R", "AY", "S"],
    "market": ["M", "AA", "R", "K", "AH", "T"], "today": ["T", "AH", "D", "EY"],
    "high": ["HH", "AY"], "low": ["L", "OW"], "new": ["N", "UW"],
    "all": ["AO", "L"], "time": ["T", "AY", "M"], "now": ["N", "AW"],
}

_WORD_RE = re.compile(r"[A-Za-z0-9\-']+")

def normalize_word(word: str) -> str:
    return word.lower().strip(" \t\r\n.,!?;:\"()[]{}")

def tokenize_text(text: str) -> List[str]:
    return _WORD_RE.findall(text)

def lookup_pronunciation(word: str) -> List[str] | None:
    w = normalize_word(word)
    if not w:
        return None
    if w in DOMAIN_LEXICON:
        return DOMAIN_LEXICON[w]
    if w in COMMON_WORDS:
        return COMMON_WORDS[w]
    if w.isdigit():
        return number_to_phones(w)
    return grapheme_to_phoneme_fallback(w)

def number_to_phones(num_str: str) -> List[str]:
    digit_map = {
        "0": ["Z","IY","R","OW"], "1": ["W","AH","N"], "2": ["T","UW"],
        "3": ["TH","R","IY"], "4": ["F","AO","R"], "5": ["F","AY","V"],
        "6": ["S","IH","K","S"], "7": ["S","EH","V","AH","N"],
        "8": ["EY","T"], "9": ["N","AY","N"],
    }
    phones: List[str] = []
    for ch in num_str:
        phones.extend(digit_map.get(ch, []))
    return phones or ["AH"]

def grapheme_to_phoneme_fallback(word: str) -> List[str]:
    rules = [
        ("tion",["SH","AH","N"]), ("sion",["ZH","AH","N"]),
        ("ough",["OW"]), ("eigh",["EY"]), ("igh",["AY"]),
        ("air",["EH","R"]), ("ear",["IH","R"]), ("ure",["Y","UH","R"]),
        ("th",["TH"]), ("sh",["SH"]), ("ch",["CH"]), ("ph",["F"]),
        ("ck",["K"]), ("ng",["NG"]), ("qu",["K","W"]), ("wh",["W"]),
        ("ai",["EY"]), ("ay",["EY"]), ("ea",["IY"]), ("ee",["IY"]),
        ("ie",["IY"]), ("oa",["OW"]), ("oo",["UW"]), ("ou",["AW"]),
        ("ow",["OW"]), ("oi",["OY"]), ("oy",["OY"]), ("au",["AO"]),
        ("ar",["AA","R"]), ("or",["AO","R"]),
    ]
    singles = {
        "a":["AE"],"b":["B"],"c":["K"],"d":["D"],"e":["EH"],
        "f":["F"],"g":["G"],"h":["HH"],"i":["IH"],"j":["JH"],
        "k":["K"],"l":["L"],"m":["M"],"n":["N"],"o":["AO"],
        "p":["P"],"q":["K"],"r":["R"],"s":["S"],"t":["T"],
        "u":["AH"],"v":["V"],"w":["W"],"x":["K","S"],"y":["Y"],
        "z":["Z"],"-":[],"'":[]
    }
    out: List[str] = []
    i = 0
    while i < len(word):
        matched = False
        for grapheme, phones in rules:
            if word[i:i+len(grapheme)] == grapheme:
                out.extend(phones)
                i += len(grapheme)
                matched = True
                break
        if matched:
            continue
        out.extend(singles.get(word[i], []))
        i += 1
    return out or ["AH"]
