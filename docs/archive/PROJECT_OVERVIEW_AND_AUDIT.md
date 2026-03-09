# Protocol Pulse — Project Overview & Code Audit

**Date:** February 2025  
**Purpose:** Full-stack overview, automation status, X Spaces feature feasibility, premium subscription strategy, and world-class feature roadmap.

---

## 1. Project Overview: Moving Parts

### 1.1 Tech Stack
- **Backend:** Flask (Python), SQLAlchemy, Flask-Login, Flask-Migrate
- **DB:** SQLite (default) or PostgreSQL via `DATABASE_URL` (Neon)
- **Payments:** Stripe (merch checkout, premium subscriptions, tips, donations)
- **External APIs:** YouTube, Reddit, X (Twitter), Nostr, Mempool.space, Coinbase, Printful, GHL, Substack, Telegram, AssemblyAI, OpenAI, Anthropic, Gemini, XAI (Grok), ElevenLabs, Heygen, etc.

### 1.2 Core Application Structure
```
core/
├── app.py              # Flask app, DB, login, template filters
├── models.py           # 40+ models (User, Article, LaunchSequence, Stripe-related, etc.)
├── routes.py          # Main routes (~6k+ lines): public, admin, API, merch, premium, webhooks
├── routes_social.py   # Social monitor, X Spaces (mock), content monitoring
├── config/social_targets.json
├── services/          # AI, content, X, YouTube, Reddit, GHL, Printful, price, etc.
├── templates/         # 50+ templates (public + admin)
├── static/             # CSS, JS, extension, images, audio, video
└── instance/          # protocol_pulse.db
```

### 1.3 Key User-Facing Areas
| Area | Routes / Pages | Notes |
|------|----------------|-------|
| **Home & content** | `/`, `/articles`, `/articles/<id>`, category pages | Today’s Signal, bento ranking, prices |
| **Media** | `/media`, `/media-hub` | Series, episodes, X/Nostr/YouTube, episode intel cards |
| **Merch** | `/merch`, `/api/merch/checkout` | Printful + Stripe checkout |
| **Premium** | `/premium`, `/subscribe/premium/<tier>`, `/subscription/success` | Stripe subscriptions |
| **Donate / tips** | `/donate`, `/tip/<amount>` | Stripe one-time |
| **Intel / live** | `/intelligence-dashboard`, `/whale-watcher`, `/signal-terminal`, `/value-stream`, `/live`, `/bitfeed-live`, `/gravity-well`, `/hud` | Mempool.space, feeds, visualizers |
| **Operative** | `/dashboard`, `/operative/<slug>`, `/drill`, `/scorecard` | Ranks, drills, briefs |
| **Admin** | `/admin/*` (command deck, ads, launch sequences, sentiment, social monitor, revenue, etc.) | RBAC via `admin_required` |

### 1.4 Data Models (High Level)
- **Users & growth:** User, CreditAccount, UserSegment, AffiliatePartner, PageView, RollingActivity, HotMoment
- **Content:** Article, Podcast, ContentPrompt, DailyBrief, FeedItem, AutoPostDraft, ContentSuggestion, AutoTweet
- **Distribution & automation:** LaunchSequence, TargetAlert, NostrEvent, ReplySquadMember, AutomationRun, AutoTweet
- **Monetization / ads:** Advertisement, Sponsor, BitcoinDonation (Stripe webhook updates)
- **Intelligence:** SentimentSnapshot, PulseEvent, SentimentReport, SarahBrief, EmergencyFlash, CollectedSignal, IntelligencePost
- **Value stream / Nostr:** ValueCreator, CuratedPost, ZapEvent, TrustEdge, BoostStake, ExtensionSession
- **Real-time / merch:** WhaleTransaction, RealTimeProduct, HotMoment

---

## 2. Automation & Tools: What Exists vs What’s Missing

### 2.1 Currently Referenced but Not in `core/services/`
These are imported by `routes.py` or `routes_social.py` but **do not exist** under `core/services/`:

| Service | Used In | Status |
|---------|---------|--------|
| **monetization_service** | `/premium`, `/subscribe/premium/<tier>`, `/donate`, `/tip/<amount>`, `/webhook/stripe`, `/admin/revenue` | **Missing in core.** Exists in `_replit_import/services/monetization_service.py`. Must be copied into `core/services/` or premium/donate/tips will 500. |
| **scheduler** | Command deck (`get_scheduler_status`, `initialize_scheduler`), `activate_scheduler` | **Missing in core.** Exists in `_replit_import/services/scheduler.py` (APScheduler). Command deck will fallback to `scheduler_status={'running': False, 'jobs': []}` on import error. |
| **telegram_bot** (`pulse_operative`) | Command deck | **Missing in core.** Command deck catches and shows `telegram_status={'initialized': False}`. |
| **substack_service** | routes (newsletter publish), routes_social (publish to Substack after article) | Optional; wrapped in try/except. |
| **rss_service** | routes | Optional; `RSSService()` only if module present. |

