# CONSENSUS REPORT — FRIDAY-DEMO — CYCLE 2
Generated: 2026-03-25 11:03
Models: grok, gemini (+1 failed: gpt4o — rate limit exceeded)

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Mic / Permission Gate | 4/10 | N/A | 4/10 | **4/10** |
| Video Playback / Autoplay | 4/10 | N/A | 4/10 | **4/10** |
| Mobile / iOS Safari | 4/10 | N/A | 4/10 | **4/10** |
| GPU / Server Queue | N/A | N/A | 6/10 | **6/10** *(single source)* |
| UX Feedback / State Transitions | 3/10 | N/A | 5/10 | **4/10** |
| Error Handling / Network Failure | 3/10 | N/A | 5/10 | **4/10** |
| Audio / Video Sync | 3/10 | N/A | 5/10 | **4/10** |
| Visual Polish / UI Consistency | N/A | N/A | 6/10 | **6/10** *(single source)* |
| **Overall Demo Readiness** | **3/10** | N/A | **5/10** | **4/10** |

> ⚠️ **Note:** GPT-4o failed due to TPM rate limit (44,483 tokens requested vs 30,000 limit). Consensus is derived from 2 of 3 models. Confidence is reduced — unanimous findings below represent 2/2 agreement, not 3/3. Treat all findings as HIGH confidence, not ABSOLUTE.

---

## UNANIMOUS FINDINGS
*(Both available models agree — implement unconditionally)*

### UNANIMOUS-1: Microphone Permission Failure Has No Demo-Safe Recovery
- **What it is:** If `getUserMedia` fails (blocked by OS, browser policy, or hardware), the app displays an error and stops. There is no retry path, no bypass, and no way to continue the demo without reloading the page and fixing browser settings live in front of an audience.
- **File:Line:** `oracle_live.html:931–987` (the `.catch` block of the `getUserMedia` call)
- **What to change:** Add two recovery options in the catch block:
  1. A styled **"Retry Mic Access"** button that re-invokes `getUserMedia`
  2. A **"Continue with Text Input"** button that activates a text-entry fallback flow so the demo can proceed regardless of mic state
- **Why:** Both models rated this P0. It is the first user interaction. If it fails with no graceful exit, the demo is dead on arrival.

---

