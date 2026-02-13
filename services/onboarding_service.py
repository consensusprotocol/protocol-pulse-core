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
