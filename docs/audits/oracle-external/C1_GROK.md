### AUDIT REPORT: ORACLE_EXTERNAL FEATURE (templates/oracle_live.html)

I have conducted a thorough review of the provided code in `templates/oracle_live.html` as part of the Protocol Pulse code audit package. Below are my detailed findings and recommendations for the four specific questions posed regarding duplicate functions, iOS Safari polling reliability, minimal viable architecture, and potential failure modes for the Friday demo.

---

### Q1 — DUPLICATE FUNCTION DEFINITIONS

**ANALYSIS:**
- I scanned the entire 2379-line file for duplicate function definitions and variable name collisions. Below is a list of all named functions with their line numbers:
  - `requestMic()`: Line 997
  - `go()`: Line 1064
  - `playIntent()`: Line 1082
  - `si()`: Line 1172
  - `process()`: Line 1175
  - `blobURL()`: Line 1367
  - `playVid()`: Line 1373
  - `initSR()`: Line 1477
  - `toggleMic()`: Line 1498
  - `startRec()`: Line 1500
  - `_newRecognition()`: Line 1484
  - `_submitSpeech()`: Line 1561
  - `stopRec()`: Line 1581
  - `setRec()`: Line 1587
  - `setStat()`: Line 1595 (original), overridden at Line 2165
  - `setBusy()`: Line 1596
  - `showSub()`: Line 1597
  - `hideSub()`: Line 1598
  - `showTX()`: Line 1599
  - `hideTX()`: Line 1600
  - `showCards()`: Line 1601
  - `hideCards()`: Line 1602
  - `showTapOverlay()`: Line 1605
  - `dismissTapOverlay()`: Line 1620
  - `goTextMode()`: Line 1635
  - `submitTextInput()`: Line 1675
  - `stageTextSubmit()`: Line 1686
  - `updateCameraButtonState()`: Line 1697
  - `triggerCamera()`: Line 1704
  - `handleVisionUpload()`: Line 1708
  - `showSecurityAlert()`: Line 1747
  - `_showRecoveryStep()`: Line 1786
  - `_speakVisionGuidance()`: Line 1824
  - `sendVisionImage()`: Line 1956
  - `showVisionStatus()`: Line 2015
  - `hideVisionStatus()`: Line 2019
  - `_addVisionEntry()`: Line 2026
  - `minimizeOracle()`: Line 2111
  - `restoreOracle()`: Line 2125
  - `exitOracle()`: Line 2132
  - `pulseMic()`: Line 885
  - `setupTapFallback()`: Line 897
  - `showActionCard()`: Line 2326
  - `showVisionSponsor()`: Line 2340
  - `hideActionCard()`: Line 2349
  - `trackCardClick()`: Line 2355
  - `fetchTO()`: Line 2318
- **Duplicate Functions:** No function is defined more than once in the traditional sense (i.e., no duplicate `function name()` declarations). However, `setStat()` is overridden at Line 2165 to extend its behavior for the floating UI indicator. This is intentional but should be noted as a potential source of confusion or future bugs if not documented.
- **Variable Name Collisions/Shadowing:** 
  - Global variables like `busy`, `isRec`, `pending`, `recognition`, and `ORACLE_STATE` are used across multiple functions and could be shadowed if local variables with the same names are introduced in patches. For instance, in `process()` (Line 1175), local variables like `_audioFinished` are prefixed with an underscore to avoid collision, which is good practice. However, `vid`, `mic`, and other DOM elements are global and repeatedly accessed without checks for existence, risking errors if DOM structure changes.
  - No explicit shadowing was found, but the heavy use of globals (e.g., `vid`, `mic`, `busy`) increases the risk of accidental overwriting in future patches.

**RISK LEVEL:** LOW
- The absence of duplicate function definitions mitigates immediate risks. The override of `setStat()` is intentional but should be documented. The reliance on global variables poses a latent risk for future development.

**RECOMMENDATION:**
- Document the intentional override of `setStat()` at Line 2165 with a comment explaining its purpose (e.g., `// Override setStat to sync with floating UI indicator`).
- Consider refactoring global DOM references (`vid`, `mic`, etc.) into a single configuration object (e.g., `const DOM = { vid: document.getElementById('vid'), ... }`) to reduce the risk of name collisions and improve maintainability.
- Enforce a naming convention for local variables (e.g., prefix with `_`) to prevent accidental shadowing of globals in future patches.

---

### Q2 — iOS SAFARI POLLING RELIABILITY

