Here is a complete code audit for the `oracle-forensic` feature.

### Q1 — iOS SRC SWAP ON ACTIVELY PLAYING VIDEO

*   **ANALYSIS:**
    The code initiates video playback with a "thinking" loop. In `playIntent()` (for the greeting), this happens at L1082-1083 where `vid.src` is set to `/oracle/thinking` and `vid.play()` is called. This action is tied to the initial user gesture from `requestMic()`. Subsequently, when the greeting video blob is fetched, `playVid()` is called (L1121). Inside `playVid()`, `vid.src` is immediately reassigned to the new `blobURL` (L1476).

    On iOS Safari, while a user gesture allows playback, rapidly changing the `src` of a `<video>` element that is actively playing or in the process of loading/playing can put it into an indeterminate state. iOS may not smoothly transition to the new source, resulting in a frozen frame from the previous video (or a black screen if the buffer is empty) while the audio track of the new source begins to play. This is a known fragile behavior in mobile browsers. The browser expects a more orderly transition, like `pause() -> change src -> load() -> play()`.

*   **BUG CONFIRMED:** Yes
*   **SEVERITY:** CRITICAL
*   **ROOT CAUSE:** The `<video>` element's `src` attribute is changed while it is actively playing a different video (`/oracle/thinking`). This corrupts the video element's internal state on iOS, causing the video renderer to freeze while the audio track continues.
*   **FIX:** Before setting a new `src` in `playVid`, the video element must be explicitly paused and its current source cleared. This ensures a clean state transition.

    ```javascript
    // In playVid() function, around L1474:
    // FIX: Add these two lines to reset the video element before loading a new source.
    vid.pause();
    vid.src = ''; 
    
    setOracleState('RESPONDING');
    vid.loop=false;
    vid.muted=false; 
    vid.src=url; // This should come AFTER the reset
    ```

### Q2 — BLOB URL VIDEO PLAYBACK

*   **ANALYSIS:**
    The flow `r.blob().then(blobURL)` correctly creates a blob object and a corresponding object URL (e.g., `blob:https://...`). This URL is then assigned to `vid.src`. The issue is not with the blob URL itself, but with the state of the `<video>` element when the new `src` is assigned. As identified in Q1, the video element is already busy with the `/oracle/thinking` video. When the new blob URL is assigned, the audio decoder correctly picks up the new source's audio track, but the video decoder is stuck, displaying a static frame. This sequence of events perfectly matches the user-reported bug: audio plays, but lip-sync video is frozen.

*   **BUG CONFIRirmed:** Yes
*   **SEVERITY:** CRITICAL
*   **ROOT CAUSE:** The `<video>` element is not in a receptive state for a new source due to the ongoing playback of the thinking loop, causing a playback failure where only the audio track of the new source is processed.
*   **FIX:** Same as Q1. The video element must be reset before being assigned the new blob URL.

### Q3 — RECOVERING STATE MAPPING

*   **ANALYSIS:**
    A search for "Recovering" reveals it is only set in one place:
    -   **L1544:** `setStat('Recovering\u2026','#f4c46f',true);`

    This line is inside the `vid.onerror` event handler within the `playVid` function. Therefore, the "Recovering..." state is exclusively triggered when the `<video>` element itself fires an error event.

    The state transition map is as follows:
    1.  User speaks after the broken greeting. `process()` is called.
    2.  `process()` shows the "thinking" loop (L1195-1206), which again puts the video element into an active state.
    3.  A response is fetched, and eventually `playVid()` is called with the response video URL.
    4.  Because the `<video>` element is in a broken state from the initial greeting failure (see Q1/Q2), any subsequent attempt to set a new `src` and play it also fails.
    5.  The `play()` command on the new source fails, triggering the `vid.onerror` event (L1542).
    6.  `setStat('Recovering...')` is called (L1544).
    7.  After 500ms, `_finish(false)` is called, which resolves the promise from `playVid`.
    8.  The `.finally()` block in `process()` (L1456) runs, which calls `setOracleState('LISTENING')` and ultimately `setStat('Ready', ...)`.

    The user sees "Recovering..." for a brief period before it is cleared by the `.finally` block, but the actual video playback has failed, leaving the application in a dead-end loop where no output is ever produced.

