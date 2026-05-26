"""
X Spaces Listener
==================
Find and record X Spaces from monitored Bitcoin accounts.
Soft dependency — pipeline continues gracefully if no Spaces found.

Uses yt-dlp for recording and local_whisper for transcription.
"""
import logging
import subprocess
import time
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger("SpacesListener")

# Accounts known to host Bitcoin Spaces
SPACES_HOSTS = [
    "ODELL",
    "MartyBent",
    "PrestonPysh",
    "BitcoinMagazine",
    "TheBitcoinConf",
    "SimplyBitcoinTV",
]


def find_recent_spaces(accounts: List[str] = None,
                       hours: int = 48) -> List[dict]:
    """
    Find recently completed X Spaces from monitored accounts.
    Returns list of Space metadata dicts (may be empty).

    This is a soft dependency — returns [] gracefully on any failure.
    """
    accounts = accounts or SPACES_HOSTS
    spaces = []

    for account in accounts:
        try:
            found = _check_account_spaces(account)
            if found:
                spaces.extend(found)
        except Exception as e:
            logger.debug(f"  @{account}: spaces check failed — {e}")

    logger.info(f"  Spaces found: {len(spaces)} from {len(accounts)} accounts checked")
    return spaces


def _check_account_spaces(account: str) -> List[dict]:
    """Check if an account has recent Spaces (via yt-dlp)."""
    url = f"https://x.com/{account}/spaces"

    try:
        cmd = [
            "yt-dlp", "--flat-playlist", "--no-download",
            "--print", "%(id)s|||%(title)s|||%(duration)s|||%(upload_date)s",
            "--playlist-items", "1:3",
            url
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            return []

        spaces = []
        for line in result.stdout.strip().split("\n"):
            if not line or "|||" not in line:
                continue
            parts = line.split("|||")
            if len(parts) >= 2:
                spaces.append({
                    "space_id": parts[0],
                    "title": parts[1],
                    "duration": int(float(parts[2])) if len(parts) > 2 and parts[2] not in ("NA", "") else 0,
                    "host": account,
                    "url": f"https://x.com/i/spaces/{parts[0]}",
                    "source": "spaces",
                })
        return spaces

    except subprocess.TimeoutExpired:
        return []
    except Exception:
        return []


def record_space(space_url: str, output_path: str,
                 max_duration: int = 3600) -> Optional[str]:
    """
    Record/download a Space using yt-dlp.
    Returns path to audio file, or None.
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "yt-dlp", space_url,
        "-x", "--audio-format", "wav",
        "-o", output_path,
    ]

    if max_duration:
        cmd.extend(["--match-filter", f"duration<={max_duration}"])

    logger.info(f"  Recording Space: {space_url}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=max_duration + 60)
        if result.returncode == 0 and Path(output_path).exists():
            size_mb = Path(output_path).stat().st_size / (1024 * 1024)
            logger.info(f"  Space recorded: {size_mb:.1f} MB")
            return output_path
        else:
            logger.warning(f"  Space recording failed: {result.stderr[:200]}")
    except subprocess.TimeoutExpired:
        logger.warning("  Space recording timed out")
    except Exception as e:
        logger.error(f"  Space recording error: {e}")

    return None


def transcribe_space(audio_path: str) -> Optional[dict]:
    """Transcribe a Space recording using local Whisper."""
    try:
        from pp_services.video_engine.local_whisper import transcribe_audio
        return transcribe_audio(audio_path, model_size="base")
    except Exception as e:
        logger.error(f"  Space transcription failed: {e}")
        return None
