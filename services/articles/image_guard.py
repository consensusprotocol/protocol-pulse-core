"""
image_guard.py — Perceptual-hash-based image firewall for article headers.

Prevents banned, duplicate, and low-quality images from being used.

Env-var tunables (all have safe defaults):
    IMAGE_GUARD_BAN_MAX_DIST     max hamming distance to treat as banned match  (default 8)
    IMAGE_GUARD_DUP_MAX_DIST     max hamming distance to treat as duplicate     (default 6)
    IMAGE_GUARD_MIN_ENTROPY      minimum Shannon entropy for quality            (default 3.5)
    IMAGE_GUARD_MIN_VARIANCE     minimum pixel variance for quality             (default 80)
    IMAGE_GUARD_RECENT_WINDOW    hours to keep images in recent-duplicate cache (default 168 = 7 days)

Python 3.8 compatible — uses Optional[] instead of X | None.
"""

import json
import logging
import math
import os
import time
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import imagehash
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_DATA_DIR = Path(os.environ.get("IMAGE_GUARD_DATA_DIR", "data/articles"))
BANNED_PATH = _DATA_DIR / "banned_images.json"
RECENT_PATH = _DATA_DIR / "recent_images.json"

# ---------------------------------------------------------------------------
# Tunables
# ---------------------------------------------------------------------------
BAN_MAX_DIST = int(os.environ.get("IMAGE_GUARD_BAN_MAX_DIST", "8"))
DUP_MAX_DIST = int(os.environ.get("IMAGE_GUARD_DUP_MAX_DIST", "6"))
MIN_ENTROPY = float(os.environ.get("IMAGE_GUARD_MIN_ENTROPY", "3.5"))
MIN_VARIANCE = float(os.environ.get("IMAGE_GUARD_MIN_VARIANCE", "80"))
RECENT_WINDOW_H = int(os.environ.get("IMAGE_GUARD_RECENT_WINDOW", "168"))  # 7 days


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------

def _ensure_data_dir():
    # type: () -> None
    _DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load_json(path):
    # type: (Path) -> list
    if path.exists():
        try:
            with open(str(path), "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            logger.warning("Corrupt JSON at %s — resetting", path)
    return []


def _save_json(path, data):
    # type: (Path, list) -> None
    _ensure_data_dir()
    tmp = str(path) + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, str(path))


# ---------------------------------------------------------------------------
# Hash computation
# ---------------------------------------------------------------------------

def compute_phash(img_bytes):
    # type: (bytes) -> Optional[str]
    """Compute perceptual hash string from raw image bytes."""
    try:
        img = Image.open(BytesIO(img_bytes))
        h = imagehash.phash(img)
        return str(h)
    except Exception as e:
        logger.error("Failed to compute phash: %s", e)
        return None


def _hamming(h1_str, h2_str):
    # type: (str, str) -> int
    """Hamming distance between two hex-encoded imagehash strings."""
    h1 = imagehash.hex_to_hash(h1_str)
    h2 = imagehash.hex_to_hash(h2_str)
    return h1 - h2


# ---------------------------------------------------------------------------
# Quality metrics
# ---------------------------------------------------------------------------

def _image_entropy(img):
    # type: (Image.Image) -> float
    """Shannon entropy of grayscale histogram (0–8 for 8-bit)."""
    gray = img.convert("L")
    hist = gray.histogram()  # 256 bins
    total = sum(hist)
    if total == 0:
        return 0.0
    probs = [float(c) / total for c in hist if c > 0]
    return -sum(p * math.log2(p) for p in probs)


def _image_variance(img):
    # type: (Image.Image) -> float
    """Pixel variance across all channels (measures visual complexity)."""
    arr = np.array(img, dtype=np.float64)
    return float(np.var(arr))


# ---------------------------------------------------------------------------
# Core check
# ---------------------------------------------------------------------------

class ImageVerdict:
    """Result of check_image_bytes()."""
    __slots__ = ("ok", "reason", "phash")

    def __init__(self, ok, reason, phash=None):
        # type: (bool, str, Optional[str]) -> None
        self.ok = ok
        self.reason = reason
        self.phash = phash

    def __repr__(self):
        # type: () -> str
        return "ImageVerdict(ok=%r, reason=%r, phash=%r)" % (self.ok, self.reason, self.phash)


