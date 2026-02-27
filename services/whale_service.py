import os
import logging
import requests
from datetime import datetime
from typing import Dict, List, Optional
from app import db
from models import WhaleTransaction

logger = logging.getLogger(__name__)

KNOWN_COLD_WALLETS = {
    'bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh': 'Binance Cold',
    '3Kzh9qAqVWQhEsfQz7zEQL1EuSx5tyNLNS': 'Bitfinex Cold',
    'bc1qgdjqv0av3q56jvd82tkdjpy7gdp9ut8tlqmgrpmv24sq90ecnvqqjwvw97': 'BitMEX Cold',
    '1P5ZEDWTKTFGxQjZphgWPQUpe554WKDfHQ': 'Coinbase Cold',
    'bc1qa5wkgaew2dkv56kfc68j2s0fz9v0ffc7khkz2p': 'Kraken Cold',
    '3LYJfcfHPXYJreMsASk2jkn69LWEYKzexb': 'Huobi Cold'
}

EXCHANGE_WALLETS = {
    'bc1qm34lsc65zpw79lxes69zkqmk6ee3ewf0j77s3h': 'Binance Hot',
    'bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh': 'Binance',
    '3Kzh9qAqVWQhEsfQz7zEQL1EuSx5tyNLNS': 'Bitfinex',
    '1P5ZEDWTKTFGxQjZphgWPQUpe554WKDfHQ': 'Coinbase'
}


