# CONSENSUS REPORT — STAGE-BROADCAST — CYCLE 1
Generated: 2026-03-21 03:08
Models: Grok-3, Gemini 2.5 Pro

---

## SCORES

> **Note:** Neither model produced explicit numeric scores. Scores below are inferred from severity language, section summaries, and relative critique intensity. Scale: 1–10.

| Subsystem | Gemini | Grok | Consensus |
|---|---|---|---|
| Correctness | 6.5 | 6.0 | **6.2** |
| Law Compliance | 8.5 | 6.0 | **7.2** |
| Security | 5.5 | 6.0 | **5.8** |
| Frontend Quality | 6.0 | 6.5 | **6.2** |
| Backend Quality | 5.5 | 5.5 | **5.5** |
| Overall | 6.4 | 6.0 | **6.2** |

---

## UNANIMOUS FINDINGS
*(Both models flagged — implement unconditionally)*

---

### U1 — Client-Side Rate Limiting Is Trivially Bypassable
**File:** `templates/stage.html`
**Lines:** ~1173 (briefing cooldown), ~1198 (greet cooldown), ~1264 (chat — no limit at all)
**Both models flagged this as the most critical security issue.**

The `requestBrief`, `requestGreet`, and `stageChat` functions have zero or trivially-bypassed client-side throttles. Any user can open DevTools and call these functions in a loop, triggering paid API calls (ElevenLabs TTS, avatar generation, AI completions) indefinitely. The client-side `busy` flag and cooldown timers are not enforceable controls.

**Fix:** The backend at `AVATAR_BASE` must implement per-IP and per-session rate limiting (e.g., max 5 brief requests/min, max 30 chat messages/min). Client-side limits are UX conveniences only, not security controls. Add a `429 Too Many Requests` handler in the frontend that surfaces a message to the user.

---

### U2 — Incomplete HTML Escaping in `esc()` Creates XSS Risk
**File:** `templates/stage.html`
**Line:** ~1057
**Both models flagged this as a security/correctness issue.**

