from __future__ import annotations

from datetime import datetime
from typing import Dict

from app import db
import models


class GatekeeperService:
    """Commander Tier entitlement sync for Stripe/BTCPay confirmations."""

    def confirm_commander_upgrade(self, user_id: int, provider: str, reference: str | None = None) -> Dict:
        user = models.User.query.get(user_id)
        if not user:
            return {"ok": False, "error": "user_not_found"}

        lead = models.Lead.query.filter_by(user_id=user_id).order_by(models.Lead.updated_at.desc()).first()
        if lead is None:
            lead = models.Lead(user_id=user_id, email=getattr(user, "email", None), name=getattr(user, "username", None))
            db.session.add(lead)

        lead.status = "commander"
        lead.funnel_stage = "action"
        lead.notes = ((lead.notes or "") + f"\n[{datetime.utcnow().isoformat()}] commander unlocked via {provider}:{reference or 'n/a'}").strip()
        user.subscription_tier = "commander"
        user.subscription_expires_at = None
        db.session.commit()
        return {"ok": True, "user_id": user_id, "lead_id": lead.id, "tier": user.subscription_tier}


gatekeeper_service = GatekeeperService()