**ANALYSIS:**
- **Foreground Polling (90 seconds):** On iOS Safari, a page in the foreground will generally remain alive during 90 seconds of `fetch()` polling as long as the user does not navigate away or minimize the browser. iOS Safari supports background JavaScript execution for a short period (typically up to 30 seconds) after losing focus, but this is not guaranteed for extended periods like 90 seconds. The current polling loop in `process()` (Line 1255-1305) uses repeated `fetch()` calls every 2 seconds for up to 45 attempts, which is within iOS's foreground execution limits if the page remains active.
- **Locking Phone During Polling:** If the user locks their phone during polling, iOS Safari will suspend JavaScript execution after a brief grace period (usually 30 seconds). This means the polling loop will pause, and no further `fetch()` calls will be made until the phone is unlocked and Safari regains focus. Upon unlocking, the JavaScript engine resumes execution, but any pending `setTimeout()` calls may be delayed, potentially causing the polling to miss the video render completion window or exceed the 45-attempt limit.
- **Risk of iOS Killing Page or Suspending JS:** There is a moderate risk of iOS suspending JavaScript execution if the device is under memory pressure or if the user switches apps for an extended period. If the page is backgrounded for more than a few minutes, iOS may terminate the page entirely, especially on older devices with limited RAM. Even if the page survives, the `fetch()` requests may fail due to network interruptions during suspension, and the current code does not handle such failures gracefully beyond a generic timeout (Line 1301).
- **Long-Poll vs. Repeated Short Polls:** A single long-poll `fetch()` request (e.g., with a server-side timeout of 90 seconds) would be more reliable than repeated short polls on iOS Safari. Long-polling reduces the number of network requests, lowering the chance of interruption during suspension. It also simplifies error handling since there’s only one request to monitor. However, long-polling requires server-side support to hold the connection open, which may not be currently implemented in `/oracle/job/{id}`.

**RISK LEVEL:** MEDIUM
- The current polling approach works in ideal conditions but is vulnerable to iOS Safari’s background execution limits and network interruptions during device lock or app switching.

**RECOMMENDATION:**
- Implement a retry mechanism for polling failures due to network interruptions or suspension. After each failed `fetch()` in the polling loop (Line 1261), check if the error is network-related (e.g., `Failed to fetch`) and extend the polling interval or attempt count before giving up.
- Explore server-side long-polling support for `/oracle/job/{id}` to replace the current 2-second interval polling. If the server can hold the connection until the video is ready (or timeout after 90 seconds), this would eliminate the risk of missed polls during iOS suspension. Add a fallback to short polling if long-polling fails.
- Add a user-visible status update (e.g., via `setStat()`) when polling resumes after suspension to inform the user of delays (e.g., “Resuming after pause…”).

---

### Q3 — MINIMAL VIABLE ARCHITECTURE

**ANALYSIS:**
- **State Machine Simplification:** The current state machine (IDLE → WELCOME → LISTENING → PROCESSING → RESPONDING → LISTENING) defined at Line 830-853 is functional but overly complex due to multiple state variables (`ORACLE_STATE`, `busy`, `isRec`) that can desynchronize. For instance, `busy` and `ORACLE_STATE` are updated independently (e.g., `setBusy()` at Line 1596 and `setOracleState()` at Line 832), risking inconsistent UI behavior if one update is missed. The state machine can be simplified by consolidating state logic into a single variable (`ORACLE_STATE`) and deriving UI behavior (e.g., mic disabled/enabled) directly from it.
- **Redundant State Variables:** There are redundant state variables:
  - `busy` (Line 821) overlaps with `ORACLE_STATE` values like `PROCESSING` and `RESPONDING`, both of which imply the system is busy.
  - `isRec` (Line 821) can be derived from `ORACLE_STATE === 'LISTENING'` and whether `recognition` is active, reducing the need for a separate flag.
  - `_greeted` (Line 821) is a one-time flag that could be replaced by checking if `ORACLE_STATE` has transitioned past `WELCOME`.
- **Minimum Set of State Variables:** The minimum set needed for correct operation is:
  - `ORACLE_STATE`: Single source of truth for the current mode (IDLE, WELCOME, LISTENING, PROCESSING, RESPONDING).
  - `recognition`: Tracks the active speech recognition instance (null if not listening).
  - `currentVideoUrl`: Tracks the currently playing video (if any) to prevent overlap or double-play issues.
  - All other flags (`busy`, `isRec`, `_greeted`) can be derived from `ORACLE_STATE` or DOM state (e.g., `mic.classList.contains('rec')`).

**RISK LEVEL:** MEDIUM
- The current architecture works but is prone to desynchronization due to multiple state variables, increasing maintenance complexity and bug risk.

