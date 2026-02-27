"""
Matty Ice Engagement Agent (V5 Overhaul).

Monitors high-value Bitcoin/sovereignty accounts and drafts/posts concise
replies using the unified Protocol Pulse V5 prompt.

V5 additions: NO_REPLY filter, banned phrase detection, 20-min spacing,
18/day cap, no same-author-twice-per-day.
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
MAX_REPLIES_PER_DAY = 18
MIN_REPLY_SPACING_MINUTES = 20

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

BANNED_PHRASES = [
    "bitcoin fixes this", "stay humble, stack sats", "stay humble stack sats",
    "have fun staying poor", "few understand", "this is the way", "bullish",
    "not your keys, not your coins", "not your keys not your coins",
    "tick tock next block", "number go up", "in it for the tech", "ser",
]

V5_REPLY_PROMPT = """You are the social media voice of Protocol Pulse (@ProtocolPulseHQ), a Bitcoin
intelligence platform. You are writing a reply to a tweet.

YOUR PERSONALITY:
- Sharp, witty, observant. The smartest person in the room who doesn't need
  to prove it.
- You have genuine opinions and aren't afraid to push back respectfully.
- You sound like a real person, not a brand. Lowercase, casual, direct.
- You deeply understand Bitcoin, macro economics, and internet culture.
- You're allergic to cliches and generic Bitcoin platitudes.

REPLY RULES:
1. Read the tweet carefully. Identify the SPECIFIC point being made.
2. Your reply must engage with THAT specific point, not Bitcoin in general.
3. Add something new: a sharper angle, missing context, a challenge, or humor.
4. Keep it under 180 characters. Ideally under 100. One thought. One punch.
5. Sound human. Use lowercase. Use contractions. No hashtags. No emojis (rare exception: 1 max).
6. Bitcoin connection only if genuinely relevant and specific. NOT every reply
   needs to mention Bitcoin. A sharp cultural observation is better than a
   forced Bitcoin pivot.
7. NEVER use these phrases: "Bitcoin fixes this", "few understand", "stay humble
   stack sats", "not your keys not your coins", "tick tock next block",
   "have fun staying poor", "this is the way", "bullish" (as standalone),
   or anything that could be a bumper sticker.
8. Match the energy: serious tweet -> thoughtful. funny -> witty. angry -> edgy.
9. Before outputting, ask: would the original poster want to reply to THIS?
   If no, output "NO_REPLY" instead.
10. If you can't add genuine value, output "NO_REPLY". Silence > noise.

OUTPUT FORMAT:
Return ONLY the reply text. No quotes. No explanation. No "here's a reply:" prefix.
If the tweet doesn't warrant a reply, return only: NO_REPLY"""


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _contains_banned_phrase(text: str) -> bool:
    lower = (text or "").lower().strip()
    return any(phrase in lower for phrase in BANNED_PHRASES)


def _is_no_reply(text: str) -> bool:
    stripped = (text or "").strip().upper()
    return stripped in ("NO_REPLY", "NO REPLY")


