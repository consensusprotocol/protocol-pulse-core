### AUDIT REPORT: ORACLE iOS VIDEO ONENDED RACE CONDITION

I have conducted a thorough review of the provided `oracle_live.html` file, focusing on the specific issue of the Satomi Oracle live interface failing to activate the microphone after the greeting video plays on iOS Safari. Below, I address each of the eight questions with detailed analysis, bug confirmation, severity assessment, and specific fixes. I conclude with a final verdict summarizing critical issues and prioritized fixes.

---

### Q1 — PLAYVID PROMISE HANG
**ANALYSIS**:  
In the `playIntent()` flow (starting at line 1050), the Promise chain is as follows:
- Line 1050: `playIntent('GREETING')` initiates a fetch to `/oracle/speak`.
- Line 1079: `fetchTO` resolves to `playVid(url)` which returns a Promise (line 1412).
- Line 1080-1095: `.then()` blocks wait for `playVid()` to resolve, which depends on `vid.onended` (line 1431) or `vid.onerror` (line 1441) to trigger the resolution of the Promise.
- Line 1096-1104: `.finally()` block sets `busy=false` and calls `pulseMic()`.

If `playVid()` never resolves on iOS Safari (due to `onended` not firing), the Promise chain stalls at line 1079. The `.then()` blocks (lines 1080-1095) including the critical `startRec()` call (line 1088) never execute. The `.finally()` block (line 1096) also never runs because the Promise is stuck in a pending state. The UI remains in the 'RESPONDING' state (set at line 1414 in `playVid()`), with `busy=true` (set at line 1051), `mic.disabled=true` (line 846 in `setOracleState('RESPONDING')`), and the video potentially stuck or looping silently. The user cannot interact with the mic, and the app appears frozen.

**BUG CONFIRMED**: Yes  
**SEVERITY**: CRITICAL  
**FIX**: Add a fallback mechanism in `playVid()` to ensure the Promise resolves even if `onended` fails to fire. Modify lines 1419-1426 to resolve the Promise explicitly after the safety timeout:
```javascript
var _safetyTimer = setTimeout(function(){
    if(busy){
        console.warn('[Satomi] Safety timeout — forcing mic unlock after 30s');
        vid.style.opacity='0'; // Ensure video is hidden
        vid.src=''; // Clear source to prevent looping
        setBusy(false);
        if(window._thinkTimer){clearInterval(window._thinkTimer);window._thinkTimer=null;}
        setOracleState('LISTENING');
        res(); // Explicitly resolve the Promise
    }
}, 30000);
```

---

### Q2 — iOS AUTOPLAY + BLOB URLS
**ANALYSIS**:  
iOS Safari has strict autoplay policies, especially for media with audio. At line 1455, the code mutes the video (`vid.muted=true`) before playing, and at line 1459-1462, it attempts to unmute on `canplay`. However, iOS Safari often blocks autoplay of blob URLs unless triggered by a direct user gesture. If the video fails to play, `onended` (line 1431) will not fire, and `onerror` (line 1441) may not trigger either if the failure is due to a policy restriction rather than a loading error. The code at line 1472-1476 detects autoplay failure and shows a tap-to-play overlay, but if the user does not tap, the Promise remains unresolved, stalling the chain as described in Q1.

**BUG CONFIRMED**: Yes  
**SEVERITY**: CRITICAL  
**FIX**: Enhance the tap-to-play overlay logic to force a state transition if the user does not interact within a timeout. Modify line 1474 to include a fallback:
```javascript
p.then(function(){}).catch(function(){
    showTapOverlay();
    // Fallback: If user doesn't tap within 10s, resolve anyway to prevent hang
    setTimeout(function(){
        if(busy && vid.paused){
            console.warn('[Satomi] Tap-to-play timeout — forcing state transition');
            vid.style.opacity='0';
            setBusy(false);
            setOracleState('LISTENING');
            res();
        }
    }, 10000);
});
```

---

### Q3 — RACE BETWEEN .then() AND .finally()
**ANALYSIS**:  
In `playIntent()`, the `.then()` block at line 1087 uses a 400ms `setTimeout` to call `startRec()`, while the `.finally()` block at line 1101 sets `busy=false`. JavaScript Promise chains guarantee that `.finally()` runs after all `.then()` blocks complete, so there is no race condition between them. However, if `playVid()` hangs (as in Q1), neither `.then()` nor `.finally()` executes. The issue with `busy` and `isRec` arises only if the safety timeout (line 1419) triggers, resolving the Promise, but the 400ms delay might still be pending. In this case, `busy=false` from `.finally()` (line 1101) could precede the `startRec()` call, but `isRec` would still be set correctly by `startRec()` (line 1507).

**BUG CONFIRMED**: No  
**SEVERITY**: N/A  
**FIX**: None required. The Promise chain order is correct, but the hang issue (Q1) must be addressed to ensure execution.

---

### Q4 — process() NEVER FIRES AFTER GREETING
**ANALYSIS**:  
After the greeting ends, `startRec()` is called (line 1088) which sets `isRec=true` and starts speech recognition (line 1509). The `process()` function (line 1111) checks if `text` is non-empty and `busy=false`. Speech recognition results are handled at line 1486-1493, updating `pending` with final results. The `recognition.onend` handler (line 1494) submits `pending` to `process()` after a 100ms delay (line 1500). If `busy=true` when `onend` fires (due to a lingering state from Q1), `process()` returns early at line 1111. Additionally, if recognition fails to capture any input (empty `pending`), nothing is processed (line 1500).