**RECOMMENDATION:**
- Refactor to use `ORACLE_STATE` as the single source of truth. Update `setOracleState()` to handle all side effects (e.g., enabling/disabling `mic`, updating UI status) in one place. Remove `busy` and `isRec` by deriving their values (e.g., `const isBusy = ['PROCESSING', 'RESPONDING', 'WELCOME'].includes(ORACLE_STATE)`).
- Replace `_greeted` with a check on whether `ORACLE_STATE` has progressed beyond `WELCOME` (e.g., store a history flag in localStorage if persistence is needed).
- Add a state transition log (e.g., `console.log('Transitioning from', oldState, 'to', newState)`) in `setOracleState()` to debug desynchronization issues during testing.

---

### Q4 — WHAT WILL ACTUALLY WORK ON FRIDAY DEMO

**ANALYSIS:**
- **Most Likely Failure Mode on iOS Safari:**
  - **Sequence of Events:** During the demo, after the user speaks and `process()` (Line 1175) is called, the polling loop for `/oracle/job/{id}` (Line 1255-1305) starts. If the user locks their phone or switches apps briefly (common during a live demo to check notifications), iOS Safari suspends JavaScript execution. The polling loop pauses mid-cycle. Upon unlocking, the delayed `setTimeout()` calls may exceed the 45-attempt limit (Line 1296), causing the code to abandon polling and restart the mic (Line 1298-1302) without playing the response video. The user sees “Tap mic to respond” but misses the expected Satomi response.
  - **Stuck State Variable:** `ORACLE_STATE` is most likely to get stuck in `PROCESSING` if the polling loop fails silently (e.g., network error not caught properly) and the `.finally()` block (Line 1352) doesn’t execute. This prevents the transition back to `LISTENING`, leaving the mic disabled.
  - **Most Dangerous Race Condition:** The race condition between video playback completion in `playVid()` (Line 1373) and mic reactivation via `startRec()` (Line 1317-1325 or Line 1357-1364). If `playVid()`’s Promise resolves late due to iOS autoplay restrictions (Line 1467-1471), but the `setTimeout()` for `startRec()` fires earlier, the mic may activate while Satomi is still speaking, causing audio overlap or speech recognition errors.
  - **Manual Recovery Action:** If the demo breaks (e.g., no response after speaking, mic stuck disabled), the user should tap the stage area to trigger the fallback tap-to-speak handler (Line 897-917). If that fails, refresh the page to reset to the gate screen and restart the flow via `requestMic()` (Line 997). As a last resort, switch to text input mode via the fallback UI (Line 1059) if mic access remains blocked.

**RISK LEVEL:** HIGH
- The combination of iOS Safari’s background execution limits and the polling-based video fetch introduces a high likelihood of failure during a live demo, especially under non-ideal conditions like phone locking or network hiccups.

**RECOMMENDATION:**
- Add a user-visible recovery button (e.g., “Retry Response”) in the UI when polling times out (Line 1296-1302) or `ORACLE_STATE` remains in `PROCESSING` for over 30 seconds. This button should reset `ORACLE_STATE` to `LISTENING` and restart `startRec()`.
- Mitigate the race condition in `playVid()` by ensuring `startRec()` is only called after confirming `vid.onended` or the safety timeout (Line 1412-1418) has fired. Use a flag (e.g., `_videoPlaying`) to block mic activation until playback is confirmed complete.
- Pre-test the demo on iOS Safari with simulated phone locks to verify polling behavior. If failures occur, reduce the polling interval to 1 second (Line 1293) to increase the chance of catching the video render before the 45-attempt limit.

---

### FINAL VERDICT

- **Number of Duplicate Functions Found:** 0 (Note: `setStat()` is intentionally overridden at Line 2165, not a duplicate).
- **Top 3 Risks for Friday Demo, Ranked by Likelihood:**
  1. **Polling Failure Due to iOS Suspension (HIGH):** Phone lock or app switch during `/oracle/job/{id}` polling causes missed video response (Line 1255-1305).
  2. **Race Condition in Video-to-Mic Transition (HIGH):** `startRec()` activates before `playVid()` completes, risking audio overlap (Line 1317-1325 vs. Line 1449-1451).
  3. **State Desynchronization (MEDIUM):** `ORACLE_STATE` stuck in `PROCESSING` if polling errors aren’t handled, blocking mic reactivation (Line 1352-1364).
- **Single Most Important Fix Still Needed:** Implement a robust polling retry mechanism with user-visible feedback for `/oracle/job/{id}` (Line 1255-1305). Add a fallback long-poll option if server-side support can be enabled before the demo. This addresses the highest-likelihood failure mode on iOS Safari due to suspension during polling.

This audit prioritizes immediate demo reliability while identifying architectural improvements for long-term stability. I’m confident these recommendations will mitigate critical risks if applied promptly.