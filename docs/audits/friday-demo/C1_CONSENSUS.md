# CONSENSUS REPORT — FRIDAY-DEMO — CYCLE 1
Generated: 2026-03-25 11:00
Models: grok, gemini (+1 failed — GPT-4o: TPM rate limit exceeded)

---

## SCORES

*Note: Neither model provided explicit numerical scores. Scores below are synthesized from severity ratings and issue density across the 8 audit questions. GPT-4o failed — marked N/A.*

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Mic / Permission Gate | 4/10 (CRITICAL) | N/A | 4/10 (CRITICAL) | **4/10** |
| Video Playback / Autoplay | 5/10 (HIGH) | N/A | 5/10 (CRITICAL) | **5/10** |
| Mobile / iOS Safari | 4/10 (CRITICAL) | N/A | 5/10 (CRITICAL) | **4/10** |
| GPU / Server Queue | 6/10 (HIGH) | N/A | 6/10 (HIGH) | **6/10** |
| UX Feedback / State Transitions | 6/10 (MEDIUM) | N/A | 5/10 (HIGH) | **5/10** |
| Error Handling / Network Failure | 6/10 (implied) | N/A | 4/10 (CRITICAL) | **5/10** |
| Visual Polish / UI Consistency | 7/10 (implied) | N/A | 6/10 (MEDIUM) | **6/10** |
| Audio/Video Sync | 4/10 (HIGH) | N/A | 6/10 (implied) | **5/10** |
| **Overall Demo Readiness** | **5/10** | **N/A** | **5/10** | **5/10** |

**Interpretation:** 5/10 overall. The app has a solid aesthetic foundation but carries multiple CRITICAL-severity failure modes that have a high probability of triggering during a live audience demo. It is **not yet demo-safe** without targeted fixes.

---

## UNANIMOUS FINDINGS
*(Both models flagged these — implement unconditionally)*

---

### UNANIMOUS-1 — Microphone Permission Failure Has No Demo-Safe Recovery

**What it is:** If `getUserMedia` fails (browser block, OS denial, HTTPS issue, device conflict), the app displays a developer-facing error message and stops. There is no path forward for the presenter or audience. The demo dies at the very first interaction.

**File:Line:** `templates/oracle_live.html:931–987` (Gemini) / `oracle_live.html:977–986` (Grok)

**What to change:**
- In the `.catch` block of `getUserMedia`, after existing error text is rendered, inject a styled **"Continue with Text Input"** button that activates a text-based fallback flow
- The fallback flow should bypass `getUserMedia` entirely and allow typed queries to proceed through the full oracle pipeline
- Error container must be styled to match the cyberpunk design language (dark background, neon border, monospace font) — not raw unstyled HTML
- Add a visible **"Retry Mic Access"** button as a secondary option before the text fallback

---

### UNANIMOUS-2 — iOS Safari Autoplay Blocks Response Video Playback

**What it is:** iOS Safari blocks video `.play()` calls that are not synchronously triggered by a direct user gesture. The response video — which plays after server-side processing completes — is not tied to any new user gesture. The `vid.play()` promise at the `playVid` function will be rejected silently or with a `NotAllowedError`, leaving the avatar static while audio may or may not play.

**File:Line:** `templates/oracle_live.html:1388–1394` (Gemini) / `oracle_live.html:1100–1101` (Grok)

**What to change:**
- In the `.catch` handler of the `vid.play()` promise, render a full overlay element (positioned absolute, covers the avatar area, semi-transparent dark background, large centered play icon SVG, z-index above avatar)
- On tap/click of the overlay: set `vid.muted = false`, call `vid.play()`, remove the overlay
- The current `setStat('Tap to play', ...)` text is confirmed by Gemini as **too subtle** — it will be missed in a live demo context
- This overlay pattern must be applied to *both* the thinking video and the response video play calls

---

## MAJORITY FINDINGS
*(2 of 2 models agree — implement unless compelling reason not to)*

Since both models reviewed the same 8 questions and only 2 models participated (GPT-4o failed), all shared findings are effectively unanimous. The following are confirmed by both models with varying framing:

---

### MAJORITY-1 — GPU Contention Has No Client-Side Signal

**Both models flagged this.** If the GPU is busy rendering, the client sits in "thinking" animation for up to 90 seconds before a generic timeout error. There is no differentiated feedback for "queue busy" vs. "network dead" vs. "server error."

