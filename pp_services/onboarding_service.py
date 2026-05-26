import os
"""
PROTOCOL PULSE - BITCOIN ONBOARDING RAMP
AI-Driven Conversion Engine with Psychological Profiling
"""
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict, field
from enum import Enum
import secrets

logger = logging.getLogger('OnboardingRamp')

class BuyerType(Enum):
    ANALYTICAL = "analytical"
    DRIVER = "driver"
    EXPRESSIVE = "expressive"
    AMIABLE = "amiable"

class CommitmentLevel(Enum):
    CURIOUS = "curious"
    INTERESTED = "interested"
    READY = "ready"
    COMMITTED = "committed"
    MAXIMALIST = "maximalist"

class WealthTier(Enum):
    STARTER = "starter"
    BUILDER = "builder"
    ESTABLISHED = "established"
    AFFLUENT = "affluent"
    WHALE = "whale"

@dataclass
class UserProfile:
    session_id: str
    buyer_type: Optional[BuyerType] = None
    commitment_level: Optional[CommitmentLevel] = None
    wealth_tier: Optional[WealthTier] = None
    questions_answered: int = 0
    email_captured: bool = False
    intent_score: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

PRODUCT_CATALOG = {
    "swan_bitcoin": {
        "id": "swan_bitcoin",
        "name": "Swan Bitcoin",
        "min_wealth_tier": "starter",
        "affiliate_url": "https://swanbitcoin.com/protocolpulse",
        "messaging": {"amiable": {"headline": "The Safe Way to Own Bitcoin", "cta": "See How It Works"}}
    },
    "unchained": {
        "id": "unchained",
        "name": "Unchained",
        "min_wealth_tier": "builder",
        "affiliate_url": "https://unchained.com/?ref=protocolpulse",
        "messaging": {"analytical": {"headline": "2-of-3 Multisig Security", "cta": "Understand the Model"}}
    }
}

class OnboardingRampService:
    def __init__(self):
        self.sessions: Dict[str, UserProfile] = {}
    
    def create_session(self) -> str:
        session_id = secrets.token_urlsafe(16)
        self.sessions[session_id] = UserProfile(session_id=session_id)
        return session_id

onboarding_service = OnboardingRampService()


# ════════════════════════════════════════════════════════════
# AIDA ONBOARDING ENGINE — Required by routes.py
# ════════════════════════════════════════════════════════════

AIDA_STAGES = ["attention", "interest", "desire", "action", "close"]

STAGE_PROMPTS = {
    "attention": {
        "prompt": "Where are you in Bitcoin right now? (holdings, goals, constraints)",
        "next": "interest"
    },
    "interest": {
        "prompt": "What matters most to you: growing wealth, protecting it, or passing it to family?",
        "next": "desire"
    },
    "desire": {
        "prompt": "What's your biggest concern about Bitcoin? (volatility, security, complexity, regulation)",
        "next": "action"
    },
    "action": {
        "prompt": "What would make you take the next step today? (more info, a trusted guide, a specific product)",
        "next": "close"
    },
    "close": {
        "prompt": "Based on your answers, here are your personalized recommendations.",
        "next": None
    }
}

