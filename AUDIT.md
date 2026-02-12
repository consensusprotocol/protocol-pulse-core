# Protocol Pulse Audit (Ultron)

## Scope
- Run reliability on Ultron (dev + prod flow)
- Architecture visibility (entrypoints, routes, services, jobs)
- Highest-risk paths: auth, payments, webhooks, posting automation, partner links, migrations
- Logging/error handling and performance foot-guns
- Security basics (secrets, sessions, CORS, admin protection)

## Entry Points / Runtime Map
- **App boot:** `app.py` (Flask app + extension init + `db.create_all()` + route import)
- **Server entrypoint:** `run_server.py` (`0.0.0.0:5000`, no reloader)
- **Web app routes:** `routes.py` (core route surface, admin APIs, hub APIs, payments/webhooks)
- **Background jobs:** `scripts/intelligence_loop.py` (5-min loop), launched by `pulse_intel.service`
- **Media render job:** `medley_director.py` (GPU 1 render, progress file tracked by hub APIs)
- **System services in use:** `protocol-pulse.service`, `pulse_intel.service` (user-level systemd)

## Red (Must Fix Before Premium Push)
1. **Default secret fallback is hardcoded** (`app.py`): app still runs if `SESSION_SECRET` is missing, using a static dev key. This is session compromise risk.
2. **Werkzeug dev server is serving production traffic** (`run_server.py` / service logs): no gunicorn/uwsgi front layer yet; weaker resilience and request handling under load.
3. **No migration discipline at runtime** (`app.py` uses `db.create_all()` on startup): schema drift and silent prod divergence risk for premium features.
4. **Socket transport allows wildcard origins** (`app.py` SocketIO `cors_allowed_origins="*"`): broad cross-origin surface for authenticated realtime channels.
5. **Auth post-login flow is role-unsafe for premium users** (`routes.py` login currently redirects all success cases to `/admin`): non-admin paid users can hit dead/loop behavior.

## Yellow (Fix Soon)
1. **CSRF coverage is inconsistent**: `_require_csrf()` exists, but many POST endpoints do not enforce it.
2. **Blocking network calls in request thread** (`routes.py` has many `requests.get/post` paths with multi-second timeouts): can stall responses during upstream latency.
3. **Large monolithic route file** (`routes.py`): broad blast radius and hard-to-test changes.
4. **Noise-heavy startup logs**: optional service/key failures are logged loudly at boot, diluting operational signal.
5. **CTR metric quality depends on pageview tracking completeness**: pageview-based denominators can undercount if tracking JS is blocked.

## Green (Working / Acceptable)
1. **Hub + premium gates are active** (`@login_required` + `@premium_hub_required` on `/hub` and related APIs).
2. **Background automation persistence exists** (`pulse_intel.service` active with restart behavior).
3. **Signal stream now humanized** (`[signal]/[sentry]/[whale]` style log lines, noisy transport logs filtered from hub).
4. **Partner link floor is now present** (`data/referrals.json` added; `/go/<partner_key>` no longer relies on missing file).
5. **Thin-slice partner ramp shipped in hub** (catalog-driven cards, click tracking, admin analytics view).

## Stabilization Checklist (Next 10 Changes)
1. Enforce `SESSION_SECRET` at startup (fail fast if missing in non-dev mode).
2. Move production web serving to gunicorn + systemd unit; keep Flask dev server for local only.
3. Remove `db.create_all()` from runtime path; require explicit Alembic migration apply during deploy.
4. Lock SocketIO CORS to known app origins only.
5. Fix login redirect flow: honor `next`, then route non-admin users to `/hub`.
6. Add global CSRF policy for authenticated POST endpoints (except signature-verified webhooks).
7. Validate webhook signatures for all webhook endpoints (Stripe strict; Printful/GHL equivalent).
8. Split `routes.py` into blueprints (`auth`, `hub`, `admin`, `billing`, `webhooks`) to reduce blast radius.
9. Add request-timeout + retry/circuit strategy for external APIs and move expensive pulls off request thread.
10. Add uptime/error observability baseline: structured logs + central error capture + service health checks.
