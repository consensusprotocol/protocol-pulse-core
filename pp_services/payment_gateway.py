"""
PAYMENT GATEWAY - Bitcoin + Card Payments
==========================================
Handles premium subscriptions with multiple payment methods.

SUPPORTED METHODS:
1. Bitcoin (on-chain) - via BTCPay Server or manual
2. Lightning Network - via Strike API, LNBits, or BTCPay
3. Credit/Debit Cards - via Stripe

FLOW:
1. User selects tier and payment method
2. Generate invoice (BTC/LN) or redirect (Stripe)
3. On payment confirmation, upgrade subscriber
4. Send confirmation email/telegram

SETUP:
- STRIPE_SECRET_KEY: For card payments
- BTCPAY_URL: BTCPay Server URL (optional)
- BTCPAY_API_KEY: BTCPay API key (optional)
- STRIKE_API_KEY: Strike API for Lightning (optional)
- LNBITS_URL: LNBits instance URL (optional)
- LNBITS_API_KEY: LNBits invoice key (optional)
"""

import os
import sys
import json
import logging
import requests
import hashlib
import hmac
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

# Add services to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from premium_tier import SubscriberManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PaymentGateway")


# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class PricingConfig:
    """Pricing configuration for subscriptions."""
    # Monthly prices in USD
    monthly_usd: float = 21.00
    yearly_usd: float = 199.00
    lifetime_usd: float = 499.00
    
    # Bitcoin prices (calculated from USD at checkout)
    # Or set fixed sats prices
    monthly_sats: int = 21000  # ~$21 at $100k/BTC
    yearly_sats: int = 199000
    lifetime_sats: int = 499000


PRICING = PricingConfig()


# ============================================================================
# INVOICE STORAGE
# ============================================================================

class InvoiceManager:
    """
    Manages payment invoices.
    Tracks pending, paid, and expired invoices.
    """
    
    def __init__(self):
        self.invoices_file = "data/invoices.json"
        self._ensure_file()
    
    def _ensure_file(self):
        """Ensure invoices file exists."""
        os.makedirs("data", exist_ok=True)
        if not os.path.exists(self.invoices_file):
            self._save_data({"invoices": []})
    
    def _load_data(self) -> Dict:
        try:
            with open(self.invoices_file) as f:
                return json.load(f)
        except:
            return {"invoices": []}
    
    def _save_data(self, data: Dict):
        with open(self.invoices_file, "w") as f:
            json.dump(data, f, indent=2, default=str)
    
    def create_invoice(
        self,
        email: str,
        amount_usd: float,
        amount_sats: int,
        plan: str,
        payment_method: str,
        external_id: str = None,
        payment_address: str = None,
        lightning_invoice: str = None,
        expires_at: str = None
    ) -> Dict:
        """Create a new invoice."""
        data = self._load_data()
        
        invoice_id = hashlib.sha256(
            f"{email}{time.time()}{amount_usd}".encode()
        ).hexdigest()[:16]
        
        invoice = {
            "id": invoice_id,
            "email": email,
            "amount_usd": amount_usd,
            "amount_sats": amount_sats,
            "plan": plan,
            "payment_method": payment_method,
            "status": "pending",
            "external_id": external_id,
            "payment_address": payment_address,
            "lightning_invoice": lightning_invoice,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": expires_at or (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            "paid_at": None
        }
        
        data["invoices"].append(invoice)
        self._save_data(data)
        
        return invoice
    
    def get_invoice(self, invoice_id: str) -> Optional[Dict]:
        """Get invoice by ID."""
        data = self._load_data()
        for inv in data["invoices"]:
            if inv["id"] == invoice_id:
                return inv
        return None
    
    def mark_paid(self, invoice_id: str, transaction_id: str = None) -> bool:
        """Mark invoice as paid."""
        data = self._load_data()
        for inv in data["invoices"]:
            if inv["id"] == invoice_id:
                inv["status"] = "paid"
                inv["paid_at"] = datetime.now(timezone.utc).isoformat()
                inv["transaction_id"] = transaction_id
                self._save_data(data)
                return True
        return False
    
    def get_pending_invoices(self) -> List[Dict]:
        """Get all pending invoices."""
        data = self._load_data()
        return [inv for inv in data["invoices"] if inv["status"] == "pending"]
    
    def cleanup_expired(self) -> int:
        """Mark expired invoices."""
        data = self._load_data()
        now = datetime.now(timezone.utc)
        count = 0
        
        for inv in data["invoices"]:
            if inv["status"] == "pending":
                expires = datetime.fromisoformat(inv["expires_at"].replace('Z', '+00:00'))
                if now > expires:
                    inv["status"] = "expired"
                    count += 1
        
        if count > 0:
            self._save_data(data)
        
        return count