**Action items:**
1. **Copy `monetization_service.py`** from `_replit_import/services/` to `core/services/` so Stripe premium/donate/tips work.
2. **Copy `scheduler.py`** (and any job dependencies) to `core/services/` if you want the Command Deck “Activate scheduler” to run real jobs.
3. **Copy or stub `telegram_bot`** if you want Telegram status on the command deck.

### 2.2 Automation That Exists in `_replit_import` (Legacy / Replit)
- **Scheduler** (APScheduler): e.g. scheduled article generation, social monitoring, featured count, archiving.
- **Social monitor** (`/api/monitor-content`, `/api/test-spaces-only`): Reddit, X tweets, YouTube, **X Spaces (mock only)**; article generation + optional Substack publish.
- **Cron-style runners:** `scheduled_job.py`, `run_scheduler.py`, `automation_runner.py`, `start_automation.py` (all in `_replit_import`).

### 2.3 Env / Secrets (.env)
Configured in `core/.env`: SESSION_SECRET, DATABASE_URL, Stripe (STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET), Printful, YouTube, GHL, Substack, Telegram, Nostr, Reddit, OpenAI, Anthropic, AssemblyAI, ElevenLabs, Heygen, Gemini, XAI, GitHub, Neon PG, etc.

**Not in .env (needed for X posting + Spaces):**
- `TWITTER_API_KEY`, `TWITTER_API_SECRET`, `TWITTER_ACCESS_TOKEN`, `TWITTER_ACCESS_TOKEN_SECRET`, `TWITTER_BEARER_TOKEN`

Without these, `XService` runs in “mock” mode (no real tweets, no Spaces API).

### 2.4 Summary: Activating Automation
1. **Stripe & premium:** Add `core/services/monetization_service.py` (from _replit_import).
2. **Background jobs:** Add `core/services/scheduler.py` and wire jobs to your content/social pipeline; run scheduler in a separate process or on app startup (see _replit_import/main.py pattern).
3. **X (Twitter):** Add Twitter API credentials to `.env`; implement Spaces search + tweet flow (see Section 4).
4. **Telegram:** Add or port `telegram_bot` if Command Deck Telegram status is desired.

---

## 3. X (Twitter) Spaces: Live Tweet + RT Feature

### 3.1 Is It Possible?
**Yes.** The X API exposes:

- **Spaces Search:** `GET /2/spaces/search` — search by **query** (e.g. "Bitcoin", "Lightning") and **state** (`live`, `scheduled`, or `all`).
- **Spaces Lookup:** `GET /2/spaces` — get details by space IDs (title, state, participant_count, creator, hosts, speakers, started_at, etc.).

So you can:
1. Periodically call Spaces search with `query=Bitcoin` (and optionally other niche terms) and `state=live`.
2. For each live Space, get participant_count, host/speaker names, title.
3. When a Space crosses a “growth” threshold (e.g. 50, 100, 500 listeners), trigger an automated tweet that includes:
   - Who’s in / who’s hosting
   - What it’s about (title + optional topic)
   - “Spicy” hook (e.g. from title or a simple keyword rule)
   - Link to the Space (e.g. `https://x.com/i/spaces/<space_id>`).
4. Optionally **retweet** the Space link (or the host’s tweet promoting it) from your bot account.

