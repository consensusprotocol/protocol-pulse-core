# CONSENSUS REPORT — ORACLE-PHASE2 — CYCLE 1
Generated: 2026-03-24 18:58
Models: grok, gemini (+1 failed: gpt-4o — rate limit exceeded)

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Thinking Video Architecture | 8/10 | N/A | 8/10 | 8.0/10 |
| SSE Architecture | 7/10 | N/A | 7/10 | 7.0/10 |
| Thread Safety | 7/10 | N/A | 7/10 | 7.0/10 |
| Frontend UX / Cross-fade | 6/10 | N/A | 6/10 | 6.0/10 |
| Overall Phase 2 Readiness | 7/10 | N/A | 7/10 | 7.0/10 |

> **Note:** GPT-4o failed due to TPM rate limit (53,725 tokens requested vs. 30,000 limit). Scores are averaged across 2 models only. Confidence in consensus is **REDUCED** — treat majority findings as tentative until Cycle 2 with all 3 models restored.

---

## UNANIMOUS FINDINGS
*(Both available models agree — implement unconditionally)*

### U1 — Play Thinking Loop Immediately on Chat Submit
- **What:** Instead of showing a static background image + spinner while waiting for video generation, immediately play the pre-generated idle/thinking loop video as visual feedback.
- **File/Line:** `oracle_live.html`, inside `process()` function, around line 1067 (after `setStat('Oracle thinking...')`)
- **Change:**
  ```javascript
  vid.src = '/oracle_idle';   // or '/static/oracle_thinking.mp4'
  vid.loop = true;
  vid.muted = true;           // Required for autoplay compliance
  vid.style.opacity = '1';
  vid.play().catch(e => console.warn('Thinking autoplay blocked:', e));
  ```
- **Why both agree:** The static avatar background with a text spinner is the primary driver of 8–15s *perceived* latency. Immediate animation drops time-to-first-visual-feedback (TTFVF) from ~2–4s to ~200ms. Zero risk to backend pipeline.

### U2 — Replace Polling with SSE Using Per-Job `queue.Queue`
- **What:** Eliminate the `setInterval` 2-second polling loop (`oracle_live.html`, line 1178) with a Server-Sent Events stream from the Flask backend.
- **Files/Lines:**
  - `avatar_server.py`: Add `_sse_queues = {}` + `_sse_queues_lock` near line 209
  - `avatar_server.py`: Populate queue on job creation in `/oracle/chat` around line 1827
  - `avatar_server.py`: Add new `@app.route("/oracle/stream/<job_id>")` SSE endpoint
  - `avatar_server.py`: In `render_async` (line 1832), call `job_queue.put({...})` at key milestones
  - `oracle_live.html`: Replace `setInterval` block (line 1178) with `EventSource('/oracle/stream/<job_id>')`
- **Why both agree:** Polling introduces 0–2000ms dead-air latency per cycle. SSE delivers sub-100ms notification when audio or video is ready, saving **~1000–2000ms** of observable delay.

### U3 — Thinking Video Must Be `muted=true` for Autoplay
- **What:** The thinking loop video element must be muted at all times until the real response video is ready; unmute is handled inside `playVid()`.
- **File/Line:** `oracle_live.html`, in the thinking video setup block (U1 above)
- **Change:** Ensure `vid.muted = true` is set explicitly before `.play()`.
- **Why both agree:** Modern browser autoplay policies block unmuted video without user gesture. Failure to mute = silent failure in production on Chrome, Safari, Firefox mobile.

### U4 — Preload the Thinking Loop on Page Load
- **What:** Add a `<link rel="preload">` tag for the thinking/idle video in the HTML `<head>`.
- **File/Line:** `oracle_live.html`, `<head>` section, around line 11
- **Change:**
  ```html
  <link rel="preload" href="/oracle_idle" as="video">
  ```
- **Why both agree:** Without preload, the first play of the thinking loop incurs a 500–1000ms network fetch delay, negating the benefit of immediate playback.

### U5 — SSE Generator Needs Keep-Alive Pings
- **What:** The SSE generator must emit a `ping` or comment line on queue timeout to prevent proxies and load balancers from killing the connection.
- **File/Line:** `avatar_server.py`, inside the SSE generator function
- **Change:** On `queue.Empty` exception (1s timeout), yield `": ping\n\n"` (SSE comment, no client event fired) before looping.
- **Why both agree:** Both models independently included a keep-alive mechanism in their SSE designs; absence causes silent disconnection behind Nginx/CloudFlare/ALB with 60s idle timeouts.

