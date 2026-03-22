# CONSENSUS REPORT — STAGE-BROADCAST — CYCLE 2
Generated: 2026-03-21 03:11
Models: Grok, Gemini

---

## SCORES

| Subsystem       | Gemini | GPT-4o | Grok | Consensus |
|-----------------|--------|--------|------|-----------|
| Correctness     | 4.0    | N/A    | 6.0  | **5.0**   |
| Law Compliance  | 5.0    | N/A    | 6.5  | **5.8**   |
| Security        | 2.0    | N/A    | 5.5  | **3.8**   |
| Frontend Quality| 5.0    | N/A    | 6.0  | **5.5**   |
| Backend Quality | N/A    | N/A    | 5.5  | **5.5**   |
| **Overall**     | **3.5**| N/A    | **5.9** | **4.7** |

> **Scoring Note:** GPT-4o was listed in the table header but is not present in the Cycle 2 outputs — only Grok and Gemini submitted. Consensus scores reflect the two available models. Gemini's scores dropped sharply from Cycle 1 (avg 6.0 → 3.5) after reassessing severity of security issues. Grok's scores declined modestly (avg 6.4 → 5.9). The 4.7 consensus overall is a hard signal: **this feature is not production-ready.**

---

## UNANIMOUS FINDINGS
*All 2 models agree — implement unconditionally.*

### U1 — Client-Side Rate Limiting Is Trivially Bypassable ("Denial of Wallet")
- **What:** The `requestBrief`, `requestGreet`, and `stageChat` functions are gated only by a JavaScript `busy` flag and cooldown timer. Any user can open DevTools, reset these flags, and fire unlimited requests to paid backend APIs (AI inference, TTS, video generation).
- **File/Lines:** `templates/stage.html`, lines ~1173, ~1198, ~1264
- **Severity:** CRITICAL — direct financial risk, not merely a UX issue
- **Fix:** Implement strict server-side rate limiting (per-IP and/or per-session) on all Oracle endpoints. Return `429 Too Many Requests` with `Retry-After` headers. Frontend must handle 429 gracefully with user-visible feedback. Client-side throttle may remain as a UX courtesy only — never as a security control.

