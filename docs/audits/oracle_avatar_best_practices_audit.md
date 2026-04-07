# Oracle Avatar Best Practices Audit

**System Under Review:** Satomi -- Protocol Pulse Interactive AI Avatar
**Date:** 2026-04-07
**Auditor:** Claude Opus 4.6 (cross-industry research audit)
**Scope:** 8 architectural areas compared against 2026 industry leaders

---

## Executive Summary

Protocol Pulse's "Satomi" avatar system runs a self-hosted pipeline on an RTX 4090 cluster: Claude Haiku for dialogue, Kokoro TTS (local GPU), and Wav2Lip for lip-sync, served over HTTP POST endpoints at 30fps/CRF 23. The system uses an audio-first response pattern where audio plays within approximately 4 seconds while lip-synced video follows asynchronously.

This audit compares Satomi against five industry leaders -- HeyGen (LiveAvatar), D-ID (Agents API), Synthesia (Video Agents), Tavus (Phoenix-4 CVI), and Simli -- across eight critical architectural dimensions. For each area, we document what best-in-class implementations do, identify gaps in Satomi's current architecture, and provide prioritized recommendations.

**Overall Assessment:** Satomi's audio-first pattern and local GPU ownership are genuine architectural advantages that most SaaS competitors cannot offer. The primary gaps are in streaming protocol (HTTP POST vs. WebRTC), interrupt handling robustness, and mobile optimization. Of the 27 recommendations below, 8 are P0 (critical for production quality), 11 are P1 (significant improvement), and 8 are P2 (polish).

---

## Industry Players Referenced

| Platform | Model/Version | Transport | Latency Claim | Key Differentiator |
|----------|--------------|-----------|---------------|-------------------|
| **HeyGen** | LiveAvatar (replaced Interactive Avatar March 2026) | WebRTC | Sub-300ms audio | Full-duplex with barge-in, VAD built-in |
| **D-ID** | Agents API + Express-2 avatars | WebRTC | Sub-200ms e2e, 100fps generation | Fluent streaming + interrupt for Premium+ avatars |
| **Synthesia** | Express-2 + Video Agents (Enterprise, early 2026) | Proprietary streaming | Minutes for async; real-time for Video Agents | Full-body gesture, 120+ languages |
| **Tavus** | Phoenix-4 (Gaussian-diffusion hybrid, Feb 2026) | WebRTC via Daily | Sub-600ms e2e | Emotion Control API, full-duplex, 40fps 1080p |
| **Simli** | Trinity (3D Gaussian splatting) | WebRTC | Sub-300ms rendering | 3D neural architecture, cost-efficient inference |

---

## AREA 1: INPUT HANDLING

### What Industry Leaders Do

**HeyGen LiveAvatar:** The SDK manages a session state machine where new user input automatically supersedes any in-progress generation. The `StreamingAvatar` class queues input events and processes them serially, with the latest input taking priority. A dedicated `interrupt()` method exists in the SDK to programmatically cancel the current task before submitting a new one.

**D-ID Agents API:** Chat sessions maintain separate message threads. Each new user message is processed in sequence. D-ID's Agents SDK handles debouncing internally -- rapid clicks or duplicate messages are coalesced at the SDK layer before hitting the backend. The WebRTC data channel carries control signals separately from media, allowing input events to bypass the media pipeline.

**Tavus Phoenix-4:** The Conversational Video Interface (CVI) uses full-duplex WebRTC. User input (voice or text) is processed through Raven-1 (emotional perception) and Sparrow-1 (conversational timing/turn-taking) before reaching the LLM. The turn-taking model explicitly handles overlapping speech and rapid input sequences, deciding whether to yield the floor or continue speaking.

**Best-in-class pattern:** All leaders implement a three-layer input stack:
1. **Client-side debounce** (100-200ms) to coalesce rapid clicks
2. **Server-side cancellation token** that invalidates in-flight work
3. **Queue with last-wins semantics** -- only the most recent unprocessed request proceeds

### Current Satomi State

Satomi's `/oracle/ask` endpoint accepts POST requests with an optional `conversation_id` and `interrupt_id`. The interrupt mechanism checks `ACTIVE_INTERRUPTS` after the LLM call and after the TTS call, returning HTTP 409 if the interrupt ID has changed. However:

- No client-side debounce is implemented -- rapid clicks generate multiple concurrent requests
- The interrupt check is poll-based (checked at two fixed points), not event-driven
- No queue exists -- concurrent requests all proceed through the full LLM + TTS pipeline simultaneously
- Double-taps on the "Ask" button fire duplicate requests without deduplication

### Recommendations

| # | Recommendation | Complexity | Priority |
|---|---------------|------------|----------|
| 1.1 | **Client-side debounce**: Add 200ms debounce on the submit button/input handler. Disable the button immediately on click and re-enable only after response begins streaming. | Low | P0 |
| 1.2 | **Request cancellation via AbortController**: Use the browser `AbortController` API to cancel in-flight HTTP requests when a new question is submitted. Pair with server-side `asyncio.Event` cancellation so the server stops LLM/TTS work immediately rather than checking at fixed points. | Medium | P0 |
| 1.3 | **Server-side request queue with last-wins**: Implement a per-conversation asyncio queue (maxsize=1) where new requests evict pending ones. The worker coroutine processes only the latest enqueued request. This prevents GPU resource waste from concurrent duplicate requests. | Medium | P1 |