def check_image_bytes(img_bytes, title_hint=""):
    # type: (bytes, str) -> ImageVerdict
    """
    Run the full gauntlet on raw image bytes:
        1. Perceptual hash computation
        2. Banned-image check
        3. Duplicate-image check (recent window)
        4. Quality gate (entropy + variance)

    Returns ImageVerdict with .ok, .reason, .phash
    """
    if not img_bytes or len(img_bytes) < 1000:
        return ImageVerdict(False, "image too small (%d bytes)" % len(img_bytes or b""))

    phash = compute_phash(img_bytes)
    if phash is None:
        return ImageVerdict(False, "could not compute phash")

    # --- Banned check ---
    banned_list = _load_json(BANNED_PATH)
    for entry in banned_list:
        bhash = entry.get("phash", "")
        max_d = entry.get("max_dist", BAN_MAX_DIST)
        if not bhash:
            continue
        try:
            dist = _hamming(phash, bhash)
        except Exception:
            continue
        if dist <= max_d:
            label = entry.get("label", "unknown")
            return ImageVerdict(False, "banned (label=%s, dist=%d)" % (label, dist), phash)

    # --- Duplicate check ---
    now_ts = time.time()
    cutoff = now_ts - RECENT_WINDOW_H * 3600
    recent_list = _load_json(RECENT_PATH)
    for entry in recent_list:
        if entry.get("ts", 0) < cutoff:
            continue
        rhash = entry.get("phash", "")
        if not rhash:
            continue
        try:
            dist = _hamming(phash, rhash)
        except Exception:
            continue
        if dist <= DUP_MAX_DIST:
            return ImageVerdict(False, "duplicate of article_id=%s (dist=%d)" % (
                entry.get("article_id", "?"), dist), phash)

    # --- Quality gate ---
    try:
        img = Image.open(BytesIO(img_bytes))
        ent = _image_entropy(img)
        var = _image_variance(img)
        if ent < MIN_ENTROPY:
            return ImageVerdict(False, "low entropy (%.2f < %.2f)" % (ent, MIN_ENTROPY), phash)
        if var < MIN_VARIANCE:
            return ImageVerdict(False, "low variance (%.1f < %.1f)" % (var, MIN_VARIANCE), phash)
    except Exception as e:
        return ImageVerdict(False, "quality check error: %s" % e, phash)

    return ImageVerdict(True, "passed", phash)


# ---------------------------------------------------------------------------
# Bookkeeping
# ---------------------------------------------------------------------------

def remember_accepted(phash, article_id="", title=""):
    # type: (str, str, str) -> None
    """Record an accepted image in the recent-images cache."""
    recent_list = _load_json(RECENT_PATH)
    recent_list.append({
        "phash": phash,
        "article_id": str(article_id),
        "title": title[:120],
        "ts": time.time(),
    })
    # Prune entries older than window
    cutoff = time.time() - RECENT_WINDOW_H * 3600
    recent_list = [e for e in recent_list if e.get("ts", 0) >= cutoff]
    _save_json(RECENT_PATH, recent_list)
    logger.info("Remembered image phash=%s for article_id=%s", phash, article_id)


def add_banned_image_file(filepath, label="manual_ban", max_dist=None):
    # type: (str, str, Optional[int]) -> Optional[str]
    """
    Ban an image file permanently.  Returns the phash string or None on error.
    """
    try:
        with open(filepath, "rb") as f:
            img_bytes = f.read()
    except IOError as e:
        logger.error("Cannot read file %s: %s", filepath, e)
        return None

    phash = compute_phash(img_bytes)
    if phash is None:
        logger.error("Cannot compute phash for %s", filepath)
        return None

    banned_list = _load_json(BANNED_PATH)

    # Avoid duplicate ban entries
    for entry in banned_list:
        if entry.get("phash") == phash:
            logger.info("Image %s already banned (phash=%s)", filepath, phash)
            return phash

    banned_list.append({
        "phash": phash,
        "label": label,
        "max_dist": max_dist if max_dist is not None else BAN_MAX_DIST,
        "file": os.path.basename(filepath),
        "banned_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    })
    _save_json(BANNED_PATH, banned_list)
    logger.info("Banned image: phash=%s label=%s file=%s", phash, label, filepath)
    return phash


def add_banned_image_bytes(img_bytes, label="manual_ban", max_dist=None):
    # type: (bytes, str, Optional[int]) -> Optional[str]
    """Ban an image from raw bytes. Returns phash or None."""
    phash = compute_phash(img_bytes)
    if phash is None:
        return None

    banned_list = _load_json(BANNED_PATH)
    for entry in banned_list:
        if entry.get("phash") == phash:
            return phash

    banned_list.append({
        "phash": phash,
        "label": label,
        "max_dist": max_dist if max_dist is not None else BAN_MAX_DIST,
        "banned_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    })
    _save_json(BANNED_PATH, banned_list)
    logger.info("Banned image from bytes: phash=%s label=%s", phash, label)
    return phash


def get_banned_count():
    # type: () -> int
    return len(_load_json(BANNED_PATH))


def get_recent_count():
    # type: () -> int
    now_ts = time.time()
    cutoff = now_ts - RECENT_WINDOW_H * 3600
    recent = _load_json(RECENT_PATH)
    return len([e for e in recent if e.get("ts", 0) >= cutoff])
