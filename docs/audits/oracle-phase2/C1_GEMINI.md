Excellent. This is a comprehensive audit of the Oracle system's Phase 2 enhancements. My analysis will focus on architecture, thread safety, payload design, and frontend implementation to achieve the target latency reduction.

---

### Q1 — THINKING VIDEO ARCHITECTURE

#### DETAILED ANALYSIS
The primary video element is `video#vid` on **`oracle_live.html`, line 675**, located inside `div.video-wrap`. This wrapper provides a static background image of the avatar (`oracle_live.html`, line 292) which is visible when `#vid` has `opacity: 0`.

When `/oracle/chat` is called (via the `process` function on `oracle_live.html`, line 1060), the frontend currently enters a "PROCESSING" state. This involves:
1.  Disabling the mic and showing a spinner with status text like "Oracle thinking..." (`oracle_live.html`, lines 1066-1067, 800-803).
2.  The `#vid` element remains hidden (`opacity: 0`), so the user sees the static background image inside `.video-wrap`.
3.  The frontend starts polling for the completed video job via `setInterval` (`oracle_live.html`, line 1178) after receiving a `job_id`.
4.  Crucially, it fetches and plays the *audio* first, providing an auditory response long before the video is ready (`oracle_live.html`, lines 1098-1158).

The current "thinking" phase is static and not engaging. The user hears the Oracle but sees a still image with a spinner.

#### SPECIFIC RECOMMENDATION
The minimal change is to replace the static background image with a looping "thinking" video as soon as the request is sent.

1.  **Generation & Storage:**
    -   A new function, `generate_thinking_loop()`, should be created in `avatar_server.py`, mirroring the existing `generate_idle_loop()` (`line 1386`).
    -   This function will generate a 3-4 second video with head movement and blinks but no audio or lip movement, using `post_process_frames`.
    -   The output video should be saved to a static, predictable path like `oracle/static/oracle_thinking.mp4` during server startup. This file will be served via a static endpoint, e.g., `/oracle/thinking_loop`.

2.  **Frontend Implementation:**
    -   In `oracle_live.html`, at the beginning of the `process(text)` function (`line 1061`), immediately set the video element to play the thinking loop:
        ```javascript
        // oracle_live.html, inside process() around line 1067
        vid.src = '/static/oracle_thinking.mp4'; // Assuming static mapping in Flask
        vid.loop = true;
        vid.muted = true; // Crucial for autoplay
        vid.style.opacity = '1';
        vid.play().catch(e => console.warn("Thinking video autoplay blocked"));
        setStat('Oracle thinking...','#f4c46f',true);
        ```
    -   When the final video is ready (from polling or SSE push), the `playVid(url)` function will be called, which will replace the `src`, set `loop=false`, and handle unmuting. This sets the stage for the cross-fade addressed in Q4.

**Expected Latency Savings:** This change does not reduce the *actual* end-to-end video generation time. However, it dramatically reduces *perceived* latency. The time-to-first-visual-feedback (TTFVF) drops from ~2-4 seconds (for audio to start) to **~200ms** (for the thinking video to load and play). The user immediately sees a dynamic, "live" avatar, which makes the subsequent wait for audio and final video feel shorter and more natural.

#### IMPLEMENTATION RISK: LOW
This is a low-risk change. It involves generating one static asset and adding a few lines of client-side JavaScript. The core backend processing pipeline is unaffected.

#### POTENTIAL GOTCHAS
-   **Autoplay Policies:** The thinking video *must* be muted to autoplay reliably across all browsers, especially mobile. The audio will come from the separate audio stream later.
-   **Video File Size:** The thinking loop must be highly compressed (`crf 28+`, `preset ultrafast`) to ensure it loads and plays instantly, even on slower connections. A 3-4s 512x512 video should be under 200KB.
-   **Flicker on `src` change:** Simply changing the `src` attribute of the single `<video>` element will cause a noticeable flicker. This recommendation is the first step; a proper cross-fade (see Q4) is required for a polished UX.

---

### Q2 — SSE ARCHITECTURE FOR FLASK

#### DETAILED ANALYSIS
The current architecture uses polling (`setInterval` on `oracle_live.html`, line 1178), which is inefficient, introduces a minimum 2-second delay per state change, and adds unnecessary load to the server.

The correct pattern for implementing SSE in a multi-threaded Flask application is using a **generator function** that yields formatted event strings, wrapped in a `Response` object with `mimetype='text/event-stream'`.

The primary challenge is inter-thread communication: the `render_async` worker thread (`avatar_server.py`, line 1832) needs to push status updates to the SSE connection handler thread, which is serving a specific client request.

#### SPECIFIC RECOMMENDATION
1.  **State Management:** Use a global, thread-safe dictionary to hold communication queues for each job.
    ```python
    # avatar_server.py, near line 209
    from queue import Queue
    _sse_queues = {}
    _sse_queues_lock = threading.Lock()
    ```