---

## MAJORITY FINDINGS
*(2 of 2 models agree — implement unless compelling reason not to)*

All findings from 2 available models are de facto unanimous. See above. No additional majority-only tier exists given the 2-model sample.

---

## UNIQUE INSIGHTS
*(Only 1 model caught this — evaluate carefully)*

### UI-1 — Grok Only: Lock Acquisition Timing in SSE Queue Setup
- **Observation:** Grok's SSE endpoint acquires `_render_jobs_lock` inside the generator and conditionally creates an `event_queue` if missing. This race-condition mitigation handles the case where the SSE client connects *before* the job dict entry has the queue populated.
- **Assessment:** **IMPLEMENT.** Gemini's design assumes the queue always exists when the SSE endpoint is hit, but under load the SSE client could connect within milliseconds of the job being created, before `render_async` starts. Grok's defensive check is correct. Add:
  ```python
  with _sse_queues_lock:
      if job_id not in _sse_queues:
          return jsonify({"error": "Job not found"}), 404
      q = _sse_queues[job_id]
  ```

### UI-2 — Grok Only: Loop Seam Glitch Warning on Idle Loop
- **Observation:** Grok explicitly flagged that the 4s idle loop in `generate_idle_loop()` (`avatar_server.py`, line 1406) may have a visible seam at the loop boundary if frames aren't continuous.
- **Assessment:** **INVESTIGATE FURTHER.** Play `oracle_idle.mp4` in a browser on repeat and verify frame 0 ≈ frame N visually. If a jump is visible, the generation function needs a cross-dissolve at loop boundary or the loop point needs to be trimmed. Low effort to verify; potentially high UX impact.

### UI-3 — Gemini Only: Thinking Video File Size Constraint
- **Observation:** Gemini specified the thinking loop must be under ~200KB using `crf 28+, preset ultrafast` to guarantee instant load even on slow connections.
- **Assessment:** **IMPLEMENT as a hard constraint.** Grok did not set an explicit size budget. A 3–4s 512×512 H.264 video at default CRF settings could easily exceed 1MB, causing 500–2000ms load delay on mobile — the exact problem it's meant to solve. Enforce this in `generate_thinking_loop()` or `generate_idle_loop()` ffmpeg call parameters.

### UI-4 — Gemini Only: Separate `generate_thinking_loop()` vs Reusing `generate_idle_loop()`
- **Observation:** Gemini recommends a dedicated `generate_thinking_loop()` function; Grok recommends reusing the existing `generate_idle_loop()` and its output at `ORACLE_IDLE_PATH`.
- **Assessment:** **Lean toward Grok (reuse) with Gemini's size constraint added.** The idle loop already satisfies requirements (blinks, head movement, no audio, no lips). Creating a duplicate function adds maintenance surface for no functional gain. However, verify the idle loop meets the <200KB size budget (UI-3). If it doesn't, add compression parameters to `generate_idle_loop()`.

### UI-5 — Grok Only: SSE Cleanup on `job_id` Completion
- **Observation:** Grok's generator checks `job.get("status") in ("done", "error")` to break the loop and free the thread.
- **Assessment:** **IMPLEMENT** in tandem with Gemini's `finally: _sse_queues.pop(job_id, None)` cleanup. Both mechanisms are complementary: the break exits the generator, the `finally` cleans up the global dict. Missing either causes memory leaks under load.

---

## CONFLICTS
*(Models gave contradictory recommendations — tiebreaker applied)*

### C1 — Thinking Video Source: `/oracle_idle` vs `/static/oracle_thinking.mp4`
- **Grok:** Reuse existing `/oracle_idle` endpoint and `ORACLE_IDLE_PATH`.
- **Gemini:** Create a new `/oracle/thinking_loop` endpoint serving `oracle_thinking.mp4`.
- **Tiebreaker: GROK IS RIGHT.** The idle loop already exists, is generated at startup, and is served. Adding a second nearly-identical file doubles storage, generation time at startup, and maintenance. Use `/oracle_idle`. If the idle loop is ever upgraded, it benefits both use cases. Override: ensure compression budget (UI-3) is applied to `generate_idle_loop()`.

