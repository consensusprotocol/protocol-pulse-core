# Satomi Latency Audit

**Date:** 2026-04-07
**Auditor:** Claude Opus 4.6 (read-only audit — zero code changes)
**System:** Oracle Avatar Server v3 on Ultron (RTX 4090, CUDA:1)
**Reported Latency:** 27 seconds end-to-end
**Health Endpoint Avg:** 14.29s

---

## Current Pipeline Architecture

```
User speaks → Browser sends text
    ↓
[1] LLM Response Generation (Claude Haiku 4.5 via API)
    ↓
[2] TTS (Kokoro af_heart on cuda:1, fallback: ElevenLabs API)
    ↓
[3] FFmpeg resample (24kHz → 16kHz mono WAV)
    ↓
[4] Wav2Lip FP16 inference (cuda:1, batch=48)
    ↓
[5] CV2 bilateral mouth sharpening
    ↓
[6] Post-processing (MediaPipe blinks + head movement)
    ↓
[7] FFmpeg encode (CRF 23, ultrafast, 512px output)
    ↓
[8] Serve MP4 to browser
```

---

## Current Pipeline Timing (Measured from Logs)

### Stage-by-Stage Breakdown (April 7, 2026 logs — 10 renders)

| Stage | Short (~6s video) | Typical (~10-13s video) | Long (~18-25s video) | Notes |
|---|---|---|---|---|
| **LLM (Haiku 4.5)** | ~0.8-1.2s | ~0.8-1.2s | ~0.8-1.2s | 55-word cap, 180 max_tokens |
| **TTS (Kokoro)** | 1.2-2.0s | 2.0-4.0s | 4.0-18.6s | GPU-local, af_heart voice |
| **FFmpeg resample** | ~0.1s | ~0.1s | ~0.1s | 24kHz→16kHz, trivial |
| **Wav2Lip FP16** | 2.8-3.0s | 3.2-4.4s | 4.9-6.6s | Batch=48, ~100+ fps |
| **CV2 sharpen** | 0.1-0.2s | 0.6-1.5s | 1.5-2.2s | CPU-bound per-frame |
| **Post-process** | 0.0-0.4s | 1.0-1.4s | 1.4-2.4s | Blinks + head, CPU |
| **FFmpeg encode** | 0.6-1.7s | 2.4-4.8s | 4.1-6.6s | CRF 23, ultrafast, 512px |
| **TOTAL (logged)** | 1.5-5.5s | 7.4-12.3s | 10.5-18.0s | Render only |

### Actual Measured Totals from Today's Logs

```
Complete: 25.4s video, 762 frames, lip=6.6s enhance=2.2s post=2.4s enc=6.6s total=18.0s
Complete: 15.4s video, 463 frames, lip=3.9s enhance=1.1s post=1.4s enc=4.1s total=10.5s
Complete:  6.0s video, 181 frames, lip=3.0s enhance=0.2s post=0.4s enc=1.7s total= 5.5s
Complete: 18.6s video, 557 frames, lip=4.4s enhance=1.5s post=1.4s enc=4.8s total=12.3s
Complete:  9.1s video, 273 frames, lip=3.2s enhance=0.6s post=1.0s enc=2.4s total= 7.4s
Complete: 12.9s video, 386 frames, lip=3.5s enhance=1.1s post=1.0s enc=3.4s total= 9.1s
Complete: 12.0s video, 361 frames, lip=3.4s enhance=1.0s post=1.1s enc=3.2s total= 8.8s
Complete:  8.7s video, 262 frames, lip=2.8s enhance=0.7s post=0.4s enc=2.3s total= 6.4s
Complete: 15.7s video, 472 frames, lip=4.9s enhance=1.3s post=1.2s enc=4.1s total=11.7s
Complete:  1.8s video,  53 frames, lip=0.7s enhance=0.1s post=0.0s enc=0.6s total= 1.5s
```

