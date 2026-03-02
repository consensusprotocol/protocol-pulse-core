# CLAUDE CODE PROMPT — AVATAR SYSTEM OVERHAUL: GPU CACHING + INSTANT RENDER + VISION GUIDE

## CRITICAL CONTEXT

This task was attempted by a previous Claude Code session and **nothing was built**. The session ran for 2.5 minutes and committed only runtime logs. This time you MUST produce actual code changes. Do not just explore files — BUILD.

## CURRENT STATE

```
# Run these FIRST to understand what exists:
cat ~/protocol_pulse/oracle/avatar_server.py | head -50
wc -l ~/protocol_pulse/oracle/avatar_server.py
# Should be ~613 lines
grep -n "load_model\|torch.load\|Wav2Lip\|checkpoint\|face_detect\|s3fd\|RetinaFace\|batch_size" ~/protocol_pulse/oracle/avatar_server.py
# Check if model reloads per request
ls ~/protocol_pulse/oracle/
# Check avatar server is running:
curl -s http://localhost:8200/health 2>/dev/null || echo "NOT RUNNING"
```

Avatar server: `/home/ultron/protocol_pulse/oracle/avatar_server.py` (~613 lines)
- Voice: Jessica (ElevenLabs ID: cgSgspJ2msm6clMCkdW9)
- Lip-sync: Wav2Lip-GAN (batch_size=48)
- Avatar image: Proto_P_Avatar_512.png
- Running in tmux session `avatar` on port 8200
- Cloudflare tunnel: avatar.protocolpulse.io
- **PROBLEM**: Model reloads from disk every request (~13s overhead)
- 4x RTX 4090 GPUs available (use GPU 0 for avatar)

## DELIVERABLES — ALL THREE ARE REQUIRED

### DELIVERABLE 1: GPU Model Caching (MUST DO)

The Wav2Lip model and face detection model must load ONCE at server startup and stay in GPU VRAM permanently.

**Step-by-step:**

1. Read the entire `avatar_server.py` to understand the current architecture
2. Identify every place a model is loaded (torch.load, load_model, etc.)
3. Create a `ModelRegistry` class or global module-level loading that:
   - Loads Wav2Lip model to GPU 0 at startup
   - Loads face detection model to GPU 0 at startup
   - Pre-detects the reference face from Proto_P_Avatar_512.png
   - Stores all in module-level globals (NOT inside request handlers)
   - Uses FP16 (half precision) for faster inference: `model.half()`
   - Sets eval mode: `model.eval()` and wraps inference in `torch.no_grad()`
4. Modify the request handler to use pre-loaded models instead of loading fresh
5. Add a `/warmup` endpoint that runs a test generation to prime CUDA kernels
6. Add GPU memory reporting to `/health` endpoint

**Verification (you MUST run this):**
```bash
# Restart server with changes
tmux send-keys -t avatar C-c
sleep 3
tmux send-keys -t avatar 'cd ~/protocol_pulse/oracle && python3 avatar_server.py' Enter
sleep 20

# Wait for "Models loaded" message in startup
tmux capture-pane -t avatar -p | tail -10

# Test timing — request 1:
START=$(date +%s%N)
curl -s -X POST http://localhost:8200/generate \
  -H "Content-Type: application/json" \
  -d '{"text":"Testing model cache.","voice_id":"cgSgspJ2msm6clMCkdW9"}' \
  -o /tmp/avatar_test1.mp4
END=$(date +%s%N)
echo "Request 1: $(( (END-START)/1000000 ))ms"
ls -la /tmp/avatar_test1.mp4

# Test timing — request 2 (MUST be faster):
START=$(date +%s%N)
curl -s -X POST http://localhost:8200/generate \
  -H "Content-Type: application/json" \
  -d '{"text":"Second request instant.","voice_id":"cgSgspJ2msm6clMCkdW9"}' \
  -o /tmp/avatar_test2.mp4
END=$(date +%s%N)
echo "Request 2: $(( (END-START)/1000000 ))ms"

# PASS CRITERIA: Request 2 < 5000ms (5 seconds)
# FAIL CRITERIA: Both requests > 10000ms
```

### DELIVERABLE 2: Pre-warm Pipeline

After model caching works, add pre-warming:

1. **Pre-compute reference face** — Run face detection on Proto_P_Avatar_512.png ONCE at startup, cache the bounding box and cropped face tensor
2. **Pre-initialize FFmpeg** — Keep an FFmpeg subprocess pool ready
3. **Async TTS** — Start ElevenLabs audio generation while preparing face frames (asyncio or threading)
4. **Auto-warmup on boot** — After loading models, automatically run one test generation to prime all CUDA kernels

Add startup sequence:
```python
# At server startup (after models load):
print("[WARMUP] Running pipeline warmup...")
warmup_start = time.time()
# Generate a short test video
test_result = generate_avatar("Warmup complete.", voice_id="cgSgspJ2msm6clMCkdW9")
print(f"[WARMUP] Pipeline ready in {time.time()-warmup_start:.1f}s")
print(f"[WARMUP] GPU 0 VRAM: {torch.cuda.memory_allocated(0)/1024**3:.1f}GB used")
```

### DELIVERABLE 3: Vision Guide Endpoints

Add camera/image analysis for hardware setup guidance. Uses Gemini 2.5 Flash (free API).

