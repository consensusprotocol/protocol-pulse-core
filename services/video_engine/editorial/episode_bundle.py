"""
Episode Bundle Manager
======================
Creates and manages the episode bundle — the atomic artifact.
Every run produces: data/episodes/YYYY-MM-DD/ with standard subfolders.
This is what makes the system reproducible, debuggable, and improvable.
"""
import json
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger("EpisodeBundle")

EPISODES_DIR = Path("data/episodes")

SUBDIRS = [
    "inputs", "candidates", "clusters", "show_plan",
    "qa", "clips", "voiceovers", "overlays", "broll",
    "manifest", "final", "shorts", "distribution_pack",
    "costs", "logs"
]


def create_episode_bundle(date_str: str = None) -> Path:
    """Create episode directory structure. Safe to call multiple times (idempotent)."""
    if not date_str:
        date_str = datetime.utcnow().strftime("%Y-%m-%d")

    base = EPISODES_DIR / date_str
    for subdir in SUBDIRS:
        (base / subdir).mkdir(parents=True, exist_ok=True)

    logger.info(f"Episode bundle ready: {base}")
    return base


def save_artifact(bundle_path: Path, subdir: str, filename: str, data: dict) -> Path:
    """Save a JSON artifact to the episode bundle."""
    out_path = bundle_path / subdir / filename
    out_path.write_text(json.dumps(data, indent=2, default=str))
    logger.info(f"  Saved: {out_path}")
    return out_path


def load_artifact(bundle_path: Path, subdir: str, filename: str) -> dict:
    """Load a JSON artifact from the episode bundle. Returns empty dict on missing."""
    path = bundle_path / subdir / filename
    if not path.exists():
        logger.warning(f"  Artifact not found: {path}")
        return {}
    try:
        return json.loads(path.read_text())
    except Exception as e:
        logger.error(f"  Failed to load {path}: {e}")
        return {}


def get_episode_log_path(bundle_path: Path) -> Path:
    """Return the log file path for this episode."""
    return bundle_path / "logs" / "run.log"


def list_episodes(limit: int = 14) -> list:
    """List recent episode dates (most recent first)."""
    if not EPISODES_DIR.exists():
        return []
    episodes = sorted(
        [d.name for d in EPISODES_DIR.iterdir() if d.is_dir()],
        reverse=True
    )
    return episodes[:limit]