### 3.2 Requirements
- **X API access:** Spaces search/lookup typically require **Basic** ($200/mo) or higher. Free tier is write-only and does **not** include Spaces read/search. Confirm at [developer.x.com](https://developer.x.com) → your project → Products.
- **Credentials:** In `core/.env` set: `TWITTER_API_KEY`, `TWITTER_API_SECRET`, `TWITTER_ACCESS_TOKEN`, `TWITTER_ACCESS_TOKEN_SECRET`, `TWITTER_BEARER_TOKEN`. Your app uses these in `services/x_service.py`.
- **Automation:** A scheduled job (e.g. every 5–15 minutes) that:
  - Searches live Spaces (Bitcoin, Lightning, etc.).
  - Stores last-seen participant counts (DB or cache) to detect “growth” (e.g. first time above 100).
  - Drafts tweet (you can use AI for “spicy” one-liner from title/speakers).
  - Posts tweet + optional RT via your existing `XService` (extend with `post_tweet` and RT method).

### 3.3 Implementation Outline
1. **Model:** e.g. `LiveSpace` (space_id, title, host_ids, participant_count, space_url, last_count_at, tweeted_at, tweet_id).
2. **Spaces client:** In `x_service.py` (or a small `spaces_service.py”), use Tweepy v2 or requests to call `GET /2/spaces/search` and `GET /2/spaces`.
3. **Job:** Scheduler job every 10–15 min: search live Spaces → upsert `LiveSpace` → for Spaces that crossed a threshold since last run, generate tweet (template + optional AI) → post + optional RT → set `tweeted_at`/`tweet_id`.
4. **Safety:** Rate limits (300/15min per app), avoid duplicate tweets per Space (e.g. one tweet per threshold per space_id), optional admin toggle to enable/disable auto-tweet.

### 3.4 X API + Related Costs (Budget Estimate)

**X (Twitter) API**
- **Free tier:** Write-only (post tweets). Does **not** include Spaces search or read. So you **cannot** do “find live Spaces → tweet” on Free.
- **Basic tier:** **\$200/month** (as of late 2024). Includes more endpoints; Spaces search/lookup are typically on this tier (confirm at [developer.x.com](https://developer.x.com) for your project).
- **Pro tier:** \$5,000/month — overkill for this use case.

**Rough cost for your intended usage (Spaces → tweet + RT):**
- **Per month:** **~\$200** (one Basic subscription). No per-call metering; you stay under rate limits (e.g. 300 requests per 15 min).
- **Per day:** **~\$6.67** (\$200 ÷ 30).
- **Usage pattern:** Poll Spaces search every 10–15 min = ~100–150 calls/day. Posting a few tweets + RTs per day is well within limits. So the cost is **fixed** at the subscription, not usage-based.

**Other APIs for this feature**
- **Tweet drafting:** Optional. If you use **OpenAI** (you already have `OPENAI_API_KEY`) to generate a one-line “spicy” hook per Space: ~\$0.01–0.03 per tweet (tiny token count). **Template-only** (no AI) = **\$0**.
- **Hosting/cron:** Your existing app + scheduler; no extra third-party cost for the job.

**Total for “Spaces tweet + RT” feature**
- **Minimum:** **~\$200/month** (X API Basic only; template tweets, no AI).
- **With AI draft:** **~\$200–201/month** (add a few dollars if you use GPT for many tweets).

**Keeping costs low**
- Use **X API Basic** only; avoid Pro.
- Use **template-based** tweets (e.g. “LIVE: [title] with [hosts]. [X] listeners. Join: [link]”) and add AI later if budget allows.
- If X offers **annual** Basic (sometimes discounted), that can lower the effective monthly cost.

---

## 4. Paid Subscription Tier: Making $99/mo Unparalleled Value

You already have:
- **Stripe** live keys and webhook.
- **Premium page** with tiers (Operator $21/mo, Sovereign $210/mo).
- **Monetization service** (in _replit_import) defining tiers and checkout.

To add a **$99/mo tier** and make it “unparalleled”:

### 4.1 Add a New Tier (e.g. “Pulse Commander” or “Intel Pro”)
- In `monetization_service.SUBSCRIPTION_TIERS`, add a key e.g. `commander` with `price_monthly: 99` and a Stripe Price ID once created in Dashboard.
- In `subscribe_premium`, allow `tier in ['operator', 'commander', 'sovereign']`.
- Add the tier to `premium.html` (card + features list).

### 4.2 Feature Ideas to Justify $99/mo (and Differentiate)
- **Live X Spaces feed:** Dedicated page or dashboard widget of *live* Bitcoin/niche Spaces (from the same API as above) with one-click join; optional “alert when Space with X listeners goes live.”
- **Priority intel:** Early access to Daily Brief / Sarah Brief (e.g. 6–12 hours before free); or a “Pro Brief” with extra signals and links.
- **Exclusive reports:** Weekly or biweekly deep-dives (PDF or gated articles) — macro, on-chain, or “Spaces recap” summaries.
- **X Spaces alerts:** Push/email/Telegram when a Space matching keywords goes live or hits a listener threshold (drives FOMO and engagement).
- **Ad-free + extended reading:** No ads, full article history, maybe “TL;DR” and “Key quote” for every article (you already have episode intel; mirror for articles).
- **Private community:** Discord/Telegram role for subscribers only; optional monthly live Q&A or Spaces with you.
- **Signal terminal / HUD access:** Unlock “Pro” view (e.g. more indicators, export, or higher refresh) on `/signal-terminal` or `/hud`.
- **Whale watcher pro:** Alerts when a whale move matches a size threshold; or a simple “whale digest” email.
- **One “ask” per month:** Subscribers can submit one question or topic; you (or AI-assisted) answer in a weekly “Pro Q&A” post or video.

Pick 5–7 that you can actually deliver and put them clearly on the premium page.

### 4.3 Technical Implementation for Gating
- **Stripe webhook:** On `customer.subscription.created/updated/deleted`, create or update a `Subscription` (or similar) model linked to `User` (by email or Stripe customer_id), with `tier` and `status`.
- **Middleware or decorator:** e.g. `@subscription_required(min_tier='commander')` that checks `current_user` and their subscription status before serving premium routes or API.
- **Front-end:** Hide or show “Upgrade” on gated pages; show “Pro” badge and tier name in nav/dashboard.

---

## 5. World-Class Feature Suggestions

### 5.1 Content & Intel
- **Unified “Intel” feed:** One feed merging articles, podcasts, X Spaces recaps, Nostr highlights, and Daily Brief — filterable by topic and time.
- **Spaces recaps:** Auto-generate short recaps (with key quote + topics) for ended Spaces using transcript + AI; surface in Media Hub and in premium intel.
- **Sentiment + narrative dashboard:** Public or pro view of SentimentSnapshot, PulseEvent, and “narrative of the week” (from CollectedSignal / articles).
- **Fact-check badges:** Use your existing fact_checker on key claims in articles; show “Verified” / “Disputed” where applicable.

### 5.2 Community & Distribution
- **Nostr integration:** Publish article summaries or Daily Brief to Nostr (you have NostrEvent, keys in .env); allow zaps to a Protocol Pulse address.
- **Reply squad automation:** Use ReplySquadMember and TargetAlert to suggest or auto-draft replies to high-signal tweets; human-in-the-loop approve.
- **Launch sequences:** Finish the LaunchSequence workflow end-to-end (draft → approve → post to X + Nostr + optional Substack) from the admin UI.

### 5.3 Product & UX
- **Mobile PWA:** You have `manifest.json` and `sw.js`; ensure offline fallback and “Add to Home Screen” for key pages (e.g. Daily Brief, Whale Watcher).
- **Dark/light theme:** Consistent CSS vars; toggle in nav or user settings.
- **Unified search:** Search articles, podcasts, and (when you have it) Spaces by keyword or topic.
- **Operative dashboard:** Make dashboard and operative profile clearly valuable (streak, next rank, “your brief,” recommended reads).

### 5.4 Monetization & Growth
- **Affiliate tracking:** You have AffiliatePartner and `go/<partner_key>`; add a simple admin to create partners and view clicks.
- **Sponsor ads:** You have Advertisement and Sponsor; ensure ad injection and sponsor dashboard are wired and visible.
- **Bitcoin/Lightning tips:** You have BitcoinDonation and Stripe tips; add a Lightning address or BTCPay for sats tips and show on article pages next to Stripe.

### 5.5 Reliability & Ops
- **Health endpoint:** e.g. `/health` returning DB, Stripe, and key API status for monitoring.
- **Stripe webhook idempotency:** Use `event.id` (or similar) to avoid double-processing.
- **Scheduler in production:** Run APScheduler in a separate worker process or use a cron that hits a protected `/admin/api/run-jobs` (or per-job endpoints) so restarts don’t lose jobs.

---

## 6. Quick Reference: What to Do Next

| Priority | Action |
|----------|--------|
| **P0** | Copy `monetization_service.py` into `core/services/` so premium/donate/tips work. |
| **P0** | Add a $99/mo tier in monetization_service + premium template; create Stripe Product/Price. |
| **P1** | Add Twitter API credentials to `.env`; extend `XService` with Spaces search + tweet/RT for live Spaces. |
| **P1** | Implement subscription storage (webhook → DB) and `@subscription_required` for gated features. |
| **P1** | Port scheduler (and optional telegram_bot) to core if you want Command Deck automation. |
| **P2** | Build Live Spaces alert + tweet job (thresholds, cooldowns, one tweet per Space per threshold). |
| **P2** | Add 5–7 concrete premium benefits to the $99 tier and surface them on `/premium`. |
| **P2** | Intel feed, Spaces recaps, and Nostr publish for articles/briefs. |

---

*End of audit. For implementation details, use this doc as the map and implement feature-by-feature.*