### Why "27 seconds" vs "14.29s avg"

The 14.29s health-endpoint average covers only the **render pipeline** (stages 4-7). The full user-perceived latency includes:

| Component | Time | Source |
|---|---|---|
| LLM response (Haiku API call) | ~1.0s | Network + inference |
| TTS (Kokoro on GPU) | ~2-4s typical | Shared cuda:1 with Wav2Lip |
| FFmpeg resample | ~0.1s | Trivial |
| **Render pipeline** | ~7-12s | Wav2Lip + enhance + post + encode |
| HTTP response transfer | ~0.5-1s | Cloudflare tunnel + browser |
| Browser video decode + play | ~0.3s | Client-side |

**Typical total: ~12-18s. Worst case (long responses, GPU contention): 25-30s.**

The 27s user report likely includes a long response (>15s video) plus GPU contention from the cache warmer.

---

## Bottleneck Analysis (Ranked by Time Contribution)

### 1. FFmpeg Encoding — 25-37% of render time
- CRF 23 + ultrafast + 512px output
- 2.4-6.6s depending on frame count
- **Uses CPU (libx264), not GPU NVENC**
- This is the single biggest optimization opportunity

### 2. Wav2Lip Inference — 25-37% of render time
- Already FP16 on RTX 4090
- 2.8-6.6s, scales linearly with frame count
- Batch size 48 is well-tuned (tested, 64 causes VRAM pressure)
- torch.compile was tested but causes 10-50x regression (documented in model_registry.py:77)

### 3. TTS (Kokoro af_heart) — Variable, 1.2-18.6s
- Runs on cuda:1 (SAME GPU as Wav2Lip)
- Short text: 1.2-4s. Long cache warm text: 16-23s
- **GPU contention**: Kokoro and Wav2Lip share cuda:1
- The 55-word cap in dialogue_engine helps, but cache warming uses full-length text (200+ chars)

### 4. Post-Processing (CPU) — 8-13% of render time
- CV2 sharpen: per-frame CPU bilateral filter
- Blinks + head movement: per-frame CPU transforms
- Combined 1.6-4.6s for typical videos
- **Entirely CPU-bound, could be parallelized or GPU-accelerated**

### 5. GPU Contention — Cache Warmer vs Interactive
- Cache warmer renders 11 responses every 2 hours
- While warming, interactive requests get blocked or deferred
- Log evidence: Many "deferred - interactive request has GPU priority" messages
- March 22 session: ALL 11 cache renders timed out (180s each) — GPU was starved

---

## Optimization Opportunities (Ranked by Impact)

### TIER 1: Quick Wins (< 1 hour, low risk)

#### 1.1 Switch to NVENC Hardware Encoding
- **Current**: `libx264 -preset ultrafast -crf 23` (CPU encoding)
- **Proposed**: `h264_nvenc -preset p4 -rc vbr -cq 23` (GPU encoding)
- **Expected savings**: 60-80% encoding time reduction (2.4-6.6s → 0.5-1.5s)
- **Risk**: Low — NVENC runs on a separate ASIC, doesn't compete with CUDA cores
- **RTX 4090 has dedicated NVENC chip** — currently completely unused
- **Complexity**: 30 min — change 2 lines in `frames_to_video()`

#### 1.2 Skip AVI Intermediate in frames_to_video()
- **Current**: frames → OpenCV MJPEG AVI → ffmpeg → MP4
- **Proposed**: Pipe raw frames directly to ffmpeg via stdin (`-f rawvideo`)
- **Expected savings**: 0.3-0.5s (eliminates disk I/O for intermediate file)
- **Risk**: Low — standard ffmpeg pipe pattern
- **Complexity**: 30 min