class WhaleService:
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.mempool_api = "https://mempool.space/api"
    
    def fetch_recent_whales(self, min_btc: float = 10, limit: int = 10) -> List[Dict]:
        try:
            response = requests.get(f"{self.mempool_api}/mempool/recent", timeout=10)
            if response.status_code != 200:
                return []
            
            transactions = response.json()
            whales = []
            
            for tx in transactions[:50]:
                total_value = sum(out.get('value', 0) for out in tx.get('vout', [])) / 100000000
                if total_value >= min_btc:
                    whales.append({
                        'txid': tx.get('txid'),
                        'btc_amount': round(total_value, 4),
                        'fee_sats': tx.get('fee', 0),
                        'detected_at': datetime.utcnow().isoformat()
                    })
                    
                    if len(whales) >= limit:
                        break
            
            return whales
        except Exception as e:
            self.logger.error(f"Error fetching whale transactions: {e}")
            return []
    
    def evaluate_whale_move(self, tx_data: Dict) -> Dict:
        btc_amount = tx_data.get('btc_amount', 0)
        result = {
            'is_mega': btc_amount >= 1000,
            'significance': 'normal',
            'alex_analysis': None,
            'sarah_flash': None,
            'should_dispatch': False
        }
        
        if btc_amount >= 1000:
            result['significance'] = 'mega_whale'
            result['should_dispatch'] = True
            
            source_type = self._identify_address_type(tx_data.get('source_address', ''))
            dest_type = self._identify_address_type(tx_data.get('dest_address', ''))
            
            result['alex_analysis'] = self._alex_verify_move(btc_amount, source_type, dest_type)
            result['sarah_flash'] = self._sarah_intelligence_flash(btc_amount, source_type, dest_type)
        
        elif btc_amount >= 500:
            result['significance'] = 'large_whale'
        elif btc_amount >= 100:
            result['significance'] = 'notable'
        
        return result
    
    def _identify_address_type(self, address: str) -> str:
        if address in KNOWN_COLD_WALLETS:
            return f"cold_storage:{KNOWN_COLD_WALLETS[address]}"
        if address in EXCHANGE_WALLETS:
            return f"exchange:{EXCHANGE_WALLETS[address]}"
        if address.startswith('bc1q') and len(address) > 60:
            return "unknown_cold"
        return "unknown"
    
    def _alex_verify_move(self, btc_amount: float, source_type: str, dest_type: str) -> Dict:
        analysis = {
            'verified': True,
            'pattern': 'unknown',
            'risk_level': 'medium'
        }
        
        if 'exchange' in source_type and 'cold' in dest_type:
            analysis['pattern'] = 'exchange_withdrawal'
            analysis['risk_level'] = 'low'
            analysis['note'] = "Liquidity moving to cold storage - bullish signal"
        elif 'cold' in source_type and 'exchange' in dest_type:
            analysis['pattern'] = 'cold_to_exchange'
            analysis['risk_level'] = 'high'
            analysis['note'] = "Cold storage moving to exchange - potential sell pressure"
        elif 'exchange' in source_type and 'exchange' in dest_type:
            analysis['pattern'] = 'inter_exchange'
            analysis['risk_level'] = 'medium'
            analysis['note'] = "Inter-exchange transfer - arbitrage or repositioning"
        else:
            analysis['pattern'] = 'unknown_movement'
            analysis['note'] = "Unknown wallet pattern - monitoring required"
        
        return analysis
    
    def _sarah_intelligence_flash(self, btc_amount: float, source_type: str, dest_type: str) -> str:
        if 'exchange' in source_type and 'cold' in dest_type:
            return f"MEGA-WHALE ALERT: {btc_amount:,.0f} BTC moving from exchange to cold storage. Liquidity drying up. Macro bullish."
        elif 'cold' in source_type and 'exchange' in dest_type:
            return f"MEGA-WHALE ALERT: {btc_amount:,.0f} BTC moving from cold storage to exchange. Potential distribution ahead. Watch price action."
        else:
            return f"MEGA-WHALE ALERT: {btc_amount:,.0f} BTC detected on-chain. Unknown wallet signatures. Intel developing."
    
    def record_whale_transaction(self, tx_data: Dict) -> Optional[WhaleTransaction]:
        try:
            existing = WhaleTransaction.query.filter_by(txid=tx_data.get('txid')).first()
            if existing:
                return existing
            
            whale = WhaleTransaction(
                txid=tx_data.get('txid'),
                btc_amount=tx_data.get('btc_amount', 0),
                usd_value=tx_data.get('usd_value'),
                fee_sats=tx_data.get('fee_sats'),
                block_height=tx_data.get('block_height'),
                is_mega=tx_data.get('btc_amount', 0) >= 1000
            )
            
            db.session.add(whale)
            db.session.commit()
            
            return whale
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Error recording whale transaction: {e}")
            return None
    
    def dispatch_mega_whale_alert(self, tx_data: Dict, analysis: Dict) -> Dict:
        dispatch_results = {'nostr': False, 'x': False}
        
        sarah_flash = analysis.get('sarah_flash', '')
        if not sarah_flash:
            return dispatch_results
        
        try:
            from services.nostr_service import NostrService
            nostr = NostrService()
            nostr.publish_note(sarah_flash)
            dispatch_results['nostr'] = True
        except Exception as e:
            self.logger.error(f"Nostr dispatch failed: {e}")
        
        try:
            from services.x_service import XService
            x_service = XService()
            x_service.post_tweet(sarah_flash)
            dispatch_results['x'] = True
        except Exception as e:
            self.logger.error(f"X dispatch failed: {e}")
        
        return dispatch_results
    
    def check_for_mega_whales(self) -> Dict:
        """Check for mega whales (1000+ BTC) and dispatch alerts"""
        whales = self.fetch_recent_whales(min_btc=500, limit=20)
        
        mega_whale_detected = False
        alerts_sent = []
        
        for whale in whales:
            evaluation = self.evaluate_whale_move(whale)
            
            if evaluation.get('should_dispatch'):
                mega_whale_detected = True
                self.record_whale_transaction(whale)
                dispatch_result = self.dispatch_mega_whale_alert(whale, evaluation)
                alerts_sent.append({
                    'txid': whale.get('txid'),
                    'btc': whale.get('btc_amount'),
                    'dispatched': dispatch_result
                })
        
        return {
            'mega_whale_detected': mega_whale_detected,
            'alerts_sent': alerts_sent,
            'checked_at': datetime.utcnow().isoformat()
        }


whale_service = WhaleService()
