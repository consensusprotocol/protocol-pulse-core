### PROTOCOL PULSE CODE AUDIT — FRIDAY DEMO READINESS REVIEW

As part of the pre-merge quality gate for the Friday demo, I have conducted a thorough audit of the provided files (`oracle_live.html` and `merch.html`) with a focus on potential failure modes, user experience issues, and demo readiness. Below are my detailed responses to the 8 brutal questions, identifying specific issues, their severity, and actionable fixes. My goal is to ensure the demo does not embarrass the team in front of a live audience of 10+ people.

---

### Q1 — MOST LIKELY FAILURE MODE DURING LIVE DEMO
- **FAILURE MODE**: Microphone permission denial or failure to unlock audio context on mobile devices, leading to the app being stuck at the gate screen with no clear recovery path.
- **SEVERITY**: CRITICAL
- **FILE:LINE**: `oracle_live.html:977-986`
- **FIX**: Enhance error messaging to provide a more prominent retry mechanism and a fallback for users who can't grant mic access. Add a visible "Retry Mic Access" button directly in the error message (line 978) with styling to stand out (e.g., `style="background:#ff3b5f;color:#fff;padding:8px 16px;border:none;border-radius:4px;cursor:pointer;"`). Additionally, implement a timeout fallback after 10 seconds of no mic access to suggest a text input mode if available.
- **DEMO IMPACT**: The audience sees the app stuck at the gate screen with an error like "Microphone blocked," causing confusion and halting the demo. Without a clear retry or bypass, the presenter must awkwardly explain or reload the page, breaking flow.

---

### Q2 — PERCEIVED BROKENNESS
- **FAILURE MODE**: Lack of feedback during long processing delays (e.g., video rendering or network latency) makes the app appear broken. The "thinking" video plays, but if it fails to load, users see a black screen or static avatar with no status update.
- **SEVERITY**: HIGH
- **FILE:LINE**: `oracle_live.html:1096-1103`
- **FIX**: Strengthen the fallback mechanism for the thinking video. If `vid.onerror` triggers (line 1097), immediately update the status text to "Loading response... please wait" (via `setStat` call) to reassure users. Add a secondary timeout check at line 1101 to revert to static avatar with a message if playback doesn't start within 3 seconds.
- **DEMO IMPACT**: Audience perceives the app as broken due to a black screen or no visible progress for 10-15 seconds during processing. They may think the app crashed, leading to presenter intervention and loss of trust.

---

### Q3 — MOBILE-SPECIFIC FAILURE MODES
- **FAILURE MODE**: iOS Safari autoplay restrictions prevent the thinking video or response video from playing without user interaction, resulting in a static avatar or black screen. Additionally, touch targets for buttons like the mic (line 480) are too small on smaller screens.
- **SEVERITY**: CRITICAL
- **FILE:LINE**: `oracle_live.html:1100-1101` (autoplay issue), `oracle_live.html:480-483` (touch target)
- **FIX**: For autoplay, add a user-interaction fallback at line 1101: if `vid.play()` fails with a `NotAllowedError`, display a one-time overlay with a "Tap to Play" button over the video area (new DOM element at line 681). For touch targets, increase the minimum size of interactive elements like `#mic` to 48x48px (already set at line 481, but ensure it’s enforced with `min-width` and `min-height` in CSS for all buttons).
- **DEMO IMPACT**: On mobile, the audience sees a non-responsive app if videos don’t play, requiring the presenter to tap manually (if they notice). Small touch targets cause missed taps, making the demo look unpolished and frustrating the presenter.

---

### Q4 — GPU CONTENTION
- **FAILURE MODE**: Not directly addressed in the provided HTML files since `avatar_server.py` is not included. However, based on the frontend code, if the GPU is busy rendering for another user, fetch requests to `/oracle/chat` or `/oracle/job` (line 1118, 1219) could timeout or return errors, leaving the user with a "thinking" loop or static avatar indefinitely.
- **SEVERITY**: HIGH
- **FILE:LINE**: `oracle_live.html:1118-1121`
- **FIX**: Implement a server-side queue status check before initiating a render request. At line 1118, before calling `/oracle/chat`, add a pre-check to `/oracle/status` to see if the GPU is available. If not, display a message like "High demand — waiting for render slot..." via `setStat` and retry after a delay. Add a client-side timeout of 90s (already set, but reinforce with a user-facing message at line 1121).
- **DEMO IMPACT**: Audience sees the app stuck in a "thinking" state for an extended period (or timeout error if fetch fails), making the demo appear slow or broken. The presenter may need to apologize or restart, disrupting the flow.

---