**File:Line:** `templates/oracle_live.html:1121` (Gemini) / `oracle_live.html:1118–1121` (Grok)

**What to change:**
- Backend must return `HTTP 429` or `503` with a `Retry-After` header when GPU pipeline is occupied
- Client `.then()` block must check for these status codes *before* the generic `!r.ok` check
- On `429`/`503`: call `setStat('Satomi is meditating... please wait', '#f4c46f', true)` and implement timed retry (respect `Retry-After` value or default 8-second polling)
- Do NOT fall through to the generic error handler for these cases

---

### MAJORITY-2 — No Status Feedback Between Speech End and Processing Start

**Both models flagged this** (Gemini: "awkward silence" / "unpredictable," Grok: "abrupt transition," "users uncertain if input was captured").

**File:Line:** `templates/oracle_live.html:1413–1417` (Gemini) / `oracle_live.html:1431–1436` (Grok)

**What to change:**
- In `recognition.onend`, immediately before calling `process()`, fire `setStat('Processing your request...', '#f4c46f', true)`
- Remove or minimize the 300ms delay before `process()` is invoked
- This bridges the dead-air gap between listening state ending and thinking animation starting

---

### MAJORITY-3 — Thinking Video Failure Leaves Black Screen with No Status Update

**Both models flagged this.** If the thinking video fails to load or errors out (`vid.onerror`), the user sees a black screen or frozen avatar with zero status text update. The app appears crashed.

**File:Line:** `templates/oracle_live.html:1096–1103` (both models)

**What to change:**
- In `vid.onerror` handler: immediately call `setStat('Loading response... please wait', '#f4c46f', true)` to confirm the system is alive
- Add a fallback to static avatar image if video fails (do not leave canvas/video element black)
- Add a secondary timeout check: if playback has not started within 3 seconds of `vid.play()` being called, show static avatar + status text

---

## UNIQUE INSIGHTS
*(Only 1 model caught these — evaluated individually)*

---

### UNIQUE-1 — Audio/Video Sync Dissociation (Gemini only)
**Finding:** Gemini identified that audio begins streaming before the lip-synced video is ready (`oracle_live.html:1178–1211` audio vs. `1213–1300` video fetch). The user hears Satomi's voice while the avatar is still in "thinking" animation, breaking the illusion of a live speaking intelligence.

**Assessment: IMPLEMENT**
This is a high-value, non-obvious finding. It is architecturally important and will be the single most "uncanny valley" moment in the demo if not addressed. Gemini's conservative fix (update status text to indicate video is still rendering) is the low-risk path for Friday. The ideal fix (block audio until video is ready) is higher-risk but should be the target for the next build. **For this pass: implement the status text bridge fix. File a ticket for full A/V sync as a P1 follow-up.**

---

### UNIQUE-2 — Slow 3G / Network Timeout Has No User-Facing Recovery Path (Grok only)
**Finding:** Grok identified that on slow connections, fetch requests to `/oracle/chat` and `/oracle/job` can silently timeout without surfacing a retry mechanism (`oracle_live.html:1308–1315`).

**Assessment: IMPLEMENT**
This is valid and distinct from the GPU contention issue. Even if the GPU is available, a degraded network will cause the same symptom (infinite thinking). The fix is straightforward: in the timeout catch path, call `setStat('Network timeout — check connection and retry', '#ff3b5f', false)` and render a retry button. Low effort, high protection.

---

### UNIQUE-3 — Error Message Container Visual Inconsistency (Grok only)
**Finding:** Grok flagged that the gate screen error messages use unstyled inline HTML that clashes with the cyberpunk aesthetic (`oracle_live.html:978–984`).

**Assessment: IMPLEMENT**
This is a polish issue but it matters for a Friday demo. If an error fires in front of 10+ people, it should look intentional. Wrap error content in a styled container matching the design language. Low effort, zero risk.

---

### UNIQUE-4 — Touch Target Size for Mic Button (Grok only)
**Finding:** Grok flagged that the mic button may have insufficient touch target size for reliable tapping on small mobile screens (`oracle_live.html:480–483`).

