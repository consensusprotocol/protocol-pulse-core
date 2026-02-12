"""
Matty Ice Engagement Agent.

Monitors high-value Bitcoin/sovereignty accounts and drafts/posts concise
alpha replies with strict safety + anti-spam guardrails.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from app import db
import models
from services.distribution_manager import distribution_manager
from services.feature_flags import is_enabled
from services.target_monitor import target_monitor
from services.x_service import XService
from services.ollama_runtime import generate as ollama_generate

logger = logging.getLogger(__name__)

STATE_PATH = Path("/home/ultron/protocol_pulse/logs/matty_ice_state.json")
DEFAULT_VALUE_STREAM_LINK = "https://protocolpulse.ai/value-stream"
MAX_REPLIES_PER_HOUR = 10

SOVEREIGN_30_DEFAULT = [
    "saylor", "elonmusk", "jackmallers", "lynaldencontact", "jack", "lopp", "saifedean",
    "adam3us", "jeffbooth", "prestonpysh", "martybent", "pierre_rochard", "natbrunell",
    "documentingbtc", "bitcoinmagazine", "nvk", "woonomic", "coryklippsten", "caitlinlong_",
    "stephanlivera", "petermccormack", "aantonop", "nickszabo4", "snowden", "nic__carter",
    "dergigi", "btcsessions", "simplybitcointv", "thebitcoinconf", "gladstein",
]

BITCOIN_FOCUS_TERMS = (
    "bitcoin", "btc", "sats", "lightning", "hashrate", "mempool", "utxo",
    "sovereign", "sovereignty", "self-custody", "code", "node", "mining",
)
NOISE_FILTER_TERMS = (
    "election", "democrat", "republican", "left wing", "right wing", "israel", "gaza",
    "ukraine", "abortion", "race war", "culture war", "trump", "biden",
)


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


class MattyIceEngagementAgent:
    def __init__(self) -> None:
        self.x = XService()

    def _load_state(self) -> Dict[str, Any]:
        state = _load_json(STATE_PATH)
        return {
            "reply_timestamps": state.get("reply_timestamps", []),
            "replied_post_ids": state.get("replied_post_ids", []),
            "total_replies": int(state.get("total_replies", 0)),
        }

    def _save_state(self, state: Dict[str, Any]) -> None:
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATE_PATH.write_text(json.dumps(state, ensure_ascii=True, indent=2), encoding="utf-8")

    def _load_targets(self) -> List[str]:
        cfg_path = Path("/home/ultron/protocol_pulse/config/social_targets.json")
        cfg = _load_json(cfg_path)
        targets = []
        for row in cfg.get("targets", []):
            handle = str((row or {}).get("handle") or "").strip().lstrip("@").lower()
            if handle:
                targets.append(handle)
        # Keep deterministic top 30 if config has extras.
        if targets:
            return targets[:30]
        return SOVEREIGN_30_DEFAULT[:30]

    def _within_rate_limit(self, state: Dict[str, Any]) -> bool:
        now = datetime.utcnow()
        cutoff = now - timedelta(hours=1)
        stamps = []
        for ts in state.get("reply_timestamps", []):
            try:
                dt = datetime.fromisoformat(ts)
                if dt >= cutoff:
                    stamps.append(ts)
            except Exception:
                continue
        state["reply_timestamps"] = stamps
        return len(stamps) < MAX_REPLIES_PER_HOUR

    def _is_relevant(self, text: str) -> bool:
        low = (text or "").lower()
        return any(term in low for term in BITCOIN_FOCUS_TERMS)

    def _is_noise(self, text: str) -> bool:
        low = (text or "").lower()
        return any(term in low for term in NOISE_FILTER_TERMS)

    def _latest_alpha_context(self) -> str:
        snippets = []
        try:
            whale = (
                models.WhaleTransaction.query
                .filter(models.WhaleTransaction.detected_at >= datetime.utcnow() - timedelta(hours=24))
                .order_by(models.WhaleTransaction.detected_at.desc())
                .first()
            )
            if whale:
                snippets.append(f"latest whale print: {whale.btc_amount:.2f} btc")
        except Exception:
            pass
        try:
            snap = models.SentimentSnapshot.query.order_by(models.SentimentSnapshot.created_at.desc()).first()
            if snap:
                snippets.append(f"sentiment index: {float(snap.score):.1f} ({(snap.state or 'equilibrium').lower()})")
        except Exception:
            pass
        return " | ".join(snippets) if snippets else "no extra telemetry context available"

    def _generate_reply(self, original_text: str, author_handle: str, append_bridge: bool) -> str:
        alpha = self._latest_alpha_context()
        prompt = (
            "you are matty ice. write one reply.\n"
            "voice: dry, based, lowercase, concise, pro sovereignty, pro code, anti inflation.\n"
            "no emojis, no hashtags, no politics.\n"
            "must add one useful alpha point tied to telemetry context.\n"
            "max 240 chars.\n"
            f"author: @{author_handle}\n"
            f"original: {original_text[:500]}\n"
            f"telemetry: {alpha}\n"
        )
        model = (os.environ.get("MATTY_ICE_MODEL") or "llama3.3").strip()
        reply = ollama_generate(
            prompt=prompt,
            preferred_model=model,
            options={"temperature": 0.45, "num_predict": 90},
            timeout=60,
        )
        if reply:
            reply = reply.splitlines()[0].strip()

        if not reply:
            base = "sharp take. whale tape confirms this move has real conviction."
            if "mempool" in (original_text or "").lower():
                base = "mempool says the same thing: real demand, not theater."
            reply = base

        reply = reply.lower().strip()
        if append_bridge:
            bridge = (
                f" signal detected at {DEFAULT_VALUE_STREAM_LINK} "
                "just zapped 2100 sats to this thread on the stream."
            )
            room = max(0, 280 - len(bridge) - 1)
            reply = (reply[:room].rstrip(" .") + ". " + bridge).strip()
        return reply[:280]

    def _collect_candidates(self) -> List[Dict[str, Any]]:
        targets = self._load_targets()
        candidates: List[Dict[str, Any]] = []

        # X targets
        x_posts = target_monitor.get_new_x_posts(hours_back=1, handles=targets)
        for p in x_posts:
            handle = str(p.get("handle") or "").strip().lstrip("@").lower()
            if handle not in targets:
                continue
            candidates.append(
                {
                    "platform": "x",
                    "handle": handle,
                    "post_id": str(p.get("post_id") or ""),
                    "text": str(p.get("text") or ""),
                    "url": f"https://x.com/{handle}/status/{str(p.get('post_id') or '').replace('x_', '')}",
                }
            )

        # Nostr notes (BOL-style technical stream)
        try:
            from services.pulse_nexus_service import fetch_pulse_nostr
            notes = fetch_pulse_nostr(pubkeys=[], limit_total=20)
            for n in notes:
                candidates.append(
                    {
                        "platform": "nostr",
                        "handle": str(n.get("author_handle") or "nostr"),
                        "post_id": str(n.get("external_id") or ""),
                        "text": str(n.get("content") or ""),
                        "url": str(n.get("url") or ""),
                    }
                )
        except Exception as e:
            logger.warning("matty ice nostr candidate fetch failed: %s", e)

        return candidates

    def _post_reply(self, candidate: Dict[str, Any], reply_text: str) -> Dict[str, Any]:
        platform = candidate.get("platform")
        if platform == "x":
            raw_post_id = str(candidate.get("post_id") or "")
            tweet_id = raw_post_id.replace("x_", "")
            if not tweet_id.isdigit():
                return {"success": False, "error": "invalid_tweet_id"}
            reply_id = self.x.post_reply(tweet_id=tweet_id, text=reply_text)
            return {"success": bool(reply_id), "reply_id": reply_id}
        if platform == "nostr":
            # Nostr "reply" as a quote-style note with source link.
            body = f"{reply_text}\n\nref: {candidate.get('url')}"
            return distribution_manager._nostr_publish(body)
        return {"success": False, "error": "unsupported_platform"}

    def run_cycle(self) -> Dict[str, Any]:
        if not is_enabled("ENABLE_MATTY_ICE_ENGAGEMENT"):
            return {"success": True, "replies": [], "skipped": "matty_ice_disabled"}
        state = self._load_state()
        candidates = self._collect_candidates()
        dry_run = os.environ.get("MATTY_ICE_DRY_RUN", "false").lower() == "true"
        has_x = bool(self.x.client or self.x.client_v2)
        has_nostr = bool(os.environ.get("NOSTR_PRIVATE_KEY"))
        if not dry_run and not (has_x or has_nostr):
            return {
                "success": True,
                "candidates_seen": len(candidates),
                "replies": [],
                "dry_run": False,
                "rate_window_count": len(state.get("reply_timestamps", [])),
                "skipped": "no_posting_credentials",
            }

        results = []
        for c in candidates:
            post_key = f"{c.get('platform')}::{c.get('post_id')}"
            if not c.get("post_id") or post_key in state.get("replied_post_ids", []):
                continue
            if not self._is_relevant(c.get("text", "")):
                continue
            if self._is_noise(c.get("text", "")):
                continue
            if not self._within_rate_limit(state):
                break

            next_count = int(state.get("total_replies", 0)) + 1
            append_bridge = (next_count % 5 == 0)
            reply_text = self._generate_reply(
                original_text=c.get("text", ""),
                author_handle=c.get("handle", ""),
                append_bridge=append_bridge,
            )

            if dry_run:
                post_result = {"success": True, "dry_run": True, "reply_id": None}
            else:
                post_result = self._post_reply(candidate=c, reply_text=reply_text)

            success = bool(post_result.get("success"))
            if success:
                state["total_replies"] = next_count
                state.setdefault("reply_timestamps", []).append(datetime.utcnow().isoformat())
                state.setdefault("replied_post_ids", []).append(post_key)
                state["replied_post_ids"] = state["replied_post_ids"][-1000:]

            row = {
                "success": success,
                "platform": c.get("platform"),
                "source_url": c.get("url"),
                "original": c.get("text", "")[:280],
                "reply": reply_text,
                "post_result": post_result,
            }
            results.append(row)
            # Terminal-friendly log line requested by user.
            logger.info(
                "[matty-ice] live reply | platform=%s | source=%s | original=%s | reply=%s",
                c.get("platform"),
                c.get("url"),
                row["original"],
                reply_text,
            )

            # Keep each cycle intentional: 1 high-quality reply at a time.
            if success:
                break

        self._save_state(state)
        return {
            "success": True,
            "candidates_seen": len(candidates),
            "replies": results,
            "dry_run": dry_run,
            "rate_window_count": len(state.get("reply_timestamps", [])),
        }


matty_ice_agent = MattyIceEngagementAgent()