### Q5 — WORST UX MOMENT
- **FAILURE MODE**: The transition from user speaking to processing feels abrupt and lacks clear feedback. After stopping recording (line 1431-1436), the app shows the thinking video, but if it fails or delays, there’s no immediate status update, leaving users uncertain if their input was captured.
- **SEVERITY**: HIGH
- **FILE:LINE**: `oracle_live.html:1431-1436`
- **FIX**: At line 1433, before attempting to play the thinking video, add an immediate `setStat('Processing your request...', '#f4c46f', true)` call to confirm input receipt. If the video fails to load (add check after line 1432), ensure the static avatar remains visible with a fallback message.
- **DEMO IMPACT**: Audience feels confused after speaking, unsure if Satomi heard them, especially if network latency delays the thinking video. This hesitation breaks immersion and makes the interaction feel clunky.

---

### Q6 — AMATEUR VISUAL ELEMENTS
- **FAILURE MODE**: The error messages at the gate screen (line 978-984) are visually inconsistent and lack polish, using inline HTML with minimal styling. They appear as raw text with basic links, clashing with the otherwise sleek cyberpunk aesthetic.
- **SEVERITY**: MEDIUM
- **FILE:LINE**: `oracle_live.html:978-984`
- **FIX**: Style error messages to match the app’s design language. At line 978, wrap the error text in a styled container (e.g., `<div style="background:#1a0608;border:1px solid rgba(255,59,95,.3);padding:10px 14px;border-radius:6px;color:#ff3b5f;font-family:'JetBrains Mono',monospace;font-size:11px;">`) and use consistent button styling for retry actions.
- **DEMO IMPACT**: Audience notices the unstyled error text, which undercuts the premium feel of the app. It signals a lack of attention to detail, especially if an error occurs during the demo.

---

### Q7 — HIGHEST IMPACT SINGLE CHANGE
- **FAILURE MODE**: Insufficient feedback during processing delays or video load failures, leading to perceived brokenness.
- **SEVERITY**: CRITICAL
- **FILE:LINE**: `oracle_live.html:1096-1103`
- **FIX**: Add robust status feedback during processing. At line 1097, after `vid.onerror`, insert `setStat('Video failed — preparing response...', '#f4c46f', true);` and ensure a fallback to static avatar is visible. Add a progress counter (already partially implemented at line 1075-1087) that updates every 5 seconds with reassuring messages like "Still rendering... Xs elapsed."
- **DEMO IMPACT**: This change prevents the audience from seeing a black screen or thinking the app is broken during inevitable network or render delays, preserving demo flow and confidence in the product.

---

### Q8 — SILENT NETWORK FAILURES
- **FAILURE MODE**: If the avatar server is down, fetch requests (e.g., line 1118) fail silently after timeout, leaving the user in a "thinking" state with no error message. Slow 3G connections exacerbate this by delaying every fetch beyond the 90s timeout.
- **SEVERITY**: CRITICAL
- **FILE:LINE**: `oracle_live.html:1118-1121`, `oracle_live.html:1308-1315`
- **FIX**: At line 1309, enhance the timeout error handling to display a user-friendly message: `setStat('Network timeout — please check connection and retry.', '#ff3b5f', false);`. Add a retry button after timeout (new DOM element at line 1310) to reattempt the fetch. For slow connections, reduce the timeout to 60s at line 1118 and show progressive feedback (e.g., "Still connecting..." after 20s).
- **DEMO IMPACT**: Audience sees the app stuck in a loading state with no explanation if the server is down or connection is slow. The presenter must intervene, potentially abandoning the demo segment, which is catastrophic for perception.

---

### FINAL VERDICT
- **CRITICAL ISSUES FOUND**: 4 (Q1: Mic permission, Q3: Mobile autoplay, Q7: Processing feedback, Q8: Network failures)
- **DEMO-READY TODAY?**: No. The current state has multiple critical failure modes (mic access, mobile issues, network handling) that could derail a live demo. Without fixes, there’s a high risk of embarrassment in front of 10+ people.
- **TOP 3 MUST-FIX ITEMS BEFORE FRIDAY**:
  1. **Mic Permission Handling** (`oracle_live.html:977-986`) - Add prominent retry button and fallback text input mode to prevent demo halt on denial.
  2. **Processing Feedback** (`oracle_live.html:1096-1103`) - Strengthen status updates and fallbacks for video load failures to avoid perceived brokenness.
  3. **Network Failure Recovery** (`oracle_live.html:1118-1121`) - Implement clear timeout messages and retry options to handle server downtime or slow connections gracefully.

This audit prioritizes user-facing issues that could disrupt the demo experience. Immediate action on the critical fixes is essential to ensure a polished, reliable presentation on Friday.