2.  **Job Creation:** When a job is created in `/oracle/chat` (`line 1826`), create a `Queue` for it.
    ```python
    # avatar_server.py, inside /oracle/chat around line 1827
    job_id = uuid.uuid4().hex[:16]
    job_queue = Queue()
    with _sse_queues_lock:
        _sse_queues[job_id] = job_queue
    # ... create job in _render_jobs ...
    ```

3.  **Worker Thread (Producer):** The `render_async` function becomes the producer. It is passed the `job_queue` and puts messages into it at key stages.
    ```python
    # avatar_server.py, signature of render_async, line 1832
    def render_async(txt, jid, job_queue, src_name="default"):
        try:
            # After TTS is complete...
            job_queue.put({"event": "audio_ready"})

            # ... After video encoding is complete ...
            job_queue.put({"event": "video_ready"})

        except Exception as e:
            job_queue.put({"event": "error", "data": str(e)})
        finally:
            # Signal the end of the stream
            job_queue.put({"event": "close"})
    ```

4.  **SSE Endpoint (Consumer):** Create a new Flask route that is the consumer. It uses the generator pattern to read from the queue and `yield` to the client.
    ```python
    # avatar_server.py, new route
    import json
    
    @app.route("/oracle/stream/<job_id>")
    def oracle_stream(job_id):
        def event_stream(q):
            try:
                while True:
                    message = q.get(timeout=120) # 120s timeout
                    if message.get("event") == "close":
                        break
                    
                    event = message.get("event", "message")
                    data = json.dumps(message.get("data", {}))
                    yield f"event: {event}\ndata: {data}\n\n"
            except Empty: # from queue.Empty
                # Timeout occurred
                yield "event: error\ndata: {\"message\": \"Job timed out\"}\n\n"
            finally:
                # Clean up the queue
                with _sse_queues_lock:
                    _sse_queues.pop(job_id, None)

        with _sse_queues_lock:
            queue = _sse_queues.get(job_id)
        
        if not queue:
            return jsonify({"error": "Job not found or already complete"}), 404

        return Response(event_stream(queue), mimetype="text/event-stream")
    ```

**Expected Latency Savings:** This eliminates polling delay. Instead of waiting up to 2 seconds to learn the audio is ready, the client will be notified within milliseconds of the TTS finishing. This shaves **~1000-2000ms** of dead-air time from the "audio-first" response, making the entire interaction feel significantly faster.

#### IMPLEMENTATION RISK: MEDIUM
This introduces new complexity for state management. Thread safety is paramount. Failure to properly manage the `_sse_queues` dictionary could lead to memory leaks. The logic for timeouts and client disconnects must be robust.

#### POTENTIAL GOTCHAS
-   **Memory Leaks:** If a client disconnects and the SSE route's `finally` block doesn't execute properly, the queue for that job could be orphaned in the `_sse_queues` dictionary. The existing `_gc_worker` (`line 222`) should be augmented to periodically scan and remove old queues that don't have a corresponding active job.
-   **Proxy Buffering:** Reverse proxies like Nginx can buffer responses, which breaks SSE. The proxy configuration must include `proxy_buffering off;` and headers like `X-Accel-Buffering: no` for the SSE endpoint.
-   **"Thundering Herd" on Reconnect:** Standard SSE clients will try to reconnect on disconnect. The server must be idempotent and correctly handle a client connecting to a job that is already in progress or even complete. The queue system handles this naturally.

---

### Q3 — SSE PAYLOAD DESIGN

#### DETAILED ANALYSIS
The payload needs to be clear, concise, and provide all necessary information for the client to act. The events suggested are a good starting point. The client's state transitions depend entirely on these events.

#### SPECIFIC RECOMMENDATION
The SSE stream should use JSON-formatted data payloads for extensibility.

**Proposed Events:**
1.  **`job_created`**: Sent immediately upon connection to confirm the stream is open.
    -   Payload: `{"status": "Job created, awaiting TTS"}`
2.  **`progress`**: Sent at intermediate steps to keep the UI status text informative.
    -   Payload: `{"step": "tts", "status": "complete"}`
    -   Payload: `{"step": "lipsync", "status": "started"}`
3.  **`audio_ready`**: The most critical event for perceived latency.
    -   Payload: `{"status": "Audio ready", "url": "/oracle/job/<job_id>/audio"}`
    -   Client Action: Fetch and play the audio immediately.
4.  **`video_ready`**: The final success event.
    -   Payload: `{"status": "Video ready", "url": "/oracle/job/<job_id>"}`
    -   Client Action: Fetch the video and prepare for cross-fade.
5.  **`error`**: Signals a terminal failure.
    -   Payload: `{"status": "error", "message": "GPU_BUSY" or "Encoding failed"}`
    -   Client Action: Display an error message and revert to an idle state.
6.  **`close`**: An explicit signal from the server that the stream is ending normally.
    -   Payload: `{"status": "complete"}`
    -   Client Action: Close the `EventSource` and do not attempt to reconnect.

**Client Disconnect:**
If a client disconnects, the Flask generator on the server will raise a `GeneratorExit` exception. This should be caught in a `try...finally` block within the SSE generator function to ensure the job's queue is removed from `_sse_queues`, as described in Q2. The `render_async` worker thread will continue to completion, but its results will be discarded by the garbage collector. This is acceptable "at-least-once" behavior.

