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
        
        # Real Silver spot from Yahoo Finance SI=F
        try:
            import urllib.request as _ur2, json as _j2
            _req2 = _ur2.Request('https://query1.finance.yahoo.com/v8/finance/chart/SI=F?interval=1d&range=2d', headers={'User-Agent': 'Mozilla/5.0'})
            with _ur2.urlopen(_req2, timeout=5) as _r2:
                _d2 = _j2.loads(_r2.read())
            _m2 = _d2['chart']['result'][0]['meta']
            _sp = float(_m2.get('regularMarketPrice', 0) or 0)
            _sprev = float(_m2.get('chartPreviousClose', _sp) or _sp)
            _schg = round((_sp - _sprev) / _sprev * 100, 2) if _sprev else 0
            if _sp > 5:
                prices['silver'] = {'price': _sp, 'change_24h': _schg, 'market_cap': 0}
            else:
                raise ValueError(f'Bad silver: {_sp}')
        except Exception as _se:
            logging.warning(f'Silver fetch failed: {_se}')
            if prices.get('gold', {}).get('price', 0) > 0:
                prices['silver'] = {'price': round(prices['gold']['price'] / 88, 2), 'change_24h': prices['gold'].get('change_24h', 0), 'market_cap': 0}


        for _k in ["bitcoin", "gold", "silver"]:
            prices[_k]["usd"] = prices[_k]["price"]
            prices[_k]["usd_24h_change"] = prices[_k]["change_24h"]
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
