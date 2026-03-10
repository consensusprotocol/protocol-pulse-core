## SECTION 1: CORRECTNESS

### Main flow walkthrough

#### 1) Scheduled generation
`cron/briefing_cron.py` correctly registers 3 APScheduler cron jobs at 07:00, 09:30, and 16:30 ET (`cron/briefing_cron.py:65-93`). Failure isolation is good in `run_briefing()` (`40-60`).

**But there are correctness risks:**
- The service docstring says “Called by cron or manual trigger” (`core/services/briefing_service.py:275`), while the law says cron, not manual triggers. The code shown does not expose a manual route, but the service is callable from anywhere.
- No deduplication/idempotency check exists before creating a new briefing row. If cron fires twice, service restarts around schedule time, or two scheduler processes run, duplicate briefings for the same slot/day will be created (`briefing_service.py:294-315`).

#### 2) Script generation
The service fetches BTC price and recent article titles, then calls Claude Sonnet 4.6 (`briefing_service.py:147-171`). This is directionally correct.

**Correctness issues:**
- LAW 5 requires script inputs from latest articles, live BTC price, mempool stats, and network data. Only BTC price and article headlines are actually used. No mempool stats or network data are fetched anywhere.
- Script sanitization is incomplete. It replaces em dash, en dash, and ellipses after generation (`166-168`), but does not enforce:
  - max 180 words
  - no markdown
  - plain spoken English
- `asia_data` is passed into `prompt.format(...)` (`152-156`) but no prompt template uses `{asia_data}`. That suggests unfinished prompt logic.

#### 3) HeyGen generation
The payload uses the required Sarah avatar ID and 1280x720 dimensions (`174-198`). Good.

**Correctness issues:**
- The code assumes a 200 response from HeyGen generate means success (`205-211`). Many APIs use 201/202 for accepted async jobs. If HeyGen returns 201/202, this code will falsely mark it as failure.
- Polling uses `/v1/video_status.get` (`219-223`) while generation uses `/v2/video/generate` (`199-203`). That may be valid, but mixed-version API usage is a risk unless HeyGen explicitly documents this pairing.
- Poll timeout is 300 seconds (`29`, `216-240`). If HeyGen regularly takes longer, valid jobs will be marked failed.

#### 4) DB persistence
The service creates a pending `MarketBriefing`, updates it through the pipeline, and commits at each stage (`299-390`).

**Correctness issues:**
- `today = datetime.utcnow().strftime("%b %-d, %Y")` (`296`) is not portable. `%-d` breaks on some platforms. Ubuntu is fine, but this is brittle.
- Timestamps are stored in UTC, but the UI labels them as ET without conversion:
  - template uses `latest.generated_at.strftime('%-I:%M %p ET · %b %-d, %Y')` (`market_briefing.html:600`)
  - same for previous briefings (`683`)
  This is factually wrong unless `generated_at` is already ET-aware, which is not shown.
- `datetime.utcnow()` is used repeatedly despite importing timezone-aware utilities (`briefing_service.py:14`). Naive UTC datetimes can create subtle bugs.

#### 5) Briefing page rendering
The template renders a featured/latest briefing and a previous briefings grid (`market_briefing.html:555-696`).

**Correctness issues:**
- LAW 3 says “Always show last 3 briefings below the live/latest briefing: always render the 3 previous briefings.” The template merely renders whatever `recent` contains (`657-690`). If the route passes 1, 2, 4, or includes the latest again, the law is violated. The route code is not shown, so this is at best unproven.
- The previous-card click swaps only the video URL and title (`786-838`). It does **not** update:
  - timestamp
  - duration
  - BTC at generation
  - script panel content
  This makes the featured metadata incorrect after selecting a previous briefing.
- `data-script="{{ b.script_text | truncate(300) }}"` is set (`662`) but never used in JS. The script panel remains tied to the original latest briefing only.
- If a previous briefing is selected, the poster thumbnail is not updated on the featured player.

#### 6) Countdown / polling
The countdown is client-side and visually fine.

**Correctness issues:**
- `toETDate()` uses `toLocaleString(... timeZone: 'America/New_York')` then `new Date(etStr)` (`714-718`). This is a common hack and can be locale/browser fragile.
- Countdown ignores seconds, so near slot boundaries it can show stale values up to 59 seconds.
- `pollLatest()` fetches `/api/briefing/latest` every 2 minutes (`847-865`), but no loading/error state is shown if that endpoint fails. It silently swallows errors.
- If `latest.status == 'generating'`, page reloads every 30s (`840-845`). If generation is stuck for a long time, this creates repeated reload churn.

