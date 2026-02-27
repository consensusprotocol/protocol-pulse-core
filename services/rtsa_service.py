"""
Real-Time Sovereign Apparel (RTSA) Engine
Links Sentiment Engine to Printful for JIT cultural manufacturing.
When major sentiment shifts occur, generates ethos statement apparel.
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Optional, Dict

from app import db
from models import RealTimeProduct, PulseEvent

logger = logging.getLogger(__name__)


class RTSAService:
    """Orchestrates the Real-Time Sovereign Apparel pipeline"""
    
    TRIGGER_STATES = [
        'ABSOLUTE_SINGULARITY',
        'CRITICAL_CONTENTION',
        'CONSENSUS_FORMING'
    ]
    
    COOLDOWN_HOURS = 6
    
    def __init__(self):
        self.last_forge_time = None
    
    def check_trigger(self, sentiment_result: Dict) -> bool:
        """
        Check if sentiment state change should trigger RTSA forge.
        
        Args:
            sentiment_result: Result from compute_network_sentiment()
        
        Returns:
            True if should trigger, False otherwise
        """
        if not sentiment_result.get('state_changed'):
            return False
        
        new_state = sentiment_result.get('state', {}).get('key', 'EQUILIBRIUM')
        
        if new_state not in self.TRIGGER_STATES:
            logger.debug(f"State {new_state} not in trigger states")
            return False
        
        recent_product = RealTimeProduct.query.filter(
            RealTimeProduct.created_at >= datetime.utcnow() - timedelta(hours=self.COOLDOWN_HOURS)
        ).first()
        
        if recent_product:
            logger.info(f"RTSA cooldown active - last product created at {recent_product.created_at}")
            return False
        
        return True
    
    def forge_from_sentiment(self, sentiment_result: Dict) -> Optional[RealTimeProduct]:
        """
        Execute full RTSA forge pipeline from sentiment data.
        
        Args:
            sentiment_result: Result from compute_network_sentiment()
        
        Returns:
            Created RealTimeProduct or None
        """
        try:
            from services.design_forge import forge_complete_design
            
            state = sentiment_result.get('state', {})
            state_key = state.get('key', 'EQUILIBRIUM')
            score = sentiment_result.get('score', 50)
            keywords = sentiment_result.get('keywords', [])
            
            logger.info(f"RTSA Forge triggered: {state_key} @ {score}")
            
            design = forge_complete_design(
                state=state_key,
                score=score,
                keywords=keywords,
                trigger='state_change'
            )
            
            if not design:
                logger.error("Design Forge failed to generate statement")
                return None
            
            keywords_json = json.dumps(keywords) if keywords else None
            
            product = RealTimeProduct(
                statement_text=design['statement'],
                design_style=design['placement'],
                text_color=design['text_color'],
                trigger_state=state_key,
                trigger_keywords=keywords_json,
                sentiment_score=score,
                sarah_description=design['sarah_note'],
                status='draft',
                heat_multiplier=2.0
            )
            
            db.session.add(product)
            db.session.commit()
            
            logger.info(f"RTSA Product created: {product.id} - {design['statement']}")
            
            return product
            
        except Exception as e:
            logger.error(f"RTSA forge error: {e}")
            db.session.rollback()
            return None
    
    def forge_from_whale_event(self, whale_data: Dict) -> Optional[RealTimeProduct]:
        """
        Trigger RTSA forge from whale transaction event.
        
        Args:
            whale_data: Whale transaction info (amount, type, etc.)
        
        Returns:
            Created RealTimeProduct or None
        """
        try:
            from services.design_forge import generate_ethos_statement
            
            amount_btc = whale_data.get('amount_btc', 0)
            tx_type = whale_data.get('type', 'transfer')
            
            if amount_btc < 500:
                return None
            
            keywords = [
                {'keyword': f'#{tx_type.upper()}', 'weight': 3},
                {'keyword': '#WHALE', 'weight': 2},
                {'keyword': f'#{amount_btc}BTC', 'weight': 1}
            ]
            
            statement_data = generate_ethos_statement(
                state='CONSENSUS_FORMING',
                score=75,
                keywords=keywords,
                trigger='whale_detonation'
            )
            
            if not statement_data:
                return None
            
            product = RealTimeProduct(
                statement_text=statement_data['statement'],
                design_style=statement_data['placement'],
                text_color=statement_data['text_color'],
                trigger_state='WHALE_DETONATION',
                trigger_keywords=json.dumps(keywords),
                sentiment_score=75,
                sarah_description=statement_data['sarah_note'],
                status='draft',
                heat_multiplier=2.5
            )
            
            db.session.add(product)
            db.session.commit()
            
            logger.info(f"RTSA Whale Product created: {product.id}")
            return product
            
        except Exception as e:
            logger.error(f"RTSA whale forge error: {e}")
            db.session.rollback()
            return None
    
    def approve_product(self, product_id: int, user_id: int) -> Optional[Dict]:
        """
        Approve a draft RTSA product and push to Printful.
        
        Args:
            product_id: ID of the RealTimeProduct
            user_id: ID of the approving admin
        
        Returns:
            Dict with result or None on failure
        """
        try:
            from services.printful_service import printful_service
            
            product = RealTimeProduct.query.get(product_id)
            if not product:
                return None
            
            if product.status != 'draft':
                return {'error': 'Product is not in draft status'}
            
            product.approve(user_id)
            db.session.commit()
            
            logger.info(f"RTSA Product {product_id} approved by user {user_id}")
            
            return {
                'success': True,
                'product_id': product.id,
                'statement': product.statement_text,
                'status': product.status,
                'heat_expires_at': product.heat_expires_at.isoformat() if product.heat_expires_at else None
            }
            
        except Exception as e:
            logger.error(f"RTSA approval error: {e}")
            db.session.rollback()
            return None
    
    def reject_product(self, product_id: int) -> bool:
        """Reject a draft RTSA product"""
        try:
            product = RealTimeProduct.query.get(product_id)
            if not product:
                return False
            
            product.reject()
            db.session.commit()
            
            logger.info(f"RTSA Product {product_id} rejected")
            return True
            
        except Exception as e:
            logger.error(f"RTSA rejection error: {e}")
            db.session.rollback()
            return False
    
    def get_draft_products(self) -> list:
        """Get all draft RTSA products awaiting approval"""
        return RealTimeProduct.query.filter_by(
            status='draft'
        ).order_by(
            RealTimeProduct.created_at.desc()
        ).all()
    
    def get_approved_products(self, limit: int = 10) -> list:
        """Get approved RTSA products for display"""
        return RealTimeProduct.query.filter_by(
            status='approved'
        ).order_by(
            RealTimeProduct.approved_at.desc()
        ).limit(limit).all()
    
    def get_hot_products(self) -> list:
        """Get products still in their HEAT window"""
        now = datetime.utcnow()
        return RealTimeProduct.query.filter(
            RealTimeProduct.status == 'approved',
            RealTimeProduct.heat_expires_at > now
        ).order_by(
            RealTimeProduct.heat_multiplier.desc()
        ).all()
    
    def get_foundational_statements(self) -> list:
        """Get foundational ethos statements for display when no real-time products exist"""
        return [
            {
                'statement': 'Stack Sats Stay Humble',
                'placement': 'center_chest',
                'text_color': '#FFFFFF',
                'sarah_note': 'The foundational Bitcoin ethos - accumulate patiently, remain grounded.'
            },
            {
                'statement': 'Not Your Keys',
                'placement': 'left_chest_badge',
                'text_color': '#DC2626',
                'sarah_note': 'Self-custody is sovereignty. This is non-negotiable for serious holders.'
            },
            {
                'statement': 'Proof of Work',
                'placement': 'center_chest',
                'text_color': '#FFFFFF',
                'sarah_note': 'The consensus mechanism that secures the network - and a life philosophy.'
            },
            {
                'statement': 'Stay Sovereign',
                'placement': 'left_chest_badge',
                'text_color': '#F7931A',
                'sarah_note': 'Financial independence through Bitcoin. The ultimate goal.'
            },
            {
                'statement': 'Verify Dont Trust',
                'placement': 'center_chest',
                'text_color': '#FFFFFF',
                'sarah_note': 'Run your own node. Check the math. Trust no intermediary.'
            }
        ]
    
    def broadcast_new_product(self, product: RealTimeProduct) -> bool:
        """
        Broadcast new RTSA product to social channels.
        
        Args:
            product: The approved RealTimeProduct
        
        Returns:
            True if broadcast successful
        """
        try:
            from services.x_service import x_service
            
            tweet = f"""📡 Broadcasting Signal: Tactical Ethos Apparel generated for current Network State.

"{product.statement_text}"

Limited availability for Rank II+ Operatives.

protocolpulse.ai/merch

#Bitcoin #SovereignApparel"""
            
            if hasattr(x_service, 'post_tweet'):
                x_service.post_tweet(tweet)
                logger.info(f"RTSA broadcast sent for product {product.id}")
                return True
            else:
                logger.warning("X service not available for broadcast")
                return False
                
        except Exception as e:
            logger.error(f"RTSA broadcast error: {e}")
            return False


rtsa_service = RTSAService()


def hook_sentiment_engine():
    """
    Hook RTSA into the sentiment engine.
    Call this after compute_network_sentiment() completes.
    """
    from services.sentiment_engine import compute_network_sentiment
    
    original_compute = compute_network_sentiment
    
    def wrapped_compute(*args, **kwargs):
        result = original_compute(*args, **kwargs)
        
        if rtsa_service.check_trigger(result):
            product = rtsa_service.forge_from_sentiment(result)
            if product:
                logger.info(f"RTSA auto-forged product: {product.statement_text}")
        
        return result
    
    return wrapped_compute
