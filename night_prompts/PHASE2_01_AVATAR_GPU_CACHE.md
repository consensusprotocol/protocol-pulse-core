# AVATAR GPU CACHING + VISION GUIDE — EXECUTE NOW

CRITICAL: Do NOT use planning mode or todolists. Do NOT show a plan and ask to proceed. Start writing code IMMEDIATELY. Every minute you spend planning is a minute wasted.

## CONTEXT

You already analyzed this codebase in a previous session and created a plan. The plan was correct. Now EXECUTE it. Here's what you found:

- avatar_server.py is 613 lines at ~/protocol_pulse/oracle/avatar_server.py
- Models ARE loaded once at startup BUT inference is FP32 (slow)
- Face detection re-runs every request (wasteful — reference face is always the same)
- PyTorch 2.10 + CUDA 12.8 — torch.compile() fully supported
- 4x RTX 4090 available, GEMINI_API_KEY is set
- Current latency: 13-15s per request

## TASK 1: Create ~/protocol_pulse/oracle/model_registry.py

A singleton that:
- Loads Wav2Lip model ONCE in FP16
- Loads face detection model ONCE
- Pre-computes reference face from Proto_P_Avatar_512.png (detect + crop ONCE)
- Applies torch.compile(mode="reduce-overhead") to Wav2Lip
- Pins to GPU 0
- Exposes get() method for cached models
- Prints VRAM usage after loading

Look at the EXISTING avatar_server.py to find the exact model loading code and replicate it in the registry.

## TASK 2: Create ~/protocol_pulse/oracle/vision_guide.py

Gemini 2.5 Flash integration for hardware setup guidance:
- analyze_image(image_b64, mime_type, context) → JSON with device_name, category, steps, guidance_text
- GuideSession class for multi-turn setup walks
- GEMINI_API_KEY from environment
- System prompt: Bitcoin hardware expert (Coldcard, Trezor, BitAxe, Start9, etc.)
- SECURITY: Never read/repeat visible seed phrases — warn user immediately
- Graceful disable if no API key

## TASK 3: Create ~/protocol_pulse/oracle/gemini_client.py

Thin wrapper:
- POST to https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent
- Handle API errors, timeouts, JSON parsing
- Rate limiting (60 RPM free tier)

## TASK 4: Update avatar_server.py

- Import and use ModelRegistry instead of loading models inline
- Add /warmup endpoint (generates test video on startup)
- Add /vision/analyze endpoint (image upload → Gemini analysis → avatar response)
- Add /vision/guide endpoint (multi-turn with session_id)
- Add /health endpoint that shows: model loaded (bool), VRAM usage, vision enabled, uptime, avg latency

## TASK 5: Restart avatar server and test

```bash
# Kill old server
tmux send-keys -t avatar C-c
sleep 3
# Start new one
tmux send-keys -t avatar 'cd ~/protocol_pulse/oracle && python3 avatar_server.py' Enter
sleep 20

# Test timing improvement
time curl -s -X POST http://localhost:8200/generate \
  -H "Content-Type: application/json" \
  -d '{"text":"Testing.","voice_id":"cgSgspJ2msm6clMCkdW9"}' -o /tmp/t1.mp4
time curl -s -X POST http://localhost:8200/generate \
  -H "Content-Type: application/json" \
  -d '{"text":"Second test.","voice_id":"cgSgspJ2msm6clMCkdW9"}' -o /tmp/t2.mp4

# Test health
curl -s http://localhost:8200/health | python3 -m json.tool
```

## TASK 6: Git commit and push

```bash
cd ~/protocol_pulse && git add -A && git commit -m "feat(oracle): GPU model cache + FP16 + vision guide endpoints" && git push origin main
```

Report: timing before vs after, VRAM usage, files created, vision endpoints status.

START WRITING CODE NOW. Do not plan. Do not ask for confirmation. Execute.