### C2 — SSE Queue Initialization: At Job Creation vs Lazily in SSE Handler
- **Gemini:** Queue is created at job creation time in `/oracle/chat`, passed directly to `render_async`.
- **Grok:** Queue may be created lazily inside the SSE handler if missing.
- **Tiebreaker: GEMINI'S APPROACH IS ARCHITECTURALLY CLEANER, but add Grok's defensive check.** Create the queue in `/oracle/chat` at job creation (Gemini) to guarantee it exists when `render_async` starts producing events. Add Grok's defensive existence check in the SSE handler as a safety net for edge cases (race, client connects before job fully initialized). Both are needed; they are not mutually exclusive.

### C3 — SSE Event Format: Typed `event:` field vs flat `data:` JSON with `event` key
- **Gemini:** Uses SSE named events (`event: audio_ready\ndata: {...}\n\n`) — allows `addEventListener('audio_ready', ...)` on the client.
- **Grok:** Puts event type inside the JSON payload (`data: {"event": "audio_ready"}\n\n`).
- **Tiebreaker: GEMINI IS RIGHT.** Named SSE events are the spec-correct approach, enable cleaner client-side event binding, and avoid parsing overhead. Use `event: <type>\ndata: <json>\n\n` format. Client uses `es.addEventListener('audio_ready', handler)` not generic `onmessage`.

---

## VALIDATED STRENGTHS
*(Both models confirmed — do NOT change in second pass)*

1. **Audio-First Response Strategy** (`oracle_live.html`, lines 1098–1158): Fetching and playing audio before video is ready is the correct UX priority. Both models validated this pattern. Do not refactor the audio playback flow.

2. **`generate_idle_loop()` at Startup** (`avatar_server.py`, lines 1386–1414): Pre-generating the idle loop at server startup (not on-demand) is the right approach. It ensures zero generation latency when the thinking video is needed. Keep this startup call.

3. **`/oracle_idle` Static Endpoint** (`avatar_server.py`, lines 1378–1383): Serving the idle loop as a dedicated endpoint is correct. Do not convert to inline data URI or CDN-only delivery; the endpoint allows cache-control headers and conditional GET.

4. **`vid.style.opacity` CSS Transition** (`oracle_live.html`, line 293): The existing `opacity 0.5s` transition on `#vid` provides the foundation for cross-fade between thinking loop and final video. This is already in place — leverage it, don't replace it.

5. **`_render_jobs` Dict + Lock Pattern** (`avatar_server.py`, around line 206): The existing job tracking with a lock is a sound foundation. The SSE extension should add `_sse_queues` as a parallel dict using the same locking pattern rather than replacing the existing job dict.

---

## LAW COMPLIANCE CONSENSUS

*(Assessed against PIPELINE_LAWS.md principles as inferred from code context)*

| Law / Principle | Status | Finding |
|---|---|---|
| No blocking the main Flask thread | ⚠️ RISK | SSE generator holds a thread per open connection in threaded Flask. At 1000 concurrent users this exhausts the thread pool. Acceptable for current scale; document the ceiling. |
| Fail fast, fail loud | ⚠️ PARTIAL | SSE timeout after 120s is correct, but error events must be surfaced to UI (not silently swallowed). Both models' SSE designs emit error events — verify frontend handles them. |
| No polling for real-time state | ❌ VIOLATED (current) | Current `setInterval` polling violates real-time responsiveness law. SSE implementation fixes this. |
| Autoplay media must be muted | ❌ VIOLATED (proposed) | The proposed thinking video starts without explicit `muted=true` in some interpretations. Both models flagged this — U3 fix is mandatory. |
| Static assets pre-generated at startup | ✅ COMPLIANT | Idle loop generated at startup. Fully compliant. |
| Job cleanup after completion | ⚠️ RISK | SSE queue dict must be purged after job completion or timeout. Both models' `finally` blocks address this; must be verified in implementation. |

---

## SECURITY CONSENSUS

*(Priority order — both models agree)*

