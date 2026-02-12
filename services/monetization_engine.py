from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from app import db
import models

logger = logging.getLogger(__name__)

TOPIC_MAP = {
    "custody": ["hardware-wallet", "self-custody", "custody"],
    "mortgage": ["mortgage", "lending", "borrow", "finance"],
    "insurance": ["insurance"],
    "payments": ["payments", "merchant", "lightning"],
}

URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)


class MonetizationEngine:
    def __init__(self) -> None:
        self.project_root = Path(__file__).resolve().parents[1]
        self.affiliates_path = self.project_root / "config" / "affiliates.json"
        self.metrics_path = self.project_root / "logs" / "monetization_engine.report.json"

    def _catalog(self) -> List[Dict]:
        try:
            payload = json.loads(self.affiliates_path.read_text(encoding="utf-8"))
            return payload.get("catalog") or []
        except Exception as e:
            logger.warning("monetization_engine: affiliates catalog load failed: %s", e)
            return []

    def _detect_topic(self, text: str) -> Optional[str]:
        t = (text or "").lower()
        if any(k in t for k in ("multisig", "self-custody", "private key", "hardware wallet", "cold storage", "custody")):
            return "custody"
        if any(k in t for k in ("mortgage", "home loan", "real estate lending", "borrow against btc")):
            return "mortgage"
        if "insurance" in t:
            return "insurance"
        if any(k in t for k in ("merchant", "checkout", "payments", "lightning")):
            return "payments"
        return None

    def _pick_affiliate(self, topic: str) -> Optional[Dict]:
        cats = set(TOPIC_MAP.get(topic, []))
        if not cats:
            return None
        candidates = [c for c in self._catalog() if (c.get("category") or "").lower() in cats]
        return candidates[0] if candidates else None

    def _inject(self, text: str, affiliate: Dict) -> str:
        if not text:
            return text
        if URL_RE.search(text):
            return text
        name = affiliate.get("name") or affiliate.get("slug") or "partner"
        url = affiliate.get("url") or ""
        if not url:
            return text
        return f"{text}\n\noperator link: [{name}]({url})"

    def _scan_daily_briefs(self) -> Dict[str, int]:
        scanned = injected = 0
        rows = models.DailyBrief.query.order_by(models.DailyBrief.created_at.desc()).limit(80).all()
        for row in rows:
            scanned += 1
            original = row.body or ""
            topic = self._detect_topic((row.headline or "") + " " + original)
            if not topic:
                continue
            aff = self._pick_affiliate(topic)
            if not aff:
                continue
            updated = self._inject(original, aff)
            if updated != original:
                row.body = updated
                injected += 1
        if injected:
            db.session.commit()
        return {"scanned": scanned, "injected": injected}

    def _scan_x_drafts(self) -> Dict[str, int]:
        scanned = injected = 0
        rows = models.XReplyDraft.query.order_by(models.XReplyDraft.created_at.desc()).limit(120).all()
        for row in rows:
            scanned += 1
            original = row.draft_text or ""
            topic = self._detect_topic(original)
            if not topic:
                continue
            aff = self._pick_affiliate(topic)
            if not aff:
                continue
            updated = self._inject(original, aff)
            if updated != original:
                row.draft_text = updated[:300]
                injected += 1
        if injected:
            db.session.commit()
        return {"scanned": scanned, "injected": injected}

    def metrics_snapshot(self) -> Dict:
        # Injection rate based on latest scan report; click rate from partner clicks over 7d.
        report = {}
        if self.metrics_path.exists():
            try:
                report = json.loads(self.metrics_path.read_text(encoding="utf-8"))
            except Exception:
                report = {}
        injected = int((report.get("totals") or {}).get("injected", 0))
        scanned = int((report.get("totals") or {}).get("scanned", 0))
        injection_rate = round((injected / scanned) * 100, 2) if scanned else 0.0

        since = datetime.utcnow() - timedelta(days=7)
        clicks = models.PartnerClick.query.filter(models.PartnerClick.created_at >= since).count()
        click_rate = round((clicks / injected) * 100, 2) if injected else 0.0
        return {
            "scanned": scanned,
            "injected": injected,
            "injection_rate_pct": injection_rate,
            "clicks_7d": clicks,
            "click_rate_vs_injected_pct": click_rate,
        }

    def run(self) -> Dict:
        brief_stats = self._scan_daily_briefs()
        draft_stats = self._scan_x_drafts()
        totals = {
            "scanned": int(brief_stats["scanned"] + draft_stats["scanned"]),
            "injected": int(brief_stats["injected"] + draft_stats["injected"]),
        }
        report = {
            "finished_at": datetime.utcnow().isoformat(),
            "briefs": brief_stats,
            "x_drafts": draft_stats,
            "totals": totals,
            "metrics": self.metrics_snapshot(),
        }
        try:
            self.metrics_path.parent.mkdir(parents=True, exist_ok=True)
            self.metrics_path.write_text(json.dumps(report, ensure_ascii=True, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning("monetization_engine report write failed: %s", e)
        return report


monetization_engine = MonetizationEngine()

