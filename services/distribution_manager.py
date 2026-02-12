"""
Distribution manager for Sentry Auto-Poster.

Capabilities:
- Cross-post to X + Nostr.
- Inject Value Stream tracking links into every post.
- Auto-thread long brief posts into up to 3 parts on X.
- Schedule Daily Intelligence Brief dispatch at 9:00 AM America/New_York.
- Publish whale alerts instantly for >= 1000 BTC moves.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode, urlparse

import requests
import websocket
from bech32 import bech32_decode, convertbits
from coincurve import PrivateKey
from zoneinfo import ZoneInfo

from app import app, db
import models
from services.x_service import XService
from services.feature_flags import is_enabled
from services.ollama_runtime import generate as ollama_generate

logger = logging.getLogger(__name__)

DEFAULT_RELAYS = [
    "wss://relay.damus.io",
    "wss://relay.primal.net",
    "wss://nos.lol",
]
EST = ZoneInfo("America/New_York")
STATE_PATH = Path("/home/ultron/protocol_pulse/logs/distribution_state.json")


class DistributionManager:
    def __init__(self) -> None:
        self.x = XService()

    # ---------------------------
    # State / configuration
    # ---------------------------
    def _load_state(self) -> Dict[str, Any]:
        if not STATE_PATH.exists():
            return {"last_daily_brief_date": None, "posted_whale_txids": []}
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {"last_daily_brief_date": None, "posted_whale_txids": []}

    def _save_state(self, state: Dict[str, Any]) -> None:
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATE_PATH.write_text(json.dumps(state, ensure_ascii=True, indent=2), encoding="utf-8")

    def _tracking_link(self, source: str) -> str:
        base = (os.environ.get("VALUE_STREAM_TRACKING_URL") or "https://protocolpulse.ai/value-stream").strip()
        parsed = urlparse(base)
        if not parsed.scheme:
            base = "https://" + base
        query = urlencode(
            {
                "utm_source": source,
                "utm_medium": "autopost",
                "utm_campaign": "sentry_distribution",
            }
        )
        sep = "&" if "?" in base else "?"
        return f"{base}{sep}{query}"

    # ---------------------------
    # Persona hook generation
    # ---------------------------
    def generate_hook(self, context: str, intent: str = "brief") -> str:
        """
        Generate a short, lowercase hook via local Ollama where possible.
        Falls back to deterministic hook templates.
        """
        model = (os.environ.get("SENTRY_HOOK_MODEL") or os.environ.get("OLLAMA_MODEL") or "llama3.3").strip()
        prompt = (
            "write one hook line in raw matty ice voice. rules: lowercase, edgy, dry, no emojis, "
            "no hashtags, max 12 words, must feel urgent but precise.\n"
            f"intent: {intent}\n"
            f"context: {context[:500]}"
        )
        response = ollama_generate(
            prompt=prompt,
            preferred_model=model,
            options={"temperature": 0.6, "num_predict": 35},
            timeout=60,
        )
        if response:
            return response.splitlines()[0].strip().lower()[:120]

        # Deterministic fallback
        bank = [
            "signal just hit. most people are still asleep.",
            "quiet market. loud implications.",
            "this print changes the board.",
            "if you blinked, you missed the setup.",
        ]
        return random.choice(bank)

    # ---------------------------
    # X posting (single + thread)
    # ---------------------------
    def _split_for_thread(self, text: str, max_parts: int = 3, limit: int = 280) -> List[str]:
        body = (text or "").strip()
        if len(body) <= limit:
            return [body]
        words = body.split()
        parts: List[str] = []
        current: List[str] = []
        for word in words:
            trial = " ".join(current + [word]).strip()
            if len(trial) <= (limit - 8):  # reserve for "n/3 "
                current.append(word)
                continue
            if current:
                parts.append(" ".join(current).strip())
            current = [word]
            if len(parts) >= max_parts:
                break
        if current and len(parts) < max_parts:
            parts.append(" ".join(current).strip())
        if len(parts) > max_parts:
            parts = parts[:max_parts]
        if len(parts) == 1 and len(parts[0]) > limit:
            parts[0] = parts[0][: (limit - 3)] + "..."
        # force max 3 parts; if overflow, trim final part
        if len(parts) == max_parts and len(" ".join(words)) > sum(len(p) for p in parts):
            parts[-1] = (parts[-1][: (limit - 20)] + " ...").strip()
        if len(parts) > 1:
            labeled = []
            total = len(parts)
            for i, p in enumerate(parts, start=1):
                prefix = f"{i}/{total} "
                room = limit - len(prefix)
                labeled.append(prefix + p[:room])
            return labeled
        return parts

    def _x_post(self, text: str) -> Dict[str, Any]:
        text = (text or "").strip()
        if not text:
            return {"success": False, "error": "empty text"}
        if not is_enabled("ENABLE_X_POSTING"):
            return {"success": False, "error": "x_posting_disabled"}
        if not self.x.client and not self.x.client_v2:
            return {"success": False, "error": "x_not_configured"}

        parts = self._split_for_thread(text=text, max_parts=3, limit=280)
        ids: List[str] = []
        parent_id: Optional[str] = None
        try:
            for idx, part in enumerate(parts):
                if self.x.client_v2:
                    if idx == 0:
                        r = self.x.client_v2.create_tweet(text=part)
                    else:
                        r = self.x.client_v2.create_tweet(text=part, in_reply_to_tweet_id=parent_id)
                    tweet_id = str(r.data["id"] if isinstance(r.data, dict) else getattr(r.data, "id", ""))
                elif self.x.client:
                    if idx == 0:
                        r = self.x.client.update_status(part)
                    else:
                        r = self.x.client.update_status(status=part, in_reply_to_status_id=parent_id)
                    tweet_id = str(getattr(r, "id", ""))
                else:
                    return {"success": False, "error": "x_not_configured"}

                if not tweet_id:
                    return {"success": False, "error": "tweet_id_missing", "tweet_ids": ids}
                ids.append(tweet_id)
                parent_id = tweet_id
            return {"success": True, "tweet_ids": ids, "threaded": len(ids) > 1}
        except Exception as e:
            logger.exception("x_post failed")
            return {"success": False, "error": str(e), "tweet_ids": ids}

    # ---------------------------
    # Nostr publish
    # ---------------------------
    def _decode_nostr_private_key(self, raw_key: str) -> bytes:
        raw_key = (raw_key or "").strip()
        if not raw_key:
            raise ValueError("NOSTR_PRIVATE_KEY missing")
        if raw_key.startswith("nsec1"):
            hrp, data = bech32_decode(raw_key)
            if hrp != "nsec" or not data:
                raise ValueError("Invalid nsec key")
            decoded = convertbits(data, 5, 8, False)
            if not decoded:
                raise ValueError("Failed nsec convertbits")
            return bytes(decoded)
        # assume hex
        return bytes.fromhex(raw_key.lower().replace("0x", ""))

    def _nostr_relays(self) -> List[str]:
        raw = (os.environ.get("NOSTR_RELAYS") or "").strip()
        if not raw:
            return DEFAULT_RELAYS
        relays = [r.strip() for r in raw.split(",") if r.strip()]
        return relays or DEFAULT_RELAYS

    def _build_nostr_event(self, content: str) -> Dict[str, Any]:
        key = self._decode_nostr_private_key(os.environ.get("NOSTR_PRIVATE_KEY", ""))
        pk = PrivateKey(key)
        pubkey = pk.public_key.format(compressed=False)[1:].hex()
        created_at = int(time.time())
        event = {
            "pubkey": pubkey,
            "created_at": created_at,
            "kind": 1,
            "tags": [],
            "content": content.strip(),
        }
        serialized = json.dumps(
            [0, event["pubkey"], event["created_at"], event["kind"], event["tags"], event["content"]],
            separators=(",", ":"),
            ensure_ascii=False,
        )
        event_id = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        sig = pk.sign_schnorr(bytes.fromhex(event_id), aux_randomness=os.urandom(32)).hex()
        event["id"] = event_id
        event["sig"] = sig
        return event

    def _nostr_publish(self, content: str) -> Dict[str, Any]:
        if not is_enabled("ENABLE_NOSTR_POSTING"):
            return {"success": False, "error": "nostr_posting_disabled", "relays_success": [], "relays_failed": []}
        try:
            event = self._build_nostr_event(content)
        except Exception as e:
            return {"success": False, "error": str(e), "relays_success": [], "relays_failed": []}

        relays_success: List[str] = []
        relays_failed: List[str] = []
        for relay in self._nostr_relays():
            ws = None
            try:
                ws = websocket.create_connection(relay, timeout=8)
                ws.send(json.dumps(["EVENT", event], separators=(",", ":"), ensure_ascii=False))
                # Read at most one ack frame to reduce blocking.
                ws.settimeout(2)
                try:
                    _ = ws.recv()
                except Exception:
                    pass
                relays_success.append(relay)
            except Exception as e:
                relays_failed.append(f"{relay}::{e}")
            finally:
                try:
                    if ws:
                        ws.close()
                except Exception:
                    pass

        ok = len(relays_success) > 0
        return {
            "success": ok,
            "event_id": event.get("id"),
            "relays_success": relays_success,
            "relays_failed": relays_failed,
        }

    # ---------------------------
    # Message builders
    # ---------------------------
    def _latest_daily_brief_payload(self) -> Optional[Dict[str, Any]]:
        # Prefer published DailyBrief row, then latest SarahBrief article.
        brief = (
            models.DailyBrief.query.filter_by(status="published")
            .order_by(models.DailyBrief.published_at.desc(), models.DailyBrief.created_at.desc())
            .first()
        )
        if brief and (brief.body or brief.headline):
            return {
                "id": brief.id,
                "headline": (brief.headline or "daily intelligence brief").strip(),
                "body": (brief.body or "").strip(),
                "reason": f"Daily Brief #{brief.id}",
            }

        sb = models.SarahBrief.query.order_by(models.SarahBrief.created_at.desc()).first()
        if sb and sb.article:
            return {
                "id": sb.id,
                "headline": (sb.article.title or "daily intelligence brief").strip(),
                "body": (sb.article.summary or sb.article.content or "").strip(),
                "reason": f"Sarah Brief #{sb.id}",
            }
        return None

    def build_daily_brief_post(self) -> Optional[str]:
        payload = self._latest_daily_brief_payload()
        if not payload:
            return None
        body = " ".join((payload.get("body") or "").replace("\n", " ").split())
        excerpt = body[:380].strip()
        if len(body) > 380:
            excerpt += " ..."
        hook = self.generate_hook(context=payload.get("headline", "") + " " + excerpt, intent="daily_brief")
        link = self._tracking_link("daily_brief")
        text = f"{hook}\n\n{payload['headline']}\n{excerpt}\n\n{link}"
        return text.strip()

    def build_whale_alert_post(self, whale: Dict[str, Any]) -> str:
        btc = float(whale.get("btc_amount") or whale.get("btc") or 0)
        txid = str(whale.get("txid") or "")[:12]
        usd = whale.get("usd_value") or whale.get("usd")
        usd_text = f" | ${float(usd):,.0f}" if isinstance(usd, (int, float)) else ""
        hook = self.generate_hook(context=f"{btc:.2f} btc whale move", intent="whale_alert")
        link = self._tracking_link("whale_alert")
        return (
            f"{hook}\n\n"
            f"whale alert: {btc:,.2f} btc moved{usd_text}\n"
            f"tx: {txid}...\n"
            f"{link}"
        ).strip()

    # ---------------------------
    # Public dispatch API
    # ---------------------------
    def dispatch_daily_brief(self) -> Dict[str, Any]:
        text = self.build_daily_brief_post()
        if not text:
            return {"success": False, "error": "no_daily_brief_available"}

        x_result = self._x_post(text)
        nostr_result = self._nostr_publish(text)

        draft = models.AutoPostDraft(
            platform="x+nostr",
            status="posted" if (x_result.get("success") or nostr_result.get("success")) else "failed",
            body=text,
            reason="Daily Intelligence Brief",
            posted_at=datetime.utcnow(),
        )
        db.session.add(draft)
        db.session.commit()
        return {"success": bool(x_result.get("success") or nostr_result.get("success")), "x": x_result, "nostr": nostr_result}

    def dispatch_whale_alerts(self, whale_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        state = self._load_state()
        seen = set(state.get("posted_whale_txids", []))
        results: List[Dict[str, Any]] = []

        for whale in whale_events:
            txid = str(whale.get("txid") or "")
            if not txid or txid in seen:
                continue
            btc = float(whale.get("btc_amount") or whale.get("btc") or 0)
            if btc < 1000:
                continue
            text = self.build_whale_alert_post(whale)
            x_result = self._x_post(text)
            nostr_result = self._nostr_publish(text)
            success = bool(x_result.get("success") or nostr_result.get("success"))
            results.append(
                {
                    "txid": txid,
                    "btc_amount": btc,
                    "success": success,
                    "x": x_result,
                    "nostr": nostr_result,
                }
            )
            if success:
                seen.add(txid)
                draft = models.AutoPostDraft(
                    platform="x+nostr",
                    status="posted",
                    body=text,
                    reason=f"Whale Alert {txid}",
                    posted_at=datetime.utcnow(),
                )
                db.session.add(draft)

        state["posted_whale_txids"] = list(seen)[-500:]
        self._save_state(state)
        db.session.commit()
        return results

    def run_scheduled_dispatch(self, now: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Called from heartbeat loop. Posts daily brief once per date at ~9:00 AM EST.
        """
        now = now or datetime.now(tz=EST)
        state = self._load_state()
        today = now.date().isoformat()
        should_window = (now.hour == 9 and now.minute <= 5)
        if not should_window:
            return {"success": True, "scheduled": False, "reason": "outside_window"}
        if state.get("last_daily_brief_date") == today:
            return {"success": True, "scheduled": False, "reason": "already_posted_today"}

        result = self.dispatch_daily_brief()
        if result.get("success"):
            state["last_daily_brief_date"] = today
            self._save_state(state)
        return {"success": result.get("success", False), "scheduled": True, "result": result}

    def post_sovereign_greeting(self) -> Dict[str, Any]:
        text = (
            "sovereign greeting from protocol pulse.\n"
            "signal stack is live on x + nostr.\n"
            f"{self._tracking_link('sovereign_greeting')}"
        )
        x_result = self._x_post(text)
        nostr_result = self._nostr_publish(text)
        return {"success": bool(x_result.get("success") or nostr_result.get("success")), "x": x_result, "nostr": nostr_result}


distribution_manager = DistributionManager()