**BUG CONFIRMED**: Yes  
**SEVERITY**: HIGH  
**FIX**: Ensure `busy=false` before `startRec()` and handle empty `pending` gracefully. Modify line 1087-1090:
```javascript
setTimeout(function(){
    if(busy){
        console.warn('[Satomi] Busy state lingered — forcing idle');
        setBusy(false);
    }
    if(!isRec && mic){
        mic.disabled=false;
        startRec();
        setStat('Listening…','#6cff9f',false);
    }
},400);
```

---

### Q5 — RECOGNITION ONEND WITH EMPTY PENDING
**ANALYSIS**:  
At line 1494, `recognition.onend` checks `pending` for content to process (line 1500). If `pending` is empty (no final results captured), the code silently does nothing—no processing occurs, and there is no auto-restart logic. The UI remains in a listening state (`isRec=false` from line 1496), but the mic button does not restart recognition automatically, leaving the user to manually tap again.

**BUG CONFIRMED**: Yes  
**SEVERITY**: MEDIUM  
**FIX**: Add auto-restart logic if `pending` is empty. Modify line 1496-1501:
```javascript
recognition.onend=function(){
    setRec(false);
    // Auto-submit on silence — no tap required
    var _pend = pending;
    if(_pend.trim()&&!busy){setStat('Processing\u2026','#f4c46f',true);}
    setTimeout(function(){
        if(_pend.trim()&&!busy){process(_pend);pending='';}
        else if(!busy && !isRec){startRec();} // Auto-restart if no input
    }, 100);
};
```

---

### Q6 — BUSY FLAG DURING USER SPEECH
**ANALYSIS**:  
The `busy` flag is set to `true` at line 1051 in `playIntent()`, line 1114 in `process()`, and other places. It is cleared in `.finally()` blocks (line 1101, line 1400) or error handlers. If `playVid()` hangs (Q1), `busy` remains `true`, blocking `process()` at line 1111. Even with the safety timeout (line 1419), a timing window exists if the user speaks before the timeout clears `busy`. This window is exacerbated by the 400ms delay in `startRec()` (line 1087).

**BUG CONFIRMED**: Yes  
**SEVERITY**: HIGH  
**FIX**: Ensure `busy` is cleared before `startRec()`. See Q4 fix for line 1087 modification to force `busy=false`.

---

### Q7 — iOS MIC ACTIVATION AFTER VIDEO
**ANALYSIS**:  
iOS Safari requires a user gesture for `SpeechRecognition.start()` in many cases, especially if not directly tied to a tap event. The current code at line 1087 uses a 400ms `setTimeout` to call `startRec()`, which may fail silently on iOS due to lack of user interaction context. A tap event or explicit user gesture is often required post-video to activate the mic reliably.

**BUG CONFIRMED**: Yes  
**SEVERITY**: CRITICAL  
**FIX**: After video ends, prompt user to tap the mic rather than auto-starting. Modify line 1087-1090:
```javascript
setTimeout(function(){
    if(!busy && mic){
        mic.disabled=false;
        setStat('Tap mic to speak','#ff3b5f',false);
        mic.classList.add('idle-pulse');
    }
},400);
```

---

### Q8 — SAFETY TIMEOUT ADEQUACY
**ANALYSIS**:  
The 30-second safety timeout at line 1419 is too long for short videos (e.g., a 5-second greeting). The user waits unnecessarily long before the mic activates. A fixed timeout does not adapt to video duration, which could be queried via `vid.duration` after loading.

**BUG CONFIRMED**: Yes  
**SEVERITY**: MEDIUM  
**FIX**: Adjust timeout based on video duration with a fallback. Modify line 1419-1426:
```javascript
var _safetyTimer = setTimeout(function(){
    if(busy){
        console.warn('[Satomi] Safety timeout — forcing mic unlock');
        vid.style.opacity='0';
        vid.src='';
        setBusy(false);
        if(window._thinkTimer){clearInterval(window._thinkTimer);window._thinkTimer=null;}
        setOracleState('LISTENING');
        res();
    }
}, Math.min(30000, (vid.duration * 1000 + 2000) || 10000)); // Use duration if available, fallback to 10s max
```

---

### FINAL VERDICT
- **CRITICAL ISSUES CONFIRMED**: 3 (Q1: playVid hang, Q2: iOS autoplay, Q7: iOS mic activation)
- **ROOT CAUSE OF "GREETING PLAYS BUT MIC NEVER ACTIVATES"**: The primary root cause is the `playVid()` Promise hanging on iOS Safari due to `onended` not firing (Q1), compounded by autoplay restrictions (Q2) and lack of user gesture for mic activation (Q7). This stalls the Promise chain, preventing `startRec()` from executing and leaving `busy=true`.
- **ORDERED FIX LIST (MOST IMPACTFUL FIRST)**:
  1. **Q1 Fix**: Force `playVid()` Promise resolution on timeout (line 1419-1426) to prevent hangs.
  2. **Q2 Fix**: Add tap-to-play timeout fallback (line 1474) to handle autoplay blocks.
  3. **Q7 Fix**: Replace auto `startRec()` with user prompt (line 1087) for iOS mic activation.
  4. **Q4/Q6 Fix**: Ensure `busy=false` before mic activation (line 1087) to prevent `process()` early return.
  5. **Q5 Fix**: Add auto-restart for empty `pending` in `recognition.onend` (line 1496-1501).
  6. **Q8 Fix**: Adjust safety timeout based on video duration (line 1419) for better UX.

This audit identifies critical flaws in the Promise chain and iOS compatibility, with actionable fixes to ensure the mic activates reliably post-greeting. Implementing these changes in the specified order will resolve the core issue and improve overall robustness.