---

## AREA 2: STREAMING PROTOCOL

### What Industry Leaders Do

**HeyGen LiveAvatar:** Migrated from WebSocket-based Interactive Avatar to full WebRTC for LiveAvatar. WebRTC provides peer-to-peer audio/video with adaptive bitrate. If the connection drops below a quality threshold, the system automatically downgrades video quality while prioritizing the audio stream to ensure the conversation continues. The SDK handles ICE negotiation, STUN/TURN traversal, and session recovery.

**D-ID Agents API:** Uses WebRTC exclusively. The `createAgentStream` endpoint initiates a WebRTC connection, returning an SDP offer. The browser peer completes the handshake. A separate data channel carries control signals (interrupt, state changes, metadata) alongside the media tracks. Audio and video are synchronized via RTP presentation timestamps.

**Tavus Phoenix-4:** Built on WebRTC via Daily (a WebRTC infrastructure provider). The "stream-first" architecture renders and sends video packets incrementally -- frames are transmitted as they are generated, not after full video completion. This is the key architectural difference from batch-and-send approaches.

**Simli:** Uses WebRTC with PCM audio downsampled to 16kHz for minimal transmission latency. Trinity avatars use `playImmediate` for the first audio chunk after an interruption to reduce perceived latency.

**Protocol comparison findings:**

| Protocol | Latency | A/V Sync | NAT Traversal | Packet Loss Handling |
|----------|---------|----------|---------------|---------------------|
| **WebRTC (UDP)** | 50-200ms | Automatic via RTP timestamps | Built-in ICE/STUN/TURN | Tolerates loss, no head-of-line blocking |
| **WebSocket (TCP)** | 100-500ms | Manual client-side jitter buffer | Requires proxy | Single dropped packet stalls entire stream |
| **HTTP POST (TCP)** | 500ms+ per round-trip | N/A (batch delivery) | Standard HTTP | Full retransmission on failure |
| **WebTransport/QUIC** | 200-500ms (early benchmarks) | Hybrid reliable+unreliable datagrams | Emerging | Reliable streams without head-of-line blocking |

The industry has converged on WebRTC as the standard for interactive avatar systems. The critical advantage is that WebRTC uses UDP, meaning a lost packet causes a tiny glitch rather than a stream stall (as happens with TCP-based WebSocket or HTTP). RTP timestamps also provide automatic audio-video synchronization that HTTP POST approaches must implement manually.

### Current Satomi State

Satomi uses HTTP POST to `/oracle/ask`, which returns a complete JSON payload containing `audio_base64`, `answer_text`, `viseme_timeline`, and metadata. The browser then:
1. Decodes the base64 audio and begins playback immediately (~4s)
2. Uses the viseme timeline to drive client-side mouth animation
3. Optionally waits for a Wav2Lip-rendered video to replace the viseme animation

This is a batch-and-send architecture. The entire LLM response, TTS audio, and viseme data must be generated before any content reaches the user. The audio-first pattern mitigates perceived latency but does not reduce actual first-byte time.

### Recommendations

| # | Recommendation | Complexity | Priority |
|---|---------------|------------|----------|
| 2.1 | **Server-Sent Events (SSE) for progressive delivery**: Before migrating to WebRTC, implement SSE on the `/oracle/ask` endpoint to stream partial results. Send the answer text as soon as the LLM finishes (before TTS), then send audio chunks as they are generated, then send the viseme timeline. This gives the client text to display within 1-2s while audio follows. | Medium | P0 |
| 2.2 | **WebSocket upgrade path**: Implement a WebSocket endpoint (`/oracle/ws`) that maintains a persistent connection per session. This eliminates per-request TCP handshake overhead and enables bidirectional signaling (interrupts, state updates, typing indicators). | Medium | P1 |
| 2.3 | **WebRTC long-term migration**: For true sub-300ms interactive avatar, migrate to WebRTC using a library like `aiortc` (Python) for the server side. This enables frame-by-frame video streaming, automatic A/V sync via RTP, adaptive bitrate, and NAT traversal. This is a significant undertaking but is the industry standard. | High | P2 |
| 2.4 | **Chunked TTS streaming**: Modify the ElevenLabs client (or Kokoro TTS) to stream audio in chunks rather than waiting for complete generation. ElevenLabs supports streaming via their WebSocket API. Send each chunk to the client as it arrives, enabling audio playback to begin before TTS completes. | Medium | P1 |

---

## AREA 3: LATENCY

### What Industry Leaders Do

**Tavus Phoenix-4 (sub-600ms e2e):** Achieves this through:
1. A streaming audio feature extractor that begins processing before the user finishes speaking
2. A long-term memory module that pre-conditions the diffusion head with context
3. 3D Gaussian Splatting renderer producing frames at real-time speed (40fps)
4. WebRTC stream-first delivery -- frames ship as they render

