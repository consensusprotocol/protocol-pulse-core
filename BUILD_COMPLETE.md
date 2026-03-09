# BUILD COMPLETE — F3: SCHIFF-BOT HYPOCRISY METRIC
Feature ID: f3-schiff-bot
Branch: feature/f3-schiff-bot
Completed: 2026-03-09
Commit: 484754a (post-audit second pass — 9 consensus improvements)

---

## WHAT WAS BUILT

### Service (core/services/schiff_service.py — 991 lines)
- `fetch_edgar_13f(cik)` — pulls SEC EDGAR 13F gold ETF holdings for Peter Schiff's entities
- `score_schiff_tweet(text)` — Claude Haiku classifies anti-Bitcoin sentiment 0-100
- `calculate_hypocrisy_score()` — composite: gold holdings value vs BTC performance delta
- `get_brian_verdict(score)` — "Brian" persona delivers the verdict at threshold
- SEC EDGAR API: public/free, no auth required
- CIK: Schiff's registered entities in EDGAR

### Template (templates/schiff_bot.html — 837 lines)
- Live hypocrisy meter (gauge 0-100)
- Gold holdings table from latest 13F
- Tweet sentiment feed (most recent anti-Bitcoin tweets)
- Brian's verdict panel with dark humor
- Chart: BTC performance vs gold performance (rolling)

### Cron (cron/schiff_cron.py — 88 lines)
- Weekly scrape (Tue + Fri) to match 13F quarterly cadence
- Tweet refresh every 6 hours

### Routes (core/routes.py additions)
- `GET /schiff-bot` — Schiff-Bot page
- `GET /api/schiff/hypocrisy` — live hypocrisy score
- `GET /api/schiff/holdings` — latest gold holdings from EDGAR

---

## AUDIT SUMMARY

### Audit Grade (Cycle 2 — 4/10 before second pass)
- Correctness: 3/10 → fixed in second pass (EDGAR parsing + tweet scoring)
- Security: 6/10 → retained
- 9 consensus improvements applied

### Key Findings Fixed (9 consensus improvements)
1. EDGAR 13F XML parser: wrong XPath for gold holding quantity
2. Tweet scoring: prompt injection guard added (tweet text sanitized)
3. Hypocrisy composite formula: division by zero guard when gold price = 0
4. Brian verdict: threshold calibration (was always triggering at startup)
5. Blueprint hard-fail registration
6. EDGAR request timeout + retry (3x with backoff)
7. Rate limit: EDGAR asks for polite crawling (max 1 req/10s) — enforced
8. Missing DB rollback on partial failure in score storage
9. Cache: /api/schiff/hypocrisy TTL set to 5min (was 0)

---

## REGRESSION TEST
- Result: 29 PASS | 0 FAIL | 1 WARN

---

## PBX ACTIONS REQUIRED
1. **ANTHROPIC_API_KEY** for Claude Haiku tweet scoring
2. No external API keys required for EDGAR (public/free)
3. System cron: `0 */6 * * * cd /home/ultron/protocol_pulse && python3 cron/schiff_cron.py --refresh-tweets`
4. Weekly 13F cron: `0 9 * * 2,5 cd /home/ultron/protocol_pulse && python3 cron/schiff_cron.py --refresh-13f`
