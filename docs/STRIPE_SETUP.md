# Stripe Setup — Protocol Pulse Commander Tier

## Overview

The Commander tier uses Stripe for subscription billing. Two flows run in parallel:

1. **Terminal API subscriptions** — email-only checkout → provisions `ApiSubscriber` + API key.
2. **User account subscriptions** — logged-in user checkout → sets `User.subscription_tier = 'commander'`.

Both flows share the same Stripe keys and webhook endpoint.

---

## Step 1 — Get Stripe Keys

1. Log in at https://dashboard.stripe.com
2. Go to **Developers → API keys**
3. Copy your **Secret key** (`sk_live_...` for production, `sk_test_...` for testing)
4. The **Publishable key** is not required server-side

---

## Step 2 — Create a Product and Price

1. Go to **Products → Add product**
   - Name: `Protocol Pulse Commander`
   - Pricing model: **Recurring**
   - Price: `$49.00 / month`
2. After saving, copy the **Price ID** (format: `price_...`)

---

## Step 3 — Set Environment Variables

Add to your `.env` (Replit Secrets or Ultron `.env`):

```env
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...   # set after step 4
STRIPE_COMMANDER_PRICE_ID=price_...
```

Optional (for Operator and Sovereign tiers):
```env
STRIPE_OPERATOR_PRICE_ID=price_...
STRIPE_SOVEREIGN_PRICE_ID=price_...
```

---

## Step 4 — Configure Webhook Endpoint

1. Go to **Developers → Webhooks → Add endpoint**
2. Set the endpoint URL:
   ```
   https://protocolpulse.io/api/stripe/webhook
   ```
   (also supported: `/webhook/stripe` and `/webhook/stripe/terminal`)

3. Select events to listen for:
   - `checkout.session.completed`
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_failed`
   - `payment_intent.succeeded`

4. After saving, click **Reveal** under **Signing secret** and copy the `whsec_...` value
5. Set `STRIPE_WEBHOOK_SECRET=whsec_...` in your environment

---

## Step 5 — Test with Stripe CLI (Optional)

```bash
# Install Stripe CLI: https://stripe.com/docs/stripe-cli
stripe listen --forward-to localhost:5000/api/stripe/webhook

# In another terminal, trigger a test event:
stripe trigger checkout.session.completed
```

---

## Webhook Routes Summary

| Route | Purpose |
|-------|---------|
| `POST /api/stripe/webhook` | Primary spec route (SESSION 11) |
| `POST /webhook/stripe` | Legacy route (merch + subscriptions) |
| `POST /webhook/stripe/terminal` | Terminal API-specific webhook |
| `GET /v1/stripe/webhook` | Alternate webhook listener |

All routes validate `stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)`.
A missing or invalid `STRIPE_WEBHOOK_SECRET` causes a hard rejection (400/500).

---

## Key Generation

- Format: `pp_cmd_<uuid4hex>` (e.g. `pp_cmd_a1b2c3d4e5f6...`)
- Keys are UUID4-based — never sequential
- Stored in `api_subscribers.api_key` (SQLite / PostgreSQL)
- Key rotation provides a 1-hour grace period via `previous_api_key`

---

## Rate Limits

| Tier | Requests/Hour |
|------|--------------|
| Demo | 20 |
| Commander | 1,000 |
| Enterprise | Unlimited |

---

## Relevant Files

| File | Purpose |
|------|---------|
| `core/services/premium_service.py` | Clean service layer: `create_commander_checkout`, `issue_commander_key`, `revoke_commander_key`, `handle_webhook_event` |
| `core/services/stripe_service.py` | Low-level Stripe helpers: `validate_webhook_signature`, `provision_terminal_subscriber`, `cancel_terminal_subscriber` |
| `core/services/api_key_service.py` | Rate limiting, entitlements, `require_api_key` decorator |
| `core/routes_premium_api.py` | All Terminal API + billing routes |
| `core/templates/terminal_dashboard.html` | Commander self-service portal |
| `core/templates/terminal_playground.html` | Live API sandbox |
| `core/templates/premium.html` | Public upgrade page |
