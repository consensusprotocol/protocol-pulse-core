Here is a ruthless audit of the provided code, focusing on readiness for a live demo.

---

### Q1 — MOST LIKELY FAILURE MODE DURING LIVE DEMO

*   **FAILURE MODE:** The initial microphone permission request fails or is silently blocked by the browser/OS, preventing the demo from starting at all. The host clicks "Speak to Satomi," and either nothing happens or a complex, technical error message appears.
*   **SEVERITY:** CRITICAL
*   **FILE:LINE:** `templates/oracle_live.html:931-987`
*   **FIX:** The current error handling is good for a developer but terrible for a live demo. It requires the host to debug their browser settings in front of an audience. A fallback mechanism is essential. If `getUserMedia` fails, the UI should not just show an error, but also present a "Continue with Text Input" button. This guarantees the demo can proceed, even with a mic issue.
    ```javascript
    // In the .catch block at line 971
    .catch(function(err){
        // ... existing error message logic ...
        // ADD THIS:
        gErr.innerHTML += '<br><button id="text-fallback-btn" style="...">Continue with Text</button>';
        document.getElementById('text-fallback-btn').onclick = function() {
            // Logic to switch to a text input-based flow
            go_with_text_input(); 
        };
    });
    ```
*   **DEMO IMPACT:** Without this fix, the demo has a significant chance of being a non-starter. The host clicks the main call-to-action, and it fails. The audience sees the host fumbling with the browser's address bar, trying to find the permission settings. Total loss of momentum and credibility from the first click.

---

### Q2 — PERCEIVED BROKENNESS

*   **FAILURE MODE:** The audio-first response creates a jarring disconnect. The user hears Satomi's voice playing while the avatar is either static or stuck in the "thinking" animation, as the lip-synced video is not yet ready. It breaks the illusion of a live, speaking intelligence and makes it feel like a cheap voice-over.
*   **SEVERITY:** HIGH
*   **FILE:LINE:** `templates/oracle_live.html:1178-1211` (audio plays) vs. `templates/oracle_live.html:1213-1300` (video is fetched/polled for later).
*   **FIX:** Prioritize a cohesive experience over raw speed for the demo. Do not play the audio stream until the video stream is also ready. The user is more patient with a slightly longer "thinking" phase than they are with a disjointed audio/visual experience.

    Change the logic to wait for *both* streams. Alternatively, a less invasive fix is to improve the status text to manage expectations:
    ```javascript
    // At line 1183
    // setStat('Speaking','#6cff9f',false);
    // INSTEAD:
    setStat('Speaking... (rendering video)','#6cff9f',false);

    // And in playVid, at line 1383
    setStat('Speaking','#6cff9f',false); // Set the final "Speaking" state only when video plays
    ```
*   **DEMO IMPACT:** The audience hears a disembodied voice while the avatar isn't moving its lips correctly. It immediately exposes the underlying tech in an unflattering way, making it feel less like magic and more like "playing an audio file while a video loads."

---

### Q3 — MOBILE-SPECIFIC FAILURE MODES

*   **FAILURE MODE:** On iOS Safari, subsequent video playback will be blocked if it's not triggered by a direct user gesture. The initial tap on "Speak to Satomi" unlocks the audio/video context, but the response video, which plays after server processing, is not tied to a new gesture. The `vid.play()` promise at line 1388 will likely be rejected.
*   **SEVERITY:** CRITICAL
*   **FILE:LINE:** `templates/oracle_live.html:1388-1394`
*   **FIX:** The `catch` block for the video play promise needs to provide a user-facing recovery mechanism. If autoplay fails, an overlay with a large "Tap to Play" icon should appear over the video. This allows the user to manually trigger the playback and salvage the experience.
    ```javascript
    // At line 1390
    p.then(function(){}).catch(function(){
      // OLD: setStat('Tap to play',...); // This is too subtle
      // NEW:
      var playOverlay = document.createElement('div');
      playOverlay.style = 'position:absolute; inset:0; background:rgba(0,0,0,0.5); display:flex; align-items:center; justify-content:center; cursor:pointer; z-index:99;';
      playOverlay.innerHTML = '<svg ... style="width:64px; height:64px; fill:white;"><path d="...play icon..."/></svg>';
      playOverlay.onclick = function() {
        vid.muted = false;
        vid.play();
        this.remove();
      };
      vid.parentElement.appendChild(playOverlay);
    });
    ```
