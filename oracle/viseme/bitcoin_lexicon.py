"""
Bitcoin pronunciation lexicon — CMU Arpabet phonemes for Bitcoin-specific terms.
Falls back to CMU dict for general English words.
"""

BITCOIN_LEXICON = {
    "bitcoin": ["B","IH","T","K","OY","N"],
    "satoshi": ["S","AH","T","OW","SH","IY"],
    "nakamoto": ["N","AH","K","AH","M","OW","T","OW"],
    "sats": ["S","AE","T","S"],
    "hodl": ["HH","AO","D","AH","L"],
    "utxo": ["Y","UW","T","IY","EH","K","S","OW"],
    "mempool": ["M","EH","M","P","UW","L"],
    "hashrate": ["HH","AE","SH","R","EY","T"],
    "hashribbon": ["HH","AE","SH","R","IH","B","AH","N"],
    "halving": ["HH","AE","V","IH","NG"],
    "taproot": ["T","AE","P","R","UW","T"],
    "segwit": ["S","EH","G","W","IH","T"],
    "lightning": ["L","AY","T","N","IH","NG"],
    "ordinals": ["AO","R","D","AH","N","AH","L","Z"],
    "asic": ["EY","S","IH","K"],
    "runes": ["R","UW","N","Z"],
    "multisig": ["M","AH","L","T","IY","S","IH","G"],
    "timelock": ["T","AY","M","L","AO","K"],
    "blockchain": ["B","L","AO","K","CH","EY","N"],
    "decentralized": ["D","IY","S","EH","N","T","R","AH","L","AY","Z","D"],
    "cryptographic": ["K","R","IH","P","T","AH","G","R","AE","F","IH","K"],
    "sovereignty": ["S","AO","V","R","AH","N","T","IY"],
    "cypherpunk": ["S","AY","F","ER","P","AH","NG","K"],
    "coldcard": ["K","OW","L","D","K","AO","R","D"],
    "schnorr": ["SH","N","AO","R"],
    "miner": ["M","AY","N","ER"],
    "protocol": ["P","R","OW","T","AH","K","AO","L"],
    "oracle": ["AO","R","AH","K","AH","L"],
    "saylor": ["S","EY","L","ER"],
    "blackrock": ["B","L","AE","K","R","AO","K"],
    "difficulty": ["D","IH","F","AH","K","AH","L","T","IY"],
    "covenants": ["K","AH","V","AH","N","AH","N","T","S"],
    "tapscript": ["T","AE","P","S","K","R","IH","P","T"],
    "psbt": ["P","IY","EH","S","B","IY","T","IY"],
    "miniscript": ["M","IH","N","IH","S","K","R","IH","P","T"],
    "nocoiner": ["N","OW","K","OY","N","ER"],
    "hashpower": ["HH","AE","SH","P","AW","ER"],
    "stacking": ["S","T","AE","K","IH","NG"],
    "plebs": ["P","L","EH","B","Z"],
}


def get_phonemes(word: str, cmu_dict: dict) -> list:
    """Get phonemes for a word — Bitcoin lexicon first, then CMU dict fallback."""
    word_lower = word.lower().strip(".,!?;:'\"()-")
    if word_lower in BITCOIN_LEXICON:
        return BITCOIN_LEXICON[word_lower]
    entries = cmu_dict.get(word_lower, [])
    return entries[0] if entries else None
