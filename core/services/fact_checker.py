"""
Protocol Pulse Fact Checker Service
Prevents AI hallucinations by verifying claims against live blockchain data.

Philosophy: "Technical Storytelling, Not Hype" - Facts first, always.
"""

import requests
import re
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class FactChecker:
    """Verifies factual claims in Bitcoin articles against live data sources."""
    
    BITNODES_API = "https://bitnodes.io/api"
    MEMPOOL_API = "https://mempool.space/api/v1"
    COINGECKO_API = "https://api.coingecko.com/api/v3"
    BLOCKCHAIN_INFO_API = "https://blockchain.info"
    
    TREND_THRESHOLDS = {
        'surging': 15,      # 15%+ growth
        'increasing': 5,    # 5-15% growth
        'stable': -5,       # -5% to 5%
        'declining': -15,   # -15% to -5%
        'plummeting': -100  # Below -15%
    }
    
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes
    
    def _get_cached(self, key: str) -> Optional[dict]:
        """Get cached data if not expired."""
        if key in self.cache:
            data, timestamp = self.cache[key]
            if datetime.now() - timestamp < timedelta(seconds=self.cache_ttl):
                return data
        return None
    
    def _set_cache(self, key: str, data: dict):
        """Cache data with timestamp."""
        self.cache[key] = (data, datetime.now())
    
    def verify_node_count(self, claimed_count: int = None, claimed_trend: str = None) -> Dict:
        """
        Verifies Bitcoin node count claims against Bitnodes API.
        
        Args:
            claimed_count: The number claimed in article (e.g., 15000)
            claimed_trend: 'surging', 'declining', 'stable', etc.
        
        Returns:
            Verification result with actual data
        """
        try:
            cached = self._get_cached('node_count')
            if cached:
                current_count = cached['total_nodes']
            else:
                response = requests.get(f"{self.BITNODES_API}/snapshots/latest/", timeout=10)
                response.raise_for_status()
                data = response.json()
                current_count = data.get('total_nodes', 0)
                self._set_cache('node_count', data)
            
            hist_response = requests.get(f"{self.BITNODES_API}/snapshots/?limit=30", timeout=10)
            hist_data = hist_response.json()
            
            thirty_days_ago = None
            if hist_data.get('results') and len(hist_data['results']) >= 30:
                thirty_days_ago = hist_data['results'][-1].get('total_nodes')
            
            pct_change = 0
            actual_trend = 'unknown'
            if thirty_days_ago and thirty_days_ago > 0:
                pct_change = ((current_count - thirty_days_ago) / thirty_days_ago) * 100
                
                if pct_change >= self.TREND_THRESHOLDS['surging']:
                    actual_trend = 'surging'
                elif pct_change >= self.TREND_THRESHOLDS['increasing']:
                    actual_trend = 'increasing'
                elif pct_change >= self.TREND_THRESHOLDS['stable']:
                    actual_trend = 'stable'
                elif pct_change >= self.TREND_THRESHOLDS['declining']:
                    actual_trend = 'declining'
                else:
                    actual_trend = 'plummeting'
            
            errors = []
            
            if claimed_count is not None:
                tolerance = current_count * 0.10  # 10% tolerance
                if abs(claimed_count - current_count) > tolerance:
                    errors.append(
                        f"Node count claim inaccurate. Claimed: {claimed_count:,}, "
                        f"Actual: {current_count:,} (off by {abs(claimed_count - current_count):,})"
                    )
            
            if claimed_trend is not None:
                claimed_lower = claimed_trend.lower()
                if claimed_lower in ['surging', 'surge', 'skyrocketing', 'unprecedented']:
                    if actual_trend not in ['surging']:
                        errors.append(
                            f"Trend claim inaccurate. Claimed: '{claimed_trend}' but actual trend is "
                            f"'{actual_trend}' ({pct_change:+.1f}% over 30 days)"
                        )
                elif claimed_lower in ['increasing', 'growing', 'rising']:
                    if actual_trend not in ['surging', 'increasing']:
                        errors.append(
                            f"Trend claim inaccurate. Claimed: '{claimed_trend}' but actual is "
                            f"'{actual_trend}' ({pct_change:+.1f}% over 30 days)"
                        )
            
            return {
                'verified': len(errors) == 0,
                'actual_count': current_count,
                'claimed_count': claimed_count,
                'actual_trend': actual_trend,
                'claimed_trend': claimed_trend,
                'pct_change_30d': round(pct_change, 2),
                'errors': errors,
                'source': 'bitnodes.io',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Node count verification failed: {e}")
            return {
                'verified': False,
                'errors': [f"Verification failed: {str(e)}"],
                'actual_count': None,
                'source': 'bitnodes.io',
                'timestamp': datetime.now().isoformat()
            }
    
    def verify_difficulty(self, claimed_value: float = None, claimed_is_ath: bool = False) -> Dict:
        """
        Verifies Bitcoin difficulty claims against Mempool.space API.
        
        Args:
            claimed_value: Claimed difficulty in T (e.g., 146.47 for 146.47T)
            claimed_is_ath: Whether article claims this is all-time high
        
        Returns:
            Verification result
        """
        try:
            response = requests.get("https://mempool.space/api/v1/blocks/tip/height", timeout=10)
            response.raise_for_status()
            tip_height = response.json()
            
            block_response = requests.get(f"https://mempool.space/api/block-height/{tip_height}", timeout=10)
            block_hash = block_response.text.strip()
            
            block_detail_response = requests.get(f"https://mempool.space/api/block/{block_hash}", timeout=10)
            block_data = block_detail_response.json()
            
            current_difficulty = block_data.get('difficulty', 0)
            current_t = current_difficulty / 1e12
            
            KNOWN_ATH_T = 155.9
            
            errors = []
            
            if claimed_value is not None:
                tolerance = claimed_value * 0.10  # 10% tolerance
                if abs(claimed_value - current_t) > tolerance:
                    errors.append(
                        f"Difficulty claim inaccurate. Claimed: {claimed_value}T, Actual: {current_t:.2f}T"
                    )
            
            is_actually_ath = current_t > KNOWN_ATH_T
            if claimed_is_ath and not is_actually_ath:
                errors.append(
                    f"ATH claim incorrect. Current difficulty ({current_t:.2f}T) is not an all-time high. "
                    f"Known ATH is {KNOWN_ATH_T}T from November 2025."
                )
            
            return {
                'verified': len(errors) == 0,
                'actual_difficulty_t': round(current_t, 2),
                'claimed_difficulty_t': claimed_value,
                'is_ath': is_actually_ath,
                'known_ath_t': KNOWN_ATH_T,
                'claimed_is_ath': claimed_is_ath,
                'errors': errors,
                'source': 'mempool.space',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Difficulty verification failed: {e}")
            return {
                'verified': False,
                'errors': [f"Verification failed: {str(e)}"],
                'source': 'mempool.space',
                'timestamp': datetime.now().isoformat()
            }
    
    def verify_price_movement(self, claimed_movement: str) -> Dict:
        """
        Verifies price movement claims. We AVOID price headlines but verify if mentioned.
        
        Args:
            claimed_movement: 'surging', 'plummeting', 'stable', etc.
        
        Returns:
            Verification result
        """
        try:
            response = requests.get(
                f"{self.COINGECKO_API}/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true",
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            change_24h = data['bitcoin'].get('usd_24h_change', 0)
            current_price = data['bitcoin'].get('usd', 0)
            
            if change_24h > 10:
                actual_movement = 'surging'
            elif change_24h > 3:
                actual_movement = 'rising'
            elif change_24h > -3:
                actual_movement = 'stable'
            elif change_24h > -10:
                actual_movement = 'declining'
            else:
                actual_movement = 'plummeting'
            
            errors = []
            claimed_lower = claimed_movement.lower()
            
            movement_map = {
                'surging': ['surging'],
                'rising': ['surging', 'rising'],
                'stable': ['rising', 'stable', 'declining'],
                'declining': ['declining', 'stable'],
                'plummeting': ['plummeting', 'declining'],
                'crashing': ['plummeting']
            }
            
            if claimed_lower in movement_map:
                if actual_movement not in movement_map[claimed_lower]:
                    errors.append(
                        f"Price movement claim inaccurate. Claimed: '{claimed_movement}', "
                        f"Actual: '{actual_movement}' ({change_24h:+.1f}% 24h)"
                    )
            
            return {
                'verified': len(errors) == 0,
                'current_price_usd': current_price,
                'change_24h': round(change_24h, 2),
                'actual_movement': actual_movement,
                'claimed_movement': claimed_movement,
                'errors': errors,
                'source': 'coingecko.com',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Price verification failed: {e}")
            return {
                'verified': False,
                'errors': [f"Verification failed: {str(e)}"],
                'source': 'coingecko.com',
                'timestamp': datetime.now().isoformat()
            }
    
    def verify_hashrate(self, claimed_value: float = None, claimed_unit: str = 'EH/s') -> Dict:
        """
        Verifies hashrate claims.
        
        Args:
            claimed_value: Claimed hashrate value
            claimed_unit: Unit (EH/s, TH/s, etc.)
        
        Returns:
            Verification result
        """
        try:
            response = requests.get("https://mempool.space/api/v1/mining/hashrate/3d", timeout=10)
            response.raise_for_status()
            data = response.json()
            
            current_hashrate = data.get('currentHashrate', 0)
            current_eh = current_hashrate / 1e18 if current_hashrate > 0 else 0
            
            errors = []
            
            if claimed_value is not None:
                claimed_eh = claimed_value
                if claimed_unit.upper() == 'TH/S':
                    claimed_eh = claimed_value / 1e6
                elif claimed_unit.upper() == 'PH/S':
                    claimed_eh = claimed_value / 1e3
                
                tolerance = current_eh * 0.10  # 10% tolerance
                if abs(claimed_eh - current_eh) > tolerance:
                    errors.append(
                        f"Hashrate claim inaccurate. Claimed: {claimed_value} {claimed_unit}, "
                        f"Actual: {current_eh:.0f} EH/s"
                    )
            
            return {
                'verified': len(errors) == 0,
                'actual_hashrate_eh': round(current_eh, 1),
                'claimed_value': claimed_value,
                'claimed_unit': claimed_unit,
                'errors': errors,
                'source': 'mempool.space',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Hashrate verification failed: {e}")
            return {
                'verified': False,
                'errors': [f"Verification failed: {str(e)}"],
                'source': 'mempool.space',
                'timestamp': datetime.now().isoformat()
            }
    
    def extract_claims_from_article(self, article_text: str) -> List[Dict]:
        """
        Extracts verifiable claims from article text using pattern matching.
        
        Args:
            article_text: The full article text
        
        Returns:
            List of extracted claims with their types
        """
        claims = []
        
        node_patterns = [
            r'(\d{1,3}(?:,\d{3})*)\s*(?:reachable\s+)?nodes?',
            r'node\s+count\s+(?:has\s+)?(?:reached|crossed|surpassed)\s+(\d{1,3}(?:,\d{3})*)',
            r'(\d{1,3}(?:,\d{3})*)\s+mark\s+(?:globally|worldwide)?'
        ]
        
        trend_patterns = [
            (r'(?:nodes?|count)\s+(?:is\s+)?(?:surging|skyrocketing|unprecedented)', 'surging'),
            (r'(?:nodes?|count)\s+(?:is\s+)?(?:increasing|growing|rising)', 'increasing'),
            (r'(?:nodes?|count)\s+(?:is\s+)?(?:stable|steady)', 'stable'),
            (r'(?:nodes?|count)\s+(?:is\s+)?(?:declining|dropping|falling)', 'declining'),
        ]
        
        for pattern in node_patterns:
            matches = re.findall(pattern, article_text, re.IGNORECASE)
            for match in matches:
                count = int(match.replace(',', ''))
                claims.append({
                    'type': 'node_count',
                    'value': count,
                    'raw_text': match
                })
        
        for pattern, trend in trend_patterns:
            if re.search(pattern, article_text, re.IGNORECASE):
                claims.append({
                    'type': 'node_trend',
                    'value': trend,
                    'raw_text': re.search(pattern, article_text, re.IGNORECASE).group()
                })
        
        difficulty_patterns = [
            r'difficulty\s+(?:of\s+)?(\d+(?:\.\d+)?)\s*T',
            r'(\d+(?:\.\d+)?)\s*T\s+difficulty'
        ]
        
        for pattern in difficulty_patterns:
            matches = re.findall(pattern, article_text, re.IGNORECASE)
            for match in matches:
                claims.append({
                    'type': 'difficulty',
                    'value': float(match),
                    'raw_text': match
                })
        
        if re.search(r'all[- ]time\s+high|ATH|record\s+(?:high|difficulty)', article_text, re.IGNORECASE):
            claims.append({
                'type': 'difficulty_ath',
                'value': True,
                'raw_text': 'all-time high/ATH claim'
            })
        
        hashrate_patterns = [
            r'hashrate\s+(?:of\s+)?(\d+(?:\.\d+)?)\s*(EH|TH|PH)',
            r'(\d+(?:\.\d+)?)\s*(EH|TH|PH)/s\s+hashrate'
        ]
        
        for pattern in hashrate_patterns:
            matches = re.findall(pattern, article_text, re.IGNORECASE)
            for match in matches:
                claims.append({
                    'type': 'hashrate',
                    'value': float(match[0]),
                    'unit': match[1].upper() + '/s',
                    'raw_text': f"{match[0]} {match[1]}/s"
                })
        
        return claims
    
    def verify_article(self, article_text: str) -> Dict:
        """
        Comprehensive article verification. Extracts and verifies all claims.
        
        Args:
            article_text: The full article text
        
        Returns:
            Complete verification report
        """
        claims = self.extract_claims_from_article(article_text)
        
        results = {
            'verified': True,
            'claims_found': len(claims),
            'claims_verified': 0,
            'claims_failed': 0,
            'errors': [],
            'warnings': [],
            'verifications': [],
            'timestamp': datetime.now().isoformat()
        }
        
        node_count_claim = None
        node_trend_claim = None
        
        for claim in claims:
            if claim['type'] == 'node_count':
                node_count_claim = claim['value']
            elif claim['type'] == 'node_trend':
                node_trend_claim = claim['value']
        
        if node_count_claim is not None or node_trend_claim is not None:
            verification = self.verify_node_count(node_count_claim, node_trend_claim)
            results['verifications'].append({
                'type': 'node_count',
                'result': verification
            })
            if verification['verified']:
                results['claims_verified'] += 1
            else:
                results['claims_failed'] += 1
                results['errors'].extend(verification.get('errors', []))
                results['verified'] = False
        
        difficulty_claim = None
        difficulty_ath_claim = False
        
        for claim in claims:
            if claim['type'] == 'difficulty':
                difficulty_claim = claim['value']
            elif claim['type'] == 'difficulty_ath':
                difficulty_ath_claim = True
        
        if difficulty_claim is not None or difficulty_ath_claim:
            verification = self.verify_difficulty(difficulty_claim, difficulty_ath_claim)
            results['verifications'].append({
                'type': 'difficulty',
                'result': verification
            })
            if verification['verified']:
                results['claims_verified'] += 1
            else:
                results['claims_failed'] += 1
                results['errors'].extend(verification.get('errors', []))
                results['verified'] = False
        
        for claim in claims:
            if claim['type'] == 'hashrate':
                verification = self.verify_hashrate(claim['value'], claim.get('unit', 'EH/s'))
                results['verifications'].append({
                    'type': 'hashrate',
                    'result': verification
                })
                if verification['verified']:
                    results['claims_verified'] += 1
                else:
                    results['claims_failed'] += 1
                    results['errors'].extend(verification.get('errors', []))
                    results['verified'] = False
        
        return results
    
    def get_current_network_stats(self) -> Dict:
        """
        Gets current accurate network stats for article generation.
        Use this data instead of hallucinating.
        
        Returns:
            Dictionary with current verified network statistics
        """
        stats = {
            'timestamp': datetime.now().isoformat(),
            'sources': []
        }
        
        try:
            node_response = requests.get(f"{self.BITNODES_API}/snapshots/latest/", timeout=10)
            if node_response.ok:
                node_data = node_response.json()
                stats['nodes'] = {
                    'reachable_count': node_data.get('total_nodes'),
                    'timestamp': node_data.get('timestamp')
                }
                stats['sources'].append('bitnodes.io')
        except Exception as e:
            logger.warning(f"Failed to fetch node stats: {e}")
        
        try:
            mempool_response = requests.get(f"{self.MEMPOOL_API}/fees/recommended", timeout=10)
            if mempool_response.ok:
                fee_data = mempool_response.json()
                stats['fees'] = {
                    'fastest': fee_data.get('fastestFee'),
                    'half_hour': fee_data.get('halfHourFee'),
                    'hour': fee_data.get('hourFee'),
                    'economy': fee_data.get('economyFee')
                }
                stats['sources'].append('mempool.space')
        except Exception as e:
            logger.warning(f"Failed to fetch fee stats: {e}")
        
        try:
            diff_response = requests.get(f"{self.MEMPOOL_API}/difficulty-adjustment", timeout=10)
            if diff_response.ok:
                diff_data = diff_response.json()
                stats['difficulty'] = {
                    'current': diff_data.get('difficultyChange'),
                    'progress_percent': diff_data.get('progressPercent'),
                    'remaining_blocks': diff_data.get('remainingBlocks'),
                    'remaining_time': diff_data.get('remainingTime'),
                    'estimated_retarget': diff_data.get('estimatedRetargetDate')
                }
        except Exception as e:
            logger.warning(f"Failed to fetch difficulty stats: {e}")
        
        try:
            hashrate_response = requests.get("https://mempool.space/api/v1/mining/hashrate/3d", timeout=10)
            if hashrate_response.ok:
                hashrate_data = hashrate_response.json()
                current_hashrate = hashrate_data.get('currentHashrate', 0)
                stats['hashrate'] = {
                    'current_eh': round(current_hashrate / 1e18, 1) if current_hashrate > 0 else 0,
                    'current_raw': current_hashrate
                }
        except Exception as e:
            logger.warning(f"Failed to fetch hashrate stats: {e}")
        
        try:
            price_response = requests.get(
                f"{self.COINGECKO_API}/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true",
                timeout=10
            )
            if price_response.ok:
                price_data = price_response.json()
                stats['price'] = {
                    'usd': price_data['bitcoin'].get('usd'),
                    'change_24h': round(price_data['bitcoin'].get('usd_24h_change', 0), 2)
                }
                stats['sources'].append('coingecko.com')
        except Exception as e:
            logger.warning(f"Failed to fetch price stats: {e}")
        
        return stats


fact_checker = FactChecker()


def verify_article_before_publish(article_text: str) -> Tuple[bool, Dict]:
    """
    Convenience function to verify article before publication.
    
    Args:
        article_text: Full article text
    
    Returns:
        Tuple of (is_verified, verification_report)
    """
    report = fact_checker.verify_article(article_text)
    return report['verified'], report


def get_verified_network_stats() -> Dict:
    """
    Get current network stats for accurate article generation.
    
    Returns:
        Dictionary with verified network statistics
    """
    return fact_checker.get_current_network_stats()