# Protocol Pulse — Full Scope & Deliverables (Cross-Analysis Reference)

**Purpose:** Single reference for what was requested (including paid/premium tier), full feature scope, and what has been implemented in code. Use for code review or cross-analysis.

---

## Part 1: What You Asked For (Requested Features)

### A. Paid / Premium Tier (from project docs)

From **REVENUE_FEATURES.md**, **PROJECT_OVERVIEW_AND_AUDIT.md**, and **FUTURE_TASKS.md**:

| Tier | Price | Description |
|------|-------|-------------|
| **Free** | $0 | Standard site access |
| **Operator** | $21/mo | Starter paid |
| **Commander** | **$99/mo** | “Premium Hub” — real-time command center; block height, hashrate, difficulty, mempool, BTC price, Live Terminal, Whale Watcher, Pro Briefs |
| **Sovereign** | $210/mo | Elite: full access, monthly ask, 1-on-1 |

**Premium features requested:**
- **Premium Hub** (`/hub`) — Commander+ only; real-time network intel, whale feed, Pro Briefs, live tools.
- **Stripe** — `checkout.session.completed` webhook sets `subscription_tier`, `stripe_customer_id`, `stripe_subscription_id` on User.
- **Premium page** (`/premium`) — Four tiers; Commander highlighted as “Best value”; “Get Premium Hub” / “Go to Premium Hub” if already Commander+.
- **Gating** — `@premium_required` or equivalent for Commander+ routes (e.g. `/hub`).
- **Database** — User: `subscription_tier`, `stripe_customer_id`, `stripe_subscription_id`, `subscription_expires_at`; tables: `affiliate_product`, `affiliate_click`.
- **Smart Analytics** (admin) — Page views, sessions, top pages, traffic by category, premium subscriber count, MRR.
- **Affiliate** — AffiliateProduct, AffiliateClick; generate affiliate articles with referral links; track clicks.

**Sovereign tier (future, post–4090):**
- **$100/mo** “Digital Intelligence Agency” — Personal Pulse Analyst (voice-activated, GPU briefs), Nostr Shadow-Feed, Live Dossier metrics, Grok “Pulse Wire” alerts, dedicated 4090 “intelligence lane,” interactive Dossier strategy builder.
- **FUTURE_TASKS.md** describes: Stripe/BTCPay, `user_tier` (Standard vs Sovereign), DossierLive module, Sovereign Dashboard (gold + deep red), Personal Analyst, etc.

---

### B. Dossier (Sovereign 7) — Requested in conversation

