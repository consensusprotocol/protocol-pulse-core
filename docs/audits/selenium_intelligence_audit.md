# Intelligence Scraper Audit: Selenium → Playwright Adaptation
# Date: 2026-04-08
# Status: BUILT + TESTED — 2/3 targets operational

## Environment Constraints (discovered during build)
- **No Chrome/Chromium installed** — no sudo access to install
- **Playwright IS available** — Chromium at `~/.cache/ms-playwright/chromium-1208/`
- **No Tesseract OCR** — using network interception instead of screenshot+OCR
- **efts.house.gov DNS unreachable** — confirmed: domain doesn't resolve

## Architecture Decision: Playwright over Selenium
Playwright advantages:
1. Already installed on Ultron (confirmed import)
2. Built-in network interception (capture API calls charts make)
3. Better anti-detection than undetected-chromedriver
4. Auto-manages browser binaries (Chromium confirmed at 145.0.7632.6)
5. Better handling of SPAs (React/Next.js charts)

## Test Results (2026-04-08)

### Glassnode Studio — PARTIAL SUCCESS
- **SOPR**: `0.998293` — captured via API interception (free tier)
- **MVRV Z-Score**: GATED — requires Professional API key ($799/mo)
- **Puell Multiple**: GATED — requires Professional API key
- **aSOPR**: GATED — requires Professional API key
- Only `price_usd_close` loads without auth (5744 datapoints)
- SOPR is one of few free-tier metrics with chart data

### CryptoQuant — SCREENSHOT ONLY
- Chart renders visually (Exchange Reserve shows ~2.7M BTC)
- API data not interceptable: uses WebSocket or authenticated internal API
- Chart image saved for manual review
- Tooltip hover fallback attempted but CSS selectors vary

### Congress (House Clerk) — FULL SUCCESS
- Playwright submits ASP.NET form at `disclosures-clerk.house.gov/FinancialDisclosure/ViewSearch`
- Form fields: LastName, FilingYear (2026), State, District, __RequestVerificationToken
- 10+ PTR filings scraped per run
- efts.house.gov Elasticsearch API fallback (DNS currently down)

## Data Integration Verified
- `signals.json`: SOPR field updated from `null` → `0.998293` with source `"glassnode (scraped)"`
- `pro_metrics_cache.json`: timestamp updated
- Atomic writes via .tmp → rename pattern

## Anti-Detection Strategy (implemented)
1. Random delays (2-8s between page loads)
2. Realistic viewport (1920x1080)
3. User-agent rotation from pool of 8 real Chrome/Firefox/Safari UAs
4. Stealth: `navigator.webdriver` override via init_script
5. `domcontentloaded` wait strategy (avoids SPA networkidle timeouts)
6. Once-daily frequency (4am ET cron)

## Legal/ToS Assessment (from audit research)
- hiQ v. LinkedIn (Ninth Circuit): scraping public data ≠ CFAA violation
- No login/authentication bypass — only public free-tier data
- Respecting rate limits: max 1 visit per site per day
- House clerk data is public government records
- Screenshots saved with attribution

## Cron Configuration
```
# Daily at 4am ET (off-peak)
0 4 * * * cd /home/ultron/protocol_pulse && python3 services/selenium_intelligence_scraper.py >> logs/selenium_intel.log 2>&1
```

## Future Improvements
1. Obtain Glassnode API key for MVRV/Puell/aSOPR
2. CryptoQuant: investigate WebSocket protocol for live data
3. Add Senate disclosures via efdsearch.senate.gov
4. Consider Camoufox for sites that detect Playwright
