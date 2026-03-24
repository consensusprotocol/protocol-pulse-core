# CONSENSUS REPORT — ORACLE-SPEED — CYCLE 2
Generated: 2026-03-24 15:43
Models: grok, gemini (+1 failed: gpt-4o — rate limit exceeded)

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Intent Classification | 9/10 | N/A | 9/10 | **9/10** |
| LLM Response (Claude Haiku) | 7/10 | N/A | 7/10 | **7/10** |
| TTS Generation (Kokoro/ElevenLabs) | 3/10 | N/A | 5/10 | **4/10** |
| Wav2Lip Inference | 5/10 | N/A | 4/10 | **4/10** |
| Video Encoding (`frames_to_video`) | 1/10 | N/A | 2/10 | **1/10** |
| Audio-First Streaming Architecture | 2/10 | N/A | 4/10 | **3/10** |
| Frontend Polling Mechanism | 3/10 | N/A | 3/10 | **3/10** |
| Network / Transfer | 8/10 | N/A | 8/10 | **8/10** |
| **Overall System Latency** | **2/10** | N/A | **3/10** | **2/10** |

> **Note on scoring divergence:** Gemini scored more harshly than Grok on TTS (3 vs 5) and Audio-First Architecture (2 vs 4). The consensus leans toward Gemini's assessment, as its reasoning — that the system does not stream but batch-generates — is architecturally more precise. The consensus overall score of 2/10 reflects a system with a known critical regression bug (-preset medium) that blocks the stated goal.

---

## UNANIMOUS FINDINGS
*(Both models agree — implement unconditionally)*

### U1 — Video Encoding Preset is a Catastrophic Regression Bug
- **What:** The ffmpeg encoding call uses `-preset medium` instead of `-preset ultrafast`. A comment in the file header (line 12) documents the intent as `ultrafast`, meaning this is a confirmed regression. This single parameter is responsible for 4–8 seconds of unnecessary encoding latency.
- **File/Line:** `avatar_server.py:506` and `avatar_server.py:521`
- **Change:** Replace `"-preset", "medium"` with `"-preset", "ultrafast"`. Optionally adjust `-crf` from 18 to 23–25 to compensate for the slight quality trade-off from faster compression.
- **Estimated Saving:** 4–8 seconds per render.

### U2 — Frontend Polling Must Be Replaced with a Push Architecture
- **What:** The frontend polls `/oracle/job/<id>` on a 2-second interval to detect when audio and video are ready. This introduces guaranteed dead time: an average of 1,000ms and a worst case of 2,000ms *per poll event*, applied twice (once for audio, once for video), yielding up to 4,000ms of pure idle latency before the user receives anything. This is structurally incompatible with a <5s perceived latency goal.
- **File/Line:** `avatar_server.py:1691` (audio poll endpoint) and `avatar_server.py:1730` (video poll endpoint)
- **Change:** Implement a WebSocket or Server-Sent Events (SSE) connection established at the time of the `/oracle/chat` request. Push discrete events (`audio_ready`, `video_ready`) with the asset payload or a URL the moment each asset is available server-side. Remove the polling endpoints or retain them only as a degraded fallback.
- **Estimated Saving:** 0–4,000ms eliminated dead time.

### U3 — Audio-First Architecture Is Not True Streaming
- **What:** Both models independently confirmed that despite the architecture being named "audio_first," the system generates the entire TTS audio file before making any of it available. The TTS pipeline (`_avatar_tts`) uses a generator internally (`avatar_server.py:642`) but does not yield chunks to the client progressively. The client receives nothing until the full audio is ready.
- **File/Line:** `avatar_server.py:619–703`
- **Change:** Refactor `_avatar_tts` to yield and transmit audio chunks as they emerge from the Kokoro generator pipeline. Deliver these immediately over the WebSocket/SSE connection established in U2. Audio playback should begin client-side within ~500–800ms of the first chunk arriving.
- **Estimated Saving:** Allows audio start in <2s, compared to the current 2.8–7.1s subtotal.

