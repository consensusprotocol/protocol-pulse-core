# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: oracle-fix
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GROK — CYCLE 1 OUTPUT
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
After the greeting ends, `startRec()` is called (line 1088) which sets `isRec=true` and starts speech recognition (line 1509). The `process()` function (line 1111) checks if `t

## GPT4O — CYCLE 1 OUTPUT
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
- **FIX:** Use a user gesture, such as a button tap, t

## GEMINI — CYCLE 1 OUTPUT
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
    // INSIDE play

## CLAUDE'S CYCLE 1 CONSENSUS
# CONSENSUS REPORT — ORACLE-FIX — CYCLE 1
Generated: 2026-03-25 14:21
Models: grok, gpt4o, gemini

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Q1 — playVid Promise Hang | CRITICAL | CRITICAL | CRITICAL | **CRITICAL** |
| Q2 — iOS Autoplay + Blob URLs | HIGH | HIGH | CRITICAL | **HIGH** |
| Q3 — Race .then()/.finally() | MEDIUM (no bug, fragile) | MEDIUM (no bug) | PASS (no bug) | **LOW / No Bug** |
| Q4 — process() Never Fires After Greeting | HIGH (secondary) | HIGH | HIGH | **HIGH** |
| Q5 — Recognition onend Empty Pending | MEDIUM (implied) | MEDIUM | MEDIUM | **MEDIUM** |
| Q6 — Busy Flag During User Speech | HIGH (implied) | HIGH | HIGH | **HIGH** |
| Q7 — iOS Mic Activation After Video | CRITICAL (no setTimeout) | HIGH | HIGH | **HIGH** |
| Q8 — Safety Timeout Adequacy | HIGH | MEDIUM | N/A | **MEDIUM** |

---

## UNANIMOUS FINDINGS
*(All 3 models agree — implement unconditionally)*

---

### U1 — `playVid()` Promise Hangs Forever on iOS When `onended` Fails to Fire
**File:** `templates/oracle_live.html`
**Lines:** ~1413–1460 (`playVid()` function body)
**Agreement:** Gemini ✓ GPT-4o ✓ Grok ✓

**What it is:** The `playVid()` function returns a Promise that resolves *only* inside `vid.onended` or `vid.onerror`. On iOS Safari, `onended` frequently never fires for blob-URL video elements. The result: the Promise stays pending forever. `setBusy(false)` is never reached (it lives in `.finally()`), `startRec()` is never called (it lives in `.then()`), the UI is frozen in `RESPONDING` state with mic disabled, and the user cannot interact. The app is permanently hung.

**What to change:**
1. Add a `reject` parameter to the Promise constructor inside `playVid()`.
2. Modify the existing safety timeout to **both reset state AND reject/resolve the Promise** to un-hang the chain.
3. Ensure `clearTimeout(_safetyTimer)` is called inside every resolution path (`onended`, `onerror`) to prevent double-firing.

```javascript
// templates/oracle_live.html — inside playVid(), ~line 1413
function playVid(url){
  return new Promise(function(res, rej){
    setOracleState('RESPONDING');
    vid.loop = false;
    vid.src = url;
    vid.style.opacity = '1';
    if(window._matrixHide) window._matrixHide();

    var settled = false;
    function settle(resolveOrReject, value){
      if(settled) return;
      settled = true;
      clearTimeout(_safetyTimer);
      resolveOrReject(value);
    }

    var _safetyTimer = setTimeout(function(){
      if(!settled){
        console.warn('[Satomi] Safety timeout — forcing mic unlock');
        vid.style.opacity = '0';
        vid.src = '';
        if(window._thinkTimer){clearInterval(window._thinkTimer); window._thinkTimer=null;}
        setBusy(false);
        setOracleState('LISTENING');
        settle(rej, new Error('playVid safety timeout'));
      }
    }, 30000);

    vid.onended = function(){
      vid.style.opacity = '0';
      setTimeout(function(){ vid.src=''; }, 300);
  

---

## ORIGINAL CODE (same code as Cycle 1)
## THE CODE (every new and modified file)

### File: templates/oracle_live.html (2300 lines)
```
   1 | <!DOCTYPE html>
   2 | <html lang="en">
   3 | <head>
   4 | <meta charset="UTF-8">
   5 | <meta name="viewport" content="width=device-width,initial-scale=1.0,maximum-scale=1.0,user-scalable=no,viewport-fit=cover,interactive-widget=resizes-content">
   6 | <meta name="theme-color" content="#000">
   7 | <meta name="apple-mobile-web-app-capable" content="yes">
   8 | <meta name="apple-mobile-web-app-status-bar-style" content="black">
   9 | <meta http-equiv="Permissions-Policy" content="microphone=*, camera=*">
  10 | <title>Satomi · Protocol Pulse</title>
  11 | <link rel="preconnect" href="https://fonts.googleapis.com">
  12 | <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800;900&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  13 | <link rel="preload" href="/oracle/thinking" as="video" type="video/mp4">
  14 | <style>
  15 | *,*::before,*::after{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}
  16 | html,body{height:100%;width:100%;background:#000;overflow:hidden;font-family:'Inter',sans-serif;-webkit-font-smoothing:antialiased}
  17 | 
  18 | /* ─── KEYFRAMES ─────────────────────────────────────────── */
  19 | @keyframes orbit{to{transform:rotate(360deg)}}
  20 | @keyframes orbit-rev{to{transform:rotate(-360deg)}}
  21 | @keyframes breathe{0%,100%{opacity:.6;transform:scale(1)}50%{opacity:1;transform:scale(1.04)}}
  22 | @keyframes scan{0%{top:-4px}100%{top:100%}}
  23 | @keyframes live-blink{0%,100%{opacity:1}49%{opacity:1}50%,99%{opacity:.15}}
  24 | @keyframes fade-up{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:translateY(0)}}
  25 | @keyframes mic-pulse{0%{box-shadow:0 0 0 0 rgba(255,59,95,.6)}70%{box-shadow:0 0 0 22px rgba(255,59,95,0)}100%{box-shadow:0 0 0 0 rgba(255,59,95,0)}}
  26 | @keyframes mic-idle-pulse{0%,100%{box-shadow:0 0 0 0 rgba(255,59,95,0)}50%{box-shadow:0 0 0 14px rgba(255,59,95,.22),0 0 18px 4px rgba(255,59,95,.12)}}
  27 | @keyframes spin{to{transform:rotate(360deg)}}
  28 | @keyframes card-up{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
  29 | @keyframes hex-glow{0%,100%{filter:drop-shadow(0 0 8px rgba(255,59,95,.4))}50%{filter:drop-shadow(0 0 22px rgba(255,59,95,.9))}}
  30 | 
  31 | /* ─── ROOT ──────────────────────────────────────────────── */
  32 | #root{position:fixed;inset:0;background:#000;display:flex;align-items:center;justify-content:center;overflow:hidden}
  33 | 
  34 | /* ─── BACKGROUND GRID ───────────────────────────────────── */
  35 | #root::before{
  36 |   content:'';position:absolute;inset:0;
  37 |   background-image:linear-gradient(rgba(255,59,95,.04) 1px,transparent 1px),linear-gradient(90deg,rgba(255,59,95,.04) 1px,transparent 1px);
  38 |   background-size:40px 40px;
  39 |   mask-image:radial-gradient(ellipse 80% 80% at 50% 50%,black 40%,transparent 100%);
  40 |   pointer-events:none;
  41 | }
  42 | 
  43 | /* ═══════════════════════════════════════════════════════════
  44 |    GATE SCREEN
  45 | ═══════════════════════════════════════════════════════════ */
  46 | #gate{
  47 |   display:flex;flex-direction:column;align-items:center;
  48 |   gap:clamp(18px,4vw,28px);
  49 |   padding:clamp(24px,5vw,48px) clamp(24px,5vw,48px);
  50 |   width:100%;max-width:520px;
  51 |   transition:opacity .35s ease;
  52 | }
  53 | 
  54 | /* Satomi sigil */
  55 | .sigil-wrap{
  56 |   position:relative;
  57 |   width:clamp(140px,38vw,200px);
  58 |   height:clamp(140px,38vw,200px);
  59 |   flex-shrink:0;
  60 | }
  61 | /* Rotating rings */
  62 | .ring{
  63 |   position:absolute;inset:0;
  64 |   border-radius:50%;
  65 |   border:1px solid rgba(255,59,95,.25);
  66 | }
  67 | .ring-1{animation:orbit 12s linear infinite}
  68 | .ring-1::before{
  69 |   content:'';position:absolute;
  70 |   width:6px;height:6px;background:#ff3b5f;border-radius:50%;
  71 |   top:-3px;left:50%;transform:translateX(-50%);
  72 |   box-shadow:0 0 8px #ff3b5f;
  73 | }
  74 | .ring-2{
  75 |   inset:12%;border-color:rgba(255,180,50,.2);
  76 |   animation:orbit-rev 8s linear infinite;
  77 | }
  78 | .ring-2::before{
  79 |   content:'';position:absolute;
  80 |   width:4px;height:4px;background:#f8c15c;border-radius:50%;
  81 |   bottom:-2px;left:50%;transform:translateX(-50%);
  82 |   box-shadow:0 0 6px #f8c15c;
  83 | }
  84 | /* Avatar in center */
  85 | .sigil-avatar{
  86 |   position:absolute;
  87 |   inset:18%;
  88 |   border-radius:50%;
  89 |   overflow:hidden;
  90 |   background:radial-gradient(circle,#1a0608 0%,#050203 100%);
  91 |   border:1px solid rgba(255,59,95,.3);
  92 |   animation:breathe 3.5s ease-in-out infinite;
  93 | }
  94 | .sigil-avatar img{width:100%;height:100%;object-fit:cover;display:block;border-radius:50%}
  95 | .sigil-fallback{
  96 |   width:100%;height:100%;border-radius:50%;
  97 |   display:flex;align-items:center;justify-content:center;
  98 |   font-size:clamp(28px,8vw,44px);
  99 |   background:radial-gradient(circle,#2a0810 0%,#080205 100%);
 100 | }
 101 | /* Scan line */
 102 | .sigil-scan{
 103 |   position:absolute;inset:18%;border-radius:50%;overflow:hidden;pointer-events:none;
 104 | }
 105 | .sigil-scan::after{
 106 |   content:'';position:absolute;left:0;right:0;height:2px;
 107 |   background:linear-gradient(90deg,transparent,rgba(255,59,95,.6),transparent);
 108 |   animation:scan 2.5s ease-in-out infinite;
 109 | }
 110 | 
 111 | /* Wordmark */
 112 | .gate-brand{
 113 |   font-size:10px;font-weight:700;
 114 |   letter-spacing:.4em;color:rgba(255,59,95,.7);
 115 |   text-transform:uppercase;
 116 | }
 117 | 
 118 | /* Title */
 119 | .gate-title{
 120 |   font-size:clamp(32px,9vw,52px);
 121 |   font-weight:900;color:#fff;
 122 |   letter-spacing:-.03em;line-height:1;
 123 |   text-align:center;
 124 | }
 125 | .gate-title span{color:#ff3b5f}
 126 | 
 127 | /* Sub */
 128 | .gate-sub{
 129 |   font-size:clamp(13px,3.5vw,15px);
 130 |   color:#556;
 131 |   text-align:center;line-height:1.6;
 132 |   max-width:300px;
 133 |   font-weight:400;
 134 | }
 135 | 
 136 | /* ─── THE BUTTON ─────────────────────────────────────────── */
 137 | #gate-btn{
 138 |   position:relative;
 139 |   background:transparent;
 140 |   border:none;cursor:pointer;
 141 |   padding:0;
 142 |   width:clamp(200px,55vw,280px);
 143 |   -webkit-appearance:none;
 144 |   touch-action:manipulation;
 145 | }
 146 | #gate-btn:disabled{opacity:.4;cursor:not-allowed}
 147 | #gate-btn:active .btn-inner{transform:scale(.97)}
 148 | 
 149 | .btn-inner{
 150 |   position:relative;overflow:hidden;
 151 |   background:linear-gradient(135deg,#1a0508 0%,#0d0203 100%);
 152 |   border:1px solid rgba(255,59,95,.5);
 153 |   border-radius:4px;
 154 |   padding:clamp(14px,4vw,18px) clamp(20px,5vw,32px);
 155 |   transition:transform .1s,border-color .2s;
 156 |   display:flex;flex-direction:column;align-items:center;gap:6px;
 157 | }
 158 | #gate-btn:not(:disabled):hover .btn-inner{border-color:rgba(255,59,95,.9)}
 159 | 
 160 | /* Top label */
 161 | .btn-label{
 162 |   font-family:'JetBrains Mono',monospace;
 163 |   font-size:9px;letter-spacing:.35em;
 164 |   color:rgba(255,59,95,.6);text-transform:uppercase;
 165 | }
 166 | /* Main text */
 167 | .btn-text{
 168 |   font-size:clamp(13px,4vw,16px);font-weight:700;
 169 |   color:#fff;letter-spacing:.05em;text-transform:uppercase;
 170 |   display:flex;align-items:center;gap:10px;
 171 | }
 172 | .btn-mic-icon{
 173 |   width:16px;height:16px;flex-shrink:0;
 174 |   opacity:.9;
 175 | }
 176 | /* Corner accents */
 177 | .btn-inner::before,.btn-inner::after{
 178 |   content:'';position:absolute;width:8px;height:8px;
 179 |   border-color:rgba(255,59,95,.6);border-style:solid;
 180 | }
 181 | .btn-inner::before{top:4px;left:4px;border-width:1px 0 0 1px}
 182 | .btn-inner::after{bottom:4px;right:4px;border-width:0 1px 1px 0}
 183 | /* Glow sweep on hover */
 184 | .btn-sweep{
 185 |   position:absolute;inset:0;
 186 |   background:linear-gradient(105deg,transparent 40%,rgba(255,59,95,.06) 50%,transparent 60%);
 187 |   transform:translateX(-100%);
 188 |   transition:transform .5s ease;
 189 | }
 190 | #gate-btn:not(:disabled):hover .btn-sweep{transform:translateX(100%)}
 191 | 
 192 | /* Status line below btn */
 193 | #gate-status{
 194 |   font-family:'JetBrains Mono',monospace;
 195 |   font-size:11px;color:#334;letter-spacing:.08em;
 196 |   min-height:16px;text-align:center;
 197 | }
 198 | #gate-error{
 199 |   display:none;font-size:12px;color:#ff3b5f;
 200 |   text-align:center;line-height:1.5;max-width:280px;
 201 |   background:rgba(255,59,95,.06);border:1px solid rgba(255,59,95,.15);
 202 |   border-radius:4px;padding:8px 12px;
 203 | }
 204 | 
 205 | /* ═══════════════════════════════════════════════════════════
 206 |    LIVE STAGE
 207 | ═══════════════════════════════════════════════════════════ */
 208 | #stage{
 209 |   display:none;flex-direction:column;align-items:center;
 210 |   position:relative;
 211 |   width:100%;height:100%;
 212 |   padding:clamp(8px,2.5vw,14px) clamp(12px,3.5vw,20px) clamp(10px,3vw,16px);
 213 |   gap:clamp(6px,1.5vw,10px);
 214 |   overflow-y:auto;-webkit-overflow-scrolling:touch;
 215 |   animation:fade-up .4s ease;
 216 | }
 217 | 
 218 | /* Top bar */
 219 | .topbar{
 220 |   width:100%;display:flex;align-items:center;
 221 |   justify-content:space-between;flex-shrink:0;
 222 | }
 223 | /* Exit and minimize buttons */
 224 | .stage-controls{display:flex;align-items:center;gap:8px}
 225 | #minimize-btn,#exit-btn{
 226 |   width:28px;height:28px;border-radius:50%;
 227 |   background:transparent;border:1px solid #1e2235;
 228 |   cursor:pointer;display:flex;align-items:center;justify-content:center;
 229 |   transition:border-color .15s,background .15s;
 230 |   -webkit-appearance:none;touch-action:manipulation;flex-shrink:0;
 231 |   opacity:0.5;
 232 | }
 233 | #minimize-btn:hover,#exit-btn:hover{opacity:1;border-color:#556;background:#0f1117}
 234 | #exit-btn:hover{border-color:rgba(255,59,95,.5)}
 235 | 
 236 | /* ── FLOATING MINI MODE ─────────────────────────────────────────── */
 237 | @keyframes mini-in{from{opacity:0;transform:scale(.6) translateY(20px)}to{opacity:1;transform:scale(1) translateY(0)}}
 238 | @keyframes mini-pulse{0%,100%{box-shadow:0 0 0 0 rgba(255,59,95,.4)}70%{box-shadow:0 0 0 8px rgba(255,59,95,0)}}
 239 | 
 240 | #oracle-float{
 241 |   position:fixed;bottom:24px;right:24px;
 242 |   width:72px;height:72px;border-radius:50%;
 243 |   background:#0a0b0f;border:2px solid rgba(255,59,95,.6);
 244 |   cursor:pointer;z-index:9999;
 245 |   display:none;align-items:center;justify-content:center;
 246 |   animation:mini-in .3s ease, mini-pulse 2s ease-in-out infinite;
 247 |   box-shadow:0 4px 20px rgba(0,0,0,.6);
 248 |   overflow:hidden;transition:transform .15s;
 249 | }
 250 | #oracle-float:hover{transform:scale(1.08)}
 251 | #oracle-float:active{transform:scale(.95)}
 252 | #oracle-float img{width:100%;height:100%;object-fit:cover;border-radius:50%}
 253 | #oracle-float-fallback{font-size:28px}
 254 | /* Speaking ring on float */
 255 | #oracle-float.speaking{border-color:#6cff9f;animation:mini-pulse 0.8s ease-in-out infinite}
 256 | /* Tooltip */
 257 | #oracle-float::after{
 258 |   content:"Talk to Satomi";
 259 |   position:absolute;right:80px;
 260 |   background:#0f1117;border:1px solid #1e2235;border-radius:4px;
 261 |   padding:4px 8px;font-family:'JetBrains Mono',monospace;font-size:10px;
 262 |   color:#b8c2d9;white-space:nowrap;pointer-events:none;
 263 |   opacity:0;transition:opacity .2s;
 264 | }
 265 | #oracle-float:hover::after{opacity:1}
 266 | .topbar-brand{
 267 |   font-family:'JetBrains Mono',monospace;
 268 |   font-size:10px;font-weight:500;
 269 |   letter-spacing:.3em;color:rgba(255,59,95,.7);text-transform:uppercase;
 270 | }
 271 | .live-pill{
 272 |   display:flex;align-items:center;gap:5px;
 273 |   background:rgba(74,222,128,.06);
 274 |   border:1px solid rgba(74,222,128,.2);
 275 |   border-radius:20px;padding:3px 8px;
 276 | }
 277 | .live-dot{
 278 |   width:5px;height:5px;border-radius:50%;background:#4ade80;
 279 |   animation:live-blink 2s step-end infinite;
 280 | }
 281 | .live-text{
 282 |   font-family:'JetBrains Mono',monospace;
 283 |   font-size:9px;font-weight:500;color:#4ade80;letter-spacing:.15em;
 284 | }
 285 | 
 286 | /* Video */
 287 | .video-wrap{
 288 |   position:relative;
 289 |   width:100%;
 290 |   max-width:min(440px,calc(100vw - 24px));
 291 |   aspect-ratio:1/1;
 292 |   border-radius:8px;overflow:hidden;
 293 |   background: #050508;
 294 |   overflow: hidden;
 295 |   flex-shrink:0;
 296 |   min-height: min(440px, calc(100vw - 24px));
 297 | }
 298 | /* Corner brackets */
 299 | .video-wrap::before,.video-wrap::after{
 300 |   content:'';position:absolute;width:16px;height:16px;
 301 |   border-color:rgba(255,59,95,.4);border-style:solid;z-index:2;
 302 | }
 303 | .video-wrap::before{top:6px;left:6px;border-width:1px 0 0 1px}
 304 | .video-wrap::after{bottom:6px;right:6px;border-width:0 1px 1px 0}
 305 | 
 306 | #vid{width:100%;height:100%;object-fit:cover;object-position:center top;display:block}
 307 | /* Subtitle */
 308 | #subtitle{
 309 |   width:100%;
 310 |   font-family:'JetBrains Mono',monospace;
 311 |   font-size:clamp(11px,3vw,13px);color:#f8c15c;
 312 |   line-height:1.55;text-align:center;
 313 |   min-height:34px;
 314 |   opacity:0;transition:opacity .3s;
 315 |   display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;
 316 |   overflow:hidden;padding:0 4px;
 317 | }
 318 | #subtitle.on{opacity:1}
 319 | 
 320 | /* Status */
 321 | #stat{
 322 |   font-family:'JetBrains Mono',monospace;
 323 |   font-size:clamp(10px,2.8vw,12px);
 324 |   color:#334;display:flex;align-items:center;gap:6px;
 325 |   height:18px;transition:color .2s;flex-shrink:0;
 326 | }
 327 | .spin{width:12px;height:12px;border:1.5px solid currentColor;border-top-color:transparent;border-radius:50%;display:none;animation:spin .6s linear infinite;flex-shrink:0}
 328 | 
 329 | /* Transcript */
 330 | #tx{
 331 |   font-family:'JetBrains Mono',monospace;
 332 |   font-size:clamp(10px,2.8vw,11px);color:#445;font-style:italic;
 333 |   min-height:16px;text-align:center;
 334 |   opacity:0;transition:opacity .2s;
 335 |   width:100%;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;
 336 | }
 337 | #tx.on{opacity:1}
 338 | 
 339 | /* Mic */
 340 | .mic-area{display:flex;flex-direction:column;align-items:center;gap:7px;flex-shrink:0}
 341 | #mic{
 342 |   width:clamp(60px,15vw,72px);height:clamp(60px,15vw,72px);
 343 |   border-radius:50%;
 344 |   background:#0a0c12;
 345 |   border:1.5px solid #ff3b5f;
 346 |   cursor:pointer;
 347 |   display:flex;align-items:center;justify-content:center;
 348 |   transition:background .15s,transform .1s;
 349 |   -webkit-appearance:none;touch-action:manipulation;
 350 |   flex-shrink:0;
 351 | }
 352 | #mic:active:not(:disabled){transform:scale(.92)}
 353 | #mic:disabled{opacity:.2;cursor:not-allowed}
 354 | #mic.rec{background:#ff3b5f;animation:mic-pulse 1s ease-out infinite}
 355 | #mic.idle-pulse{border-color:#ff3b5f;border-width:2px;animation:mic-idle-pulse 1.8s ease-in-out 3}
 356 | .mic-hint{font-family:'JetBrains Mono',monospace;font-size:9px;color:#334;letter-spacing:.12em;text-transform:uppercase}
 357 | #cam-btn{
 358 |   width:42px;height:42px;border-radius:50%;background:#0a0c12;
 359 |   border:1.5px solid #334;cursor:pointer;
 360 |   display:flex;align-items:center;justify-content:center;
 361 |   transition:border-color .15s;-webkit-appearance:none;touch-action:manipulation;
 362 |   flex-shrink:0;
 363 | }
 364 | #cam-btn:hover{border-color:#f8c15c}
 365 | #cam-btn.active{border-color:#f8c15c;background:#1a1500}
 366 | #cam-input{display:none}
 367 | #vision-status{
 368 |   font-family:'JetBrains Mono',monospace;font-size:10px;color:#f8c15c;
 369 |   text-align:center;opacity:0;transition:opacity .3s;min-height:14px;
 370 | }
 371 | #vision-status.on{opacity:1}
 372 | 
 373 | /* Sovereignty cards */
 374 | #cards{display:none;grid-template-columns:1fr 1fr;gap:8px;width:100%;animation:card-up .35s ease;position:relative;z-index:0}
 375 | #cards.on{display:grid}
 376 | .card{
 377 |   background:#080a0f;
 378 |   border:1px solid #141824;
 379 |   border-radius:6px;
 380 |   padding:clamp(10px,2.5vw,13px);
 381 |   cursor:pointer;
 382 |   transition:border-color .15s,background .15s;
 383 |   display:flex;flex-direction:column;gap:5px;
 384 |   touch-action:manipulation;
 385 | }
 386 | .card:active{background:#100610;border-color:rgba(255,59,95,.5)}
 387 | .card-title{font-size:clamp(11px,3.2vw,13px);font-weight:600;color:#ccd;line-height:1.3}
 388 | .card-link{font-family:'JetBrains Mono',monospace;font-size:clamp(9px,2.5vw,10px);color:rgba(255,59,95,.7);text-decoration:none;letter-spacing:.03em}
 389 | 
 390 | /* ═══════════════════════════════════════════════════════════
 391 |    MOBILE — max-width 640px
 392 | ═══════════════════════════════════════════════════════════ */
 393 | /* ═══════════════════════════════════════════════════════════
 394 |    TABLET — max-width 768px
 395 | ═══════════════════════════════════════════════════════════ */
 396 | @media(max-width:768px){
 397 |   body{padding-top:48px}
 398 |   .video-wrap{
 399 |     max-width:100%;
 400 |     margin:0 auto;
 401 |   }
 402 |   #vid{
 403 |     width:100%;
 404 |     max-width:100%;
 405 |     display:block;
 406 |     margin:0 auto;
 407 |   }
 408 |   #cards{grid-template-columns:1fr 1fr}
 409 |   .card{min-height:48px}
 410 |   #mic{min-width:48px;min-height:48px}
 411 |   #cam-btn{min-width:48px;min-height:48px}
 412 |   #gate-btn{min-height:48px}
 413 |   #root{padding-bottom:80px}
 414 | }
 415 | 
 416 | @media(max-width:640px){
 417 |   body{position:fixed;width:100%;overflow:hidden}
 418 |   #root{position:relative;height:100dvh}
 419 |   /* Stage: full viewport, vertical stack, no overflow leak */
 420 |   #stage{
 421 |     height:100vh;height:100dvh;
 422 |     padding:8px 10px 0;
 423 |     gap:6px;
 424 |     overflow:hidden;
 425 |     display:none;flex-direction:column;
 426 |   }
 427 | 
 428 |   /* Topbar: compact for 375px screens */
 429 |   .topbar{
 430 |     padding:0;
 431 |     min-height:28px;
 432 |     flex-shrink:0;
 433 |   }
 434 |   .topbar-brand{font-size:9px;letter-spacing:.25em}
 435 |   .live-pill{padding:2px 6px}
 436 |   .live-text{font-size:8px}
 437 |   .stage-controls{gap:4px}
 438 |   #minimize-btn,#exit-btn{width:26px;height:26px}
 439 | 
 440 |   /* Video: constrain to 60vh max, centered */
 441 |   .video-wrap{
 442 |     max-height:60vh;
 443 |     max-width:calc(100vw - 20px);
 444 |     width:100%;
 445 |     aspect-ratio:1/1;
 446 |     margin:0 auto;
 447 |     flex-shrink:1;
 448 |     min-height:0;
 449 |   }
 450 |   #vid{
 451 |     width:100%;
 452 |     height:100%;
 453 |     max-width:340px;
 454 |     margin:0 auto;
 455 |     display:block;
 456 |     border-radius:8px;
 457 |     object-fit:cover;
 458 |   }
 459 | 
 460 |   /* Subtitle: tighter */
 461 |   #subtitle{
 462 |     font-size:11px;
 463 |     min-height:28px;
 464 |     padding:0 2px;
 465 |     flex-shrink:0;
 466 |   }
 467 | 
 468 |   /* Status + transcript: compact */
 469 |   #stat{font-size:10px;height:16px;flex-shrink:0}
 470 |   #tx{font-size:10px;min-height:14px;flex-shrink:0}
 471 | 
 472 |   /* Mic area + input controls: sticky to bottom, full width, tap-friendly */
 473 |   .mic-area{
 474 |     width:100%;
 475 |     flex-shrink:0;
 476 |     padding-bottom:env(safe-area-inset-bottom,8px);
 477 |     margin-top:auto;
 478 |   }
 479 |   #mic{
 480 |     width:60px;height:60px;
 481 |     min-width:48px;min-height:48px;
 482 |   }
 483 |   .mic-hint{font-size:9px}
 484 | 
 485 |   /* Camera button: 48px touch target */
 486 |   #cam-btn{
 487 |     width:48px;height:48px;
 488 |     min-width:48px;min-height:48px;
 489 |   }
 490 | 
 491 |   /* Vision status */
 492 |   #vision-status{font-size:9px;min-height:12px}
 493 | 
 494 |   /* Cards grid: 1 column on mobile */
 495 |   #cards{grid-template-columns:1fr}
 496 |   #cards.on{
 497 |     display:grid;
 498 |     max-height:30vh;
 499 |     overflow-y:auto;
 500 |     -webkit-overflow-scrolling:touch;
 501 |   }
 502 |   .card{
 503 |     padding:10px;
 504 |     min-height:48px;
 505 |     display:flex;flex-direction:row;align-items:center;
 506 |     gap:8px;
 507 |   }
 508 |   .card-title{font-size:13px}
 509 |   .card-link{font-size:10px}
 510 | 
 511 |   /* Gate: ensure it fits small screens */
 512 |   #gate{
 513 |     padding:20px 16px;
 514 |     gap:16px;
 515 |   }
 516 |   .sigil-wrap{width:130px;height:130px}
 517 |   .gate-title{font-size:32px}
 518 |   .gate-sub{font-size:13px;max-width:260px}
 519 |   #gate-btn{width:220px}
 520 |   .btn-inner{padding:14px 20px}
 521 |   #gate-status{font-size:10px}
 522 |   #gate-error{font-size:11px;max-width:260px}
 523 | 
 524 |   /* Float bubble: smaller on mobile */
 525 |   #oracle-float{
 526 |     width:56px;height:56px;
 527 |     bottom:16px;right:16px;
 528 |   }
 529 | }
 530 | 
 531 | /* ── STUDIO TREATMENT (oracle-live only) ─────────── */
 532 | .video-wrap {
 533 |   border: 2px solid rgba(220,38,38,0.4);
 534 |   box-shadow: 0 0 40px rgba(220,38,38,0.15);
 535 | }
 536 | #oracle-matrix { pointer-events: none; }
 537 | 
 538 | /* ── VISION TRANSCRIPT ─────────────────────────── */
 539 | .vision-entry {
 540 |   padding: 10px 14px;
 541 |   border-bottom: 1px solid rgba(255,255,255,.04);
 542 |   cursor: pointer;
 543 | }
 544 | .vision-entry:hover { background: rgba(255,255,255,.03); }
 545 | .vision-entry:last-child { border-bottom: none; }
 546 | .vision-entry-device {
 547 |   font-family: monospace;
 548 |   font-size: 10px;
 549 |   letter-spacing: .1em;
 550 |   color: rgba(255,59,95,.7);
 551 |   text-transform: uppercase;
 552 |   margin-bottom: 4px;
 553 | }
 554 | .vision-entry-step {
 555 |   font-size: 0.8rem;
 556 |   color: rgba(255,255,255,.7);
 557 |   line-height: 1.5;
 558 |   margin: 2px 0;
 559 | }
 560 | .vision-entry-time {
 561 |   font-family: monospace;
 562 |   font-size: 9px;
 563 |   color: rgba(255,255,255,.2);
 564 |   margin-top: 4px;
 565 | }
 566 | </style>
 567 | </head>
 568 | <body>
 569 | <div id="vision-security-overlay" style="display:none;position:fixed;inset:0;
 570 | z-index:99999;background:rgba(180,0,0,0.97);flex-direction:column;
 571 | align-items:center;justify-content:center;padding:32px;text-align:center;">
 572 |   <div style="font-size:64px;margin-bottom:16px;">⚠️</div>
 573 |   <div style="font-family:monospace;font-size:13px;letter-spacing:.12em;
 574 | color:rgba(255,255,255,.6);margin-bottom:8px;text-transform:uppercase;">
 575 | SECURITY ALERT</div>
 576 |   <div id="vision-security-msg" style="font-size:1.2rem;font-weight:700;
 577 | color:#fff;margin-bottom:32px;line-height:1.5;max-width:340px;"></div>
 578 |   <button id="vision-security-dismiss"
 579 |     style="background:#fff;color:#b40000;font-family:monospace;font-weight:800;
 580 | font-size:14px;letter-spacing:.1em;border:none;border-radius:8px;
 581 | padding:16px 32px;cursor:pointer;text-transform:uppercase;
 582 | min-height:56px;width:100%;max-width:320px;">
 583 |     ✓ GOT IT — COVER NOW
 584 |   </button>
 585 |   <div id="vision-recovery-panel" style="display:none;width:100%;
 586 | max-width:340px;margin-top:24px;">
 587 |     <div style="font-family:monospace;font-size:11px;letter-spacing:.12em;
 588 | color:rgba(255,255,255,.5);margin-bottom:12px;text-transform:uppercase;">
 589 | YOUR FUNDS MAY BE AT RISK — ACT NOW</div>
 590 |     <div id="vision-recovery-step-label" style="font-family:monospace;
 591 | font-size:11px;color:rgba(255,200,0,.8);letter-spacing:.1em;
 592 | margin-bottom:8px;text-transform:uppercase;">STEP 1 OF 3</div>
 593 |     <div id="vision-recovery-step-text" style="font-size:1rem;
 594 | font-weight:600;color:#fff;line-height:1.6;margin-bottom:24px;"></div>
 595 |     <button id="vision-recovery-next"
 596 |       style="background:rgba(255,255,255,.15);color:#fff;
 597 | font-family:monospace;font-weight:700;font-size:13px;
 598 | letter-spacing:.08em;border:2px solid rgba(255,255,255,.3);
 599 | border-radius:8px;padding:14px 24px;cursor:pointer;
 600 | text-transform:uppercase;min-height:52px;width:100%;">
 601 |       NEXT STEP →
 602 |     </button>
 603 |     <button id="vision-recovery-help"
 604 |       style="display:none;background:#fff;color:#b40000;
 605 | font-family:monospace;font-weight:800;font-size:13px;
 606 | letter-spacing:.08em;border:none;border-radius:8px;
 607 | padding:14px 24px;cursor:pointer;text-transform:uppercase;
 608 | min-height:52px;width:100%;margin-top:8px;">
 609 |       HELP ME SET UP NEW WALLET
 610 |     </button>
 611 |     <button id="vision-recovery-close"
 612 |       style="display:none;background:none;color:rgba(255,255,255,.4);
 613 | font-family:monospace;font-size:11px;letter-spacing:.08em;
 614 | border:none;padding:12px;cursor:pointer;text-transform:uppercase;
 615 | width:100%;margin-top:4px;">
 616 |       I UNDERSTAND THE RISK — CLOSE
 617 |     </button>
 618 |   </div>
 619 | </div>
 620 | <div id="mobile-nav-bar" style="display:none;position:fixed;top:0;left:0;right:0;z-index:9998;background:rgba(4,5,10,.95);padding:10px 16px;border-bottom:1px solid rgba(255,59,95,.15);align-items:center;gap:12px;">
 621 |   <button onclick="window.history.back()" style="background:none;border:1px solid rgba(255,255,255,.15);color:rgba(255,255,255,.6);padding:6px 14px;border-radius:6px;font-family:'JetBrains Mono',monospace;font-size:11px;cursor:pointer;letter-spacing:.08em;">&larr; BACK</button>
 622 |   <span style="font-family:'JetBrains Mono',monospace;font-size:10px;color:rgba(255,59,95,.8);letter-spacing:.15em;">ORACLE &mdash; PROTOCOL PULSE</span>
 623 | </div>
 624 | <div id="root">
 625 | 
 626 | <!-- ══ GATE ══ -->
 627 | <div id="gate">
 628 |   <div class="gate-brand">Protocol Pulse</div>
 629 | 
 630 |   <div class="sigil-wrap">
 631 |     <div class="ring ring-1"></div>
 632 |     <div class="ring ring-2"></div>
 633 |     <div class="sigil-avatar">
 634 |       <img src="/static/oracle_avatar.png" alt="Satomi"
 635 |            onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">
 636 |       <div class="sigil-fallback" style="display:none">⚡</div>
 637 |     </div>
 638 |     <div class="sigil-scan"></div>
 639 |   </div>
 640 | 
 641 |   <h1 class="gate-title">THE <span>SATOMI</span></h1>
 642 |   <p class="gate-sub">Sovereign Bitcoin intelligence.<br>Ask anything, in real time.</p>
 643 | 
 644 |   <button id="gate-btn" onclick="requestMic()">
 645 |     <div class="btn-sweep"></div>
 646 |     <div class="btn-inner">
 647 |       <div class="btn-label">Protocol Pulse Intelligence</div>
 648 |       <div class="btn-text">
 649 |         <svg class="btn-mic-icon" viewBox="0 0 24 24" fill="none">
 650 |           <rect x="9" y="2" width="6" height="12" rx="3" fill="#ff3b5f"/>
 651 |           <path d="M5 10a7 7 0 0014 0" stroke="#ff3b5f" stroke-width="1.5" stroke-linecap="round"/>
 652 |           <line x1="12" y1="19" x2="12" y2="22" stroke="#ff3b5f" stroke-width="1.5" stroke-linecap="round"/>
 653 |         </svg>
 654 |         Speak to Satomi
 655 |       </div>
 656 |     </div>
 657 |   </button>
 658 | 
 659 |   <div id="gate-status">— tap to activate —</div>
 660 |   <div id="gate-error"></div>
 661 |   <!-- P0: Text input fallback when mic is unavailable -->
 662 |   <div id="text-input-fallback" style="display:none;width:100%;max-width:320px;margin-top:12px;">
 663 |     <div style="display:flex;gap:8px;align-items:center;">
 664 |       <input type="text" id="text-input-field" placeholder="Type your question..."
 665 |         style="flex:1;background:#0a0c12;border:1px solid rgba(255,59,95,.4);border-radius:4px;
 666 |         padding:12px 14px;color:#fff;font-family:'JetBrains Mono',monospace;font-size:13px;
 667 |         outline:none;" onkeydown="if(event.key==='Enter')submitTextInput()">
 668 |       <button onclick="submitTextInput()"
 669 |         style="background:rgba(255,59,95,.15);border:1px solid rgba(255,59,95,.5);
 670 |         border-radius:4px;padding:12px 16px;color:#ff3b5f;font-family:'JetBrains Mono',monospace;
 671 |         font-size:12px;font-weight:600;cursor:pointer;white-space:nowrap;letter-spacing:.05em;">SEND</button>
 672 |     </div>
 673 |   </div>
 674 | </div>
 675 | 
 676 | <!-- ══ LIVE STAGE ══ -->
 677 | <div id="stage">
 678 | 
 679 |   <div class="topbar">
 680 |     <span class="topbar-brand">Satomi</span>
 681 |     <div class="live-pill"><div class="live-dot"></div><span class="live-text">LIVE</span></div>
 682 |     <a href="/" style="margin-left:auto;color:rgba(255,255,255,0.3);font-size:22px;text-decoration:none;padding:4px 10px;line-height:1;transition:color 0.2s;" onmouseover="this.style.color='rgba(255,255,255,0.8)'" onmouseout="this.style.color='rgba(255,255,255,0.3)'" aria-label="Exit Satomi" title="Go to homepage">&times;</a>
 683 |   </div>
 684 | 
 685 |   <canvas id="bg-canvas" style="position:absolute;top:0;left:0;width:100%;height:100%;z-index:0;pointer-events:none;will-change:transform;"></canvas>
 686 | 
 687 |   <div class="video-wrap" style="position:relative;z-index:1;">
 688 |     <!-- P0-1: Static avatar always visible behind video — never black screen -->
 689 |     <img id="avatar-idle" src="/static/oracle_avatar.png" alt="Satomi"
 690 |          style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;z-index:0;border-radius:8px;"
 691 |          onerror="this.style.background='radial-gradient(circle,#1a0608,#050203)'">
 692 |     <canvas id="oracle-matrix" style="position:absolute;inset:0;width:100%;height:100%;z-index:1;opacity:0.35;transition:opacity 0.5s;"></canvas>
 693 |     <video id="vid" playsinline webkit-playsinline x-webkit-airplay="allow" preload="auto" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:0;z-index:2;"></video>
 694 |     <!-- P0: Tap-to-play overlay for iOS Safari autoplay restrictions -->
 695 |     <div id="tap-to-play" style="display:none;position:absolute;inset:0;z-index:10;background:rgba(0,0,0,.55);
 696 |       border-radius:8px;cursor:pointer;align-items:center;justify-content:center;flex-direction:column;gap:8px;"
 697 |       onclick="dismissTapOverlay()">
 698 |       <svg width="48" height="48" viewBox="0 0 24 24" fill="none">
 699 |         <circle cx="12" cy="12" r="11" stroke="rgba(255,59,95,.7)" stroke-width="1.5"/>
 700 |         <polygon points="10,7 10,17 18,12" fill="#ff3b5f"/>
 701 |       </svg>
 702 |       <span style="font-family:'JetBrains Mono',monospace;font-size:10px;letter-spacing:.12em;color:rgba(255,255,255,.8);text-transform:uppercase;">Tap to Play</span>
 703 |     </div>
 704 |   </div>
 705 | 
 706 |   <div id="subtitle"></div>
 707 |   <div id="oracle-action-card" style="display:none;margin-top:12px;max-width:min(440px,calc(100vw - 24px));width:100%;"></div>
 708 | 
 709 |   <div id="stat">
 710 |     <span class="spin" id="spin"></span>
 711 |     <span id="stat-text">Ready</span>
 712 |   </div>
 713 | 
 714 |   <div id="tx"></div>
 715 | 
 716 |   <div class="mic-area">
 717 |     <button id="mic" disabled onclick="toggleMic()">
 718 |       <svg id="i-mic" width="24" height="24" viewBox="0 0 24 24" fill="none">
 719 |         <rect x="9" y="2" width="6" height="12" rx="3" fill="#ff3b5f"/>
 720 |         <path d="M5 10a7 7 0 0014 0" stroke="#ff3b5f" stroke-width="1.5" stroke-linecap="round"/>
 721 |         <line x1="12" y1="19" x2="12" y2="22" stroke="#ff3b5f" stroke-width="1.5" stroke-linecap="round"/>
 722 |         <line x1="9" y1="22" x2="15" y2="22" stroke="#ff3b5f" stroke-width="1.5" stroke-linecap="round"/>
 723 |       </svg>
 724 |       <svg id="i-stop" width="24" height="24" viewBox="0 0 24 24" fill="none" style="display:none">
 725 |         <rect x="6" y="6" width="12" height="12" rx="2" fill="#fff"/>
 726 |       </svg>
 727 |     </button>
 728 |     <span class="mic-hint" id="mic-hint">tap to speak</span>
 729 |   </div>
 730 |   <!-- P0: Stage text input — shown when mic is unavailable or as alternative -->
 731 |   <div id="stage-text-input" style="display:none;width:100%;max-width:min(440px,calc(100vw - 24px));margin-top:4px;">
 732 |     <div style="display:flex;gap:6px;align-items:center;">
 733 |       <input type="text" id="stage-text-field" placeholder="Type your question..."
 734 |         style="flex:1;background:#080a0f;border:1px solid #1e2235;border-radius:4px;
 735 |         padding:10px 12px;color:#fff;font-family:'JetBrains Mono',monospace;font-size:12px;
 736 |         outline:none;transition:border-color .15s;" onfocus="this.style.borderColor='rgba(255,59,95,.5)'" onblur="this.style.borderColor='#1e2235'" onkeydown="if(event.key==='Enter')stageTextSubmit()">
 737 |       <button onclick="stageTextSubmit()"
 738 |         style="background:#0a0c12;border:1px solid rgba(255,59,95,.4);border-radius:4px;
 739 |         padding:10px 14px;color:#ff3b5f;font-family:'JetBrains Mono',monospace;font-size:11px;
 740 |         font-weight:600;cursor:pointer;letter-spacing:.05em;">SEND</button>
 741 |     </div>
 742 |   </div>
 743 | 
 744 |   <!-- Vision status + Camera button -->
 745 |   <div id="vision-status"></div>
 746 |   <div style="display:flex;align-items:center;gap:10px;justify-content:center;margin-top:4px">
 747 |     <button id="cam-btn" onclick="triggerCamera()" title="Show Satomi your screen — she will guide you step by step">
 748 |       <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
 749 |         <path d="M23 19a2 2 0 01-2 2H3a2 2 0 01-2-2V8a2 2 0 012-2h4l2-3h6l2 3h4a2 2 0 012 2z" stroke="#556" stroke-width="1.5" stroke-linecap="round"/>
 750 |         <circle cx="12" cy="13" r="4" stroke="#556" stroke-width="1.5"/>
 751 |       </svg>
 752 |     </button>
 753 |     <span id="cam-btn-label" style="font-family:'JetBrains Mono',monospace;font-size:9px;color:#334;letter-spacing:.08em">ANALYZE HARDWARE</span>
 754 |   </div>
 755 |   <div id="vision-transcript-panel" style="display:none;
 756 |   width:100%;max-width:min(440px,calc(100vw - 24px));
 757 |   margin:12px auto 0;background:rgba(6,7,14,.9);
 758 |   border:1px solid rgba(255,59,95,.15);border-radius:8px;
 759 |   overflow:hidden;">
 760 |     <div style="display:flex;align-items:center;justify-content:space-between;
 761 |   padding:10px 14px;border-bottom:1px solid rgba(255,255,255,.06);">
 762 |       <span style="font-family:monospace;font-size:10px;letter-spacing:.12em;
 763 |   color:rgba(255,59,95,.8);text-transform:uppercase;">SESSION LOG</span>
 764 |       <button id="vision-transcript-clear"
 765 |         style="background:none;border:none;color:rgba(255,255,255,.3);
 766 |   font-family:monospace;font-size:9px;letter-spacing:.08em;
 767 |   cursor:pointer;text-transform:uppercase;padding:2px 6px;">
 768 |         CLEAR
 769 |       </button>
 770 |     </div>
 771 |     <div id="vision-transcript-entries" style="max-height:280px;
 772 |   overflow-y:auto;padding:8px 0;"></div>
 773 |   </div>
 774 | 
 775 |   <input type="file" id="cam-input" accept="image/*" capture="environment" onchange="handleVisionUpload(event)">
 776 | 
 777 |   <div id="cards">
 778 |     <div class="card" onclick="si('SOVEREIGNTY_COLD_WALLET')">
 779 |       <div class="card-title">&#128272; Self-Custody</div>
 780 |       <a class="card-link" href="https://coldcard.com" target="_blank" rel="noopener" onclick="event.stopPropagation()">coldcard.com &#8594;</a>
 781 |     </div>
 782 |     <div class="card" onclick="si('SOVEREIGNTY_NODE')">
 783 |       <div class="card-title">&#9889; Run a Node</div>
 784 |       <a class="card-link" href="https://getumbrel.com" target="_blank" rel="noopener" onclick="event.stopPropagation()">getumbrel.com &#8594;</a>
 785 |     </div>
 786 |     <div class="card" onclick="si('SOVEREIGNTY_BITAXE')">
 787 |       <div class="card-title">&#9935; Solo Mining</div>
 788 |       <a class="card-link" href="https://curatedmining.com" target="_blank" rel="noopener" onclick="event.stopPropagation()">curatedmining.com &#8594;</a>
 789 |     </div>
 790 |     <div class="card" onclick="si('SOVEREIGNTY_LIFE_INSURANCE')">
 791 |       <div class="card-title">&#128737; BTC Insurance</div>
 792 |       <a class="card-link" href="https://application.meanwhile.bm/start?referralCode=KKM73K" target="_blank" rel="noopener" onclick="event.stopPropagation()">meanwhile.bm &#8594;</a>
 793 |     </div>
 794 |   </div>
 795 | 
 796 | </div><!-- /stage -->
 797 | </div><!-- /root -->
 798 | 
 799 | <script>
 800 | 'use strict';
 801 | /* ── iOS zoom prevention ── */
 802 | document.addEventListener('gesturestart',function(e){e.preventDefault();},{passive:false});
 803 | document.addEventListener('touchmove',function(e){if(e.touches.length>1)e.preventDefault();},{passive:false});
 804 | var A='https://avatar.protocolpulse.io';
 805 | var S={
 806 |   GREETING:"Hey. I'm Satomi — your Protocol Pulse intelligence anchor. On-chain, macro, geopolitical. What can I help you with?",
 807 |   SOVEREIGNTY_INTRO:"Your sovereignty score is a snapshot of how free you actually are — how much of your financial life you've pulled out of legacy systems.",
 808 |   SOVEREIGNTY_ASSESSMENT:"Four pillars: self-custody of your Bitcoin, your own node, private comms, and no KYC on your income. Where are you today?",
 809 |   SOVEREIGNTY_COLD_WALLET:"If your Bitcoin is on an exchange, it's not yours — it's an IOU. A hardware wallet fixes that. I can walk you through it.",
 810 |   SOVEREIGNTY_NODE:"Running your own node means you verify your own transactions. You don't trust, you verify. Umbrel on a Pi is the easiest path.",
 811 |   SOVEREIGNTY_BITAXE:"Bitaxe is a solo miner you can run at home. A Bitcoin lottery ticket. Curated Mining also does white-glove setup.",
 812 |   SOVEREIGNTY_LIFE_INSURANCE:"If you die with Bitcoin in cold storage and nobody knows the seed phrase, it's gone. Meanwhile offers life insurance that actually understands Bitcoin.",
 813 |   SOVEREIGNTY_RESIDENCY:"Digital residency through Palau via RNS.ID gives you a second legal identity outside your home country. Real tax and privacy implications.",
 814 |   DAILY_BRIEF_INTRO:"Here's what's moving in Bitcoin right now. Pulling the latest from our intelligence layer...",
 815 |   DAILY_BRIEF_LIVE:"Here's today's Bitcoin intelligence brief.",
 816 |   UNKNOWN_QUESTION:"I'm researching that now. One moment.",
 817 |   GOODBYE:"Stack sats, verify everything, and come back anytime."
 818 | };
 819 | 
 820 | var busy=false,isRec=false,pending='',objURL=null,recognition=null;
 821 | var _greeted=false;
 822 | 
 823 | /* ── ORACLE STATE MACHINE ──
 824 |    States: WELCOME → LISTENING → PROCESSING → RESPONDING → LISTENING
 825 |    Every state shows the avatar face (never black screen).
 826 |    LISTENING: mic active, avatar static idle visible, status "Ready"
 827 |    PROCESSING: mic off, spinner, avatar idle visible
 828 |    RESPONDING: video playing over idle bg, mic off
 829 | */
 830 | var ORACLE_STATE = 'IDLE'; /* IDLE, WELCOME, LISTENING, PROCESSING, RESPONDING */
 831 | function setOracleState(state){
 832 |   ORACLE_STATE = state;
 833 |   console.log('[Satomi] State →', state);
 834 |   switch(state){
 835 |     case 'LISTENING':
 836 |       mic.disabled=false;
 837 |       setStat('Ready','#334',false);
 838 |       /* Ensure avatar idle is visible (video-wrap bg shows through when vid is transparent) */
 839 |       vid.style.opacity='0';
 840 |       break;
 841 |     case 'PROCESSING':
 842 |       mic.disabled=true;
 843 |       if(isRec) stopRec();
 844 |       break;
 845 |     case 'RESPONDING':
 846 |       mic.disabled=true;
 847 |       if(isRec) stopRec();
 848 |       break;
 849 |     case 'WELCOME':
 850 |       mic.disabled=true;
 851 |       break;
 852 |   }
 853 | }
 854 | 
 855 | var VISION_SPONSOR_MAP = {
 856 |   'trezor':   { category:'amazon', title:'Trezor Hardware Wallet', id:'vision_trezor',
 857 |     description:'The original Bitcoin hardware wallet. Battle-tested since 2014.',
 858 |     url:'https://amzn.to/trezor', cta:'View on Amazon' },
 859 |   'coldcard': { category:'affiliate', title:'Coldcard Mk4', id:'vision_coldcard',
 860 |     description:'The most secure Bitcoin signing device. Air-gapped by default.',
 861 |     url:'https://coldcard.com', cta:'Get Coldcard' },
 862 |   'ledger':   { category:'amazon', title:'Ledger Hardware Wallet', id:'vision_ledger',
 863 |     description:'Secure your Bitcoin with industry-leading hardware security.',
 864 |     url:'https://amzn.to/ledger', cta:'View on Amazon' },
 865 |   'bitaxe':   { category:'affiliate', title:'BitAxe Solo Miner', id:'vision_bitaxe',
 866 |     description:'Open-source Bitcoin miner. Stack sats from your home.',
 867 |     url:'https://bitaxe.org', cta:'Get BitAxe' },
 868 |   'umbrel':   { category:'affiliate', title:'Umbrel Home Server', id:'vision_umbrel',
 869 |     description:'Run your own Bitcoin node. Your keys, your coins.',
 870 |     url:'https://umbrel.com', cta:'Run Umbrel' },
 871 |   'start9':   { category:'affiliate', title:'Start9 Embassy', id:'vision_start9',
 872 |     description:'Sovereign computing for the sovereign individual.',
 873 |     url:'https://start9.com', cta:'Get Embassy' },
 874 |   'seedsigner':{ category:'affiliate', title:'SeedSigner', id:'vision_seedsigner',
 875 |     description:'Air-gapped signing device. Build your own or buy assembled.',
 876 |     url:'https://seedsigner.com', cta:'Learn More' },
 877 |   'passport': { category:'affiliate', title:'Foundation Passport', id:'vision_passport',
 878 |     description:'Open-source, air-gapped Bitcoin hardware wallet.',
 879 |     url:'https://foundationdevices.com', cta:'Get Passport' },
 880 |   'jade':     { category:'affiliate', title:'Blockstream Jade', id:'vision_jade',
 881 |     description:'Open-source hardware wallet with air-gapped signing.',
 882 |     url:'https://store.blockstream.com', cta:'Get Jade' }
 883 | };
 884 | 
 885 | function pulseMic(){
 886 |   if(!mic||mic.disabled||isRec)return;
 887 |   mic.classList.remove('idle-pulse');
 888 |   void mic.offsetWidth;
 889 |   mic.classList.add('idle-pulse');
 890 |   setStat('Tap mic to respond','#ff3b5f',false);
 891 |   setTimeout(function(){mic.classList.remove('idle-pulse');setStat('Ready','#334',false);},6000);
 892 | }
 893 | 
 894 | // ── VISITOR FINGERPRINT ───────────────────────────────────
 895 | // Generates a stable browser fingerprint — no cookies, no login
 896 | // Used server-side to recognize returning visitors
 897 | (function() {
 898 |   try {
 899 |     var fp = '';
 900 |     // Canvas fingerprint
 901 |     var canvas = document.createElement('canvas');
 902 |     var ctx = canvas.getContext('2d');
 903 |     ctx.textBaseline = 'top';
 904 |     ctx.font = '14px Arial';
 905 |     ctx.fillText('Satomi fp', 2, 2);
 906 |     fp += canvas.toDataURL().slice(-20);
 907 |     // Screen + timezone
 908 |     fp += screen.width + 'x' + screen.height + Intl.DateTimeFormat().resolvedOptions().timeZone;
 909 |     // Hash it (simple djb2)
 910 |     var hash = 5381;
 911 |     for (var i = 0; i < fp.length; i++) {
 912 |       hash = ((hash << 5) + hash) + fp.charCodeAt(i);
 913 |       hash = hash & hash; // 32-bit int
 914 |     }
 915 |     window._visitorToken = Math.abs(hash).toString(36);
 916 |   } catch(e) {
 917 |     window._visitorToken = 'anon';
 918 |   }
 919 | })();
 920 | 
 921 | // Read session_id and page context from URL params (injected by widget)
 922 | var _urlParams = new URLSearchParams(window.location.search);
 923 | var SESSION_ID = _urlParams.get('session_id') || ('sess_'+Date.now()+'_'+Math.random().toString(36).slice(2,8));
 924 | window.ORACLE_FINGERPRINT_MATCH = false;
 925 | var PAGE_CONTEXT = {
 926 |   type: _urlParams.get('page_type') || 'general',
 927 |   path: _urlParams.get('page_path') || window.location.pathname,
 928 |   content: null,
 929 |   url: document.referrer || window.location.href,
 930 | };
 931 | 
 932 | // Receive richer context from parent widget via postMessage
 933 | window.addEventListener('message', function(e) {
 934 |   if (!e.data || typeof e.data !== 'object') return;
 935 |   var d = e.data;
 936 |   if (d.type === 'oracle:context') {
 937 |     // Parent widget sent full page context
 938 |     if (d.sessionId) SESSION_ID = d.sessionId;
 939 |     if (d.pageContext) PAGE_CONTEXT = d.pageContext;
 940 |   }
 941 | });
 942 | 
 943 | // Tell parent we want context (in case we loaded before message was sent)
 944 | setTimeout(function(){
 945 |   try{ if(window.parent!==window) window.parent.postMessage({type:'oracle:context_request'},'*'); }catch(e){}
 946 | },300);
 947 | 
 948 | /* DOM */
 949 | var gate=document.getElementById('gate');
 950 | var stage=document.getElementById('stage');
 951 | var gBtn=document.getElementById('gate-btn');
 952 | var gStatus=document.getElementById('gate-status');
 953 | var gErr=document.getElementById('gate-error');
 954 | var vid=document.getElementById('vid');
 955 | var sub=document.getElementById('subtitle');
 956 | var statEl=document.getElementById('stat-text');
 957 | var spinEl=document.getElementById('spin');
 958 | var txEl=document.getElementById('tx');
 959 | var mic=document.getElementById('mic');
 960 | var micHint=document.getElementById('mic-hint');
 961 | var iMic=document.getElementById('i-mic');
 962 | var iStop=document.getElementById('i-stop');
 963 | var cards=document.getElementById('cards');
 964 | 
 965 | /* ── MIC REQUEST ── */
 966 | function requestMic(){
 967 |   gBtn.disabled=true;
 968 |   gStatus.textContent='Requesting microphone...';
 969 |   gErr.style.display='none';
 970 | 
 971 |   /* CRITICAL: unlock audio context immediately on this user gesture */
 972 |   try{
 973 |     var _unlockAc=new(window.AudioContext||window.webkitAudioContext)();
 974 |     var _unlockBuf=_unlockAc.createBuffer(1,1,22050);
 975 |     var _unlockSrc=_unlockAc.createBufferSource();
 976 |     _unlockSrc.buffer=_unlockBuf;_unlockSrc.connect(_unlockAc.destination);_unlockSrc.start(0);
 977 |     setTimeout(function(){try{_unlockAc.close();}catch(e){}},300);
 978 |   }catch(e){}
 979 | 
 980 |   try{
 981 |     var ac=new(window.AudioContext||window.webkitAudioContext)();
 982 |     var buf=ac.createBuffer(1,1,22050);
 983 |     var src=ac.createBufferSource();
 984 |     src.buffer=buf;src.connect(ac.destination);src.start(0);
 985 |     setTimeout(function(){try{ac.close();}catch(e){}},500);
 986 |   }catch(e){}
 987 | 
 988 |   /* Also "unlock" video element immediately */
 989 |   vid.muted=true;
 990 |   vid.play().catch(function(){});
 991 | 
 992 |   /* Pre-unlock Audio element for PATH B (chat responses) */
 993 |   window._audioUnlocked = new Audio();
 994 |   window._audioUnlocked.src = 'data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAESsAABErAAABAAgAZGF0YQIAAAABAA==';
 995 |   window._audioUnlocked.volume = 0.001;
 996 |   window._audioUnlocked.play().catch(function(){});
 997 | 
 998 |   window._chatAudioPlaying = false;
 999 | 
1000 |   navigator.mediaDevices.getUserMedia({audio:true,video:false})
1001 |     .then(function(stream){
1002 |       stream.getTracks().forEach(function(t){t.stop();}); /* don't need stream, just the gesture */
1003 |       gStatus.textContent='';
1004 |       go();
1005 |     })
1006 |     .catch(function(err){
1007 |       console.warn('[Satomi mic error]', err);
1008 |       gBtn.disabled=false;
1009 |       gStatus.textContent='';
1010 |       gErr.style.display='block';
1011 |       var name = err && err.name ? err.name : '';
1012 |       var msg='';
1013 |       if(name === 'NotAllowedError' || name === 'PermissionDeniedError'){
1014 |         msg='Microphone access denied. Allow mic in your browser settings, then retry.';
1015 |       } else if(name === 'NotReadableError' || name === 'TrackStartError'){
1016 |         msg='Microphone busy. Close other apps using the mic.';
1017 |       } else if(name === 'NotFoundError'){
1018 |         msg='No microphone detected.';
1019 |       } else {
1020 |         msg='Microphone unavailable'+(name?' ('+name+')':'.')+'.';
1021 |       }
1022 |       /* P0: Styled error + text fallback — demo never stops */
1023 |       gErr.innerHTML='<div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;letter-spacing:.1em;color:rgba(255,59,95,.7);text-transform:uppercase;margin-bottom:6px;">MIC UNAVAILABLE</div>'
1024 |         +'<div style="font-size:12px;color:rgba(255,255,255,.7);margin-bottom:12px;line-height:1.5;">'+msg+'</div>'
1025 |         +'<div style="display:flex;flex-direction:column;gap:8px;">'
1026 |         +'<button onclick="requestMic()" style="background:rgba(255,59,95,.1);border:1px solid rgba(255,59,95,.3);color:#ff3b5f;font-family:\'JetBrains Mono\',monospace;font-size:11px;letter-spacing:.05em;padding:10px 16px;border-radius:4px;cursor:pointer;font-weight:600;">RETRY MIC ACCESS</button>'
1027 |         +'<button onclick="goTextMode()" style="background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.15);color:#fff;font-family:\'JetBrains Mono\',monospace;font-size:11px;letter-spacing:.05em;padding:10px 16px;border-radius:4px;cursor:pointer;font-weight:600;">CONTINUE WITH TEXT INPUT</button>'
1028 |         +'</div>';
1029 |     });
1030 | }
1031 | 
1032 | /* ── TRANSITION ── */
1033 | function go(){
1034 |   gate.style.opacity='0';
1035 |   setTimeout(function(){
1036 |     gate.style.display='none';
1037 |     stage.style.display='flex';
1038 |     stage.style.opacity='0';
1039 |     setTimeout(function(){
1040 |       stage.style.transition='opacity .45s';
1041 |       stage.style.opacity='1';
1042 |       initSR();
1043 |       setOracleState('WELCOME');
1044 |       playIntent('GREETING');
1045 |     },30);
1046 |   },350);
1047 | }
1048 | 
1049 | /* ── PLAY CACHED INTENT ── */
1050 | function playIntent(intent){
1051 |   if(busy&&intent!=='GREETING')return;
1052 |   if(intent.indexOf('DAILY_BRIEF')===0&&window._briefFetched)return;
1053 |   setBusy(true);
1054 |   setStat('Satomi loading\u2026','#f4c46f',true);
1055 |   // Show thinking loop during intent loading (never dark screen)
1056 |   try{vid.muted=true;vid.loop=true;vid.src=A+'/oracle/thinking';vid.style.opacity='1';vid.play().catch(function(){vid.style.opacity='0';});}catch(e){}
1057 |   // Progress messages so user knows it's working, not broken
1058 |   var _loadMsgs = ['Initializing\u2026','Rendering response\u2026','Almost ready\u2026'];
1059 |   var _loadIdx = 0;
1060 |   var _loadTimer = setInterval(function(){
1061 |     _loadIdx++;
1062 |     if(_loadIdx < _loadMsgs.length) setStat(_loadMsgs[_loadIdx],'#f4c46f',true);
1063 |     else clearInterval(_loadTimer);
1064 |   }, 6000);
1065 |   var _clearTimer = function(){ clearInterval(_loadTimer); };
1066 |   fetchTO(A+'/oracle/speak',{
1067 |     method:'POST',
1068 |     headers:{'Content-Type':'application/json'},
1069 |     body:JSON.stringify({intent:intent})
1070 |   },30000)
1071 |   .then(function(r){
1072 |     if(!r.ok)throw new Error('HTTP '+r.status);
1073 |     var ct=r.headers.get('content-type')||'';
1074 |     if(ct.indexOf('video')>=0)return r.blob().then(blobURL);
1075 |     return r.json().then(function(j){
1076 |       return fetchTO(A+j.video_url,{},20000).then(function(r2){return r2.blob().then(blobURL);});
1077 |     });
1078 |   })
1079 |   .then(function(url){ if(typeof _clearTimer=='function') _clearTimer(); return playVid(url);})
1080 |   .then(function(){
1081 |     if(intent==='SOVEREIGNTY_ASSESSMENT')showCards();
1082 |     if(intent==='GREETING'){
1083 |       window._briefFetched=false;
1084 |       _greeted=true;
1085 |       /* State machine: welcome done → LISTENING. Always activate mic. */
1086 |       setOracleState('LISTENING');
1087 |       setTimeout(function(){
1088 |         if(!busy&&!isRec&&mic){
1089 |           mic.disabled=false;
1090 |           startRec();
1091 |           setStat('Listening…','#6cff9f',false);
1092 |         }
1093 |       },400);
1094 |     }
1095 |   })
1096 |   .catch(function(e){
1097 |     if(e&&e.message&&e.message.indexOf('HTTP')>=0)
1098 |       setStat('Satomi error — try again.','#ff3b5f',false);
1099 |   })
1100 |   .finally(function(){
1101 |     setBusy(false);
1102 |     setOracleState('LISTENING');
1103 |     setTimeout(pulseMic,500);
1104 |   });
1105 | }
1106 | 
1107 | function si(intent){if(busy)return;hideCards();playIntent(intent);}
1108 | 
1109 | /* ── PROCESS SPEECH (two-phase: audio-first + async video) ── */
1110 | function process(text){
1111 |   if(!text.trim()||busy)return;
1112 |   // Guard: mark brief as fetched to prevent double-play with DAILY_BRIEF_INTRO
1113 |   if(/daily\s*brief/i.test(text)) window._briefFetched=true;
1114 |   setOracleState('PROCESSING');
1115 |   setBusy(true);hideCards();hideActionCard();showTX(text);
1116 | 
1117 |   // P0-3: Elapsed time counter — show "Satomi is thinking... Xs" with live counter
1118 |   var _thinkStart=Date.now();
1119 |   var _thinkReassured=false;
1120 |   setStat('Satomi is thinking\u2026 0s','#f4c46f',true);
1121 |   var _thinkTimer=setInterval(function(){
1122 |     var elapsed=Math.floor((Date.now()-_thinkStart)/1000);
1123 |     // P0-4: Reassurance message after 15s
1124 |     if(elapsed>=15&&!_thinkReassured){
1125 |       _thinkReassured=true;
1126 |       setStat('Rendering your brief\u2026 '+elapsed+'s','#f4c46f',true);
1127 |     } else if(!_thinkReassured){
1128 |       setStat('Satomi is thinking\u2026 '+elapsed+'s','#f4c46f',true);
1129 |     } else {
1130 |       setStat('Rendering your brief\u2026 '+elapsed+'s','#f4c46f',true);
1131 |     }
1132 |   },1000);
1133 |   window._thinkTimer=_thinkTimer;
1134 | 
1135 |   // Phase 2 T1.4: Play thinking loop immediately for instant visual feedback
1136 |   // P0-2: Add onerror fallback — if thinking video fails, show static avatar
1137 |   vid.muted=true;
1138 |   vid.loop=true;
1139 |   vid.src=A+'/oracle/thinking';
1140 |   vid.style.opacity='1';
1141 |   vid.onerror=function(){
1142 |     console.warn('[Satomi] thinking video failed — showing static avatar');
1143 |     vid.style.opacity='0'; /* static avatar image underneath is always visible */
1144 |   };
1145 |   vid.play().catch(function(e){
1146 |     console.warn('[Satomi] thinking autoplay blocked:',e);
1147 |     vid.style.opacity='0'; /* fallback to static avatar */
1148 |   });
1149 | 
1150 |   // Re-unlock audio context on every user interaction
1151 |   try{
1152 |     var _ac=new(window.AudioContext||window.webkitAudioContext)();
1153 |     if(_ac.state==='suspended') _ac.resume();
1154 |     var _buf=_ac.createBuffer(1,1,22050);
1155 |     var _src=_ac.createBufferSource();
1156 |     _src.buffer=_buf;_src.connect(_ac.destination);_src.start(0);
1157 |     setTimeout(function(){try{_ac.close();}catch(e){}},300);
1158 |   }catch(e){}
1159 | 
1160 |   var pendingVideoUrl=null;
1161 |   var _audioFinished=false;
1162 | 
1163 |   fetchTO(A+'/oracle/chat',{
1164 |     method:'POST',headers:{'Content-Type':'application/json'},
1165 |     body:JSON.stringify({text:text,session_id:SESSION_ID,visitor_token:window._visitorToken||'anon',use_cache_for_intents:true,page_context:PAGE_CONTEXT,audio_first:true,avatar_source:"oracle_studio"})
1166 |   },90000)
1167 |   .then(function(r){
1168 |     if(!r.ok) throw new Error('HTTP '+r.status);
1169 |     var ct=r.headers.get('content-type')||'';
1170 |     if(ct.indexOf('video')>=0){
1171 |       // Cache hit — video came back immediately
1172 |       return r.blob().then(blobURL).then(function(url){ return playVid(url); });
1173 |     }
1174 |     // Audio-first JSON response
1175 |     return r.json().then(function(j){
1176 |       var responseText=j.text;
1177 |       var videoJobId=j.job_id;
1178 |       var _pendingCard = j.action_card || null;
1179 | 
1180 |       // Play audio: try cached job audio first (no duplicate Kokoro), fallback to /oracle/voice
1181 |       var audioFetch;
1182 |       if(videoJobId){
1183 |         // Poll job audio with retry — server returns 202 while TTS is rendering
1184 |         function pollJobAudio(jobId, attemptsLeft){
1185 |           return fetchTO(A+'/oracle/job/'+jobId+'/audio',{},15000)
1186 |             .then(function(ar){
1187 |               if(ar.status===202){
1188 |                 // Still rendering — retry after 2s
1189 |                 if(attemptsLeft>0){
1190 |                   return new Promise(function(res){ setTimeout(function(){ res(pollJobAudio(jobId,attemptsLeft-1)); },2000); });
1191 |                 } else {
1192 |                   throw new Error('audio timeout after retries');
1193 |                 }
1194 |               }
1195 |               if(!ar.ok) throw new Error('no cached audio');
1196 |               return ar.blob().then(function(b){
1197 |                 // Validate: must be real audio (>1KB), not a tiny error body
1198 |                 if(b.size < 1024) throw new Error('audio blob too small: '+b.size);
1199 |                 return b;
1200 |               });
1201 |             });
1202 |         }
1203 |         audioFetch=pollJobAudio(videoJobId, 10)
1204 |           .catch(function(){
1205 |             // Fallback: generate fresh TTS
1206 |             return fetchTO(A+'/oracle/voice',{
1207 |               method:'POST',headers:{'Content-Type':'application/json'},
1208 |               body:JSON.stringify({text:responseText})
1209 |             },35000).then(function(ar){
1210 |               if(!ar.ok) throw new Error('audio failed');
1211 |               return ar.blob();
1212 |             });
1213 |           });
1214 |       } else {
1215 |         audioFetch=fetchTO(A+'/oracle/voice',{
1216 |           method:'POST',headers:{'Content-Type':'application/json'},
1217 |           body:JSON.stringify({text:responseText})
1218 |         },35000).then(function(ar){
1219 |           if(!ar.ok) throw new Error('audio failed');
1220 |           return ar.blob();
1221 |         });
1222 |       }
1223 |       return audioFetch
1224 |       .then(function(b){
1225 |         return new Blob([b], {type: b.type || 'audio/wav'});
1226 |       })
1227 |       .then(function(audioBlob){
1228 |         var audioUrl=URL.createObjectURL(audioBlob);
1229 |         var audio;
1230 |         if(window._audioUnlocked){
1231 |           audio=window._audioUnlocked;
1232 |           window._audioUnlocked=null;
1233 |           audio.src=audioUrl;
1234 |           audio.volume=1.0;
1235 |           audio.muted=false;
1236 |         } else {
1237 |           audio=new Audio(audioUrl);
1238 |           audio.volume=1.0;
1239 |         }
1240 |         window._chatAudioPlaying=true;
1241 |         var playPromise = audio.play();
1242 |         if(playPromise !== undefined){
1243 |           playPromise.then(function(){
1244 |             if(window._thinkTimer){clearInterval(window._thinkTimer);window._thinkTimer=null;}
1245 |             /* P0-4: If video not yet ready, show "Rendering video..." instead of "Speaking" */
1246 |             if(!pendingVideoUrl) setStat('Rendering video\u2026','#f4c46f',true);
1247 |             else setStat('Speaking','#6cff9f',false);
1248 |           }).catch(function(err){
1249 |             console.warn('[Satomi] audio.play() rejected:', err.name);
1250 |             // On mobile, audio may be blocked — set volume via user gesture retry
1251 |             audio.muted = false;
1252 |             audio.volume = 1.0;
1253 |             setTimeout(function(){
1254 |               audio.play().catch(function(e2){
1255 |                 console.warn('[Satomi] retry failed:', e2.name);
1256 |                 if(audio.onended) audio.onended();
1257 |               });
1258 |             }, 100);
1259 |           });
1260 |         }
1261 | 
1262 |         return new Promise(function(resolve){
1263 |           audio.onended=function(){
1264 |             _audioFinished=true;
1265 |             if(_pendingCard){ showActionCard(_pendingCard); _pendingCard=null; }
1266 |             window._chatAudioPlaying=false;
1267 |             URL.revokeObjectURL(audioUrl);
1268 |             // Audio finished — unmute video if it's playing lip sync
1269 |             try{ if(!vid.paused){ vid.muted=false; vid.volume=1.0; } }catch(e){}
1270 |             // Don't replay lip-sync video after audio already finished — just resolve
1271 |             if(pendingVideoUrl){
1272 |               try { URL.revokeObjectURL(pendingVideoUrl); } catch(e) {}
1273 |             }
1274 |             resolve();
1275 |           };
1276 | 
1277 |           // Phase 2 T2.1: SSE push replaces polling (with polling fallback)
1278 |           if(videoJobId){
1279 |             var _videoHandled=false;
1280 |             function _handleVideoReady(){
1281 |               if(_videoHandled) return;
1282 |               _videoHandled=true;
1283 |               fetch(A+'/oracle/job/'+videoJobId)
1284 |                 .then(function(vr){
1285 |                   if(vr.status===200 && (vr.headers.get('content-type')||'').indexOf('video')>=0){
1286 |                     return vr.blob();
1287 |                   }
1288 |                   return null;
1289 |                 })
1290 |                 .then(function(vb){
1291 |                   if(vb){
1292 |                     pendingVideoUrl=blobURL(vb);
1293 |                     if(_audioFinished){
1294 |                       // Cross-fade: thinking loop → lip-sync video
1295 |                       vid.style.opacity='0';
1296 |                       setTimeout(function(){
1297 |                         vid.loop=false;
1298 |                         vid.muted=false;
1299 |                         vid.src=pendingVideoUrl;
1300 |                         vid.style.opacity='1';
1301 |                         playVid(pendingVideoUrl);
1302 |                       },300);
1303 |                     }
1304 |                   }
1305 |                 })
1306 |                 .catch(function(e){console.warn('[Satomi] video fetch error:',e);});
1307 |             }
1308 | 
1309 |             if(window.EventSource){
1310 |               // SSE push — sub-100ms notification
1311 |               var evtSource=new EventSource(A+'/oracle/job/'+videoJobId+'/stream');
1312 |               evtSource.addEventListener('audio_ready',function(){
1313 |                 // Audio already being fetched above — this is informational
1314 |               });
1315 |               evtSource.addEventListener('video_ready',function(){
1316 |                 evtSource.close();
1317 |                 _handleVideoReady();
1318 |               });
1319 |               evtSource.addEventListener('error',function(e){
1320 |                 evtSource.close();
1321 |                 // P1-1: SSE error — stop thinking loop but keep static avatar visible
1322 |                 vid.loop=false;
1323 |                 vid.style.opacity='0'; /* static avatar img underneath remains visible */
1324 |                 setStat('Connection issue — retrying\u2026','#f4c46f',true);
1325 |               });
1326 |               evtSource.onerror=function(){
1327 |                 // Connection lost — fall back to polling
1328 |                 evtSource.close();
1329 |                 if(!_videoHandled) _startPollFallback();
1330 |               };
1331 |             } else {
1332 |               _startPollFallback();
1333 |             }
1334 | 
1335 |             function _startPollFallback(){
1336 |               var pollAttempts=0,maxPollAttempts=60;
1337 |               var pollVideo=setInterval(function(){
1338 |                 pollAttempts++;
1339 |                 fetch(A+'/oracle/job/'+videoJobId)
1340 |                   .then(function(vr){
1341 |                     if(vr.status===200 && (vr.headers.get('content-type')||'').indexOf('video')>=0){
1342 |                       return vr.blob();
1343 |                     }
1344 |                     return null;
1345 |                   })
1346 |                   .then(function(vb){
1347 |                     if(vb){
1348 |                       clearInterval(pollVideo);
1349 |                       _videoHandled=true;
1350 |                       pendingVideoUrl=blobURL(vb);
1351 |                       if(_audioFinished){
1352 |                         vid.style.opacity='1';
1353 |                         playVid(pendingVideoUrl);
1354 |                       }
1355 |                     }
1356 |                   })
1357 |                   .catch(function(){});
1358 |                 if(pollAttempts>=maxPollAttempts){
1359 |                   clearInterval(pollVideo);
1360 |                   setBusy(false);mic.disabled=false;
1361 |                 }
1362 |               },2000);
1363 |             }
1364 |           }
1365 |         });
1366 |       });
1367 |     });
1368 |   })
1369 |   .then(function(){
1370 |     setTimeout(pulseMic,500);
1371 |   })
1372 |   .catch(function(e){
1373 |     console.error('process error:',e);
1374 |     var msg=(e&&e.message)||'';
1375 |     /* P1: 429/503 — server overloaded, auto-retry after 5s */
1376 |     if(msg.indexOf('429')>=0||msg.indexOf('503')>=0){
1377 |       vid.style.opacity='0';
1378 |       setStat('Satomi is meditating\u2026 retrying in 5s','#f4c46f',true);
1379 |       var _retryText=text;
1380 |       setTimeout(function(){
1381 |         setBusy(false);
1382 |         if(window._thinkTimer){clearInterval(window._thinkTimer);window._thinkTimer=null;}
1383 |         setOracleState('LISTENING');
1384 |         if(_retryText)process(_retryText);
1385 |       },5000);
1386 |       return; /* skip .finally cleanup — retry will handle it */
1387 |     } else if(msg.indexOf('timeout')>=0){
1388 |       vid.style.opacity='0';
1389 |       setStat('Request timed out — tap mic to retry','#f4c46f',false);
1390 |     } else if(msg.indexOf('HTTP')>=0){
1391 |       vid.style.opacity='0';
1392 |       setStat('Satomi error — tap mic to retry','#ff3b5f',false);
1393 |     } else if(msg.indexOf('Failed to fetch')>=0||msg.indexOf('NetworkError')>=0){
1394 |       vid.style.opacity='0';
1395 |       setStat('Network error — check connection','#ff3b5f',false);
1396 |     }
1397 |   })
1398 |   .finally(function(){
1399 |     if(window._thinkTimer){clearInterval(window._thinkTimer);window._thinkTimer=null;}
1400 |     setBusy(false);hideTX();
1401 |     setOracleState('LISTENING');
1402 |   });
1403 | }
1404 | 
1405 | function blobURL(b){
1406 |   if(objURL)try{URL.revokeObjectURL(objURL);}catch(e){}
1407 |   objURL=URL.createObjectURL(b);
1408 |   return objURL;
1409 | }
1410 | 
1411 | /* ── PLAY VIDEO ── */
1412 | function playVid(url){
1413 |   return new Promise(function(res){
1414 |     setOracleState('RESPONDING');
1415 |     vid.loop=false;
1416 |     vid.src=url;
1417 |     vid.style.opacity='1';
1418 |     if(window._matrixHide) window._matrixHide();
1419 |     var _safetyTimer = setTimeout(function(){
1420 |       if(busy){
1421 |         console.warn('[Satomi] Safety timeout — forcing mic unlock after 30s');
1422 |         setBusy(false);
1423 |         if(window._thinkTimer){clearInterval(window._thinkTimer);window._thinkTimer=null;}
1424 |         setOracleState('LISTENING');
1425 |       }
1426 |     }, 30000);
1427 |     try{if(window.parent!==window) window.parent.postMessage({type:'oracle:speaking'},'*');}catch(e){}
1428 |     vid.onended=function(){
1429 |       clearTimeout(_safetyTimer);
1430 |       if(window._thinkTimer){clearInterval(window._thinkTimer);window._thinkTimer=null;}
1431 |       /* P1-3: Fade out first, then clear src — avoids flash. Static avatar underneath stays visible. */
1432 |       vid.style.opacity='0';
1433 |       setTimeout(function(){ vid.src=''; },300);
1434 |       if(window._matrixShow) window._matrixShow();
1435 |       hideSub();
1436 |       setBusy(false);
1437 |       setOracleState('LISTENING');
1438 |       res();
1439 |       try{if(window.parent!==window) window.parent.postMessage({type:'oracle:idle'},'*');}catch(e){}
1440 |     };
1441 |     vid.onerror=function(){
1442 |       clearTimeout(_safetyTimer);
1443 |       if(window._thinkTimer){clearInterval(window._thinkTimer);window._thinkTimer=null;}
1444 |       // P0-2: On video error, fade to static avatar (always visible behind vid)
1445 |       vid.style.opacity='0';
1446 |       vid.src='';
1447 |       setStat('Recovering\u2026','#f4c46f',true);
1448 |       setTimeout(function(){
1449 |         setBusy(false);
1450 |         setOracleState('LISTENING');
1451 |         setStat('Ready','#334',false);
1452 |         res();
1453 |       }, 1500);
1454 |     };
1455 |     vid.muted=true;
1456 |     vid.volume=1.0;
1457 |     var unmuted=false;
1458 |     function tryUnmute(){
1459 |       if(unmuted)return; unmuted=true;
1460 |       vid.muted=false;
1461 |       vid.volume=1.0;
1462 |     }
1463 |     vid.addEventListener('canplay',function oncp(){
1464 |       vid.removeEventListener('canplay',oncp);
1465 |       setStat('Speaking','#6cff9f',false);
1466 |       if(!window._chatAudioPlaying){
1467 |         tryUnmute();
1468 |       }
1469 |     },{once:true});
1470 |     var p=vid.play();
1471 |     if(p){
1472 |       p.then(function(){}).catch(function(){
1473 |         /* P0: iOS Safari — show centered tap-to-play overlay */
1474 |         showTapOverlay();
1475 |       });
1476 |     }
1477 |   });
1478 | }
1479 | 
1480 | /* ── SPEECH RECOGNITION ── */
1481 | function initSR(){
1482 |   var SR=window.SpeechRecognition||window.webkitSpeechRecognition;
1483 |   if(!SR){micHint.textContent='no speech api';return;}
1484 |   recognition=new SR();
1485 |   recognition.continuous=true;recognition.interimResults=true;recognition.lang='en-US';recognition.maxAlternatives=1;
1486 |   recognition.onresult=function(e){
1487 |     var fin='',int='';
1488 |     for(var i=0;i<e.results.length;i++){
1489 |       if(e.results[i].isFinal)fin+=e.results[i][0].transcript;
1490 |       else int+=e.results[i][0].transcript;
1491 |     }
1492 |     showTX(fin||int);if(fin)pending=fin;
1493 |   };
1494 |   recognition.onend=function(){
1495 |     setRec(false);
1496 |     // Auto-submit on silence — no tap required
1497 |     var _pend = pending;
1498 |     /* P1: Bridge status — show "Processing..." immediately so user sees feedback */
1499 |     if(_pend.trim()&&!busy){setStat('Processing\u2026','#f4c46f',true);}
1500 |     setTimeout(function(){ if(_pend.trim()&&!busy){process(_pend);pending='';}}, 100);
1501 |   };
1502 |   recognition.onerror=function(e){console.warn(e.error);setRec(false);};
1503 | }
1504 | 
1505 | function toggleMic(){if(busy)return;isRec?stopRec():startRec();}
1506 | function startRec(){
1507 |   if(!recognition){setStat('No speech API','#ff3b5f',false);return;}
1508 |   pending='';isRec=true;setRec(true);setStat('\ud83c\udf99 Listening...','#66d9ff',false);
1509 |   try{recognition.start();}catch(e){console.warn(e);}
1510 | }
1511 | function stopRec(){
1512 |   isRec=false;setRec(false);
1513 |   /* P1-2: Don't play thinking video here — let recognition.onend → process() be the sole trigger.
1514 |      This eliminates the race condition where both stopRec and onend try to set thinking state. */
1515 |   if(recognition)try{recognition.stop();}catch(e){}
1516 |   // onend will fire after recognition.stop() and handle process() automatically
1517 | }
1518 | function setRec(on){
1519 |   mic.classList.toggle('rec',on);
1520 |   iMic.style.display=on?'none':'block';
1521 |   iStop.style.display=on?'block':'none';
1522 |   micHint.textContent=on?'tap to send':'tap to speak';
1523 | }
1524 | 
1525 | /* ── HELPERS ── */
1526 | function setStat(t,c,sp){statEl.textContent=t;statEl.style.color=c||'#334';spinEl.style.display=sp?'block':'none';spinEl.style.color=c||'#334';}
1527 | function setBusy(b){busy=b;if(b){mic.disabled=true;if(isRec)stopRec();}}
1528 | function showSub(t){sub.textContent=t;sub.classList.add('on');}
1529 | function hideSub(){sub.classList.remove('on');}
1530 | function showTX(t){txEl.textContent=t;txEl.classList.add('on');}
1531 | function hideTX(){txEl.classList.remove('on');}
1532 | function showCards(){cards.classList.add('on');}
1533 | function hideCards(){cards.classList.remove('on');}
1534 | 
1535 | /* ── TAP-TO-PLAY OVERLAY (P0: iOS Safari autoplay) ── */
1536 | function showTapOverlay(){
1537 |   var ov=document.getElementById('tap-to-play');
1538 |   if(ov){ov.style.display='flex';}
1539 |   setStat('Tap to play','#f4c46f',false);
1540 | }
1541 | function dismissTapOverlay(){
1542 |   var ov=document.getElementById('tap-to-play');
1543 |   if(ov){ov.style.display='none';}
1544 |   vid.muted=false;vid.volume=1.0;
1545 |   vid.play().then(function(){
1546 |     setStat('Speaking','#6cff9f',false);
1547 |   }).catch(function(e){
1548 |     console.warn('[Satomi] tap-to-play retry failed:',e);
1549 |     vid.style.opacity='0';
1550 |     setStat('Ready','#334',false);
1551 |   });
1552 | }
1553 | 
1554 | /* ── TEXT INPUT FALLBACK (P0: mic failure → text mode) ── */
1555 | var _textMode=false;
1556 | function goTextMode(){
1557 |   /* Skip mic, transition straight to stage with text input visible */
1558 |   _textMode=true;
1559 |   gBtn.disabled=true;
1560 |   gErr.style.display='none';
1561 |   /* Unlock audio context on this user gesture (same as requestMic) */
1562 |   try{
1563 |     var _ac=new(window.AudioContext||window.webkitAudioContext)();
1564 |     var _buf=_ac.createBuffer(1,1,22050);var _src=_ac.createBufferSource();
1565 |     _src.buffer=_buf;_src.connect(_ac.destination);_src.start(0);
1566 |     setTimeout(function(){try{_ac.close();}catch(e){}},300);
1567 |   }catch(e){}
1568 |   vid.muted=true;vid.play().catch(function(){});
1569 |   window._audioUnlocked=new Audio();
1570 |   window._audioUnlocked.src='data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAESsAABErAAABAAgAZGF0YQIAAAABAA==';
1571 |   window._audioUnlocked.volume=0.001;
1572 |   window._audioUnlocked.play().catch(function(){});
1573 |   window._chatAudioPlaying=false;
1574 |   gate.style.opacity='0';
1575 |   setTimeout(function(){
1576 |     gate.style.display='none';
1577 |     stage.style.display='flex';
1578 |     stage.style.opacity='0';
1579 |     setTimeout(function(){
1580 |       stage.style.transition='opacity .45s';
1581 |       stage.style.opacity='1';
1582 |       /* Show text input, hide mic area, init speech recognition (may still work for some) */
1583 |       document.getElementById('stage-text-input').style.display='block';
1584 |       mic.disabled=true;
1585 |       micHint.textContent='text mode';
1586 |       initSR();
1587 |       setOracleState('WELCOME');
1588 |       playIntent('GREETING');
1589 |       /* After greeting, enable mic if SR is available as bonus */
1590 |       setTimeout(function(){
1591 |         if(recognition){mic.disabled=false;micHint.textContent='tap to speak';}
1592 |       },8000);
1593 |     },30);
1594 |   },350);
1595 | }
1596 | function submitTextInput(){
1597 |   var field=document.getElementById('text-input-field');
1598 |   var text=(field.value||'').trim();
1599 |   if(!text)return;
1600 |   field.value='';
1601 |   goTextMode();
1602 |   /* Queue the text to process after greeting finishes */
1603 |   var _waitGreeting=setInterval(function(){
1604 |     if(!busy){clearInterval(_waitGreeting);process(text);}
1605 |   },500);
1606 | }
1607 | function stageTextSubmit(){
1608 |   var field=document.getElementById('stage-text-field');
1609 |   var text=(field.value||'').trim();
1610 |   if(!text||busy)return;
1611 |   field.value='';
1612 |   process(text);
1613 | }
1614 | 
1615 | /* ── GEMINI VISION ── */
1616 | var _visionSessionId = null;
1617 | 
1618 | function updateCameraButtonState() {
1619 |   var lbl = document.getElementById('cam-btn-label');
1620 |   if (!lbl) return;
1621 |   lbl.textContent = _visionSessionId
1622 |     ? 'FOLLOW-UP PHOTO'
1623 |     : 'ANALYZE HARDWARE';
1624 | }
1625 | 
1626 | function triggerCamera(){
1627 |   document.getElementById("cam-input").click();
1628 | }
1629 | 
1630 | function handleVisionUpload(evt){
1631 |   var file = evt.target.files[0];
1632 |   if(!file) return;
1633 |   if (busy) {
1634 |     showVisionStatus('Satomi is speaking — wait a moment');
1635 |     setTimeout(hideVisionStatus, 2000);
1636 |     evt.target.value = "";
1637 |     return;
1638 |   }
1639 |   evt.target.value = "";
1640 |   
1641 |   var reader = new FileReader();
1642 |   reader.onload = function(e){
1643 |     var b64 = e.target.result.split(",")[1];
1644 |     var mime = file.type || "image/jpeg";
1645 |     sendVisionImage(b64, mime);
1646 |   };
1647 |   reader.readAsDataURL(file);
1648 | }
1649 | 
1650 | var SEED_RECOVERY_STEPS = [
1651 |   {
1652 |     label: 'STEP 1 OF 3 — STOP IMMEDIATELY',
1653 |     text: 'Do NOT send any Bitcoin from this wallet until you have moved your funds. Anyone who saw this seed phrase can access your Bitcoin right now.',
1654 |     speak: 'Stop. Do not send any Bitcoin from this wallet. Anyone who saw this seed phrase can steal your funds right now.'
1655 |   },
1656 |   {
1657 |     label: 'STEP 2 OF 3 — MOVE YOUR FUNDS',
1658 |     text: 'On a different device, create a brand new wallet. Generate a NEW seed phrase — write it down on paper only, never photograph it. Transfer ALL funds to the new wallet address immediately.',
1659 |     speak: 'On a different device, create a new wallet with a new seed phrase. Write it on paper only. Transfer all your funds to the new wallet immediately.'
1660 |   },
1661 |   {
1662 |     label: 'STEP 3 OF 3 — SECURE THE NEW WALLET',
1663 |     text: 'Once funds are transferred, the old wallet is abandoned. Store your new seed phrase in a metal backup, split across two secure locations. Never store seed phrases digitally.',
1664 |     speak: 'Once funds are moved, abandon the old wallet. Store your new seed phrase in metal, split across two secure locations. Never store seed phrases digitally.'
1665 |   }
1666 | ];
1667 | 
1668 | function showSecurityAlert(msg, onDismiss) {
1669 |   var overlay = document.getElementById('vision-security-overlay');
1670 |   var msgEl = document.getElementById('vision-security-msg');
1671 |   var dismissBtn = document.getElementById('vision-security-dismiss');
1672 |   var recoveryPanel = document.getElementById('vision-recovery-panel');
1673 |   if (!overlay || !msgEl) return;
1674 | 
1675 |   msgEl.textContent = msg;
1676 |   overlay.style.display = 'flex';
1677 | 
1678 |   // Speak the initial alert urgently
1679 |   function speakText(text) {
1680 |     fetchTO(A+'/oracle/voice', {
1681 |       method: 'POST',
1682 |       headers: {'Content-Type': 'application/json'},
1683 |       body: JSON.stringify({text: text})
1684 |     }, 20000).then(function(r) {
1685 |       if (!r.ok) return;
1686 |       return r.blob();
1687 |     }).then(function(blob) {
1688 |       if (!blob) return;
1689 |       var alertAudio = new Audio(URL.createObjectURL(blob));
1690 |       alertAudio.volume = 1.0;
1691 |       alertAudio.play().catch(function(){});
1692 |     }).catch(function(){});
1693 |   }
1694 | 
1695 |   speakText('SECURITY ALERT. ' + msg +
1696 |     ' Your seed phrase may be compromised. Do not send Bitcoin until you hear the recovery steps.');
1697 | 
1698 |   // Dismiss transitions to recovery steps
1699 |   dismissBtn.onclick = function() {
1700 |     dismissBtn.style.display = 'none';
1701 |     msgEl.style.fontSize = '0.9rem';
1702 |     msgEl.style.opacity = '0.7';
1703 |     recoveryPanel.style.display = 'block';
1704 |     _showRecoveryStep(0, speakText);
1705 |   };
1706 | }
1707 | 
1708 | function _showRecoveryStep(idx, speakFn) {
1709 |   var steps = SEED_RECOVERY_STEPS;
1710 |   var stepLabel = document.getElementById('vision-recovery-step-label');
1711 |   var stepText = document.getElementById('vision-recovery-step-text');
1712 |   var nextBtn = document.getElementById('vision-recovery-next');
1713 |   var helpBtn = document.getElementById('vision-recovery-help');
1714 |   var closeBtn = document.getElementById('vision-recovery-close');
1715 | 
1716 |   if (!stepLabel || !stepText) return;
1717 | 
1718 |   stepLabel.textContent = steps[idx].label;
1719 |   stepText.textContent = steps[idx].text;
1720 |   speakFn(steps[idx].speak);
1721 | 
1722 |   var isLast = (idx === steps.length - 1);
1723 |   nextBtn.style.display = isLast ? 'none' : 'block';
1724 |   helpBtn.style.display = isLast ? 'block' : 'none';
1725 |   closeBtn.style.display = isLast ? 'block' : 'none';
1726 | 
1727 |   nextBtn.onclick = function() {
1728 |     if (idx < steps.length - 1) _showRecoveryStep(idx + 1, speakFn);
1729 |   };
1730 | 
1731 |   helpBtn.onclick = function() {
1732 |     // Close overlay and trigger Satomi to help set up new wallet
1733 |     var overlay = document.getElementById('vision-security-overlay');
1734 |     if (overlay) overlay.style.display = 'none';
1735 |     // Inject a vision guidance request for new wallet setup
1736 |     sendVisionImage(null, null, 'help me set up a new hardware wallet safely');
1737 |   };
1738 | 
1739 |   closeBtn.onclick = function() {
1740 |     var overlay = document.getElementById('vision-security-overlay');
1741 |     if (overlay) overlay.style.display = 'none';
1742 |   };
1743 | }
1744 | 
1745 | function _speakVisionGuidance(d) {
1746 |   var raw = d.guidance_text || d.guidance || d.analysis || d.response
1747 |     || "I can see your hardware. Let me walk you through the next step.";
1748 |   // Hard 30-word cap for TTS speed
1749 |   var words = raw.split(/\s+/);
1750 |   var guideText = words.length > 30 ? words.slice(0,30).join(" ") : raw;
1751 | 
1752 |   // Urgent spoken prefix for transaction verdicts
1753 |   if (d.verdict === 'DO NOT SIGN') {
1754 |     guideText = 'WARNING. DO NOT SIGN THIS TRANSACTION. ' + guideText;
1755 |   } else if (d.verdict === 'REVIEW CAREFULLY' && d.red_flags && d.red_flags.length) {
1756 |     guideText = 'REVIEW CAREFULLY. ' + guideText;
1757 |   }
1758 | 
1759 |   showVisionStatus("Speaking...");
1760 |   showSub(guideText);
1761 | 
1762 |   // Transaction review verdict card
1763 |   if (d.category === 'transaction' && d.verdict) {
1764 |     var verdictColor = d.verdict === 'SAFE TO SIGN'
1765 |       ? '#00d4aa'
1766 |       : d.verdict === 'DO NOT SIGN'
1767 |       ? '#ff3b5f'
1768 |       : '#f5a623';
1769 | 
1770 |     var verdictHtml = '<div style="background:rgba(0,0,0,.4);' +
1771 |       'border:2px solid ' + verdictColor + ';border-radius:8px;' +
1772 |       'padding:12px 16px;margin-bottom:12px;">' +
1773 |       '<div style="font-family:monospace;font-size:10px;' +
1774 |       'letter-spacing:.12em;color:' + verdictColor + ';' +
1775 |       'text-transform:uppercase;margin-bottom:6px;">' +
1776 |       '\u26A1 TRANSACTION ANALYSIS</div>' +
1777 |       '<div style="font-size:1.1rem;font-weight:800;' +
1778 |       'color:' + verdictColor + ';margin-bottom:8px;">' +
1779 |       d.verdict + '</div>';
1780 | 
1781 |     if (d.recipient_address) {
1782 |       verdictHtml += '<div style="font-family:monospace;font-size:10px;' +
1783 |         'color:rgba(255,255,255,.5);word-break:break-all;">' +
1784 |         'TO: ' + d.recipient_address + '</div>';
1785 |     }
1786 |     if (d.amount_btc) {
1787 |       verdictHtml += '<div style="font-family:monospace;font-size:11px;' +
1788 |         'color:rgba(255,255,255,.7);margin-top:4px;">' +
1789 |         'AMOUNT: ' + d.amount_btc + ' BTC</div>';
1790 |     }
1791 |     if (d.fee_sats) {
1792 |       verdictHtml += '<div style="font-family:monospace;font-size:11px;' +
1793 |         'color:rgba(255,255,255,.6);">' +
1794 |         'FEE: ' + d.fee_sats + ' sats</div>';
1795 |     }
1796 |     if (d.red_flags && d.red_flags.length) {
1797 |       verdictHtml += '<div style="margin-top:8px;">';
1798 |       d.red_flags.forEach(function(flag) {
1799 |         verdictHtml += '<div style="font-family:monospace;font-size:9px;' +
1800 |           'color:#f5a623;letter-spacing:.06em;">\u26A0 ' + flag + '</div>';
1801 |       });
1802 |       verdictHtml += '</div>';
1803 |     }
1804 |     verdictHtml += '</div>';
1805 | 
1806 |     var vsEl = document.getElementById('vision-status');
1807 |     if (vsEl) {
1808 |       vsEl.innerHTML = verdictHtml + (vsEl.innerHTML || '');
1809 |       vsEl.classList.add('on');
1810 |     }
1811 |   }
1812 | 
1813 |   // Show steps in vision-status area if present
1814 |   if(d.steps && d.steps.length){
1815 |     var stepsHtml = d.steps.map(function(s,i){ return (i+1)+". "+s; }).join("<br>");
1816 |     var el=document.getElementById("vision-status");
1817 |     el.innerHTML = (d.device_name && d.device_name!=="unknown" ? "<b>"+d.device_name+"</b><br>" : "") + stepsHtml;
1818 |     el.classList.add("on");
1819 |   }
1820 | 
1821 |   // Add to session transcript
1822 |   _addVisionEntry(d.device_name, d.steps || [], guideText);
1823 | 
1824 |   // VOICE-ONLY: /oracle/voice is ElevenLabs-only, no GPU, ~400ms vs 14s
1825 |   fetchTO(A+"/oracle/voice",{method:"POST",
1826 |     headers:{"Content-Type":"application/json"},
1827 |     body:JSON.stringify({text:guideText})},15000)
1828 |   .then(function(ar){
1829 |     if(!ar.ok) throw new Error("voice "+ar.status);
1830 |     return ar.blob();
1831 |   })
1832 |   .then(function(audioBlob){
1833 |     hideVisionStatus();
1834 |     var audioURL = URL.createObjectURL(audioBlob);
1835 |     var audio;
1836 |     if(window._audioUnlocked){
1837 |       audio=window._audioUnlocked;
1838 |       window._audioUnlocked=null;
1839 |       audio.src=audioURL;
1840 |       audio.volume=1.0;
1841 |       audio.muted=false;
1842 |     } else {
1843 |       audio = new Audio(audioURL);
1844 |       audio.volume = 1.0;
1845 |     }
1846 |     return new Promise(function(res){
1847 |       audio.onended = function(){
1848 |         URL.revokeObjectURL(audioURL);
1849 |         setStat("Ready","#334",false);
1850 |         hideSub();
1851 |         if(d.device_name){
1852 |           setTimeout(function(){ showVisionSponsor(d.device_name); },800);
1853 |         }
1854 |         // Prompt for follow-up photo if session is active
1855 |         if (_visionSessionId) {
1856 |           showVisionStatus('Tap camera to show next screen \u2192');
1857 |           setTimeout(function() {
1858 |             hideVisionStatus();
1859 |           }, 4000);
1860 |         }
1861 |         res();
1862 |       };
1863 |       audio.onerror = function(){ URL.revokeObjectURL(audioURL); res(); };
1864 |       var vp = audio.play();
1865 |       if(vp !== undefined){
1866 |         vp.then(function(){ setStat("Speaking","#6cff9f",false); }).catch(function(){ res(); });
1867 |       }
1868 |     });
1869 |   })
1870 |   .catch(function(){
1871 |     showVisionStatus("Ready");
1872 |     setBusy(false);
1873 |     mic.disabled = false;
1874 |   });
1875 | }
1876 | 
1877 | function sendVisionImage(b64, mimeType, textOverride){
1878 |   // Text-only mode: no image, just a guided question
1879 |   if (!b64 && textOverride) {
1880 |     setBusy(true);
1881 |     showVisionStatus('Preparing guidance...');
1882 |     _speakVisionGuidance({
1883 |       guidance_text: 'I can guide you through setting up a new hardware wallet securely. First, choose a wallet: Coldcard for maximum security, Trezor for ease of use, or SeedSigner for open-source air-gapped signing. Which would you like help with?',
1884 |       device_name: 'new_wallet_setup',
1885 |       steps: [
1886 |         'Choose your hardware wallet: Coldcard, Trezor, or SeedSigner',
1887 |         'Purchase only from official manufacturer websites — never third party',
1888 |         'On first boot, generate a new seed phrase on the device itself',
1889 |         'Write seed phrase on paper only — never photograph or type it',
1890 |         'Test recovery before sending any funds'
1891 |       ]
1892 |     });
1893 |     setBusy(false);
1894 |     return;
1895 |   }
1896 | 
1897 |   setBusy(true);
1898 |   showVisionStatus("Analyzing your screen...");
1899 | 
1900 |   var endpoint = _visionSessionId ? A+"/vision/guide" : A+"/vision/analyze";
1901 |   var body = {image_base64:b64, mime_type:mimeType,
1902 |     context:"User needs Bitcoin hardware setup guidance"};
1903 |   if(_visionSessionId){
1904 |     body.session_id = _visionSessionId;
1905 |     body.question = "What step am I at and what should I do next?";
1906 |     body.last_context = _visionTranscript.length > 0
1907 |       ? _visionTranscript[_visionTranscript.length - 1].steps.join('; ')
1908 |       : '';
1909 |   }
1910 | 
1911 |   fetchTO(endpoint,{method:"POST",headers:{"Content-Type":"application/json"},
1912 |     body:JSON.stringify(body)},20000)
1913 |   .then(function(r){
1914 |     if(!r.ok) throw new Error("vision "+r.status);
1915 |     return r.json();
1916 |   })
1917 |   .then(function(d){
1918 |     _visionSessionId = d.session_id || _visionSessionId;
1919 |     updateCameraButtonState();
1920 | 
1921 |     // Security alert takes absolute priority — recovery flow keeps overlay open
1922 |     if (d.security_alert) {
1923 |       showSecurityAlert(d.security_alert);
1924 |       return;
1925 |     }
1926 |     _speakVisionGuidance(d);
1927 |   })
1928 |   .catch(function(e){
1929 |     console.error("Vision error:", e);
1930 |     showVisionStatus("Vision error — try again.");
1931 |     setTimeout(hideVisionStatus, 3000);
1932 |   })
1933 |   .finally(function(){ setBusy(false); mic.disabled=false; });
1934 | }
1935 | 
1936 | function showVisionStatus(msg){ 
1937 |   var el=document.getElementById("vision-status");
1938 |   el.textContent=msg; el.classList.add("on");
1939 | }
1940 | function hideVisionStatus(){
1941 |   var el=document.getElementById("vision-status");
1942 |   el.classList.remove("on");
1943 | }
1944 | 
1945 | /* ── VISION SESSION TRANSCRIPT ── */
1946 | var _visionTranscript = [];
1947 | 
1948 | function _addVisionEntry(deviceName, steps, guidanceText) {
1949 |   var panel = document.getElementById('vision-transcript-panel');
1950 |   var entries = document.getElementById('vision-transcript-entries');
1951 |   if (!entries) return;
1952 | 
1953 |   if (panel && _visionTranscript.length === 0) {
1954 |     panel.style.display = 'block';
1955 |   }
1956 | 
1957 |   var entry = {
1958 |     device: deviceName || 'Unknown Device',
1959 |     steps: steps || [],
1960 |     guidance: guidanceText || '',
1961 |     time: new Date().toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'})
1962 |   };
1963 |   _visionTranscript.push(entry);
1964 | 
1965 |   var el = document.createElement('div');
1966 |   el.className = 'vision-entry';
1967 | 
1968 |   var deviceEl = document.createElement('div');
1969 |   deviceEl.className = 'vision-entry-device';
1970 |   deviceEl.textContent = entry.device.toUpperCase();
1971 |   el.appendChild(deviceEl);
1972 | 
1973 |   if (entry.steps.length) {
1974 |     entry.steps.forEach(function(s, i) {
1975 |       var stepEl = document.createElement('div');
1976 |       stepEl.className = 'vision-entry-step';
1977 |       stepEl.textContent = (i+1) + '. ' + s;
1978 |       el.appendChild(stepEl);
1979 |     });
1980 |   } else if (entry.guidance) {
1981 |     var guidEl = document.createElement('div');
1982 |     guidEl.className = 'vision-entry-step';
1983 |     guidEl.textContent = entry.guidance.substring(0, 120) +
1984 |       (entry.guidance.length > 120 ? '…' : '');
1985 |     el.appendChild(guidEl);
1986 |   }
1987 | 
1988 |   var timeEl = document.createElement('div');
1989 |   timeEl.className = 'vision-entry-time';
1990 |   timeEl.textContent = entry.time + ' — tap to re-read';
1991 |   el.appendChild(timeEl);
1992 | 
1993 |   el.onclick = function() {
1994 |     var text = entry.steps.length
1995 |       ? entry.device + '. ' + entry.steps.join('. ')
1996 |       : entry.guidance;
1997 |     fetchTO(A+'/oracle/voice', {
1998 |       method: 'POST',
1999 |       headers: {'Content-Type': 'application/json'},
2000 |       body: JSON.stringify({text: text.substring(0, 200)})
2001 |     }, 20000).then(function(r) {
2002 |       return r.ok ? r.blob() : null;
2003 |     }).then(function(blob) {
2004 |       if (!blob) return;
2005 |       var a = new Audio(URL.createObjectURL(blob));
2006 |       a.volume = 1.0;
2007 |       a.play().catch(function(){});
2008 |     }).catch(function(){});
2009 |   };
2010 | 
2011 |   entries.appendChild(el);
2012 |   entries.scrollTop = entries.scrollHeight;
2013 | }
2014 | 
2015 | document.addEventListener('DOMContentLoaded', function() {
2016 |   var clearBtn = document.getElementById('vision-transcript-clear');
2017 |   if (clearBtn) {
2018 |     clearBtn.onclick = function() {
2019 |       _visionTranscript = [];
2020 |       var entries = document.getElementById('vision-transcript-entries');
2021 |       if (entries) entries.innerHTML = '';
2022 |       var panel = document.getElementById('vision-transcript-panel');
2023 |       if (panel) panel.style.display = 'none';
2024 |       _visionSessionId = null;
2025 |       updateCameraButtonState();
2026 |     };
2027 |   }
2028 | });
2029 | 
2030 | /* ── MINIMIZE / EXIT / FLOAT ── */
2031 | var _oracleMinimized = false;
2032 | 
2033 | function minimizeOracle(){
2034 |   var inIframe = (function(){ try{ return window.self !== window.top; }catch(e){ return true; }})();
2035 |   if(inIframe){
2036 |     try{ window.parent.postMessage({type:'oracle:minimize'},'*'); }catch(e){}
2037 |     return;
2038 |   }
2039 |   // Standalone: shrink to float bubble
2040 |   _oracleMinimized = true;
2041 |   document.getElementById("oracle-root").style.display = "none";
2042 |   var f = document.getElementById("oracle-float");
2043 |   if(f){ f.style.display = "flex"; if(busy) f.classList.add("speaking"); }
2044 | }
2045 | 
2046 | function restoreOracle(){
2047 |   _oracleMinimized = false;
2048 |   document.getElementById("oracle-float").style.display = "none";
2049 |   document.getElementById("oracle-root").style.display = "flex";
2050 |   document.getElementById("oracle-float").classList.remove("speaking");
2051 | }
2052 | 
2053 | function exitOracle(){
2054 |   // If running inside widget iframe — tell parent to close
2055 |   var inIframe = (function(){ try{ return window.self !== window.top; }catch(e){ return true; }})();
2056 |   if(inIframe){
2057 |     try{ window.parent.postMessage({type:'oracle:close'},'*'); }catch(e){}
2058 |     return;
2059 |   }
2060 |   // Standalone page — return to gate screen
2061 |   _oracleMinimized = false;
2062 |   // Stop any playing audio/video
2063 |   vid.pause(); vid.src="";
2064 |   if(isRec) stopRec();
2065 |   // Reset session on server
2066 |   fetch(A+"/oracle/session/reset",{method:"POST",
2067 |     headers:{"Content-Type":"application/json"},
2068 |     body:JSON.stringify({session_id:SESSION_ID})}).catch(function(){});
2069 |   // Hide everything
2070 |   document.getElementById("oracle-float").style.display = "none";
2071 |   document.getElementById("live-stage").style.display = "none";
2072 |   document.getElementById("oracle-root").style.display = "flex";
2073 |   // Show gate again
2074 |   var g = document.getElementById("gate");
2075 |   g.style.display = "flex";
2076 |   g.style.opacity = "1";
2077 |   g.style.transition = "opacity .3s";
2078 |   // Reset state
2079 |   busy = false; window._briefFetched = false;
2080 |   setStat("Ready","#334",false);
2081 |   hideSub(); hideTranscript && hideTX();
2082 | }
2083 | 
2084 | // Keep float speaking indicator in sync
2085 | var _origSetStat = setStat;
2086 | setStat = function(msg, color, spin){
2087 |   _origSetStat(msg, color, spin);
2088 |   var f = document.getElementById("oracle-float");
2089 |   if(f && _oracleMinimized){
2090 |     if(msg === "Speaking") f.classList.add("speaking");
2091 |     else f.classList.remove("speaking");
2092 |   }
2093 | };
2094 | 
2095 | /* ── ORACLE IDLE MATRIX ANIMATION ── */
2096 | (function(){
2097 |   var canvas = document.getElementById('oracle-matrix');
2098 |   if (!canvas) return;
2099 |   var ctx = canvas.getContext('2d');
2100 |   var chars = '01₿⚡∆Ω█▓░10₿Ξ∞◆'.split('');
2101 |   var cols, drops;
2102 | 
2103 |   function resize() {
2104 |     canvas.width = canvas.offsetWidth;
2105 |     canvas.height = canvas.offsetHeight;
2106 |     cols = Math.floor(canvas.width / 14);
2107 |     drops = Array(cols).fill(1);
2108 |   }
2109 |   resize();
2110 |   window.addEventListener('resize', resize);
2111 | 
2112 |   function draw() {
2113 |     ctx.fillStyle = 'rgba(4,5,8,0.05)';
2114 |     ctx.fillRect(0, 0, canvas.width, canvas.height);
2115 |     ctx.font = '11px monospace';
2116 |     for (var i = 0; i < drops.length; i++) {
2117 |       var char = chars[Math.floor(Math.random() * chars.length)];
2118 |       var alpha = Math.random() * 0.4 + 0.05;
2119 |       var cx = canvas.width / 2;
2120 |       var dist = Math.abs(i * 14 - cx) / cx;
2121 |       var r = Math.floor(180 + (1 - dist) * 75);
2122 |       var g = Math.floor(20 + (1 - dist) * 30);
2123 |       var b = Math.floor(40 + (1 - dist) * 20);
2124 |       ctx.fillStyle = 'rgba(' + r + ',' + g + ',' + b + ',' + alpha + ')';
2125 |       ctx.fillText(char, i * 14, drops[i] * 14);
2126 |       if (drops[i] * 14 > canvas.height && Math.random() > 0.975) drops[i] = 0;
2127 |       drops[i]++;
2128 |     }
2129 |   }
2130 | 
2131 |   var _matrixInterval = setInterval(draw, 50);
2132 | 
2133 |   window._matrixHide = function() {
2134 |     canvas.style.opacity = '0';
2135 |   };
2136 |   window._matrixShow = function() {
2137 |     /* P0-1: Subtle overlay so static avatar face stays visible during idle */
2138 |     canvas.style.opacity = '0.35';
2139 |   };
2140 | })();
2141 | 
2142 | /* ── CYBERPUNK MATRIX BACKGROUND ── */
2143 | (function(){
2144 |   var cvs=document.getElementById('bg-canvas');
2145 |   if(!cvs)return;
2146 |   var ctx=cvs.getContext('2d');
2147 |   var W,H,cols,drops,hexFrags=[];
2148 |   var matrixChars='0123456789ABCDEFabcdef₿⚡∆Ω█▓░▒╔╗╚╝║═';
2149 |   var fontSize=14;
2150 |   var scanY=-2,scanDir=1,scanTimer=0,scanInterval=15000;
2151 | 
2152 |   function resize(){
2153 |     W=cvs.width=cvs.offsetWidth;
2154 |     H=cvs.height=cvs.offsetHeight;
2155 |     cols=Math.floor(W/fontSize);
2156 |     drops=new Array(cols);
2157 |     for(var i=0;i<cols;i++) drops[i]=Math.random()*(-H/fontSize);
2158 |   }
2159 |   resize();
2160 |   window.addEventListener('resize',resize);
2161 | 
2162 |   // Hex fragments: random hex strings that fade in/out
2163 |   function spawnHex(){
2164 |     if(hexFrags.length>6) return;
2165 |     hexFrags.push({
2166 |       x:Math.random()*W,
2167 |       y:Math.random()*H,
2168 |       text:'0x'+Math.random().toString(16).substr(2,6).toUpperCase(),
2169 |       alpha:0,phase:0, // 0=fade in, 1=hold, 2=fade out
2170 |       speed:0.003+Math.random()*0.005,
2171 |       holdTime:2000+Math.random()*3000,
2172 |       holdStart:0
2173 |     });
2174 |   }
2175 | 
2176 |   var lastTime=0;
2177 |   function frame(ts){
2178 |     requestAnimationFrame(frame);
2179 |     if(!lastTime) lastTime=ts;
2180 |     var dt=ts-lastTime;
2181 |     lastTime=ts;
2182 | 
2183 |     ctx.clearRect(0,0,W,H);
2184 | 
2185 |     // 1. Falling matrix characters (sparse)
2186 |     ctx.font=fontSize+'px JetBrains Mono,monospace';
2187 |     for(var i=0;i<cols;i++){
2188 |       if(Math.random()>0.06) { // sparse: only 6% of columns draw per frame
2189 |         if(drops[i]>0){
2190 |           ctx.fillStyle='rgba(255,59,95,0.15)';
2191 |           var ch=matrixChars[Math.floor(Math.random()*matrixChars.length)];
2192 |           ctx.fillText(ch,i*fontSize,drops[i]*fontSize);
2193 |         }
2194 |       }
2195 |       drops[i]+=0.3;
2196 |       if(drops[i]*fontSize>H && Math.random()>0.98){
2197 |         drops[i]=0;
2198 |       }
2199 |     }
2200 | 
2201 |     // 2. Scan line sweep every 15s
2202 |     scanTimer+=dt;
2203 |     if(scanTimer>=scanInterval){
2204 |       scanTimer=0;
2205 |       scanY=-2;
2206 |       scanDir=1;
2207 |     }
2208 |     if(scanY>=0 && scanY<=H){
2209 |       var grad=ctx.createLinearGradient(0,scanY-8,0,scanY+8);
2210 |       grad.addColorStop(0,'rgba(255,59,95,0)');
2211 |       grad.addColorStop(0.5,'rgba(255,59,95,0.12)');
2212 |       grad.addColorStop(1,'rgba(255,59,95,0)');
2213 |       ctx.fillStyle=grad;
2214 |       ctx.fillRect(0,scanY-8,W,16);
2215 |     }
2216 |     if(scanY>=-2 && scanY<=H+10) scanY+=2;
2217 | 
2218 |     // 3. Hex fragments fade in/out
2219 |     if(Math.random()<0.008) spawnHex();
2220 |     for(var h=hexFrags.length-1;h>=0;h--){
2221 |       var frag=hexFrags[h];
2222 |       if(frag.phase===0){
2223 |         frag.alpha+=frag.speed*dt;
2224 |         if(frag.alpha>=0.2){frag.alpha=0.2;frag.phase=1;frag.holdStart=ts;}
2225 |       } else if(frag.phase===1){
2226 |         if(ts-frag.holdStart>frag.holdTime) frag.phase=2;
2227 |       } else {
2228 |         frag.alpha-=frag.speed*dt;
2229 |         if(frag.alpha<=0){hexFrags.splice(h,1);continue;}
2230 |       }
2231 |       ctx.fillStyle='rgba(255,59,95,'+frag.alpha.toFixed(3)+')';
2232 |       ctx.font='10px JetBrains Mono,monospace';
2233 |       ctx.fillText(frag.text,frag.x,frag.y);
2234 |     }
2235 |   }
2236 |   requestAnimationFrame(frame);
2237 | })();
2238 | 
2239 | function fetchTO(url,opts,ms){
2240 |   var ctrl=new AbortController();
2241 |   var id=setTimeout(function(){ctrl.abort();},ms);
2242 |   var o=opts||{};o.signal=ctrl.signal;
2243 |   return fetch(url,o).finally(function(){clearTimeout(id);})
2244 |     .catch(function(e){if(e.name==='AbortError')throw new Error('timeout');throw e;});
2245 | }
2246 | /* ── ACTION CARDS ── */
2247 | function showActionCard(card){
2248 |   var el=document.getElementById('oracle-action-card');
2249 |   var catColor = card.category==='amazon' ? '#FF9900' : card.category==='internal' ? '#6cff9f' : '#ff3b5f';
2250 |   el.innerHTML='<a href="'+card.url+'" target="_blank" rel="noopener" onclick="trackCardClick(\''+card.id+'\')" style="display:block;background:#0d0f14;border:1px solid '+catColor+';border-radius:8px;padding:14px 16px;text-decoration:none;transition:border-color 0.2s;">'
2251 |     +'<div style="font-family:\'JetBrains Mono\',monospace;font-size:9px;letter-spacing:.1em;color:'+catColor+';margin-bottom:4px;">'+card.category.toUpperCase()+'</div>'
2252 |     +'<div style="font-size:13px;font-weight:700;color:#fff;margin-bottom:4px;">'+card.title+'</div>'
2253 |     +'<div style="font-size:11px;color:rgba(255,255,255,0.55);margin-bottom:10px;">'+card.description+'</div>'
2254 |     +'<div style="font-size:11px;font-weight:600;color:'+catColor+';">'+card.cta+'</div>'
2255 |     +'</a>';
2256 |   el.style.display='block';
2257 |   el.style.opacity='0';
2258 |   setTimeout(function(){el.style.transition='opacity 0.4s';el.style.opacity='1';},100);
2259 |   setTimeout(function(){hideActionCard();},45000);
2260 | }
2261 | function showVisionSponsor(deviceName){
2262 |   if(!deviceName || deviceName==='unknown') return;
2263 |   var key=deviceName.toLowerCase();
2264 |   var match=null;
2265 |   Object.keys(VISION_SPONSOR_MAP).forEach(function(k){
2266 |     if(!match && key.indexOf(k)>=0) match=VISION_SPONSOR_MAP[k];
2267 |   });
2268 |   if(!match) return;
2269 |   showActionCard(match);
2270 | }
2271 | function hideActionCard(){
2272 |   var el=document.getElementById('oracle-action-card');
2273 |   el.style.opacity='0';
2274 |   setTimeout(function(){el.style.display='none';el.innerHTML='';},400);
2275 | }
2276 | function trackCardClick(id){
2277 |   fetch('/api/telemetry',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({event:'oracle_card_clicked',properties:{card_id:id,fingerprint:window._visitorToken||'anon'}})}).catch(function(){});
2278 | }
2279 | 
2280 | /* ── MOBILE NAV BAR ── */
2281 | (function(){
2282 |   var isMobile=/iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
2283 |   if(isMobile){
2284 |     var nb=document.getElementById('mobile-nav-bar');
2285 |     if(nb) nb.style.display='flex';
2286 |   }
2287 | })();
2288 | 
2289 | window.addEventListener('beforeunload',function(){
2290 |   try{
2291 |     var xhr=new XMLHttpRequest();
2292 |     xhr.open('POST',A+'/oracle/session/save',false);
2293 |     xhr.setRequestHeader('Content-Type','application/json');
2294 |     xhr.send(JSON.stringify({session_id:SESSION_ID}));
2295 |   }catch(e){}
2296 | });
2297 | </script>
2298 | </body>
2299 | </html>
2300 | 
```

---



---

## CYCLE 2 INSTRUCTIONS

You've now seen what the other models said. This is your final review.

1. WHAT DID THEY CATCH THAT YOU MISSED?
   Review their findings. Be honest about what you overlooked.

2. WHERE DO YOU AGREE OR DISAGREE?
   For each of their key findings: agree / disagree / partially agree + why.

3. NEW FINDINGS FROM THIS REVIEW
   Anything the combined analysis revealed that nobody caught in Cycle 1?

4. REVISED SCORES
   Update your scores from Cycle 1. Did anything change your assessment?
   | Subsystem | Cycle 1 | Cycle 2 | Why changed |

5. FINAL PRIORITY LIST
   Your definitive list of what must change before this ships.
   P0 CRITICAL | P1 HIGH | P2 MEDIUM — cite file and line numbers.

6. THE SINGLE HIGHEST-LEVERAGE CHANGE
   After seeing everything — one sentence. What matters most?

7. PRODUCTION READY?
   Yes / No / Yes with conditions. State your conditions precisely.
