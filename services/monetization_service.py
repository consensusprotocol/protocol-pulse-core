"""
Monetization Service for Protocol Pulse
Handles Stripe integration for premium subscriptions, donations, and affiliate tracking
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import json

try:
    import stripe
    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False
    logging.warning("Stripe not installed - monetization features limited")

class MonetizationService:
    """Service for handling payments, subscriptions, and revenue tracking"""

    SUBSCRIPTION_TIERS = {
        'free': {
            'name': 'Free Intel',
            'price_monthly': 0,
            'features': [
                'Daily intelligence briefings',
                'Basic article access',
                'Public podcast episodes',
                'Community access'
            ]
        },
        'operator': {
            'name': 'Pulse Operator',
            'price_monthly': 21,
            'price_id': None,
            'features': [
                'All Free features',
                'Priority intel alerts',
                'Exclusive deep-dive reports',
                'Early access to content',
                'Ad-free experience',
                'Discord/Telegram access',
                'Weekly strategy calls'
            ]
        },
        'commander': {
            'name': 'Pulse Commander',
            'price_monthly': 99,
            'price_id': None,
            'features': [
                'All Operator features',
                'Live X Spaces feed & alerts',
                'Pro Brief (early + extra signals)',
                'Weekly exclusive reports',
                'Whale watcher alerts',
                'Signal Terminal Pro view',
                'Private Commander community',
                'One monthly "ask" (Q&A)'
            ]
        },
        'sovereign': {
            'name': 'Sovereign Elite',
            'price_monthly': 210,
            'price_id': None,
            'features': [
                'All Commander features',
                '1-on-1 monthly strategy session',
                'Custom research requests',
                'Private Signal group',
                'Early investment opportunities',
                'Lifetime protocol access',
                'Name in credits'
            ]
        }
    }

    def __init__(self):
        self.stripe_key = os.environ.get('STRIPE_SECRET_KEY')
        self.stripe_webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')
        self.initialized = False

        if STRIPE_AVAILABLE and self.stripe_key:
            stripe.api_key = self.stripe_key
            self.initialized = True
            logging.info("Stripe monetization service initialized")
        else:
            logging.warning("Stripe not configured - using simulation mode")

    def get_subscription_tiers(self) -> Dict:
        """Return available subscription tiers"""
        return self.SUBSCRIPTION_TIERS

    def create_checkout_session(self, tier: str, user_email: str,
                                 success_url: str, cancel_url: str) -> Dict:
        """Create a Stripe checkout session for subscription"""
        if tier not in ['operator', 'commander', 'sovereign']:
            return {'error': 'Invalid tier'}

        tier_info = self.SUBSCRIPTION_TIERS[tier]

        if not self.initialized:
            return {
                'simulated': True,
                'checkout_url': f"{success_url}?session_id=sim_session_{tier}",
                'tier': tier,
                'message': 'Stripe not configured - simulation mode'
            }

        try:
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': tier_info['name'],
                            'description': f"Protocol Pulse {tier_info['name']} Subscription"
                        },
                        'unit_amount': tier_info['price_monthly'] * 100,
                        'recurring': {'interval': 'month'}
                    },
                    'quantity': 1
                }],
                mode='subscription',
                customer_email=user_email,
                success_url=success_url + '?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=cancel_url,
                metadata={
                    'tier': tier,
                    'source': 'protocol_pulse'
                }
            )

            return {
                'success': True,
                'checkout_url': session.url,
                'session_id': session.id
            }

        except Exception as e:
            logging.error(f"Stripe checkout error: {e}")
            return {'error': str(e)}

    def create_donation_session(self, amount_usd: int, donor_email: str,
                                 success_url: str, cancel_url: str,
                                 message: str = '', article_id: Optional[str] = None) -> Dict:
        """Create a one-time donation payment session"""
        if not self.initialized:
            return {
                'simulated': True,
                'checkout_url': f"{success_url}?donation=sim_{amount_usd}",
                'amount': amount_usd,
                'message': 'Stripe not configured - simulation mode'
            }

        metadata = {
            'type': 'donation',
            'message': message[:500] if message else '',
            'source': 'protocol_pulse'
        }
        if article_id:
            metadata['article_id'] = str(article_id)

        try:
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': 'Protocol Pulse Support',
                            'description': 'One-time contribution to support sovereign journalism'
                        },
                        'unit_amount': amount_usd * 100
                    },
                    'quantity': 1
                }],
                mode='payment',
                customer_email=donor_email,
                success_url=success_url + '?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=cancel_url,
                metadata=metadata
            )

            return {
                'success': True,
                'checkout_url': session.url,
                'session_id': session.id
            }

        except Exception as e:
            logging.error(f"Stripe donation error: {e}")
            return {'error': str(e)}

    def handle_webhook(self, payload: bytes, sig_header: str) -> Dict:
        """Handle Stripe webhook events"""
        if not self.initialized or not self.stripe_webhook_secret:
            return {'error': 'Webhook not configured'}

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, self.stripe_webhook_secret
            )

            if event['type'] == 'checkout.session.completed':
                session = event['data']['object']
                return self._handle_checkout_complete(session)

            elif event['type'] == 'customer.subscription.updated':
                subscription = event['data']['object']
                return self._handle_subscription_update(subscription)

            elif event['type'] == 'customer.subscription.deleted':
                subscription = event['data']['object']
                return self._handle_subscription_cancel(subscription)

            elif event['type'] == 'invoice.payment_failed':
                invoice = event['data']['object']
                return self._handle_payment_failed(invoice)

            return {'success': True, 'event_type': event['type']}

        except stripe.error.SignatureVerificationError as e:
            logging.error(f"Webhook signature verification failed: {e}")
            return {'error': 'Invalid signature'}
        except Exception as e:
            logging.error(f"Webhook processing error: {e}")
            return {'error': str(e)}

    def _handle_checkout_complete(self, session: Dict) -> Dict:
        """Process completed checkout"""
        customer_email = session.get('customer_email')
        metadata = session.get('metadata', {})
        tier = metadata.get('tier')

        logging.info(f"Checkout complete: {customer_email} - {tier}")

        return {
            'success': True,
            'action': 'subscription_created',
            'email': customer_email,
            'tier': tier
        }

    def _handle_subscription_update(self, subscription: Dict) -> Dict:
        """Handle subscription updates"""
        logging.info(f"Subscription updated: {subscription.get('id')}")
        return {'success': True, 'action': 'subscription_updated'}

    def _handle_subscription_cancel(self, subscription: Dict) -> Dict:
        """Handle subscription cancellation"""
        logging.info(f"Subscription cancelled: {subscription.get('id')}")
        return {'success': True, 'action': 'subscription_cancelled'}

    def _handle_payment_failed(self, invoice: Dict) -> Dict:
        """Handle failed payment"""
        logging.warning(f"Payment failed for invoice: {invoice.get('id')}")
        return {'success': True, 'action': 'payment_failed'}

    def get_revenue_stats(self) -> Dict:
        """Get revenue statistics (simulated if Stripe not available)"""
        if not self.initialized:
            return {
                'mrr': 0,
                'subscribers': {
                    'operator': 0,
                    'commander': 0,
                    'sovereign': 0
                },
                'total_donations': 0,
                'affiliate_earnings': 0,
                'zaps_sats': 0,
                'simulated': True
            }

        try:
            subscriptions = stripe.Subscription.list(limit=100, status='active')

            operator_count = 0
            commander_count = 0
            sovereign_count = 0
            mrr = 0

            for sub in subscriptions.data:
                amount = sub.plan.amount / 100
                if amount <= 50:
                    operator_count += 1
                elif amount <= 150:
                    commander_count += 1
                else:
                    sovereign_count += 1
                mrr += amount

            return {
                'mrr': mrr,
                'subscribers': {
                    'operator': operator_count,
                    'commander': commander_count,
                    'sovereign': sovereign_count
                },
                'total_donations': 0,
                'affiliate_earnings': 0,
                'zaps_sats': 0,
                'simulated': False
            }

        except Exception as e:
            logging.error(f"Error fetching revenue stats: {e}")
            return {
                'mrr': 0,
                'subscribers': {'operator': 0, 'commander': 0, 'sovereign': 0},
                'error': str(e)
            }

    def generate_affiliate_link(self, product_type: str, product_id: str,
                                 user_id: Optional[int] = None) -> str:
        """Generate an affiliate tracking link"""
        base_urls = {
            'amazon_book': 'https://www.amazon.com/dp/',
            'amazon': 'https://www.amazon.com/dp/',
            'trezor': 'https://shop.trezor.io/?offer_id=',
            'cold_wallet': 'https://shop.trezor.io/?offer_id=',
            'swan': 'https://www.swanbitcoin.com/signup?ref=',
            'river': 'https://river.com/signup?ref='
        }

        base = base_urls.get(product_type, '')
        if not base:
            return ''

        affiliate_tag = os.environ.get('AMAZON_AFFILIATE_TAG', 'protocolpulse-20')

        if product_type in ('amazon_book', 'amazon'):
            return f"{base}{product_id}?tag={affiliate_tag}"
        return f"{base}{product_id}" if base else ''

    def track_affiliate_click(self, link_type: str, product_id: str,
                               user_id: Optional[int] = None) -> bool:
        """Track an affiliate link click"""
        logging.info(f"Affiliate click: {link_type} - {product_id}")
        return True

    def get_lightning_invoice(self, amount_sats: int, memo: str = '') -> Dict:
        """Generate a Lightning invoice for zap payments"""
        lnurl = os.environ.get('LIGHTNING_ADDRESS', '')

        if not lnurl:
            return {
                'simulated': True,
                'invoice': 'lnbc10u1pj...(simulated)',
                'amount_sats': amount_sats,
                'message': 'Lightning not configured'
            }

        return {
            'lightning_address': lnurl,
            'amount_sats': amount_sats,
            'memo': memo
        }


monetization_service = MonetizationService()