---

## MAJORITY FINDINGS
*(2 of 2 models agree — implement unless compelling reason not to)*

All three unanimous findings above are also the majority findings given the two-model quorum. No additional issues rose to majority level beyond those already listed in the Unanimous section. The items below were independently corroborated by both models through different framings:

- **Wav2Lip inference is the dominant compute bottleneck**, accounting for 10–15s of the 15–25s total. Both models agree it cannot be "fixed" with a parameter change — it requires architectural solutions (progressive rendering, pre-baked segments, or model replacement). Treat as a known constraint requiring a longer-term solution.
- **The combination of encoding bug + polling + non-streaming TTS is multiplicative**, not additive. Each compounds the others. Fixing all three in the same pass is required to hit the target; fixing only one or two will not be sufficient.

---

## UNIQUE INSIGHTS
*(Only 1 model caught this — evaluated individually)*

### Gemini-Only Findings:

**G1 — Two Sequential ffmpeg Subprocesses in TTS Post-Processing**
- **Finding:** `_avatar_tts` (`avatar_server.py:653–687`) launches two separate `ffmpeg` subprocess calls — one to resample and one to apply `loudnorm` — writing intermediate temporary files to disk between them.
- **Assessment:** **Implement.** This is a straightforward, low-risk optimization. Combining into a single ffmpeg filter chain (`-af "aresample=16000, loudnorm=..."`) reduces subprocess spawning overhead, eliminates intermediate disk writes, and reduces TTS post-processing time. Estimated saving: 100–300ms. No downside.

**G2 — Intermediate .avi File in Video Encoding Pipeline**
- **Finding:** `frames_to_video` (`avatar_server.py:486–495`) writes all raw frames to an intermediate `.avi` file on disk before ffmpeg reads it back for final MP4 encoding. This is redundant disk I/O.
- **Assessment:** **Implement.** Piping raw frames directly to ffmpeg via `stdin` (using `ffmpeg -f rawvideo -pix_fmt bgr24 -s WxH -r FPS -i pipe:0 ...`) eliminates the `.avi` write/read cycle entirely. Combined with G1 and the preset fix, this compounds meaningfully. Medium complexity — requires careful frame format alignment with ffmpeg pipe expectations. Estimated saving: 200–800ms.

**G3 — Blink Engine is a Disabled Stub**
- **Finding:** `apply_blink_gradient` in `blink_engine.py:261` returns frames unmodified. A comment confirms it was disabled due to visual artifacts.
- **Assessment:** **Investigate but do not block on.** This is a functional/quality bug, not a latency bug. It means users are not getting natural blink animation. It does not affect speed. Flag for the avatar quality backlog — do not include in this performance pass.

**G4 — Async Job System Stores Full Video Bytes in Memory**
- **Finding:** `render_async` (`avatar_server.py:1895–1900`) stores the entire encoded video as a byte array in the global `_render_jobs` dictionary. Under concurrent load, this creates unbounded memory pressure.
- **Assessment:** **Implement at P2.** Store the file path instead of the bytes. Serve via `send_file` with a TTL-based cleanup. This is not a latency fix but is a scalability and stability requirement. Becomes critical once the speed fixes drive increased usage.

### Grok-Only Findings:

**R1 — Batch Size for Wav2Lip Uses Binary Threshold, Not Graduated Scaling**
- **Finding:** Wav2Lip batch size switches between `BATCH_SIZE_SMALL=16` and `BATCH_SIZE_DEFAULT=48` based on a single threshold (mel frames < 60), with no graduated scaling between these extremes.
- **Assessment:** **Investigate.** The logic exists at `avatar_server.py:338–339`. For mid-length clips that fall just above the 60-frame threshold, using batch size 48 may be suboptimal. A linear or stepped scaling function could reduce inference time on mid-length inputs. Low priority — the potential gain is tens to low hundreds of milliseconds. Worthwhile to profile but not a blocker.

