import requests
import logging
import time

class NodeService:
    """Service for fetching live Bitcoin network statistics from Mempool.space API"""
    
    _cache = None
    _cache_expiry = 0
    CACHE_DURATION = 30  # Cache for 30 seconds
    
    @classmethod
    def get_network_stats(cls):
        """Fetches live PoW metrics for the Protocol Heartbeat tracker."""
        current_time = time.time()
        
        # Return cached data if still valid
        if cls._cache and current_time < cls._cache_expiry:
            return cls._cache
        
        try:
            # Fetching from Mempool.space API
            height_res = requests.get(
                "https://mempool.space/api/blocks/tip/height", 
                timeout=5
            )
            hashrate_res = requests.get(
                "https://mempool.space/api/v1/mining/hashrate/3d", 
                timeout=5
            )
            difficulty_res = requests.get(
                "https://mempool.space/api/v1/difficulty-adjustment",
                timeout=5
            )
            
            if height_res.status_code == 200:
                height = int(height_res.text)
                
                # Convert raw hashrate to EH/s for that 'Powerhouse' feel
                hashrate_data = hashrate_res.json()
                current_hashrate = hashrate_data.get('currentHashrate', 0) / 10**18
                
                # Get difficulty adjustment info
                diff_data = difficulty_res.json() if difficulty_res.status_code == 200 else {}
                progress_percent = diff_data.get('progressPercent', 0)
                remaining_blocks = diff_data.get('remainingBlocks', 0)
                
                result = {
                    "height": f"{height:,}",
                    "height_raw": height,
                    "hashrate": f"{current_hashrate:.2f} EH/s",
                    "hashrate_raw": current_hashrate,
                    "difficulty_progress": f"{progress_percent:.1f}%",
                    "remaining_blocks": remaining_blocks,
                    "status": "OPERATIONAL"
                }
                
                # Update cache
                cls._cache = result
                cls._cache_expiry = current_time + cls.CACHE_DURATION
                
                return result
                
        except requests.exceptions.Timeout:
            logging.warning("Mempool.space API timeout")
            return cls._get_fallback("TIMEOUT")
        except requests.exceptions.RequestException as e:
            logging.error(f"Node Tracker Request Error: {e}")
            return cls._get_fallback("NETWORK_ERROR")
        except Exception as e:
            logging.error(f"Node Tracker Error: {e}")
            return cls._get_fallback("RECONNECTING")
    
    @classmethod
    def _get_fallback(cls, status):
        """Return cached data if available, otherwise offline status"""
        if cls._cache:
            fallback = cls._cache.copy()
            fallback["status"] = status
            return fallback
        return {
            "height": "---,---",
            "height_raw": 0,
            "hashrate": "--- EH/s",
            "hashrate_raw": 0,
            "difficulty_progress": "--%",
            "remaining_blocks": 0,
            "status": status
        }


# Global instance
node_service = NodeService()