PARTNER_RECOMMENDATIONS = {
    "protect": [
        {
            "id": "meanwhile",
            "name": "Meanwhile",
            "category": "Bitcoin Life Insurance",
            "headline": "Protect Your Family with Bitcoin-Denominated Life Insurance",
            "description": "The first whole life insurance policy denominated entirely in Bitcoin. Premiums in BTC, death benefit in BTC. Regulated by Bermuda Monetary Authority. Your policy, your keys, your sovereignty.",
            "cta": "Get a Quote",
            "url": "https://application.meanwhile.bm/start?referralCode=KKM73K",
            "trust_badges": ["Regulated", "Bitcoin-Native", "Whole Life"],
            "priority": 1
        },
        {
            "id": "unchained",
            "name": "Unchained",
            "category": "Multi-sig Custody",
            "headline": "Secure Your Bitcoin with Collaborative Custody",
            "description": "2-of-3 multisig vaults so no single party controls your keys.",
            "cta": "Learn More",
            "url": "https://unchained.com/?ref=protocolpulse",
            "trust_badges": ["Multi-sig", "US-Based"],
            "priority": 2
        }
    ],
    "grow": [
        {
            "id": "swan",
            "name": "Swan Bitcoin",
            "category": "Auto-DCA",
            "headline": "Stack Sats on Autopilot",
            "description": "Automated recurring Bitcoin purchases with instant withdrawal to your own wallet.",
            "cta": "Start Stacking",
            "url": "https://swanbitcoin.com/protocolpulse",
            "trust_badges": ["Auto-DCA", "Self-Custody"],
            "priority": 1
        },
        {
            "id": "river",
            "name": "River",
            "category": "Bitcoin Exchange",
            "headline": "Buy Bitcoin with Zero Trading Fees",
            "description": "Bitcoin-only exchange. No altcoins, no distractions.",
            "cta": "Open Account",
            "url": "https://river.com/?ref=protocolpulse",
            "trust_badges": ["Bitcoin-Only", "Zero Fees"],
            "priority": 2
        }
    ],
    "family": [
        {
            "id": "meanwhile",
            "name": "Meanwhile",
            "category": "Bitcoin Life Insurance",
            "headline": "Leave Your Family a Legacy in Sound Money",
            "description": "Bitcoin-denominated whole life insurance. Pay premiums in BTC, your family receives BTC. Borrow against your policy tax-free.",
            "cta": "Protect Your Legacy",
            "url": "https://application.meanwhile.bm/start?referralCode=KKM73K",
            "trust_badges": ["Regulated", "Tax-Advantaged", "Generational"],
            "priority": 1
        },
        {
            "id": "casa",
            "name": "Casa",
            "category": "Inheritance Planning",
            "headline": "Multi-sig Self-Custody with Inheritance Support",
            "description": "Protect your Bitcoin and ensure your family can access it.",
            "cta": "See Plans",
            "url": "https://keys.casa/?ref=protocolpulse",
            "trust_badges": ["Multi-sig", "Inheritance"],
            "priority": 2
        }
    ],
    "default": [
        {
            "id": "meanwhile",
            "name": "Meanwhile",
            "category": "Bitcoin Life Insurance",
            "headline": "The First Bitcoin-Native Life Insurance",
            "description": "Whole life insurance denominated in Bitcoin. Regulated, sovereign, generational.",
            "cta": "Learn More",
            "url": "https://application.meanwhile.bm/start?referralCode=KKM73K",
            "trust_badges": ["Regulated", "Bitcoin-Native"],
            "priority": 1
        },
        {
            "id": "swan",
            "name": "Swan Bitcoin",
            "category": "Auto-DCA",
            "headline": "Start Your Bitcoin Journey",
            "description": "Automated Bitcoin purchases with instant self-custody withdrawal.",
            "cta": "Get Started",
            "url": "https://swanbitcoin.com/protocolpulse",
            "trust_badges": ["Beginner-Friendly", "Auto-DCA"],
            "priority": 2
        }
    ]
}


@dataclass
class AidaStepResult:
    stage: str
    next_stage: Optional[str]
    prompt: str
    profile: dict
    interest_level: float
    capacity_score: float
    recommendations: list
    next_prompt: Optional[str] = None
    urgency_copy: Optional[str] = None