**Connection Duration:**
The connection should remain open for the duration of the job. A server-side timeout in the `queue.get(timeout=120)` call (`avatar_server.py`, LOCK_TIMEOUT) is essential to prevent connections from hanging indefinitely on a stuck job. After the final `video_ready` or `error` event, the server should send the `close` event and then terminate the stream.

#### IMPLEMENTATION RISK: LOW
Designing the payload is a low-risk task. The main risk is on the client and server to correctly implement the contract defined here.

#### POTENTIAL GOTCHAS
-   **JSON Parsing Errors:** Ensure both client and server robustly handle JSON serialization and deserialization. A malformed JSON string could break the client's state machine.
-   **Event Naming:** Use a consistent naming scheme (e.g., `snake_case`) for events and payload keys.
-   **Client-Side State:** The client-side `EventSource` implementation needs to correctly handle the `onmessage`, `onerror`, and custom event listeners for each event type. It must also correctly interpret the `close` event to prevent automatic reconnection loops.

---

### Q4 — FRONTEND CROSS-FADE

#### DETAILED ANALYSIS
A seamless transition from the "thinking" loop to the final lip-synced video is critical for a high-quality user experience. A simple `src` change on a single `<video>` element (`oracle_live.html`, line 675) will cause a flicker (a brief black or empty frame) as the browser unloads the old media and buffers the new.

#### SPECIFIC RECOMMENDATION
The most robust solution is to use **two overlapping video elements**.

1.  **HTML Structure:** Modify `div.video-wrap` to contain two video elements.
    ```html
    <!-- oracle_live.html, around line 673 -->
    <div class="video-wrap" style="position:relative;z-index:1;">
      <canvas id="oracle-matrix" ...></canvas>
      <video id="vid_thinking" playsinline muted loop ... style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;z-index:2;opacity:0;"></video>
      <video id="vid_main" playsinline ... style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;z-index:3;opacity:0;"></video>
    </div>
    ```
    CSS `transition: opacity 0.4s ease-in-out;` should be applied to both video elements.

2.  **JavaScript Logic:**
    -   **Start "Thinking":** At the beginning of `process()`, make the thinking video visible.
      ```javascript
      var vidThinking = document.getElementById('vid_thinking');
      var vidMain = document.getElementById('vid_main');
      vidThinking.src = '/static/oracle_thinking.mp4';
      vidThinking.style.opacity = '1';
      vidMain.style.opacity = '0';
      vidThinking.play();
      ```
    -   **Prepare Main Video:** When the `video_ready` SSE event is received, fetch the blob URL and prepare the main video element in the background.
      ```javascript
      // Inside SSE handler for 'video_ready'
      const mainVideoUrl = URL.createObjectURL(videoBlob);
      vidMain.src = mainVideoUrl;
      vidMain.muted = false; // The audio has been playing separately. Mute this to avoid echo. Or sync carefully. Best to play final video without its own audio track.
      vidMain.play();
      ```
    -   **Execute Cross-Fade:** Listen for an event that indicates the main video is ready to be displayed without stuttering, like `playing` or `canplaythrough`.
      ```javascript
      vidMain.addEventListener('playing', () => {
        // Fade out thinking video, fade in main video
        vidThinking.style.opacity = '0';
        vidMain.style.opacity = '1';
      }, { once: true });
      ```
    -   **Cleanup:** After the main video ends (`onended`), reset both elements for the next interaction.
      ```javascript
      vidMain.onended = () => {
          vidMain.style.opacity = '0';
          vidMain.src = '';
          vidThinking.src = '';
          // ... revert to idle state
      };
      ```

**Minimum Thinking Video Duration:**
The thinking video's purpose is to cover the time to first audio. Based on the logs and TTS provider performance, this is typically 2-4 seconds. The loop itself should be 3-4 seconds long to feel natural. The *critical UX metric* is that this loop must start playing almost *instantly* (<300ms) after the user stops speaking. The cross-fade to the real video will happen much later (5-10s), but by then the user is already engaged with the audio response, so the wait doesn't feel as long.

#### IMPLEMENTATION RISK: MEDIUM
This requires careful orchestration of DOM elements, events, and CSS transitions. Mobile browsers can be particularly finicky with video events and autoplay, requiring thorough testing. Syncing the separately-played audio with the final video can be tricky. A simpler approach is to have the final video be silent and let the initial audio play out.

#### POTENTIAL GOTCHAS
-   **Audio/Video Sync:** The simplest approach is to let the initial audio play to completion and have the final video be muted, serving only as a visual track for lip-sync. Attempting to stop the audio stream and start the video with its own embedded audio at the perfect time is very difficult and prone to glitches.
-   **Event Timing:** Relying on `canplaythrough` can be unreliable. The `playing` event is often a better indicator that frames are actually being rendered.
-   **Resource Consumption:** Using two video elements temporarily increases memory usage. Ensure the unused element's `src` is cleared after the transition to free up resources.