Read ~/protocol_pulse/PIPELINE_LAWS.md.
Read ~/protocol_pulse/oracle/avatar_server.py FULLY — every line.
Read ~/protocol_pulse/oracle/oracle_cache_manager.py FULLY.
Read ~/protocol_pulse/oracle/cache_render_helper.py FULLY.
Read ~/protocol_pulse/oracle/model_registry.py FULLY.
Read ~/protocol_pulse/templates/oracle_live.html lines 750-900 (JS polling/playback logic).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ORACLE + STAGE AVATAR — MAXIMUM SPEED CROSS-LLM AUDIT
Goal: find every millisecond of latency and eliminate it.
Current: ~15-25s from user input to avatar speaking.
Target: <5s perceived latency. Sub-3s audio start.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STEP 1 — REGISTER FEATURE
Add to utils/cross_llm_audit.py FEATURE_MAP:
  "oracle-speed": ("PIPELINE_LAWS.md", "main")

EXPLICIT_FILES["oracle-speed"] = [
    "oracle/avatar_server.py",
    "oracle/oracle_cache_manager.py",
    "oracle/cache_render_helper.py",
    "oracle/model_registry.py",
]

STEP 2 — FIRE CYCLE 1 AUDIT
Each of Gemini, GPT-4o, Grok answers these 8 questions
independently having read the FULL codebase above:

Q1 — CURRENT LATENCY BREAKDOWN:
Map every step from POST /oracle/chat to avatar speaking in browser.
Give realistic millisecond estimates for each step:
  - Intent classification
  - Response text generation
  - ElevenLabs TTS call
  - Wav2Lip inference (batch_size=48, FP16, 4090)
  - Video encoding (CRF28 ultrafast)
  - Network transfer to browser
  - Browser decode + play
Where is >80% of latency concentrated?

Q2 — AUDIO-FIRST STREAMING (already partially built):
The job_id system exists. Audio is fetched first via /oracle/job/<id>/audio.
What is broken/suboptimal in this flow?
How can we get audio to browser in <2s from request?
Specifically: can TTS run before Wav2Lip starts? Can audio stream
to browser while video is still rendering?

Q3 — WAV2LIP OPTIMIZATION:
Current: batch_size=48, FP16, CRF28 ultrafast, cuda:1.
What are the fastest possible Wav2Lip settings on RTX 4090?
Should batch_size increase beyond 48? What is the GPU memory limit?
Is torch.compile applicable here for further speedup?
Is there a faster lip sync model available in 2025/2026 that
maintains quality? (LatentSync, Hallo2, AniPortrait, etc.)

Q4 — STREAMING VIDEO DELIVERY:
Currently: full video renders, then downloads to browser, then plays.
Can we stream the video as it renders using chunked transfer or HLS?
What is the minimum chunk size for acceptable lip sync quality?
How would the frontend JS need to change to support streaming playback?

Q5 — PARALLEL PIPELINE:
Currently: TTS → Wav2Lip sequential.
Can TTS and Wav2Lip preparation (face detection, mel spectrogram)
run in parallel? What is the theoretical minimum latency if
audio generation and video prep are fully parallelized?

Q6 — PRE-PREDICTION:
The INTENT_PATTERNS dict exists. When a user asks about "cold wallet",
we know before they finish speaking what response is likely.
Can we pre-render the response video while they're still asking?
What would the architecture look like?

Q7 — CACHE ARCHITECTURE:
Current cache warms 11 SOVEREIGNTY keys sequentially on startup.
The cache is blocking interactive requests (root cause of tonight's issues).
What is the optimal caching strategy?
Should cache renders run at low priority on a separate CUDA stream?
Should we cache short 2-3s "thinking" clips to play while rendering?

Q8 — FRONTEND LATENCY:
The oracle_live.html polls /oracle/job/<id> every 2 seconds.
What is the fastest delivery mechanism?
SSE (Server-Sent Events)? WebSocket? WebRTC?
How would we push the rendered video/audio to the browser
the instant it's ready without polling?

python3 utils/cross_llm_audit.py --feature oracle-speed 2>&1
Save: docs/audits/oracle_speed_c1.json

STEP 3 — CYCLE 2 CROSS-EXAMINATION
python3 utils/cross_llm_audit.py --feature oracle-speed \
  --cycle 2 --cycle1-results docs/audits/oracle_speed_c1.json
Save: docs/audits/oracle_speed_c2.json

STEP 4 — SYNTHESIZE AND WRITE OPTIMIZATION SPEC

After reading both audit cycles, write a prioritized implementation plan:

TIER 1 — Quick wins (<2h each, immediate impact):
  List specific code changes with file + line numbers

TIER 2 — Medium effort (2-8h each, major impact):
  Architecture changes with spec

TIER 3 — Major rebuild (>8h, maximum impact):
  Streaming/WebRTC/new model recommendations

For each recommendation include:
  - Expected latency reduction (ms)
  - Implementation risk (low/medium/high)
  - Whether it conflicts with existing code
  - Whether it requires new dependencies

Write final spec to: docs/cc_oracle_speed_implementation.md

STEP 5 — COMMIT AUDIT ARTIFACTS ONLY
git add docs/audits/oracle_speed_c1.json \
  docs/audits/oracle_speed_c2.json \
  docs/cc_oracle_speed_implementation.md \
  utils/cross_llm_audit.py
git commit -m "audit(oracle-speed): cross-LLM speed audit — full codebase analysis, optimization roadmap"
git push

DO NOT implement any changes in this session.
This session produces the roadmap. Implementation fires next.