**R2 — Sequential Per-Frame Post-Processing (Blinks, Head Movement)**
- **Finding:** Post-processing in `avatar_server.py:439–473` applies blink and head movement effects sequentially per frame, accumulating overhead for longer clips.
- **Assessment:** **Investigate.** Vectorizing with NumPy or parallelizing across frames with a thread pool could reduce this. However, since the blink engine is disabled (see G3), the practical impact of this optimization is currently near-zero. Revisit after blink engine is fixed.

**R3 — ffmpeg Loudnorm Could Be Skipped for Pre-Normalized Sources**
- **Finding:** The loudnorm step in TTS post-processing could be conditionally skipped if the source (e.g., Kokoro) already outputs normalized audio.
- **Assessment:** **Skip for now.** This optimization requires reliable characterization of Kokoro's output levels. Applying loudnorm unconditionally is safer for audio consistency. The time saving (~100ms) does not justify the audio quality risk without further data.

---

## CONFLICTS
*(Where models gave contradictory recommendations — tiebreaker applied)*

### Conflict 1: Wav2Lip Inference Time — Grok 12s vs. Gemini 1.5–3s

- **Grok's position:** Wav2Lip inference takes approximately 10–15s on RTX 4090 with FP16, accounting for ~67% of total latency.
- **Gemini's position:** Wav2Lip takes 1.5–3s on RTX 4090 for a typical 5–8 second response.
- **Tiebreaker verdict: Grok is more likely correct.** The user's stated observed latency of 15–25s is the ground truth calibration point. Gemini's estimate of 1.5–3s for Wav2Lip, when combined with its own estimates for TTS (2–3.5s), encoding (4–9s), and polling (0–4s), still only reaches ~12–20s at the high end — which barely explains the observed ceiling. Grok's 12s Wav2Lip estimate more plausibly explains the observed floor of 15s. Additionally, Wav2Lip's published benchmarks on RTX-class hardware for full-face video at typical resolutions support the longer estimate. Note: if Gemini's estimate is correct, it implies the encoding bug alone may explain most of the pathological 25s cases, which is also plausible. Profile under real conditions before committing Wav2Lip-specific hardware changes.

### Conflict 2: Severity of TTS Score — Gemini 3/10 vs. Grok 5/10

- **Verdict: Gemini's 3/10 is correct.** Grok's 5/10 reflects the raw API call latency as acceptable. Gemini's 3/10 correctly weights that the architecture prevents the latency from being _perceived_ as low, because even a fast 2s TTS generation is entirely hidden from the user until the full file is assembled. The scoring should reflect user-perceived impact, not component throughput in isolation.

### Conflict 3: Feasibility of TTS Chunk Streaming

- **Grok's position:** Noted the approach is ideal but may require deeper integration changes depending on Kokoro/ElevenLabs API streaming support.
- **Gemini's position:** The code already uses a generator (`avatar_server.py:642`), so the streaming infrastructure exists — the failure to use it is the bug.
- **Verdict: Gemini is correct.** The generator exists. The problem is architectural — the output is being buffered rather than forwarded. This is not an API capability question; it is a code flow question. The risk is lower than Grok implied.

---

## VALIDATED STRENGTHS
*(All models confirmed excellent — do NOT change in second pass)*

1. **Intent Classification** (`oracle_dialogue_engine.py:1441–1459`): Regex-based, runs in memory, ~5–15ms. Both models scored this 9/10. Do not add LLM calls or async overhead here.

2. **LLM Response Generation (Claude Haiku)** (`dialogue_engine.py:863`): Both models scored this 7/10. ~800–1500ms is acceptable for a generative API call. The timeout of 12s is reasonable headroom. Do not change the model, the prompt structure, or the timeout in this pass.

