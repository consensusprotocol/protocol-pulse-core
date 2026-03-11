"""
premium_service.py — Protocol Pulse Commander Tier service layer.

Clean wrapper around api_key_service + stripe_service for the
SESSION 11 PREMIUM + STRIPE feature.

Used by /api/subscribe/commander, /api/stripe/webhook, /terminal/dashboard.
"""

import logging
import os
import uuid

logger = logging.getLogger("PremiumService")

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
STRIPE_COMMANDER_PRICE_ID = os.environ.get("STRIPE_COMMANDER_PRICE_ID", "")


def generate_api_key() -> str:
    """Generate a UUID4-based Commander API key. Format: pp_cmd_<32hex>"""
    return f"pp_cmd_{uuid.uuid4().hex}"


def create_commander_checkout(email: str, success_url: str, cancel_url: str) -> str:
    """
    Create a Stripe Checkout session for the Commander tier.

    Args:
        email:        Customer email (pre-filled in Stripe form)
        success_url:  Redirect URL on payment success
        cancel_url:   Redirect URL on payment cancel

    Returns:
        Stripe Checkout URL string.

    Raises:
        RuntimeError if Stripe not configured or session creation fails.
    """
    if not STRIPE_SECRET_KEY:
        raise RuntimeError("STRIPE_SECRET_KEY not configured")
    if not STRIPE_COMMANDER_PRICE_ID:
        raise RuntimeError("STRIPE_COMMANDER_PRICE_ID not configured")

    try:
        import stripe
    except ImportError:
        raise RuntimeError("stripe package not installed — run: pip install stripe")

    stripe.api_key = STRIPE_SECRET_KEY
    try:
        stripe.default_http_client = stripe.RequestsClient(timeout=10)
    except Exception:
        pass  # older stripe versions may not support this

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        mode="subscription",
        customer_email=email,
        line_items=[{"price": STRIPE_COMMANDER_PRICE_ID, "quantity": 1}],
        success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=cancel_url,
        metadata={
            "subscription_type": "terminal_api",
            "tier": "commander",
            "email": email,
        },
    )
    return session.url


def issue_commander_key(user_id: int, db, models) -> str:
    """
    Issue (or re-issue) a Commander API key for a User by user_id.

    Creates a new ApiSubscriber record or updates an existing one.
    Returns the new API key string.
    """
    import json
    from services.api_key_service import TIER_ENTITLEMENTS

    key = generate_api_key()

    try:
        # Find existing subscriber by user_id (if ApiSubscriber has user_id)
        sub = None
        try:
            # Try user-linked lookup if the field exists
            sub = models.ApiSubscriber.query.filter_by(user_id=user_id).first()
        except Exception:
            pass

        if sub:
            sub.api_key = key
            sub.tier = "commander"
            sub.is_active = True
            sub.subscription_status = "active"
            sub.entitlements = json.dumps(TIER_ENTITLEMENTS.get("commander", {}))
        else:
            # Look up email from User model
            user = models.User.query.get(user_id)
            email = user.email if user else f"user_{user_id}@protocolpulse.io"

            existing_by_email = models.ApiSubscriber.query.filter_by(email=email).first()
            if existing_by_email:
                existing_by_email.api_key = key
                existing_by_email.tier = "commander"
                existing_by_email.is_active = True
                existing_by_email.subscription_status = "active"
                existing_by_email.entitlements = json.dumps(TIER_ENTITLEMENTS.get("commander", {}))
            else:
                sub = models.ApiSubscriber(
                    email=email,
                    api_key=key,
                    tier="commander",
                    rate_limit_per_hour=1000,
                    entitlements=json.dumps(TIER_ENTITLEMENTS.get("commander", {})),
                    key_scopes=json.dumps(["read", "stream", "webhook"]),
                    is_active=True,
                    subscription_status="active",
                )
                db.session.add(sub)

        db.session.commit()
        logger.info("Commander API key issued for user_id=%d", user_id)
        return key

    except Exception as e:
        logger.error("Error issuing commander key for user_id=%d: %s", user_id, e)
        try:
            db.session.rollback()
        except Exception:
            pass
        raise


def revoke_commander_key(user_id: int, db, models) -> bool:
    """
    Revoke Commander tier for a user. Sets tier='free', is_active=False.
    Returns True on success, False if subscriber not found.
    """
    try:
        user = models.User.query.get(user_id)
        if not user:
            return False

        sub = models.ApiSubscriber.query.filter_by(email=user.email).first()
        if not sub:
            return False

        sub.tier = "free"
        sub.is_active = False
        sub.subscription_status = "canceled"

        # Also downgrade User model
        user.subscription_tier = "free"
        user.stripe_subscription_id = None

        db.session.commit()
        logger.info("Commander key revoked for user_id=%d", user_id)
        return True

    except Exception as e:
        logger.error("Error revoking commander key for user_id=%d: %s", user_id, e)
        try:
            db.session.rollback()
        except Exception:
            pass
        return False


def handle_webhook_event(payload: bytes, sig_header: str, db, models) -> dict:
    """
    Validate and process a Stripe webhook event.

    Returns {"ok": True} or {"error": str, "status": int}
    """
    from services.stripe_service import (
        validate_webhook_signature,
        provision_terminal_subscriber,
        cancel_terminal_subscriber,
        handle_checkout_completed,
        handle_subscription_deleted,
    )

    if not STRIPE_WEBHOOK_SECRET:
        logger.critical("STRIPE_WEBHOOK_SECRET not set — rejecting webhook")
        return {"error": "Webhook secret not configured", "status": 500}

    event = validate_webhook_signature(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    if not event:
        return {"error": "Invalid signature", "status": 400}

    event_type = event.get("type", "")
    event_obj = (event.get("data") or {}).get("object", {})
    metadata = event_obj.get("metadata") or {}

    logger.info("Premium webhook received: %s", event_type)

    try:
        if event_type == "checkout.session.completed":
            # Terminal API subscriptions → provision ApiSubscriber
            if metadata.get("subscription_type") == "terminal_api":
                provision_terminal_subscriber(event_obj, db, models)
            else:
                # User-model subscriptions → set subscription_tier
                handle_checkout_completed(event_obj, db, models)

        elif event_type == "customer.subscription.deleted":
            # Try both paths
            cancel_terminal_subscriber(event_obj, db, models)
            handle_subscription_deleted(event_obj, db, models)

        elif event_type == "payment_intent.succeeded":
            # For one-time payments: look up user and set tier
            customer_email = event_obj.get("receipt_email") or ""
            if customer_email:
                try:
                    user = models.User.query.filter_by(email=customer_email).first()
                    if user and user.subscription_tier == "free":
                        user.subscription_tier = "commander"
                        db.session.commit()
                        logger.info("payment_intent.succeeded: %s -> commander", customer_email)
                except Exception as e:
                    logger.warning("payment_intent tier upgrade error: %s", e)

    except Exception as e:
        logger.error("Webhook handler error for %s: %s", event_type, e)
        # Don't return error — Stripe will retry

    return {"ok": True}