#### 1.3 Reduce MAX_RESPONSE_WORDS from 55 to 35
- **Current**: 55-word cap allows 15-20s videos
- **Proposed**: 35-word cap → ~8-10s videos max
- **Expected savings**: 30-40% render time on the longest responses
- **Risk**: Medium — changes Satomi's personality feel (shorter answers)
- **Complexity**: 5 min — one constant change in dialogue_engine.py

### TIER 2: Medium Effort (1-4 hours, medium risk)

#### 2.1 Pipeline Parallelism: Overlap TTS + Encoding
- **Concept**: Start Wav2Lip on first TTS chunk while rest of TTS is still generating
- **Current**: TTS completes fully → then Wav2Lip starts
- **Proposed**: Sentence-level TTS → immediate Wav2Lip per sentence → concat
- **Expected savings**: 2-4s (TTS and Wav2Lip overlap)
- **Risk**: Medium — already partially implemented via `/generate_stream`, but not the default path
- **Complexity**: 3-4 hours to make it the primary `/oracle/chat` path

#### 2.2 GPU-Accelerate Post-Processing
- **Current**: CV2 sharpen + blinks + head movement all CPU per-frame
- **Proposed**: Batch all frames into a GPU tensor, apply sharpening via torch convolution
- **Expected savings**: 50-70% of post-processing time (1.6-4.6s → 0.5-1.5s)
- **Risk**: Medium — needs careful testing of visual quality
- **Complexity**: 2-3 hours

#### 2.3 Move Kokoro TTS to cuda:0 (Separate GPU)
- **Current**: Kokoro and Wav2Lip both on cuda:1
- **Proposed**: Kokoro on cuda:0 (or CPU fallback)
- **Expected savings**: Eliminates GPU contention during interactive requests
- **Risk**: Medium — cuda:0 may be used by video pipeline renders
- **Complexity**: 1 hour — change one device string + test

#### 2.4 Audio-First Response Pattern (Already Exists)
- **Status**: `audio_first=True` flag exists in `/oracle/chat`
- **Current behavior**: Returns text + job_id immediately, renders video in background
- **Frontend sends audio via SSE, polls for video**
- **Gap**: Frontend may not be using this optimally — user sees thinking loop for full duration
- **Expected savings**: Perceived latency drops to ~3-5s (audio plays while video renders)
- **Complexity**: 1-2 hours frontend work to polish the experience

#### 2.5 Pre-render Cache Warming Fix
- **Issue**: Cache warming on March 22 caused ALL 11 renders to timeout (180s each)
- **Issue**: Cache warming on April 7 deferred 8/9 keys due to "interactive request has GPU priority"
- **Proposed**: Stagger cache warming to off-peak hours, limit to 3 renders per cycle
- **Expected savings**: Eliminates interactive latency spikes during cache warm
- **Risk**: Low — only affects background behavior
- **Complexity**: 1 hour

### TIER 3: Major Effort (4-16 hours, higher risk)

#### 3.1 Replace Wav2Lip with MuseTalk
- **MuseTalk** (Tencent): 30+ fps real-time, latent-space inpainting
- RTX 4090 benchmark: batch=4 achieves 1.14s inference latency
- **Expected savings**: Wav2Lip 3-6s → MuseTalk 1-2s for same content
- **Risk**: High — different visual quality, may need avatar re-tuning
- **Complexity**: 8-16 hours (new model pipeline, testing, quality validation)

#### 3.2 Streaming Video Delivery (Chunked Rendering)
- **Concept**: Render and send first 3 seconds of video immediately, stream rest
- **Current**: Full video must complete before any bytes sent
- **Proposed**: WebSocket or chunked transfer encoding, sentence-level video segments
- **Expected savings**: First visual response in 3-5s regardless of total length
- **Risk**: High — complex frontend/backend coordination, buffering issues
- **Complexity**: 8-12 hours

#### 3.3 TensorRT or ONNX Acceleration for Wav2Lip
- **ONNX Runtime**: wav2lip-onnx-256 project exists (256x256 resolution)
- **TensorRT**: Could provide 2-3x speedup on RTX 4090
- **Expected savings**: Wav2Lip 3-6s → 1-3s
- **Risk**: High — model conversion quality, FP16 compatibility
- **Complexity**: 6-10 hours