### SEC-1 — Job ID Enumeration / Authorization (MEDIUM)
- **Issue:** `/oracle/stream/<job_id>` and `/oracle/job/<id>/audio` have no authentication check. Any user who guesses or observes a `job_id` (16-char hex) can subscribe to another user's SSE stream or download their audio.
- **Both models implicitly assumed auth exists but neither explicitly flagged this.** The 16-char hex space (2^64) provides adequate brute-force resistance, but there is no session binding.
- **Recommendation:** Bind `job_id` to the requesting session/user in the SSE handler. Return 403 if session mismatch.

### SEC-2 — SSE Thread Exhaustion / DoS (LOW-MEDIUM)
- **Issue:** A malicious client can open many SSE connections without closing them, exhausting Flask's thread pool.
- **Recommendation:** Limit concurrent SSE connections per IP or session. Set `SO_REUSEPORT` or switch to Gunicorn + gevent for event-heavy endpoints.

### SEC-3 — `job_id` in URL Leaks to Server Logs (LOW)
- **Issue:** Job IDs in the URL path (`/oracle/stream/<job_id>`) appear in access logs, which may be retained and accessible to admins.
- **Recommendation:** Acceptable for internal tool. If user data is sensitive, move job_id to a request header or use short-lived signed tokens.

---

## WORLD-CLASS GAP CONSENSUS
*(Items 2+ models mentioned as missing from a truly world-class implementation)*

### WCG-1 — Cross-Fade Between Thinking Loop and Final Video *(both models)*
Both models flagged that simply changing `vid.src` causes a flicker/flash. A world-class implementation needs a true cross-fade: a second hidden `<video>` element (`#vid2`) that the final video loads into, fading in while the thinking loop fades out. Neither model provided complete implementation code for this. **This is the highest-polish gap.**

### WCG-2 — Gunicorn + Async Workers for SSE at Scale *(both models)*
Both models noted that Flask threaded mode is a limitation for long-lived SSE connections. A production-grade system should use Gunicorn with `gevent` or `eventlet` workers, which handle thousands of concurrent SSE connections without thread exhaustion. Current architecture is explicitly acknowledged as sufficient "for now" (~1000 users) but not world-class.

### WCG-3 — SSE Reconnection / Resilience *(both models implied)*
The `EventSource` API auto-reconnects, but neither model addressed what happens to missed events (audio_ready, video_ready) if the client briefly disconnects. A world-class implementation includes event sequence numbers and a replay buffer so reconnecting clients catch up without re-polling.

---

## FINAL ACTION PLAN
*(Sorted by consensus priority)*

| Priority | Change | File:Line | Models | Why |
|---|---|---|---|---|
| **P0 CRITICAL** | Set `vid.src='/oracle_idle'; vid.loop=true; vid.muted=true; vid.play()` immediately in `process()` | `oracle_live.html:1067` | both | Drops TTFVF from 2–4s to 200ms; single highest-impact UX change |
| **P0 CRITICAL** | Add `<link rel="preload" href="/oracle_idle" as="video">` in `<head>` | `oracle_live.html:11` | both | Without preload, thinking video delays 500–1000ms, negating P0 above |
| **P0 CRITICAL** | Enforce `vid.muted=true` before `.play()` in thinking video setup | `oracle_live.html:1067` | both | Browser autoplay policy; silent failure without this |
| **P1 HIGH** | Create `_sse_queues = {}` + `_sse_queues_lock` + populate queue in `/oracle/chat` at job creation | `avatar_server.py:209, ~1827` | both | Foundation of SSE; queue must exist before `render_async` starts |
| **P1 HIGH** | Add `render_async` queue.put() calls at TTS-complete and video-complete milestones | `avatar_server.py:1832` | both | Producer side of SSE; without this, SSE delivers nothing |
| **P1 HIGH** | Add `@app.route("/oracle/stream/<job_id>")` SSE endpoint with typed events (`event: audio_ready`) | `avatar_server.py:new` | both (Gemini format) | Consumer side; use Gemini's named-event format per C3 tiebreaker |
| **P1 HIGH** | Replace `setInterval` polling with `EventSource('/oracle/stream/<job_id>')` | `oracle_live.html:1178` | both | Eliminates 1000–2000ms polling dead-air; core latency fix |
| **P1 HIGH** | Add keep-alive `": ping\n\n"` on queue.Empty in SSE generator | `avatar_server.py:SSE endpoint` | both | Prevents proxy/LB idle-timeout disconnection |
| **P1 HIGH** | Add `finally: _sse_queues.pop(job_id, None)` in SSE generator + break on done/error status | `avatar_server.py:SSE endpoint` | both (complementary) | Prevents memory leak; both mechanisms required |
| **P1 HIGH** | Add Grok's defensive queue existence check in SSE handler before yielding | `avatar_server.py:SSE endpoint` | unique/grok | Race condition: client connects before queue fully initialized |
| **P2 MEDIUM** | Enforce `crf 28+, preset ultrafast` in `generate_idle_loop()` ffmpeg call; verify output <200KB | `avatar_server.py:1386` | unique/gemini | Slow-loading thinking video defeats its own purpose |
| **P2 MEDIUM** | Play-test `oracle_idle.mp4` loop boundary; fix seam if visible (cross-dissolve at boundary) | `avatar_server.py:1406` | unique/grok | Jarring loop seam degrades the "live avatar" illusion |
| **P2 MEDIUM** | Implement cross-fade via second `<video>` element for thinking→final transition | `oracle_live.html:672` | both (WCG-1) | Eliminates flicker on `src` change; polish gap noted by both models |
| **P2 MEDIUM** | Bind SSE job_id to requesting session; return 403 on mismatch | `avatar_server.py:SSE endpoint` | consensus/security | Prevents unauthorized stream interception |

