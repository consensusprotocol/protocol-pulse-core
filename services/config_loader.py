"""
CONFIG LOADER
==============
Load and validate partner channels config.
Hot-reload support for runtime updates.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict
from datetime import datetime

logger = logging.getLogger("ConfigLoader")

CONFIG_PATH = Path("config/partner_channels.json")
_config_cache = None
_config_mtime = None


def load_channels_config(force_reload: bool = False) -> Dict:
    """Load channels config with caching and hot-reload support."""
    global _config_cache, _config_mtime

    if not CONFIG_PATH.exists():
        logger.error(f"Config file not found: {CONFIG_PATH}")
        return {"channels": [], "settings": {}}

    current_mtime = CONFIG_PATH.stat().st_mtime

    if not force_reload and _config_cache and _config_mtime == current_mtime:
        return _config_cache

    try:
        config = json.loads(CONFIG_PATH.read_text())
        _config_cache = config
        _config_mtime = current_mtime
        logger.info(f"Loaded config v{config.get('version', 'unknown')} with {len(config.get('channels', []))} channels")
        return config
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return {"channels": [], "settings": {}}


def get_enabled_channels() -> List[Dict]:
    """Get only enabled channels, sorted by priority."""
    config = load_channels_config()
    channels = [c for c in config.get("channels", []) if c.get("enabled", True)]

    priority_order = {"high": 0, "medium": 1, "low": 2}
    channels.sort(key=lambda c: priority_order.get(c.get("priority", "medium"), 1))

    return channels


def get_settings() -> Dict:
    """Get pipeline settings from config."""
    config = load_channels_config()
    return config.get("settings", {
        "max_channels_per_run": 20,
        "top_clips_for_video": 5,
        "min_hook_score": 60,
        "clip_duration_min": 15,
        "clip_duration_max": 25
    })


def add_channel(channel: Dict) -> bool:
    """Add a new channel to config."""
    config = load_channels_config(force_reload=True)

    existing = [c for c in config["channels"] if c["channel_id"] == channel["channel_id"]]
    if existing:
        logger.warning(f"Channel already exists: {channel['name']}")
        return False

    config["channels"].append(channel)
    config["version"] = datetime.now().strftime("%Y-%m-%d")
    CONFIG_PATH.write_text(json.dumps(config, indent=2))

    load_channels_config(force_reload=True)
    logger.info(f"Added channel: {channel['name']}")
    return True


def toggle_channel(channel_id: str, enabled: bool) -> bool:
    """Enable or disable a channel."""
    config = load_channels_config(force_reload=True)

    for channel in config["channels"]:
        if channel["channel_id"] == channel_id:
            channel["enabled"] = enabled
            CONFIG_PATH.write_text(json.dumps(config, indent=2))
            load_channels_config(force_reload=True)
            logger.info(f"Channel {channel['name']} {'enabled' if enabled else 'disabled'}")
            return True

    return False
