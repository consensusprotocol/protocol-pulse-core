An audit of the provided `oracle_live.html` file has been completed. The analysis focuses on the race condition and state management issues on iOS Safari that prevent microphone activation after the initial greeting video.

### Q1 — PLAYVID PROMISE HANG

*   **ANALYSIS:**
    If the `playVid()` Promise (created on line 1413) never resolves, the entire application state becomes permanently frozen. The execution chain is as follows:
    1.  `playIntent('GREETING')` is called at line 1044.
    2.  `setBusy(true)` is called at line 1053, disabling all user interaction.
    3.  A `fetch` is made, and its result is piped into `playVid()` at line 1079.
    4.  Inside `playVid()`, `setOracleState('RESPONDING')` is called at line 1414, which disables the mic button.
    5.  The `playVid()` Promise is designed to resolve *only* in the `vid.onended` (line 1438) or `vid.onerror` (line 1452) event handlers.
    6.  As stated, `onended` is unreliable on iOS and may never fire. If no error occurs, the Promise remains in a pending state forever.
    7.  The subsequent `.then()` block in `playIntent()` (starting line 1080) is never executed. This means the crucial `startRec()` call (line 1090) is never reached.
    8.  Crucially, the `.finally()` block at line 1100 also **never executes**. A `.finally()` clause only runs after a promise is settled (either resolved or rejected), not while it is pending.

    The UI is stuck in this state:
    *   The `busy` flag remains `true`.
    *   The `ORACLE_STATE` is `'RESPONDING'`.
    *   The mic button is disabled (per lines 846-847).
    *   The user sees the last frame of the greeting video.
    *   No further actions are possible. The application is completely hung.

*   **BUG CONFIRMED:** Yes
*   **SEVERITY:** CRITICAL
*   **FIX:** The safety timer within `playVid` must be modified to not only reset state but also to resolve the Promise, thereby un-hanging the entire application.

    ```javascript
    // MODIFIED file: templates/oracle_live.html
    // AROUND LINE 1413
    function playVid(url){
      return new Promise(function(res, rej){ // Add rej
        setOracleState('RESPONDING');
        vid.loop=false;
        vid.src=url;
        vid.style.opacity='1';
        if(window._matrixHide) window._matrixHide();
        var _safetyTimer = setTimeout(function(){
          if(busy){
            console.warn('[Satomi] Safety timeout — forcing mic unlock after 30s');
            setBusy(false);
            if(window._thinkTimer){clearInterval(window._thinkTimer);window._thinkTimer=null;}
            setOracleState('LISTENING');
            rej(new Error('playVid safety timeout')); // <<< FIX: Reject the promise to un-hang the chain
          }
        }, 30000);
        try{if(window.parent!==window) window.parent.postMessage({type:'oracle:speaking'},'*');}catch(e){}
        
        var onFinish = function() { // Create a unified finish handler
            clearTimeout(_safetyTimer);
            if(window._thinkTimer){clearInterval(window._thinkTimer);window._thinkTimer=null;}
            vid.style.opacity='0';
            setTimeout(function(){ vid.src=''; },300);
            if(window._matrixShow) window._matrixShow();
            hideSub();
            setBusy(false);
            setOracleState('LISTENING');
            res();
            try{if(window.parent!==window) window.parent.postMessage({type:'oracle:idle'},'*');}catch(e){}
        };

        vid.onended = onFinish; // Use unified handler
        
        vid.onerror=function(){
          clearTimeout(_safetyTimer);
          if(window._thinkTimer){clearInterval(window._thinkTimer);window._thinkTimer=null;}
          vid.style.opacity='0';
          vid.src='';
          setStat('Recovering\u2026','#f4c46f',true);
          setTimeout(function(){
            setBusy(false);
            setOracleState('LISTENING');
            setStat('Ready','#334',false);
            res(); // Resolve even on error to continue flow
          }, 1500);
        };
        // ... rest of function
    ```

### Q2 — iOS AUTOPLAY + BLOB URLS

*   **ANALYSIS:**
    iOS Safari's handling of media is notoriously strict. While autoplay of `muted` videos (as done on line 1455) is generally permitted, the reliability of events like `onended` for programmatically controlled, `blob:`-sourced media is poor. The browser can de-prioritize or even fail to fire the event if the tab is not perfectly in focus or due to other internal heuristics. A scenario where the video plays to completion but `onended` never fires is common. The code does not account for this possibility beyond the fixed 30s safety timer, which is itself flawed (see Q1 and Q8).