class MattyIceEngagementAgent:
    def __init__(self) -> None:
        self.x = XService()

    def _load_state(self) -> Dict[str, Any]:
        state = _load_json(STATE_PATH)
        return {
            "reply_timestamps": state.get("reply_timestamps", []),
            "replied_post_ids": state.get("replied_post_ids", []),
            "replied_authors_today": state.get("replied_authors_today", []),
            "replied_authors_date": state.get("replied_authors_date", ""),
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
        if targets:
            return targets[:30]
        return SOVEREIGN_30_DEFAULT[:30]

    def _daily_count(self, state: Dict[str, Any]) -> int:
        """Count replies sent today (UTC)."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        count = 0
        for ts in state.get("reply_timestamps", []):
            try:
                if ts[:10] == today:
                    count += 1
            except Exception:
                continue
        return count

    def _minutes_since_last_reply(self, state: Dict[str, Any]) -> float:
        """Minutes since the most recent reply."""
        stamps = state.get("reply_timestamps", [])
        if not stamps:
            return 999.0
        try:
            last = datetime.fromisoformat(stamps[-1])
            return (datetime.utcnow() - last).total_seconds() / 60
        except Exception:
            return 999.0

    def _authors_replied_today(self, state: Dict[str, Any]) -> set:
        """Return set of authors we've already replied to today."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        if state.get("replied_authors_date") != today:
            state["replied_authors_today"] = []
            state["replied_authors_date"] = today
            return set()
        return set(state.get("replied_authors_today", []))

    def _within_rate_limit(self, state: Dict[str, Any]) -> bool:
        # V5: check daily cap
        if self._daily_count(state) >= MAX_REPLIES_PER_DAY:
            logger.info("[matty-ice] daily cap reached (%d/%d)", self._daily_count(state), MAX_REPLIES_PER_DAY)
            return False
        # V5: check 20-min spacing
        elapsed = self._minutes_since_last_reply(state)
        if elapsed < MIN_REPLY_SPACING_MINUTES:
            logger.info("[matty-ice] spacing enforced (%.1f min < %d min)", elapsed, MIN_REPLY_SPACING_MINUTES)
            return False
        return True

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
        return " | ".join(snippets) if snippets else ""

    def _generate_reply(self, original_text: str, author_handle: str, append_bridge: bool) -> str | None:
        """Generate a reply using V5 prompt. Returns None if NO_REPLY or banned."""
        alpha = self._latest_alpha_context()
        alpha_line = f"\nAdditional context: {alpha}" if alpha else ""

        user_prompt = (
            f'Tweet by @{author_handle}:\n'
            f'"{original_text[:500]}"{alpha_line}\n\n'
            f"Write a reply as @ProtocolPulseHQ."
        )

        full_prompt = f"{V5_REPLY_PROMPT}\n\n{user_prompt}"

        model = (os.environ.get("MATTY_ICE_MODEL") or "llama3.3").strip()
        reply = ollama_generate(
            prompt=full_prompt,
            preferred_model=model,
            options={"temperature": 0.7, "num_predict": 100},
            timeout=60,
        )
        if reply:
            reply = reply.splitlines()[0].strip()

        if not reply:
            return None

        # V5: NO_REPLY filter
        if _is_no_reply(reply):
            logger.info("[matty-ice] NO_REPLY for @%s", author_handle)
            return None

        # Clean up
        reply = reply.lower().strip()
        # Strip wrapping quotes
        if (reply.startswith('"') and reply.endswith('"')) or (
            reply.startswith("'") and reply.endswith("'")
        ):
            reply = reply[1:-1].strip()

        # V5: Banned phrase filter
        if _contains_banned_phrase(reply):
            logger.info("[matty-ice] banned phrase detected, skipping: %s", reply[:80])
            return None

        # V5: Cap at 180 chars
        if len(reply) > 180:
            reply = reply[:177] + "..."

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
                "rate_window_count": self._daily_count(state),
                "skipped": "no_posting_credentials",
            }

        # V5: get authors replied today
        replied_authors = self._authors_replied_today(state)

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

            # V5: no same author twice per day
            author = c.get("handle", "").lower()
            if author in replied_authors:
                logger.info("[matty-ice] already replied to @%s today, skipping", author)
                continue

            next_count = int(state.get("total_replies", 0)) + 1
            append_bridge = (next_count % 5 == 0)
            reply_text = self._generate_reply(
                original_text=c.get("text", ""),
                author_handle=c.get("handle", ""),
                append_bridge=append_bridge,
            )

            # V5: NO_REPLY or banned phrase — skip silently
            if not reply_text:
                logger.info("[matty-ice] skipped @%s — NO_REPLY or banned phrase", c.get("handle"))
                continue

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
                # V5: track author
                replied_authors.add(author)
                state["replied_authors_today"] = list(replied_authors)
                state["replied_authors_date"] = datetime.utcnow().strftime("%Y-%m-%d")

            row = {
                "success": success,
                "platform": c.get("platform"),
                "source_url": c.get("url"),
                "original": c.get("text", "")[:280],
                "reply": reply_text,
                "post_result": post_result,
            }
            results.append(row)
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
            "rate_window_count": self._daily_count(state),
        }


matty_ice_agent = MattyIceEngagementAgent()