# ============================================================================
# STRIPE INTEGRATION (Cards)
# ============================================================================

class StripeGateway:
    """
    Stripe payment gateway for card payments.
    """
    
    def __init__(self):
        self.api_key = os.environ.get("STRIPE_SECRET_KEY")
        self.base_url = "https://api.stripe.com/v1"
        self.webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET")
    
    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)
    
    def _request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """Make Stripe API request."""
        url = f"{self.base_url}/{endpoint}"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        if method == "POST":
            response = requests.post(url, headers=headers, data=data, timeout=30)
        else:
            response = requests.get(url, headers=headers, params=data, timeout=30)
        
        return response.json()
    
    def create_checkout_session(
        self,
        email: str,
        plan: str,
        success_url: str,
        cancel_url: str
    ) -> Dict:
        """Create Stripe Checkout session."""
        if not self.is_configured:
            return {"error": "Stripe not configured"}
        
        # Get price based on plan
        if plan == "monthly":
            amount = int(PRICING.monthly_usd * 100)  # Cents
            description = "Protocol Pulse Premium - Monthly"
        elif plan == "yearly":
            amount = int(PRICING.yearly_usd * 100)
            description = "Protocol Pulse Premium - Yearly"
        else:
            amount = int(PRICING.lifetime_usd * 100)
            description = "Protocol Pulse Premium - Lifetime"
        
        data = {
            "payment_method_types[]": "card",
            "line_items[0][price_data][currency]": "usd",
            "line_items[0][price_data][unit_amount]": amount,
            "line_items[0][price_data][product_data][name]": description,
            "line_items[0][quantity]": 1,
            "mode": "payment",
            "success_url": success_url,
            "cancel_url": cancel_url,
            "customer_email": email,
            "metadata[email]": email,
            "metadata[plan]": plan
        }
        
        result = self._request("POST", "checkout/sessions", data)
        
        if "url" in result:
            return {
                "success": True,
                "checkout_url": result["url"],
                "session_id": result["id"]
            }
        
        return {"error": result.get("error", {}).get("message", "Unknown error")}
    
    def verify_webhook(self, payload: bytes, signature: str) -> Optional[Dict]:
        """Verify Stripe webhook signature."""
        if not self.webhook_secret:
            return None
        
        try:
            # Simplified verification - in production use stripe library
            timestamp, sig = signature.split(",")[0].split("=")[1], signature.split(",")[1].split("=")[1]
            signed_payload = f"{timestamp}.{payload.decode()}"
            expected = hmac.new(
                self.webhook_secret.encode(),
                signed_payload.encode(),
                hashlib.sha256
            ).hexdigest()
            
            if hmac.compare_digest(expected, sig):
                return json.loads(payload)
        except:
            pass
        
        return None


# ============================================================================
# LIGHTNING INTEGRATION (via LNBits or Strike)
# ============================================================================

