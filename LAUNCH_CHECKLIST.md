# Launch checklist (Protocol Pulse)

Use this before going live. Everything below is optional except security and basics.

## Security & env

- [ ] Copy `core/.env.example` to `core/.env` and fill in values.
- [ ] Set **SESSION_SECRET** to a long random value in production (e.g. `openssl rand -hex 32`). Never commit `.env`.
- [ ] In production, ensure **FLASK_ENV=production** (or equivalent) so debug is off.

## Database

- [ ] Run migrations: `flask db upgrade` (from repo root or `core/` as appropriate).
- [ ] For production, use **PostgreSQL** and set **DATABASE_URL** accordingly.

## Health & monitoring

- [ ] **/health** – liveness (app is up). Point load balancer / Render health check here.
- [ ] **/ready** – readiness (app + DB). Use for k8s or similar if you use it.
- [ ] **/health/automation** – optional; automation last-run status.

## SEO & crawlers

- [ ] **/robots.txt** – live; allows crawlers, disallows /admin, /api/, /hub, /login, /signup.
- [ ] **/sitemap.xml** – live; includes home, articles, key pages and recent articles. Submit to Google Search Console (and Bing if desired).

## Payments & webhooks

- [ ] **Stripe**: set **STRIPE_SECRET_KEY** and **STRIPE_WEBHOOK_SECRET**. In Stripe Dashboard → Developers → Webhooks, add endpoint **https://yourdomain.com/webhook/stripe** and copy the signing secret into **STRIPE_WEBHOOK_SECRET**.
- [ ] **Lightning**: set **LIGHTNING_ADDRESS** if you use LN tips.

## Optional integrations

- [ ] **GHL**: GHL_API_KEY, GHL_LOCATION_ID (and GHL_WEBHOOK_URL / GHL_SARAH_WORKFLOW_ID if used).
- [ ] **X (Twitter)**: required for posting and Spaces; add keys and set AUTOPOST_X if desired.
- [ ] **Newsletter / CRM**: SendGrid, ConvertKit – set keys if you use those flows.

## Legal & pages

- [ ] **Privacy**: `/privacy-policy` is live; linked in footer and nav. Review copy for your jurisdiction.
- [ ] **Contact**: `/contact` is live. Submissions are stored in DB and viewable under Admin → Contact. Optional: set **CONTACT_EMAIL** and **SENDGRID_API_KEY** (and **SENDGRID_FROM_EMAIL**) to receive notification emails for each submission.

## DNS & hosting

- [ ] Point domain to your host (e.g. Render). Set **SITE_URL** to your production URL.
- [ ] HTTPS: ensure your host provides TLS (Render does by default).

## Post-launch

- [ ] Submit sitemap in Google Search Console.
- [ ] Test checkout and webhooks (Stripe test mode first).
- [ ] Rate limiting (login, contact, donate) and CSRF on forms are already enabled.

---

*Quick reference: health = `/health`, ready = `/ready`, sitemap = `/sitemap.xml`, robots = `/robots.txt`.*