*   **DEMO IMPACT:** The oracle processes the request, the "thinking" animation stops, and... nothing. The host is left with a static image of the avatar, while the audio may or may not play. The demo grinds to a halt on what is arguably the most important platform.

---

### Q4 — GPU CONTENTION

*   **FAILURE MODE:** The server-side Python code (not provided, but inferred) has no client-facing mechanism for handling a busy GPU. If one person starts a long video render, and the demo host immediately makes another request, the second request will be queued. The user sees the "Satomi is thinking..." animation for an unacceptably long time (potentially up to the 90-second timeout).
*   **SEVERITY:** HIGH
*   **FILE:LINE:** `templates/oracle_live.html:1121` (The client-side `fetchTO` call with a 90,000ms timeout).
*   **FIX:** The backend server MUST implement a lock or semaphore for the GPU pipeline. If the GPU is busy, the `/oracle/chat` endpoint should immediately respond with an `HTTP 429 Too Many Requests` or `503 Service Unavailable` status, including a `Retry-After` header.

    The client-side JavaScript must be updated to handle this specific status code gracefully, instead of just timing out.
    ```javascript
    // In the fetchTO call at line 1121
    .then(function(r){
        if (r.status === 429 || r.status === 503) {
            setStat('Satomi is busy. Please wait...', '#f4c46f', true);
            // Implement a retry mechanism based on Retry-After header
            throw new Error('GPU_BUSY');
        }
        if(!r.ok) throw new Error('HTTP '+r.status);
        // ... rest of the logic
    })
    ```
*   **DEMO IMPACT:** The host asks a question and is met with a "thinking" animation that lasts for over a minute. The host will be forced to say "it must be a very complex question," but the audience will correctly perceive it as a system hang. It completely destroys the illusion of a real-time, responsive intelligence.

---

### Q5 — WORST UX MOMENT

*   **FAILURE MODE:** The "auto-submit on silence" feature in the speech recognition flow is ambiguous and lacks clear feedback. After the user stops talking, there's a brief, awkward silence where nothing happens. The UI still shows "tap to send" but then automatically sends the request anyway after 300ms. This feels unpredictable and out of the user's control.
*   **SEVERITY:** MEDIUM
*   **FILE:LINE:** `templates/oracle_live.html:1413-1417` (The `recognition.onend` handler).
*   **FIX:** Provide immediate and explicit feedback when silence is detected. When `onend` fires, immediately change the status.
    ```javascript
    // In recognition.onend at line 1413
    recognition.onend=function(){
      setRec(false);
      var _pend = pending;
      if (_pend.trim() && !busy) {
        // ADD THIS: Provide immediate feedback
        setStat('Processing your request...', '#f4c46f', true); 
        setTimeout(function(){ 
            process(_pend);
            pending='';
        }, 100); // Shorten or remove delay
      }
    };
    ```
    This removes the awkward pause and confirms to the user that their speech was received and is now being processed, bridging the gap between listening and thinking states.
*   **DEMO IMPACT:** The host finishes speaking, and for a moment, nothing happens. They might instinctively tap the mic button (as the UI suggests) just as the system auto-submits, creating a confusing, clunky interaction. It feels less like a polished product and more like a tech demo with rough edges.

---

### Q6 — AMATEUR VISUAL ELEMENTS

*   **FAILURE MODE:** The massive block of inline styles for the security overlay (`#vision-security-overlay`) and mobile nav bar (`#mobile-nav-bar`) is a major red flag. It screams "hacked together" and is difficult to maintain. The security alert itself, with its default emoji and aggressive red background, looks more like a browser malware popup than a sophisticated part of the UI.
*   **SEVERITY:** MEDIUM
*   **FILE:LINE:** `templates/oracle_live.html:569-623`
*   **FIX:** Abstract all inline styles into the main `<style>` block and give them proper class names. Redesign the security alert to be thematically consistent with the rest of the cyberpunk aesthetic. Use the established color palette and typography (`JetBrains Mono`, etc.) instead of generic system fonts and harsh colors.
    ```css
    /* Instead of inline styles */
    #vision-security-overlay {
      display: flex; /* Initially 'none' */
      position: fixed;
      inset: 0;
      /* ... all other styles from the inline block ... */
    }
    .security-alert-icon { font-size: 64px; /* etc. */ }
    ```
