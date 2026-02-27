"""
ALBY LIGHTNING GATEWAY
======================
Integration with Alby for Lightning payments.
"""

import os
import sys
import json
import logging
import requests
from datetime import datetime, timezone
from typing import Dict, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AlbyGateway")


class AlbyGateway:
    def __init__(self):
        self.access_token = os.environ.get("ALBY_ACCESS_TOKEN")
        self.lightning_address = os.environ.get("LIGHTNING_ADDRESS", "protocolpulse@getalby.com")
        self.base_url = "https://api.getalby.com"
    
    @property
    def is_configured(self) -> bool:
        return bool(self.access_token or self.lightning_address)
    
    @property
    def can_create_invoices(self) -> bool:
        return bool(self.access_token)
    
    def _request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        url = f"{self.base_url}/{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        try:
            if method == "POST":
                response = requests.post(url, headers=headers, json=data, timeout=30)
            else:
                response = requests.get(url, headers=headers, timeout=30)
            return response.json()
        except Exception as e:
            logger.error(f"Alby API error: {e}")
            return {"error": str(e)}
    
    def get_balance(self) -> Dict:
        if not self.access_token:
            return {"error": "API token not configured"}
        return self._request("GET", "balance")
    
    def create_invoice(self, amount_sats: int, memo: str, metadata: Dict = None) -> Dict:
        if not self.access_token:
            return {
                "success": True,
                "manual": True,
                "lightning_address": self.lightning_address,
                "amount_sats": amount_sats,
                "memo": memo,
                "instructions": f"Send {amount_sats:,} sats to {self.lightning_address}"
            }
        
        data = {
            "amount": amount_sats,
            "description": memo,
            "metadata": metadata or {}
        }
        
        result = self._request("POST", "invoices", data)
        
        if "payment_request" in result:
            return {
                "success": True,
                "payment_request": result["payment_request"],
                "payment_hash": result["payment_hash"],
                "amount_sats": amount_sats,
                "expires_at": result.get("expires_at"),
                "qr_code_url": f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data={result['payment_request']}"
            }
        
        return {"error": result.get("error", "Unknown error"), "raw": result}
    
    def check_invoice(self, payment_hash: str) -> Dict:
        if not self.access_token:
            return {"error": "API token required"}
        result = self._request("GET", f"invoices/{payment_hash}")
        return {
            "paid": result.get("settled", False),
            "amount_sats": result.get("amount"),
            "settled_at": result.get("settled_at")
        }
    
    def generate_payment_page(self, amount_sats: int, memo: str, email: str = None) -> str:
        if self.access_token:
            invoice = self.create_invoice(amount_sats, memo, {"email": email})
            if invoice.get("success") and not invoice.get("manual"):
                payment_request = invoice["payment_request"]
                qr_url = invoice["qr_code_url"]
                return f'''<!DOCTYPE html>
<html>
<head>
    <title>Lightning Payment - Protocol Pulse</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{ background: #0d0d0d; color: #fff; font-family: -apple-system, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; padding: 20px; }}
        .container {{ background: #1a1a1a; border: 1px solid #ff3131; border-radius: 12px; padding: 32px; max-width: 400px; text-align: center; }}
        h1 {{ color: #ff3131; margin: 0 0 8px 0; font-size: 24px; }}
        .amount {{ font-size: 36px; font-weight: bold; color: #f7931a; margin: 16px 0; }}
        .qr {{ background: white; padding: 16px; border-radius: 8px; display: inline-block; margin: 16px 0; }}
        .invoice {{ background: #0d0d0d; padding: 12px; border-radius: 6px; word-break: break-all; font-family: monospace; font-size: 11px; margin: 16px 0; max-height: 80px; overflow: auto; }}
        .copy-btn {{ background: #ff3131; color: white; border: none; padding: 12px 24px; border-radius: 6px; cursor: pointer; font-size: 16px; width: 100%; }}
        .note {{ color: #888; font-size: 12px; margin-top: 16px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Lightning Payment</h1>
        <p>{memo}</p>
        <div class="amount">{amount_sats:,} sats</div>
        <div class="qr"><img src="{qr_url}" alt="QR" width="200" height="200"></div>
        <div class="invoice" id="invoice">{payment_request}</div>
        <button class="copy-btn" onclick="navigator.clipboard.writeText(document.getElementById('invoice').textContent); this.textContent='Copied!';">Copy Invoice</button>
        <p class="note">Scan with any Lightning wallet or copy the invoice.</p>
    </div>
</body>
</html>'''
        
        # Manual payment fallback
        return f'''<!DOCTYPE html>
<html>
<head>
    <title>Lightning Payment - Protocol Pulse</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{ background: #0d0d0d; color: #fff; font-family: -apple-system, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; padding: 20px; }}
        .container {{ background: #1a1a1a; border: 1px solid #ff3131; border-radius: 12px; padding: 32px; max-width: 400px; text-align: center; }}
        h1 {{ color: #ff3131; margin: 0 0 8px 0; }}
        .amount {{ font-size: 36px; font-weight: bold; color: #f7931a; margin: 16px 0; }}
        .address {{ background: #0d0d0d; padding: 16px; border-radius: 6px; font-family: monospace; margin: 16px 0; color: #f7931a; }}
        .copy-btn {{ background: #ff3131; color: white; border: none; padding: 12px 24px; border-radius: 6px; cursor: pointer; font-size: 16px; width: 100%; }}
        .note {{ color: #888; font-size: 12px; margin-top: 16px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Lightning Payment</h1>
        <p>{memo}</p>
        <div class="amount">{amount_sats:,} sats</div>
        <p>Send to this Lightning address:</p>
        <div class="address" id="address">{self.lightning_address}</div>
        <button class="copy-btn" onclick="navigator.clipboard.writeText(document.getElementById('address').textContent); this.textContent='Copied!';">Copy Address</button>
        <p class="note">After sending, email us with your payment proof.</p>
    </div>
</body>
</html>'''


if __name__ == "__main__":
    alby = AlbyGateway()
    print(f"Lightning Address: {alby.lightning_address}")
    print(f"API Token: {'CONFIGURED' if alby.access_token else 'NOT SET'}")
    print(f"Can Create Invoices: {'YES' if alby.can_create_invoices else 'NO (manual only)'}")
    
    if alby.access_token:
        print("\nTesting balance...")
        balance = alby.get_balance()
        print(f"Balance: {balance}")
        
        print("\nTesting invoice creation...")
        invoice = alby.create_invoice(100, "Test Invoice")
        print(f"Invoice: {invoice}")