**Assessment: INVESTIGATE**
Grok notes the mic is already set to a size at line 481 but questions whether `min-width`/`min-height` is enforced. Check computed CSS. If the touch target is below 44×44px (Apple HIG) or 48×48dp (Material), add `min-width: 48px; min-height: 48px` to the CSS rule. Quick verify, quick fix.

---

### UNIQUE-5 — Pre-flight GPU Status Check Before Chat Request (Grok only)
**Finding:** Grok suggested adding a `/oracle/status` pre-check call before hitting `/oracle/chat` to determine GPU availability.

**Assessment: SKIP (for Friday)**
This adds a round-trip latency to every interaction for a marginal benefit already covered by the `429`/`503` handling in MAJORITY-1. The backend-side semaphore + HTTP status code approach from Gemini is architecturally cleaner. Do not implement the pre-flight check for this pass — it adds complexity and latency without net gain given the other fix is in place.

---

## CONFLICTS
*(Areas where models gave different or incompatible recommendations)*

---

### CONFLICT-1 — Timing of Audio vs. Video: Block or Bridge?

**Gemini** recommends holding audio until video is ready (block audio) OR at minimum adding status text bridge. **Grok** does not raise the A/V sync issue explicitly — instead focuses on video load failure fallback.

**Resolution: Gemini is correct on the diagnosis; Grok's video fallback fix is complementary, not conflicting.**
For Friday: implement Gemini's status text bridge (low risk). Do not block audio until video is ready for this pass — it requires deeper async coordination that could introduce new failure modes under time pressure. Both fixes coexist without conflict.

---

### CONFLICT-2 — Retry Delay After Speech Recognition Ends

**Gemini** recommends shortening or removing the 300ms delay before `process()` is called. **Grok** recommends adding an immediate `setStat` call but does not address the delay itself.

**Resolution: Gemini is right to question the delay; Grok's `setStat` addition is the safe, non-breaking improvement.**
Implement Grok's `setStat` call unconditionally. On the delay: reduce from 300ms to 100ms (Gemini's suggestion) as a reasonable middle ground — it provides enough buffer for recognition to stabilize without the perceptible dead-air pause. Do not remove it entirely as it may cause race conditions with recognition cleanup.

---

### CONFLICT-3 — Severity of Mobile Autoplay Issue

**Gemini** rates iOS autoplay as CRITICAL with a full overlay solution. **Grok** also rates it CRITICAL but proposes a simpler "Tap to Play" text overlay.

**Resolution: Gemini's full overlay implementation is correct.**
Grok's own earlier finding (Q6) notes that subtle status text is insufficient. The overlay must be a visually prominent, tap-anywhere element — not just text. Gemini's specific implementation (positioned absolute, covers avatar, large SVG play icon, tap-to-dismiss) is the right call for a demo context.

---

## VALIDATED STRENGTHS
*(Both models confirmed these are already working well — do NOT change in the second pass)*

- **Overall visual/aesthetic design:** Both models acknowledge the cyberpunk design language is polished and coherent. The color palette, typography, and layout are intentional and effective.
- **90-second client-side timeout exists:** Both models acknowledged the timeout is already present at `oracle_live.html:1121` — the issue is the *response* to it, not its absence.
- **Existing `vid.onerror` handler structure:** The hook is there — both models praised the architecture of having the handler; the gap is in what it does when triggered.
- **Status text system (`setStat`):** Both models used `setStat` as the primary remediation tool throughout, confirming the underlying status-display infrastructure is solid and the right abstraction.
- **Gate screen architecture:** The overall flow of mic permission → gate → oracle interaction is structurally sound. Neither model recommended rearchitecting this flow, only hardening its failure paths.

---

## LAW COMPLIANCE CONSENSUS

*Assessed against standard frontend/production pipeline laws (inferred from PIPELINE_LAWS.md context):*

| Law / Principle | Status | Confidence |
|---|---|---|
| All user interactions must have visible feedback within 300ms | **VIOLATED** — gap between speech end and processing start | High (both models) |
| All async operations must have timeout + user-facing error | **VIOLATED** — timeout exists but error surface is inadequate | High (both models) |
| Mobile-first: all features must work on iOS Safari | **VIOLATED** — autoplay rejection not handled properly | High (both models) |
| All error states must match design system | **VIOLATED** — gate error messages unstyled | Medium (Grok only) |
| No demo-blocking single points of failure without bypass | **VIOLATED** — mic failure has no bypass | High (both models) |
| GPU resources must be protected with queuing/semaphore | **VIOLATED** (backend, inferred) — no 429/503 handling | High (both models) |
| Audio and video must be synchronized | **VIOLATED** — audio plays before video is ready | Medium (Gemini only) |
| Network degradation must be gracefully communicated | **VIOLATED** — slow 3G causes silent stuck state | Medium (Grok only) |

