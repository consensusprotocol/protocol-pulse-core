from __future__ import annotations

import json
import logging
import os
from typing import Dict, List

from app import db
import models

logger = logging.getLogger(__name__)

try:
    from pywebpush import webpush, WebPushException
except Exception:  # pragma: no cover
    webpush = None
    WebPushException = Exception


class WebPushService:
    def _vapid_claims(self) -> Dict:
        return {"sub": os.environ.get("WEB_PUSH_SUBJECT", "mailto:ops@protocolpulse.io")}

    def _vapid_private_key(self) -> str:
        return (os.environ.get("WEB_PUSH_VAPID_PRIVATE_KEY") or "").strip()

    def save_subscription(self, user_id: int, subscription: Dict, tier: str) -> Dict:
        endpoint = str(subscription.get("endpoint") or "").strip()
        keys = subscription.get("keys") or {}
        if not endpoint:
            return {"ok": False, "error": "missing endpoint"}
        row = models.PushSubscription.query.filter_by(endpoint=endpoint).first()
        if row is None:
            row = models.PushSubscription(
                user_id=user_id,
                endpoint=endpoint,
            )
            db.session.add(row)
        row.user_id = user_id
        row.p256dh = str(keys.get("p256dh") or "")[:255]
        row.auth = str(keys.get("auth") or "")[:255]
        row.tier = (tier or "free")[:30]
        row.is_active = True
        db.session.commit()
        return {"ok": True, "id": row.id}

    def notify_sovereign_whale(self, btc_amount: float, message: str, txid: str = "") -> Dict:
        rows = (
            models.PushSubscription.query
            .filter(models.PushSubscription.is_active.is_(True))
            .filter(models.PushSubscription.tier == 'sovereign')
            .all()
        )
        payload = {
            "title": "Whale Move Detected",
            "body": message,
            "url": f"/whale-watcher?txid={txid}" if txid else "/whale-watcher",
            "btc_amount": btc_amount,
        }
        if not rows:
            return {"ok": True, "sent": 0, "skipped": 0, "reason": "no subscribers"}

        private_key = self._vapid_private_key()
        if not webpush or not private_key:
            # Soft-fail in environments without pywebpush or vapid keys.
            logger.info("web_push simulated: subscribers=%s payload=%s", len(rows), payload)
            return {"ok": True, "sent": 0, "skipped": len(rows), "simulated": True}

        sent = 0
        skipped = 0
        for row in rows:
            sub_info = {
                "endpoint": row.endpoint,
                "keys": {"p256dh": row.p256dh or "", "auth": row.auth or ""},
            }
            try:
                webpush(
                    subscription_info=sub_info,
                    data=json.dumps(payload),
                    vapid_private_key=private_key,
                    vapid_claims=self._vapid_claims(),
                    ttl=60,
                )
                sent += 1
            except WebPushException as e:
                skipped += 1
                # Prune dead endpoints to keep retry fanout clean.
                status_code = getattr(getattr(e, "response", None), "status_code", None)
                if status_code in (404, 410):
                    row.is_active = False
                logger.debug("web_push send failed endpoint=%s err=%s", row.endpoint[:48], e)
        db.session.commit()
        return {"ok": True, "sent": sent, "skipped": skipped}


web_push_service = WebPushService()

