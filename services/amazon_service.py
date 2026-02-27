import os
import logging
from typing import Optional, Dict, List

class AmazonService:
    """
    Amazon Product Advertising API integration for dynamic book data.
    
    Note: Requires AMAZON_ACCESS_KEY, AMAZON_SECRET_KEY, and AMAZON_PARTNER_TAG
    environment variables to be set for full API functionality.
    
    Without API keys, uses curated fallback book data with affiliate links.
    """
    
    def __init__(self):
        self.access_key = os.environ.get('AMAZON_ACCESS_KEY')
        self.secret_key = os.environ.get('AMAZON_SECRET_KEY')
        self.partner_tag = os.environ.get('AMAZON_PARTNER_TAG', 'protocolpulse-20')
        self.amazon = None
        
        if self.access_key and self.secret_key:
            try:
                from amazon_paapi import AmazonAPI
                self.amazon = AmazonAPI(
                    self.access_key,
                    self.secret_key,
                    self.partner_tag,
                    "US"
                )
                logging.info("Amazon PA-API initialized successfully")
            except ImportError:
                logging.warning("amazon-paapi not installed, using fallback book data")
            except Exception as e:
                logging.error(f"Failed to initialize Amazon API: {e}")
        else:
            logging.info("Amazon API keys not configured, using curated book data")
    
    def get_book_details(self, asin: str) -> Optional[Dict]:
        """
        Fetches book details from Amazon Product Advertising API.
        Returns high-res images and affiliate URLs automatically.
        
        Args:
            asin: Amazon Standard Identification Number
            
        Returns:
            Dict with title, image, url, price, rating or None if failed
        """
        if not self.amazon:
            return self._get_fallback_book(asin)
        
        try:
            product = self.amazon.get_products(asin)
            if product and len(product) > 0:
                item = product[0]
                return {
                    'title': item.title,
                    'image': item.images.primary.large.url if item.images else None,
                    'url': item.detail_page_url,
                    'price': item.offers.listings[0].price.display_amount if item.offers else None,
                    'rating': item.customer_reviews.star_rating if item.customer_reviews else None,
                    'asin': asin
                }
        except Exception as e:
            logging.error(f"Amazon API error for ASIN {asin}: {e}")
        
        return self._get_fallback_book(asin)
    
    def get_books_batch(self, asins: List[str]) -> List[Dict]:
        """
        Fetch multiple books at once for efficiency.
        
        Args:
            asins: List of ASINs to fetch
            
        Returns:
            List of book dictionaries
        """
        if not self.amazon:
            return [self._get_fallback_book(asin) for asin in asins if self._get_fallback_book(asin)]
        
        try:
            products = self.amazon.get_products(asins)
            return [{
                'title': item.title,
                'image': item.images.primary.large.url if item.images else None,
                'url': item.detail_page_url,
                'price': item.offers.listings[0].price.display_amount if item.offers else None,
                'asin': item.asin
            } for item in products]
        except Exception as e:
            logging.error(f"Amazon batch API error: {e}")
            return [self._get_fallback_book(asin) for asin in asins if self._get_fallback_book(asin)]
    
    def _get_fallback_book(self, asin: str) -> Optional[Dict]:
        """
        Returns curated fallback data for known Bitcoin books.
        """
        fallback_books = {
            'bitcoin_standard': {
                'title': 'The Bitcoin Standard',
                'author': 'Saifedean Ammous',
                'image': '/static/images/books/bitcoin_standard.jpg',
                'url': f'https://www.amazon.com/dp/1119473861?tag={self.partner_tag}',
                'asin': '1119473861'
            },
            'broken_money': {
                'title': 'Broken Money',
                'author': 'Lyn Alden',
                'image': '/static/images/books/broken_money.jpg',
                'url': f'https://www.amazon.com/dp/B0CG83MBN9?tag={self.partner_tag}',
                'asin': 'B0CG83MBN9'
            },
            'mastering_bitcoin': {
                'title': 'Mastering Bitcoin',
                'author': 'Andreas Antonopoulos & David Harding',
                'image': '/static/images/books/mastering_bitcoin.jpg',
                'url': f'https://www.amazon.com/dp/1098150090?tag={self.partner_tag}',
                'asin': '1098150090'
            },
            'genesis_book': {
                'title': 'The Genesis Book',
                'author': 'Aaron van Wirdum',
                'image': '/static/images/books/genesis_book.jpg',
                'url': f'https://www.amazon.com/dp/B0BTRPZTY4?tag={self.partner_tag}',
                'asin': 'B0BTRPZTY4'
            },
            'big_print': {
                'title': 'The Big Print',
                'author': 'Lawrence Lepard',
                'image': '/static/images/books/big_print.jpg',
                'url': f'https://www.amazon.com/dp/B0D5K6T8MB?tag={self.partner_tag}',
                'asin': 'B0D5K6T8MB'
            },
            'daylight_robbery': {
                'title': 'Daylight Robbery',
                'author': 'Dominic Frisby',
                'image': '/static/images/books/daylight_robbery.jpg',
                'url': f'https://www.amazon.com/dp/0241360544?tag={self.partner_tag}',
                'asin': '0241360544'
            },
            'everything_21m': {
                'title': 'Everything Divided By 21 Million',
                'author': 'Knut Svanholm',
                'image': '/static/images/books/everything_21m.jpg',
                'url': f'https://www.amazon.com/dp/B09MYXHP1Z?tag={self.partner_tag}',
                'asin': 'B09MYXHP1Z'
            },
            '1544526474': {
                'title': 'The Fiat Standard',
                'author': 'Saifedean Ammous',
                'image': 'https://m.media-amazon.com/images/I/71ePXw1aYhL._SY522_.jpg',
                'url': f'https://www.amazon.com/dp/1544526474?tag={self.partner_tag}',
                'asin': '1544526474'
            },
            '1999257405': {
                'title': 'The Price of Tomorrow',
                'author': 'Jeff Booth',
                'image': 'https://m.media-amazon.com/images/I/71oYv6hF1cL._SY522_.jpg',
                'url': f'https://www.amazon.com/dp/1999257405?tag={self.partner_tag}',
                'asin': '1999257405'
            },
            '1697526349': {
                'title': '21 Lessons',
                'author': 'Gigi',
                'image': 'https://m.media-amazon.com/images/I/71vR+59OxuL._SY522_.jpg',
                'url': f'https://www.amazon.com/dp/1697526349?tag={self.partner_tag}',
                'asin': '1697526349'
            },
            '0684832720': {
                'title': 'The Sovereign Individual',
                'author': 'James Dale Davidson',
                'image': 'https://m.media-amazon.com/images/I/718T+2u9GaL._SY522_.jpg',
                'url': f'https://www.amazon.com/dp/0684832720?tag={self.partner_tag}',
                'asin': '0684832720'
            }
        }
        
        return fallback_books.get(asin)
    
    def search_bitcoin_books(self, keywords: str = "bitcoin", limit: int = 10) -> List[Dict]:
        """
        Search for Bitcoin-related books on Amazon.
        
        Args:
            keywords: Search terms
            limit: Maximum results to return
            
        Returns:
            List of book dictionaries
        """
        if not self.amazon:
            return list(self._get_all_fallback_books())[:limit]
        
        try:
            search_result = self.amazon.search_products(
                keywords=keywords,
                search_index="Books",
                item_count=limit
            )
            return [{
                'title': item.title,
                'image': item.images.primary.large.url if item.images else None,
                'url': item.detail_page_url,
                'asin': item.asin
            } for item in search_result]
        except Exception as e:
            logging.error(f"Amazon search error: {e}")
            return list(self._get_all_fallback_books())[:limit]
    
    def _get_all_fallback_books(self) -> List[Dict]:
        """Returns all curated fallback books."""
        return [
            self._get_fallback_book(asin) 
            for asin in ['1119473861', '1544526474', 'B0CG83MBN9', '1999257405', 
                        '1697526349', '1098150090', '0684832720', 'B09MYXHP1Z', 'B0BTRPZTY4']
            if self._get_fallback_book(asin)
        ]


# Singleton instance
amazon_service = AmazonService()