---

## Cross-LLM Recommendations

### From Competitive Research

| Approach | Expected Impact | Source |
|---|---|---|
| NVENC encoding | 60-80% encode speedup | NVIDIA Video SDK docs |
| MuseTalk replacement | 2-3x Wav2Lip speedup | Tencent research, 30+ fps V100 |
| Pipeline parallelism (TTS ∥ Wav2Lip) | 2-4s savings | arxiv:2512.18318 |
| AvatarForcing (one-step diffusion) | 34ms/frame streaming | arxiv:2603.14331 |
| Sentence-chunked delivery | First response in 3-5s | Industry pattern (HeyGen, D-ID) |

### Key Insight: HeyGen/D-ID Achieve 3-8s Because
1. **Pre-rendered avatar meshes** — no per-frame face detection
2. **Cloud GPU clusters** — dedicated encoding ASICs
3. **Streaming delivery** — first frames sent before full render completes
4. **Optimized models** — proprietary, not open-source Wav2Lip
5. **Lower quality threshold** — 480p, 24fps, simpler post-processing

---

## Cache System Analysis

### Pre-Cached Responses (11 keys)
```
GREETING              — 11.83s video (instant serve, ~598KB)
SOVEREIGNTY_INTRO     — 15.43s video
SOVEREIGNTY_ASSESSMENT — 14.87s video
SOVEREIGNTY_COLD_WALLET — 13.77s video
SOVEREIGNTY_NODE      — 14.40s video
SOVEREIGNTY_BITAXE    — 17.00s video
SOVEREIGNTY_LIFE_INSURANCE — 17.80s video
SOVEREIGNTY_RESIDENCY — 16.11s video
DAILY_BRIEF_INTRO     — 7.41s video
UNKNOWN_QUESTION      — 8.18s video
GOODBYE               — 5.23s video
```

### Cache Hit Behavior
- Greetings: 3 rotation variants, instant serve (~0ms latency)
- Intent classification: regex patterns → if confidence ≥ 0.8, serve cached video
- Turn > 0 skips cache (conversational context needed)
- Cache TTL: 2 hours, warm cycle every 2 hours

### Cache Effectiveness Issues
- **March 22**: ALL 11 cache renders timed out → no cache available at all
- **April 7**: Only SOVEREIGNTY_INTRO cached successfully; 8 keys deferred
- **Root cause**: Cache warmer competes with interactive requests for GPU
- **Greeting cache works perfectly**: Pre-rendered, instant serve, good rotation

### Cache Expansion Opportunities
- Top 10 most-asked questions could be pre-cached
- Common follow-ups ("what is bitcoin", "how to buy", "what is mining") are predictable
- Daily brief could be pre-rendered at scheduled times (not on-demand)

---

## TTS Analysis

### Primary: Kokoro af_heart (Local GPU)
- Model: Kokoro-82M on cuda:1
- Output: 24kHz numpy → ffmpeg resample to 16kHz mono WAV
- Latency range (from logs):
  - Short text (~30 words): 1.2-4.0s
  - Medium text: 3.0-6.0s
  - Long text (cache warming, 200+ chars): 16.5-23.8s
- **Problem**: Shares cuda:1 with Wav2Lip — contention during concurrent use

### Fallback: ElevenLabs API
- Voice: Jessica (cgSgspJ2msm6clMCkdW9)
- Model: eleven_turbo_v2_5
- Additional latency: ~0.5-1.5s network round-trip
- Only triggered when Kokoro fails

### TTS Optimization Notes
- Kokoro's `loudnorm` ffmpeg pass adds ~0.3s — could be deferred or removed
- The resample (24kHz → 16kHz) adds ~0.1s — necessary for Wav2Lip
- Kokoro's 82M parameter model is already tiny; faster models (Piper, eSpeak) sacrifice quality

