Here is a forensic code review of the `f2-briefing-room` feature.

### SECTION 1: CORRECTNESS

The code is largely correct and logically sound, but there are several subtle bugs and oversights.

-   **[BUG] Incorrect User Experience on Playback:** In `market_briefing.html`, the `loadBriefing` Javascript function (line 786) is designed to load a previous briefing into the main player. However, it only updates the `<video>` source and the main title (`#featuredTitle`). It fails to update the associated metadata (timestamp, duration, BTC price) or the script shown in the script panel. This leads to a confusing state where a user is watching an old video but seeing the metadata and script for the latest one.
-   **[BUG] Unreliable Countdown Timer:** The Javascript countdown timer in `market_briefing.html` (lines 714-718) uses `nowUTC.toLocaleString('en-US', { timeZone: 'America/New_York' })` and then passes the resulting string to `new Date()`. This is a known anti-pattern and is notoriously unreliable across different browsers, operating systems, and user locales, which will result in the "Next Briefing In" timer being wrong for a significant portion of users.
-   **[BUG] Incomplete Cost Guard Logic:** The `_check_cost_guard` function in `briefing_service.py` (line 254) checks for recent briefings with a status of `'generating'` or `'completed'`. It does not include `'failed'`. A generation process can fail *after* the most expensive API call (e.g., to Claude) has already been made. By not counting failed attempts, the cost guard could allow budget overruns in a persistent failure scenario.
-   **[LOGIC FLAW] Hardcoded Placeholder Data:** In `briefing_service.py` (line 155), the `asia_data` variable passed to the script-generation prompt is a hardcoded string: `"Asian markets closed mixed; see latest data."`. This undermines the feature's claim of providing timely intelligence on Asian market closes and makes the pre-market briefing less valuable.

### SECTION 2: LAW COMPLIANCE

-   **LAW 1: HeyGen Sarah is the ONLY avatar for Briefing Room**
    -   **Verdict:** COMPLIANT
    -   **Evidence:** `briefing_service.py:25` correctly uses `SARAH_AVATAR_ID` 'd259...b4e'. `briefing_service.py:195` specifies the correct `1280x720` resolution. No other avatar or lip-sync method is used.

-   **LAW 2: Three briefings per day, fixed schedule**
    -   **Verdict:** COMPLIANT
    -   **Evidence:** `cron/briefing_cron.py` correctly implements the 07:00, 09:30, and 16:30 ET schedule using cron triggers. `briefing_service.py:30` sets `HEYGEN_MAX_RETRIES = 2`, which is correctly enforced by the loop at `briefing_service.py:335`.

-   **LAW 3: Always show last 3 briefings**
    -   **Verdict:** PARTIAL
    -   **Evidence:** The template `market_briefing.html:656` is built to loop through and display the `recent` briefings. However, the backend code that queries the database for these briefings is not provided. The law requires showing the 3 *previous* briefings, meaning the latest one (in the main player) should not be repeated in the grid. Compliance depends entirely on the un-provided query logic in `routes.py` correctly implementing `...order_by(...).offset(1).limit(3)`.

-   **LAW 4: /stage → 302 redirect → /briefing**
    -   **Verdict:** UNVERIFIED
    -   **Evidence:** The necessary route definitions are not present in the provided code. The new template `market_briefing.html` exists as required, but the crucial redirect logic cannot be verified.

-   **LAW 5: Scripts are Claude-generated, not hardcoded**
    -   **Verdict:** COMPLIANT
    -   **Evidence:** `briefing_service.py:161` uses `model="claude-sonnet-4-6"`. Prompts (lines 45-87) are dynamic and pull in live data. Script cleanup at line 167 enforces the "no em dashes, no ellipses" rule.

### SECTION 3: SECURITY

The feature's security posture is strong.

-   **SQL Injection:** No risk found. All database queries are performed via the SQLAlchemy ORM, which prevents SQLi.
-   **Authentication Bypasses:** Not applicable. The briefing page is public, and the expensive generation process is correctly triggered by a server-side cron job, not a public-facing API endpoint.
-   **Rate Limiting Gaps:** The most critical resource (the paid HeyGen API) is well-protected by the `_check_cost_guard` function (`briefing_service.py:243`), which acts as a robust, domain-specific rate limiter. This is better than a generic IP-based limit.
-   **Secrets in Code:** No secrets are hardcoded. All API keys and secrets are correctly loaded from environment variables (e.g., `briefing_service.py:94`, `app.py:46`).

### SECTION 4: FRONTEND QUALITY

The frontend is aesthetically strong but has significant functional flaws.

-   **UI:** The CSS in `market_briefing.html` is well-organized and detailed, creating a professional, premium "broadcast" aesthetic that aligns with the brand. It looks world-class.
-   **Mobile:** Responsiveness is handled via media queries (lines 520-530), correctly adapting the grid layout for smaller viewports.
-   **Async States:** Excellent. The video player handles loading, error, and multiple empty states (`generating`, `failed`, `unavailable`) gracefully (lines 568-583). This provides clear feedback to the user.
-   **Hardcoded Values:** The briefing schedule is hardcoded in `market_briefing.html` (lines 642-644, 708-712), duplicating the configuration in `briefing_cron.py`. This is a maintenance liability; a change in schedule requires editing code in two separate places.
-   **JS Errors:** The timezone and video-swapping logic bugs mentioned in Section 1 are serious functional defects that will directly and negatively impact the user experience.

