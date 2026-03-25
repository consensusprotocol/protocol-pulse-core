### Q1 — PLAYVID PROMISE HANG

- **ANALYSIS:** In the `playIntent()` function, the `playVid()` function is called at line 1079. This function returns a Promise that resolves when `vid.onended` fires (line 1428). If `vid.onended` does not fire, the Promise never resolves, causing the `.then()` block at line 1087 to never execute. Consequently, `startRec()` is never called, leaving the mic inactive. The UI remains in the "RESPONDING" state, with `busy` set to `true` (line 1054), and the mic is disabled (lines 836 and 846).
- **BUG CONFIRMED:** Yes
- **SEVERITY:** CRITICAL
- **FIX:** Implement a fallback mechanism in `playVid()` to ensure the Promise resolves even if `vid.onended` does not fire. For example, use a timeout to resolve the Promise after a reasonable duration if `onended` hasn't fired.

```javascript
// Add this inside playVid() after setting vid.onended
setTimeout(() => {
  if (busy) {
    console.warn('[Satomi] Fallback timeout — resolving playVid Promise');
    vid.onended(); // Manually trigger onended logic
  }
}, 10000); // Adjust timeout duration as needed
```

### Q2 — iOS AUTOPLAY + BLOB URLS

- **ANALYSIS:** iOS Safari has strict autoplay policies, especially for blob URLs. Even if a video is muted initially (line 1455), it may not play if the autoplay policy is violated, leading to `onended` not firing. The code attempts to unmute the video on `canplay` (lines 1458-1462), but if the video never starts, `canplay` may not fire, and no error is thrown.
- **BUG CONFIRMED:** Yes
- **SEVERITY:** HIGH
- **FIX:** Ensure that the video is explicitly started with a user gesture if autoplay fails. Implement a tap-to-play overlay that prompts the user to start the video manually.

```javascript
// Modify showTapOverlay() to ensure user interaction starts the video
function showTapOverlay() {
  var ov = document.getElementById('tap-to-play');
  if (ov) {
    ov.style.display = 'flex';
    ov.onclick = function() {
      vid.play().then(() => {
        setStat('Speaking', '#6cff9f', false);
        ov.style.display = 'none';
      }).catch((e) => {
        console.warn('[Satomi] tap-to-play retry failed:', e);
        vid.style.opacity = '0';
        setStat('Ready', '#334', false);
      });
    };
  }
}
```

### Q3 — RACE BETWEEN .then() AND .finally()

- **ANALYSIS:** The `.finally()` block at line 1101 sets `busy` to `false`. If `.finally()` executes before `.then()`, the `setBusy(false)` in `.then()` becomes redundant. However, the `!busy` check at line 1088 would pass, allowing `startRec()` to be called. The `isRec` flag is set to `true` in `startRec()` (line 1508), so it should not affect the flow.
- **BUG CONFIRMED:** No
- **SEVERITY:** MEDIUM
- **FIX:** Ensure that `setBusy(false)` is called only once by moving it to a common function that both `.then()` and `.finally()` can call.

### Q4 — process() NEVER FIRES AFTER GREETING

- **ANALYSIS:** After `startRec()` is called, `recognition.onend` (line 1494) is responsible for calling `process()`. If `pending` is empty and `busy` is `true`, `process()` will not execute (line 1111). If `recognition` fires `onend` with an empty `pending` immediately after `start()`, it would result in no action.
- **BUG CONFIRMED:** Yes
- **SEVERITY:** HIGH
- **FIX:** Add a check in `recognition.onend` to handle cases where `pending` is empty and ensure `process()` is called with a fallback message or retry logic.

```javascript
recognition.onend = function() {
  setRec(false);
  if (!pending.trim() && !busy) {
    // Retry logic or fallback message
    setStat('Listening again...', '#66d9ff', false);
    startRec();
  } else if (pending.trim() && !busy) {
    process(pending);
    pending = '';
  }
};
```

### Q5 — RECOGNITION ONEND WITH EMPTY PENDING

- **ANALYSIS:** If `recognition.onend` fires with no final results, the current implementation does not restart the recognition or provide feedback. It silently does nothing unless `pending` is non-empty.
- **BUG CONFIRMED:** Yes
- **SEVERITY:** MEDIUM
- **FIX:** Implement a retry mechanism in `recognition.onend` to restart recognition if `pending` is empty.

### Q6 — BUSY FLAG DURING USER SPEECH

- **ANALYSIS:** The `busy` flag is set to `true` during `playIntent()` (line 1054) and reset to `false` in `.finally()` (line 1101). If the mic is activated after `busy` is set to `false`, there should be no issue. However, if `busy` remains `true` due to a Promise hang, `process()` will not execute (line 1111).
- **BUG CONFIRMED:** Yes
- **SEVERITY:** HIGH
- **FIX:** Ensure `busy` is consistently reset by using a centralized function to manage state transitions.

### Q7 — iOS MIC ACTIVATION AFTER VIDEO

- **ANALYSIS:** iOS requires a user gesture to start `SpeechRecognition`. The 400ms `setTimeout` (line 1087) may not suffice if it is not triggered by a user gesture. iOS may require a direct tap event to activate the mic.
- **BUG CONFIRMED:** Yes
- **SEVERITY:** HIGH
- **FIX:** Use a user gesture, such as a button tap, to start `SpeechRecognition`.

### Q8 — SAFETY TIMEOUT ADEQUACY

- **ANALYSIS:** The 30-second safety timeout (line 1419) is excessive for short videos. It should be based on the actual video duration to avoid unnecessary delays.
- **BUG CONFIRMED:** Yes
- **SEVERITY:** MEDIUM
- **FIX:** Adjust the safety timeout based on video duration.

```javascript
// Calculate timeout based on video duration
var safetyTimeoutDuration = Math.max(vid.duration * 2, 30) * 1000; // Double the video duration or 30s
setTimeout(() => {
  if (busy) {
    console.warn('[Satomi] Safety timeout — forcing mic unlock');
    setBusy(false);
    setOracleState('LISTENING');
  }
}, safetyTimeoutDuration);
```

### FINAL VERDICT

- **CRITICAL issues confirmed:** 1
- **Root cause of the "greeting plays but mic never activates" bug:** The `playVid()` Promise never resolves due to `vid.onended` not firing on iOS Safari, leaving the UI in a busy state.
- **Ordered fix list:**
  1. Implement a fallback mechanism in `playVid()` to resolve the Promise if `onended` doesn't fire.
  2. Use a user gesture to activate the microphone on iOS.
  3. Adjust the safety timeout based on video duration.
  4. Add retry logic in `recognition.onend` for empty `pending`.