class LightningGateway:
    """
    Lightning Network payment gateway.
    Supports LNBits, Strike, or generic LNURL.
    """
    
    def __init__(self):
        # LNBits config
        self.lnbits_url = os.environ.get("LNBITS_URL")
        self.lnbits_key = os.environ.get("LNBITS_API_KEY")
        
        # Strike config
        self.strike_key = os.environ.get("STRIKE_API_KEY")
        
        # Generic Lightning address
        self.lightning_address = os.environ.get("LIGHTNING_ADDRESS")
    
    @property
    def is_configured(self) -> bool:
        return bool(self.lnbits_url or self.strike_key or self.lightning_address)
    
    def create_lnbits_invoice(self, amount_sats: int, memo: str) -> Optional[Dict]:
        """Create invoice via LNBits."""
        if not self.lnbits_url or not self.lnbits_key:
            return None
        
        try:
            response = requests.post(
                f"{self.lnbits_url}/api/v1/payments",
                headers={
                    "X-Api-Key": self.lnbits_key,
                    "Content-Type": "application/json"
                },
                json={
                    "out": False,
                    "amount": amount_sats,
                    "memo": memo
                },
                timeout=30
            )
            
            data = response.json()
            
            if "payment_request" in data:
                return {
                    "success": True,
                    "payment_request": data["payment_request"],
                    "payment_hash": data["payment_hash"],
                    "checking_id": data.get("checking_id")
                }
        except Exception as e:
            logger.error(f"LNBits error: {e}")
        
        return None
    
    def check_lnbits_payment(self, payment_hash: str) -> bool:
        """Check if LNBits payment is complete."""
        if not self.lnbits_url or not self.lnbits_key:
            return False
        
        try:
            response = requests.get(
                f"{self.lnbits_url}/api/v1/payments/{payment_hash}",
                headers={"X-Api-Key": self.lnbits_key},
                timeout=30
            )
            
            data = response.json()
            return data.get("paid", False)
        except:
            return False
    
    def create_invoice(self, amount_sats: int, memo: str) -> Dict:
        """Create Lightning invoice using available provider."""
        if self.lnbits_url:
            result = self.create_lnbits_invoice(amount_sats, memo)
            if result:
                return result
        
        # Fallback: return Lightning address for manual payment
        if self.lightning_address:
            return {
                "success": True,
                "lightning_address": self.lightning_address,
                "amount_sats": amount_sats,
                "memo": memo,
                "manual": True
            }
        
        return {"error": "Lightning not configured"}


# ============================================================================
# BITCOIN ON-CHAIN
# ============================================================================

class BitcoinGateway:
    """
    Bitcoin on-chain payment gateway.
    Uses BTCPay Server or provides static address.
    """
    
    def __init__(self):
        self.btcpay_url = os.environ.get("BTCPAY_URL")
        self.btcpay_key = os.environ.get("BTCPAY_API_KEY")
        self.btcpay_store = os.environ.get("BTCPAY_STORE_ID")
        
        # Static fallback address
        self.static_address = os.environ.get("BTC_ADDRESS")
    
    @property
    def is_configured(self) -> bool:
        return bool(self.btcpay_url or self.static_address)
    
    def create_btcpay_invoice(
        self,
        amount_usd: float,
        email: str,
        plan: str
    ) -> Optional[Dict]:
        """Create BTCPay Server invoice."""
        if not self.btcpay_url or not self.btcpay_key or not self.btcpay_store:
            return None
        
        try:
            response = requests.post(
                f"{self.btcpay_url}/api/v1/stores/{self.btcpay_store}/invoices",
                headers={
                    "Authorization": f"token {self.btcpay_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "amount": amount_usd,
                    "currency": "USD",
                    "metadata": {
                        "email": email,
                        "plan": plan
                    },
                    "checkout": {
                        "speedPolicy": "MediumSpeed"
                    }
                },
                timeout=30
            )
            
            data = response.json()
            
            if "id" in data:
                return {
                    "success": True,
                    "invoice_id": data["id"],
                    "checkout_url": data.get("checkoutLink"),
                    "amount_btc": data.get("amount"),
                    "address": data.get("cryptoInfo", [{}])[0].get("address")
                }
        except Exception as e:
            logger.error(f"BTCPay error: {e}")
        
        return None
    
    def create_invoice(self, amount_usd: float, email: str, plan: str) -> Dict:
        """Create Bitcoin invoice."""
        if self.btcpay_url:
            result = self.create_btcpay_invoice(amount_usd, email, plan)
            if result:
                return result
        
        # Fallback: static address
        if self.static_address:
            # Calculate BTC amount (would need price feed in production)
            return {
                "success": True,
                "address": self.static_address,
                "amount_usd": amount_usd,
                "manual": True,
                "instructions": f"Send ${amount_usd} worth of BTC to: {self.static_address}"
            }
        
        return {"error": "Bitcoin payments not configured"}


