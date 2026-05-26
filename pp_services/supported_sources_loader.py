"""
Load designated partner and source config from core/config/supported_sources.json.
Single source of truth for: partner YouTube channels, RSS, X accounts, Nostr allowlist.
Used by: content_generator, youtube_service, avatar pipeline, partner amplification.
"""
import json
import logging
import os

_CONFIG_PATH = None

def _config_path():
    global _CONFIG_PATH
    if _CONFIG_PATH is None:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        _CONFIG_PATH = os.path.join(base, "config", "supported_sources.json")
    return _CONFIG_PATH


def load_supported_sources():
    """Load full supported_sources.json. Returns dict with youtube_channels, rss_sources, x_accounts, nostr_allowlist."""
    path = _config_path()
    if not os.path.isfile(path):
        logging.warning("supported_sources.json not found at %s", path)
        return {"youtube_channels": [], "rss_sources": [], "x_accounts": [], "nostr_allowlist": []}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {
            "youtube_channels": data.get("youtube_channels", []),
            "rss_sources": data.get("rss_sources", []),
            "x_accounts": data.get("x_accounts", []),
            "nostr_allowlist": data.get("nostr_allowlist", []),
        }
    except Exception as e:
        logging.error("Failed to load supported_sources.json: %s", e)
        return {"youtube_channels": [], "rss_sources": [], "x_accounts": [], "nostr_allowlist": []}


def get_partner_youtube_channels(featured_only=False):
    """
    Return list of partner YouTube channel dicts: name, channel_id, tier, featured.
    Used to prioritize partner content in content generation and avatar pipeline.
    """
    data = load_supported_sources()
    channels = data.get("youtube_channels", [])
    if featured_only:
        channels = [c for c in channels if c.get("featured")]
    return channels


def get_partner_youtube_channel_ids(featured_only=False):
    """Return list of channel_id strings for partner channels."""
    return [c["channel_id"] for c in get_partner_youtube_channels(featured_only=featured_only)]
