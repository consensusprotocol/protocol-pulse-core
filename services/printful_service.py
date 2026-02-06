import requests
import logging
from typing import List, Dict, Optional
import os

class PrintfulService:
    """Service for integrating with Printful API for merch store"""
    
    # Multiple store IDs - Proto P first (priority), then Consensus Protocol
    STORES = [
        {'id': '17589919', 'name': 'Proto P', 'url_base': 'https://proto-p.printful.me'},
        {'id': '13051112', 'name': 'Consensus Protocol', 'url_base': 'https://protocolpulse.printful.me'}
    ]
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.api_key = os.environ.get('PRINTFUL_API_KEY')
        self.base_url = 'https://api.printful.com'
        
        if not self.api_key:
            self.logger.warning("PRINTFUL_API_KEY not configured - merch functionality disabled")
    
    def _get_headers(self, store_id: str) -> Dict:
        """Get headers for a specific store"""
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'X-PF-Store-Id': store_id
        }
    
    def get_store_products(self) -> List[Dict]:
        """Get all products from all Printful stores (Proto P first, then Consensus Protocol)"""
        if not self.api_key:
            return []
        
        all_products = []
        
        for store in self.STORES:
            try:
                headers = self._get_headers(store['id'])
                response = requests.get(
                    f'{self.base_url}/sync/products',
                    headers=headers,
                    timeout=30
                )
                response.raise_for_status()
                
                data = response.json()
                if data.get('code') == 200:
                    products = data.get('result', [])
                    for product in products:
                        product_id = product.get('id')
                        if product_id:
                            detail = self.get_product_details(product_id, store['id'], store['url_base'])
                            if detail:
                                detail['store_name'] = store['name']
                                all_products.append(detail)
                    self.logger.info(f"Fetched {len(products)} products from {store['name']}")
                else:
                    self.logger.error(f"Printful API error for {store['name']}: {data}")
                    
            except Exception as e:
                self.logger.error(f"Error fetching products from {store['name']}: {e}")
        
        return all_products
    
    def get_product_details(self, product_id: int, store_id: str = None, url_base: str = None) -> Optional[Dict]:
        """Get detailed information for a specific product"""
        if not self.api_key:
            return None
        
        # Default to first store if not specified
        if not store_id:
            store_id = self.STORES[0]['id']
        if not url_base:
            url_base = self.STORES[0]['url_base']
        
        try:
            headers = self._get_headers(store_id)
            response = requests.get(
                f'{self.base_url}/sync/products/{product_id}',
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            if data.get('code') == 200:
                result = data.get('result')
                # Attach the store URL base for proper linking
                if result:
                    result['_store_url_base'] = url_base
                return result
            else:
                self.logger.error(f"Printful API error for product {product_id}: {data}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error fetching Printful product {product_id}: {e}")
            return None
    
    def create_order(self, order_data: Dict, store_id: str = None, confirm: bool = False) -> Optional[Dict]:
        """Create an order in Printful
        
        Args:
            order_data: Order details including recipient and items
            store_id: Which store to create order in (defaults to first store)
            confirm: If False, order is created as draft for review
        """
        if not self.api_key:
            return None
        
        if not store_id:
            store_id = self.STORES[0]['id']
        
        try:
            headers = self._get_headers(store_id)
            
            # Add confirm parameter to URL if needed
            url = f'{self.base_url}/orders'
            if confirm:
                url += '?confirm=true'
            
            response = requests.post(
                url,
                headers=headers,
                json=order_data,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            if data.get('code') in [200, 201]:
                self.logger.info(f"Printful order created: {data.get('result', {}).get('id')}")
                return data.get('result')
            else:
                self.logger.error(f"Printful order creation error: {data}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error creating Printful order: {e}")
            return None
    
    def get_variant_details(self, variant_id: int, store_id: str = None) -> Optional[Dict]:
        """Get details for a specific variant"""
        if not self.api_key:
            return None
        
        if not store_id:
            store_id = self.STORES[0]['id']
        
        try:
            headers = self._get_headers(store_id)
            response = requests.get(
                f'{self.base_url}/sync/variant/{variant_id}',
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            if data.get('code') == 200:
                return data.get('result')
            return None
        except Exception as e:
            self.logger.error(f"Error getting variant {variant_id}: {e}")
            return None
    
    def get_shipping_rates(self, recipient: Dict, items: List[Dict]) -> List[Dict]:
        """Get shipping rates for an order"""
        if not self.api_key:
            return []
        
        try:
            shipping_data = {
                'recipient': recipient,
                'items': items
            }
            
            headers = self._get_headers(self.STORES[0]['id'])
            response = requests.post(
                f'{self.base_url}/shipping/rates',
                headers=headers,
                json=shipping_data,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            if data.get('code') == 200:
                return data.get('result', [])
            else:
                self.logger.error(f"Printful shipping rates error: {data}")
                return []
                
        except Exception as e:
            self.logger.error(f"Error getting Printful shipping rates: {e}")
            return []
    
    def format_product_for_display(self, product: Dict) -> Dict:
        """Format Printful product data for website display"""
        sync_product = product.get('sync_product', {})
        sync_variants = product.get('sync_variants', [])
        store_url_base = product.get('_store_url_base', 'https://proto-p.printful.me')
        store_name = product.get('store_name', 'Proto P')
        
        # Get the main product image
        main_image = None
        if sync_variants:
            files = sync_variants[0].get('files', [])
            for file_data in files:
                if file_data.get('type') == 'preview':
                    main_image = file_data.get('preview_url')
                    break
        
        # Format variants with pricing
        variants = []
        for variant in sync_variants:
            variant_data = {
                'id': variant.get('id'),
                'name': variant.get('name', ''),
                'price': variant.get('retail_price', '0.00'),
                'currency': variant.get('currency', 'USD'),
                'size': variant.get('size', ''),
                'color': variant.get('color', ''),
                'in_stock': variant.get('availability_status') != 'out_of_stock'
            }
            variants.append(variant_data)
        
        # Construct store URL using the correct store base URL
        product_id = sync_product.get('external_id') or sync_product.get('id')
        store_url = f"{store_url_base}/product/{product_id}" if product_id else None
        
        return {
            'id': sync_product.get('id'),
            'name': sync_product.get('name', 'Product'),
            'thumbnail': sync_product.get('thumbnail_url'),
            'main_image': main_image,
            'variants': variants,
            'description': sync_product.get('description', ''),
            'tags': sync_product.get('tags', []),
            'is_ignored': sync_product.get('is_ignored', False),
            'store_url': store_url,
            'store_name': store_name
        }
    
    def create_realtime_product(
        self, 
        design_url: str, 
        statement_text: str,
        sarah_description: str = None,
        store_id: str = None
    ) -> Optional[Dict]:
        """
        Create a draft RTSA product in Printful.
        Uses the Gildan 64000 Softstyle T-Shirt (black) as base.
        
        Args:
            design_url: URL to the transparent PNG design file
            statement_text: The ethos statement for the product name
            sarah_description: Sarah's voice product description
            store_id: Target store ID (defaults to Proto P)
        
        Returns:
            Dict with created product info or None on failure
        """
        if not self.api_key:
            self.logger.error("PRINTFUL_API_KEY not configured")
            return None
        
        if not store_id:
            store_id = self.STORES[0]['id']
        
        try:
            product_name = f"RTSA: {statement_text}"
            description = sarah_description or f"Real-Time Signal Drop. {statement_text}. A physical record of network inflection. Limited availability."
            
            product_data = {
                "sync_product": {
                    "name": product_name,
                    "thumbnail": design_url
                },
                "sync_variants": [
                    {
                        "variant_id": 4012,
                        "retail_price": "35.00",
                        "files": [
                            {
                                "url": design_url,
                                "type": "front"
                            }
                        ]
                    },
                    {
                        "variant_id": 4013,
                        "retail_price": "35.00",
                        "files": [
                            {
                                "url": design_url,
                                "type": "front"
                            }
                        ]
                    },
                    {
                        "variant_id": 4014,
                        "retail_price": "35.00",
                        "files": [
                            {
                                "url": design_url,
                                "type": "front"
                            }
                        ]
                    },
                    {
                        "variant_id": 4015,
                        "retail_price": "37.00",
                        "files": [
                            {
                                "url": design_url,
                                "type": "front"
                            }
                        ]
                    },
                    {
                        "variant_id": 4016,
                        "retail_price": "37.00",
                        "files": [
                            {
                                "url": design_url,
                                "type": "front"
                            }
                        ]
                    }
                ]
            }
            
            headers = self._get_headers(store_id)
            response = requests.post(
                f'{self.base_url}/sync/products',
                headers=headers,
                json=product_data,
                timeout=60
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                if data.get('code') in [200, 201]:
                    result = data.get('result', {})
                    self.logger.info(f"RTSA product created: {result.get('id')} - {statement_text}")
                    return result
                else:
                    self.logger.error(f"Printful API error: {data}")
                    return None
            else:
                self.logger.error(f"Printful request failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error creating RTSA product: {e}")
            return None
    
    def get_catalog_variants(self, product_id: int = 71) -> List[Dict]:
        """
        Get available variants for a catalog product.
        Default product_id 71 = Gildan 64000 Softstyle T-Shirt
        """
        if not self.api_key:
            return []
        
        try:
            response = requests.get(
                f'{self.base_url}/products/{product_id}',
                headers={'Authorization': f'Bearer {self.api_key}'},
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            if data.get('code') == 200:
                result = data.get('result', {})
                variants = result.get('variants', [])
                black_variants = [
                    v for v in variants 
                    if v.get('color', '').lower() == 'black'
                ]
                return black_variants
            return []
        except Exception as e:
            self.logger.error(f"Error getting catalog variants: {e}")
            return []


printful_service = PrintfulService()