# BUILD COMPLETE — B1: NEWSLETTER ENGINE
Feature ID: b1-newsletter
Branch: feature/b1-newsletter
Completed: 2026-03-09
Commit: (see below — built on top of 200fb70)

---

## WHAT WAS BUILT

### Routes (routes_newsletter_b1.py — Blueprint)
- `POST /api/newsletter/subscribe` — subscribe with email, idempotent
- `GET /unsubscribe` — CAN-SPAM unsubscribe via ?token=UUID (LAW 4)
- `POST /api/newsletter/send` — admin-triggered manual send (auth required)

### Service (services/newsletter_service.py — 716 lines)
- `subscribe(email, source)` — atomic subscribe with UUID unsubscribe_token
- `unsubscribe(token)` — mark subscriber inactive
- `already_sent_today()` — LAW 2 idempotency gate
- `build_newsletter_html(...)` — LAW 3 format: BTC price, top story, 4 others, network stat, oracle signal, CTA, footer, unsubscribe link
- `send_daily_newsletter(force)` — full send pipeline with Resend batch API
- `send_test_newsletter(to_email)` — test send to single address

### Models (models.py — added)
- `NewsletterSubscriber` — email, unsubscribe_token (UUID), subscribed, source
- `NewsletterSend` — send log for LAW 2 idempotency (subject, resend_batch_id, recipient_count, sent_at)

### Cron (cron/newsletter_cron.py)
- Scheduler loop: sends at 08:00 ET (13:00 UTC) daily
- `--now` flag: immediate send
- `--test EMAIL` flag: test send
- System cron: `0 13 * * * cd /home/ultron/protocol_pulse && python3 cron/newsletter_cron.py --now`

### App Registration (app.py)
- `newsletter_b1_bp` registered at module level (hard-fail if missing — no silent swallow)

---

## AUDIT SUMMARY

### Audit Grade (Cycle 1 — before second pass)
- Backend Logic: ~17/100 → second pass resolved core implementation gaps
- Law Compliance: ~7/100 → RESEND_API_KEY startup validation + blueprint registration fixed

### Key P0/P1 Findings Fixed
1. U1 — Core implementation was absent (routes/service/models) → fully implemented
2. U2 — RESEND_API_KEY validation at startup → critical log if missing
3. U3 — Blueprint registration in hard-fail mode (no try/except swallow)
4. U4 — _resend_api_key() reads from env at call time (supports late .env)
5. U5 — Idempotency keys per batch: pp-newsletter-{date}-batch{N} (double-send safe)
6. P1 — get_json(silent=True) for safe handling of malformed JSON

---

## REGRESSION TEST
- Result: 29 PASS | 0 FAIL | 1 WARN

---

## PBX ACTIONS REQUIRED
1. `RESEND_API_KEY` must be in `.env` (newsletter silently disabled without it, logs CRITICAL)
2. DNS: `pulse@protocolpulse.io` must be verified in Resend dashboard
3. System cron: `0 13 * * * cd /home/ultron/protocol_pulse && python3 cron/newsletter_cron.py --now`
4. Test send: `python3 cron/newsletter_cron.py --test pbx@protocolpulse.io`
