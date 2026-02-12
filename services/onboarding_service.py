from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List

from app import db
import models
from services import ollama_runtime


FUNNEL_STEPS = ["attention", "interest", "desire", "action", "activation"]
PROFILE_CLASSES = {"off-zero", "sovereign-builder", "autism-maxxer"}


@dataclass
class OnboardingResult:
    stage: str
    profile: str
    interest_level: str
    capacity_score: float
    next_prompt: str
    urgency_copy: str


def _safe_stage(stage: str) -> str:
    stage = (stage or "").strip().lower()
    return stage if stage in FUNNEL_STEPS else FUNNEL_STEPS[0]


def _safe_profile(profile: str) -> str:
    profile = (profile or "").strip().lower()
    return profile if profile in PROFILE_CLASSES else "off-zero"


def classify_profile(raw_text: str) -> str:
    text = (raw_text or "").strip()
    if not text:
        return "off-zero"
    prompt = (
        "classify this user into one label only: off-zero, sovereign-builder, autism-maxxer.\n"
        "return only label, lowercase, no punctuation.\n\n"
        f"user_text:\n{text[:1400]}"
    )
    out = ollama_runtime.generate(
        prompt,
        preferred_model="llama3.2:3b",
        options={"temperature": 0.1, "num_predict": 10},
        timeout=20,
    ).strip().lower()
    if out in PROFILE_CLASSES:
        return out
    heur = text.lower()
    if any(k in heur for k in ("multisig", "utxo", "node", "liquidity routing", "taproot")):
        return "autism-maxxer"
    if any(k in heur for k in ("business", "family office", "capital", "treasury", "allocation")):
        return "sovereign-builder"
    return "off-zero"


def compute_capacity_score(raw_text: str, annual_income: float | None = None) -> float:
    text = (raw_text or "").lower()
    score = 20.0
    if annual_income:
        score += min(max(float(annual_income), 0.0) / 5000.0, 35.0)
    if any(k in text for k in ("long term", "discipline", "dca", "conviction")):
        score += 20.0
    if any(k in text for k in ("leverage", "ape", "all in tomorrow")):
        score -= 10.0
    return round(max(0.0, min(100.0, score)), 2)


def suggest_interest_level(raw_text: str) -> str:
    text = (raw_text or "").lower()
    if any(k in text for k in ("just learning", "new", "beginner")):
        return "early"
    if any(k in text for k in ("self-custody", "hardware wallet", "multisig")):
        return "advanced"
    return "intermediate"


def next_prompt_for_stage(stage: str, profile: str) -> str:
    stage = _safe_stage(stage)
    if stage == "attention":
        return "what is your primary bitcoin goal over the next 12 months?"
    if stage == "interest":
        return "what resources can you deploy monthly without stress?"
    if stage == "desire":
        if profile == "autism-maxxer":
            return "which sovereignty stack matters most right now: node, multisig, or mining?"
        return "what would make you feel fully sovereign in your setup?"
    if stage == "action":
        return "choose your first move now: dca plan, custody upgrade, or services sprint."
    return "want a custom 30-day sovereignty sprint based on your profile?"


def build_urgency_copy(whale_24h: int, mega_24h: int) -> str:
    return f"live signal: {whale_24h} whale flows in 24h, {mega_24h} mega prints. windows close fast."


def run_aida_step(
    stage: str,
    user_text: str,
    whale_24h: int,
    mega_24h: int,
    annual_income: float | None = None,
) -> OnboardingResult:
    profile = classify_profile(user_text)
    capacity = compute_capacity_score(user_text, annual_income=annual_income)
    interest = suggest_interest_level(user_text)
    next_stage_idx = min(FUNNEL_STEPS.index(_safe_stage(stage)) + 1, len(FUNNEL_STEPS) - 1)
    next_stage = FUNNEL_STEPS[next_stage_idx]
    return OnboardingResult(
        stage=next_stage,
        profile=profile,
        interest_level=interest,
        capacity_score=capacity,
        next_prompt=next_prompt_for_stage(next_stage, profile),
        urgency_copy=build_urgency_copy(whale_24h, mega_24h),
    )


def upsert_lead(
    *,
    user_id: int | None,
    email: str | None,
    name: str | None,
    stage: str,
    profile: str,
    interest_level: str,
    capacity_score: float,
    newsletter_opt_in: bool,
    notes: str,
) -> models.Lead:
    row = None
    if user_id:
        row = models.Lead.query.filter_by(user_id=user_id).order_by(models.Lead.id.desc()).first()
    if row is None and email:
        row = models.Lead.query.filter_by(email=email).order_by(models.Lead.id.desc()).first()
    if row is None:
        row = models.Lead(
            user_id=user_id,
            email=(email or None),
            name=(name or None),
            source="onboarding",
            created_at=datetime.utcnow(),
        )
        db.session.add(row)

    row.interest_level = (interest_level or "unknown")[:40]
    row.capacity_score = float(capacity_score or 0.0)
    row.btc_profile = _safe_profile(profile)
    row.newsletter_opt_in = bool(newsletter_opt_in)
    row.funnel_stage = _safe_stage(stage)
    row.notes = (notes or "")[:4000]
    row.updated_at = datetime.utcnow()
    db.session.commit()
    return row


def onboarding_progress(stage: str) -> Dict[str, int | str | List[Dict[str, str | bool]]]:
    stage = _safe_stage(stage)
    idx = FUNNEL_STEPS.index(stage)
    labels = {
        "attention": "attention",
        "interest": "interest",
        "desire": "desire",
        "action": "action",
        "activation": "activation",
    }
    return {
        "stage": stage,
        "percent": int(round(((idx + 1) / len(FUNNEL_STEPS)) * 100)),
        "steps": [{"key": s, "label": labels[s], "active": i <= idx} for i, s in enumerate(FUNNEL_STEPS)],
    }