**Compliant:**
- Core accessibility structure (touch targets exist, though minimum size needs verification)
- HTTPS assumed (required for `getUserMedia`)
- Timeout mechanism is present (even if its UX handling is insufficient)

---

## SECURITY CONSENSUS

Neither model flagged security vulnerabilities as primary concerns, which is consistent with this being a frontend-focused demo audit. However, the following warrant attention:

| Issue | Model(s) | Priority |
|---|---|---|
| No input sanitization mentioned for text fallback flow (to be added) | Gemini (implied) | P1 — must sanitize before sending to `/oracle/chat` |
| No rate limiting on client side for repeated chat requests | Grok (implied via Q8) | P2 — add debounce/cooldown on submit |
| Error messages may expose internal server details (HTTP status codes surfaced to user) | Neither — synthesized | P2 — ensure catch blocks show user-friendly text only |

**No CRITICAL security findings from either model. Security posture is acceptable for a controlled Friday demo, but text input fallback must sanitize before production.**

---

## WORLD-CLASS GAP CONSENSUS
*(Only items flagged by 2+ models)*

1. **No graceful degradation path exists at any layer.** Both models independently described the same failure pattern: the app reaches a dead end (mic fail, video fail, network fail, GPU busy) with no path to recovery. A world-class product has multiple fallback layers — text input if mic fails, static avatar if video fails, queued retry if GPU is busy — and the user never reaches a dead end. This app currently has none of these working.

2. **Audio/visual coherence is not guaranteed.** Both models (Gemini explicitly, Grok implicitly via video fallback focus) identified that the user experience can fracture along the audio/video boundary — voice plays without lips moving, or lips move silently, or neither plays. A world-class conversational AI interface treats A/V sync as an absolute invariant, not a best-effort outcome.

3. **The system communicates in developer language under failure.** Both models flagged that error messages, status text, and failure states read as technical/internal rather than designed user communications. A world-class product has a defined "voice" for every failure state that maintains immersion and brand even when things go wrong.

---

## FINAL ACTION PLAN
*(Sorted by consensus priority)*

| Priority | Change | File:Line | Models | Why |
|---|---|---|---|---|
| **P0 CRITICAL** | Add "Continue with Text Input" fallback button in `getUserMedia` catch block; style error container to match design system | `oracle_live.html:971–987` | Both | Demo cannot start without this recovery path. Mic failure is the highest-probability failure mode. |
| **P0 CRITICAL** | Replace subtle `setStat('Tap to play')` with full tap-to-play overlay (positioned absolute, SVG play icon, tap-to-dismiss) in `vid.play()` catch | `oracle_live.html:1388–1394` | Both | iOS Safari will block autoplay. Without a visible recovery, demo halts silently on mobile. |
| **P0 CRITICAL** | Add `setStat('Processing your request...', '#f4c46f', true)` immediately in `recognition.onend` before `process()` call; reduce delay to 100ms | `oracle_live.html:1413–1417` | Both | Eliminates dead-air gap that makes app appear frozen after user stops speaking. |
| **P0 CRITICAL** | In `vid.onerror`, immediately call `setStat` with alive-system message and revert to static avatar fallback | `oracle_live.html:1096–1103` | Both | Black screen after video error is the most "app is broken" signal possible in a live demo. |
| **P1 HIGH** | Add HTTP 429/503 handling in fetch `.then()` with user-facing "Satomi is busy" message and timed retry; backend must emit these status codes when GPU is occupied | `oracle_live.html:1121` | Both | 90-second silent hang destroys demo credibility. Differentiated feedback preserves trust. |
| **P1 HIGH** | Add `setStat` bridge in audio play path to indicate video is still rendering; do NOT block audio for this pass | `oracle_live.html:1178–1211` | Gemini (unique but high-value) | A/V dissociation is the most "uncanny valley" moment. Status bridge is low-risk for Friday. |
| **P1 HIGH** | In network timeout catch block, surface user-friendly retry message and add retry button | `oracle_live.html:1308–1315` | Grok (unique, valid) | Slow 3G causes same symptom as GPU hang but requires different recovery path. |
| **P2 MEDIUM** | Apply same tap-to-play overlay pattern to thinking video `play()` call, not just response video | `oracle_live.html:1100–1101` | Grok | Consistent autoplay handling across all video elements. |
| **P2 MEDIUM** | Verify mic button computed touch target; if below 48×48px, add `min-width: 48px; min-height: 48px` to CSS | `oracle_live.html:480–483` | Grok | Missed tap on primary CTA in demo is embarrassing. Quick verify. |
| **P2 MEDIUM** | Wrap all gate-screen error messages in styled container matching cyberpunk design language | `oracle_live.html:978–984` | Grok | If error fires in front of audience, it must look designed not debugged. |

