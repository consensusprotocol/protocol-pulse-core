# COST LAWS — Protocol Pulse Paid API Budget Governance
**Created:** 2026-09-19
**Status:** GOSPEL. Load into every CC session touching API call code.

---

## RULE 1: EVERY PAID API GOES THROUGH A GATEWAY
No service may call a paid API directly. Every call must go through a gateway
module that enforces daily budget limits. The gateway:
- Counts requests and estimates cost from token usage
- Enforces max_requests_per_day, max_search_calls_per_day, max_usd_per_day
- Returns a BudgetExceeded result when any limit is hit (caller degrades gracefully)
- Persists counters in a JSON file with daily auto-reset
- Exposes a status() for watchdog/dashboard consumption

## RULE 2: SEARCH TOOLS OFF BY DEFAULT
Search tools (web_search, x_search, grounding) are ONLY attached when the caller
explicitly passes allow_search=True. The only callers allowed to pass it are:
- x_reader.py (X reads via x_search — its sole purpose)
- story_engine.py harvest_xai() (reduced to 3 X-native themes)
- claim_verifier.py for quoted_statement verification only (must pass explicit tools)
Everything else runs without search tools.

## RULE 3: ONE ALERT ON BUDGET STOP
When the gateway sees HTTP 402/429 or any budget limit is hit:
- Writes an alert file the watchdog can pick up
- Sends ONE Telegram message per day (no flood)
- Never more than one Telegram per day per gateway
No more silent multi-week outages.

## RULE 4: DUAL API KEYS FOR AUDIT ISOLATION
Audit scripts (cross_llm_audit.py) use XAI_AUDIT_API_KEY via the gateway's
for_audit=True flag. This falls back to XAI_API_KEY if the audit key is unset
(with a logged warning). This prevents audit runs from consuming intel pipeline budget.

## RULE 5: FAIL PATTERN LOGGING
Every cost failure pattern must be appended to docs/QWEN_CONTEXT_BIBLE.md so the
watchdog and future CC sessions know about it.

---

## GATEWAY STATUS

| API Provider | Gateway Module | Status | Default Limits |
|-------------|---------------|--------|----------------|
| xAI/Grok | `core/services/xai_gateway.py` | LIVE | 400 req/day, 40 search/day, $1/day |
| OpenAI | — | TODO | — |
| Gemini | — | TODO | — |
| ElevenLabs | — | TODO (voice credits, not token-based) | — |
| HeyGen | — | TODO (avatar server currently DISABLED) | — |
| Anthropic | — | TODO (CC sessions use their own key) | — |

---

## FAILURE PATTERN: RUNAWAY GROK SPEND (2026-09-01 to 2026-09-05)
- **What happened:** $99.97 in 5 days, 41K requests, 59M tokens, 7,600 search calls
- **Root cause:** No budget limits. Search tools (web_search, x_search) attached to every
  automated call. 13 x_search themes in story_engine running every 2h. x_reader enabled
  with 30min cache TTL feeding 6+ social consumers.
- **Why nobody noticed:** Every downstream consumer already had graceful degradation.
  When xAI key hit account limit on Sept 5, all calls failed silently. Two weeks of
  zero Grok output and zero alerts.
- **Fix:** xai_gateway.py with hard budget caps. Search reduced to 3 themes. Article
  generation moved to Anthropic. Telegram alert on first budget stop.
