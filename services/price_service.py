"""
Cryptocurrency Price Service
Fetches real-time prices from CoinGecko API (free, no API key required)
"""
import requests
import logging
from datetime import datetime, timedelta
from functools import lru_cache
import time

class PriceService:
    def __init__(self):
        self.base_url = "https://api.coingecko.com/api/v3"
        self.cache = {}
        self.cache_duration = 60  # Cache prices for 60 seconds
        self.last_fetch = None
        logging.info("Price service initialized")
    
    def get_prices(self):
        """Get current prices for Bitcoin, Ethereum, and other major coins"""
        now = datetime.utcnow()
        
        # Return cached data if still valid
        if self.last_fetch and (now - self.last_fetch).total_seconds() < self.cache_duration:
            if self.cache:
                return self.cache
        
        try:
            # Fetch prices from CoinGecko (free, no API key)
            url = f"{self.base_url}/simple/price"
            params = {
                'ids': 'bitcoin,ethereum,solana',
                'vs_currencies': 'usd',
                'include_24hr_change': 'true',
                'include_market_cap': 'true'
            }
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            # Format the data
            prices = {
                'bitcoin': {
                    'price': data.get('bitcoin', {}).get('usd', 0),
                    'change_24h': data.get('bitcoin', {}).get('usd_24h_change', 0),
                    'market_cap': data.get('bitcoin', {}).get('usd_market_cap', 0)
                },
                'ethereum': {
                    'price': data.get('ethereum', {}).get('usd', 0),
                    'change_24h': data.get('ethereum', {}).get('usd_24h_change', 0),
                    'market_cap': data.get('ethereum', {}).get('usd_market_cap', 0)
                },
                'solana': {
                    'price': data.get('solana', {}).get('usd', 0),
                    'change_24h': data.get('solana', {}).get('usd_24h_change', 0),
                    'market_cap': data.get('solana', {}).get('usd_market_cap', 0)
                },
                'last_updated': now.isoformat()
            }
            
            # Update cache
            self.cache = prices
            self.last_fetch = now
            
            logging.info(f"Prices updated: BTC ${prices['bitcoin']['price']:,.0f}, ETH ${prices['ethereum']['price']:,.0f}")
            return prices
            
        except Exception as e:
            logging.error(f"Error fetching prices: {e}")
            # Return cached data if available, otherwise return defaults
            if self.cache:
                return self.cache
            return self._get_default_prices()
    
    def _get_default_prices(self):
        """Return default prices if API fails"""
        return {
            'bitcoin': {'price': 0, 'change_24h': 0, 'market_cap': 0},
            'ethereum': {'price': 0, 'change_24h': 0, 'market_cap': 0},
            'solana': {'price': 0, 'change_24h': 0, 'market_cap': 0},
            'last_updated': None,
            'error': True
        }
    
    def get_defi_tvl(self):
        """Get total DeFi TVL from DeFiLlama API"""
        try:
            url = "https://api.llama.fi/tvl/defi"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                tvl = response.json()
                return tvl
        except Exception as e:
            logging.error(f"Error fetching DeFi TVL: {e}")
        
        # Fallback - try to get from protocols endpoint
        try:
            url = "https://api.llama.fi/protocols"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                protocols = response.json()
                total_tvl = sum(p.get('tvl', 0) for p in protocols if p.get('tvl'))
                return total_tvl
        except:
            pass
        
        return None
    
    def format_price(self, price):
        """Format price with commas and dollar sign"""
        if not price or price == 0:
            return "$--"
        if price >= 1000:
            return f"${price:,.0f}"
        elif price >= 1:
            return f"${price:,.2f}"
        else:
            return f"${price:.4f}"
    
    def format_change(self, change):
        """Format percentage change with + or - sign"""
        if change >= 0:
            return f"+{change:.1f}%"
        else:
            return f"{change:.1f}%"
    
    def format_market_cap(self, cap):
        """Format market cap in billions/trillions"""
        if cap >= 1_000_000_000_000:
            return f"${cap / 1_000_000_000_000:.2f}T"
        elif cap >= 1_000_000_000:
            return f"${cap / 1_000_000_000:.0f}B"
        elif cap >= 1_000_000:
            return f"${cap / 1_000_000:.0f}M"
        else:
            return f"${cap:,.0f}"

# Initialize singleton
price_service = PriceService()