#### 7) App-level concerns
- `db.create_all()` at startup (`app.py:241-247`) in a migrated app is dangerous. It can mask migration drift and create schema inconsistencies.
- Default rate limit is `200 per day` globally (`96`). That is likely too blunt and may break normal traffic while still not protecting expensive generation endpoints if they are exempt or internal.

### N+1 / query issues
From shown code:
- No obvious N+1 in the template itself.
- `_get_top_headlines()` does one bounded query (`133-139`).
- `_check_cost_guard()` does one count query (`249-257`).

### Race conditions
- **Duplicate generation race**: no uniqueness guard for one briefing per slot/day (`briefing_service.py:294-315`).
- **Cost guard race**: `_check_cost_guard()` and insert are not atomic. Two concurrent workers can both pass the guard and both create records (`243-266`, `294-308`).
- **UI state race**: page polling may reload while a user is watching a previous briefing.

---

## SECTION 2: LAW COMPLIANCE

### LAW 1: HeyGen Sarah is the ONLY avatar for Briefing Room
**Status: PARTIAL**
- Correct Sarah avatar ID used: `core/services/briefing_service.py:25`, `181`
- Resolution 1280x720 met: `195`
- No Wav2Lip use in shown briefing code: compliant by absence

**Partial because:**
- No enforcement that only this avatar can ever be used beyond a constant in code. No validation layer or DB constraint prevents future misuse.
- No duration/cost guard tied to 2 minutes per briefing. There is only a count-based guard (`31-32`, `243-266`), not a duration/budget guard.

### LAW 2: Three briefings per day, fixed schedule
**Status: PARTIAL**
- Cron schedule exists at correct ET times: `cron/briefing_cron.py:65-93`
- Retry cap of 2 attempts for HeyGen generation exists: `briefing_service.py:30`, `333-343`

**Partial because:**
- No guard ensures exactly one briefing per slot/day. Duplicates are possible.
- Polling failures/timeouts are not retried, only generation submission is retried.
- The service docstring still references manual trigger usage: `briefing_service.py:275`

### LAW 3: Always show last 3 briefings
**Status: PARTIAL / likely VIOLATION**
- Template has a previous briefings section: `market_briefing.html:650-696`

**But:**
- No evidence it always shows exactly 3 previous briefings. It renders arbitrary `recent` (`657-690`).
- No evidence the route excludes the latest from `recent`.
- Empty state exists, but the permanent rule is not enforced in the shown code.

### LAW 4: /stage → 302 redirect → /briefing
**Status: UNVERIFIABLE / PARTIAL**
- `market_briefing.html` exists as required.
- But no route code is shown for `/stage` or `/briefing`, so compliance cannot be confirmed.
- No proof of permanent 302 redirect.

### LAW 5: Scripts are Claude-generated, not hardcoded
**Status: PARTIAL**
- Claude Sonnet 4.6 is used at generation time: `briefing_service.py:158-164`
- Prompt rules include no em dashes, no ellipses, no markdown, plain spoken English: `45-86`
- Post-processing removes em dash / en dash / ellipses: `166-168`

**Partial because:**
- Missing required data sources: mempool stats and network data are not fetched or injected.
- No hard enforcement of 90 seconds / ~180 words.
- No markdown scrub beyond prompt instruction.
- No validation pass before publishing.

---

## SECTION 3: SECURITY

### Good
- No raw SQL shown; ORM usage appears safe from SQL injection.
- External requests use timeouts consistently in `briefing_service.py`.
- Cron catches exceptions and avoids scheduler crash (`cron/briefing_cron.py:57-60`, `98-101`).

### Issues

#### 1) Hardcoded insecure Flask secret fallback
**`app.py:46`**
- `app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key_protocol_pulse_2026")`
- In production, if env is missing, sessions become forgeable with a known secret.

#### 2) CSRF token generation without enforcement shown
**`app.py:115-126`**
- Token is injected into templates, but no validation middleware or form protection is shown. This can create false confidence.

#### 3) CORS wildcard on SocketIO
**`app.py:111`**
- `cors_allowed_origins="*"` is broad. If any authenticated socket features exist, this is risky.

#### 4) Rate limiting does not protect paid generation path
- Global `200 per day` (`app.py:96`) is not enough to protect expensive operations.
- No shown auth/authorization or per-endpoint limiter around briefing generation.
- If any route exists to trigger `generate_briefing()`, one user could burn HeyGen budget.