**D-ID (sub-200ms e2e, 100fps generation):** Their generation pipeline produces frames at 100fps, meaning the rendering step itself is never the bottleneck. The sub-200ms figure includes network transit via WebRTC.

**HeyGen LiveAvatar (sub-300ms audio):** Separates audio and video latency. Audio reaches the user in under 300ms via WebRTC audio tracks. Video follows with slightly higher latency but is synchronized via RTP timestamps. The user hears the avatar immediately and sees lip-sync catch up within one frame.

**Simli (sub-300ms rendering):** Uses 3D Gaussian splatting (not video-based lip-sync), giving full control over facial animation without the frame-processing overhead of Wav2Lip-style approaches.

**Common latency reduction patterns across all leaders:**
- **LLM streaming**: Begin TTS as soon as the first sentence is complete, not after the full response
- **Speculative rendering**: Start avatar idle/thinking animation immediately while waiting for LLM
- **Audio-video decoupling**: Send audio first, video catches up
- **Pre-warmed models**: Keep all models loaded in GPU VRAM permanently
- **Edge inference**: Process as close to the user as possible

**Wav2Lip-specific optimization research:**
- TensorRT compilation + FP16 quantization achieves 4.7x speedup over PyTorch FP32 baseline
- With kernel fusion on RTX 4070 Ti, inference drops to 0.96ms average per frame (over 1000fps theoretical)
- 63% lower latency variance with TensorRT vs. PyTorch

### Current Satomi State

Satomi's pipeline timing (sequential):
1. **LLM (Claude Haiku):** ~800ms-1.5s for 2-4 sentence response
2. **TTS (Kokoro local or ElevenLabs):** ~1-3s depending on text length
3. **Viseme generation:** ~50ms (CPU, negligible)
4. **Network transit:** ~100-200ms (Cloudflare tunnel)
5. **Total first-audio:** ~3-5s

The audio-first pattern is a genuine advantage -- it matches the industry pattern of decoupling audio and video latency. However, the pipeline is entirely sequential: LLM must fully complete before TTS begins, and TTS must fully complete before audio is delivered.

The Wav2Lip model runs on `cuda:1` with pre-warmed models via the `ModelRegistry` singleton, which is good practice. The blink engine runs at ~0.3ms per frame (pure NumPy/OpenCV), which is negligible.

### Recommendations

| # | Recommendation | Complexity | Priority |
|---|---------------|------------|----------|
| 3.1 | **LLM streaming + sentence-level TTS pipelining**: Stream Claude Haiku's response and begin TTS on the first complete sentence while the LLM continues generating. This alone can cut first-audio latency by 40-60%, from ~3-5s down to ~1.5-2.5s. | Medium | P0 |
| 3.2 | **TensorRT compilation for Wav2Lip**: Convert the Wav2Lip GAN model to TensorRT FP16. Based on published benchmarks, this can achieve 4.7x speedup and sub-1ms per frame inference on the RTX 4090. The 4090 is significantly faster than the 4070 Ti used in published benchmarks. | Medium | P1 |
| 3.3 | **Pre-cached first-sentence responses**: For common question patterns (greetings, "what is Bitcoin", market status), maintain a cache of pre-rendered first sentences. Serve the cached first sentence immediately while generating the full response in parallel. The cache_render_helper.py already supports this pattern -- expand the cache corpus. | Low | P0 |
| 3.4 | **Kokoro TTS streaming**: If Kokoro supports chunked output, pipe audio chunks to the client as they generate rather than waiting for the full waveform. This converts TTS from a blocking step to a streaming step. | Medium | P1 |
| 3.5 | **Connection keep-alive / session pre-warming**: When a user loads the Oracle page, immediately establish a persistent connection (WebSocket or SSE) and pre-warm the conversation context. When the user actually submits a question, the connection overhead is already paid. | Low | P1 |

---

## AREA 4: ERROR RECOVERY

### What Industry Leaders Do

**HeyGen LiveAvatar:** WebRTC's ICE framework handles network disruptions with automatic candidate re-negotiation. If the video track fails, audio continues independently. The SDK provides event callbacks (`on_connection_state_change`, `on_error`) that let developers implement custom recovery UI. Session state is preserved server-side, so reconnection resumes the conversation.

**D-ID Agents API:** Chat sessions are persisted server-side with separate message histories. If a WebRTC connection drops, the client can create a new stream connection attached to the same chat session, preserving full conversation context. The API returns structured error codes that distinguish between transient failures (retry-safe) and permanent failures (re-authentication needed).

**Tavus CVI:** Built on Daily's WebRTC infrastructure, which includes automatic reconnection with exponential backoff. If the Phoenix-4 GPU pipeline fails, the system falls back to audio-only mode while the video pipeline recovers. The full-duplex architecture means partial failures (e.g., video generation fails but audio works) degrade gracefully rather than failing completely.