---

## LLM Response Analysis

### Model: Claude Haiku 4.5 (claude-haiku-4-5-20251001)
- max_tokens: 180 (maps to ~30 words after safety buffer)
- Timeout: 12 seconds
- Fallback: Gemini 2.5 Flash (on billing errors)
- Word cap: 55 words (MAX_RESPONSE_WORDS in dialogue_engine.py:27)
- Actual outputs: 24-44 words observed in logs

### LLM Latency
- Consistently ~0.8-1.2s for Haiku responses
- This is already near-optimal — Haiku is the fastest Claude model
- Not a meaningful bottleneck

---

## Competitive Gap Analysis

| Metric | Satomi (Current) | HeyGen | D-ID | Gap |
|---|---|---|---|---|
| First audio | ~3-5s | ~2s | ~1s | 2-4s behind |
| First video frame | ~10-18s | ~5s | ~3s | 7-15s behind |
| Full video complete | ~12-27s | ~5-8s | ~3-5s | 7-22s behind |
| Video quality | 512px, 30fps, CRF 23 | 1080p | 720p | Behind on res |
| Cost per response | ~$0.002 (API) + GPU | $0.01-0.05 | $0.01-0.05 | Cheaper |
| Self-hosted | Yes (RTX 4090) | No (cloud) | No (cloud) | Advantage |

### What It Would Take to Match HeyGen (5-8s)

1. **NVENC encoding**: -3s (encoding 6s → 1.5s)
2. **Audio-first delivery**: -5s perceived (audio plays at 3s, video at 10s)
3. **Reduce word cap to 35**: -2s (shorter videos)
4. **GPU separation (Kokoro on cuda:0)**: -1s contention
5. **Combined effect**: ~5-8s perceived latency (audio-first), ~8-10s full video

### What It Would Take to Match D-ID (3-5s)

All of the above, plus:
- Replace Wav2Lip with MuseTalk or TensorRT-optimized model
- Streaming video delivery (first chunk at 3s)
- This is a significant engineering effort (2-3 weeks)

---

## Recommended Action Plan

### Phase 1: Quick Wins (Today, 1-2 hours total)
1. **NVENC encoding** — biggest single win, ~3s savings, 30 min work
2. **Skip AVI intermediate** — 0.3-0.5s savings, 30 min work
3. **Ensure audio-first is default** — drops perceived latency to ~3-5s

### Phase 2: Medium Optimizations (This week, 4-6 hours)
4. **Move Kokoro to cuda:0** — eliminates GPU contention
5. **GPU-accelerate post-processing** — 1-2s savings
6. **Fix cache warmer staggering** — eliminates interactive latency spikes

### Phase 3: Architecture Improvements (Next sprint, 8-16 hours)
7. **MuseTalk evaluation** — potential 2-3x Wav2Lip speedup
8. **Streaming video delivery** — first visual at 3-5s regardless of length

### Projected Latency After Phase 1+2
- **Perceived (audio-first)**: 3-5s (matches HeyGen)
- **Full video complete**: 6-10s (competitive with HeyGen)
- **Worst case (long response)**: 12-15s (down from 27s)

---

## Summary

The 27-second latency is caused by three compounding factors:
1. **CPU encoding (libx264)** consuming 25-37% of render time when NVENC is available
2. **GPU contention** between Kokoro TTS and Wav2Lip on the same cuda:1 device
3. **Sequential pipeline** — each stage waits for the previous to fully complete

The audio-first pattern already exists in the codebase but may not be the default frontend behavior. Enabling it alone would cut perceived latency to 3-5 seconds. Combined with NVENC encoding and GPU separation, Satomi could match HeyGen-tier responsiveness within a few hours of work.

---

*Audit complete. No code was changed. This document is read-only analysis.*