- **Condense** the Dossier into **7 Definitive Chapters** (“Sovereign 7”).
- **UI:** Single-page, horizontal scroll, 7 sections; **Sovereignty Tracker** at top that fills as user scrolls.
- **Aesthetic:** Red (#DC2626), Black (#000000), White (#FFFFFF) Cyberpunk theme.
- **Per section:** Image + narrative + **Deep Dive** button opening a modal with technical intel (Key Metric, The Math, Technical Insight).
- **Mobile-responsive** (e.g. iPhone).
- **Navigation:** Smooth scroll; prev/next arrows; dot nav; keyboard arrows; Deep Dive modal shows chapter image + Previous/Next chapter.
- **Classic:** 32-slide full Dossier still available at `/dossier/classic`.
- **Content:** Seven chapters with provided narratives and Technical Intel Sheets (Infinite Printing Press, Nixon Shock, Scarcity Wall, Difficulty Adjustment, Energy Shield, S-Curve, Sovereign Custody).

---

### C. 4090 Server & Medley Engine — Requested in conversation

**Phase 1 – Hardware & drivers**
- Verify `nvidia-smi`; all 4090s detected.
- Install **nvtop** for thermal monitoring.

**Phase 2 – Video infrastructure**
- **ffmpeg** with **libnvenc** (render on 4090s).
- **yt-dlp** for content scraping.
- **faster-whisper** for GPU transcription (GPU 0).

**Phase 3 – Medley Engine**
- Python project under **`~/protocol_pulse`**.
- Monitor YouTube channels for new daily uploads.
- Extract **60-second “Alpha” clips** (Bitcoin-related keywords).
- Merge clips with **smooth cross-dissolve**.
- Append **branding tag** at end.

**Production-grade (later request):**
1. **Directory architecture**
   - `~/protocol_pulse/sponsors/slot_1/` (mid-roll)
   - `~/protocol_pulse/sponsors/slot_2/` (pre-outro)
   - `~/protocol_pulse/branding/` (tag.mp4)
   - `~/protocol_pulse/output/` (final renders)

2. **News Oracle**
   - Ping latest Bitcoin news (free RSS or NewsAPI).
   - “Trending Keywords” for the day (e.g. Saylor, ETF Inflows, Hashrate).
   - Pass to selection logic.

3. **Viral-Pulse selection**
   - Editorial prompt: *“Act as a world-class Bitcoin media editor. Scan the transcripts for segments that overlap with today’s breaking news and trending topics. Prioritize high-conviction insights and technical breakthroughs. Ignore evergreen content unless it provides a direct counter-narrative to current FUD. Target 60-second Alpha clips with high-energy delivery.”*

4. **Ad-Weaver**
   - **Slot 1:** If file in `sponsors/slot_1/`, insert after first two content clips.
   - **Slot 2:** If file in `sponsors/slot_2/`, insert immediately before tag.mp4.
   - Use **h264_nvenc** and CUDA for 4090 transcoding.

5. **Remote sustainability**
   - Cron or internal timer: **daily at 6 PM**.
   - Logs to **`~/protocol_pulse/logs/daily_report.log`** (check remotely via Cursor).

6. **Dashboard**
   - Folder structure in Cursor = dashboard.
   - Update sponsors: replace file in slot_1 or slot_2.
   - Check progress: open `daily_report.log` (“Render Complete” → video in `output/`).
   - Watch render: right-click finished .mp4 in Cursor → Download.

**Assets you provided:**
- **tag.mp4** → `medley_engine/branding/tag.mp4`
- **sponsor_1.mp4** → `medley_engine/sponsors/slot_1/sponsor_1.mp4`
- **slot_2.mp4** → `medley_engine/sponsors/slot_2/slot_2.mp4`

---

## Part 2: What Exists in Code (Deliverables)

### Web app (core/)

| Feature | Status | Location / notes |
|--------|--------|------------------|
| **Dossier (Sovereign 7)** | Implemented | `/dossier` → `dossier.html` (7 chapters, tracker, Deep Dive modals, arrows/dots, image + nav). `dossier_classic.html` = 32-slide at `/dossier/classic`. |
| **Dossier data** | Implemented | `core/static/data/sovereign7_manifest.json` + fallback in `routes.py` (`SOVEREIGN7_CHAPTERS_FALLBACK`). Images: `core/static/images/dossier/sovereign7/*.png`. |
| **Premium tiers** | In codebase | `/premium`, `/hub`, `/subscribe/premium/<tier>`, Stripe webhook; templates `premium.html`, `premium_hub.html`; `has_commander_tier()` etc. |
| **monetization_service** | **Missing in core** | Referenced by routes; exists in `_replit_import/services/monetization_service.py`. **Not** in `core/services/`. Premium/donate/tips can 500 until copied. |
| **Smart Analytics** | In codebase | `/admin/smart-analytics` (admin). |
| **Affiliate** | In codebase | Models, seed, generate-affiliate-article; tracking. |

### Medley Engine (medley_engine/)

| Feature | Status | Location / notes |
|--------|--------|------------------|
| **Directory layout** | Implemented | `branding/`, `channels/`, `clips/`, `output/`, `logs/`, **`sponsors/slot_1/`**, **`sponsors/slot_2/`**. |
| **Branding & sponsor assets** | In repo | `branding/tag.mp4`, `sponsors/slot_1/sponsor_1.mp4`, `sponsors/slot_2/slot_2.mp4`. |
| **run_medley.py** | Implemented | Fetch uploads (yt-dlp), transcribe (faster-whisper), keyword-based Alpha windows, merge with xfade, append branding. **No** News Oracle, **no** Viral-Pulse LLM prompt, **no** Ad-Weaver (slot_1/slot_2 injection) in current merge pipeline. |
| **config.yaml** | Implemented | Paths, channels, alpha_keywords, clip_duration_seconds, cross_dissolve_duration, whisper_device/model, max_clips_per_medley. |
| **News Oracle** | **Not implemented** | Requested: RSS/NewsAPI → trending keywords → pass to selection. |
| **Viral-Pulse (LLM/editorial)** | **Not implemented** | Requested: editorial prompt + “trending + breaking news” selection logic. |
| **Ad-Weaver** | **Not implemented** | Requested: insert slot_1 after 2 clips, slot_2 before tag; NVENC. Current merge does not read sponsors/slot_1 or slot_2. |
| **Daily 6 PM + daily_report.log** | **Not implemented** | No cron entry or runner script that logs to `logs/daily_report.log`. |
| **NVENC** | Partially implemented | `run_medley.py` tries `h264_nvenc` then falls back to libx264; no explicit CUDA device selection. |

### 4090 server setup

| Feature | Status | Location / notes |
|--------|--------|------------------|
| **setup_4090_medley.sh** | Implemented | `scripts/setup_4090_medley.sh`: Phase 1 (nvidia-smi, nvtop), Phase 2 (ffmpeg, yt-dlp, faster-whisper venv), Phase 3 (mkdir layout). |
| **Deploy doc** | Implemented | `DEPLOY_4090_MEDLEY.md`: rsync, run setup, deploy medley_engine, config, run. |
| **Cron 6 PM** | Not in repo | You add on server: e.g. `0 18 * * * cd ~/protocol_pulse && ./venv/bin/python run_medley.py --daily >> logs/daily_report.log 2>&1`. |

### Git / repo

- **Remote:** `origin` = `https://github.com/consensusprotocol/protocol-pulse-core.git`.
- **main** has Dossier + medley_engine (including branding + sponsor slots); tag.mp4 and medley layout are committed.

---

## Part 3: Summary Table for Cross-Analysis

| Requested feature | Delivered in code? | Where to look |
|-------------------|--------------------|----------------|
| Premium tiers (Operator / Commander / Sovereign) | Yes (routes + templates) | `core/routes.py`, `premium.html`, `premium_hub.html`, User model |
| Stripe webhook → subscription_tier | Yes (if monetization_service present) | Webhook handler; **monetization_service missing in core** |
| Premium Hub (/hub) gated | Yes | `premium_required`, Commander/Sovereign check |
| Dossier Sovereign 7 (7 chapters, tracker, Deep Dive) | Yes | `core/templates/dossier.html`, `core/routes.py`, sovereign7 manifest/fallback |
| Dossier classic (32-slide) | Yes | `dossier_classic.html`, `/dossier/classic` |
| Medley dirs (sponsors/slot_1, slot_2, branding, output) | Yes | `medley_engine/sponsors/slot_1`, `slot_2`, `branding/`, `output/` |
| Medley: fetch uploads, Whisper, keyword clips, merge, tag | Yes | `medley_engine/run_medley.py` |
| Medley: News Oracle (RSS/trending keywords) | No | — |
| Medley: Viral-Pulse (LLM editorial prompt) | No | — |
| Medley: Ad-Weaver (slot_1 after 2 clips, slot_2 before tag) | No | — |
| Medley: daily 6 PM + daily_report.log | No (cron not in repo) | Add cron on server; optional runner script |
| 4090 setup script (nvtop, ffmpeg, yt-dlp, faster-whisper) | Yes | `scripts/setup_4090_medley.sh` |
| Sovereign tier ($100, GPU briefs, DossierLive, etc.) | No (future) | **FUTURE_TASKS.md** |

---

## Part 4: Files to Hand to a Code Analyst

**Premium / revenue:**
- `core/routes.py` (premium, subscribe, webhook, hub)
- `core/templates/premium.html`, `core/templates/premium_hub.html`
- `core/models.py` (User subscription fields, AffiliateProduct, AffiliateClick)
- `REVENUE_FEATURES.md`, `PROJECT_OVERVIEW_AND_AUDIT.md`
- **Missing:** `core/services/monetization_service.py` (copy from `_replit_import/services/` if needed)

**Dossier:**
- `core/templates/dossier.html`, `core/templates/dossier_classic.html`
- `core/routes.py` (dossier, dossier_classic, _get_sovereign7_chapters)
- `core/static/data/sovereign7_manifest.json`
- `core/static/images/dossier/sovereign7/*.png`

**Medley Engine:**
- `medley_engine/run_medley.py` (main pipeline)
- `medley_engine/config.yaml`
- `medley_engine/requirements.txt`
- `medley_engine/README.md`
- `medley_engine/branding/tag.mp4`, `medley_engine/sponsors/slot_1/`, `medley_engine/sponsors/slot_2/`
- `scripts/setup_4090_medley.sh`
- `DEPLOY_4090_MEDLEY.md`

**Future / Sovereign:**
- `FUTURE_TASKS.md` (Sovereign tier, Avatar cinema mode, etc.)

---

*Document generated for cross-analysis. Last updated to match repo state as of this session.*
