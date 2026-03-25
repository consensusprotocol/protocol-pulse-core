# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
## Feature: oracle-fix
## My Second and Final Review

---

Having reviewed my initial findings alongside the comprehensive analysis from the other AI models and the consensus report, I have a much clearer and more robust understanding of the issues. The collective intelligence has highlighted several nuances I initially missed and has solidified the path to a production-ready fix.

### 1. WHAT DID THEY CATCH THAT YOU MISSED?

My initial analysis correctly identified the `playVid` promise hang as the central issue. However, the other models provided critical depth and additional findings that I overlooked:

*   **The *Why* of the Hang:** Gemini's analysis was particularly sharp in pointing out that a `.finally()` block *never* executes on a promise that remains in a `pending` state. I had correctly identified that the block wasn't running but failed to articulate this fundamental promise behavior as the root cause, which makes the bug's severity undeniable.
*   **Proactive `onended` Fallback:** Gemini's suggestion to use the `timeupdate` event to detect the end of the video is a significantly more elegant and user-friendly solution than simply relying on a long safety timeout. It prevents the user from waiting 30 seconds for the app to un-hang itself. This is a brilliant piece of defensive programming I did not consider.
*   **Speech Recognition Dead-End:** GPT-4o correctly identified a secondary but crucial bug in the `recognition.onend` handler. If the recognition ends due to silence (`pending` is empty), the current logic does nothing, effectively breaking the conversation loop. The user is left with a silent, unresponsive mic.
*   **Resolution Path Race Condition:** The consensus report, by combining all fixes, implicitly revealed a new potential issue: without a `settled` flag, the three potential resolution paths for the `playVid` promise (`onended`, `onerror`, `_safetyTimer`) could race against each other, leading to unpredictable state changes.

### 2. WHERE DO YOU AGREE OR DISAGREE?