### SECTION 5: BACKEND QUALITY

The backend code is of very high quality.

-   **DB Operations:** Excellent. All database writes within `generate_briefing` are wrapped in try/except blocks and correctly use `db.session.rollback()` on failure, ensuring data integrity (`briefing_service.py:309`, `349`, `359`, `389`).
-   **External API Calls:** Excellent. All external requests have explicit timeouts. The BTC price fetch has a fallback (`_get_btc_price`), and the HeyGen submission has a robust retry loop (`_heygen_generate`, `generate_briefing`). The polling logic is also fault-tolerant. This is a production-grade implementation.
-   **Cron Job:** Excellent. The job runner in `briefing_cron.py` wraps the core logic in a broad `except Exception` block (line 57). This is critical as it prevents a single failed briefing from crashing the entire scheduler service.
-   **Logging:** Good. Key events, successes, and failures are logged with useful context (e.g., briefing ID). The logging on HeyGen API errors could be enhanced by logging the full response body, but it's sufficient for basic debugging.

### SECTION 6: WORLD-CLASS GAP ANALYSIS

This feature is functionally solid but lacks the polish and depth of a top-tier financial intelligence product.

1.  **Lack of Interactivity and Context:** When a user selects a previous briefing, the *entire* context should update—not just the video. A Bloomberg or Blockworks terminal would treat the selected item as the new focal point, updating all associated data displays (script, price, timestamp) to match. The current implementation feels disconnected.
2.  **Absence of "Live" Feel:** The page relies on polling and full-page reloads. A world-class product would use WebSockets (which are available in the stack via `flask_socketio`) to push updates to the client in real-time. The moment a briefing is ready, the player should appear instantly without the user needing to refresh, creating a much more dynamic and premium "live" experience.
3.  **Missing Accessibility Features:** There are no closed captions or a synchronized transcript for the video. For a professional product, especially one delivering critical information, this is a major omission that excludes hearing-impaired users and prevents silent viewing.
4.  **Superficial Data Integration:** The failure to pull in real Asian market data (the `asia_data` placeholder) is a significant gap. A premium product would integrate with a financial data provider to inject concrete numbers (e.g., "Nikkei is down 0.8%, Hang Seng up 0.5%") into the script, adding real, verifiable value.

### SECTION 7: SCORES (0-100 each)

-   Backend logic:    90/100
-   Frontend/UI:      70/100
-   Error handling:   95/100
-   Security:         95/100
-   Performance:      90/100
-   Law compliance:   90/100
-   World-class gap:  75/100
-   **OVERALL:**      **85/100**

### SECTION 8: PRIORITY ACTION PLAN

-   **P0 CRITICAL** | Fix unreliable JS timezone conversion | `market_briefing.html:714-718` | The current implementation will show incorrect countdown times to many users, breaking a core UI element. Replace with a robust library like `date-fns-tz` or pass a pre-calculated `nextMs` value from the server.
-   **P1 HIGH** | Update all metadata when playing a previous briefing | `market_briefing.html:786` | The UX is currently broken and confusing. The `loadBriefing` function must be expanded to update the title, timestamp, BTC price, script panel, and any other associated data.
-   **P1 HIGH** | Replace placeholder `asia_data` with a real data feed | `briefing_service.py:155` | The credibility of the pre-market briefing is undermined by fake data. Integrate a financial API to pull actual closing data for key Asian indices.
-   **P2 MEDIUM** | Centralize the briefing schedule configuration | `briefing_cron.py` & `market_briefing.html` | Having the schedule in two places is a maintenance risk. Define it once (e.g., in `app.py` config) and have both the cron and the template view read from it.
-   **P2 MEDIUM** | Include 'failed' status in cost guard query | `briefing_service.py:254` | To prevent potential budget overruns from repeated API failures, the cost guard query should be `status.in_(['generating', 'completed', 'failed'])`.
-   **P3 LOW** | Use WebSockets for real-time page updates | `market_briefing.html` | Replace the `30000ms` auto-refresh and `120000ms` poll with a WebSocket connection to push new briefing availability to clients instantly.

### SECTION 9: THE ONE THING

The backend is production-ready, but you must fix the frontend JavaScript to correctly update the entire page context when an old video is played, as the current disjointed experience feels broken and unprofessional.

### SECTION 10: FINAL VERDICT

This feature is architecturally sound and demonstrates excellent backend engineering, especially in its robust error handling and API integrations. It is **not ready for production** due to two critical frontend bugs: a broken countdown timer and a confusing user experience when switching videos. Once these P0/P1 user-facing issues are resolved, this feature will be a high-quality, reliable addition to the platform.