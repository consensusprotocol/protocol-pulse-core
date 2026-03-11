# STRIPE + TERMINAL API SETUP — PBX Instructions

## 1. Create Stripe Account
- Go to https://dashboard.stripe.com
- Create account if needed
- Start in **test mode** (toggle top-right)

## 2. Create Product
- Go to **Products** → **Add product**
- Name: `Protocol Pulse Commander`
- Price: `$49.00 / month` (recurring)
- Click **Save product**
- Copy the **Price ID** (starts with `price_...`)

## 3. Get API Keys
- Go to **Developers** → **API keys**
- Copy the **Secret key** (starts with `sk_test_...` in test mode)

## 4. Set Up Webhook
- Go to **Developers** → **Webhooks** → **Add endpoint**
- Endpoint URL: `https://protocolpulse.io/webhook/stripe/terminal`
- Events to listen for:
  - `checkout.session.completed`
  - `customer.subscription.deleted`
- Click **Add endpoint**
- Copy the **Signing secret** (starts with `whsec_...`)

## 5. Add to Ultron .env
SSH to Ultron and add these to `~/protocol_pulse/.env`:
```
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_COMMANDER_PRICE_ID=price_...
```

## 6. Restart Flask
```bash
tmux send-keys -t flask_main C-c
tmux send-keys -t flask_main "cd ~/protocol_pulse && python3 app.py" Enter
```

## 7. Test with Stripe Test Card
- Card number: `4242 4242 4242 4242`
- Expiry: any future date (e.g., `12/30`)
- CVC: any 3 digits (e.g., `123`)
- ZIP: any 5 digits (e.g., `10001`)

## 8. Test Endpoints
```bash
# Status (no auth)
curl http://localhost:5000/api/v2/terminal/status

# With demo key
curl -H "X-PP-API-Key: pp_demo_readonly" http://localhost:5000/api/v2/terminal/sentiment
curl -H "X-PP-API-Key: pp_demo_readonly" http://localhost:5000/api/v2/terminal/topics
curl -H "X-PP-API-Key: pp_demo_readonly" http://localhost:5000/api/v2/terminal/entities
curl -H "X-PP-API-Key: pp_demo_readonly" http://localhost:5000/api/v2/terminal/breaking
curl -H "X-PP-API-Key: pp_demo_readonly" http://localhost:5000/api/v2/terminal/network
```

## 9. Go Live
When ready for production:
1. Toggle Stripe to **live mode**
2. Replace `sk_test_` with `sk_live_` key
3. Create a new webhook with the production URL
4. Update `.env` with live keys
5. Restart Flask