def _classify_intent(text: str) -> str:
    """Classify user intent from free-text response."""
    text_lower = text.lower()
    protect_words = ["protect", "safe", "secure", "insurance", "risk", "worry", "concern", "lose", "theft", "hack"]
    family_words = ["family", "kids", "children", "inherit", "legacy", "pass down", "generational", "wife", "husband", "estate"]
    grow_words = ["grow", "invest", "buy", "accumulate", "stack", "dca", "more", "profit", "return", "earn"]

    scores = {
        "protect": sum(1 for w in protect_words if w in text_lower),
        "family": sum(1 for w in family_words if w in text_lower),
        "grow": sum(1 for w in grow_words if w in text_lower)
    }
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "default"


def _estimate_wealth_tier(annual_income) -> str:
    if not annual_income:
        return "builder"
    if annual_income >= 1000000:
        return "whale"
    if annual_income >= 500000:
        return "affluent"
    if annual_income >= 150000:
        return "established"
    if annual_income >= 50000:
        return "builder"
    return "starter"


def run_aida_step(stage: str, user_text: str, whale_24h=0, mega_24h=0, annual_income=None) -> AidaStepResult:
    """Run one step of the AIDA onboarding funnel."""
    stage_info = STAGE_PROMPTS.get(stage, STAGE_PROMPTS["attention"])
    next_stage = stage_info["next"]

    intent = _classify_intent(user_text)
    wealth_tier = _estimate_wealth_tier(annual_income)

    # Build interest score (0-1) based on stage progression
    stage_scores = {"attention": 0.2, "interest": 0.4, "desire": 0.6, "action": 0.8, "close": 1.0}
    interest_level = stage_scores.get(stage, 0.2)

    # Capacity score based on wealth
    capacity_map = {"starter": 0.2, "builder": 0.4, "established": 0.6, "affluent": 0.8, "whale": 1.0}
    capacity_score = capacity_map.get(wealth_tier, 0.4)

    # Get recommendations if closing
    recommendations = []
    if stage in ("action", "close"):
        recs = PARTNER_RECOMMENDATIONS.get(intent, PARTNER_RECOMMENDATIONS["default"])
        recommendations = sorted(recs, key=lambda r: r["priority"])

    # Next prompt
    if next_stage:
        next_prompt = STAGE_PROMPTS[next_stage]["prompt"]
    else:
        next_prompt = "Your personalized Bitcoin roadmap is ready."

    profile = {
        "intent": intent,
        "wealth_tier": wealth_tier,
        "stage": stage,
        "response_summary": user_text[:200]
    }

    return AidaStepResult(
        stage=next_stage or "close",
        next_stage=next_stage,
        prompt=next_prompt,
        profile=profile,
        interest_level=interest_level,
        capacity_score=capacity_score,
        recommendations=recommendations,
        next_prompt=next_prompt
    )


def onboarding_progress(stage: str) -> dict:
    """Return progress through the AIDA funnel."""
    idx = AIDA_STAGES.index(stage) if stage in AIDA_STAGES else 0
    return {
        "current_stage": stage,
        "stage_number": idx + 1,
        "total_stages": len(AIDA_STAGES),
        "percent": int(((idx + 1) / len(AIDA_STAGES)) * 100),
        "complete": stage == "close"
    }


def upsert_lead(user_id=None, email=None, name=None, stage=None,
                profile=None, interest_level=None, capacity_score=None,
                newsletter_opt_in=False, notes=None) -> dict:
    """Track onboarding lead. Returns lead data dict."""
    lead = {
        "user_id": user_id,
        "email": email,
        "name": name,
        "stage": stage,
        "profile": profile or {},
        "interest_level": interest_level,
        "capacity_score": capacity_score,
        "newsletter_opt_in": newsletter_opt_in,
        "notes": notes,
        "updated_at": datetime.utcnow().isoformat()
    }

    # Persist to file
    os.makedirs("data", exist_ok=True)
    leads_file = "data/onboarding_leads.json"
    leads = []
    if os.path.exists(leads_file):
        try:
            leads = json.loads(open(leads_file).read())
        except:
            leads = []
    leads.append(lead)
    open(leads_file, "w").write(json.dumps(leads, indent=2, default=str))

    return lead