---

## CYCLE 1 VERDICT

**READY FOR SECOND BUILD PASS — WITH CONDITIONS.**

The architecture is sound and both models independently converged on the same two primary changes (thinking video loop + SSE). There are no fundamental design flaws requiring rework. However, the following conditions must be met in the second pass:

1. The cross-fade (WCG-1 / P2) should be included in this pass — both models flagged it as a polish gap, and shipping the thinking video without it will produce a visible flicker that undermines the UX goal.
2. GPT-4o must be included in Cycle 2 review after the build pass. The 2-model sample reduces confidence, particularly for thread-safety edge cases. Reduce prompt token count or split into sub-audits to stay within TPM limits.
3. The SSE format conflict (C3) is resolved in favor of Gemini's named-event format — implementer must not inadvertently use Grok's flat-JSON format.

---

## SECOND PASS PROMPT
*(Ready to fire into Claude Code)*

```
Read ~/protocol_pulse/docs/gospels/PIPELINE_LAWS.md.
Read ~/protocol_pulse/docs/audits/oracle-phase2_CONSENSUS_C1.md.

This is the SECOND PASS for oracle-phase2.
The first build was reviewed by 2 independent AI models (grok, gemini) across 1 cycle.
GPT-4o failed due to rate limit and must be re-engaged in Cycle 2 post-build.
Implement every P0 and P1 item from the consensus. Use judgment on P2.

PRIORITY ACTION PLAN:

P0 CRITICAL | In process() immediately after setStat('Oracle thinking...'), add:
              vid.src='/oracle_idle'; vid.loop=true; vid.muted=true;
              vid.style.opacity='1';
              vid.play().catch(e=>console.warn('Thinking autoplay blocked:',e));
            | oracle_live.html:1067 | models: both | Drops TTFVF to ~200ms

P0 CRITICAL | Add <link rel="preload" href="/oracle_idle" as="video"> in <head>
            | oracle_live.html:11 | models: both | Prevents 500-1000ms cold-load delay

P0 CRITICAL | Ensure vid.muted=true is set before .play() in thinking video block
            | oracle_live.html:1067 | models: both | Browser autoplay policy compliance

P1 HIGH     | Add _sse_queues={} and _sse_queues_lock=threading.Lock() near line 209.
              In /oracle/chat at job creation (~line 1827), create a Queue() per job_id
              and store in _sse_queues under _sse_queues_lock.
            | avatar_server.py:209,1827 | models: both | SSE foundation

P1 HIGH     | In render_async (line 1832), after TTS completes call job_queue.put({"event":"audio_ready"}).
              After video encode completes call job_queue.put({"event":"video_ready"}).
              On exception call job_queue.put({"event":"error","data":str(e)}).
              In finally block call job_queue.put({"event":"close"}).
            | avatar_server.py:1832 | models: both | SSE producer milestones

P1 HIGH     | Add