*   **BUG CONFIRMED:** Yes
*   **SEVERITY:** CRITICAL
*   **ROOT CAUSE:** The `vid.onerror` event is the sole trigger for the "Recovering..." status. This error is consistently thrown on all playback attempts after the initial greeting because the video element's state was corrupted by the faulty `src` swap.
*   **FIX:** The fix from Q1 will prevent the initial `onerror` from ever firing, thus preventing this entire failure cascade.

### Q4 — RECOVERING NEVER CLEARED

*   **ANALYSIS:**
    The premise of the question is slightly misleading. The status *is* cleared, but the process has already failed.
    1.  `vid.onerror` fires (L1542), calling `setStat('Recovering...')`.
    2.  The `onerror` handler calls `_finish(false)` (L1545).
    3.  `_finish()` resolves the `playVid` promise (L1497).
    4.  This allows the promise chain in `process()` to proceed to its `.finally()` block (L1456).
    5.  The `.finally()` block calls `setOracleState('LISTENING')` (L1459).
    6.  `setOracleState('LISTENING')` calls `setStat('Ready', ...)` (L837).

    The "Recovering..." message appears for about 500ms (the `setTimeout` in `onerror`) plus the time it takes for the promise to resolve and `.finally` to run. The user experiences a loop because the *function* of playing the video has failed. They are returned to a "Ready" state, but no response was given. When they speak again, the exact same failure occurs.

*   **BUG CONFIRMED:** Yes
*   **SEVERITY:** CRITICAL
*   **ROOT CAUSE:** The `process()` function's error handling correctly clears the UI status text but cannot recover from the underlying broken state of the `<video>` element, resulting in a functional loop of failure.
*   **FIX:** The root cause fix in Q1 prevents the error, making the recovery logic moot.

### Q5 — AUDIO/VIDEO RACE CONDITION

*   **ANALYSIS:**
    The `process()` function uses two parallel mechanisms for the response: polling/fetching for an audio-only file and a separate EventSource/polling mechanism for the final lip-synced video.
    -   When the `video_ready` event arrives, the handler explicitly stops the audio-only playback at L1354: `try{if(window._chatAudioEl){window._chatAudioEl.pause();...}}catch(e){}`.
    -   It then proceeds to call `playVid` with the full video, which contains the same audio track.
    This is not a deadlock. It's an intentional design to provide faster audio feedback while the GPU-intensive video renders. If the video arrives before the audio finishes, the audio is correctly interrupted and replaced by the video. If the audio finishes first, its `onended` handler (L1322) simply cleans up and resolves. The later arrival of the video will still trigger its handler and play the video (now with a bit of silence at the beginning if the user has already heard the audio). While complex, this flow does not appear to contain a deadlock.

*   **BUG CONFIRMED:** No
*   **SEVERITY:** N/A
*   **ROOT CAUSE:** N/A
*   **FIX:** N/A

### Q6 — SETTLED GUARD FROM THINKING LOOP

*   **ANALYSIS:**
    The premise is that `playVid` is used for the thinking loop. A code trace shows this is false.
    -   `playIntent()` sets the thinking loop `src` and calls `.play()` directly on the video element (L1082-1083).
    -   `process()` does the same (L1195-1206).
    The `playVid` function, which contains the `_settled` guard, is only ever called with the final content video URLs (greeting or response). Each call to `playVid` initializes its own local `_settled` flag (L1481). A flag from a previous call cannot affect a new call.

*   **BUG CONFIRMED:** No
*   **SEVERITY:** N/A
*   **ROOT CAUSE:** The thinking loop does not use the `playVid` function, so its `_settled` guard is not involved.
*   **FIX:** N/A

### Q7 — iOS BLOB URL + VIDEO ELEMENT ISSUES