#### 5) Potential XSS in ad injection filter
**`app.py:175-183`**
- `ad.image_url` and `ad.name` are interpolated directly into HTML.
- If ad content is admin-controlled but not sanitized, stored XSS is possible.

#### 6) Logging sensitive third-party error bodies
**`briefing_service.py:210-211`**
- Logs first 300 chars of HeyGen response text. Usually okay, but if provider echoes request metadata, this can leak content.

---

## SECTION 4: FRONTEND QUALITY

### What’s good
- Visual direction is strong: typography, spacing, dark premium look, CSS-only animations.
- Responsive breakpoints exist (`520-530`).
- Empty states for no video / no previous briefings are present.
- Loading overlay exists for player swaps.

### Problems

#### 1) Featured metadata becomes wrong after selecting a previous briefing
**`market_briefing.html:786-838`**
- Only title and video source update.
- Timestamp, duration, type pill, BTC-at-generation, and script remain stale.
- This is the biggest UX correctness flaw.

#### 2) ET timestamps are hardcoded labels, not converted
**`600`, `683`**
- This will display UTC values as ET unless backend already converts them.

#### 3) Async states are incomplete
- `pollLatest()` has no visible error state (`847-865`).
- `loadBriefing()` has loading and silent failure, but no user-facing error state if video fails (`829-831` only hides spinner).
- No fallback if `/api/briefing/latest` returns malformed JSON.

#### 4) Accessibility / semantics are weak
- Previous briefing cards are clickable `<div>`s with `onclick` (`659-663`), not buttons/links.
- Keyboard accessibility is poor.
- “View All →” is hardcoded arrow text, okay visually but not ideal.

#### 5) Script panel implementation is incomplete
- Previous cards include `data-script` (`662`) but JS never updates script panel.
- Truncating script to 300 chars in a data attribute is wrong if full script should be viewable.

#### 6) Prototype smell
- Inline CSS and JS inside an 870-line template is maintainability debt.
- World-class products would split this into reusable assets and stronger state handling.

---

## SECTION 5: BACKEND QUALITY

### Good
- External API calls have timeouts.
- DB writes generally use try/except with rollback.
- Cron is resilient and won’t crash on job failure.
- Logging exists at key steps.

### Problems

#### 1) Not every write is safely rolled back
- Some commits are wrapped, but object state mutation happens before commit and after rollback the in-memory object may be stale.
- Example: after poll failure, `briefing.status` and `error_message` are set then commit attempted (`365-371`). If commit fails, rollback happens but function still returns error based on object state, not persisted state.

#### 2) App context imports are awkward and fragile
**`briefing_service.py:130-132`, `247-248`, `292`**
- Importing `from app import app, db` inside service functions is brittle and tightly coupled.
- This can break in alternate execution contexts and complicates testing.

#### 3) `db.create_all()` at runtime
**`app.py:241-247`**
- This is not production-grade for a migration-managed app.

#### 4) Cost guard is too weak
**`243-266`**
- It limits count per hour, not actual spend, duration, or per-slot generation.
- It is also race-prone.

#### 5) Logging lacks enough context
- Failures don’t consistently include `briefing_type`, `briefing_id`, and attempt number together.
- Example: script generation failure logs only exception (`169-171`), not which briefing type/title.

#### 6) API compatibility assumptions
- Generate endpoint only accepts 200 (`205`).
- Poll endpoint shape is assumed without schema validation (`225-236`).

---

## SECTION 6: WORLD-CLASS GAP ANALYSIS

Material gaps only:

1. **No editorial/data validation layer before publish**
   - A premium product would validate script length, prohibited formatting, factual inputs present, and maybe confidence score before spending on video render.

2. **No slot/day idempotency**
   - Professional scheduled media systems guarantee one canonical asset per slot, with dedupe and rerun semantics.

3. **Archive UX is shallow**
   - The page is visually polished, but not operationally premium. Selecting an older briefing should fully hydrate all metadata and transcript, with shareable permalinks.

4. **No observability for paid pipeline**
   - Missing structured metrics: generation latency, HeyGen failure rate, Claude failure rate, average duration, cost/day, slot completion SLA.

5. **No fallback publishing strategy**
   - If HeyGen fails, a premium product might still publish transcript + audio + “video unavailable” state rather than a dead slot.

What is already good:
- The visual design direction is strong.
- The cron schedule and basic failure isolation are solid.
- The HeyGen avatar/resolution choices align with the product spec.