*   **Q1 — `playVid` Promise Hang:** **Strongly Agree.** This is the unanimous, critical bug. The application hangs indefinitely. The consensus to modify the safety timer to resolve/reject the promise is the correct and only viable fix.
*   **Q2 — iOS Autoplay + Blob URLs:** **Agree.** This is a primary *trigger* for the Q1 hang. iOS's strict policies make events like `onended` unreliable, necessitating the robust promise handling discussed in Q1. The `tap-to-play` overlay is a necessary but insufficient patch.
*   **Q3 — Race between `.then()` and `.finally()`:** **Agree (with Grok's clarification).** There is no race condition. The promise specification guarantees `.finally()` runs after `.then()` settles. The issue isn't a race; it's that *neither* block runs because of the hung promise. I now see this as a symptom, not a separate bug.
*   **Q4/Q5 — `process()` / `recognition.onend` Issues:** **Strongly Agree.** GPT-4o's finding is correct. The user speaking nothing is a common case, and the app must handle it gracefully by restarting the listener, not by going silent. This is a high-severity bug that breaks the core user experience loop.
*   **Q7 — iOS Mic Activation After Video:** **Agree.** The `setTimeout` of 400ms is fragile and a code smell in this context. While it might work because it's part of a chain initiated by a user gesture, it's not guaranteed. Removing the delay and calling `startRec()` directly within the promise's `.then()` block is more robust.

### 3. NEW FINDINGS FROM THIS REVIEW

The combined analysis of all models and their proposed fixes revealed one critical architectural flaw that no single model isolated:

*   **Non-Idempotent Promise Resolution:** The `playVid` function has three asynchronous exit paths: `onended`, `onerror`, and the `_safetyTimer`. The original code, and some naive fixes, would allow more than one of these to execute. For instance, the safety timer could fire, and moments later, a delayed `onended` event could also fire. This would lead to calling state-cleanup logic twice and attempting to settle an already-settled promise.

    **The fix requires a `settled` flag** to ensure that whichever of these three events fires *first* is the only one that can resolve the promise and perform the cleanup. This makes the resolution logic idempotent and prevents race conditions between the fix mechanisms themselves. The consensus report correctly included a sample implementation of this pattern.

### 4. REVISED SCORES

| Subsystem | Cycle 1 Score | Cycle 2 Score | Why changed |
|---|---|---|---|
| Q1 — `playVid` Promise Hang | CRITICAL | CRITICAL | Unchanged. Remains the show-stopper bug. |
| Q2 — iOS Autoplay + Blob URLs | HIGH | HIGH | Unchanged. It's a primary trigger for the critical hang. |
| Q3 — Race `.then()`/`.finally()` | MEDIUM | LOW / Not a Bug | Re-classified as a misunderstanding of the core bug (Q1). The promise chain logic is sound; it just never gets to execute. |
| Q4 — `process()` Never Fires | HIGH | HIGH | Unchanged. This bug breaks the core conversational loop and creates a dead end for the user. |
| Q5 — Recognition `onend` Empty | MEDIUM | (merged into Q4) | Merged with Q4 as they describe the same user-facing problem: the app stops listening after silence. |
| Q7 — iOS Mic Activation | HIGH | MEDIUM | Downgraded slightly. While fragile, it's part of a trusted event chain. The primary risk is flakiness, not a guaranteed hang like Q1. It should still be fixed. |
| **NEW** — Resolution Path Race | N/A | CRITICAL | This new finding is critical because a faulty fix for Q1 could introduce new, subtle bugs. The `settled` flag is essential for a correct implementation. |

### 5. FINAL PRIORITY LIST

Here is the definitive list of changes required to ship this feature.

**P0 — CRITICAL (Must fix before shipping)**

1.  **Fix `playVid` Promise Hang with Idempotent Resolution:** In `templates/oracle_live.html`, rewrite the `playVid` function (line ~1412) to use a `settled` flag. The promise must be resolved or rejected in `onended`, `onerror`, AND the `_safetyTimer`. The first event to fire settles the promise and prevents the others from running. This is the single most critical fix.

    ```javascript
    // file: templates/oracle_live.html, around line 1412
    function playVid(url){
      return new Promise(function(res, rej){ // Add rej
        // ... (initial setup)
        var settled = false;
        function settle(isSuccess, value) {
          if (settled) return;
          settled = true;
          clearTimeout(_safetyTimer);
          if (isSuccess) res(value);
          else rej(value);
        }
        
        var _safetyTimer = setTimeout(function(){
          console.warn('[Satomi] Safety timeout — forcing state transition');
          vid.style.opacity='0'; vid.src='';
          setBusy(false);
          setOracleState('LISTENING');
          settle(false, new Error('playVid safety timeout'));
        }, 30000);

        vid.onended = function(){
          // ... (cleanup logic)
          settle(true);
        };

        vid.onerror = function(){
          // ... (error handling logic)
          settle(true); // Resolve even on error to allow the chain to continue
        };
        // ... (rest of function)
      });
    }
    ```

**P1 — HIGH (Essential for a good user experience)**

1.  **Make Speech Recognition Loop Robust:** In `templates/oracle_live.html`, modify the `recognition.onend` handler (line ~1494) to restart the recognition if it stops due to silence and the app is not busy.

    ```javascript
    // file: templates/oracle_live.html, around line 1494
    recognition.onend = function() {
      setRec(false);
      var _pend = pending.trim();
      pending = ''; // Clear pending immediately
      if (_pend && !busy) {
        setStat('Processing…', '#f4c46f', true);
        setTimeout(function() { process(_pend); }, 100);
      } else if (!_pend && !busy) {
        // User was silent, just restart listening without processing
        console.log('[Satomi] Silence detected, restarting recognition.');
        startRec(); 
      }
    };
    ```
2.  **Add Proactive Video End Detection:** To avoid relying on the 30s safety timer, add a `timeupdate` event listener inside `playVid` as a fallback for the unreliable `onended` event.

    ```javascript
    // file: templates/oracle_live.html, inside the playVid promise
    vid.addEventListener('timeupdate', function onTimeUpdate() {
        // If we are within 0.25s of the end, consider it ended.
        if (vid.duration > 0 && vid.currentTime >= vid.duration - 0.25) {
            vid.removeEventListener('timeupdate', onTimeUpdate);
            console.log('[Satomi] Forcing onended via timeupdate.');
            if (vid.onended) vid.onended();
        }
    });
    ```

**P2 — MEDIUM (Recommended improvements)**

1.  **Remove `setTimeout` for `startRec`:** In `templates/oracle_live.html`, line 1087, remove the 400ms delay and call `startRec()` directly. This makes the mic activation more immediate and less fragile.

    ```javascript
    // file: templates/oracle_live.html, around line 1086
    setOracleState('LISTENING');
    // setTimeout(function(){ // REMOVE
      if(!busy && !isRec && mic){
        mic.disabled = false;
        startRec();
        setStat('Listening…', '#6cff9f', false);
      }
    // }, 400); // REMOVE
    ```

### 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The single highest-leverage change is to **guarantee the `playVid` promise always settles by implementing mutually exclusive resolution paths for success, error, and timeout,** which completely eliminates the application-hanging bug.

### 7. PRODUCTION READY?

**No.**

The application is not production-ready. The `playVid` promise hang (P0) is a 100% reproducible, session-ending bug on a major target platform (iOS Safari). Shipping in this state would render the feature unusable for a significant portion of the audience.

**Conditions for Approval:**
1.  All **P0** and **P1** fixes listed above must be implemented.
2.  The fixes must be validated via manual testing on multiple physical iOS devices (e.g., iPhone with recent iOS) to confirm that the greeting video plays, the mic activates correctly afterward, and the listening loop continues even after a period of user silence.