*   **BUG CONFIRMED:** Yes
*   **SEVERITY:** HIGH
*   **FIX:** Do not rely solely on `onended`. Add a secondary check using the `timeupdate` event to see if the video has played to within a small threshold of its duration.

    ```javascript
    // ADDED to file: templates/oracle_live.html
    // INSIDE playVid(), AFTER vid.onended, AROUND LINE 1440
        var finished = false;
        function checkTime() {
          if (finished || !vid.duration) return;
          if (vid.currentTime >= vid.duration - 0.25) {
            finished = true;
            console.log('[Satomi] timeupdate triggered onended fallback.');
            vid.onended(); // Manually trigger the onended handler
          }
        }
        vid.addEventListener('timeupdate', checkTime);

        vid.onended = function(){
          if (finished) return; // Prevent double-firing
          finished = true;
          vid.removeEventListener('timeupdate', checkTime);
          // ... original onended logic from Q1 fix ...
          onFinish();
        };
    ```

### Q3 — RACE BETWEEN .then() AND .finally()

*   **ANALYSIS:**
    There is no race condition where `.finally()` runs before `.then()`. In a Promise chain, `.finally()` is guaranteed to execute only after the promise it's attached to is settled. However, there is a subtle timing issue with the `setTimeout` at line 1087.
    1.  The `playVid` promise resolves.
    2.  The `.then()` at line 1080 is executed.
    3.  The `setTimeout` at line 1087 is scheduled to run in 400ms.
    4.  The `.then()` block finishes its synchronous execution.
    5.  The `.finally()` at line 1100 runs *immediately*, calling `setBusy(false)`.
    6.  ~400ms later, the `setTimeout` callback fires. At this point, `busy` is already `false`. The `!busy` check at line 1088 passes, and `startRec()` is called.
    
    While not a bug that breaks the flow, it's a fragile design. The state is set to `!busy` before the mic is actually ready to record. This could allow a user to click something in that 400ms window. The core problem remains the hanging promise, not this specific race.

*   **BUG CONFIRMED:** No (but the code structure is fragile)
*   **SEVERITY:** MEDIUM
*   **FIX:** The logic inside the `.then()` block is too complex. `startRec()` should be called directly, without a `setTimeout`, to keep the action as close as possible to the event that triggered it, which is crucial for iOS permissions.

    ```javascript
    // MODIFIED file: templates/oracle_live.html
    // AROUND LINE 1085
        /* State machine: welcome done → LISTENING. Always activate mic. */
        setOracleState('LISTENING');
        if(!busy && !isRec && mic){ // busy check is redundant here but safe
            mic.disabled = false;
            startRec();
            setStat('Listening…','#6cff9f',false);
        }
    ```

### Q4 — process() NEVER FIRES AFTER GREETING

*   **ANALYSIS:**
    The primary reason `process()` never fires is that `startRec()` is never called due to the hanging Promise described in Q1. If `recognition` never starts, its `onend` handler (line 1494), which is the sole entrypoint to `process()` from speech, can never fire.

    Assuming the primary bug were fixed, `process()` could still fail to fire if:
    1.  The `recognition.onend` event fires.
    2.  The `pending` variable (populated by `onresult` at line 1492) is an empty string.
    3.  The condition `if(_pend.trim() && !busy)` at line 1500 fails because `_pend.trim()` is false.
    4.  The application flow stops, waiting for another user action.

*   **BUG CONFIRMED:** Yes
*   **SEVERITY:** CRITICAL
*   **FIX:** The fix for Q1 is the primary solution. Fixing the hanging promise will ensure `startRec()` is called.

### Q5 — RECOGNITION ONEND WITH EMPTY PENDING

*   **ANALYSIS:**
    The `recognition.onend` handler at line 1494 is not robust. If it fires with an empty `pending` string (e.g., a short utterance, background noise, or immediate silence), the condition `if(_pend.trim() && !busy)` on line 1500 evaluates to false. The function then completes without calling `process()` and without restarting recognition. The UI state is `LISTENING` but `isRec` is false, and the microphone is inactive. The user is forced to tap the microphone again to re-initiate speech recognition. There is no auto-restart logic.

*   **BUG CONFIRMED:** Yes
*   **SEVERITY:** MEDIUM
*   **FIX:** The `onend` handler should be smarter. If it ends without a valid submission and was not manually stopped by the user, it should ideally restart or at least provide clear feedback. A simple fix is to ensure the state is correctly reset to prompt the user again.

    ```javascript
    // MODIFIED file: templates/oracle_live.html
    // AROUND LINE 1495
      recognition.onend=function(){
        setRec(false);
        var _pend = pending;
        pending = ''; // Clear pending immediately
        if(_pend.trim() && !busy){
            setStat('Processing\u2026','#f4c46f',true);
            setTimeout(function(){ if(!busy){ process(_pend); }}, 100);
        } else if (!busy) {
            // No result, just go back to ready state
            setOracleState('LISTENING');
            setTimeout(pulseMic, 100); // Prompt user to speak again
        }
      };
    ```

### Q6 — BUSY FLAG DURING USER SPEECH