### U2 — Incomplete HTML Escaping in `esc()` Creates XSS Risk
- **What:** The custom `esc()` function at line ~1057 escapes `&`, `<`, `>`, and `"` but omits single quotes (`'`) and backticks (`` ` ``). This is compounded by direct `innerHTML` assignments (e.g., `sidebarSentimentLine` at line ~965) that pass user-influenced or API-sourced data into the DOM without sanitization.
- **File/Lines:** `templates/stage.html`, lines ~965, ~1057
- **Severity:** HIGH — XSS vector; risk escalates if data sources are ever compromised or expanded
- **Fix:** Delete the custom `esc()` function entirely. Replace with a DOM-based sanitizer (e.g., create a text node and read `.textContent`, or use `DOMPurify`). Audit every `innerHTML` assignment: use `textContent` where markup is not required; use the sanitizer where markup is needed.

### U3 — Polling Architecture Is Unacceptable for a Live Intelligence Product
- **What:** Price, sentiment, and Nostr data are fetched via `setInterval` at 2–3 minute polling intervals. The product is marketed as delivering "live" Bitcoin intelligence. These intervals mean data can be 180 seconds stale at the moment of display.
- **File/Lines:** `templates/stage.html`, lines ~1451, ~1482
- **Severity:** HIGH — product integrity and value proposition failure
- **Fix:** Migrate frequently-updated data feeds (price, sentiment) to WebSockets or Server-Sent Events (SSE). For MVP, if SSE/WebSocket infrastructure is not yet available, reduce polling to 15–30 seconds and remove all "live" or "real-time" language from the UI until true real-time transport is implemented.

---

## MAJORITY FINDINGS
*2 of 2 models agree — implement unless compelling reason exists.*

All three unanimous findings above are technically also majority findings (100% agreement). The following additional issues received agreement from both models, even if framed differently:

### M1 — Web Accessibility (WCAG) Failures
- **What:** Interactive elements (mic button, mode toggles, avatar controls) lack `aria-label`, `role`, and keyboard focus management. Screen reader users cannot operate the interface. Grok flagged this explicitly; Gemini incorporated it as a compliance issue.
- **File/Lines:** `templates/stage.html`, line ~810 (mic button), ~855, other interactive controls
- **Fix:** Add `aria-label` to all icon-only buttons. Ensure all interactive controls are keyboard-reachable and have visible focus states. Add `role="status"` or `aria-live` regions for dynamic content updates (price ticker, sentiment).

### M2 — Speech Recognition Has No Timeout or Error Feedback
- **What:** If `_stageRecognition` fails to detect audio or encounters an error, users receive no feedback and may remain stuck in a "recording" state indefinitely.
- **File/Lines:** `templates/stage.html`, line ~1339
- **Fix:** Add a timeout (e.g., 10 seconds) that auto-cancels recognition and shows a toast/status message. Populate `_stageRecognition.onerror` with a user-visible error state.

---

## UNIQUE INSIGHTS
*One model only — evaluate carefully.*

### I1 — Race Condition in `stageChat` Video Playback (Gemini)
- **What:** In `stageChat`, `setBusy(false)` is called in a `.finally()` block (line ~1309) that fires after the initial HTTP request completes — not after the polled video finishes playing. The video is retrieved via a `setInterval` poll (line ~1290). This means `busy` clears while video is still playing, allowing overlapping requests, audio collision, and unpredictable UI state.
- **File/Lines:** `templates/stage.html`, lines ~1290, ~1309
- **Assessment:** **IMPLEMENT.** This is a concrete, logic-level bug with clear, observable consequences (audio overlap, broken UI state). Gemini's identification is precise. Fix by moving `setBusy(false)` to a callback that fires only after the video playback promise resolves (or the polling interval is cleared after confirmed playback completion).

### I2 — Missing `#txDots` DOM Element Causes Silent `TypeError` (Gemini)
- **What:** `initTxDots()` calls `document.getElementById('txDots')` (line ~1454–1457), but no element with that ID exists in the HTML. This fails silently — mobile transcript scroll dots never render.
- **File/Lines:** `templates/stage.html`, lines ~1454–1480, HTML section ~865
- **Assessment:** **IMPLEMENT.** This is a definitive, reproducible bug on mobile. The fix is trivial: add `<div id="txDots"></div>` inside `.stage-transcripts-wrap`. Gemini also correctly flagged the fragile monkey-patching of `window.renderTranscripts` (lines ~1476–1480) as a secondary concern — emit a custom event or return a promise instead.

### I3 — Hardcoded `AVATAR_BASE` URL (Grok)
- **What:** The avatar base URL is a hardcoded string with no mechanism for environment-specific configuration (dev/staging/prod). Any URL change requires a code edit.
- **File/Lines:** `templates/stage.html`, line ~924
- **Assessment:** **INVESTIGATE FURTHER.** If the project already uses environment injection (e.g., via Jinja2 template variables or a config endpoint), this is a P2 fix. If not, it should be addressed as part of a broader config management approach. Don't over-engineer for a single URL, but don't hardcode production endpoints in templates.

### I4 — `URL.revokeObjectURL` Not Called in All Error Paths (Grok)
- **What:** In `playVid`, `objURL` may not be revoked if `vid.onerror` fires before `objURL` is assigned, or if certain error paths are taken. This accumulates orphaned blob URLs over a session.
- **File/Lines:** `templates/stage.html`, line ~1136
- **Assessment:** **IMPLEMENT.** Memory leaks from uncollected blob URLs compound over time, especially on mobile where heap pressure is real. Wrap `URL.revokeObjectURL` in a `finally` block that checks if `objURL` is defined before calling revoke. Low effort, meaningful impact on long sessions.

### I5 — `playVid` Promise Never Resolves on Autoplay Block (Gemini, Grok both noted — elevated to majority)
- **What:** If `vid.play()` is rejected by browser autoplay policy and the user never taps the video, the promise returned by `playVid` hangs unresolved, stalling all chained logic. The "Tap to play" overlay appears but there's no timeout or alternative recovery.
- **File/Lines:** `templates/stage.html`, lines ~1155–1158
- **Assessment:** **IMPLEMENT.** Safari and hardened Chrome profiles block autoplay. A hung promise is a broken user flow. Add a timeout (e.g., 30 seconds) that rejects the promise and shows a recovery UI if no interaction is detected.

---

## CONFLICTS
*Where models gave contradictory recommendations.*

### C1 — Severity of Polling Architecture Fix (Grok vs. Gemini)
- **Grok:** Polling is suboptimal but a WebSocket migration may be overkill for initial deployment; shorter intervals (30s) are an acceptable interim fix.
- **Gemini:** Polling is architecturally unacceptable; WebSockets or SSE are required to fulfill the product's value proposition.
- **Tiebreaker: Gemini is more correct on principle; Grok is more pragmatic on sequencing.** The right answer is both: for MVP, reduce to 30-second intervals AND remove "live" marketing language. Commit to SSE/WebSocket in the next sprint. Shipping a "live" product on 3-minute polling is a product integrity failure, not just a tech debt item.

### C2 — Overall Severity Assessment
- **Grok Overall:** 5.9 (marginal but potentially shippable with fixes)
- **Gemini Overall:** 3.5 (not remotely production-ready)
- **Tiebreaker: Gemini's reassessment is more accurate.** Grok's Cycle 2 scores reflect moderate concern; Gemini's sharp downgrade after properly weighting the financial risk of the rate-limiting vulnerability is the correct calibration. A feature with an unmitigated "Denial of Wallet" attack surface and multiple XSS vectors is not a 5.9 — it is closer to Gemini's 3.5. The consensus 4.7 is a reasonable midpoint but the blocking conditions align with Gemini's position.

---

## VALIDATED STRENGTHS
*All models agree these are already solid — do not regress.*

1. **Global `busy` Flag Pattern:** The single `busy` flag as a UI lock is simple, effective, and prevents most duplicate-request scenarios. Both models acknowledged it works as designed. Do not replace it with a more complex queue unless requirements demand it — just fix the `stageChat` race condition (I1) that undermines it.

2. **Autoplay Fallback Overlay ("Tap to Play"):** The code does attempt to handle browser autoplay rejection with a visible overlay. This is the right instinct. The issue is it doesn't go far enough (no timeout, promise hangs) — but the pattern itself is correct and should be preserved and extended, not removed.

3. **Briefing Cooldown UX Intent:** The design intent of preventing briefing spam with a cooldown period is sound from a UX perspective. The flaw is implementation (client-side only). Keep the UX pattern; move the enforcement server-side.

4. **Mobile Carousel for Transcripts:** The attempt to provide a carousel/swipe interface for mobile transcript viewing is the right product decision. The bug (missing `#txDots` element) is a trivial implementation error, not a design flaw. Preserve the architecture, fix the element.

---

## LAW COMPLIANCE CONSENSUS

| Area | Status | Finding |
|------|--------|---------|
| GDPR / Privacy | **LIKELY COMPLIANT** | No PII collection or storage detected in frontend code. No tracking pixels, no cookie consent triggers observed. Verify backend endpoints do not log IP addresses without disclosure. |
| WCAG 2.1 (Accessibility) | **NON-COMPLIANT** | Missing ARIA labels, no keyboard navigation for interactive controls, likely color contrast failures. In jurisdictions with ADA/EAA enforcement (US, EU), this is a legal exposure. |
| Financial Regulations | **NOT APPLICABLE (CURRENTLY)** | Bitcoin price display and sentiment analysis do not constitute financial advice if properly disclaimed. No disclaimer visible in reviewed code — verify one exists in the UI or ToS. |
| Content Security Policy | **UNKNOWN / AT RISK** | XSS vulnerabilities in `esc()` and `innerHTML` usage suggest CSP headers may not be strict enough to compensate. Verify CSP headers on the server; a strict CSP would significantly reduce XSS blast radius. |

**Final Determination:** The feature has one clear legal exposure — WCAG non-compliance — which is actionable in multiple jurisdictions. All other compliance areas are either clean or require backend verification outside the scope of this file.

---

## SECURITY CONSENSUS

Priority order, both models in agreement:

| Priority | Issue | Risk |
|----------|-------|------|
| **P0** | No server-side rate limiting on paid API endpoints | Financial — unlimited cost amplification attack |
| **P0** | XSS via incomplete `esc()` + `innerHTML` assignments | Data integrity, user session compromise |
| **P1** | Unresolved `playVid` promise on autoplay block | Logic hang, potential for chained exploit if combined with other issues |
| **P1** | `URL.revokeObjectURL` not called in all error paths | Memory exhaustion (DoS vector on constrained devices) |
| **P2** | Hardcoded `AVATAR_BASE` URL | Supply chain / config drift risk |

**Security Consensus Statement:** The two P0 issues are not theoretical — they are exploitable today by any user with browser DevTools access. The XSS risk is lower-probability but higher-impact. Both must be resolved before any public exposure of this feature.

---

## WORLD-CLASS GAP CONSENSUS
*What the combined intelligence of both models says is missing from a truly world-class product.*

Both models identified these gaps (2/2 agreement required):

1. **Real-Time Data Transport:** A world-class "live intelligence" product uses WebSockets or SSE. Polling is a prototype pattern. The gap between the product's promise and its architecture is visible to technically sophisticated users and undermines trust.

2. **Accessibility as a First-Class Concern:** World-class products are usable by everyone. The complete absence of ARIA labels, focus management, and keyboard navigation indicates accessibility was never in scope. For a product targeting a broad crypto audience (which includes users with disabilities), this is both a market and legal gap.

3. **Observability and Error Telemetry:** Neither model found any evidence of structured error logging, user-facing error recovery flows, or backend health monitoring hooks. API failures degrade silently. A world-class product instruments every failure path and provides clear recovery UX.

4. **Security-by-Design:** Rolling custom HTML escape functions, placing rate limits in JavaScript, and using `innerHTML` for dynamic content are patterns from a pre-security-aware era. World-class frontend code uses established sanitization libraries, treats all external data as untrusted by default, and enforces security controls at the layer where they cannot be bypassed.

---

## FINAL ACTION PLAN

| Priority | Change | File:Line | Models | Why |
|----------|--------|-----------|--------|-----|
| **P0 CRITICAL** | Implement server-side rate limiting on all Oracle endpoints (`/oracle/speak`, `/oracle/chat`, etc.); return 429 with `Retry-After`; handle 429 in frontend with user-visible message | `templates/stage.html` ~1173, ~1198, ~1264 + backend routes | Both | Trivially bypassable client-side throttle exposes paid APIs to unlimited abuse — direct financial risk |
| **P0 CRITICAL** | Delete custom `esc()` function; replace with DOM-based sanitizer or DOMPurify; audit all `innerHTML` assignments and switch to `textContent` where markup is unnecessary | `templates/stage.html` ~965, ~1057 | Both | Incomplete escaper provides false security; multiple confirmed XSS vectors in conjunction with `innerHTML` |
| **P0 CRITICAL** | Fix `stageChat` race condition: move `setBusy(false)` to fire only after video playback promise resolves, not in the HTTP `.finally()` block | `templates/stage.html` ~1290, ~1309 | Gemini (unique, high confidence) | `busy` clears while video plays → overlapping requests, audio collision, broken UI |
| **P0 CRITICAL** | Add `<div id="txDots"></div>` to HTML inside `.stage-transcripts-wrap`; replace monkey-patching of `window.renderTranscripts` with custom event or callback | `templates/stage.html` ~865, ~1454–1480 | Gemini (unique, confirmed bug) | `getElementById('txDots')` returns null → `TypeError`, mobile scroll dots never render |
| **P1 HIGH** | Add `aria-label` to all icon-only buttons; add `role` and `aria-live` regions for dynamic content; verify keyboard focus order | `templates/stage.html` ~810, ~855, throughout | Both | WCAG non-compliance is a legal exposure in US/EU; screen reader users cannot operate the interface |
| **P1 HIGH** | Add speech recognition timeout (10s); populate `onerror` with user-visible toast/status message | `templates/stage.html` ~1339 | Both | Users can be silently stuck in recording state indefinitely |
| **P1 HIGH** | Add timeout to `playVid` autoplay-block scenario; reject promise after 30s of no interaction; show recovery UI | `templates/stage.html` ~1155–1158 | Both (noted independently) | Safari/hardened Chrome block autoplay; hung promise breaks all chained logic with no recovery path |
| **P1 HIGH** | Reduce polling interval to 30s as interim measure; remove all "live" / "real-time" UI copy until WebSocket/SSE is implemented | `templates/stage.html` ~1451, ~1482 | Both | 3-minute polling contradicts "live" product branding; immediate mitigation before architectural migration |
| **P1 HIGH** | Wrap `URL.revokeObjectURL` in a null-checking `finally` block to ensure all blob URLs are released regardless of error path | `templates/stage.html` ~1136 | Grok (unique, clear risk) | Unreleased blob URLs accumulate over session; memory pressure on mobile |
| **P2 MEDIUM** | Replace monkey-patching of `renderTranscripts` with custom DOM event (`dispatchEvent(new CustomEvent('transcriptsRendered'))`) listened to by `initTxDots` | `templates/stage.html` ~1476–1480 | Gemini | Fragile coupling — function rename or reorder silently breaks dots |
| **P2 MEDIUM** | Remove `body { position: fixed; }` for mobile; find non-destructive scroll locking approach | `templates/stage.html` ~349 | Gemini | `position: fixed` on body breaks native browser scroll, back-navigation, and accessibility |
| **P2 MEDIUM** | Externalize `AVATAR_BASE` URL to environment config (Jinja2 variable, meta tag, or `/config` endpoint) | `templates/stage.html` ~924 | Grok | Hardcoded URLs create deployment friction and config drift risk |
| **P2 MEDIUM** | Migrate price/sentiment/Nostr feeds to WebSockets or SSE | Backend + `templates/stage.html` ~1451, ~1482 | Both | Required for true real-time delivery; polling is architecturally misaligned with product value proposition |

---

## CYCLE 2 VERDICT

**NOT PRODUCTION-READY.**

Two full cycles of independent AI review across two models have identified four P0-critical issues, four P1-high issues, and four P2-medium issues. The security posture is the decisive blocker:

**Absolute Final Blockers (must resolve before any public traffic):**
1. **The "Denial of Wallet" vulnerability** — any anonymous user can exhaust paid API budgets. This is not a future risk; it is an immediate financial liability the moment the feature is exposed publicly.
2. **The XSS vulnerabilities** — the `esc()` function provides a false sense of security and the `innerHTML` patterns are unsafe. User data and sessions are at risk.
3. **The `stageChat` race condition** — overlapping video playback from a cleared `busy` flag produces a broken, unprofessional experience and undermines the core interactive feature.
4. **The missing `#txDots` element** — a provable `TypeError` that silently breaks mobile transcript navigation.

The feature demonstrates thoughtful product design (avatar interaction, briefing schedule, broadcast/interactive modes) and the architectural intentions are sound. But the implementation has critical gaps in security hygiene and correctness that make it unsafe to ship. With focused effort on the P0 list, this could reach production-readiness within a single sprint.

**Consensus Overall Score: 4.7 / 10**
**Recommendation: DO NOT SHIP. Fix P0s. Re-audit P1s. Then ship.**

---

## SECOND PASS PROMPT

```
Read ~/protocol_pulse/docs/gospels/STAGE_BROADCAST_GOSPEL.md.
Read ~/protocol_pulse/docs/audits/stage-broadcast_CONSENSUS_C2.md.

This is the FINAL PASS for stage-broadcast.
The feature was reviewed by 2 independent AI models across 2 cycles.
Implement every P0 and P1 item from the consensus. Use judgment on P2.

PRIORITY ACTION PLAN:

P0 CRITICAL | Implement server-side rate limiting on all Oracle endpoints
            | templates/stage.html ~1173, ~1198, ~1264 + backend routes
            | Models: both
            | Why: client-side throttle is trivially bypassed via DevTools;
            |      paid API endpoints exposed to unlimited abuse (Denial of Wallet)
            | Action: add per-IP + per-session rate limiting server-side;
            |         return 429 with Retry-After; handle 429 in frontend with
            |         user-visible error message

P0 CRITICAL | Delete custom esc() function; fix all XSS vectors
            | templates/stage.html ~965, ~1057
            | Models: both
            | Why: esc() misses single quotes and backticks; innerHTML at line
            |      ~965 passes API data to DOM without safe sanitization
            | Action: replace esc() with DOM-based sanitizer (DOMPurify or
            |         createTextNode pattern); switch innerHTML → textContent
            |         where markup is not required; sanitize where it is

P0 CRITICAL | Fix stageChat race condition — setBusy(false) fires too early
            | templates/stage.html ~1290, ~1309
            | Models: Gemini (high confidence unique finding)
            | Why: setBusy(false) in .finally() clears lock while polled video
            |      is still playing → overlapping audio, broken UI state
            | Action: move setBusy(false) to fire only after video playback
            |         promise resolves or polling interval is cleared

P0 CRITICAL | Add missing #txDots DOM element; fix fragile monkey-patching
            | templates/stage.html ~865, ~1454–1480
            | Models: Gemini (confirmed bug)
            | Why: getElementById('txDots') returns null → TypeError;
            |      mobile scroll dots never render
            | Action: add <div id="txDots"></div> inside .stage-transcripts-wrap;
            |         replace window.renderTranscripts monkey-patch with
            |

---

# WINNER DETERMINATION

## WINNER: Grok — Grok delivered the most consistently accurate, deep, and actionable analysis across both cycles, earning the highest consensus score (5.9 overall vs Gemini's 3.5) while correctly identifying and prioritizing the critical "Denial of Wallet" vulnerability, WCAG accessibility failures, and backend quality issues that Gemini initially underweighted or missed entirely, demonstrating superior completeness across all four evaluation criteria.

---

## FINAL SECOND-PASS PRIORITY LIST

*Definitive ordered implementation sequence based on severity, consensus confidence, and financial/security risk.*

---

### PRIORITY 1 — CRITICAL / IMPLEMENT IMMEDIATELY (Pre-Launch Blocker)

**P1.1 — Server-Side Rate Limiting on All Oracle Endpoints (U1)**
- Implement per-IP + per-session rate limiting at the server layer on `requestBrief`, `requestGreet`, and `stageChat` endpoints
- Return `429 Too Many Requests` with `Retry-After` header on breach
- Frontend must render user-visible feedback on 429 (not silent failure)
- Client-side `busy` flag and cooldown timer are demoted to UX courtesy only — remove any security assumption from them
- *Rationale: Direct, unbounded financial exposure. A single malicious user can drain API budget in minutes.*

**P1.2 — Replace `esc()` and Audit All `innerHTML` Assignments (U2)**
- Delete the custom `esc()` function at line ~1057; it does not escape single quotes or backticks
- Replace all `innerHTML` assignments that accept any external or API-sourced data with either:
  - `textContent` for plain text, or
  - A hardened sanitizer (DOMPurify) for intentional HTML
- Specifically audit line ~965 (`sidebarSentimentLine` innerHTML assignment) flagged as a direct XSS vector
- *Rationale: XSS vulnerability with confirmed missing escape characters. External data sources make this exploitable.*

---

### PRIORITY 2 — HIGH / Implement in Sprint Following Launch

**P2.1 — Fix Confirmed JavaScript TypeError: `initTxDots` Missing DOM Element**
- `document.getElementById('txDots')` returns null — the element does not exist in the HTML
- Add the required container element (e.g., `<div id="txDots">`) inside `.stage-transcripts-wrap`
- Validate the monkey-patch of `renderTranscripts` (lines ~1476–1480); replace with a custom event or callback pattern to eliminate fragile function wrapping
- *Rationale: Confirmed hard bug causing silent failure on mobile transcript scroll dots. Gemini caught this; confirmed by consensus.*

**P2.2 — Replace Polling Architecture with WebSocket or SSE (U3)**
- The 2–3 minute polling intervals on price, sentiment, and Nostr data are architecturally mismatched with a "live Bitcoin intelligence" product
- Migrate to WebSocket or Server-Sent Events (SSE) for real-time data delivery
- As interim mitigation, reduce polling interval and display a "last updated" timestamp with staleness warning
- *Rationale: Core product value proposition is live intelligence. Polling at 2–3 minute intervals undermines it.*

**P2.3 — Harden Concurrent API Failure Handling**
- Parallel API calls (`loadIntel`, `loadTranscripts`, `loadNostr`) have no coordinated failure UX
- Wrap in `Promise.allSettled()` and surface per-source failure states to the user
- Add fallback/stale-data indicators rather than silent partial loads
- *Rationale: Users currently see a partially loaded page with no signal that data is missing.*

---

### PRIORITY 3 — MEDIUM / Next Hardening Sprint

**P3.1 — WCAG Accessibility Remediation**
- Add ARIA labels and roles to all interactive elements (flagged at line ~810 and throughout)
- Audit color contrast ratios against WCAG AA minimum (4.5:1)
- All avatar controls, chat inputs, and mode toggles must be keyboard navigable
- *Rationale: Legal compliance risk; product is inaccessible to screen reader users in current state.*

**P3.2 — Remove `body { position: fixed }` on Mobile (CSS)**
- Line ~349: `body { position: fixed }` breaks native browser scroll, back-navigation, and accessibility on mobile viewports
- Replace with an explicit scroll container on the content layer
- Audit all mobile breakpoints for downstream layout breakage
- *Rationale: Confirmed bad practice causing browser functionality regression on mobile.*

**P3.3 — Add Queuing and User Feedback for Avatar Request Throttling**
- Currently, clicks during a pending `requestBrief` or `requestGreet` are silently ignored
- Implement a visible loading/queued state so users understand the system received their request
- Consider a lightweight request queue rather than hard-drop behavior
- *Rationale: Silent ignoring of user input is a UX failure that erodes trust in the product.*

**P3.4 — Harden `playVid` Against Mid-Playback Network Failure**
- `onended`/`onerror` handlers on the `vid` element can be overwritten in rapid succession
- Ensure `URL.revokeObjectURL` executes in all exit paths (success, error, abort) to prevent memory leaks
- Add visible error state when video fails mid-playback rather than silent reset
- *Rationale: Memory leak risk and invisible failure during core product interaction.*

---

### PRIORITY 4 — LOW / Backlog (Quality & Maintainability)

**P4.1 — Remove `renderTranscripts` Monkey-Patch Pattern**
- Fragile global function wrapping will break on any script reorder or rename
- Emit a custom DOM event (`transcriptsRendered`) from `renderTranscripts` and listen for it in `initTxDots`

**P4.2 — Add Stale Data Handling on Price/Sentiment**
- Line ~993: price only updates if new data exists; no fallback or staleness warning for stale data
- Display timestamp of last successful fetch with visual staleness indicator after threshold

**P4.3 — Consolidate Error Messaging**
- Static error messages (lines ~981–983) do not distinguish between network failure, empty response, or service unavailability
- Implement typed error states with distinct user-facing messages per failure mode

---

### IMPLEMENTATION SEQUENCE SUMMARY

| Priority | Item | Severity | Owner Hint |
|----------|------|----------|------------|
| P1.1 | Server-side rate limiting | CRITICAL | Backend |
| P1.2 | Replace `esc()` + audit innerHTML | CRITICAL | Frontend/Security |
| P2.1 | Fix `initTxDots` TypeError | HIGH | Frontend |
| P2.2 | Replace polling with SSE/WS | HIGH | Full-stack |
| P2.3 | Concurrent API failure handling | HIGH | Frontend |
| P3.1 | WCAG accessibility | MEDIUM | Frontend |
| P3.2 | Remove `body: fixed` mobile CSS | MEDIUM | Frontend |
| P3.3 | Avatar request queue + feedback | MEDIUM | Frontend |
| P3.4 | `playVid` memory/error hardening | MEDIUM | Frontend |
| P4.1–4.3 | Maintainability / UX polish | LOW | Frontend |

**Bottom line: P1.1 and P1.2 are non-negotiable pre-launch requirements. Everything in P2 should ship in the first post-launch sprint. The feature is not production-ready in its current state.**