3. **Network Transfer Layer**: Both models scored this 8/10. Using `send_file` for video and direct byte responses for audio is appropriate. File sizes and transfer times are not material bottlenecks. Do not add compression layers or CDN logic in this pass.

4. **GPU Assignment Architecture** (`model_registry.py:23`): Both models implicitly validated the use of FP16 on RTX 4090 (cuda:1) for Wav2Lip and the separate GPU allocation strategy. This is correct and should not be changed.

---

## LAW COMPLIANCE CONSENSUS

Based on the audit findings cross-referenced against documented pipeline intent (header comments, architecture docs referenced):

| Law / Principle | Status | Finding |
|---|---|---|
| Audio-First Delivery | ❌ **VIOLATED** | System is batch-audio-then-poll, not streaming audio-first |
| Preset Speed Compliance | ❌ **VIOLATED** | Header documents `ultrafast`; code ships `medium` — active regression |
| Sub-5s Perceived Latency | ❌ **VIOLATED** | Current floor is ~15s; ceiling is ~25s |
| Sub-3s Audio Start | ❌ **VIOLATED** | Audio start is 2.8–7.1s before polling dead time is added |
| GPU Resource Isolation | ✅ **COMPLIANT** | Wav2Lip on cuda:1, correctly separated |
| LLM Timeout Bounding | ✅ **COMPLIANT** | 12s hard timeout on Claude Haiku is appropriate |
| Intent Classification Efficiency | ✅ **COMPLIANT** | Regex path is fast and correct |
| Memory Safety for Job Cache | ⚠️ **AT RISK** | Storing full video bytes in memory is not production-safe under load |

**Final Determination:** 4 of 8 measured laws/principles are currently violated. The system is not compliant with its own stated performance contract. All violations are addressable in a single implementation pass.

---

## SECURITY CONSENSUS

Neither model raised critical security vulnerabilities in this performance-focused audit. The following items emerged peripherally:

1. **Temporary File Cleanup** (Gemini, medium): The multi-step ffmpeg post-processing writes intermediate files (`wav24_path`, `wav16_path`, `norm_path`). If exceptions interrupt the pipeline, these files may persist. Ensure `try/finally` cleanup is in place. Risk: disk exhaustion over time, not data exposure.

2. **Global In-Memory Job Cache** (Gemini, medium): Storing full video bytes in `_render_jobs` with no TTL-based eviction is a denial-of-service surface under adversarial traffic. A malicious client could trigger many renders and exhaust RAM. Implement TTL eviction and size caps.

