"""
Central feature-flag helpers for safety-first deployments.

Risky automations and external posting are OFF by default unless explicitly enabled.
"""

from __future__ import annotations

import os
from typing import Dict


DEFAULT_FLAGS: Dict[str, bool] = {
    # External posting
    "ENABLE_X_POSTING": False,
    "ENABLE_NOSTR_POSTING": True,
    "ENABLE_TELEGRAM_ALERTS": False,
    # Automation families
    "ENABLE_AUTOMATION_ARTICLES": False,
    "ENABLE_SOCIAL_LISTENER": False,
    "ENABLE_SUPERVISOR_AUTOPUBLISH": False,
    "ENABLE_WHALE_HEARTBEAT": True,
    "ENABLE_DISTRIBUTION_ENGINE": False,
    "ENABLE_MATTY_ICE_ENGAGEMENT": False,
    # Reply engine auto-post (off by default — review drafts first)
    "ENABLE_AUTO_REPLY": False,
}


def env_flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name, None)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def is_enabled(name: str) -> bool:
    return env_flag(name, DEFAULT_FLAGS.get(name, False))

