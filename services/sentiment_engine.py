"""
Network Sentiment Engine - Phase 3
Weighted scoring with 3x multiplier for Verified Sovereign accounts.
Maps scores to 5 named states with state change detection.
"""

import logging
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from collections import Counter

logger = logging.getLogger(__name__)

VERIFIED_SOVEREIGNS = [
    'saylor', 'michael saylor', 'microstrategy',
    'lyn alden', 'lynalden', 
    'natalie brunell', 'nataliebrunell',
    'preston pysh', 'prestonpysh',
    'parker lewis', 'parkerlewis',
    'jeff booth', 'jeffbooth',
    'saifedean', 'saifedean ammous',
    'caitlin long', 'caitlinlong',
    'lawrence lepard', 'lawrencelepard',
    'pomp', 'apompliano', 'anthony pompliano',
    'btc sessions', 'btcsessions',
    'marty bent', 'martybent',
    'american hodl', 'americanhodl',
]

SENTIMENT_STATES = {
    'CRITICAL_CONTENTION': {'min': 0, 'max': 20, 'color': '#dc2626', 'label': 'CRITICAL CONTENTION'},
    'FRAGMENTED_SIGNAL': {'min': 21, 'max': 40, 'color': '#eab308', 'label': 'FRAGMENTED SIGNAL'},
    'EQUILIBRIUM': {'min': 41, 'max': 60, 'color': '#ffffff', 'label': 'EQUILIBRIUM'},
    'CONSENSUS_FORMING': {'min': 61, 'max': 80, 'color': '#f97316', 'label': 'CONSENSUS FORMING'},
    'ABSOLUTE_SINGULARITY': {'min': 81, 'max': 100, 'color': '#f7931a', 'label': 'ABSOLUTE SINGULARITY'},
}

BULLISH_KEYWORDS = {
    'etf_inflow': ['etf inflow', 'etf inflows', 'blackrock', 'ishares', 'spot etf', 'billion inflow'],
    'institutional': ['institutional', 'treasury', 'corporate adoption', 'institutional buy', 'microstrategy'],
    'halving': ['halving', 'halvening', 'supply shock', 'block subsidy'],
    'adoption': ['adoption', 'legal tender', 'nation state', 'sovereign adoption', 'el salvador'],
    'monetary': ['fiscal dominance', 'debasement', 'money printing', 'inflation hedge', 'hard money'],
    'protocol': ['layer 2', 'lightning', 'taproot', 'ordinals', 'runes', 'scaling'],
    'price': ['ath', 'all time high', 'new high', 'breakout', 'bullish', 'moon'],
    'accumulation': ['accumulation', 'hodl', 'stacking', 'dca', 'buy the dip'],
}

BEARISH_KEYWORDS = {
    'regulatory': ['sec lawsuit', 'ban', 'crackdown', 'regulation', 'cbdc threat'],
    'market': ['crash', 'dump', 'bear market', 'capitulation', 'liquidation'],
    'fud': ['scam', 'ponzi', 'bubble', 'dead', 'worthless'],
    'security': ['hack', 'exploit', 'stolen', 'breach', 'vulnerability'],
    'centralization': ['centralization', 'mining pool', '51% attack'],
}


def is_verified_sovereign(author: str) -> bool:
    if not author:
        return False
    author_lower = author.lower()
    return any(vs in author_lower for vs in VERIFIED_SOVEREIGNS)


def extract_keywords(text: str) -> Dict[str, int]:
    if not text:
        return {}
    
    text_lower = text.lower()
    keywords_found = {}
    
    for category, terms in BULLISH_KEYWORDS.items():
        for term in terms:
            if term in text_lower:
                key = f"#{category.upper()}"
                keywords_found[key] = keywords_found.get(key, 0) + 1
    
    for category, terms in BEARISH_KEYWORDS.items():
        for term in terms:
            if term in text_lower:
                key = f"#{category.upper()}_FUD"
                keywords_found[key] = keywords_found.get(key, 0) + 1
    
    return keywords_found


def compute_item_score(text: str, author: str = None, verified: bool = False) -> Tuple[float, Dict[str, int]]:
    if not text:
        return 50.0, {}
    
    text_lower = text.lower()
    bullish_score = 0
    bearish_score = 0
    keywords = {}
    
    for category, terms in BULLISH_KEYWORDS.items():
        for term in terms:
            if term in text_lower:
                weight = 3 if (verified or is_verified_sovereign(author)) else 1
                bullish_score += weight
                key = f"#{category.upper()}"
                keywords[key] = keywords.get(key, 0) + weight
    
    for category, terms in BEARISH_KEYWORDS.items():
        for term in terms:
            if term in text_lower:
                weight = 3 if (verified or is_verified_sovereign(author)) else 1
                bearish_score += weight
                key = f"#{category.upper()}_FUD"
                keywords[key] = keywords.get(key, 0) + weight
    
    if bullish_score + bearish_score == 0:
        return 50.0, {}
    
    raw_score = (bullish_score / (bullish_score + bearish_score)) * 100
    return raw_score, keywords