---

## SECTION 7: SCORES

- Backend logic:    72/100
- Frontend/UI:      74/100
- Error handling:   76/100
- Security:         63/100
- Performance:      78/100
- Law compliance:   68/100
- World-class gap:  58/100
- OVERALL:          70/100

---

## SECTION 8: PRIORITY ACTION PLAN

P0 CRITICAL | Enforce one canonical briefing per slot/day with DB uniqueness + idempotent generation guard | core/services/briefing_service.py:294-315 | duplicate cron fires or multiple scheduler processes will create duplicate paid videos and violate the fixed-schedule product contract

P0 CRITICAL | Add a strict post-generation script validator for word count, markdown, em dash/ellipsis, and required data presence before sending to HeyGen | core/services/briefing_service.py:147-171 | invalid scripts will be published or paid renders will be wasted on non-compliant content

P0 CRITICAL | Implement required LAW 5 data inputs: mempool stats and network data, not just BTC price and headlines | core/services/briefing_service.py:102-156 | the product is currently not generating the mandated intelligence inputs and is materially off-spec

P0 CRITICAL | Remove hardcoded production secret fallback and fail closed in non-dev environments | app.py:46 | a missing env var would make session forgery trivial in production

P1 HIGH     | Fix featured-player state hydration so selecting a previous briefing updates title, timestamp, duration, type, BTC-at-generation, poster, and script | core/templates/market_briefing.html:586-633, 656-689, 786-838 | users will see mismatched metadata and transcript, which undermines trust in a premium intelligence product

P1 HIGH     | Convert timestamps to America/New_York instead of labeling naive/UTC datetimes as ET | core/templates/market_briefing.html:600, 683 | displayed times will be wrong in production and directly violate the schedule semantics

P1 HIGH     | Enforce exactly 3 previous briefings in backend route/query, excluding latest, and guarantee rendering contract | core/templates/market_briefing.html:656-690 | LAW 3 is not actually enforced and the page may show the wrong number of archive items

P1 HIGH     | Harden HeyGen API handling to accept documented async success codes and validate response schema | core/services/briefing_service.py:199-211, 219-236 | valid provider responses may be misclassified as failures, causing skipped briefings

P1 HIGH     | Add endpoint-level auth/rate limiting around any manual or internal generation trigger | core/services/briefing_service.py:273-403, app.py:96-97 | one actor could exhaust paid API budget if a trigger route exists or is later added without protection

P2 MEDIUM   | Replace app-context imports inside service functions with injected dependencies or application factory patterns | core/services/briefing_service.py:129-132, 247-248, 292-294 | current coupling is brittle, hard to test, and prone to import-context bugs

P2 MEDIUM   | Replace runtime `db.create_all()` with migration-only schema management in production | app.py:241-247 | schema drift will be harder to detect and debug

P2 MEDIUM   | Add visible error state for failed player loads and failed `/api/briefing/latest` polling | core/templates/market_briefing.html:829-831, 847-865 | silent failures make the UI feel broken and opaque

P2 MEDIUM   | Sanitize ad HTML interpolation or escape fields before injecting into markup | app.py:175-183 | admin/content-originated XSS is possible if ad fields are not trusted

P2 MEDIUM   | Move inline CSS/JS into versioned static assets | core/templates/market_briefing.html:17-531, 702-869 | maintainability and cacheability are weaker than they should be for a high-traffic page

P3 LOW      | Replace `%-d` strftime usage with portable formatting helpers | core/services/briefing_service.py:296, core/templates/market_briefing.html:600, 683 | portability issue and minor brittleness

P3 LOW      | Improve countdown implementation using exact zoned time math instead of locale-string roundtrip | core/templates/market_briefing.html:714-718 | current approach is serviceable but not robust

P3 LOW      | Add structured logging fields for briefing_type, briefing_id, slot, and attempt across all failure paths | core/services/briefing_service.py:169-171, 210, 237-238, 259-262 | production debugging will be slower than necessary

---

## SECTION 9: THE ONE THING

Make briefing generation idempotent and validated end-to-end, because right now the system can both publish off-spec content and charge you twice for the same slot.

---

## SECTION 10: FINAL VERDICT

This is **not production-ready yet** for a premium scheduled video product. The visual foundation is good and the cron/HeyGen pipeline is close, but duplicate-generation risk, incomplete LAW 5 data inputs, incorrect ET timestamp handling, and broken featured-player metadata must be fixed before merge.