3. **No authentication observed on job retrieval endpoints** (implicit from both models' discussion of polling endpoints `1691`, `1730`): If `/oracle/job/<id>/audio` and `/oracle/job/<id>/video` are accessible without session validation, any client who guesses a job ID can retrieve another user's audio/video. Validate job ownership against session before serving.

**Priority order:** Job ownership validation → TTL eviction on cache → Temp file cleanup hardening.

---

## WORLD-CLASS GAP CONSENSUS
*(Items 2+ models mentioned as missing from a truly world-class system)*

1. **True Progressive Streaming (Both models):** A world-class avatar system does not wait for complete asset generation. It streams audio chunks to the browser as TTS generates them, begins Wav2Lip inference on early frames while later frames are still being generated, and begins video playback using HTTP chunked transfer or HLS. The current system is batch-oriented end to end. The target architecture should allow the user to hear the first word before the last word has been synthesized.

2. **Push-Based Real-Time Architecture (Both models):** WebSocket or SSE is table-stakes for a conversational AI interface in 2024+. Polling-based delivery creates a ceiling on perceived responsiveness regardless of how fast the backend becomes. This is the architectural foundation that must exist before other latency optimizations deliver their full benefit to users.

3. **Wav2Lip as a Long-Term Bottleneck (Both models):** Both models acknowledged that Wav2Lip, even optimized, will remain the single largest latency component at 1.5–12s depending on clip length. A world-class system would either (a) pre-bake idle/listening avatar loops and composite audio dynamically, (b) evaluate faster inference models, or (c) decouple video generation entirely by playing a high-quality audio response immediately while video renders asynchronously. The current architecture treats video as a prerequisite for user value delivery; a world-class system treats audio as primary and video as progressive enhancement.

---

## FINAL ACTION PLAN

| Priority | Change | File:Line | Models | Why |
|---|---|---|---|---|
| **P0 CRITICAL** | Change ffmpeg encoding preset from `medium` to `ultrafast` | `avatar_server.py:506, 521` | Both | Confirmed regression vs. documented intent. Single change, 4–8s saving, zero downside risk at this scale. |
| **P0 CRITICAL** | Replace frontend polling with WebSocket/SSE push for `audio_ready` and `video_ready` events | `avatar_server.py:1691, 1730` + frontend | Both | Eliminates guaranteed 0–4s idle tax. Prerequisite for all streaming improvements. |
| **P0 CRITICAL** | Refactor `_avatar_tts` to stream TTS chunks progressively over WebSocket/SSE instead of buffering full audio | `avatar_server.py:619–703` | Both | Generator already exists at line 642. Architecture change, not API dependency. Enables <2s audio start. |
| **P1 HIGH** | Combine two sequential ffmpeg subprocess calls (resample + loudnorm) into a single filter chain command | `avatar_server.py:653–687` | Gemini | Eliminates intermediate disk writes, reduces process overhead. Low risk, ~100–300ms saving. |
| **P1 HIGH** | Pipe raw video frames directly to ffmpeg stdin instead of writing intermediate `.avi` file | `avatar_server.py:486–495` | Gemini | Eliminates unnecessary disk I/O in hot path. Medium complexity. ~200–800ms saving. |
| **P1 HIGH** | Adjust `-crf` from 18 to 23–25 alongside preset change to maintain acceptable quality | `avatar_server.py:506, 521` | Gemini (implied) | Ultrafast preset at CRF 18 will produce larger files with marginal quality gain. Balanced trade-off. |
| **P2 MEDIUM** | Store video file path in `_render_jobs` instead of full byte array; serve via `send_file`; implement TTL eviction | `avatar_server.py:1895–1900` | Gemini | Prevents unbounded memory growth under load. Required for production scalability. |
| **P2 MEDIUM** | Add job ownership validation on audio/video retrieval endpoints before serving assets | `avatar_server.py:1730, 1691` | Consensus (implied) | Prevents cross-session asset access via job ID guessing. |
| **P2 MEDIUM** | Investigate graduated Wav2Lip batch size scaling beyond binary 16/48 threshold | `avatar_server.py:338–339` | Grok | Low-risk micro-optimization for mid-length clips. Profile before implementing. |
| **P2 MEDIUM** | Harden temp file cleanup with try/finally blocks in TTS post-processing | `avatar_server.py:653–687` | Gemini | Prevents disk exhaustion from orphaned temp files on pipeline exceptions. |
| **P3 BACKLOG** | Fix or properly re-enable blink engine in `apply_blink_gradient` | `blink_engine.py:261` | Gemini | Functional quality issue. Does not affect latency. Schedule separately. |
| **P3 BACKLOG** | Evaluate Wav2Lip replacement or pre-baked loop architecture for video layer | `avatar_server.py:292–391` | Both | Long-term architectural work. Wav2Lip will remain the compute ceiling regardless of other fixes. |

---

## CYCLE 2 VERDICT

**Not production-ready.** The system has an active regression bug (P0: encoding preset) that alone adds 4–8 seconds to every render, making the stated latency targets physically impossible to achieve. This is not a tuning problem — it is a bug that violates the system's own documented specification.

Beyond the regression, the architecture has two structural flaws (polling, non-streaming TTS) that together guarantee a user experience incompatible with the <5s/<3s targets even if all other components were perfectly optimized.

**Absolute final blocker:** The encoding preset must be corrected before any performance measurement is meaningful. Until line 506 reads `ultrafast`, reported latency numbers are inflated by 4–8s and all benchmark comparisons are invalid.

The good news: the three P0 items are all addressable in a focused implementation sprint. The underlying hardware (dual RTX 4090), the LLM choice (Haiku), and the network layer are all well-configured and should not be touched.

---

## SECOND PASS PROMPT

```
Read ~/protocol_pulse/docs/gospels/PIPELINE_LAWS.md.
Read ~/protocol_pulse/docs/audits/oracle-speed_CONSENSUS_C2.md.

This is the FINAL PASS for oracle-speed.
The feature was reviewed by 2 independent AI models across 2 cycles.
Implement every P0 and P1 item from the consensus. Use judgment on P2.

PRIORITY ACTION PLAN:

P0 CRITICAL | Fix ffmpeg encoding preset regression | avatar_server.py:506, 521
  Change: "-preset", "medium" → "-preset", "ultrafast"
  Also change: "-crf", "18" → "-crf", "23"
  Reason: Confirmed regression vs. header comment line 12. Single largest correctable latency source. 4–8s saving.

P0 CRITICAL | Replace frontend polling with WebSocket/SSE push architecture | avatar_server.py:1691, 1730 + frontend
  Change: Remove 2s polling loop. Establish persistent connection at /oracle/chat time.
  Push "audio_ready" event (with URL or inline bytes) when audio is stored at line 1859.
  Push "video_ready" event (with URL or inline bytes) when video is stored at line 1898.
  Reason: Polling introduces 0–4s guaranteed dead time. Incompatible with <5s target.

P0 CRITICAL | Implement true progressive TTS audio streaming | avatar_server.py:619–703
  Change: Refactor _avatar_tts to yield chunks from the existing Kokoro generator (line 642).
  Transmit each chunk immediately over the WebSocket/SSE connection.
  Do not buffer the full audio before signaling readiness.
  Reason: Generator already exists. This is a code flow fix, not an API capability issue.
  Target: Audio starts playing client-side within 500–800ms of first chunk.

P1 HIGH | Combine TTS ffmpeg post-processing into single command | avatar_server.py:653–687
  Change: Replace two sequential subprocess calls (resample, loudnorm) with one ffmpeg command:
  ffmpeg -i

---

# WINNER DETERMINATION

WINNER: **Gemini** — Gemini delivered the highest-quality analysis across both cycles, correctly identifying the most impactful and actionable finding (the `-preset medium` regression bug) with precise file/line citations and a clear severity framing that proved accurate in Cycle 2 consensus. Its architectural critique of the audio-first pipeline as batch-generation-disguised-as-streaming was more technically precise than Grok's characterization, and its harsher scoring on TTS and streaming architecture was validated as correct by the consensus report's own reasoning.

---

## FINAL SECOND-PASS PRIORITY LIST
*(Definitive ordered implementation plan — highest ROI first)*

---

### P0 — CRITICAL / DO THIS TODAY

**1. Fix Video Encoding Preset Regression**
- **File:** `avatar_server.py:506, 521`
- **Change:** `"-preset", "medium"` → `"-preset", "ultrafast"`, `-crf 18` → `-crf 23`
- **Why first:** Zero architectural risk, one-line fix, 4–8 second saving. This alone may cut total latency by 30–50%. It is a confirmed regression with documented intent.
- **Estimated saving:** 4–8s

---

### P1 — HIGH IMPACT / THIS SPRINT

**2. Replace Frontend Polling with Server-Sent Events (SSE)**
- **File:** Frontend polling loop + `avatar_server.py` job status endpoints
- **Change:** Emit SSE events on job state transitions (`audio_ready`, `video_ready`). Client subscribes once, reacts immediately.
- **Why second:** Eliminates a guaranteed 0–4s dead-time tax applied *twice* (audio wait + video wait). Average saving is ~2s with zero compute cost.
- **Estimated saving:** 1–4s (average ~2s)

**3. Begin Audio Playback Before Video is Ready (True Audio-First)**
- **File:** `avatar_server.py` — `audio_first` flow, ~lines 1857–1939; frontend player logic
- **Change:** As soon as audio bytes exist in the job dict, push them to the client via SSE and begin playback. Do not wait for Wav2Lip render. Video streams in behind audio.
- **Why third:** Currently the system generates audio first but does not deliver it first — the client still waits for the full video pipeline. This is the core architectural fix for hitting <3s audio start.
- **Estimated saving:** 6–12s perceived (audio start decoupled from Wav2Lip)

---

### P2 — MEDIUM IMPACT / NEXT SPRINT

**4. Parallelize TTS and Wav2Lip Preprocessing**
- **File:** `avatar_server.py` — render pipeline sequencing
- **Change:** As soon as LLM response text is available, begin TTS generation. Simultaneously, preload Wav2Lip face detection and frame extraction on the static avatar. Join threads when both are ready.
- **Estimated saving:** 1–2s (overlaps ~2s of prep work)

**5. Eliminate ffmpeg Subprocess for Loudnorm / Resampling in TTS**
- **File:** `avatar_server.py:655–672`
- **Change:** Replace ffmpeg subprocess calls with in-process `librosa` or `scipy` resampling. Loudnorm can be approximated with peak normalization for real-time use.
- **Estimated saving:** 300–800ms per TTS call

**6. Cache Wav2Lip Inference for Repeated Phrases / Intros**
- **File:** `avatar_server.py` — Wav2Lip inference block, ~lines 292–391
- **Change:** Hash (text + voice_id) → store rendered video segment. Serve from cache on repeat. Prioritize common greetings and closing phrases.
- **Estimated saving:** 10–15s on cache hits (full Wav2Lip skip)

---

### P3 — LOWER PRIORITY / FUTURE SPRINT

**7. Upgrade LLM Response Streaming**
- **File:** `oracle_dialogue_engine.py:863–878`
- **Change:** Use Anthropic's streaming API. Begin TTS on first sentence as it arrives rather than waiting for full response completion.
- **Estimated saving:** 400–900ms (TTS starts ~1 sentence earlier)

**8. Wav2Lip Batch Size and Model Quantization Tuning**
- **File:** `avatar_server.py:55` (`batch_size=48`), `model_registry.py:23`
- **Change:** Profile batch sizes 32, 64, 96 on RTX 4090. Evaluate INT8 quantization for Wav2Lip if quality is acceptable.
- **Estimated saving:** 1–4s depending on optimal batch size

**9. Intent Classification LLM Fallback Guard**
- **File:** `oracle_dialogue_engine.py:1441–1459`
- **Change:** Ensure the `oracle_intent` LLM fallback is never triggered on the hot chat path. Add a hard circuit breaker that defaults to `general` intent if regex returns no match.
- **Estimated saving:** 800–1500ms on edge cases that currently fall through to LLM classification

---

## THEORETICAL MAXIMUM SAVING SUMMARY

| Fix | Saving |
|---|---|
| P0: Encoding preset | 4–8s |
| P1: SSE replace polling | 1–4s |
| P1: True audio-first | 6–12s perceived |
| P2: Parallel TTS/prep | 1–2s |
| P2: Remove ffmpeg subprocesses | 0.3–0.8s |
| P2: Wav2Lip cache (hits) | up to 15s |
| P3: LLM streaming | 0.4–0.9s |
| **Conservative combined (no cache)** | **~13–27s** |

**Conclusion:** The <5s perceived latency target and <3s audio start are both achievable with P0 + P1 alone, assuming the audio-first architectural fix is implemented correctly. P2 items push the system into <2s audio start territory on warm paths.