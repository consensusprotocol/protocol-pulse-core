"""
nostr_keys.py — Keypair management for Protocol Pulse's Nostr identity.

Handles generation, storage, and bech32 encoding of Nostr keys.
Keys are read from environment variables (NOSTR_PRIVATE_KEY, NOSTR_PUBLIC_KEY, NOSTR_NPUB).
On first run: generate and print instructions for adding to .env.
"""
import os
import logging

logger = logging.getLogger(__name__)

try:
    from pynostr.key import PrivateKey as _PrivateKey
    _PYNOSTR_OK = True
except ImportError:
    _PYNOSTR_OK = False
    logger.error("pynostr not installed — run: pip install pynostr")


def generate_keypair() -> dict:
    """Generate a new Nostr keypair. Returns dict with all key formats."""
    if not _PYNOSTR_OK:
        raise RuntimeError("pynostr not installed")
    k = _PrivateKey()
    return {
        "private_key_hex": k.hex(),
        "public_key_hex": k.public_key.hex(),
        "npub": k.public_key.bech32(),
        "nsec": k.bech32(),
    }


def get_pp_private_key() -> str:
    """Return PP private key hex from env. Raises if missing."""
    key = os.environ.get("NOSTR_PRIVATE_KEY", "")
    if not key or len(key) != 64:
        raise RuntimeError("NOSTR_PRIVATE_KEY not set or invalid in .env")
    return key


def get_pp_public_key() -> str:
    """Return PP public key hex from env."""
    key = os.environ.get("NOSTR_PUBLIC_KEY", "")
    if not key or len(key) != 64:
        # Derive from private key
        if _PYNOSTR_OK:
            try:
                priv = get_pp_private_key()
                k = _PrivateKey.from_hex(priv)
                return k.public_key.hex()
            except Exception:
                pass
        raise RuntimeError("NOSTR_PUBLIC_KEY not set and cannot be derived")
    return key


def get_pp_npub() -> str:
    """Return PP npub (bech32 public key) for display."""
    npub = os.environ.get("NOSTR_NPUB", "")
    if npub:
        return npub
    if _PYNOSTR_OK:
        try:
            priv = get_pp_private_key()
            k = _PrivateKey.from_hex(priv)
            return k.public_key.bech32()
        except Exception:
            pass
    return "npub1unknown"


def ensure_keypair_in_env(env_path: str = None) -> dict:
    """
    Check if PP keypair exists in env. If not, generate and append to env file.
    Returns the current keypair info.
    """
    try:
        priv = get_pp_private_key()
        pub = get_pp_public_key()
        npub = get_pp_npub()
        return {"private_key_hex": priv, "public_key_hex": pub, "npub": npub}
    except RuntimeError:
        pass

    # Generate new keypair
    if not _PYNOSTR_OK:
        raise RuntimeError("pynostr required to generate keypair")

    kp = generate_keypair()
    logger.info("Generated new PP Nostr keypair: npub=%s", kp["npub"])

    if env_path:
        try:
            with open(env_path, "a") as f:
                f.write(f"\nNOSTR_PRIVATE_KEY={kp['private_key_hex']}\n")
                f.write(f"NOSTR_PUBLIC_KEY={kp['public_key_hex']}\n")
                f.write(f"NOSTR_NPUB={kp['npub']}\n")
                f.write(f"NOSTR_NSEC={kp['nsec']}\n")
            logger.info("Keypair appended to %s", env_path)
        except Exception as e:
            logger.error("Could not write keypair to %s: %s", env_path, e)

    # Set in-process env vars
    os.environ["NOSTR_PRIVATE_KEY"] = kp["private_key_hex"]
    os.environ["NOSTR_PUBLIC_KEY"] = kp["public_key_hex"]
    os.environ["NOSTR_NPUB"] = kp["npub"]
    return kp


if __name__ == "__main__":
    kp = generate_keypair()
    print("=== NEW NOSTR KEYPAIR ===")
    print(f"NOSTR_PRIVATE_KEY={kp['private_key_hex']}")
    print(f"NOSTR_PUBLIC_KEY={kp['public_key_hex']}")
    print(f"NOSTR_NPUB={kp['npub']}")
    print(f"NOSTR_NSEC={kp['nsec']}")
    print("Add these to core/.env")
