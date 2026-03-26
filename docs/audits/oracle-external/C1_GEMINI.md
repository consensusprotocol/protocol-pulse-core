This is an audit of `templates/oracle_live.html`.

## Q1 — DUPLICATE FUNCTION DEFINITIONS

### ANALYSIS

A line-by-line scan of the 2400-line file reveals one function redefinition and one critical bug related to a non-existent function.

1.  **Function Redefinition:** The function `setStat` is defined twice.
    *   **First definition (line 1595):** `function setStat(t,c,sp){...}` This is the base implementation.
    *   **Second definition (line 2165):** `setStat = function(msg, color, spin){...}` This is a monkey-patch that wraps the original `_origSetStat` to add logic for the floating "minimized" icon. While intentional, this is a confusing and fragile pattern in a large, monolithic script. If the file were reordered, the monkey-patch could fail.

2.  **Critical `ReferenceError`:** A call is made to a function `hideTranscript` which is never defined.
    *   **Location (line 2160):** `hideSub(); hideTranscript && hideTX();`
    *   **Impact:** The `exitOracle` function attempts to check for the existence of `hideTranscript`. This will throw a `ReferenceError: hideTranscript is not defined`, which will stop the execution of the `exitOracle` function. This means a user trying to exit the session and return to the gate screen will be stuck. The reset logic will fail. This is likely a typo or a remnant from a refactor where `hideTX` was intended.

3.  **Variable Shadowing/Collision:**
    *   **`_thinkTimer` (lines 1191 & 1203):** In the `process()` function, `_thinkTimer` is declared with `var` at line 1191, making it function-scoped. However, it is then assigned to `window._thinkTimer` at line 1203. This is redundant and confusing. Later, `clearInterval` is called on `window._thinkTimer`. This works, but it unnecessarily pollutes the global scope and makes the code harder to reason about. The local `var _thinkTimer` is sufficient.

### RISK LEVEL