def get_state_from_score(score: float) -> Dict:
    for state_key, state_info in SENTIMENT_STATES.items():
        if state_info['min'] <= score <= state_info['max']:
            return {
                'key': state_key,
                'label': state_info['label'],
                'color': state_info['color'],
                'score': score
            }
    return {
        'key': 'EQUILIBRIUM',
        'label': 'EQUILIBRIUM',
        'color': '#ffffff',
        'score': 50
    }


def compute_network_sentiment(hours: int = 24) -> Dict:
    try:
        from app import db
        from models import FeedItem, SentimentSnapshot, PulseEvent
        
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        items = FeedItem.query.filter(FeedItem.published_at >= cutoff).all()
        
        if not items:
            return {
                'score': 50,
                'state': get_state_from_score(50),
                'keywords': [],
                'sample_size': 0,
                'verified_count': 0
            }
        
        total_score = 0
        total_weight = 0
        all_keywords = Counter()
        verified_count = 0
        
        for item in items:
            is_verified = item.verified or is_verified_sovereign(item.author)
            weight = 3 if is_verified else 1
            
            if is_verified:
                verified_count += 1
            
            content = f"{item.title or ''} {item.summary or ''}"
            item_score, item_keywords = compute_item_score(content, item.author, is_verified)
            
            total_score += item_score * weight
            total_weight += weight
            
            for kw, count in item_keywords.items():
                all_keywords[kw] += count
        
        final_score = total_score / total_weight if total_weight > 0 else 50
        state = get_state_from_score(final_score)
        
        top_keywords = [{'keyword': kw, 'weight': count} for kw, count in all_keywords.most_common(5)]
        
        last_snapshot = SentimentSnapshot.query.order_by(SentimentSnapshot.computed_at.desc()).first()
        state_changed = False
        previous_state = None
        
        if last_snapshot:
            previous_state = last_snapshot.state
            if previous_state != state['key']:
                state_changed = True
                pulse_event = PulseEvent(
                    event_type='state_change',
                    from_state=previous_state,
                    to_state=state['key'],
                    score=final_score,
                    triggered_at=datetime.utcnow()
                )
                db.session.add(pulse_event)
                logger.info(f"State change detected: {previous_state} -> {state['key']}")
                
                try:
                    from services.rtsa_service import rtsa_service
                    rtsa_service.check_trigger(state['key'], final_score)
                    logger.info(f"RTSA trigger checked for state: {state['key']}")
                except Exception as rtsa_error:
                    logger.warning(f"RTSA trigger failed (non-critical): {rtsa_error}")
        
        new_snapshot = SentimentSnapshot(
            score=final_score,
            state=state['key'],
            state_label=state['label'],
            state_color=state['color'],
            top_keywords=json.dumps(top_keywords),
            sample_size=len(items),
            verified_weight=verified_count,
            computed_at=datetime.utcnow()
        )
        db.session.add(new_snapshot)
        db.session.commit()
        
        return {
            'score': round(final_score, 1),
            'state': state,
            'keywords': top_keywords,
            'sample_size': len(items),
            'verified_count': verified_count,
            'state_changed': state_changed,
            'previous_state': previous_state
        }
        
    except Exception as e:
        logger.error(f"Error computing network sentiment: {e}")
        return {
            'score': 50,
            'state': get_state_from_score(50),
            'keywords': [],
            'sample_size': 0,
            'verified_count': 0,
            'error': str(e)
        }


def get_latest_sentiment() -> Dict:
    try:
        from models import SentimentSnapshot
        
        snapshot = SentimentSnapshot.query.order_by(SentimentSnapshot.computed_at.desc()).first()
        
        if not snapshot:
            return {
                'score': 50,
                'state': get_state_from_score(50),
                'keywords': [],
                'sample_size': 0,
                'computed_at': None
            }
        
        keywords = []
        if snapshot.top_keywords:
            try:
                keywords = json.loads(snapshot.top_keywords)
            except:
                pass
        
        return {
            'score': snapshot.score,
            'state': {
                'key': snapshot.state,
                'label': snapshot.state_label,
                'color': snapshot.state_color,
                'score': snapshot.score
            },
            'keywords': keywords[:3],
            'sample_size': snapshot.sample_size,
            'verified_count': snapshot.verified_weight,
            'computed_at': snapshot.computed_at.isoformat() if snapshot.computed_at else None
        }
        
    except Exception as e:
        logger.error(f"Error getting latest sentiment: {e}")
        return {
            'score': 50,
            'state': get_state_from_score(50),
            'keywords': [],
            'error': str(e)
        }


def get_recent_pulse_events(limit: int = 10) -> List[Dict]:
    try:
        from models import PulseEvent
        
        events = PulseEvent.query.order_by(PulseEvent.triggered_at.desc()).limit(limit).all()
        
        return [{
            'id': e.id,
            'event_type': e.event_type,
            'from_state': e.from_state,
            'to_state': e.to_state,
            'score': e.score,
            'triggered_at': e.triggered_at.isoformat() if e.triggered_at else None
        } for e in events]
        
    except Exception as e:
        logger.error(f"Error getting pulse events: {e}")
        return []