The custom `esc()` function is an incomplete HTML sanitizer. It does not escape single quotes (`'`) or backticks (`` ` ``), leaving potential XSS vectors if data sources change or are ever compromised. It is also used inconsistently — Nostr content correctly uses `.textContent` but other dynamic data paths use `innerHTML` with this weak escaper.

**Fix:** Replace the custom `esc()` function with a hardened utility:
```javascript
function esc(s) {
  const d = document.createElement('div');
  d.textContent = String(s ?? '');
  return d.innerHTML;
}
```
Audit every `innerHTML` assignment and replace with `textContent` + DOM construction wherever possible. Specifically, refactor `sidebarSentimentLine` (line ~965) away from `innerHTML`.

---

### U3 — Polling Architecture Is Unacceptable for a Live Intelligence Product
**File:** `templates/stage.html`
**Lines:** ~1451, ~1482 (2–3 minute poll intervals)
**Both models flagged this as a fundamental product gap.**

Polling every 2–3 minutes for a product positioned as "Live Bitcoin Intelligence" is architecturally inconsistent with the value proposition. Price data, sentiment, and Nostr signals can become stale within seconds. Both models explicitly compared this unfavorably to real-time tools.

**Fix:** Implement WebSocket or Server-Sent Events (SSE) for price, sentiment, and Nostr signal delivery. Polling can remain as a fallback/health-check only. The backend needs a push architecture.

---

### U4 — No Retry Logic on External API Calls
**File:** `templates/stage.html`
**Lines:** ~1162 (`fetchTO`), ~1186, ~944
**Both models flagged this.**

The `fetchTO` wrapper implements timeouts via `AbortController` (good), but there is no retry logic anywhere. Any transient network error results in a hard failure and degraded UI. Both models noted this as a resilience gap.

**Fix:** Implement exponential backoff with jitter for non-user-triggered fetches (data polling). For user-triggered actions (chat, brief, greet), surface a clear retry button on failure rather than silently failing.

```javascript
async function fetchWithRetry(url, opts = {}, retries = 3, backoff = 500) {
  for (let i = 0; i < retries; i++) {
    try { return await fetchTO(url, opts); }
    catch (e) {
      if (i === retries - 1) throw e;
      await new Promise(r => setTimeout(r, backoff * 2 ** i + Math.random() * 200));
    }
  }
}
```

---

### U5 — Mobile `body { position: fixed }` + Pinch-Zoom Disabled = Accessibility Failure
**File:** `templates/stage.html`
**Lines:** ~349, ~1487–1488
**Both models flagged this.**

`body { position: fixed }` combined with a `<meta name="viewport">` that disables user scaling is a dual accessibility failure. It traps users, breaks browser "find in page," prevents low-vision users from zooming, and breaks standard browser behavior on iOS and Android. This fails WCAG 1.4.4 (Resize Text) and violates Apple/Google store review guidelines.

**Fix:** Remove `position: fixed` from body. Remove `user-scalable=no` and `maximum-scale=1` from the viewport meta tag. Achieve the same scroll-locking effect with `overflow: hidden` on `body` only when a modal/overlay is active, and restore it on close.

---

## MAJORITY FINDINGS
*(2 of 2 models agree — implement unless compelling reason not to)*

All unanimous findings above also qualify. Additional majority findings below:

---

### M1 — Missing ARIA Labels on Interactive Elements
**File:** `templates/stage.html`
**Line:** ~810 (`briefBtn`), ~759 (video element), all icon-only buttons
**Both models noted this (Grok more explicitly, Gemini implicitly via mobile UX critique).**

Interactive elements have no `aria-label`, `aria-role`, or keyboard navigation support. Screen readers cannot identify button purposes. This fails WCAG 2.1 AA 4.1.2 (Name, Role, Value).

**Fix:** Add `aria-label` to all icon-only buttons. Add `role="status"` or `aria-live="polite"` to data display regions that update dynamically (price, sentiment). Add `alt` text to avatar video region.

---

### M2 — Silent Failure on `URL.revokeObjectURL` and Memory Leak Risk
**File:** `templates/stage.html`
**Line:** ~1136
**Both models noted incomplete cleanup in error paths.**

In `playVid`, `URL.revokeObjectURL` is called on the happy path but may not be called in all error branches, leaving blob URLs alive in memory. On long sessions with many briefings, this accumulates.

**Fix:** Wrap revocation in a `finally` block:
```javascript
const blobUrl = URL.createObjectURL(blob);
try {
  vid.src = blobUrl;
  // ... await playback
} finally {
  URL.revokeObjectURL(blobUrl);
}
```

---

### M3 — Speech Recognition Has No Timeout / Stuck-State Risk
**File:** `templates/stage.html`
**Line:** ~1324–1339
**Both models flagged this.**

`webkitSpeechRecognition` / `SpeechRecognition` has no timeout. If the browser fails to detect input (background noise, mic permission issue, browser bug), the user is left in a permanent "recording" visual state with no escape. Additionally, `webkitSpeechRecognition` is non-standard with inconsistent cross-browser support.

**Fix:** Add a `setTimeout` of ~10 seconds that calls `recognition.stop()` and shows a "No speech detected — try again" message. Add a visible "tap to cancel" affordance during recording. Add a feature-detection check and show a graceful "not supported in your browser" message if neither `SpeechRecognition` nor `webkitSpeechRecognition` exists.

---

## UNIQUE INSIGHTS
*(Single model — evaluate carefully)*

---

### UI1 — `txDots` Element Missing from HTML (Gemini only)
**File:** `templates/stage.html`
**Line:** ~1454–1457
**Assessment: IMPLEMENT — this is a concrete null-reference bug**

Gemini identified that `initTxDots` references `document.getElementById('txDots')` but no element with that ID exists in the HTML. The function fails silently. The transcript scroll dots on mobile simply don't render.

**Fix:** Add `<div id="txDots" class="tx-dots"></div>` inside `.stage-transcripts-wrap`. Add CSS for dot styling.

---

### UI2 — `renderTranscripts` Monkey-Patch is Fragile (Gemini only)
**File:** `templates/stage.html`
**Lines:** ~1476–1480
**Assessment: IMPLEMENT — fragile coupling is a future maintenance trap**

Gemini flagged that monkey-patching `window.renderTranscripts` to inject dot initialization is a brittle pattern that breaks silently if function naming or script order changes.

**Fix:** Have `renderTranscripts` dispatch a `CustomEvent('transcriptsRendered')` on completion, and listen for that event to trigger dot initialization. Decouples the two concerns cleanly.

---

### UI3 — `webkit-playsinline` vs `playsinline` (Gemini only)
**File:** `templates/stage.html`
**Line:** ~760
**Assessment: IMPLEMENT — low effort, correct hygiene**

`webkit-playsinline` is legacy. The standard `playsinline` attribute is universally supported in modern browsers. Using both is safest.

**Fix:** Keep `playsinline` and add `webkit-playsinline` as a belt-and-suspenders measure, but ensure `playsinline` (without prefix) is the primary attribute.

---

### UI4 — `_hasUserInteracted` False-State UX Confusion (Grok only)
**File:** `templates/stage.html`
**Line:** ~1435
**Assessment: INVESTIGATE FURTHER**

Grok noted that if `_hasUserInteracted` is false, broadcast won't auto-play and the user may not understand why. This is browser autoplay policy compliance (correct behavior) but the UX feedback is unclear.

**Fix (if confirmed):** Add a visible "Click anywhere to enable auto-playback" prompt that appears when the page has loaded but no user interaction has been detected. Dismiss on first click.

---

### UI5 — N+1 Query Concern on Backend (Grok only)
**File:** Backend (not reviewed)
**Assessment: INVESTIGATE FURTHER**

Grok flagged a potential N+1 query pattern on backend endpoints. Without backend code, this cannot be confirmed. Flag for backend review in a dedicated audit cycle.

---

### UI6 — Invalid or Negative `countdown_seconds` Handling (Grok only)
**File:** `templates/stage.html`
**Line:** ~1372
**Assessment: IMPLEMENT — cheap defensive guard**

If the API returns a malformed, negative, or non-numeric `countdown_seconds`, the countdown logic may display garbage or fail silently.

**Fix:**
```javascript
const seconds = Math.max(0, parseInt(data.countdown_seconds, 10) || 0);
```
Add input validation before using any schedule API response values.

---

## CONFLICTS
*(Models disagree — tiebreaker ruling)*

---

### C1 — Severity of Authentication on API Endpoints
- **Grok:** Flagged absence of auth checks as a potential security risk
- **Gemini:** Stated "the page appears to be public, with no authentication mentioned" — treated as compliant

**Ruling: Gemini is correct in context.** The spec describes a public broadcast page. No authentication is required for read access to public Bitcoin intelligence data. However, Grok's concern is valid for the *Oracle chat and TTS endpoints* specifically — those trigger paid operations and should require at minimum a valid session token or CSRF protection even on a "public" page. **Partial implementation: protect mutation/generation endpoints, not read endpoints.**

---

### C2 — Law Compliance Rating
- **Grok:** Rated compliance as PARTIAL, citing accessibility violations and performance concerns
- **Gemini:** Rated as COMPLIANT because no specific laws were listed in the spec

**Ruling: Grok is more correct in spirit.** WCAG 2.1 AA is a de facto legal requirement in many jurisdictions (EU Web Accessibility Directive, US Section 508, ADA precedents). Marking the code as "compliant" because no laws were listed in a spec is a documentation gap, not actual compliance. The code has real WCAG violations. **Adopt Grok's assessment: PARTIAL — accessibility violations must be remediated.**

---

## VALIDATED STRENGTHS
*(Both models confirmed — do NOT change in second pass)*

1. **`fetchTO` with `AbortController`** — Proper timeout implementation on API calls. Keep this pattern; extend it with retry logic but don't replace it.

2. **Shimmer/Loading States** — Consistent use of shimmer loaders for async operations is well-executed. Both models praised this explicitly.

3. **Empty State Handling** — Transcript and data empty states are explicitly handled (line ~1029). This is correct practice; maintain consistency across all data regions.

4. **Nostr Content Safety** — Use of `.textContent` for Nostr post rendering (lines ~1090, ~1093) correctly avoids XSS. Do not change this to `innerHTML`.

5. **CSS Architecture** — Custom properties, dark theme, grid layouts, and animation approach are well-structured and consistent with the design brief. Both models noted this positively.

6. **Chat API Async Job Polling Pattern** — The sophisticated pattern of supporting both synchronous responses and async job polling for long-running AI generation (line ~1287) is correct and production-appropriate.

7. **`busy` Flag as Global Lock** — Simple and effective for this UI's single-thread-of-interaction design. Both models accepted this as sufficient for the use case.

---

## LAW COMPLIANCE CONSENSUS

| Area | Status | Finding |
|---|---|---|
| WCAG 2.1 AA (Accessibility) | ❌ VIOLATED | No ARIA labels, pinch-zoom disabled, `position:fixed` body traps users |
| GDPR / Data Privacy | ✅ COMPLIANT | No PII collected; session ID is ephemeral and non-identifying |
| EU Web Accessibility Directive | ❌ VIOLATED | Follows from WCAG violations above |
| US ADA / Section 508 (if applicable) | ❌ AT RISK | Same accessibility failures create legal exposure |
| Browser Standards (HTML5) | ⚠️ PARTIAL | `webkit-playsinline` legacy attribute; `webkitSpeechRecognition` non-standard |

**Final Determination: NOT FULLY COMPLIANT.** Accessibility failures are the primary compliance gap. These must be addressed before production launch.

---

## SECURITY CONSENSUS

Priority order (both models agree on ranking):

| Priority | Issue | Severity |
|---|---|---|
| P0 | Backend rate limiting absent on paid API endpoints (TTS, avatar, chat) | CRITICAL |
| P1 | Incomplete `esc()` function — XSS risk if data sources change | HIGH |
| P1 | `innerHTML` on sentiment data (line ~965) — unescaped API data | HIGH |
| P2 | No CSRF protection on Oracle chat/brief endpoints | MEDIUM |
| P2 | Chat and speech input sent to backend without length/content validation | MEDIUM |
| P3 | `AVATAR_BASE` hardcoded — should be environment-configurable | LOW |

**Security Consensus:** The frontend has made reasonable XSS efforts (`.textContent` for Nostr, custom escaper) but the escaper is incomplete. The catastrophic gap is the unprotected paid-API surface — this is the only issue both models elevated to CRITICAL. All others are standard web security hygiene.

---

## WORLD-CLASS GAP CONSENSUS
*(Only items 2+ models mentioned)*

1. **Real-Time Architecture (WebSocket/SSE) is Missing** — Both models. A "Live Bitcoin Intelligence" product polling every 2–3 minutes is not live. This is the single largest gap between current state and world-class. Bloomberg, Coinbase, and TradingView push data in <1 second. This is an architectural change, not a patch.

2. **Accessibility is Below Acceptable Bar** — Both models. A world-class product is usable by everyone. Current state actively harms low-vision users and screen reader users. This is not a nice-to-have; it's a quality gate.

3. **Error States Are Inconsistent / Under-Designed** — Both models noted that error handling is present but incomplete and inconsistent (some paths handled, others silently fail). A world-class product has a unified error presentation layer — a single `showError(context, message, retryFn)` utility that all failure paths route through.

4. **No Retry Logic** — Both models. Production-grade systems do not hard-fail on transient network errors. Exponential backoff is table-stakes for a data-intensive product.

---

## FINAL ACTION PLAN

```
P0 CRITICAL | Implement backend rate limiting on /oracle/chat, /oracle/brief, /oracle/greet endpoints | Backend (AVATAR_BASE routes) | models: both | Unprotected paid API surface — trivial to exploit for financial damage and DoS

P0 CRITICAL | Remove user-scalable=no + maximum-scale=1 from viewport meta; remove body{position:fixed} | templates/stage.html:349,1487-1488 | models: both | WCAG 1.4.4 violation, accessibility/legal risk, breaks browser UX

P1 HIGH     | Replace custom esc() with textContent-based sanitizer; audit all innerHTML assignments | templates/stage.html:1057,965 | models: both | Incomplete XSS protection — data source compromise = stored XSS

P1 HIGH     | Add ARIA labels to all interactive elements; add aria-live to dynamic data regions | templates/stage.html:~810,759,965 | models: both | WCAG 4.1.2 violation, legal exposure

P1 HIGH     | Add <div id="txDots"> to HTML; wire transcript dot initialization via CustomEvent | templates/stage.html:~1454,1476 | models: gemini (unique but confirmed bug) | Null reference — scroll dots never render on mobile

P1 HIGH     | Implement exponential backoff retry in fetchWithRetry wrapper for polling calls | templates/stage.html:~1162 | models: both | Transient errors cause hard failures in a data-intensive live product

P1 HIGH     | Add speech recognition timeout (~10s) + cancel affordance + browser support detection | templates/stage.html:~1324-1339 | models: both | Users stuck in recording state with no escape

P1 HIGH     | Wrap URL.revokeObjectURL in finally block for all playVid code paths | templates/stage.html:~1136 | models: both | Memory leak on long sessions with frequent briefings

P2 MEDIUM   | Add WebSocket or SSE infrastructure for price/sentiment/Nostr push delivery | templates/stage.html:~1451,1482 + backend | models: both | 2-3min polling is architecturally misaligned with "live intelligence" product positioning

P2 MEDIUM   | Add input length validation + content check before sending chat/speech to backend | templates/stage.html:~1265,1335 | models: grok | Oversized or malicious input reaches backend unchecked

P2 MEDIUM   | Add CSRF token to Oracle mutation endpoints (chat, brief, greet) | templates/stage.html:~1273 + backend | consensus | Standard protection for state-changing API calls

P2 MEDIUM   | Add _hasUserInteracted=false UX prompt ("Click to enable auto-playback") | templates/stage.html:~1435 | models: grok | Autoplay policy compliance is correct but UX is silent and confusing

P2 MEDIUM   | Replace renderTranscripts monkey-patch with CustomEvent pattern | templates/stage.html:~1476-1480 | models: gemini | Fragile coupling — breaks silently on refactor

P2 MEDIUM   | Add playsinline (standard) alongside webkit-playsinline | templates/stage.html:~760 | models: gemini | Standards compliance; future-proofing

P2 MEDIUM   | Add Math.max(0, parseInt(...) || 0) guard on countdown_seconds | templates/stage.html:~1372 | models: grok | Defensive guard against malformed API responses; cheap and correct

P2 MEDIUM   | Create unified showError(context, message, retryFn) utility; route all catch blocks through it | templates/stage.html:~981,1029,1079 | models: both | Inconsistent error presentation — some paths handle gracefully, others are silent
```

---

## CYCLE 1 VERDICT

**The code is NOT ready for production but IS ready for a second build pass.**

The architecture is sound, the aesthetic is world-class, and the core user flow functions correctly. However, there are two P0 blockers that must be resolved before any user traffic touches this system: the unprotected paid API surface (backend rate limiting) and the accessibility/viewport failures. There are no fundamental design flaws that require rearchitecting the entire feature — this is a hardening and polish pass, not a rewrite. The second build pass should address all P0 and P1 items.

The real-time architecture gap (WebSocket/SSE) is the most significant strategic shortcoming but is scoped as P2 because it requires backend infrastructure work that likely spans more than a single pass.

---

## SECOND PASS PROMPT

```
Read ~/protocol_pulse/docs/gospels/STAGE_BROADCAST_GOSPEL.md.
Read ~/protocol_pulse/docs/audits/stage-broadcast_CONSENSUS_C1.md.

This is the SECOND PASS for stage-broadcast.
The first build was reviewed by 2 independent AI models (Grok-3, Gemini 2.5 Pro) across 1 cycle.
Implement every P0 and P1 item from the consensus report. Use judgment on P2.

PRIORITY ACTION PLAN:

P0 CRITICAL | Implement backend rate limiting on /oracle/chat, /oracle/brief, /oracle/greet endpoints | Backend (AVATAR_BASE routes) | Unprotected paid API — trivial financial DoS

P0 CRITICAL | Remove user-scalable=no + maximum-scale=1 from viewport meta; remove body{position:fixed} | templates/stage.html:349,1487-1488 | WCAG 1.4.4 violation + legal risk

P1 HIGH     | Replace custom esc() with textContent-based sanitizer; audit all innerHTML — especially sidebarSentimentLine (~965) | templates/stage.html:~1057,965 | XSS risk

P1 HIGH     | Add aria-label to all icon-only buttons; aria-live="polite" to price/sentiment regions; role="status" to data panels | templates/stage.html:~810,759,965 | WCAG 4.1.2

P1 HIGH     | Add <div id="txDots" class="tx-dots"></div> inside .stage-transcripts-wrap; wire init via CustomEvent('transcriptsRendered') instead of monkey-patch | templates/stage.html:~1454,1476-1480 | Null ref bug — dots never render

P1 HIGH     | Implement fetchWithRetry with exponential backoff + jitter (max 3 retries, 500ms base) for all polling fetch calls | templates/stage.html:~1162 | Transient errors = hard failures

P1 HIGH     | Add 10-second timeout to SpeechRecognition; add cancel affordance; add feature-detection guard with "not supported" fallback | templates/stage.html:~1324-1339 | Stuck recording state

P1 HIGH     | Wrap URL.revokeObjectURL call in finally block within playVid | templates/stage.html:~