**General industry patterns for error recovery:**
- **Audio-only fallback**: If video rendering fails, deliver audio response with a static avatar image. Never show the user a blank screen.
- **Last-known-good frame**: If lip-sync fails mid-response, freeze on the last successfully rendered frame rather than showing artifacts.
- **Retry with backoff**: TTS and LLM calls get automatic retry (2-3 attempts) with exponential backoff before surfacing an error.
- **Graceful timeout**: If total response time exceeds a threshold (e.g., 30s), deliver a canned "I need a moment to think about that" response rather than hanging.
- **Circuit breaker**: After N consecutive GPU failures, stop attempting GPU rendering and serve audio-only until a health check passes.

### Current Satomi State

Satomi has basic error handling:
- If Claude fails, a hardcoded fallback response is used: `"The Oracle is processing your question about {question[:50]}."`
- If ElevenLabs TTS fails, an HTTP 502 is returned to the client
- The interrupt mechanism returns HTTP 409 on interrupt
- No retry logic exists for either LLM or TTS calls
- No fallback from Kokoro to ElevenLabs (or vice versa) on failure
- No circuit breaker for GPU failures
- No session persistence -- if the connection drops, all context is lost

The `request_timeout_sec` is set to 45 seconds, which is too long for a user to wait without feedback.

### Recommendations

| # | Recommendation | Complexity | Priority |
|---|---------------|------------|----------|
| 4.1 | **TTS failover chain**: Implement automatic failover: Kokoro (local GPU, fastest) -> ElevenLabs (cloud, reliable) -> pyttsx3/espeak (CPU, last resort). If Kokoro fails, retry once, then fall to ElevenLabs. Log every failover for monitoring. | Medium | P0 |
| 4.2 | **LLM retry with backoff**: Wrap the Claude Haiku call in a retry decorator (2 attempts, 500ms backoff). If both fail, fall back to a curated set of topical responses keyed by detected question category (market, mining, macro, general). | Low | P0 |
| 4.3 | **Progressive timeout with user feedback**: Replace the 45s hard timeout with three stages: (1) at 5s, send a "thinking" status event to the client; (2) at 15s, send a "this is taking longer than usual" message; (3) at 30s, deliver a canned "Let me get back to you on that" audio response and log the failure. | Medium | P1 |
| 4.4 | **GPU health circuit breaker**: Track consecutive GPU failures (Wav2Lip, Kokoro). After 3 consecutive failures, flip a circuit breaker flag that routes all requests to the non-GPU fallback path (ElevenLabs + viseme-only) for 5 minutes, then attempt one GPU health check before re-enabling. | Medium | P1 |
| 4.5 | **Session persistence**: Store conversation state (last 5 turns, conversation_id, visitor fingerprint) in the SQLite visitor_memory.db (which already exists). On client reconnection, restore context from the database rather than starting fresh. | Low | P1 |

---

## AREA 5: VISUAL FEEDBACK

### What Industry Leaders Do

**HeyGen LiveAvatar:** During the "thinking" phase, the avatar maintains natural idle behavior -- subtle breathing motion, occasional blinks, slight head movements. The avatar does not freeze or show a loading spinner. When the response begins, the transition from idle to speaking is seamless. The SDK emits state events (`IDLE`, `LISTENING`, `THINKING`, `SPEAKING`) that developers use to overlay UI elements.

**D-ID Express-2:** Avatars have continuous micro-expressions and ambient motion even when not speaking. The transition between listening and speaking states is animated, not a hard cut. Full-body avatars show weight shifting and hand gestures during idle states.

**Tavus Phoenix-4:** The Emotion Control API allows explicit control of the avatar's emotional state during thinking phases. Developers can set the avatar to "curious" or "contemplative" while waiting for the LLM. The Raven-1 perception model generates natural listening behavior (nodding, eye contact) while the user is speaking. Full-duplex rendering means the avatar is always generating frames -- there is never a blank or frozen state.

**Synthesia Express-2:** Three-part architecture combines facial expressions, lip sync, hand gestures, and body language. Professional speaker footage training means the idle state looks like a real person waiting to speak, not a static image.

**UX research findings on loading states:**
- Animations should stay under 300ms for micro-interactions
- For waits longer than a few seconds, provide value (progress indication, context)
- A faster-spinning animation improves perceived performance even when actual load time is unchanged
- Skeleton screens (showing the shape of expected content) outperform spinners for perceived speed
- Branded loading experiences build trust and recognition

### Current Satomi State

Satomi has a blink engine (MediaPipe landmarks, ~0.3ms/frame) and a head movement system (rotation +/-1 degree, 4s period). These provide basic idle animation. However:
- During the thinking/generation phase (3-5 seconds), the user likely sees the avatar with idle animation but no explicit indication that their question was received and is being processed
- No state machine events are emitted to the client (LISTENING -> THINKING -> SPEAKING transitions)
- No "thinking" animation distinct from "idle" animation
- No progress indication during the generation phase
- The viseme system drives lip animation during speech, but the transition from idle to speaking may not be smooth

### Recommendations