*   **DEMO IMPACT:** When the (very cool) vision security feature is shown, the UI quality suddenly drops. The audience, especially designers or product people, will notice the inconsistency immediately. It cheapens an otherwise impressive feature.

---

### Q7 — HIGHEST IMPACT SINGLE CHANGE

*   **FAILURE MODE:** The `merch.html` page uses a `<canvas>` element for a particle effect that runs constantly, consuming significant CPU/GPU resources even when the tab might be in the background. This is unnecessary and can degrade performance on the user's machine, especially on laptops, leading to fan spin-up and battery drain. The animation is not paused when the tab is hidden.
*   **SEVERITY:** HIGH
*   **FILE:LINE:** `templates/merch.html:1470`
*   **FIX:** The code attempts to add a `visibilitychange` listener at line 1483, which is excellent. However, this is a very complex and resource-intensive animation for what is essentially a background effect on a store page. The highest impact change for demo quality and general performance is to **replace the entire JS-driven canvas animation with a much lighter-weight CSS/SVG alternative.** A simple animated gradient or a CSS particle animation would achieve 90% of the effect with 10% of the performance cost, ensuring the page is always smooth and responsive during the demo.
    If keeping the canvas is non-negotiable, ensuring the `visibilitychange` listener is correctly implemented and works across browsers is paramount. The current implementation is a good start but is still a high performance risk.
*   **DEMO IMPACT:** The host has the merch tab open in the background. Their laptop fan starts spinning loudly during the *oracle* demo because the hidden merch tab is pegging a CPU core. This is distracting and unprofessional. The page itself might feel sluggish if the main thread is busy with the canvas animation.

---

### Q8 — SILENT NETWORK FAILURES

*   **FAILURE MODE:** The `EventSource` (SSE) connection for video readiness can fail silently. The `onerror` handler at line 1262 correctly closes the source and tries to fall back to polling. However, if the polling itself also fails (e.g., the server is down or the network is gone), the `setInterval` at line 1273 will run for its full 60 attempts (2 minutes) with no user feedback other than the endless thinking loop. The `catch` block for the `fetch` inside the poll is empty.
*   **SEVERITY:** HIGH
*   **FILE:LINE:** `templates/oracle_live.html:1293`
*   **FIX:** The empty `.catch(function(){})` is unacceptable. It must handle the failure. After a few failed polling attempts (e.g., 3-5), it should give up, inform the user, and reset the state.
    ```javascript
    // Inside _startPollFallback at line 1273
    var pollVideo=setInterval(function(){
      pollAttempts++;
      fetch(...)
        .then(...)
        .catch(function(err){ // DON'T LEAVE THIS EMPTY
          console.warn('Polling attempt ' + pollAttempts + ' failed.');
          if (pollAttempts > 5) { // Give up after 5 tries
            clearInterval(pollVideo);
            setStat('Connection lost. Please try again.', '#ff3b5f', false);
            setBusy(false);
            setOracleState('LISTENING');
          }
        });
      //...
    },2000);
    ```
*   **DEMO IMPACT:** The network connection is flaky. The SSE stream drops, and the polling fallback starts. The network then dies completely. The user is stuck watching a "thinking" animation for two full minutes with zero indication of what's wrong. The application appears completely frozen, forcing a page reload to fix.

---

### FINAL VERDICT

*   **How many CRITICAL issues did you find?**
    *   I found **2 CRITICAL** issues that could stop the demo cold (Q1: Mic Permissions, Q3: Mobile Video Autoplay).

*   **Is this demo-ready today?**
    *   **No. Absolutely not.** There is a high probability of a complete stall or a severely degraded experience, especially on mobile or with minor network issues. The core user flow has several points of failure that would be embarrassing in a live demo.

*   **Top 3 must-fix items before Friday:**
    1.  **Mic Permission Fallback (Q1):** The demo *must* have a way to proceed if the mic fails. Implement a text input fallback immediately. This is the single most important change to ensure the demo can actually happen.
    2.  **Mobile Video Autoplay Recovery (Q3):** Add a "Tap to Play" overlay if the response video fails to autoplay on mobile. A large portion of the audience will likely be watching on their phones.
    3.  **Graceful Network/GPU Failure (Q4 & Q8):** The client must handle server-busy (429/503) and network-down states. Replace the endless "thinking" spinner on network failure with a clear error message and a state reset. This prevents the perception of a frozen application.