# ============================================================================
# UNIFIED PAYMENT GATEWAY
# ============================================================================

class PaymentGateway:
    """
    Unified payment gateway supporting multiple methods.
    """
    
    def __init__(self):
        self.stripe = StripeGateway()
        self.lightning = LightningGateway()
        self.bitcoin = BitcoinGateway()
        self.invoices = InvoiceManager()
        self.subscribers = SubscriberManager()
    
    def get_available_methods(self) -> List[str]:
        """Get list of available payment methods."""
        methods = []
        if self.stripe.is_configured:
            methods.append("card")
        if self.lightning.is_configured:
            methods.append("lightning")
        if self.bitcoin.is_configured:
            methods.append("bitcoin")
        return methods
    
    def get_pricing(self) -> Dict:
        """Get current pricing."""
        return {
            "monthly": {
                "usd": PRICING.monthly_usd,
                "sats": PRICING.monthly_sats
            },
            "yearly": {
                "usd": PRICING.yearly_usd,
                "sats": PRICING.yearly_sats
            },
            "lifetime": {
                "usd": PRICING.lifetime_usd,
                "sats": PRICING.lifetime_sats
            }
        }
    
    def create_checkout(
        self,
        email: str,
        plan: str,
        payment_method: str,
        success_url: str = None,
        cancel_url: str = None
    ) -> Dict:
        """
        Create checkout for any payment method.
        
        Args:
            email: Customer email
            plan: monthly, yearly, or lifetime
            payment_method: card, lightning, or bitcoin
            success_url: Redirect URL after successful payment (for Stripe)
            cancel_url: Redirect URL if cancelled (for Stripe)
        
        Returns:
            Dict with checkout details
        """
        # Get amounts
        pricing = self.get_pricing()
        if plan not in pricing:
            return {"error": f"Invalid plan: {plan}"}
        
        amount_usd = pricing[plan]["usd"]
        amount_sats = pricing[plan]["sats"]
        
        # Create checkout based on method
        if payment_method == "card":
            if not self.stripe.is_configured:
                return {"error": "Card payments not configured"}
            
            result = self.stripe.create_checkout_session(
                email=email,
                plan=plan,
                success_url=success_url or "https://protocolpulse.io/success",
                cancel_url=cancel_url or "https://protocolpulse.io/cancel"
            )
            
            if "checkout_url" in result:
                # Create invoice record
                invoice = self.invoices.create_invoice(
                    email=email,
                    amount_usd=amount_usd,
                    amount_sats=amount_sats,
                    plan=plan,
                    payment_method="card",
                    external_id=result.get("session_id")
                )
                result["invoice_id"] = invoice["id"]
            
            return result
        
        elif payment_method == "lightning":
            if not self.lightning.is_configured:
                return {"error": "Lightning payments not configured"}
            
            memo = f"Protocol Pulse Premium - {plan.title()}"
            result = self.lightning.create_invoice(amount_sats, memo)
            
            if result.get("success"):
                invoice = self.invoices.create_invoice(
                    email=email,
                    amount_usd=amount_usd,
                    amount_sats=amount_sats,
                    plan=plan,
                    payment_method="lightning",
                    lightning_invoice=result.get("payment_request"),
                    external_id=result.get("payment_hash")
                )
                result["invoice_id"] = invoice["id"]
            
            return result
        
        elif payment_method == "bitcoin":
            if not self.bitcoin.is_configured:
                return {"error": "Bitcoin payments not configured"}
            
            result = self.bitcoin.create_invoice(amount_usd, email, plan)
            
            if result.get("success"):
                invoice = self.invoices.create_invoice(
                    email=email,
                    amount_usd=amount_usd,
                    amount_sats=amount_sats,
                    plan=plan,
                    payment_method="bitcoin",
                    payment_address=result.get("address"),
                    external_id=result.get("invoice_id")
                )
                result["invoice_id"] = invoice["id"]
            
            return result
        
        return {"error": f"Unknown payment method: {payment_method}"}
    
    def confirm_payment(self, invoice_id: str, transaction_id: str = None) -> bool:
        """
        Confirm payment and upgrade subscriber.
        Called by webhook or manual confirmation.
        """
        invoice = self.invoices.get_invoice(invoice_id)
        if not invoice:
            logger.error(f"Invoice not found: {invoice_id}")
            return False
        
        if invoice["status"] == "paid":
            logger.info(f"Invoice already paid: {invoice_id}")
            return True
        
        # Mark invoice as paid
        self.invoices.mark_paid(invoice_id, transaction_id)
        
        # Upgrade subscriber
        self.subscribers.upgrade_to_premium(invoice["email"])
        
        logger.info(f"Payment confirmed for {invoice['email']}, plan: {invoice['plan']}")
        
        return True
    
    def print_status(self):
        """Print payment gateway status."""
        methods = self.get_available_methods()
        pricing = self.get_pricing()
        
        print("""
======================================================================
                    PAYMENT GATEWAY STATUS                             
======================================================================
""")
        print("AVAILABLE PAYMENT METHODS:")
        if "card" in methods:
            print("  [x] Credit/Debit Cards (Stripe)")
        else:
            print("  [ ] Credit/Debit Cards - Set STRIPE_SECRET_KEY")
        
        if "lightning" in methods:
            print("  [x] Lightning Network")
        else:
            print("  [ ] Lightning Network - Set LNBITS_URL or LIGHTNING_ADDRESS")
        
        if "bitcoin" in methods:
            print("  [x] Bitcoin On-chain")
        else:
            print("  [ ] Bitcoin On-chain - Set BTCPAY_URL or BTC_ADDRESS")
        
        print()
        print("PRICING:")
        print(f"  Monthly:  ${pricing['monthly']['usd']:.2f} / {pricing['monthly']['sats']:,} sats")
        print(f"  Yearly:   ${pricing['yearly']['usd']:.2f} / {pricing['yearly']['sats']:,} sats")
        print(f"  Lifetime: ${pricing['lifetime']['usd']:.2f} / {pricing['lifetime']['sats']:,} sats")
        
        print()
        pending = self.invoices.get_pending_invoices()
        print(f"PENDING INVOICES: {len(pending)}")
        
        print()
        print("======================================================================")


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    gateway = PaymentGateway()
    
    if len(sys.argv) < 2:
        gateway.print_status()
        print("""
COMMANDS:
  status                          - Show gateway status
  checkout <email> <plan> <method> - Create checkout
  confirm <invoice_id>            - Confirm payment manually
  pending                         - List pending invoices
  pricing                         - Show pricing

EXAMPLES:
  python3 payment_gateway.py checkout user@email.com monthly lightning
  python3 payment_gateway.py confirm abc123def456
""")
        sys.exit(0)
    
    cmd = sys.argv[1]
    
    if cmd == "status":
        gateway.print_status()
    
    elif cmd == "checkout":
        if len(sys.argv) < 5:
            print("Usage: checkout <email> <plan> <method>")
            print("  plan: monthly, yearly, lifetime")
            print("  method: card, lightning, bitcoin")
            sys.exit(1)
        
        email = sys.argv[2]
        plan = sys.argv[3]
        method = sys.argv[4]
        
        result = gateway.create_checkout(email, plan, method)
        print(json.dumps(result, indent=2))
    
    elif cmd == "confirm":
        if len(sys.argv) < 3:
            print("Usage: confirm <invoice_id>")
            sys.exit(1)
        
        invoice_id = sys.argv[2]
        if gateway.confirm_payment(invoice_id):
            print(f"SUCCESS: Payment confirmed for invoice {invoice_id}")
        else:
            print(f"ERROR: Could not confirm invoice {invoice_id}")
    
    elif cmd == "pending":
        pending = gateway.invoices.get_pending_invoices()
        if pending:
            print(f"\nPending invoices: {len(pending)}\n")
            for inv in pending:
                print(f"  {inv['id']}: {inv['email']} - {inv['plan']} ({inv['payment_method']})")
        else:
            print("No pending invoices")
    
    elif cmd == "pricing":
        pricing = gateway.get_pricing()
        print(json.dumps(pricing, indent=2))
    
    else:
        print(f"Unknown command: {cmd}")