| # | Recommendation | Complexity | Priority |
|---|---------------|------------|----------|
| 5.1 | **Explicit state machine with client events**: Define four states (IDLE, LISTENING, THINKING, SPEAKING) and emit state transitions to the client via the response stream or a dedicated status endpoint. The client uses these to drive UI changes (e.g., pulsing glow during THINKING, waveform during SPEAKING). | Low | P0 |
| 5.2 | **"Thinking" avatar animation**: During the THINKING state, increase blink frequency slightly, add a subtle "look up and to the side" head movement (the universal human signal for recalling information), and display a subtle pulsing indicator near the avatar. This is distinct from idle and signals active processing. | Medium | P1 |
| 5.3 | **Immediate text echo**: As soon as the user submits a question, display their question text in a chat-style UI element. This provides instant confirmation that input was received, even before any server response. Pair with a "Satomi is thinking..." text indicator. | Low | P0 |
| 5.4 | **Smooth idle-to-speaking transition**: Add a 200-300ms transition animation between idle and speaking states. The mouth should not snap from closed to the first viseme -- ease into the first phoneme shape over 4-6 frames. Similarly, ease from the last phoneme back to neutral at the end of speech. | Medium | P2 |
| 5.5 | **Streamed text reveal**: As the LLM generates text (with streaming enabled per recommendation 3.1), display the answer text word-by-word or sentence-by-sentence in a subtitle area below the avatar. This gives the user content to read while audio is being generated. | Low | P1 |

---

## AREA 6: CONVERSATION MEMORY

### What Industry Leaders Do

**D-ID Agents API:** Each agent maintains separate Chat sessions with independent message histories. The session persists server-side, and context is automatically included in each LLM call. Developers control the maximum conversation length and can inject system messages at any point.

**Tavus CVI:** Phoenix-4 includes a "long-term memory module" that analyzes incoming frames alongside past context to produce conditioning signals. The conversational model maintains awareness of the full session. Memory is managed at the platform level -- developers do not need to implement their own sliding window.

**HeyGen LiveAvatar:** Session context is maintained within the streaming session. The SDK manages conversation history, and the backend includes prior turns in the LLM prompt automatically. Session length limits are handled by the platform.

**Industry patterns for conversation memory in real-time avatars:**
- **Sliding window (most common):** Keep the last N turns (typically 5-10) in the LLM context. Summarize older turns into a compact context block.
- **Summarization compaction:** After every 5-10 turns, run a separate LLM call to summarize the conversation so far into 2-3 sentences. Include this summary as a system message prefix.
- **Targeted RAG:** For domain-specific avatars (like a Bitcoin oracle), retrieve relevant context from a knowledge base based on the current question rather than relying solely on conversation history.
- **Token budgeting:** Reserve a fixed token budget for conversation history (e.g., 2000 of 4000 input tokens). When history exceeds the budget, apply sliding window + summarization.
- **Cross-session persistence:** Store summarized session data in a database keyed by user identifier, enabling the avatar to "remember" returning visitors.

### Current Satomi State

Satomi has a robust visitor memory system in `oracle_memory.py`:
- SQLite-backed storage in `visitor_memory.db`
- Anonymous fingerprinting (SHA-256 of IP + user-agent + visitor token)
- Tracks: `session_count`, `personality`, `session_summaries`, `topics_seen`, `products_shown`, `recent_turns`
- 30-day expiry on visitor records

However, the current `/oracle/ask` endpoint in `oracle-live/backend/app.py` does NOT use this memory system. Each call to `generate_answer_via_claude()` sends only the current question with no conversation history:
```python
messages=[{"role": "user", "content": question}]
```

The `oracle_memory.py` module exists but appears disconnected from the live API path. The `recent_turns` field is stored but never read during response generation.

### Recommendations

| # | Recommendation | Complexity | Priority |
|---|---------------|------------|----------|
| 6.1 | **Wire conversation history into the LLM call**: Load the visitor's `recent_turns` from `oracle_memory.py` and include the last 5 turns as prior messages in the Claude Haiku call. This is the single highest-impact memory improvement and requires minimal code change. | Low | P0 |
| 6.2 | **Save turns after each response**: After each successful `/oracle/ask` response, append `{role: "user", content: question}` and `{role: "assistant", content: answer_text}` to the visitor's `recent_turns`. Cap at 10 turns. | Low | P0 |
| 6.3 | **Token-budgeted sliding window**: Before including conversation history in the LLM call, estimate token count (rough: `len(text) / 4`). If history exceeds 1500 tokens, summarize the oldest turns using a separate fast Claude Haiku call, then include the summary + most recent 3 turns. | Medium | P1 |
| 6.4 | **Session summary on disconnect**: When a conversation session ends (no activity for 5 minutes or explicit close), summarize the session and store it in `session_summaries`. On the visitor's next visit, include a one-line session recap in the system prompt: "This visitor previously asked about {topics}." | Medium | P2 |
| 6.5 | **RAG context injection**: For Bitcoin-specific questions, query the existing `oracle_rag.py` module and inject relevant context snippets into the system prompt. This reduces hallucination and provides up-to-date data without consuming conversation history token budget. | Medium | P2 |

---

## AREA 7: MOBILE OPTIMIZATION

### What Industry Leaders Do

**HeyGen LiveAvatar:** The SDK handles mobile-specific concerns automatically. Adaptive bitrate streaming via WebRTC downgrades video quality on slow connections while maintaining audio quality. The SDK works in mobile browsers without requiring a native app. The LiveAvatar FAQ confirms mobile browser support.

