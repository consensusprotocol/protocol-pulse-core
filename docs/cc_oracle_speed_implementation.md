# ORACLE SPEED OPTIMIZATION — IMPLEMENTATION ROADMAP
# Cross-LLM Audit Synthesis (Gemini 2.5 Pro + Grok-3, 2 cycles)
# Generated: 2026-03-24
# Status: AUDIT COMPLETE — NO CODE CHANGES THIS SESSION

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CURRENT STATE: ~15-25s from user input to avatar speaking
TARGET STATE:  <5s perceived latency, <3s audio start
VERDICT:       Achievable with P0 + P1 fixes (no model swap needed)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## AUDIT METHODOLOGY

- **Models**: Gemini 2.5 Pro, Grok-3 (GPT-4o hit 30K TPM limit on 227K package — excluded)
- **Cycles**: 2 full cycles. Cycle 2 had cross-visibility (each model reviewed the other's C1 output)
- **Winner**: Gemini — identified the encoding preset regression with header comment evidence
- **Consensus Score**: Overall system latency 2/10 (Cycle 2)
- **Artifacts**: `docs/audits/oracle-speed/` — C1_GEMINI.md, C1_GROK.md, C1_CONSENSUS.md, C2_GEMINI.md, C2_GROK.md, FINAL_CONSENSUS.md

## CURRENT LATENCY MODEL (Consensus)

| Step | Function | File:Line | Time (ms) |
|------|----------|-----------|-----------|
| Intent classification | `classify_intent()` | `avatar_server.py:1789` | 5-15 |
| LLM response (Claude Haiku) | `generate_response()` | `dialogue_engine.py:863` | 800-1500 |
| TTS generation (Kokoro) | `_avatar_tts()` | `avatar_server.py:619-703` | 2000-3500 |
| Audio cache in job dict | `_render_jobs[jid]` | `avatar_server.py:1861` | <1 |
| **Frontend poll (audio)** | **polling loop** | **frontend JS** | **0-2000** |
| ffmpeg resample + loudnorm | two subprocess calls | `avatar_server.py:653-687` | 200-500 |
| Wav2Lip inference (FP16) | `wav2lip_generate()` | `avatar_server.py:292-391` | 1500-12000¹ |
| Mouth sharpening (CV2) | `sharpen_mouth_region()` | `face_enhancer.py` | 100-250 |
| Post-processing (head) | `post_process_frames()` | `avatar_server.py:439-474` | 50-200 |
| **Video encoding (BROKEN)** | **`frames_to_video()`** | **`avatar_server.py:506,521`** | **4000-9000²** |
| **Frontend poll (video)** | **polling loop** | **frontend JS** | **0-2000** |
| Network transfer | HTTP response | `avatar_server.py:1691` | 200-800 |
| Browser decode + play | client-side | — | 50-150 |
| **TOTAL** | | | **~9000-32000** |

¹ Gemini estimates 1.5-3s; Grok estimates 10-12s. True value needs profiling.
² `-preset medium` is a regression from documented `-preset ultrafast` (header line 12).

### Where >80% of Latency Lives (Both Models Agree)
1. **Video encoding** (broken preset): 4-9s unnecessary
2. **TTS generation** (no streaming): 2-3.5s before any audio reaches client
3. **Frontend polling** (2× 0-2s): up to 4s of pure dead time
4. **Wav2Lip inference**: 1.5-12s (unavoidable compute, but parallelizable)

---

## TIER 1 — QUICK WINS (<2h each, immediate impact)

### T1.1 — Fix Video Encoding Preset Regression [P0 CRITICAL]
- **File**: `avatar_server.py:506, 521`
- **Change**: `"-preset", "medium"` → `"-preset", "ultrafast"`
- **Also**: `"-crf", "18"` → `"-crf", "23"`
- **Evidence**: Header comment (line 12) documents `CRF 28, preset ultrafast`. Code implements `CRF 18, preset medium`. This is a confirmed regression.
- **Expected savings**: 4000-8000ms per render
- **Risk**: LOW — ultrafast produces larger files but quality difference at 512px is negligible
- **Conflicts**: None
- **Dependencies**: None

### T1.2 — Combine TTS ffmpeg Post-Processing Into Single Command [P1 HIGH]
- **File**: `avatar_server.py:653-687`
- **Current**: Two sequential `subprocess.run()` calls: (1) resample 24kHz→16kHz, (2) loudnorm to -14 LUFS. Each writes intermediate temp files to disk.
- **Change**: Single ffmpeg command with filter chain:
  ```
  ffmpeg -y -loglevel error -i input.wav -af "aresample=16000,loudnorm=I=-14:TP=-1.5:LRA=11" -ac 1 output.wav
  ```
- **Expected savings**: 100-300ms (eliminates subprocess spawn + disk I/O)
- **Risk**: LOW — standard ffmpeg filter chain
- **Dependencies**: None

### T1.3 — Add `torch.compile` to Wav2Lip Model [P1 HIGH]
- **File**: `model_registry.py:77` (after `model.eval()`)
- **Change**: Add `self.wav2lip_model = torch.compile(model, mode="reduce-overhead")`
- **Note**: First inference call will be slow (JIT compilation). Already mitigated by existing 5-frame warmup at startup.
- **Expected savings**: 10-20% inference speedup (~200-600ms on Gemini timing, ~1-2s on Grok timing)
- **Risk**: LOW — requires PyTorch 2.0+ (already in use). May need `torch._dynamo.config.suppress_errors = True` as safety net.
- **Dependencies**: PyTorch 2.0+

### T1.4 — Pre-Render "Thinking" Loop Videos [P1 HIGH]
- **File**: New — extend `oracle_cache_manager.py` or generate at startup
- **What**: Create 2-3 short (3-4s) videos of the Oracle with neutral animation (subtle head movement, blinks disabled currently). No mouth movement, no audio.
- **Use**: `/oracle/chat` returns a thinking video immediately while real render proceeds in background. Frontend plays thinking loop, cross-fades to real video when ready.
- **Expected savings**: 2000-4000ms perceived latency (masks entire LLM+TTS wait)
- **Risk**: LOW — reuses existing `post_process_frames()` pipeline
- **Dependencies**: None

---

## TIER 2 — MEDIUM EFFORT (2-8h each, major impact)

### T2.1 — Replace Frontend Polling with SSE Push [P0 CRITICAL]
- **Files**: `avatar_server.py:1691, 1730` + frontend JS
- **Current**: Frontend polls `/oracle/job/<id>` every 2s. Two poll cycles (audio + video) = 0-4s dead time.
- **Architecture**:
  1. `/oracle/chat` returns `{text, job_id, sse_url}` immediately
  2. Client opens `EventSource` to SSE endpoint
  3. Server pushes events as they occur:
     - `event: audio_ready` → client fetches `/oracle/job/<id>/audio` and plays immediately
     - `event: video_ready` → client fetches `/oracle/job/<id>` and switches video
  4. `render_async` thread pushes to a per-job event queue when audio/video are stored
- **Expected savings**: 1000-4000ms eliminated dead time
- **Risk**: MEDIUM — stateful connection model in Flask threaded mode. Consider `flask-sse` or raw generator with `text/event-stream`.
- **Dependencies**: No new libraries required (Flask supports SSE via Response generators)
- **Conflicts**: None — enhances T1.4 (SSE pushes "switch from thinking to real" event)

### T2.2 — True Audio-First Streaming [P0 CRITICAL]
- **File**: `avatar_server.py:619-703, 1857`
- **Current**: `_avatar_tts()` generates entire audio, buffers it, then stores in job dict. Client can only fetch audio after full TTS completion.
- **Key insight**: Kokoro `KPipeline` already yields chunks via generator (`avatar_server.py:642`). The streaming infrastructure EXISTS but is not used.
- **Architecture**:
  1. Refactor `_avatar_tts()` to yield audio chunks as Kokoro generates them
  2. Each chunk is sent via SSE (from T2.1) as raw bytes or base64
  3. Frontend uses `MediaSource API` or progressive `<audio>` loading
  4. Full audio is simultaneously buffered for Wav2Lip mel spectrogram computation
  5. Wav2Lip begins as soon as full audio is available (no change to Wav2Lip itself)
- **Expected savings**: Audio start from ~3-7s down to ~1.5-2s (first chunk arrives after LLM + first Kokoro yield)
- **Risk**: MEDIUM — requires careful audio format handling for streaming. WAV headers need to be correct for progressive playback. May need to use raw PCM chunks and reconstruct on client.
- **Dependencies**: None (generator exists)

### T2.3 — Pipe Frames to ffmpeg Instead of Intermediate AVI [P1 HIGH]
- **File**: `avatar_server.py:481-537`
- **Current**: All frames written to temp `.avi` via `cv2.VideoWriter`, then ffmpeg reads it back for MP4 encoding. Double disk I/O.
- **Change**: Pipe raw BGR24 frames directly to ffmpeg stdin:
  ```python
  ffmpeg_proc = subprocess.Popen([
      "ffmpeg", "-y", "-loglevel", "error",
      "-f", "rawvideo", "-pix_fmt", "bgr24",
      "-s", f"{w}x{h}", "-r", str(fps),
      "-i", "pipe:0",
      "-itsoffset", "0.08", "-i", audio_path,
      "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
      ...
  ], stdin=subprocess.PIPE, ...)
  for frame in frames:
      ffmpeg_proc.stdin.write(frame.tobytes())
  ffmpeg_proc.stdin.close()
  ffmpeg_proc.wait()
  ```
- **Expected savings**: 200-800ms (eliminates AVI write/read cycle)
- **Risk**: MEDIUM — requires careful frame format alignment. bgr24 from OpenCV matches ffmpeg expectation.
- **Dependencies**: None

### T2.4 — Parallel TTS + Wav2Lip Prep [P2 MEDIUM]
- **File**: `avatar_server.py:1848-1917` (render_async)
- **Current**: Strictly sequential: TTS → ffmpeg resample → Wav2Lip
- **Change**: While TTS runs, pre-load avatar face data and pre-compute anything that doesn't depend on audio. The mel spectrogram requires the full audio, so true parallelism is limited. But face crop + resize (lines 343-348) can be pre-computed.
- **Expected savings**: 100-500ms (modest — most Wav2Lip prep needs audio)
- **Risk**: LOW — face data is already cached in ModelRegistry
- **Dependencies**: None

---

## TIER 3 — MAJOR REBUILD (>8h, maximum impact)

### T3.1 — Streaming Video via fMP4 + Media Source Extensions [P2 MEDIUM]
- **Files**: `avatar_server.py` (new endpoint) + frontend JS (MSE player)
- **What**: Instead of encoding all frames then sending the whole MP4, output fragmented MP4 segments as they encode. Client uses `MediaSource` API to append fragments and begin playback immediately.
- **ffmpeg**: `-movflags frag_keyframe+empty_moov` produces streamable fragments
- **Expected savings**: 5000-10000ms perceived (video starts playing mid-render)
- **Risk**: HIGH — MSE API is complex, cross-browser behavior varies, requires managing chunk boundaries carefully
- **Dependencies**: No server-side deps; significant frontend JS work

### T3.2 — Evaluate Alternative Lip Sync Models [P3 BACKLOG]
- **What**: Wav2Lip is 2019-era. Newer models (LatentSync, Hallo2, SadTalker, GeneFace++) may offer faster inference. Key question is quality parity on a static avatar.
- **Approach**: Set up A/B quality benchmark with 10 test phrases. Compare inference time and visual quality.
- **Expected savings**: If a model runs 2-5× faster than Wav2Lip, saves 1-8s per render
- **Risk**: HIGH — model integration, quality regression risk, potential retraining needed
- **Dependencies**: New model checkpoints, potentially different input formats

### T3.3 — WebRTC for Real-Time Audio/Video Delivery [P3 BACKLOG]
- **What**: Replace HTTP polling/SSE with WebRTC peer connection for sub-100ms delivery
- **Why defer**: SSE achieves <500ms delivery latency, which is sufficient for the target. WebRTC adds massive infrastructure complexity (TURN/STUN servers, NAT traversal, codec negotiation).
- **Risk**: HIGH — infrastructure overhead far exceeds the marginal latency gain vs SSE
- **Dependencies**: TURN/STUN server infrastructure

### T3.4 — Pre-Baked Avatar Loop Architecture [P3 BACKLOG]
- **What**: Instead of Wav2Lip per-request, maintain a library of pre-rendered phoneme-to-mouth-shape video loops. Composite audio onto the correct mouth shapes in real-time using frame selection.
- **Why**: Eliminates Wav2Lip entirely from the hot path. Audio plays immediately; video is assembled from cached frames.
- **Risk**: HIGH — massive R&D effort, visual quality depends on phoneme coverage
- **Dependencies**: Viseme system (partially exists in `oracle/viseme/`)

---

## VALIDATED STRENGTHS — DO NOT TOUCH

Both audit models confirmed these are correct and well-implemented:

1. **FP16 inference on Wav2Lip** (`model_registry.py`, `avatar_server.py:362`)
2. **cudnn.benchmark = True** — appropriate for fixed-size inputs
3. **Intent classification** (`oracle_dialogue_engine.py:1441-1459`) — regex, ~10ms, correct
4. **Claude Haiku model selection** — 800-1500ms is acceptable for quality
5. **GPU assignment** (`cuda:1` for Wav2Lip) — correct isolation
6. **Audio/video endpoint separation** (`/oracle/job/<id>/audio` vs `/oracle/job/<id>`)
7. **Job dictionary architecture** (`_render_jobs`) — sound pattern, polling is the problem

---

## IMPLEMENTATION ORDER (Recommended)

### Phase 1 — Same Day (2h)
1. T1.1: Fix encoding preset (ultrafast + CRF 23)
2. T1.2: Combine ffmpeg post-processing
3. T1.3: Add torch.compile
4. **Benchmark**: Time 10 renders before/after. Expected: 15-25s → 8-15s.

### Phase 2 — Next Day (4-6h)
5. T1.4: Pre-render thinking videos
6. T2.1: SSE push architecture
7. **Benchmark**: Measure perceived latency with thinking video + SSE. Expected: 8-15s → 4-8s perceived.

### Phase 3 — Sprint 1 (8-16h)
8. T2.2: True audio-first streaming via Kokoro generator
9. T2.3: Pipe frames to ffmpeg
10. **Benchmark**: Audio start time. Expected: <2s audio start, <5s perceived video.

### Phase 4 — Sprint 2 (16h+)
11. T2.4: Parallel TTS + Wav2Lip prep
12. T3.1: Streaming video via fMP4 (if needed after Phase 3 benchmarks)
13. Profile Wav2Lip actual timing to resolve the Gemini (1.5-3s) vs Grok (10-12s) conflict

---

## PROJECTED LATENCY AFTER EACH PHASE

| Phase | Audio Start | Perceived Video Start | Total Render |
|-------|------------|----------------------|--------------|
| **Current** | 3-7s | 15-25s | 15-25s |
| **Phase 1** | 3-7s | 8-15s | 8-15s |
| **Phase 2** | 3-7s (thinking masks it) | 4-8s perceived | 8-15s |
| **Phase 3** | **<2s** | **<5s perceived** | 6-12s |
| **Phase 4** | **<1.5s** | **<4s perceived** | 5-10s |

---

## OPEN QUESTIONS (Resolve During Implementation)

1. **Wav2Lip actual inference time**: Need to profile. If it's truly 10-12s (Grok), then T3.2 (model replacement) moves up to Tier 2 priority. If it's 1.5-3s (Gemini), the encoding fix alone gets us close to target.

2. **Kokoro streaming chunk format**: Does Kokoro yield PCM numpy arrays or full WAV segments? The streaming architecture (T2.2) depends on chunk format. Verify the generator output before designing the SSE payload.

3. **flask-sse vs raw generator**: Flask's threaded mode may have issues with long-lived SSE connections under load. May need to evaluate `gevent` or a separate SSE microservice.

4. **Cache warmer + interactive GPU contention**: After T1.1 makes encoding fast, does the cache warmer still cause interactive latency? Profile to determine if CUDA stream priority (T2 extension) is needed.

---

## COMMIT SCOPE (This Session)

Audit artifacts only — no code changes:
- `docs/audits/oracle-speed/` — all C1/C2 outputs + consensus
- `docs/cc_oracle_speed_implementation.md` — this file
- `utils/cross_llm_audit.py` — oracle-speed registration
- `docs/audits/AUDIT_REGISTRY.json` — updated registry