*   **ANALYSIS:**
    Yes, the `busy` flag is a central part of the failure mode.
    1.  `playIntent()` sets `busy = true` at line 1053.
    2.  The `playVid()` promise hangs.
    3.  The `.finally()` block that would set `busy = false` (line 1101) is never reached.
    4.  Therefore, `busy` remains `true` indefinitely.
    5.  Even if speech recognition were to run and call `process(text)`, the very first line of defense in `process()` (line 1111) is `if(!text.trim() || busy) return;`. Since `busy` is `true`, the function would exit immediately, and the user's speech would be ignored.

*   **BUG CONFIRMED:** Yes
*   **SEVERITY:** CRITICAL
*   **FIX:** This is a direct symptom of the root cause in Q1. Fixing the hanging promise in `playVid` will ensure the `.finally()` block runs and correctly manages the `busy` flag.

### Q7 — iOS MIC ACTIVATION AFTER VIDEO

*   **ANALYSIS:**
    iOS requires that sensitive APIs like `SpeechRecognition.start()` be initiated from a user gesture. This "trust" can propagate through a promise chain that originates from that gesture. The `requestMic()` function is correctly called from an `onclick` (line 644). The subsequent `startRec()` is called from a promise chain, which is acceptable. However, the `setTimeout` at line 1087 is problematic. It breaks the direct execution chain from the user's gesture, which can cause iOS to reject the `recognition.start()` call. While it might work sometimes, it is not the most reliable method. A direct call within the `.then()` block is far more likely to succeed.

*   **BUG CONFIRMED:** Yes (fragile implementation)
*   **SEVERITY:** HIGH
*   **FIX:** Remove the `setTimeout` and call `startRec()` directly from the `.then()` block once the video promise resolves, as suggested in the fix for Q3.

### Q8 — SAFETY TIMEOUT ADEQUACY

*   **ANALYSIS:**
    The safety timeout is inadequate for two reasons:
    1.  **It's a fixed 30 seconds (line 1426).** If a greeting video is 5 seconds long and hangs, the user is stuck waiting 30 seconds for the app to recover. This is an extremely poor user experience.
    2.  **It doesn't resolve the promise.** As identified in Q1, the timer resets some state but does not resolve the hanging `playVid` promise, leaving the application in a permanently broken state.

    The timeout should be dynamic, based on the video's actual duration, plus a small buffer.

*   **BUG CONFIRMED:** Yes
*   **SEVERITY:** HIGH
*   **FIX:** Tie the timeout to the video's duration and ensure it rejects or resolves the promise.

    ```javascript
    // MODIFIED file: templates/oracle_live.html
    // INSIDE playVid(), REPLACE safetyTimer
    var _safetyTimer = null;
    function setDynamicTimeout() {
        if (_safetyTimer) clearTimeout(_safetyTimer);
        var duration = vid.duration;
        if (duration && isFinite(duration)) {
            // Timeout is video length + 2 seconds buffer
            var timeoutMs = Math.ceil(duration * 1000) + 2000;
            _safetyTimer = setTimeout(function(){
                console.warn('[Satomi] Dynamic safety timeout fired.');
                rej(new Error('playVid dynamic safety timeout'));
            }, timeoutMs);
        }
    }
    vid.addEventListener('loadedmetadata', setDynamicTimeout);
    // Remove the old fixed setTimeout
    ```

---

### FINAL VERDICT

*   **How many CRITICAL issues confirmed?**
    **3.** (Q1: Promise Hang, Q4: Process Not Firing, Q6: Busy Flag Stuck). These are all symptoms of the same root cause.

*   **Root cause of the "greeting plays but mic never activates" bug:**
    The root cause is a **hanging Promise in the `playVid` function**. This is triggered by an unreliable `onended` event on iOS Safari for `blob:`-sourced videos. Because the Promise never settles, the `.then()` and `.finally()` blocks in the `playIntent` function's Promise chain are never executed. This leaves the `busy` flag permanently set to `true` and prevents the `startRec()` function from ever being called, effectively bricking the application. The existing 30-second safety timeout is critically flawed as it fails to resolve or reject the hanging promise.

*   **Ordered fix list (most impactful first):**

    1.  **CRITICAL FIX: Make `playVid` Promise Robust.**
        *   Modify the `_safetyTimer` in `playVid` to **reject the promise** so the application can un-hang.
        *   Make the `_safetyTimer` dynamic, based on `vid.duration` plus a 2-second buffer, set on the `loadedmetadata` event.
        *   Implement a `timeupdate` event listener as a fallback to manually trigger the finish logic if `onended` fails to fire.

    2.  **HIGH FIX: Improve Mic Activation Reliability.**
        *   In `playIntent`, remove the 400ms `setTimeout` wrapper around the `startRec()` call. Activate the microphone directly in the `.then()` block to maintain a clear execution path from the original user gesture.

    3.  **MEDIUM FIX: Harden Speech Recognition Logic.**
        *   Update the `recognition.onend` handler to gracefully handle cases where no speech is detected (i.e., `pending` is empty), preventing a dead UI state and re-prompting the user.