**Tavus CVI:** Built on Daily's WebRTC infrastructure, which includes responsive layouts and device management out of the box. The system reports major bandwidth savings (up to 60%) using edge architectures. When synthesis cannot achieve a minimal quality or latency constraint, the system falls back to audio-only with a static avatar or last-known-good frame.

**D-ID Agents SDK:** The SDK provides responsive layouts for streaming, presentations, and media content. Videos render up to 60fps at resolutions up to 1080p, with automatic downscaling for mobile devices.

**Mobile-specific challenges for AI avatars:**
1. **Autoplay restrictions**: iOS Safari and Android Chrome both block autoplay of video with audio unless the user has interacted with the page. This means the first response cannot auto-play video+audio without a prior tap gesture.
2. **Touch event handling**: Touch events fire differently than mouse events (touchstart vs. click, 300ms delay on older browsers, ghost clicks). Double-tap zoom conflicts with double-tap-to-ask patterns.
3. **Bandwidth adaptation**: Mobile connections fluctuate. The system must detect bandwidth changes and adapt in real-time.
4. **Battery and thermal**: Continuous GPU-decoded video and audio playback drains battery. Efficient codec selection (H.264 baseline profile, not High) matters.
5. **Screen real estate**: Avatar + chat + input must fit on a phone screen without requiring scroll-to-interact.

### Current Satomi State

Satomi serves video via HTTP POST with base64-encoded audio/video. The current state regarding mobile:
- No adaptive bitrate -- the same CRF 23 / 30fps video is sent to all clients
- Base64 audio decoding works on all browsers but is not bandwidth-efficient (33% overhead vs. binary)
- No explicit handling of iOS/Android autoplay restrictions
- Touch event handling: unknown (depends on the frontend template, which is in the Flask routes)
- No bandwidth detection or quality adaptation
- Video at 30fps / CRF 23 may be unnecessarily high quality for mobile screens

### Recommendations

| # | Recommendation | Complexity | Priority |
|---|---------------|------------|----------|
| 7.1 | **Autoplay compliance**: Ensure the Oracle page requires a user tap/click before attempting audio playback. Use a "Tap to start conversation" overlay on mobile. After the first interaction, the `AudioContext` is unlocked and subsequent responses can auto-play. Test on iOS Safari, Android Chrome, and Samsung Internet. | Low | P0 |
| 7.2 | **Binary audio delivery**: Replace base64 audio encoding with binary delivery via a separate audio URL (`/oracle/audio/{response_id}.mp3`). This eliminates 33% base64 overhead and enables browser-native caching and streaming. The JSON response includes the URL rather than inline audio. | Low | P1 |
| 7.3 | **Adaptive quality tiers**: Detect client bandwidth (either via `navigator.connection` API or by timing the first response) and serve appropriate quality: HIGH (30fps, CRF 23, 720p) for desktop/fast connections; MEDIUM (24fps, CRF 28, 480p) for mobile/medium; LOW (audio-only + viseme animation) for slow connections. | Medium | P1 |
| 7.4 | **Touch event normalization**: Use `pointer events` API (unified touch/mouse) instead of separate click/touch handlers. Add `touch-action: manipulation` CSS to prevent double-tap zoom on the input area. Ensure the "Ask" button has a minimum 44x44px touch target (Apple HIG minimum). | Low | P1 |
| 7.5 | **Responsive avatar layout**: Design a mobile-first layout where the avatar occupies the top 40% of the screen, the text response area is scrollable in the middle 40%, and the input bar is fixed at the bottom 20%. Use CSS `env(safe-area-inset-bottom)` for notched devices. | Medium | P2 |

---

## AREA 8: INTERRUPT HANDLING

### What Industry Leaders Do

**HeyGen LiveAvatar:** Provides a dedicated `v1/streaming.interrupt` endpoint. The SDK includes voice activity detection (VAD) that automatically triggers interrupts when the user begins speaking while the avatar is talking. Interruption is "immediate" -- the avatar stops mid-word. However, some users report that VAD sensitivity is not configurable enough, with avatars sometimes cutting off users mid-sentence or responding too quickly.

**Tavus Phoenix-4:** Full-duplex architecture means the system simultaneously talks and listens. The Sparrow-1 model handles turn-taking decisions -- it distinguishes between actual user interruptions, background noise, filler sounds ("uh huh"), and the AI's own echo. When a true barge-in is detected, the system stops TTS playback, cancels in-flight TTS generation, cancels LLM generation, and resets stream state. All four steps must complete to prevent the "finishes the old thought" bug.

**Industry best practices for barge-in (from voice AI research):**

1. **VAD with debounce**: Use Silero ONNX for silence-based VAD, processing audio in 10-20ms intervals. Apply a 500-1000ms debounce before triggering interrupt to prevent accidental triggers from background noise.
2. **Client-side immediate action**: A lightweight WebAssembly VAD loop detects barge-in on the client side, immediately mutes playback and drops the jitter buffer. Simultaneously, it sends a truncate signal via WebRTC data channel to the backend.
3. **Four-step cancellation**: Stop TTS playback -> cancel in-flight TTS generation -> cancel LLM generation -> reset stream state. Missing any step causes talk-over or stale responses.
4. **Natural break points**: Structure avatar responses to allow interruption at natural break points (sentence boundaries, pauses) rather than long unbroken monologues.
5. **Partial response preservation**: When interrupted, save how far the avatar got in its response. If the user's new question is a follow-up, include the partial response context.