*   **ANALYSIS:**
    -   **Blob URL Support:** iOS Safari has robust support for `fetch()` and `Blob` object URLs for `<video>` elements. A 646KB file is trivial and poses no size-related issues.
    -   **Known Issues:** The most relevant and common issue is precisely the one identified in Q1 and Q2: corrupting the element's state by swapping `src` during active playback. This is a well-documented source of bugs on mobile browsers. It often manifests as a frozen video frame, failure to play, or unexpected `error` events, all of which are observed here. A standard mitigation pattern is to halt the current video (`pause()`) and clear its source (`src = ''`) before assigning a new one.

*   **BUG CONFIRMED:** Yes
*   **SEVERITY:** CRITICAL
*   **ROOT CAUSE:** A known fragile behavior in WebKit's video implementation where rapidly changing the `src` attribute during playback leads to an unrecoverable error state for the video element.
*   **FIX:** Identical to Q1's fix. Reset the video element's state before assigning the new blob URL.

### Q8 — MUTED FLAG RACE

*   **ANALYSIS:**
    Tracing `vid.muted` assignments in the `playVid` function:
    1.  L1475: `vid.muted=false;`
    2.  L1547: `vid.muted=true;` (immediately before `.play()`)
    3.  L1552: `vid.muted=false;` (inside `tryUnmute()`, which is called by the `canplay` event listener)

    This sequence is intentional, albeit confusing. It's a common pattern to bypass mobile autoplay restrictions:
    - Start the video playback while it's muted (`.play()` is more likely to succeed).
    - Once the `canplay` event fires, indicating the video is ready, unmute it.

    While this code path is convoluted, it is not the root cause of the *frozen video*. This logic primarily affects whether audio is heard. The core problem is that the video element's renderer is frozen, which happens before this mute/unmute logic can even properly execute. The `onerror` event, which is the source of the "Recovering" bug, often fires before `canplay`.

*   **BUG CONFIRMED:** No (The code is confusing but not the root cause of the reported bugs).
*   **SEVERITY:** MEDIUM (This is poor code quality and should be simplified, but it is not the primary bug).
*   **ROOT CAUSE:** N/A for the reported bugs.
*   **FIX:** Refactor the `playVid` function to be clearer. Set `muted` once based on whether audio is expected. However, the critical fix from Q1 must be applied first.

---

### FINAL VERDICT

*   **How many CRITICAL issues confirmed?**
    Two distinct critical bugs were confirmed, but they stem from a single root cause.

*   **Root cause of the lip sync failure:**
    The core issue is a state-corruption race condition in the `<video>` element. The code attempts to set a new `src` (the greeting video) while the element is actively playing a previous one (the thinking loop). This action breaks the video element's renderer on mobile browsers like Safari, causing the video to freeze while the audio track of the new source continues to play.

*   **Root cause of the Recovering loop:**
    This is a direct downstream effect of the lip sync failure. The broken video element throws an `onerror` event. The `vid.onerror` handler sets the status to "Recovering...". Because the element is now in a permanently corrupted state, *every subsequent attempt* to play a video also triggers `onerror`, creating the "recovering" loop from the user's perspective, even though the status text is eventually cleared.

*   **Ordered fix list (most impactful first):**

    1.  **CRITICAL FIX: Stabilize the Video Element State Transition.**
        In `templates/oracle_live.html`, modify the `playVid` function to reset the video element before assigning a new source. This will prevent the state corruption that causes both reported bugs.

        **File:** `templates/oracle_live.html`
        **Location:** Around line 1474, at the beginning of the `playVid` function.

        **Change:**
        ```javascript
        function playVid(url){
          return new Promise(function(res,rej){
            console.log('[Satomi] playVid called:',url&&url.substring(0,60));
            
            // <<< START FIX >>>
            // Reset the video element to ensure a clean state before loading new media.
            vid.pause();
            vid.src = '';
            // <<< END FIX >>>
        
            setOracleState('RESPONDING');
            vid.loop=false;
            vid.muted=false; 
            vid.src=url;
            vid.style.opacity='1';
            // ... rest of the function
        ```

    2.  **REFACTOR (Recommended): Simplify Muted Logic.**
        The current mute/unmute logic in `playVid` is confusing. While not the primary cause of the bug, simplifying it would improve maintainability. The fix above makes the complex autoplay workarounds less necessary, as the element state is more stable.