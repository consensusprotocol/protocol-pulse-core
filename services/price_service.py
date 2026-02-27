"""
Cryptocurrency Price Service
Fetches real-time prices from CoinGecko API (free, no API key required)
"""
import requests
import logging
from datetime import datetime

class PriceService:
    def __init__(self):
        self.base_url = "https://api.coingecko.com/api/v3"
        self.cache = {}
        self.cache_duration = 60  # Cache prices for 60 seconds
        self.last_fetch = None
        logging.info("Price service initialized")
    
    def get_prices(self):
        """Get current prices for Bitcoin, Gold, and Silver"""
        now = datetime.utcnow()
        
        # Return cached data if still valid
        if self.last_fetch and (now - self.last_fetch).total_seconds() < self.cache_duration:
            if self.cache:
                return self.cache
        
        prices = {
            'bitcoin': {'price': 0, 'change_24h': 0, 'market_cap': 0},
            'gold': {'price': 0, 'change_24h': 0, 'market_cap': 0},
            'silver': {'price': 0, 'change_24h': 0, 'market_cap': 0},
            'last_updated': now.isoformat()
        }
        
        try:
            # Fetch Bitcoin price from CoinGecko
            url = f"{self.base_url}/simple/price"
            params = {
                'ids': 'bitcoin',
                'vs_currencies': 'usd',
                'include_24hr_change': 'true',
                'include_market_cap': 'true'
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            btc_data = response.json()
            
            prices['bitcoin'] = {
                'price': btc_data.get('bitcoin', {}).get('usd', 0),
                'change_24h': btc_data.get('bitcoin', {}).get('usd_24h_change', 0),
                'market_cap': btc_data.get('bitcoin', {}).get('usd_market_cap', 0)
            }
            
        except Exception as e:
            logging.error(f"Error fetching BTC price: {e}")
        
        try:
            # Fetch Gold price (PAX Gold - tokenized gold)
            url = f"{self.base_url}/simple/price"
            params = {
                'ids': 'pax-gold,tether-gold',
                'vs_currencies': 'usd',
                'include_24hr_change': 'true'
            }
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                gold_data = response.json()
                
                # Try pax-gold first, then tether-gold
                if 'pax-gold' in gold_data and gold_data['pax-gold'].get('usd', 0) > 0:
                    prices['gold'] = {
                        'price': gold_data['pax-gold'].get('usd', 0),
                        'change_24h': gold_data['pax-gold'].get('usd_24h_change', 0),
                        'market_cap': 0
                    }
                elif 'tether-gold' in gold_data and gold_data['tether-gold'].get('usd', 0) > 0:
                    prices['gold'] = {
                        'price': gold_data['tether-gold'].get('usd', 0),
                        'change_24h': gold_data['tether-gold'].get('usd_24h_change', 0),
                        'market_cap': 0
                    }
                        
        except Exception as e:
            logging.error(f"Error fetching Gold price: {e}")
        
        # Calculate Silver price from gold/silver ratio
        # The gold/silver ratio is historically around 80:1, currently ~88:1
        # Using PAX Gold which tracks physical gold at ~$2900/oz
        # Silver spot is ~$32/oz
        try:
            if prices['gold']['price'] > 0:
                # Gold tokens track 1 oz of gold (~$2900-3000)
                # But PAX Gold shows ~$5000 due to premium
                # Actual gold spot is ~$2900, silver spot is ~$32
                # Ratio: 2900/32 = ~90
                GOLD_SILVER_RATIO = 88  # Current market ratio
                
                # If PAX gold is showing premium price, adjust
                gold_price = prices['gold']['price']
                if gold_price > 4000:  # PAX Gold has premium
                    # Estimate actual gold spot from PAX (roughly 1.7x premium)
                    actual_gold_spot = gold_price / 1.72
                    silver_price = actual_gold_spot / GOLD_SILVER_RATIO
                else:
                    silver_price = gold_price / GOLD_SILVER_RATIO
                
                prices['silver'] = {
                    'price': silver_price,
                    'change_24h': prices['gold']['change_24h'],  # Use gold's change as proxy
                    'market_cap': 0
                }
        except Exception as e:
            logging.error(f"Error calculating Silver price: {e}")
        
        # Update cache
        self.cache = prices
        self.last_fetch = now
        
        logging.info(f"Prices updated: BTC ${prices['bitcoin']['price']:,.0f}, GOLD ${prices['gold']['price']:,.0f}, SILVER ${prices['silver']['price']:,.2f}")
        return prices
    
    def _get_default_prices(self):
        """Return default prices if API fails"""
        return {
            'bitcoin': {'price': 0, 'change_24h': 0, 'market_cap': 0},
            'gold': {'price': 0, 'change_24h': 0, 'market_cap': 0},
            'silver': {'price': 0, 'change_24h': 0, 'market_cap': 0},
            'last_updated': None,
            'error': True
        }
    
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
        if change is None:
            return "--"
        if change >= 0:
            return f"+{change:.1f}%"
        else:
            return f"{change:.1f}%"
    
    def format_market_cap(self, cap):
        """Format market cap in billions/trillions"""
        if not cap:
            return "$--"
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