### UNANIMOUS-2: iOS Safari Autoplay Blocks Response Video
- **What it is:** The response video is loaded asynchronously and fetched after the initial user gesture has expired. iOS Safari's autoplay policy requires video playback to be triggered directly within a user gesture. `vid.play()` will throw a `NotAllowedError` silently, leaving a static or frozen avatar while audio may or may not play.
- **File:Line:** `oracle_live.html:1388–1394` (the `playVid` function's play call)
- **What to change:** Wrap `vid.play()` in a `.catch()` handler. If it rejects, display a large, visually prominent **"Tap to Play ▶"** overlay centered on the avatar. This overlay's `onclick` calls `vid.play()` within the new user gesture, which iOS permits.
- **Why:** Both models rated this P0/critical. On mobile — the most likely demo device type — this is a guaranteed silent failure with no existing fallback.

---

### UNANIMOUS-3: Audio Plays Before Lip-Synced Video Is Ready (De-Sync UX Flaw)
- **What it is:** The audio stream begins playing (`oracle_live.html:1178–1211`) while the lip-synced video is still being fetched and polled asynchronously (`oracle_live.html:1213–1300`). The audience hears Satomi speaking while the avatar is still in "thinking" mode or static. This shatters the illusion of a live AI intelligence, which is the entire premise of the feature.
- **File:Line:** `oracle_live.html:1178–1211` (audio playback) vs. `oracle_live.html:1213–1300` (video fetch/poll)
- **What to change:**
  - **Ideal:** Buffer both streams; play neither until both are ready. Single synchronized play call.
  - **Acceptable (time-constrained):** Suppress audio start until `playVid()` is ready to fire. Update `setStat()` immediately after audio loads to display `'Rendering video...'` so the delay is visually explained rather than invisible.
- **Why:** Gemini identified this as the most insightful UX finding of Cycle 1. Grok confirmed the feedback-during-delay problem that encompasses it. Both models scored Audio/Video Sync as 3–5/10.

---

### UNANIMOUS-4: "Thinking" Video Failure Leaves a Black/Frozen Screen
- **What it is:** If the `/oracle/thinking` video fails to load (`vid.onerror`) or stalls for more than a few seconds, the user sees a black screen or static avatar with no status update. There is no fallback state, no messaging, and no indication the app is still working. A 15-second black screen reads as a crash.
- **File:Line:** `oracle_live.html:1096–1103` (thinking video setup and play call)
- **What to change:**
  - Wire `vid.onerror` to immediately call `setStat('Processing... please wait', '#6cff9f', false)` and fall back to the static avatar image
  - Add a `setTimeout` of 3–5 seconds: if the video hasn't begun playing by then, trigger the same fallback
- **Why:** Both models flagged this. It compounds with the autoplay issue — if the thinking video also fails to play on iOS, the user is completely in the dark for the entire processing duration.

---

## MAJORITY FINDINGS
*(2 of 2 available models agree — implement unless compelling reason not to)*

> With only 2 models, all agreements are technically unanimous. Items here are classified by relative priority and specificity of agreement rather than mathematical majority.

### MAJ-1: API Timeout / Network Failure Produces a Silent Dead End
- **What it is:** If the `fetch` to `/oracle/chat` times out or fails after a long wait (potentially 90+ seconds), the `.catch` block provides poor user feedback. The `finally` block resets to `LISTENING` state, but the user has been staring at a thinking animation for over a minute with no result and no explanation.
- **File:Line:** `oracle_live.html:1118` (fetch call), `oracle_live.html:1308–1316` (catch/finally)
- **What to change:** In the `.catch` block, clear the thinking timer, reset the avatar, and display a user-facing message: `"I'm having trouble connecting. Please try asking again."` with a clear `IDLE` or `READY` state so the user knows they can retry.

### MAJ-2: Touch Targets Too Small on Mobile
- **What it is:** The mic button and related controls have insufficient tap target size for comfortable use on smaller mobile screens, creating fumbling during a live demo.
- **File:Line:** `oracle_live.html:480–483`
- **What to change:** Ensure all interactive elements meet minimum 44×44px touch target size per iOS HIG / Material Design guidelines. Use `padding` or `min-width/min-height` to expand targets without changing visual size.

---

## UNIQUE INSIGHTS
*(Only 1 model caught this — evaluated individually)*

### UNIQUE-1 (Gemini): Race Condition Between `stopRec()` and `recognition.onend`
- **What it is:** `stopRec()` at line 1427 immediately plays the thinking video. Milliseconds later, `recognition.stop()` fires `onend` (line 1412), which calls `process()` (line 1416), which *also* plays the thinking video. This double-trigger causes visual glitches — a stutter or flash in the avatar — and makes the state machine fragile under rapid speech-stop interactions.
- **File:Line:** `oracle_live.html:1412–1416` (`recognition.onend`), `oracle_live.html:1427–1436` (`stopRec`)
- **Assessment: IMPLEMENT.** This is a legitimate race condition in an event-driven system with two handlers targeting the same state transition. The fix is clean and low-risk: strip the thinking video call from `stopRec()` and let `recognition.onend` be the single source of truth for initiating `process()`. This is a textbook state machine correctness fix.

### UNIQUE-2 (Gemini): `alert()` Used for Checkout Errors on Merch Page
- **What it is:** `merch.html` uses a native browser `alert()` dialog for checkout errors. This is jarring, visually incompatible with the site's aesthetic, and blocks the UI thread — a completely unprofessional pattern on an otherwise polished page.
- **File:Line:** `merch.html:1659`
- **Assessment: IMPLEMENT.** This is a quick, low-risk, high-polish fix. Replace with an inline error message rendered inside the product modal matching the site's design language. Takes < 30 minutes and prevents an embarrassing popup during demo.

### UNIQUE-3 (Grok): Security Alert Overlay Has No Timeout/Fallback
- **What it is:** The vision security overlay (`oracle_live.html:569–619`) has no timeout or escape path. If it triggers unexpectedly during the demo, and the user/presenter doesn't interact with it correctly, they could be trapped in a blocking state with no recovery.
- **File:Line:** `oracle_live.html:569–619`
- **Assessment: INVESTIGATE FURTHER.** The actual trigger condition for this overlay is unclear from the audit alone. If this overlay can fire unexpectedly during normal demo flow, it must have a timeout (e.g., auto-dismiss after 10 seconds) or a clearly labeled dismiss button. If it only fires on intentional security events, the risk is lower. Verify the trigger path before the demo.

### UNIQUE-4 (Grok): Mobile Layout `overflow:hidden` May Clip UI Elements
- **What it is:** `#stage` uses `overflow:hidden` on mobile, which could clip cards or buttons on very small screens, making them inaccessible.
- **File:Line:** `oracle_live.html:417–524`
- **Assessment: INVESTIGATE FURTHER.** Test on the actual demo device(s). If content is confirmed clipped, switch to `overflow:auto` or `overflow:scroll` for the stage element, or audit which child elements overflow and constrain them instead.

### UNIQUE-5 (Grok): GPU Contention Has No Client-Side Indication
- **What it is:** When the server-side GPU is under load, rendering delays can be significant but the client has no way to distinguish "GPU busy" from "network failure" from "crashed."
- **File:Line:** `oracle_live.html:1118–1121`
- **Assessment: LOW PRIORITY / SKIP FOR NOW.** The existing timeout handling, once improved per MAJ-1, will surface this as a generic delay. Server-side GPU queue status would require a new API endpoint. Not worth the complexity before the Friday demo. Revisit post-demo.

---

## CONFLICTS
*(Where models gave contradictory recommendations)*

### CONFLICT-1: Audio/Video Sync — Wait vs. Manage Expectations
- **Gemini says:** Wait for both audio and video to be ready before playing either. Prioritize cohesive experience over raw speed.
- **Grok says:** A hybrid approach is better — play audio immediately but update status text to manage expectations, since delaying audio adds unnecessary latency.
- **Tiebreaker verdict: Gemini is right for the demo; Grok is right for production.**
  - For a **live demo**, the illusion of a speaking avatar is the entire "magic moment." A disembodied voice with a static face actively harms the impression. The audience can tolerate an extra 1–2 seconds of "Rendering..." more than they can tolerate hearing words without lip sync.
  - For **production**, Grok's latency concern is valid — some users will prefer faster audio even without video. That's a product decision for post-demo.
  - **For Friday: implement Gemini's approach** (hold audio until video is ready, or update status text at minimum if buffering both is too complex to ship in time).

### CONFLICT-2: Overall Demo Readiness Score
- **Gemini:** 3/10 — The app is aesthetically impressive but functionally fragile with multiple P0 failure paths
- **Grok:** 5/10 — Issues are real but the app has working foundations
- **Tiebreaker verdict: 4/10 is the consensus score, and Gemini's framing is more accurate.**
  - The specific failure modes identified (mic gate, iOS autoplay, audio/video desync, race condition) are not edge cases — they are on the critical path of the primary user flow. A demo tool that fails at its first user interaction under common conditions (iOS Safari, mic permission dialog) must score below 5. The aesthetic quality does not compensate for structural fragility in a live demo context.

---

## VALIDATED STRENGTHS
*(Both models confirmed these are already solid — do NOT change in second pass)*

> ⚠️ Note: With GPT-4o absent and Cycle 1 outputs incomplete, validated strengths are sparse. Both models focused heavily on failures. The following were implicitly not flagged as broken:

- **Core visual design and aesthetic:** Both models acknowledged the app is visually polished and impressive. The cyberpunk / Satomi aesthetic is coherent and complete. Do not refactor visual styling before the demo.
- **Thinking video concept:** The "thinking" animation concept itself is sound — both models praised the idea and only flagged the fallback handling, not the mechanism. Keep the thinking video; just add the fallback.
- **Existing `setStat()` utility:** Both models leveraged this function in their proposed fixes, indicating it is correctly designed and useful. Do not replace it — extend it.
- **`merch.html` visual design:** Flagged only for an `alert()` bug and minor accessibility concerns, not for structural or layout failures. The merch page is substantially complete.

---

## LAW COMPLIANCE CONSENSUS

*No PIPELINE_LAWS.md file was provided to the auditors in this cycle. The following assessment is based on general web/demo best practices inferred from the code context:*

| Law / Standard | Status | Finding |
|---|---|---|
| **Graceful Degradation** | ❌ VIOLATED | No fallback when mic, video, or network fails |
| **Progressive Enhancement** | ❌ VIOLATED | App assumes mic, autoplay, GPU pipeline all succeed |
| **User Feedback on Async Operations** | ❌ VIOLATED | Silent failures on API timeout, video load error |
| **Mobile-First / Touch Compatibility** | ⚠️ PARTIAL | Layout exists but autoplay and touch targets are broken |
| **No Native Browser Dialogs in UI** | ❌ VIOLATED | `alert()` on `merch.html:1659` |
| **Error State Recovery** | ❌ VIOLATED | Multiple dead-end states with no retry path |
| **Accessibility Minimums** | ⚠️ PARTIAL | Low-contrast text in `merch.html`, touch target sizing |

**Final determination:** The code violates at minimum 4 fundamental web application laws. All violations are fixable within the P0/P1 action plan below.

---

## SECURITY CONSENSUS

Neither model flagged explicit security vulnerabilities as primary concerns for this demo-focused audit. The following were noted incidentally:

1. **Vision Security Overlay (Grok, single-model):** An overlay that can trap UI state without an escape path could theoretically be exploited or triggered unexpectedly. Low security risk, high UX risk.
2. **No input sanitization mentioned:** Text input fallback (proposed fix) must sanitize any user-entered text before sending to `/oracle/chat`. If implementing the text fallback, ensure the input field has proper XSS protections.
3. **API endpoint exposure:** `/oracle/chat` and `/oracle/thinking` are called client-side with no visible auth token in the audited code. Not a demo blocker but a production concern.

**Security is not the primary risk vector for Friday's demo. UX and reliability are.**

---

## WORLD-CLASS GAP CONSENSUS
*(Only items 2+ models mentioned)*

### GAP-1: No Graceful Degradation Architecture
Both models independently observed that the app has no fallback layer — it assumes 100% success on mic, autoplay, GPU, and network. A world-class interactive AI demo product has a **resilience matrix**: every primary flow has a defined fallback, and every fallback has a defined escape. This is not just about Friday — it's a fundamental architectural gap.

### GAP-2: State Machine Is Fragile and Implicit
Both models identified state transition issues (the race condition, the double-play, the silent dead-end after API failure). A world-class implementation uses an explicit state machine (even a simple enum + transition table) so that impossible states are impossible by design, not by accident. The current implementation has implicit state encoded in which variables happen to be set — a recipe for demo-night race conditions.

### GAP-3: No Monitoring or Observability During Live Demo
Neither model flagged this as a code bug, but both noted symptoms of it — you cannot tell from the client whether a delay is caused by GPU contention, network latency, or a silent crash. A world-class demo product has a hidden operator overlay (e.g., `?debug=1` query param) showing real-time state, latency, and error counts. This would let the presenter diagnose and recover from failures in seconds rather than minutes.

---

## FINAL ACTION PLAN
*(Sorted by consensus priority)*

### P0 CRITICAL — Demo will fail without these

| # | Change | File:Line | Models | Why |
|---|---|---|---|---|
| P0-1 | Add "Continue with Text Input" button in `getUserMedia` `.catch` block to allow demo to proceed without mic | `oracle_live.html:971–987` | Both (unanimous) | Most probable catastrophic failure at first click |
| P0-2 | Add "Retry Mic Access" button alongside text fallback for users who want to fix mic and try again | `oracle_live.html:971–987` | Both (unanimous) | Completes the recovery UX; text fallback alone isn't always the right path |
| P0-3 | Wrap `vid.play()` in `.catch()`; if rejected, show centered "Tap to Play ▶" overlay on avatar | `oracle_live.html:1388–1394` | Both (unanimous) | iOS Safari guaranteed silent failure on async video load |
| P0-4 | Hold audio playback until video is ready (buffer both, play together); fallback: show `setStat('Rendering video...')` when audio loads but video isn't ready | `oracle_live.html:1178–1211` | Both (unanimous, Gemini primary) | Audio without lip-sync destroys the core "magic" of the feature |

---

### P1 HIGH — Likely to cause major disruption or embarrassment

| # | Change | File:Line | Models | Why |
|---|---|---|---|---|
| P1-1 | Add `vid.onerror` handler + 3–5s timeout to fallback to static avatar + `setStat('Processing... please wait')` when thinking video fails | `oracle_live.html:1096–1103` | Both (unanimous) | 15-second black screen reads as a crash to any audience |
| P1-2 | Refactor `stopRec()` to not call thinking video directly; let `recognition.onend` → `process()` be the sole trigger | `oracle_live.html:1412–1436` | Gemini (unique) | Race condition causes visual stutter and fragile state transitions on every speech submission |
| P1-3 | In API fetch `.catch` block: clear thinking timer, reset avatar, display "I'm having trouble connecting. Please try asking again." | `oracle_live.html:1308–1316` | Both (unanimous) | Silent dead end after 90s wait is the worst possible UX outcome for a timed demo |
| P1-4 | Ensure all interactive controls meet 44×44px minimum touch target size | `oracle_live.html:480–483` | Grok (unique, high risk) | Small touch targets cause fumbling in live demo on mobile |

---

### P2 MEDIUM — Unpolished, unprofessional, or low-probability embarrassment

| # | Change | File:Line | Models | Why |
|---|---|---|---|---|
| P2-1 | Replace `alert()` on checkout error with inline styled error message inside product modal | `merch.html:1659` | Gemini (unique) | Native `alert()` is jarring and incompatible with polished aesthetic |
| P2-2 | Style mic error messages with site's design language (matching colors, button styles) | `oracle_live.html:978–985` | Grok (unique) | Unstyled error text looks like a debug message in front of an audience |
| P2-3 | Verify vision security overlay has auto-dismiss timeout or explicit close button; add if missing | `oracle_live.html:569–619` | Grok (unique) | Could trap UI state in blocking overlay with no recovery during demo |
| P2-4 | Test `#stage overflow:hidden` on actual demo device; change to `overflow:auto` if content is clipped | `oracle_live.html:417–524` | Grok (unique) | Clipped UI elements are inaccessible and confusing |

---

## CYCLE 2 VERDICT

**Is this code production-ready?** No.

**Is this code demo-ready as of this audit?** No — not without the P0 fixes.

**After P0 fixes are applied?** Yes, with significant caveats. The app will be demo-survivable, not demo-bulletproof.

**Absolute final blockers (in order):**
1. The mic permission gate has no recovery → kills the demo before it begins
2. iOS autoplay fails silently on the response video → the feature's climax is broken on mobile
3. Audio plays before lip-sync video → the core "magic" illusion is shattered even when it "works"

These three issues are independent failure paths on the primary user journey. Any one of them firing on a live demo in front of 10+ people will undermine confidence in the product. All three are fixable in under a day of focused engineering.

**Consensus overall demo readiness score: 4/10**
The app is visually impressive and conceptually compelling. It is structurally fragile at every async boundary. Fix the P0s, ship the P1s, and it becomes a 7/10 demo — which is enough to wow a room.

---

## SECOND PASS PROMPT
*(Ready to fire into Claude Code)*

```
Read ~/protocol_pulse/docs/gospels/PIPELINE_LAWS.md.
Read ~/protocol_pulse/docs/audits/friday-demo_CONSENSUS_C2.md.

This is the FINAL PASS for friday-demo.
The first build was reviewed by 2 independent AI models across 2 cycles.
(GPT-4o failed Cycle 2 due to rate limits — consensus is Gemini + Grok only.)
Implement every P0 and P1 item from the consensus. Use judgment on P2.

PRIORITY ACTION PLAN:

P0 CRITICAL — implement all before anything else:
1. Add "Continue with Text Input" + "Retry Mic Access" buttons in getUserMedia .catch block
   FILE: oracle_live.html:971–987
   WHY: Most probable catastrophic failure at first user interaction

2. Wrap vid.play() in .catch(); if rejected display centered "Tap to Play ▶" overlay on avatar
   FILE: oracle_live.html:1388–1394
   WHY: iOS Safari guaranteed silent failure on async video — showstopper on mobile

3. Hold audio playback until video is ready (buffer both, play together)
   Fallback if too complex: setStat('Rendering video...') when audio loads but video not ready
   FILE: oracle_live.html:1178–1211
   WHY: Audio without lip-sync destroys the core magic of the feature

P1 HIGH — implement before demo:
4. Add vid.onerror handler +

---

# WINNER DETERMINATION

# WINNER: **Gemini**

Gemini delivered the highest-quality analysis across the 2-cycle audit. Its findings proved most accurate in Cycle 2 — both the text-input fallback strategy and the audio/video de-sync UX flaw were explicitly validated and praised by Grok in its Cycle 2 self-assessment as findings it had missed. Gemini also demonstrated superior depth by identifying a subtle but high-severity UX failure (audio playing before lip-synced video) that functioned even when the system was technically working — a distinction neither Grok nor GPT-4o surfaced — while its recommendations were immediately implementable with concrete code and clear rationale tied directly to demo impact.

---

# FINAL SECOND-PASS PRIORITY LIST
*(Definitive implementation order — derived from 2-cycle consensus, weighted by severity and demo impact)*

---

## P0 — DEMO-KILLERS: Fix before any rehearsal

### 1. Mic Permission Failure — Add Dual Recovery Path
- **File:Line:** `oracle_live.html:931–987` (`.catch` block of `getUserMedia`)
- **What:** Add two buttons inside the catch block:
  - **"Retry Mic Access"** — re-invokes `getUserMedia` without page reload
  - **"Continue with Text Input"** — activates a text-entry fallback that bypasses mic entirely and routes through the same response pipeline
- **Why first:** This is the first user interaction. A failure here with no exit is a full stop in front of a live audience. Gemini's text-fallback framing is correct — the goal is not to fix the mic, it is to guarantee the demo continues regardless.
- **Acceptance test:** Block mic in browser settings → click gate CTA → both buttons appear → text fallback produces a valid Satomi response.

---

### 2. iOS Safari Autoplay Block — Response Video Never Plays
- **File:Line:** `oracle_live.html` — `vid.play()` call on asynchronously loaded response video
- **What:** Wrap the response video in a user-gesture-gated overlay. On iOS Safari, `.play()` on a video not tied to the originating gesture is silently rejected. Add a full-screen semi-transparent **"Tap to see response"** overlay that fires `.play()` on tap.
- **Why second:** On any iPhone or iPad in the audience, the avatar will be permanently silent and static after the first query. This is visually indistinguishable from a crash.
- **Acceptance test:** Load on iPhone Safari → submit query → overlay appears → tap → video plays with audio in sync.

---

## P1 — HIGH-SEVERITY: Fix before the demo day, not just before rehearsal

### 3. Audio/Video De-Sync — Audio Plays Before Lip-Sync Video Is Ready
- **File:Line:** `oracle_live.html:1096–1103` (response audio trigger and video load sequence)
- **What:** Gate audio playback until the response video has buffered to a playable state. Use the video element's `canplay` or `canplaythrough` event to synchronize the audio start:
  ```javascript
  responseVideo.addEventListener('canplaythrough', function() {
      responseAudio.play();
      responseVideo.play();
  }, { once: true });
  ```
- **Why third:** Even when everything works technically, the audience hears Satomi's voice while watching a frozen or "thinking" avatar. It breaks the core illusion of the product. This is Gemini's most important unique finding and was confirmed critical in Cycle 2.
- **Acceptance test:** Throttle network to Fast 3G → submit query → audio does not begin until avatar video begins moving simultaneously.

---

### 4. Thinking/Processing State — No Feedback on Long Delays
- **File:Line:** `oracle_live.html:1096–1103` (thinking video fallback logic)
- **What:** If the thinking animation video fails to load or the GPU/server queue is long, the user sees a static black frame or frozen avatar with no status indicator. Add:
  - A CSS fallback animated pulse ring behind the avatar container (pure CSS, zero network dependency)
  - A visible status string that updates: `"Thinking..." → "Almost ready..." → "Taking longer than expected — still working"` on a timer (5s, 15s intervals)
- **Why fourth:** During a live demo, a 10-second silence with a static screen will prompt someone in the audience to say "is it frozen?" — which derails the presenter regardless of whether it recovers.
- **Acceptance test:** Simulate 20-second server response delay → status text updates at correct intervals → CSS pulse visible throughout → no black screen.

---

### 5. GPU / Server Queue — No Queue Position or Wait Communication
- **File:Line:** Server-side queue handler (single-source Grok finding, score 6/10)
- **What:** If the GPU server is under load, requests queue silently. Surface queue state to the frontend:
  - Emit a queue position signal from the backend (`"You're #3 in line"`)
  - Display it in the thinking state UI alongside the existing animation
- **Why fifth:** Queue silences are the most likely cause of multi-second freezes. Without communication, every queue wait reads as a crash to the audience.
- **Acceptance test:** Submit two simultaneous requests → second request displays queue position → updates to 0 when processing begins.

---

## P2 — POLISH: Do these if time permits after P0/P1 are green

### 6. Error Handling / Network Failure — No Recovery on Dropped Connection
- **What:** If the fetch to the response API fails mid-demo (flaky venue WiFi), the UI silently stalls. Add a catch on all network calls that surfaces a **"Connection lost — tap to retry"** button and resets the avatar to idle state cleanly.
- **Acceptance test:** Kill network mid-request → retry button appears within 3 seconds → re-enabling network and tapping retry produces a valid response.

### 7. Visual Polish / UI Consistency
- **What (Grok-sourced, score 6/10):** Audit all state transitions (gate → thinking → response → idle reset) for visual consistency. Ensure button states, avatar container sizing, and text overlays are stable across the full interaction loop without layout shift.
- **Acceptance test:** Run the full demo flow 5 times consecutively → no layout shifts, no orphaned UI elements, consistent sizing throughout.

---

## IMPLEMENTATION SEQUENCE SUMMARY

| Priority | Item | Owner | Must-Have By |
|---|---|---|---|
| P0-1 | Mic fallback + text input bypass | Frontend | Before rehearsal |
| P0-2 | iOS Safari autoplay gate overlay | Frontend | Before rehearsal |
| P1-3 | Audio/video sync on `canplaythrough` | Frontend | Day before demo |
| P1-4 | Thinking state feedback + CSS pulse | Frontend | Day before demo |
| P1-5 | GPU queue position surfaced to UI | Full-stack | Day before demo |
| P2-6 | Network failure retry button | Frontend | If time permits |
| P2-7 | Visual polish pass | Frontend | If time permits |