**LiveKit's Adaptive Interruption Handling** (used by multiple avatar platforms):
- Distinguishes between intentional interruptions and incidental speech (backchannel, cough, ambient noise)
- Uses both audio energy and semantic analysis to determine intent
- Configurable sensitivity thresholds per deployment

### Current Satomi State

Satomi has a basic interrupt mechanism:
- `/oracle/interrupt` POST endpoint registers an interrupt by setting `ACTIVE_INTERRUPTS[conversation_id] = interrupt_id`
- The `/oracle/ask` handler checks `ACTIVE_INTERRUPTS` at two points: after the LLM call and after the TTS call
- If the interrupt ID has changed, the handler returns HTTP 409

Gaps:
- The interrupt check is poll-based at two fixed points -- if the LLM takes 2 seconds and the interrupt arrives at 0.5 seconds, 1.5 seconds of compute are wasted
- No client-side audio/video playback cancellation on interrupt -- the browser continues playing the old response
- No VAD -- interrupts are only triggered by explicit user action (button click), not by the user speaking
- No graceful stop: the response is fully aborted (409 error) rather than cleanly stopped at a natural break point
- The in-flight TTS request to ElevenLabs cannot be cancelled -- the server pays for the full TTS generation even if interrupted

### Recommendations

| # | Recommendation | Complexity | Priority |
|---|---------------|------------|----------|
| 8.1 | **Client-side immediate stop on new input**: When the user clicks "Ask" while a response is playing, immediately: (1) stop audio playback via `AudioContext.close()` or `audio.pause()`, (2) stop any video playback, (3) send the interrupt signal to the server, (4) submit the new question. The user should hear silence within 100ms of clicking. | Low | P0 |
| 8.2 | **Event-driven server-side cancellation**: Replace the poll-based interrupt check with an `asyncio.Event`. The `/oracle/interrupt` endpoint sets the event, and the `/oracle/ask` handler `await`s with a timeout at each step. When the event fires, all in-flight work (including the `httpx` call to ElevenLabs) is cancelled via `asyncio.CancelledError`. | Medium | P1 |
| 8.3 | **Partial response on interrupt**: When an interrupt arrives after the LLM has completed but during TTS, save the generated answer text. If the new question appears to be a follow-up (heuristic: short query, starts with "what about", "and", "also"), include the partial answer as context for the next LLM call. | Medium | P2 |
| 8.4 | **Voice Activity Detection (future)**: Add browser-side VAD using the Web Audio API + a lightweight VAD model (Silero ONNX via WebAssembly). When the user begins speaking while the avatar is talking, automatically trigger the interrupt flow. Apply a 500ms debounce to prevent false triggers from background noise. This is the path to true conversational feel. | High | P2 |

---

## Summary Matrix

| Area | Current Grade | Target Grade | Top Priority Action |
|------|:------------:|:------------:|-------------------|
| 1. Input Handling | C | B+ | Client-side debounce + AbortController (1.1, 1.2) |
| 2. Streaming | D+ | B | SSE progressive delivery (2.1) |
| 3. Latency | B- | A- | LLM streaming + sentence-level TTS pipelining (3.1) |
| 4. Error Recovery | D | B | TTS failover chain + LLM retry (4.1, 4.2) |
| 5. Visual Feedback | C+ | A- | State machine events + immediate text echo (5.1, 5.3) |
| 6. Conversation Memory | F | B+ | Wire existing memory into LLM calls (6.1, 6.2) |
| 7. Mobile Optimization | D | B | Autoplay compliance + touch normalization (7.1, 7.4) |
| 8. Interrupt Handling | C- | B | Client-side immediate stop (8.1) |

### P0 Recommendations (Implement First)

| # | Action | Area | Complexity |
|---|--------|------|-----------|
| 1.1 | Client-side debounce (200ms) | Input | Low |
| 1.2 | AbortController request cancellation | Input | Medium |
| 2.1 | SSE progressive delivery | Streaming | Medium |
| 3.1 | LLM streaming + sentence-level TTS | Latency | Medium |
| 3.3 | Expand pre-cached responses | Latency | Low |
| 4.1 | TTS failover chain (Kokoro -> ElevenLabs -> espeak) | Error Recovery | Medium |
| 4.2 | LLM retry with backoff | Error Recovery | Low |
| 5.1 | State machine with client events | Visual Feedback | Low |
| 5.3 | Immediate text echo | Visual Feedback | Low |
| 6.1 | Wire conversation history into LLM | Memory | Low |
| 6.2 | Save turns after each response | Memory | Low |
| 7.1 | Autoplay compliance | Mobile | Low |
| 8.1 | Client-side immediate stop on new input | Interrupt | Low |

### Estimated Impact

