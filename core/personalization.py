from __future__ import annotations

import json
from typing import Dict, Iterable, List

import models


def build_user_profile(user) -> Dict:
    lead = None
    if user:
        lead = models.Lead.query.filter_by(user_id=user.id).order_by(models.Lead.updated_at.desc()).first()
    profile = {
        "risk_appetite": "medium",
        "stack_rate": "steady",
        "custody_posture": "hybrid",
        "region": "global",
        "content_preferences": ["whale", "risk", "sentry"],
        "reaction_history": {"clicks": 0, "zaps": 0},
    }
    if lead:
        if (lead.capacity_score or 0) >= 70:
            profile["risk_appetite"] = "high"
        if (lead.capacity_score or 0) <= 30:
            profile["risk_appetite"] = "low"
        profile["stack_rate"] = "aggressive" if (lead.capacity_score or 0) > 60 else "steady"
        bp = str(getattr(lead, "btc_profile", "") or "").lower()
        if bp == "autism-maxxer":
            profile["content_preferences"] = ["whale", "risk", "medley"]
            profile["custody_posture"] = "sovereign"
        elif bp == "off-zero":
            profile["content_preferences"] = ["system", "sentry", "risk"]
            profile["custody_posture"] = "learning"
    return profile


def rank_feed_for_user(events: Iterable[Dict], profile: Dict) -> List[Dict]:
    prefs = set(profile.get("content_preferences") or [])
    risk = profile.get("risk_appetite", "medium")
    out = []
    for e in events:
        lane = str(e.get("lane") or "")
        sev = str(e.get("severity") or "info")
        base = 1.0
        if lane in prefs:
            base += 1.0
        if sev == "crit":
            base += 1.2
        elif sev == "warn":
            base += 0.6
        if risk == "high" and lane in {"whale", "risk"}:
            base += 0.5
        if risk == "low" and lane == "risk":
            base += 0.2
        row = dict(e)
        row["rank_score"] = round(base, 3)
        out.append(row)
    out.sort(key=lambda x: (x.get("rank_score", 0), x.get("ts", "")), reverse=True)
    return out


def recommend_next_action(profile: Dict) -> str:
    risk = profile.get("risk_appetite")
    if risk == "high":
        return "review whale alerts and queue one sentry reply with highest signal density."
    if risk == "low":
        return "complete onboarding action step and harden custody lane."
    return "scan command dashboard and execute top risk escalation."


def save_user_profile(user_id: int, profile: Dict, behavior: Dict | None = None) -> None:
    row = models.UserProfile.query.filter_by(user_id=user_id).first()
    if row is None:
        row = models.UserProfile(user_id=user_id)
        models.db.session.add(row)
    row.profile_json = json.dumps(profile, ensure_ascii=True)
    row.behavior_json = json.dumps(behavior or {}, ensure_ascii=True)
    models.db.session.commit()

