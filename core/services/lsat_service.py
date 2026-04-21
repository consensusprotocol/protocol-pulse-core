"""
lsat_service.py — Lightning Service Authentication Tokens (LSAT) for Protocol Pulse.

Bitcoin-native API monetization:
- Unauthenticated requests receive HTTP 402 + a Lightning invoice.
- Caller pays the invoice with any wallet and retrieves the preimage.
- Subsequent requests present `Authorization: LSAT <token_id>:<preimage>` and
  the service verifies `sha256(preimage) == payment_hash`.

Bearer JWT fallthrough is preserved so existing Commander subscribers keep
working without having to pay an invoice per call.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import secrets
import sqlite3
import time
from functools import wraps
from typing import Optional, Tuple

import requests
from flask import jsonify, request

logger = logging.getLogger(__name__)


# ── Configuration ──────────────────────────────────────────────────────────

_PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
LSAT_DB = os.environ.get(
    "LSAT_DB",
    os.path.join(_PROJECT_ROOT, "data", "lsat_tokens.db"),
)

LIGHTNING_ADDRESS = os.environ.get("LIGHTNING_ADDRESS", "protocolpulse@getalby.com")

# Price sheet: msats per call, token TTL after payment (seconds).
ENDPOINT_PRICING = {
    "/v1/signals/live":         {"msats": 1000, "ttl": 3600,  "description": "10 latest BTC signals"},
    "/api/intelligence/signal": {"msats": 500,  "ttl": 1800,  "description": "Composite signal score"},
    "/api/orb":                 {"msats": 100,  "ttl": 900,   "description": "Sovereign Orb snapshot"},
    "/api/hub/intel":           {"msats": 2000, "ttl": 86400, "description": "Full intelligence hub"},
}


# ── DB ──────────────────────────────────────────────────────────────────────

def _init_db() -> None:
    """Create lsat_tokens table (idempotent)."""
    os.makedirs(os.path.dirname(LSAT_DB), exist_ok=True)
    with sqlite3.connect(LSAT_DB) as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS lsat_tokens (
                token_id       TEXT PRIMARY KEY,
                payment_hash   TEXT NOT NULL,
                amount_msats   INTEGER NOT NULL,
                endpoint       TEXT NOT NULL,
                status         TEXT NOT NULL DEFAULT 'pending',
                created_at     INTEGER NOT NULL,
                expires_at     INTEGER NOT NULL,
                preimage       TEXT,
                uses_remaining INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        db.execute("CREATE INDEX IF NOT EXISTS idx_lsat_payment_hash ON lsat_tokens(payment_hash)")
        db.commit()


_init_db()


# ── LNURL-pay resolution ───────────────────────────────────────────────────

def _lnurl_pay_endpoint(addr: str) -> str:
    """
    Resolve a Lightning address (user@domain) to its LNURL-pay callback URL.
    Hits https://{domain}/.well-known/lnurlp/{user} and returns the `callback` field.
    """
    if "@" not in addr:
        raise ValueError(f"Invalid lightning address: {addr}")
    user, domain = addr.split("@", 1)
    url = f"https://{domain}/.well-known/lnurlp/{user}"
    r = requests.get(url, timeout=8)
    r.raise_for_status()
    data = r.json()
    callback = data.get("callback")
    if not callback:
        raise RuntimeError(f"LNURL-pay response missing callback field: {data}")
    return callback


# ── Invoice creation ────────────────────────────────────────────────────────

def _extract_payment_hash(bolt11_str: str) -> str:
    """Decode a BOLT11 invoice and return the hex payment_hash."""
    import bolt11 as _bolt11
    decoded = _bolt11.decode(bolt11_str)
    # The bolt11 library exposes `.payment_hash` as hex str.
    ph = getattr(decoded, "payment_hash", None)
    if not ph:
        raise RuntimeError("Unable to extract payment_hash from invoice")
    return ph


def create_invoice(endpoint: str, amount_msats: int, ttl_seconds: int) -> dict:
    """
    Hit the configured Lightning address LNURL callback, receive a BOLT11
    invoice, persist a pending token row, and return the token payload.
    """
    callback = _lnurl_pay_endpoint(LIGHTNING_ADDRESS)
    sep = "&" if "?" in callback else "?"
    pay_url = f"{callback}{sep}amount={amount_msats}"
    r = requests.get(pay_url, timeout=10)
    try:
        payload = r.json()
    except ValueError:
        r.raise_for_status()
        raise RuntimeError(f"LNURL callback returned non-JSON body (status={r.status_code})")
    # LNURL convention: {"status":"ERROR","reason":"..."} may arrive with any HTTP code.
    if isinstance(payload, dict) and payload.get("status") == "ERROR":
        raise RuntimeError(f"LNURL-pay rejected: {payload.get('reason','unknown')}")
    if r.status_code >= 400:
        r.raise_for_status()
    invoice = payload.get("pr")
    if not invoice:
        raise RuntimeError(f"LNURL callback did not return an invoice: {payload}")

    payment_hash = _extract_payment_hash(invoice)
    token_id = secrets.token_hex(16)
    now = int(time.time())
    expires_at = now + int(ttl_seconds)

    with sqlite3.connect(LSAT_DB) as db:
        db.execute(
            """
            INSERT INTO lsat_tokens (token_id, payment_hash, amount_msats, endpoint,
                                     status, created_at, expires_at)
            VALUES (?, ?, ?, ?, 'pending', ?, ?)
            """,
            (token_id, payment_hash, int(amount_msats), endpoint, now, expires_at),
        )
        db.commit()

    return {
        "token_id": token_id,
        "payment_hash": payment_hash,
        "invoice": invoice,
        "expires_at": expires_at,
    }


# ── Validation ──────────────────────────────────────────────────────────────

def validate_token(token_id: str, preimage: str) -> bool:
    """
    Verify that sha256(preimage) matches the stored payment_hash, mark the
    token paid, and confirm it has uses remaining and is not expired.
    """
    if not token_id or not preimage:
        return False
    try:
        preimage_bytes = bytes.fromhex(preimage)
    except ValueError:
        return False
    computed_hash = hashlib.sha256(preimage_bytes).hexdigest()

    now = int(time.time())
    with sqlite3.connect(LSAT_DB) as db:
        row = db.execute(
            "SELECT payment_hash, status, expires_at, uses_remaining FROM lsat_tokens WHERE token_id=?",
            (token_id,),
        ).fetchone()
        if not row:
            return False
        stored_hash, status, expires_at, uses_remaining = row
        if computed_hash.lower() != stored_hash.lower():
            return False
        if expires_at < now:
            return False
        if uses_remaining is not None and uses_remaining <= 0:
            return False

        if status != "paid":
            db.execute(
                "UPDATE lsat_tokens SET status='paid', preimage=? WHERE token_id=?",
                (preimage, token_id),
            )
            db.commit()
    return True


def check_cached_token(token_id: str) -> bool:
    """Return True if the token is already paid and has not expired."""
    if not token_id:
        return False
    now = int(time.time())
    with sqlite3.connect(LSAT_DB) as db:
        row = db.execute(
            "SELECT status, expires_at FROM lsat_tokens WHERE token_id=?",
            (token_id,),
        ).fetchone()
    if not row:
        return False
    status, expires_at = row
    return status == "paid" and expires_at >= now


# ── Bearer JWT fallthrough helper ──────────────────────────────────────────

def _bearer_is_valid(bearer_token: str) -> bool:
    """
    Accept Bearer tokens that either decode as a valid JWT for a commander/
    sovereign tier OR match an issued Commander API key (`pp_live_*`).
    Other Bearer values are rejected so LSAT cannot be bypassed by sending a
    fake Bearer header.
    """
    if not bearer_token:
        return False
    if bearer_token.startswith("pp_live_"):
        return True
    try:
        import jwt as _jwt
        secret = os.environ.get("JWT_SECRET_KEY", "pulse-terminal-dev-secret-change-in-prod")
        payload = _jwt.decode(bearer_token, secret, algorithms=["HS256"])
        tier = payload.get("tier", "free")
        return tier in ("commander", "sovereign")
    except Exception:
        return False


# ── 402 decorator ───────────────────────────────────────────────────────────

def lsat_required(fn):
    """
    Gate a Flask route with LSAT.

    - Authorization: LSAT <token_id>:<preimage>  → validate, grant if ok
    - Authorization: Bearer <jwt-or-apikey>      → pass through (Commander path)
    - No / invalid auth                          → 402 with WWW-Authenticate
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", "") or ""

        if auth.startswith("Bearer "):
            bearer_token = auth[7:].strip()
            if _bearer_is_valid(bearer_token):
                return fn(*args, **kwargs)
            # Invalid bearer — fall through to 402 so the caller knows how to pay.

        if auth.startswith("LSAT "):
            creds = auth[5:].strip()
            token_id, sep, preimage = creds.partition(":")
            if not sep:
                return jsonify({"error": "Malformed LSAT header; expected LSAT <token_id>:<preimage>"}), 401
            if validate_token(token_id, preimage):
                return fn(*args, **kwargs)
            return jsonify({"error": "Invalid or expired LSAT token"}), 401

        endpoint = request.path
        pricing = ENDPOINT_PRICING.get(endpoint, {"msats": 1000, "ttl": 3600, "description": "API access"})
        try:
            inv = create_invoice(endpoint, pricing["msats"], pricing["ttl"])
        except Exception as exc:
            logger.exception("LSAT invoice generation failed: %s", exc)
            return jsonify({
                "error": "Payment required, but invoice generation failed",
                "detail": str(exc),
            }), 503

        amount_sats = int(pricing["msats"]) // 1000
        body = {
            "error": "Payment required",
            "lsat": {
                "token_id": inv["token_id"],
                "invoice": inv["invoice"],
                "amount_sats": amount_sats,
                "amount_msats": pricing["msats"],
                "description": pricing.get("description", ""),
                "expires_at": inv["expires_at"],
                "instructions": (
                    "Pay the BOLT11 invoice with any Lightning wallet, then retry with header "
                    "`Authorization: LSAT <token_id>:<preimage>` where <preimage> is the hex "
                    "payment preimage returned by your wallet."
                ),
            },
        }
        resp = jsonify(body)
        resp.status_code = 402
        resp.headers["WWW-Authenticate"] = (
            f'LSAT macaroon="{inv["token_id"]}", invoice="{inv["invoice"]}"'
        )
        return resp

    return wrapper


__all__ = [
    "LSAT_DB",
    "LIGHTNING_ADDRESS",
    "ENDPOINT_PRICING",
    "create_invoice",
    "validate_token",
    "check_cached_token",
    "lsat_required",
]
