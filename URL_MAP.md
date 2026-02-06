# Protocol Pulse – URL map (visual sitemap)

Base URL when running locally: **http://127.0.0.1:5000** (or the port in your `.env`).

---

## Public pages

| URL | Description |
|-----|-------------|
| `/` | Home |
| `/articles` | Article listing |
| `/articles/<id>` | Single article |
| `/category/<category>` | Category (Bitcoin, DeFi, etc.) |
| `/podcasts` | Podcasts |
| `/bitcoin` | Bitcoin section |
| `/defi` | DeFi section |
| `/regulation` | Regulation |
| `/privacy` | Privacy |
| `/innovation` | Innovation |
| `/about` | About |
| `/contact` | Contact |
| `/login` | Login |
| `/signup` | Signup |
| `/dashboard` | Dashboard |
| `/clips` | Clips |
| `/chat` | Chat |
| `/sentiment` | Sentiment |
| `/sarah-briefing` | Sarah's briefing |
| `/merch` | Merch store |
| `/donate` | Donate |
| `/donate/bitcoin` | Bitcoin donate |
| `/donate/thanks` | Donate thanks |
| `/premium` | Premium |
| `/subscribe/premium/<tier>` | Premium subscribe |
| `/subscription/success` | Subscription success |
| `/cypherpunks` | Cypherpunks |
| `/guides/cold-storage` | Cold storage guide |
| `/sovereign-custody` | Sovereign custody |
| `/meetup-map` | Meetup map |
| `/logistics` | Logistics |
| `/go/<partner_key>` | Affiliate / partner |
| `/bitcoin-music` | Bitcoin music |
| `/bitcoin-artists` | Bitcoin artists |
| `/freedom-tech` | Freedom tech |
| `/operative/<slug>` | Operative profile |
| `/scorecard` | Scorecard |
| `/drill` | Drill |
| `/operator-costs` | Operator costs |
| `/solo-slayers` | Solo slayers |
| `/extension` | Extension |
| `/extension/download` | Extension download |

---

## Live / feeds / media

| URL | Description |
|-----|-------------|
| `/live` | Live |
| `/bitfeed-live` | Bitfeed live |
| `/kinetic` | Kinetic |
| `/gravity-well` | Gravity well |
| `/hud` | HUD |
| `/map` | Map |
| `/whale-watcher` | Whale watcher |
| `/value-stream` | Value stream |
| `/signal-terminal` | Signal terminal |
| `/media` | Media hub |
| `/media-hub` | Media hub (alias) |
| `/rss/podcasts.xml` | Podcast RSS feed |
| `/api/media/feed` | Media feed API |
| `/api/media/sentiment` | Media sentiment API |
| `/api/verified-signals` | Verified signals |

---

## APIs (examples)

| URL | Methods | Description |
|-----|---------|-------------|
| `/api/network-data` | GET | Network data |
| `/api/latest-episodes` | GET | Latest podcast episodes |
| `/api/episodes/<show_id>` | GET | Episodes by show |
| `/api/episodes/search` | GET | Search episodes |
| `/api/whales` | GET | Whales |
| `/api/whales/live` | GET | Live whales |
| `/api/whales/save` | POST | Save whale tx |
| `/api/donate/lightning` | POST | Lightning donation |
| `/api/chat/ask` | POST | Chat |
| `/api/subscribe` | POST | Subscribe |
| `/api/latest-articles` | GET | Latest articles |
| `/api/reddit-trends` | GET | Reddit trends |
| `/api/analytics/*` | GET/POST | Analytics |
| `/api/activity-heatmap` | GET | Activity heatmap |
| `/api/rtsa/products` | GET | RTSA products |
| `/api/hot-ticker` | GET | Hot ticker |

---

## Admin (login required)

| URL | Description |
|-----|-------------|
| `/admin` | Admin home |
| `/admin/write` | Write article |
| `/admin/edit/<id>` | Edit article |
| `/admin/delete/<id>` | Delete article |
| `/admin/ads` | Ads |
| `/admin/generate` | Generate content |
| `/admin/generate-content` | Generate content |
| `/admin/publish-to-substack/<id>` | Publish to Substack |
| `/admin/launch-sequences` | Launch sequences |
| `/admin/launch-sequence/create` | Create sequence |
| `/admin/target-alerts` | Target alerts |
| `/admin/nostr` | Nostr |
| `/admin/intelligence` | Intelligence |
| `/admin/reply-squad` | Reply squad |
| `/admin/analytics` | Analytics |
| `/admin/autopost` | Autopost |
| `/admin/command-deck` | Command deck |
| `/admin/supervisor` | Supervisor |
| `/admin/segments` | Segments |
| `/admin/captions` | Captions |
| `/admin/revenue` | Revenue |
| `/admin/rtsa` | RTSA |
| `/admin/crm-setup` | CRM setup |
| `/admin/sentiment-report` | Sentiment report |
| … | (many more under `/admin/*`) |

---

## Webhooks

| URL | Description |
|-----|-------------|
| `/webhook/printful` | Printful webhook |
| `/webhook/stripe` | Stripe webhook |

---

## How to see this in the browser

1. **Start the app** (from `core/`):
   ```bash
   .venv/bin/python app.py
   ```
   Or with a different port:
   ```bash
   PORT=5001 .venv/bin/python app.py
   ```

2. **Open in the browser**:  
   - Main site: **http://127.0.0.1:5000** (or your port).  
   - Try: `/`, `/articles`, `/dashboard`, `/login`, etc.

3. **List all routes in the terminal** (optional):
   ```bash
   cd core && .venv/bin/python -c "
   from app import app
   for r in sorted(app.url_map.iter_rules(), key=lambda x: x.rule):
       print(r.rule, r.methods - {'HEAD','OPTIONS'})
   "
   ```

You now have both a **URL visual** (this file) and a way to **see the app** at real URLs in the browser.