---

## CYCLE 1 VERDICT

**NOT READY for merge without P0 fixes. Needs targeted hardening pass, not fundamental rework.**

The underlying architecture is sound. The design is strong. The pipeline logic is coherent. However, the app currently has **four independent P0 failure modes**, any one of which can halt the demo in front of a live audience with no recovery path. The probability that zero P0 failures occur during a live demo is low.

The good news: all P0 fixes are **localized, low-risk, and implementable in a single focused session.** No architectural changes are required. This is a hardening pass, not a rebuild.

**Recommendation:** Implement all P0 items and P1-HIGH items before Friday. P2 items are strongly recommended but non-blocking for demo go/no-go. After implementation, run `regression_test.sh` and conduct a dry-run on an iOS Safari device specifically (the highest-risk platform per both models).

---

## SECOND PASS PROMPT
*(Ready to fire into Claude Code)*

```
Read ~/protocol_pulse/docs/gospels/PIPELINE_LAWS.md.
Read ~/protocol_pulse/docs/audits/friday-demo_CONSENSUS_C1.md.

This is the SECOND PASS for friday-demo.
The first build was reviewed by 2 independent AI models (Grok-3, Gemini 2.5 Pro)
across 1 cycle. GPT-4o failed due to rate limit and did not contribute.
Implement every P0 and P1 item from the consensus. Use judgment on P2.

PRIORITY ACTION PLAN:

P0 CRITICAL | Add "Continue with Text Input" fallback button + styled error container in getUserMedia catch block | oracle_live.html:971-987 | models: both | Demo cannot start without mic recovery path — highest probability failure mode

P0 CRITICAL | Replace setStat('Tap to play') with full tap-to-play overlay (position:absolute, SVG play icon, tap-to-dismiss, muted=false on tap) in vid.play() catch | oracle_live.html:1388-1394 | models: both | iOS Safari blocks autoplay — without visible recovery demo halts silently on mobile

P0 CRITICAL | Add setStat('Processing your request...', '#f4c46f', true) immediately in recognition.onend before process() call; reduce existing delay from 300ms to 100ms | oracle_live.html:1413-1417 | models: both | Eliminates dead-air gap that makes app appear frozen after user stops speaking

P0 CRITICAL | In vid.onerror handler, immediately call setStat with alive-system message AND revert canvas/video element to static avatar fallback image | oracle_live.html:1096-1103 | models: both | Black screen after video error is definitive "app crashed" signal in live demo context

P1 HIGH | Add HTTP 429 and 503 status handling in fetch .then() block before generic !r.ok check; display setStat('Satomi is meditating... please wait', '#f4c46f', true) and implement timed retry respecting Retry-After header or 8s default; backend must emit 429/503 with Retry-After when GPU pipeline is occupied | oracle_live.html:1121 | models: both | 90-second silent hang destroys demo credibility; differentiated GPU-busy feedback preserves trust

P1 HIGH | Add setStat status bridge in audio play path to indicate video is still rendering (do NOT block audio from playing for this pass — full A/V sync is a follow-up ticket) | oracle_live.html:1178-1211 | models: gemini | A/V dissociation breaks illusion of live intelligence; status bridge is low-risk mitigation for Friday

P1 HIGH | In network timeout catch block, call setStat('Network timeout — check connection and retry', '#ff3b5f', false) and render a retry button | oracle_live.html:1308-1315 | models: grok |