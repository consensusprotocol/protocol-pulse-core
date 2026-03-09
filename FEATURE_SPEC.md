# FEATURE SPEC — terminal-api-v2
## IDENTITY
- **FEATURE:**       Pulse Terminal Commander tier ($49/mo)
- **BRANCH:**        agent/terminal-api-v2
- **WORKTREE_DIR:**  ~/worktrees/terminal-api-v2
- **SESSION:**       agent_terminal-api-v2
- **PRIORITY:**      🟡 Medium

## SCOPE
Build the Commander tier of the Pulse Terminal API per EXPANSION_SPEC_V22_V30.md.
5 endpoints (already built in Phase 1) + Commander-specific endpoints: /v1/signals/live,
/v1/spaces/live, /v1/tradfi/signals, /v1/sentiment/composite, /v1/alerts/webhook.
Stripe billing integration for $49/mo Commander tier. Rate limiting: 1000 req/day.
JWT auth with tier claims. No frontend — API only.

## SUCCESS CRITERIA
1. All 5 Commander endpoints return valid JSON with correct schema
2. Stripe webhook validates Commander subscription before granting access
3. Rate limit: 1000 req/day enforced via Redis or SQLite counter
4. JWT token includes tier=commander claim
5. /v1/signals/live returns last 10 BTC-relevant signals with btc_lens_sentiment
6. /v1/spaces/live returns active X Spaces from live_signals.json
7. /v1/tradfi/signals returns top 20 TradFi signals
8. All endpoints return 401 for missing/invalid JWT
9. Regression zero FAILs

## FILES_TO_TOUCH
- `core/routes.py` — Commander endpoints (after line ~6800)
- `core/services/pulse_terminal_service.py` — create if not exists
- `core/services/stripe_service.py` — Stripe webhook handler

## FILES_NEVER_TOUCH
- `video_pipeline_v3/` — no pipeline touches
- `regression_test.sh`
- `PIPELINE_LAWS.md`

## GPU USAGE
- Requires GPU render: NO
- Can run 24/7 alongside production

## PR FORMAT
- **Title:** `feat(terminal-api): Commander tier — 5 endpoints, Stripe $49/mo, JWT auth`

## STATUS
- [x] Spec written
- [ ] Agent launched
