"""
stripe_service.py — Stripe webhook handler for Pulse Terminal Commander tier.
Processes subscription events and updates user tier accordingly.
"""

import logging
import os

logger = logging.getLogger("StripeService")

# Stripe price IDs for Terminal tiers (set in env)
COMMANDER_PRICE_ID = os.environ.get("STRIPE_COMMANDER_PRICE_ID", "")
OPERATOR_PRICE_ID = os.environ.get("STRIPE_OPERATOR_PRICE_ID", "")
SOVEREIGN_PRICE_ID = os.environ.get("STRIPE_SOVEREIGN_PRICE_ID", "")

_PRICE_TO_TIER = {
    COMMANDER_PRICE_ID: "commander",
    OPERATOR_PRICE_ID: "operator",
    SOVEREIGN_PRICE_ID: "sovereign",
}


def resolve_tier_from_price(price_id: str) -> str | None:
    """Map a Stripe price ID to a subscription tier name. Returns None if unknown."""
    if not price_id:
        return None
    tier = _PRICE_TO_TIER.get(price_id)
    if tier:
        return tier
    # Fallback: check metadata passed in line items
    return None


def handle_checkout_completed(session_obj: dict, db, models) -> dict:
    """
    Process a checkout.session.completed event for Terminal subscriptions.
    Upgrades user tier to commander (or whichever tier was purchased).

    Returns {"success": bool, "tier": str, "user_id": int|None, "error": str|None}
    """
    customer_email = (session_obj.get("customer_details") or {}).get("email")
    customer_id = session_obj.get("customer")
    subscription_id = session_obj.get("subscription")

    # Determine tier from metadata first, then price_id fallback
    metadata = session_obj.get("metadata") or {}
    tier = metadata.get("tier") or metadata.get("subscription_tier")

    if not tier:
        # Try to get from line items metadata if present
        tier = metadata.get("terminal_tier", "commander")  # default to commander for Terminal

    if tier not in ("operator", "commander", "sovereign"):
        logger.warning("Unrecognized tier '%s' in checkout session %s", tier, session_obj.get("id"))
        return {"success": False, "tier": tier, "user_id": None, "error": "unrecognized tier"}

    # Find user by email or customer_id
    user = None
    if customer_email:
        user = models.User.query.filter_by(email=customer_email).first()
    if not user and customer_id:
        user = models.User.query.filter_by(stripe_customer_id=customer_id).first()

    if not user:
        logger.warning("No user found for checkout: email=%s customer=%s", customer_email, customer_id)
        return {"success": False, "tier": tier, "user_id": None, "error": "user not found"}

    # Update user tier
    user.subscription_tier = tier
    if customer_id:
        user.stripe_customer_id = customer_id
    if subscription_id:
        user.stripe_subscription_id = subscription_id

    try:
        db.session.commit()
        logger.info("User %d upgraded to %s tier via Stripe", user.id, tier)
        return {"success": True, "tier": tier, "user_id": user.id, "error": None}
    except Exception as e:
        db.session.rollback()
        logger.error("DB error upgrading user %d: %s", user.id, e)
        return {"success": False, "tier": tier, "user_id": user.id, "error": str(e)}


def handle_subscription_deleted(subscription_obj: dict, db, models) -> dict:
    """
    Process a customer.subscription.deleted event.
    Downgrades user back to free tier.
    """
    subscription_id = subscription_obj.get("id")
    customer_id = subscription_obj.get("customer")

    user = None
    if subscription_id:
        user = models.User.query.filter_by(stripe_subscription_id=subscription_id).first()
    if not user and customer_id:
        user = models.User.query.filter_by(stripe_customer_id=customer_id).first()

    if not user:
        logger.warning("No user found for subscription deletion: sub=%s", subscription_id)
        return {"success": False, "error": "user not found"}

    old_tier = user.subscription_tier
    user.subscription_tier = "free"
    user.stripe_subscription_id = None

    try:
        db.session.commit()
        logger.info("User %d downgraded from %s to free (subscription deleted)", user.id, old_tier)
        return {"success": True, "user_id": user.id, "old_tier": old_tier}
    except Exception as e:
        db.session.rollback()
        logger.error("DB error downgrading user %d: %s", user.id, e)
        return {"success": False, "error": str(e)}


def validate_webhook_signature(payload: bytes, sig_header: str, secret: str) -> dict | None:
    """
    Validates Stripe webhook signature. Returns parsed event or None on failure.
    """
    try:
        import stripe
        stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
        event = stripe.Webhook.construct_event(payload, sig_header, secret)
        return event
    except Exception as e:
        logger.warning("Stripe signature validation failed: %s", e)
        return None
