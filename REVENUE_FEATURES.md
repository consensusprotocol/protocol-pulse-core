# Revenue & Monetization Features

This document describes the revenue-generating features added to Protocol Pulse.

## 1. Smart Analytics (Admin)

- **Route:** `/admin/smart-analytics` (admin only)
- **Purpose:** Single dashboard for all site metrics to understand user preferences and target content.
- **Includes:** Page views, unique sessions, top pages, traffic by category, top referrers, article performance, affiliate click performance, premium subscriber count, MRR.
- **Engagement tracking:** Base template sends `time_on_page` and `scroll_depth` every 30s and on beforeunload to `/api/track/event` (event_type: `engagement`).

## 2. Affiliate Products & Product-Highlight Articles

- **Models:** `AffiliateProduct` (name, product_type, product_id, category, affiliate_url, etc.), `AffiliateClick` (tracks clicks for analytics).
- **Seed:** Visiting `/admin/smart-analytics` seeds default products (Trezor, Ledger, Cryptosteel, Bitaxe placeholder) if none exist.
- **Generate article:** `POST /admin/generate-affiliate-article` — picks a random active product, generates a draft article with the referral link appended, using ContentEngine.
- **Tracking:** Use `/api/track/event` with `event_type: 'affiliate_click'`, `product_id`, `link_type`, `page_path` when users click affiliate links so Smart Analytics shows conversions.

## 3. Paid Tier: $99/mo Commander & Premium Hub

- **Tiers:** Free, Operator ($21), **Commander ($99)**, Sovereign ($210). Commander is the “Premium Hub” tier.
- **Premium Hub:** `/hub` — real-time command center (block height, hashrate, difficulty, mempool fees, BTC price, links to Live Terminal, Whale Watcher, latest briefs). Requires login and Commander (or Sovereign) subscription.
- **Stripe:** On `checkout.session.completed` with `metadata.tier` in (operator, commander, sovereign), the webhook finds the user by email and sets `subscription_tier`, `stripe_customer_id`, `stripe_subscription_id`.
- **Premium page:** `/premium` shows all four tiers and highlights Commander as “Best value” with “Get Premium Hub”. If the user is already Commander+, a “Go to Premium Hub” button is shown.

## Database

Ensure the following exist (e.g. via Flask-Migrate or manual ALTER):

**User table:**
- `subscription_tier` (VARCHAR, default `'free'`)
- `stripe_customer_id` (VARCHAR, nullable)
- `stripe_subscription_id` (VARCHAR, nullable)
- `subscription_expires_at` (DATETIME, nullable)

**New tables:** `affiliate_product`, `affiliate_click` (see `models.AffiliateProduct` and `models.AffiliateClick`).

If you use `db.create_all()`, create the new tables and add the User columns with a migration or:

```sql
ALTER TABLE user ADD COLUMN subscription_tier VARCHAR(30) DEFAULT 'free';
ALTER TABLE user ADD COLUMN stripe_customer_id VARCHAR(120);
ALTER TABLE user ADD COLUMN stripe_subscription_id VARCHAR(120);
ALTER TABLE user ADD COLUMN subscription_expires_at DATETIME;
```

## Environment

- `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` for payments and webhook (subscription tier update).
- `AMAZON_AFFILIATE_TAG` (e.g. `protocolpulse-20`) for Amazon affiliate links.

## Quick Links

- Smart Analytics: `/admin/smart-analytics`
- Generate affiliate article: POST `/admin/generate-affiliate-article` (admin)
- Premium pricing: `/premium`
- Premium Hub (Commander+): `/hub`
