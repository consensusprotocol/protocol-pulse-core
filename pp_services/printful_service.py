"""
Protocol Pulse — Printful API v2 Service
Uses /v2/ endpoints, Bearer token auth, leaky bucket rate limiting aware.
Store: Proto P (ID: 17589919)
"""
import requests
import logging
import hashlib
import hmac
import os
import time
from typing import List, Dict, Optional
from functools import lru_cache

class PrintfulService:
    BASE_URL = 'https://api.printful.com/v2'
    BASE_URL_V1 = 'https://api.printful.com'  # fallback for unported endpoints

    # Proto P is the primary store
    PRIMARY_STORE_ID = '17589919'
    STORES = [
        {'id': '17589919', 'name': 'Proto P', 'url_base': 'https://proto-p.printful.me'},
        {'id': '13051112', 'name': 'Consensus Protocol', 'url_base': 'https://protocolpulse.printful.me'},
    ]

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.api_key = os.environ.get('PRINTFUL_API_KEY')
        self._rate_limit_reset = 0

        if not self.api_key:
            self.logger.warning('PRINTFUL_API_KEY not set — merch disabled')

    # ── Auth ──────────────────────────────────────────────────────────────────

    def _headers(self, store_id: str = None) -> Dict:
        h = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }
        sid = store_id or self.PRIMARY_STORE_ID
        if sid:
            h['X-PF-Store-Id'] = sid
        return h

    def _get(self, path: str, store_id: str = None, params: dict = None, v1: bool = False) -> Optional[Dict]:
        if not self.api_key:
            return None
        base = self.BASE_URL_V1 if v1 else self.BASE_URL
        url = f'{base}{path}'
        try:
            r = requests.get(url, headers=self._headers(store_id), params=params, timeout=10)
            # Respect leaky bucket
            remaining = int(r.headers.get('X-Ratelimit-Remaining', 120))
            if remaining < 10:
                reset = float(r.headers.get('X-Ratelimit-Reset', 1))
                time.sleep(min(reset, 2))
            if r.status_code == 429:
                retry = float(r.headers.get('Retry-After', 5))
                time.sleep(retry)
                r = requests.get(url, headers=self._headers(store_id), params=params, timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            self.logger.error('Printful GET %s: %s', path, e)
            return None

    def _post(self, path: str, payload: dict, store_id: str = None, v1: bool = False) -> Optional[Dict]:
        if not self.api_key:
            return None
        base = self.BASE_URL_V1 if v1 else self.BASE_URL
        url = f'{base}{path}'
        try:
            r = requests.post(url, headers=self._headers(store_id), json=payload, timeout=15)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            self.logger.error('Printful POST %s: %s', path, e)
            return None

    # ── Stores ────────────────────────────────────────────────────────────────

    def get_stores(self) -> List[Dict]:
        data = self._get('/stores')
        return data.get('data', []) if data else []

    # ── Products (v2 catalog + store sync) ───────────────────────────────────

    def get_store_products(self, store_id: str = None) -> List[Dict]:
        """
        Fetch sync products from store. Falls back to v1 sync endpoint since
        v2 product sync is not yet available (per Printful docs).
        """
        sid = store_id or self.PRIMARY_STORE_ID
        # v2 doesn't have sync products yet — use v1 sync endpoint
        data = self._get('/store/products', store_id=sid, params={'limit': 100}, v1=True)
        if data and data.get('code') == 200:
            return data.get('result', [])

        # Fallback: return catalog bestsellers if no sync products
        return self._get_catalog_products()

    def _get_catalog_products(self, limit: int = 20) -> List[Dict]:
        """Fetch from Printful catalog as fallback."""
        data = self._get('/catalog-products', params={
            'limit': limit,
            'sort_type': 'bestseller',
            'sort_direction': 'descending',
            'selling_region_name': 'north_america',
        })
        if not data:
            return []
        products = data.get('data', [])
        # Normalize to match sync product format
        normalized = []
        for p in products:
            normalized.append({
                'id': p.get('id'),
                'external_id': None,
                'name': p.get('name', ''),
                'synced': 1,
                'thumbnail_url': p.get('image', ''),
                'is_ignored': False,
                '_catalog': True,
                'catalog_data': p,
            })
        return normalized

    def get_product_variants(self, product_id: str, store_id: str = None) -> List[Dict]:
        """Get variants for a sync product (v1) or catalog product (v2)."""
        sid = store_id or self.PRIMARY_STORE_ID
        # Try v1 sync variants first
        data = self._get(f'/store/products/{product_id}', store_id=sid, v1=True)
        if data and data.get('code') == 200:
            result = data.get('result', {})
            return result.get('sync_variants', [])
        # Fallback to v2 catalog variants
        data = self._get(f'/catalog-products/{product_id}/catalog-variants')
        return data.get('data', []) if data else []

    def format_product_for_display(self, product: Dict) -> Dict:
        """Normalize a product dict for merch.html template."""
        is_catalog = product.get('_catalog', False)

        if is_catalog:
            cd = product.get('catalog_data', {})
            return {
                'id': product['id'],
                'name': cd.get('name', product.get('name', 'Unknown')),
                'thumbnail_url': cd.get('image', ''),
                'retail_price': None,
                'currency': 'USD',
                'variants': [],
                'sizes': cd.get('sizes', []),
                'colors': cd.get('colors', []),
                'description': cd.get('description', ''),
                'is_ignored': False,
                'type': cd.get('type', ''),
                'brand': cd.get('brand', ''),
            }

        # Standard sync product
        variants = product.get('sync_variants', [])
        prices = [float(v.get('retail_price', 0)) for v in variants if v.get('retail_price')]
        min_price = min(prices) if prices else 0

        sizes = list({v.get('size', '') for v in variants if v.get('size')})
        colors = list({v.get('color', '') for v in variants if v.get('color')})

        return {
            'id': product.get('id'),
            'external_id': product.get('external_id'),
            'name': product.get('name', 'Unknown'),
            'thumbnail_url': product.get('thumbnail_url', ''),
            'retail_price': f'{min_price:.2f}' if min_price else None,
            'currency': 'USD',
            'variants': variants,
            'sizes': sorted(sizes),
            'colors': colors,
            'description': product.get('description', ''),
            'is_ignored': product.get('is_ignored', False),
            'type': '',
            'brand': '',
        }

    # ── Orders (v2) ───────────────────────────────────────────────────────────

    def create_draft_order(self, recipient: Dict, items: List[Dict], store_id: str = None) -> Optional[Dict]:
        """
        Create a draft order via v2 API.
        items format: [{'catalog_variant_id': int, 'quantity': int, 'retail_price': str}]
        """
        sid = store_id or self.PRIMARY_STORE_ID
        order_items = []
        for item in items:
            order_items.append({
                'source': 'catalog',
                'catalog_variant_id': item['catalog_variant_id'],
                'quantity': item.get('quantity', 1),
                'retail_price': str(item.get('retail_price', '0.00')),
                'placements': [{
                    'placement': 'front',
                    'technique': 'dtg',
                    'layers': [{'type': 'file', 'url': item.get('design_url', '')}]
                }] if item.get('design_url') else [],
            })

        payload = {
            'recipient': recipient,
            'order_items': order_items,
            'customization': {
                'packing_slip': {
                    'store_name': 'Protocol Pulse',
                    'email': 'orders@protocolpulse.io',
                    'message': 'Stay sovereign. Stack sats.',
                }
            }
        }
        data = self._post('/orders', payload, store_id=sid)
        return data.get('data') if data else None

    def confirm_order(self, order_id: int, store_id: str = None) -> Optional[Dict]:
        """Confirm a draft order — triggers fulfillment and charge."""
        sid = store_id or self.PRIMARY_STORE_ID
        data = self._post(f'/orders/{order_id}/confirmation', {}, store_id=sid)
        return data.get('data') if data else None

    def get_order(self, order_id: int, store_id: str = None) -> Optional[Dict]:
        sid = store_id or self.PRIMARY_STORE_ID
        data = self._get(f'/orders/{order_id}', store_id=sid)
        return data.get('data') if data else None

    def estimate_shipping(self, recipient: Dict, items: List[Dict], store_id: str = None) -> List[Dict]:
        """Get shipping rate options for a cart."""
        sid = store_id or self.PRIMARY_STORE_ID
        order_items = [{'catalog_variant_id': i['catalog_variant_id'], 'quantity': i.get('quantity', 1)} for i in items]
        payload = {'recipient': recipient, 'order_items': order_items, 'currency': 'USD'}
        data = self._post('/shipping-rates', payload, store_id=sid)
        return data.get('data', []) if data else []

    # ── Webhook verification (v2 HMAC-SHA256) ─────────────────────────────────

    def verify_webhook(self, payload_bytes: bytes, signature_hex: str, secret_key_hex: str) -> bool:
        """
        Verify Printful v2 webhook signature.
        secret_key_hex is the hex-encoded secret from webhook setup.
        """
        try:
            secret_bytes = bytes.fromhex(secret_key_hex)
            expected = hmac.new(secret_bytes, payload_bytes, hashlib.sha256).hexdigest()
            return hmac.compare_digest(expected, signature_hex)
        except Exception as e:
            self.logger.error('Webhook verification error: %s', e)
            return False

    # ── Register webhooks (v2) ─────────────────────────────────────────────────

    def setup_webhooks(self, webhook_url: str, store_id: str = None) -> Optional[Dict]:
        """Register order + shipment webhooks pointing to our Flask endpoint."""
        sid = store_id or self.PRIMARY_STORE_ID
        payload = {
            'default_url': webhook_url,
            'events': [
                {'type': 'order_created'},
                {'type': 'order_updated'},
                {'type': 'order_failed'},
                {'type': 'shipment_sent'},
                {'type': 'shipment_delivered'},
            ]
        }
        data = self._post('/webhooks', payload, store_id=sid)
        return data.get('result') if data else None

    # ── Catalog prices ─────────────────────────────────────────────────────────

    def get_variant_price(self, variant_id: int, currency: str = 'USD') -> Optional[Dict]:
        data = self._get(f'/catalog-variants/{variant_id}/prices', params={'currency': currency})
        return data.get('data') if data else None
