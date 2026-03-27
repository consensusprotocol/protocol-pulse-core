# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
## Feature: oracle-forensic

This is my second and final review of the `oracle-forensic` feature code. Having analyzed my own initial findings alongside those from the other AI models, I have a more complete picture of the critical issues.

### 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, while I would have identified general issues with video playback on iOS, the other models (particularly Gemini) were more precise in their diagnosis. They correctly identified the **root cause** was not just any autoplay policy violation, but the specific act of swapping the `src` attribute on a `<video>` element *that was already actively playing* the "thinking" loop. This is a subtle but critical distinction, as it's this specific sequence that corrupts the video element's internal state on iOS Safari, leading to the frozen frame.

Furthermore, their analysis correctly linked the "Recovering..." loop as a direct *symptom* of this primary bug, because the corrupted video element would subsequently fire an `onerror` event on every playback attempt. My initial analysis might have treated these as two separate issues.

### 2. WHERE DO YOU AGREE OR DISAGREE?

After reviewing the consensus report and re-evaluating the code, here is my stance on the key findings:

*   **iOS `src` Swap on Actively Playing Video (U1): AGREE**
    This is unanimously and correctly identified as the P0, critical root cause of the lip-sync failure. The proposed fix of resetting the video element state before assigning a new source (`vid.pause(); vid.removeAttribute('src'); vid.load();`) is the correct and standard solution.

*   **"Recovering" State Loop (U2): AGREE**
    This is a direct consequence of the `src` swap bug. Fixing the root cause will prevent this from happening in the reported scenario. However, the underlying point that the `vid.onerror` handler is not robust is still valid (see New Findings).

*   **Audio/Video Race Condition (Q5): AGREE (Upgraded Assessment)**
    Initially, I under-scored this issue. However, after reviewing the other models' concerns and re-tracing the logic, I now believe this is a **HIGH** severity bug. There is a clear race condition between the audio playback promise and the video readiness event. The `audio.onended` handler at line 1331 attempts to revoke `pendingVideoUrl`. If the audio finishes before the video has a chance to start playing, this line will invalidate the blob URL, causing video playback to fail silently. This is a significant bug.

*   **`_settled` Guard Flag (Q6): DISAGREE**
    I disagree with GPT-4o and Grok on this point. The `_settled` variable is locally scoped within the `playVid` promise executor. It is re-initialized to `false` every time `playVid` is called. It cannot persist state between calls and therefore cannot cause the described bug. This is a false positive.

### 3. NEW FINDINGS FROM THIS REVIEW

The combined analysis of all models in Cycle 1 revealed deeper architectural issues:

1.  **Insufficient `onerror` Recovery Mechanism:** While the "Recovering" loop is caused by the `src` swap bug, the `vid.onerror` handler itself is flawed. It sets a status and moves on, but it **never resets the video element's state**. Should any *other* video error occur in the future (e.g., a legitimately corrupt video chunk), the element would be left in a broken state, triggering the exact same infinite loop. A robust error handler must actively attempt to return the element to a known-good state.

2.  **Unsynchronized Media Playback:** The root of the race condition (Q5) is that the audio playback and video playback are handled in completely separate, unsynchronized asynchronous flows. The `process` function plays audio and resolves its main promise when the audio ends. In parallel, an `EventSource` or `setInterval` fetches the video and calls `playVid` as a fire-and-forget action. This architectural flaw is inherently fragile and should be refactored to use a more coordinated approach, like `Promise.all` or a state manager, to sequence the media correctly.

### 4. REVISED SCORES

My initial assessments have been updated based on the Cycle 1 consensus and my deeper review.

| Subsystem | Cycle 1 Score | Cycle 2 Score | Why changed |
| :--- | :---: | :---: | :--- |
| iOS src-swap / video element reset | 10/10 | 10/10 | Confirmed as the single most critical bug. |
| Blob URL playback failure | 9/10 | 10/10 | Re-classified as a direct and inevitable symptom of the src-swap bug. |
| Recovering state mapping | 8/10 | 9/10 | Score increased, recognizing the handler's lack of robustness is a latent bug beyond the immediate symptom. |
| **Audio/video race condition** | 4/10 | **9/10** | **Upgrade.** Deeper analysis confirms this is a high-severity bug that will cause video playback to fail. |
| **_settled guard / thinking loop** | 3/10 | **1/10** | **Downgrade.** Confirmed as a false positive due to local variable scoping. This is not a bug. |
| State machine reset completeness | 8/10 | 8/10 | No change. The state machine has decent resets, but the underlying async logic is fragile. |

### 5. FINAL PRIORITY LIST

Here is the definitive, ordered list of changes required before this feature can be considered for production.

*   **P0 CRITICAL**
    1.  **Fix iOS `src` Swap:** In `playVid()`, immediately before line 1474, reset the video element to prevent state corruption on iOS.
        -   **File:** `templates/oracle_live.html`, line ~1473
        -   **Fix:**
            ```javascript
            // Add these lines before setting the new src
            vid.pause();
            vid.removeAttribute('src');
            vid.load(); // Forces the element back to an empty state
            
            setOracleState('RESPONDING');
            vid.loop=false;
            // ... continue with setting src etc.
            ```

*   **P1 HIGH**
    1.  **Prevent Audio/Video Race Condition:** Remove the line that prematurely revokes the video's object URL from the audio `onended` handler. This is the simplest, most direct fix.
        -   **File:** `templates/oracle_live.html`, line 1331
        -   **Fix:**
            ```javascript
            // REMOVE or COMMENT OUT this line:
            // if(pendingVideoUrl){ try { URL.revokeObjectURL(pendingVideoUrl); } catch(e) {} }
            ```
    2.  **Harden Video Error Handler:** Make the `vid.onerror` handler robust by resetting the video element's state, ensuring any future errors don't cause an infinite loop.
        -   **File:** `templates/oracle_live.html`, line ~1545
        -   **Fix:**
            ```javascript
            vid.onerror=function(e){
              console.warn('[Satomi] vid.onerror:',e);
              setStat('Recovering\u2026','#f4c46f',true);
              // ADD a reset here to clean up the broken element
              vid.pause();
              vid.src = '';
              setTimeout(function(){ _finish(false); },500);
            };
            ```

### 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The single highest-leverage change is to **reset the video element with `vid.pause()` and `vid.removeAttribute('src')` before assigning a new `src` URL**, as this one fix resolves both the critical lip-sync failure on iOS and the subsequent "Recovering" loop.

### 7. PRODUCTION READY?

**No.**

The application is critically broken for all iOS users due to the P0 bug, which constitutes a large portion of the mobile user base. Furthermore, the P1 race condition creates a significant risk of video playback failure for all users under certain network conditions.

**Conditions for release:** The P0 and P1 issues identified in the priority list must be fixed and tested on target devices, especially iOS on Safari.