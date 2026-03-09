# STRIPE SETUP FOR PBX — Terminal API Commander Tier
# Created: 2026-03-09

---

## STEP 1: Create Stripe Account
- Go to https://dashboard.stripe.com
- Create account if needed (or log in)
- Stay in TEST MODE first (toggle in top-left: "Test mode")

## STEP 2: Create the Commander Product
1. Go to **Products** → **+ Add product**
2. Name: `Protocol Pulse Commander API`
3. Description: `Terminal API — 1,000 req/hr · SSE Stream · Webhook Delivery`
4. Pricing model: **Recurring**
5. Amount: **$49.00 USD** per **month**
6. Click **Save product**
7. On the product page, copy the **Price ID** → starts with `price_...`
   → This is your `STRIPE_COMMANDER_PRICE_ID`

## STEP 3: Get API Keys
1. Go to **Developers** → **API keys**
2. Copy **Secret key** (starts with `sk_test_...` for test mode)
   → This is your `STRIPE_SECRET_KEY`
3. (Do NOT use the publishable key — only the secret key)

## STEP 4: Create Webhook Endpoint
1. Go to **Developers** → **Webhooks** → **+ Add endpoint**
2. Endpoint URL: `https://protocolpulse.io/webhook/stripe/terminal`
   (For local testing: use Stripe CLI or ngrok)
3. Select events to listen to:
   - `checkout.session.completed`
   - `customer.subscription.deleted`
   - `customer.subscription.updated`
   - `invoice.payment_failed`
4. Click **Add endpoint**
5. On the webhook page, click **Reveal** on "Signing secret"
   → Copy the value starting with `whsec_...`
   → This is your `STRIPE_WEBHOOK_SECRET`

## STEP 5: Add Keys to Ultron .env
SSH to Ultron and add to `~/protocol_pulse/.env`:

```bash
STRIPE_SECRET_KEY=sk_test_...        # from Step 3
STRIPE_WEBHOOK_SECRET=whsec_...      # from Step 4
STRIPE_COMMANDER_PRICE_ID=price_...  # from Step 2
```

## STEP 6: Restart Flask
```bash
# Find the gunicorn/flask process
tmux list-sessions
tmux attach -t flask_main

# Or restart via systemd if configured:
sudo systemctl restart protocol-pulse
```

## STEP 7: Test with Test Card
1. Go to https://protocolpulse.io/premium
2. Enter your email, click "JOIN THE INTEL FEED →"
3. On Stripe checkout page:
   - Card: `4242 4242 4242 4242`
   - Expiry: Any future date (e.g., `12/28`)
   - CVC: Any 3 digits (e.g., `123`)
   - ZIP: Any 5 digits (e.g., `90210`)
4. Click "Subscribe"
5. You should be redirected to `/subscribe/terminal/success` with your API key
6. Check that welcome email was sent (if RESEND_API_KEY is configured)

## STEP 8: Verify API Key Works
```bash
# Replace with your actual key from the success page
curl https://protocolpulse.io/api/v2/terminal/topics \
  -H "X-API-Key: pp_cmd_your_key_here"
```
Should return: `{"data": [...], "meta": {"tier": "commander", ...}}`

## STEP 9: Go Live (when ready)
1. Toggle Stripe dashboard from **Test mode** to **Live mode**
2. Repeat Steps 2-4 with live keys (they start with `sk_live_`, `price_live_`, `whsec_live_`)
3. Update `.env` on Ultron with live keys
4. Restart Flask

---

## VERIFICATION CHECKLIST
- [ ] GET /premium → HTTP 200, Terminal API section visible
- [ ] POST /api/v2/terminal/subscribe → Stripe redirect (with STRIPE keys in .env)
- [ ] GET /api/v2/terminal/topics with valid api_key → 200 with data
- [ ] GET /api/v2/terminal/topics with bad key → 401
- [ ] 21st request with demo key → 429 with Retry-After header
- [ ] Stripe webhook processes checkout.session.completed → creates api_key in DB
- [ ] Welcome email sent via Resend on subscription
- [ ] GET /api/playground → playground renders, demo key works
- [ ] GET /api/dashboard → unauthenticated state shown
- [ ] GET /api/dashboard?key=pp_cmd_... → subscriber state shown

---

## TROUBLESHOOTING

**"Stripe not configured" error on checkout:**
→ STRIPE_SECRET_KEY not in .env. Add it and restart Flask.

**Webhook not firing / subscriber not created:**
→ Check webhook endpoint URL is correct.
→ Check STRIPE_WEBHOOK_SECRET matches the whsec_ from Stripe dashboard.
→ Check Flask logs: `tail -f logs/app.log`

**API key not in success page after checkout:**
→ Webhook may not have fired yet. Wait 30s and go to /api/dashboard.
→ Enter your email in the key lookup to find your key.
→ If still missing, check webhook logs in Stripe dashboard.

**Demo key not working in playground:**
→ Run: `curl http://localhost:5000/api/v2/terminal/topics -H "X-API-Key: pp_demo_00000000000000000000000000000001"`
→ If 401: demo key not provisioned. Restart Flask to trigger provision_demo_key().

---

*Questions: support@protocolpulse.io*