-   `setStat` Redefinition: **LOW** (It's an intentional but poor pattern).
-   `hideTranscript` ReferenceError: **CRITICAL** (Guaranteed to break a core UI feature).
-   `_thinkTimer` Collision: **LOW** (Confusing, but not functionally breaking).

### RECOMMENDATION

1.  **CRITICAL FIX:** Immediately fix the `ReferenceError` on line 2160. The likely intent was to call `hideTX()`. Change `hideTranscript && hideTX();` to just `hideTX();`.

    ```javascript
    // Line 2160
    // BEFORE:
    hideSub(); hideTranscript && hideTX();
    // AFTER:
    hideSub(); hideTX();
    ```

2.  Refactor the `setStat` monkey-patch. Integrate the logic for the float button directly into the main `setStat` function to create a single source of truth.

    ```javascript
    // In setStat function (line 1595)
    function setStat(t,c,sp){
      statEl.textContent=t;
      statEl.style.color=c||'#334';
      spinEl.style.display=sp?'block':'none';
      spinEl.style.color=c||'#334';

      // Integrated logic from line 2165
      var f = document.getElementById("oracle-float");
      if(f && _oracleMinimized){
        if(t === "Speaking") f.classList.add("speaking");
        else f.classList.remove("speaking");
      }
    }
    // Then delete lines 2164-2172 entirely.
    ```

## Q2 — iOS SAFARI POLLING RELIABILITY

### ANALYSIS

The current polling mechanism (`setTimeout` in a loop) is fragile on iOS Safari.

1.  **Foreground Execution:** For the 8-15 second render time, the polling will likely work if the user keeps the app in the foreground and the screen on. However, extending this to the full 90-second timeout is risky. iOS can still throttle timers for pages it deems inactive, even in the foreground, leading to delayed or bunched-up polls. The "Satomi is thinking... Xs" UI is crucial for user patience.

2.  **Screen Lock / Backgrounding:** If the user locks their phone or switches to another app, iOS Safari will aggressively suspend or throttle JavaScript execution. The `setTimeout` chain will be paused. When the user returns, the timers may resume, but the timing will be completely desynchronized from the wall clock. The 45 attempts could take much longer than 90 seconds to complete, or the chain could break entirely.

3.  **Risk of Page Termination:** Yes, there is a significant risk. If the user switches to a memory-intensive app (like the Camera or a game), iOS may terminate the Safari tab to reclaim memory. When the user returns, the page will reload from scratch, losing the `videoJobId` and all session state. The user will be back at the gate screen, and the response will be lost.

4.  **Long-Polling vs. Short-Polling:** A single long-polling request would be significantly more reliable on iOS. The `fetch()` request is handed off to the OS networking layer, which is not suspended when the app is backgrounded. The TCP connection can remain open. When the server responds, the `fetch` promise will resolve the next time the JavaScript event loop is given execution time (i.e., when the user returns to the app). This completely bypasses the unreliability of `setTimeout`. A WebSocket connection would be even better, as it's designed for this exact push-based communication pattern.

### RISK LEVEL

**HIGH**. The current polling implementation is not robust against common mobile user behaviors like screen locking or app switching, making it very likely to fail during a real-world demo or in production.

### RECOMMENDATION

1.  **Immediate Mitigation:** Increase the timeout on the `fetchTO` call inside the poll loop to be slightly longer than the interval (e.g., 3000ms for a 2000ms interval) to handle minor network hiccups. This is a minor improvement.
2.  **Recommended Fix:** Change the architecture from short-polling to long-polling. The server-side `/oracle/job/{id}` endpoint would need to be modified to hold the connection open until the video is ready or a timeout occurs (e.g., 90 seconds). The client-side code would simplify to a single `fetch` call with a long timeout.

    ```javascript
    // Simplified client-side long-poll
    function pollForVideo(videoJobId) {
        setStat('Rendering your brief…', '#f4c46f', true);
        // Single fetch with a 95-second timeout
        fetchTO(A + '/oracle/job/' + videoJobId, {}, 95000)
            .then(res => {
                if (!res.ok) throw new Error('Polling failed');
                return res.blob();
            })
            .then(videoBlob => {
                if (videoBlob && videoBlob.size > 10000) {
                    var url = blobURL(videoBlob);
                    // ... play video ...
                } else {
                    throw new Error('Polling timed out or invalid blob');
                }
            })
            .catch(err => {
                console.warn('[Satomi] Video poll failed:', err);
                // ... handle error, restart mic ...
            });
    }
    ```

## Q3 — MINIMAL VIABLE ARCHITECTURE

### ANALYSIS

The current architecture suffers from state fragmentation. Multiple boolean flags (`busy`, `isRec`, `_greeted`) are used alongside a primary state string (`ORACLE_STATE`), leading to desynchronization and complex conditional logic.

1.  **State Simplification:** The state machine itself is logical (IDLE → ... → RESPONDING → LISTENING). The implementation is the problem. The `busy` flag often acts as the primary lock, while `ORACLE_STATE` is updated but not always checked. `isRec` is largely redundant if the `ORACLE_STATE` is `'LISTENING'`.

2.  **Redundant Variables:**
    *   `busy` and `isRec` can be completely replaced by `ORACLE_STATE`.
        *   `busy = true` is equivalent to `ORACLE_STATE` being `'PROCESSING'` or `'RESPONDING'`.
        *   `isRec = true` is equivalent to `ORACLE_STATE` being `'LISTENING'`.
    *   The code is littered with checks like `if(busy) return;` and `if(!isRec && mic && recognition)`. These could all be replaced by checking `if (ORACLE_STATE !== 'LISTENING') return;`.

3.  **Minimum State Variables:** A robust system can be built with just two primary state variables:
    *   `ORACLE_STATE` (string): The single source of truth for the system's current mode (e.g., `IDLE`, `LISTENING`, `PROCESSING`, `RESPONDING`).
    *   `_greeted` (boolean): This is a simple, effective one-time flag to manage the initial entry flow. It's acceptable as-is.

### RISK LEVEL

**HIGH**. The fragmented state management is the root cause of most potential race conditions and bugs where the UI gets "stuck". A small logic error in updating one of the flags can lead to a deadlock.

### RECOMMENDATION

Adopt a "single source of truth" model for state.

1.  **Eliminate `busy` and `isRec` globals.**
2.  Make the `setOracleState` function the **only** place where UI and functional state is changed. This function should become a comprehensive state transition handler.

    ```javascript
    // Example of a consolidated state manager
    function setOracleState(newState) {
      console.log('[Satomi] State →', newState);
      ORACLE_STATE = newState;

      // Reset all UI to a known baseline
      mic.disabled = true;
      spinEl.style.display = 'none';
      mic.classList.remove('rec');
      // ... etc ...

      switch (newState) {
        case 'LISTENING':
          mic.disabled = false;
          setStat('Listening…', '#6cff9f', false);
          // Stop any previous recognition and start a new one
          if(recognition) try { recognition.stop(); } catch(e) {}
          startRec(); // startRec should ONLY try to start, not check state
          break;

        case 'PROCESSING':
          setStat('Processing…', '#f4c46f', true);
          if(isRec || recognition) stopRec(); // stopRec should ONLY try to stop
          break;

        case 'RESPONDING':
          setStat('Speaking', '#6cff9f', false);
          if(isRec || recognition) stopRec();
          break;
        
        // ... other states
      }
    }
    ```
3.  Refactor all code to call `setOracleState()` instead of manually setting `busy=true`, `mic.disabled=true`, etc. For example, in `process()`, the first line should be `setOracleState('PROCESSING')`. When a response video finishes, the final action should be `setOracleState('LISTENING')`.

## Q4 — WHAT WILL ACTUALLY WORK ON FRIDAY DEMO

### ANALYSIS

Given the current patched code, the most likely failure on an iPhone in a live demo is a **state desynchronization after a video response, resulting in an unresponsive microphone.** The UI will appear ready, but the speech recognition will not be active.

1.  **Exact Sequence of Failure:**
    a. The demo works for the first 1-2 questions.
    b. A response video is fetched and `playVid()` is called.
    c. `playVid()` begins playing. The `onended` event is the primary way the system knows to continue. On iOS, this event can sometimes be unreliable. The code has fallbacks (`ontimeupdate`, timeouts) but this adds complexity.
    d. The `playVid` promise resolves (either via `onended` or a fallback).
    e. This triggers the `.then()` and `.finally()` blocks in the `process` function's promise chain.
    f. **The Race Condition:** The `finally` block on line 1352 sets a `setTimeout` to restart recognition after 1000ms. However, the `playVid` function itself (line 1403) also sets a `setTimeout` of 300ms to clean up the video element. If there is any slight hiccup, another error, or an unexpected event, multiple paths could try to set the state.
    g. The most likely outcome is that `setOracleState('LISTENING')` is called (line 1355) and the status text changes to "Listening...", but the `recognition.start()` call inside the `setTimeout` on line 1360 fails silently. This can happen on iOS if a previous recognition instance wasn't perfectly cleaned up, or if the audio context is in a bad state.

2.  **Stuck State Variable:** `isRec` will be `false`, which is correct. However, the *actual speech recognition engine* will not be running. The user will see a UI that implies listening (`micHint.textContent = 'tap to speak'`, `stat-text` says "Listening..."), but no audio is being captured. The `ORACLE_STATE` might be `'LISTENING'`, but the underlying Web Speech API is not.

3.  **Most Dangerous Race Condition:** The cleanup and restart logic that occurs when `playVid()` finishes. Multiple timers (`playVid`'s internal timers, the `process().finally()` timer) and promise resolutions all converge on the same goal: restarting the microphone. A slight deviation in timing can leave the Web Speech API in an invalid state, causing the next `recognition.start()` to fail.

4.  **Manual Recovery Action:**
    *   **Do not reload the page.** This looks unprofessional.
    *   The designed recovery is to **click the "Exit" button (the `&times;` icon)** in the top right. This calls `exitOracle()`, which should reset the state and return to the main gate screen.
    *   **However, this will fail!** As identified in Q1, `exitOracle` will crash due to the `hideTranscript` ReferenceError.
    *   **Therefore, the *only* reliable recovery during the demo is a full page reload.** The presenter should say something like, "Let's give Satomi a fresh start," and discreetly reload the browser tab.

### RISK LEVEL

**CRITICAL**. The combination of a fragile state-restart mechanism and a broken `exitOracle` function means a common failure mode has no graceful recovery path, forcing a page reload during a live demo.

### RECOMMENDATION

1.  **Fix the `exitOracle` function immediately** as described in Q1. This provides a non-reload recovery path.
2.  Simplify the mic restart logic. Remove the `setTimeout`s in the `process` promise chain's `.finally()` block. The `setOracleState('LISTENING')` call should be the single, authoritative trigger for restarting recognition, and it should happen directly inside the state transition function itself, not in a timer.

---

### FINAL VERDICT

*   **Number of duplicate functions found:** 1 (`setStat` is redefined/monkey-patched). Additionally, 1 critical `ReferenceError` for a non-existent function (`hideTranscript`) was found.

*   **Top 3 risks for Friday demo, ranked by likelihood:**
    1.  **Unresponsive Mic:** The microphone fails to activate after a video response due to a state desynchronization race condition, leaving the UI stuck.
    2.  **Broken Exit Button:** The user encounters the unresponsive mic, tries to exit gracefully using the `&times;` button, and the app state freezes completely due to the `hideTranscript` JavaScript error.
    3.  **Polling Failure:** The presenter locks/unlocks their iPhone or switches apps briefly, causing the video polling loop to break and the response to never arrive.

*   **Single most important fix still needed:**
    **Fix the `ReferenceError` on line 2160 in the `exitOracle` function.** This is a guaranteed crash on a critical user recovery path. Without this fix, any minor glitch during the demo becomes a major one requiring a full page reload.