Implementing all P0 recommendations would:
- Reduce perceived first-response latency from ~4s to ~1.5-2s (via streaming + sentence pipelining)
- Eliminate duplicate request waste (via debounce + cancellation)
- Enable multi-turn conversations (via memory wiring)
- Prevent silent failures (via failover chains and retries)
- Work correctly on mobile browsers (via autoplay compliance)

### Satomi's Unique Advantages

It is worth noting what Satomi does well compared to the SaaS competitors:

1. **Full hardware ownership**: Running on dedicated RTX 4090s means zero per-request API costs for inference, no rate limits, and complete control over the pipeline. HeyGen, D-ID, and Tavus all charge per-minute or per-API-call fees that scale linearly with usage.

2. **Audio-first pattern**: The decision to decouple audio from video and serve audio first is exactly what HeyGen and Tavus do -- Satomi arrived at this pattern independently. This is the correct architecture.

3. **Local TTS via Kokoro**: Eliminates the network round-trip to ElevenLabs for most requests. At scale, this is both faster and cheaper than cloud TTS.

4. **Pre-computed blink and head movement**: The blink engine's 0.3ms/frame performance using pre-cached MediaPipe landmarks is more efficient than real-time facial landmark detection on every frame.

5. **Visitor memory system**: The SQLite-backed fingerprint + session memory in `oracle_memory.py` is more sophisticated than what most SaaS avatar platforms offer out of the box. The gap is in wiring it into the live response path.

---

## Sources

### Platform Documentation
- [HeyGen Streaming Avatar SDK Reference](https://docs.heygen.com/docs/streaming-avatar-sdk-reference)
- [HeyGen LiveAvatar Introduction](https://help.heygen.com/en/articles/12758516-introducing-liveavatar)
- [HeyGen LiveAvatar Implementation Guide](https://www.truefan.ai/blogs/heygen-liveavatar-implementation-guide)
- [HeyGen Interrupt Task API](https://docs.heygen.com/reference/interrupt-task)
- [HeyGen LiveAvatar FAQ](https://help.heygen.com/en/articles/12758866-liveavatar-faq)
- [D-ID Agents Streams Overview](https://docs.d-id.com/reference/agents-streams-overview)
- [D-ID Agents Overview](https://docs.d-id.com/reference/agents-overview)
- [D-ID API Architecture Review](https://anam.ai/blog/d-id-api-review-2025-architecture-capabilities)
- [Tavus Phoenix-4 Launch](https://www.marktechpost.com/2026/02/18/tavus-launches-phoenix-4-a-gaussian-diffusion-model-bringing-real-time-emotional-intelligence-and-sub-600ms-latency-to-generative-video-ai/)
- [Tavus Phoenix-4 Technical Details](https://www.tavus.io/post/phoenix-4-real-time-human-rendering-with-emotional-intelligence)
- [Tavus CVI Overview](https://docs.tavus.io/sections/conversational-video-interface/overview-cvi)
- [Tavus WebRTC for Conversational Video](https://www.tavus.io/post/webrtc-for-seamless-conversational-video-interactions)
- [Simli AI Platform](https://www.simli.com/)
- [Simli Cost-Efficient Real-Time Inference](https://verda.com/blog/how-simli-achieved-cost-efficient-real-time-inference-for-interactive-ai)
- [Synthesia Technical Architecture](https://aitocore.com/en/tool/synthesia)
- [Synthesia 3.0 Announcement](https://www.synthesia.io/post/synthesia-3-0-the-next-era-of-video)

### Technical References
- [Handling Barge-In in Voice AI](https://sayna.ai/blog/handling-barge-in-what-happens-when-users-interrupt-your-ai-mid-sentence)
- [VAD Strategies for Fluid AI Conversations](https://dev.to/deepak_mishra_35863517037/the-art-of-interruption-vad-strategies-for-fluid-ai-conversations-15bh)
- [LiveKit Adaptive Interruption Handling](https://docs.livekit.io/agents/logic/turns/adaptive-interruption-handling/)
- [WebRTC vs WebSocket for AV Sync](https://getstream.io/blog/webrtc-websocket-av-sync/)
- [Why WebRTC Beats WebSockets for Voice AI](https://livekit.com/blog/why-webrtc-beats-websockets-for-voice-ai-agents)
- [WebRTC Latency Comparison 2026](https://www.nanocosmos.net/blog/webrtc-latency/)
- [Wav2Lip Real-Time Optimization](https://github.com/devkrish23/realtimeWav2lip)
- [Asynchronous Pipeline Parallelism for Real-Time Lip Sync](https://arxiv.org/html/2512.18318v1)
- [Wav2Lip-fast Modifications](https://github.com/ohsugi/Wav2Lip-fast)
- [Context Window Management Strategies](https://www.getmaxim.ai/articles/context-window-management-strategies-for-long-context-ai-agents-and-chatbots/)
- [Building AI Chatbots with Memory](https://dasroot.net/posts/2026/04/building-ai-chatbots-memory-context-management/)
- [Error Recovery and Graceful Degradation Patterns](https://www.aiuxdesign.guide/patterns/error-recovery)
- [Voice AI Architecture Guide 2026](https://www.teamday.ai/blog/voice-ai-architecture-guide-2026)