**Check for Gemini key first:**
```bash
grep -r "GEMINI" ~/protocol_pulse/.env ~/protocol_pulse/config*.py ~/protocol_pulse/oracle/*.py 2>/dev/null
```

If no key exists, the vision endpoints should:
- Return `{"status": "disabled", "reason": "GEMINI_API_KEY not configured", "setup_url": "https://aistudio.google.com/apikey"}`
- NOT crash the server
- Log a clear message at startup

**New endpoints to add to avatar_server.py:**

```python
@app.route('/vision/analyze', methods=['POST'])
def vision_analyze():
    """Analyze uploaded image of Bitcoin hardware, return setup guidance."""
    # Accept multipart image upload
    # Send to Gemini with Bitcoin hardware context prompt
    # Return: device_name, category, setup_steps, guidance_text
    # Generate avatar video of the guidance (optional, based on ?video=true param)
    pass

@app.route('/vision/guide', methods=['POST'])  
def vision_guide():
    """Multi-turn guided setup session with step tracking."""
    # Accept image + session_id + step_number
    # Track session state in memory dict
    # Analyze progress, provide next step
    pass

@app.route('/vision/status', methods=['GET'])
def vision_status():
    """Check if vision features are enabled."""
    pass
```

**Gemini integration:**
```python
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

HARDWARE_PROMPT = """You are the Protocol Pulse Oracle — a Bitcoin hardware expert.
Analyze this image and identify the Bitcoin hardware device.

SECURITY CRITICAL: If you see a seed phrase, private key, or recovery words:
- DO NOT read or repeat them
- Warn user immediately to delete the image

Supported devices: Coldcard, Trezor, Ledger, Foundation Passport, SeedSigner, 
Blockstream Jade, Start9, Umbrel, RaspiBlitz, BitAxe, Antminer, Block Clock, etc.

Respond ONLY in JSON:
{
    "device_name": "...",
    "category": "cold_wallet|node|miner|other",
    "confidence": 0.0-1.0,
    "current_state": "description of what you see",
    "security_alert": null or "warning message",
    "guidance_text": "What the Oracle would say to guide the user (2-3 sentences)",
    "steps": [{"step": 1, "action": "...", "detail": "..."}],
    "next_question": "What to show next"
}"""
```

**Session management for multi-turn guides:**
```python
GUIDE_SESSIONS = {}  # In-memory, cleaned up after 2 hours

class GuideSession:
    def __init__(self, session_id):
        self.id = session_id
        self.device = None
        self.steps_completed = []
        self.created = time.time()
    
    def to_context(self):
        return f"Device: {self.device}, Steps done: {len(self.steps_completed)}"
```

## FILE CHANGES

The main file to modify: `~/protocol_pulse/oracle/avatar_server.py`

You may also create helper files if the server is getting too large:
- `~/protocol_pulse/oracle/model_cache.py` — ModelRegistry class
- `~/protocol_pulse/oracle/vision_guide.py` — Gemini integration + sessions
- `~/protocol_pulse/oracle/gemini_client.py` — Gemini API wrapper

## AFTER BUILDING — RESTART AND VERIFY

```bash
# 1. Restart avatar server
tmux send-keys -t avatar C-c
sleep 5
tmux send-keys -t avatar 'cd ~/protocol_pulse/oracle && python3 avatar_server.py' Enter
sleep 25  # Wait for model loading + warmup

# 2. Check startup output
tmux capture-pane -t avatar -p | grep -E "Models|WARMUP|VRAM|ready|error"

# 3. Test health endpoint
curl -s http://localhost:8200/health | python3 -m json.tool

# 4. Test GPU caching (two requests, second should be fast)
time curl -s -X POST http://localhost:8200/generate \
  -H "Content-Type: application/json" \
  -d '{"text":"Test one.","voice_id":"cgSgspJ2msm6clMCkdW9"}' -o /tmp/t1.mp4
time curl -s -X POST http://localhost:8200/generate \
  -H "Content-Type: application/json" \
  -d '{"text":"Test two.","voice_id":"cgSgspJ2msm6clMCkdW9"}' -o /tmp/t2.mp4

# 5. Test vision status
curl -s http://localhost:8200/vision/status | python3 -m json.tool

# 6. Report file sizes
wc -l ~/protocol_pulse/oracle/*.py
ls -la /tmp/t1.mp4 /tmp/t2.mp4

# 7. Print GPU memory
nvidia-smi --query-gpu=index,memory.used,memory.total --format=csv
```

## SUCCESS CRITERIA

Before you commit, ALL of these must be true:
- [ ] avatar_server.py has ModelRegistry or equivalent global model cache
- [ ] `/health` reports GPU memory and model status
- [ ] Two back-to-back requests: second one < 5 seconds
- [ ] `/vision/status` endpoint exists and returns enabled/disabled
- [ ] `/vision/analyze` endpoint exists (even if Gemini key missing)
- [ ] Server starts without errors
- [ ] At least one test video file generated successfully

## RULES
- Work on `main` branch
- DO NOT just explore files and quit — you MUST produce code changes
- If avatar_server.py is too complex to modify safely, create new files and import them
- Keep Wav2Lip on GPU 0
- git add + commit + push when done
- Minimum output: modified avatar_server.py OR new helper files imported by it
