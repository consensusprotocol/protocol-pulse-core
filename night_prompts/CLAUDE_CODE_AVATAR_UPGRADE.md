# CLAUDE CODE PROMPT — AVATAR UPGRADE: GPU CACHING + INSTANT RENDER + VISION GUIDE

## MISSION

Three critical upgrades to the Protocol Pulse Oracle Avatar system:

1. **FIX GPU MODEL CACHING** — Wav2Lip model reloads from disk every request (13s). Make it load ONCE at startup and stay in GPU VRAM permanently. Target: <2s response time after first load.

2. **PRE-WARM AVATAR PIPELINE** — Pre-compute face detection, load face reference frames, keep FFmpeg ready. The avatar should respond in under 2 seconds for short utterances.

3. **INTERACTIVE VISION GUIDE** — Add camera/image input so users can show their hardware (cold wallet, Bitcoin node, BitAxe miner) and the Oracle guides them through setup step-by-step by analyzing what it sees.

## PRIORITY: THIS RUNS FIRST — IT UNBLOCKS ALL OTHER AVATAR WORK

## PART 1: GPU MODEL CACHING (CRITICAL)

### Current Problem

Location: `/home/ultron/protocol_pulse/oracle/avatar_server.py`

The avatar server reloads models from disk on every single request:
```bash
# Verify the problem:
cat ~/protocol_pulse/oracle/avatar_server.py | grep -n "load_model\|torch.load\|Wav2Lip\|checkpoint\|face_detect\|s3fd\|RetinaFace"
```

Expected findings:
- Wav2Lip model loads from .pth file (~13s)
- Face detection model (s3fd or RetinaFace) loads separately
- No global model cache — everything re-initializes per request

### The Fix

```python
# === GLOBAL MODEL REGISTRY — LOAD ONCE, USE FOREVER ===

import torch
import threading

class ModelRegistry:
    """Singleton model cache — loads once, stays in GPU VRAM."""
    
    _instance = None
    _lock = threading.Lock()
    _models = {}
    _initialized = False
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def load_all(self, device='cuda:0'):
        """Pre-load ALL models at server startup."""
        if self._initialized:
            return
        
        import time
        start = time.time()
        
        print("[ModelRegistry] Loading Wav2Lip model...")
        self._models['wav2lip'] = self._load_wav2lip(device)
        
        print("[ModelRegistry] Loading face detection model...")
        self._models['face_det'] = self._load_face_detection(device)
        
        print("[ModelRegistry] Pre-computing reference face...")
        self._models['ref_face'] = self._precompute_reference_face()
        
        self._initialized = True
        elapsed = time.time() - start
        print(f"[ModelRegistry] All models loaded in {elapsed:.1f}s — VRAM locked")
        
        # Print GPU memory usage
        for i in range(torch.cuda.device_count()):
            mem = torch.cuda.memory_allocated(i) / 1024**3
            total = torch.cuda.get_device_properties(i).total_mem / 1024**3
            print(f"  GPU {i}: {mem:.1f}GB / {total:.1f}GB")
    
    def get(self, name):
        if not self._initialized:
            raise RuntimeError("ModelRegistry not initialized — call load_all() first")
        return self._models[name]
    
    def _load_wav2lip(self, device):
        # Find the actual loading code in avatar_server.py and replicate it here
        # The model should be loaded with torch.load() and moved to device
        # Then set to eval() mode and torch.no_grad() context
        pass  # IMPLEMENT based on existing code
    
    def _load_face_detection(self, device):
        # Load s3fd or RetinaFace model
        pass  # IMPLEMENT based on existing code
    
    def _precompute_reference_face(self):
        # Load Proto_P_Avatar_512.png
        # Run face detection ONCE
        # Cache the bounding box + cropped face
        # This avoids re-detecting the face every request
        pass  # IMPLEMENT

# At server startup:
registry = ModelRegistry.get_instance()
registry.load_all(device='cuda:0')

# In request handler — use cached models:
def generate_avatar(audio_data):
    model = registry.get('wav2lip')
    face_det = registry.get('face_det')
    ref_face = registry.get('ref_face')  # Pre-computed, instant
    # ... rest of pipeline using cached models
```

### Verification

```bash
# Start the server, wait for "All models loaded" message
# Then time two consecutive requests:

# Request 1:
time curl -s -X POST https://avatar.protocolpulse.io/generate \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello, this is a test.","voice_id":"cgSgspJ2msm6clMCkdW9"}' \
  -o /tmp/test1.mp4

# Request 2 (should be MUCH faster):
time curl -s -X POST https://avatar.protocolpulse.io/generate \
  -H "Content-Type: application/json" \
  -d '{"text":"This is a second test.","voice_id":"cgSgspJ2msm6clMCkdW9"}' \
  -o /tmp/test2.mp4

# EXPECTED: Request 1 ~3-5s (first inference), Request 2 ~1-2s
# CURRENT:  Both requests ~13s (model reload every time)
```

### Additional Speed Optimizations

1. **Batch size tuning** — Already set to 48, verify it's actually being used:
   ```bash
   grep -n "batch_size\|batch" ~/protocol_pulse/oracle/avatar_server.py
   ```

2. **torch.compile()** — If PyTorch >= 2.0, wrap the model:
   ```python
   model = torch.compile(registry.get('wav2lip'), mode="reduce-overhead")
   ```

3. **Half precision** — Use FP16 for inference:
   ```python
   model = model.half()  # FP16 — 2x faster, uses half VRAM
   ```

4. **CUDA graphs** — For repeated same-shape inputs:
   ```python
   # Pre-allocate tensors for common input shapes
   # This eliminates kernel launch overhead
   ```

5. **Async audio generation** — Pipeline the ElevenLabs TTS call while setting up face frames:
   ```python
   import asyncio
   # Start TTS and face prep simultaneously
   audio_task = asyncio.create_task(generate_tts(text))
   face_frames = prepare_face_frames(ref_face)
   audio = await audio_task
   ```

6. **GPU affinity** — Pin Wav2Lip to GPU 0, keep GPUs 1-3 free for Whisper/other tasks:
   ```python
   torch.cuda.set_device(0)  # Wav2Lip on GPU 0
   # Whisper uses GPU 1 (set in transcriber config)
   ```

## PART 2: PRE-WARM AVATAR PIPELINE

The avatar shouldn't just cache models — it should pre-compute everything possible BEFORE a request comes in.

### Pre-compute on startup:
1. ✅ Wav2Lip model loaded and in VRAM
2. ✅ Face detection model loaded and in VRAM
3. ✅ Reference face detected and cropped from Proto_P_Avatar_512.png
4. **NEW:** Pre-generate 30 frames of idle animation (blinks + micro head movement)
5. **NEW:** Pre-initialize FFmpeg output pipeline (keep process warm)
6. **NEW:** Pre-establish ElevenLabs WebSocket connection (if supported)

### Request pipeline (target: <2s for short text):

```
Request arrives with text
├── [0ms] Text → ElevenLabs TTS (async, ~800ms for short text)
├── [0ms] Retrieve pre-computed face reference (instant)
├── [800ms] Audio arrives from ElevenLabs
├── [800ms] Audio → mel spectrogram (CPU, ~50ms)
├── [850ms] Mel + face → Wav2Lip inference (GPU, ~200ms for 3s audio)
├── [1050ms] Frame post-processing: blinks, head movement (GPU, ~100ms)
├── [1150ms] Frames → FFmpeg encode (pre-warmed process, ~500ms)
└── [1650ms] Response sent — total ~1.7s
```

### Add a /warmup endpoint:
```python
@app.route('/warmup', methods=['POST'])
def warmup():
    """Hit this on server start to pre-warm the full pipeline."""
    test_audio = generate_tts("Warming up.", voice_id="cgSgspJ2msm6clMCkdW9")
    result = generate_avatar_video(test_audio)
    return jsonify({"status": "warm", "latency_ms": result['elapsed_ms']})
```

Add to startup sequence:
```python
if __name__ == '__main__':
    registry = ModelRegistry.get_instance()
    registry.load_all()
    
    # Pre-warm the full pipeline with a test generation
    print("[Startup] Pre-warming pipeline...")
    with app.test_client() as client:
        resp = client.post('/warmup')
        print(f"[Startup] Pipeline warm: {resp.json}")
    
    app.run(host='0.0.0.0', port=8200)
```

## PART 3: INTERACTIVE VISION GUIDE

### The Feature

Users can upload a photo or share their camera feed, and the Oracle Avatar analyzes what it sees to guide them through hardware setup. Use cases:

1. **Cold Wallet Setup** — "Show me your Coldcard/Trezor/Ledger and I'll walk you through initialization"
2. **Bitcoin Node Setup** — "Show me your Raspberry Pi / Start9 / Umbrel and I'll help you configure it"
3. **BitAxe Setup** — "Show me your BitAxe and I'll help you connect it to a pool"
4. **General Hardware** — "What Bitcoin hardware is this?" — identify and explain

### Vision API: Gemini 2.5 Flash (FREE)

Use Gemini's multimodal API for image analysis — it's free on Google AI Studio and handles hardware identification well.

```bash
# Check if Gemini API key exists
grep -r "GEMINI\|GOOGLE_AI\|google_api" ~/protocol_pulse/.env ~/protocol_pulse/config*.py 2>/dev/null
```

If no key exists, check Google AI Studio access:
```python
# Gemini API endpoint (free tier)
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
# Key should be set as GEMINI_API_KEY in .env

# If key doesn't exist, log a clear message:
# "GEMINI_API_KEY not found. Vision guide feature disabled. 
#  Get a free key at https://aistudio.google.com/apikey"
```

### New Endpoints

Add to avatar_server.py:

```python
@app.route('/vision/analyze', methods=['POST'])
def vision_analyze():
    """
    Analyze an uploaded image of Bitcoin hardware.
    Input: multipart/form-data with 'image' file
    Output: JSON with identification + setup guidance
    """
    image = request.files.get('image')
    if not image:
        return jsonify({"error": "No image provided"}), 400
    
    # Convert to base64 for Gemini
    img_b64 = base64.b64encode(image.read()).decode()
    
    # Send to Gemini with Bitcoin hardware context
    analysis = analyze_with_gemini(img_b64)
    
    # Generate avatar response
    avatar_text = analysis['guidance_text']
    avatar_video = generate_avatar_video_from_text(avatar_text)
    
    return jsonify({
        "identified_device": analysis['device_name'],
        "device_type": analysis['category'],  # cold_wallet, node, miner, other
        "setup_steps": analysis['steps'],
        "avatar_video_url": avatar_video['url'],
        "next_prompt": analysis['next_question']
    })

@app.route('/vision/guide', methods=['POST'])
def vision_guide():
    """
    Multi-turn guided setup session.
    Input: image + session_id + step_number
    Output: Current step guidance + what to do next
    """
    image = request.files.get('image')
    session_id = request.form.get('session_id', str(uuid.uuid4()))
    step = int(request.form.get('step', 0))
    
    # Load session context
    session = get_or_create_session(session_id)
    
    # Analyze current state
    analysis = analyze_setup_progress(image, session)
    
    # Generate step-specific guidance
    guidance = generate_step_guidance(analysis, session, step)
    
    # Avatar speaks the guidance
    avatar_video = generate_avatar_video_from_text(guidance['narration'])
    
    return jsonify({
        "session_id": session_id,
        "current_step": step,
        "total_steps": guidance['total_steps'],
        "status": guidance['step_status'],  # "correct", "needs_adjustment", "wrong_device"
        "guidance": guidance['text'],
        "avatar_video_url": avatar_video['url'],
        "next_action": guidance['next_action'],
        "tips": guidance['tips']
    })
```

### Gemini Vision Integration

```python
import requests
import base64
import json
import os

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

VISION_SYSTEM_PROMPT = """You are the Protocol Pulse Oracle — a Bitcoin hardware expert. 
You're analyzing an image that a user has shared of their Bitcoin hardware setup.

Your job:
1. IDENTIFY the device (brand, model, generation if visible)
2. ASSESS the current setup state (unboxed, partially configured, running, error state)
3. PROVIDE the next step they should take
4. FLAG any security concerns (exposed seed phrases, visible private keys, etc.)

SECURITY CRITICAL: If you see a seed phrase, private key, or recovery words in the image:
- DO NOT read them out or repeat them
- IMMEDIATELY warn the user: "I can see sensitive recovery information in your image. 
  Please delete this image and NEVER share photos showing your seed phrase or private keys."

Supported devices:
- Cold wallets: Coldcard, Trezor (Model T, One, Safe), Ledger (Nano S/X, Stax), Foundation Passport, SeedSigner, Blockstream Jade
- Nodes: Start9, Umbrel, RaspiBlitz, myNode, Nodl, Bitcoin Core on desktop
- Miners: BitAxe (Supra, Ultra, Gamma), Antminer, Whatsminer, FutureBit Apollo
- Other: Block Clock, Opendime, SatsCard, Hardware signing devices

Respond ONLY in JSON:
{
    "device_name": "Coldcard Mk4",
    "category": "cold_wallet",
    "brand": "Coinkite",
    "confidence": 0.95,
    "current_state": "unboxed, showing initial setup screen",
    "security_alert": null,
    "guidance_text": "I can see your Coldcard Mk4 is showing the initial setup screen. Great choice for cold storage. Here's what to do next: ...",
    "steps": [
        {"step": 1, "action": "Set your PIN", "detail": "Choose a prefix PIN and suffix PIN..."},
        {"step": 2, "action": "Generate seed", "detail": "Select 'New Seed Words' and write them down..."}
    ],
    "next_question": "Can you show me the screen after you've set your PIN?",
    "tips": ["Never take photos of your seed phrase", "Verify the anti-tampering bag was sealed"]
}
"""

def analyze_with_gemini(image_b64, mime_type="image/jpeg", context=""):
    """Send image to Gemini for Bitcoin hardware analysis."""
    
    if not GEMINI_API_KEY:
        return {
            "error": "Vision guide requires GEMINI_API_KEY. Get one free at https://aistudio.google.com/apikey",
            "device_name": "unknown",
            "guidance_text": "I need a Gemini API key to analyze images. Please ask PBX to configure GEMINI_API_KEY."
        }
    
    payload = {
        "contents": [{
            "parts": [
                {"text": VISION_SYSTEM_PROMPT + (f"\n\nAdditional context: {context}" if context else "")},
                {"inline_data": {"mime_type": mime_type, "data": image_b64}}
            ]
        }],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 2048
        }
    }
    
    resp = requests.post(GEMINI_URL, json=payload, timeout=30)
    if resp.status_code != 200:
        return {"error": f"Gemini API error: {resp.status_code}", "device_name": "unknown"}
    
    result = resp.json()
    text = result['candidates'][0]['content']['parts'][0]['text']
    
    # Parse JSON from response (strip markdown fences if present)
    text = text.strip().replace('```json', '').replace('```', '').strip()
    return json.loads(text)
```

### Session Management for Multi-Turn Guides

```python
import uuid
from datetime import datetime

# In-memory session store (fine for single-server)
GUIDE_SESSIONS = {}

class GuideSession:
    def __init__(self, session_id, device_type=None):
        self.id = session_id
        self.device_type = device_type
        self.device_name = None
        self.current_step = 0
        self.history = []  # List of (image_summary, guidance, timestamp)
        self.created_at = datetime.now()
    
    def add_step(self, image_analysis, guidance):
        self.history.append({
            "step": self.current_step,
            "analysis": image_analysis,
            "guidance": guidance,
            "timestamp": datetime.now().isoformat()
        })
        self.current_step += 1
    
    def get_context(self):
        """Build context string from session history for Gemini."""
        if not self.history:
            return ""
        ctx = f"Device: {self.device_name}\nPrevious steps completed:\n"
        for h in self.history[-3:]:  # Last 3 steps for context
            ctx += f"  Step {h['step']}: {h['analysis'].get('current_state','')}\n"
        return ctx

def get_or_create_session(session_id):
    if session_id not in GUIDE_SESSIONS:
        GUIDE_SESSIONS[session_id] = GuideSession(session_id)
    return GUIDE_SESSIONS[session_id]

# Cleanup old sessions (run periodically)
def cleanup_sessions(max_age_hours=2):
    now = datetime.now()
    expired = [sid for sid, s in GUIDE_SESSIONS.items() 
               if (now - s.created_at).total_seconds() > max_age_hours * 3600]
    for sid in expired:
        del GUIDE_SESSIONS[sid]
```

### Frontend Integration (for /stage page)

The `/stage` page should have:
1. **"Start Setup Guide" button** → opens camera or file upload
2. **Live camera feed** with "Capture" button (uses getUserMedia API)
3. **Step-by-step panel** showing current step, progress bar, tips
4. **Avatar video** playing the guidance for current step
5. **"Show me again" button** → re-captures and re-analyzes

This is a FUTURE frontend task. For now, build the backend API endpoints and test with curl.

## TESTING

### Test Part 1 (GPU caching):
```bash
# Restart avatar server
tmux send-keys -t avatar C-c
sleep 3
tmux send-keys -t avatar 'cd ~/protocol_pulse/oracle && python3 avatar_server.py' Enter
sleep 20  # Wait for model loading

# Time two requests:
echo "=== Request 1 ==="
time curl -s -X POST http://localhost:8200/generate \
  -H "Content-Type: application/json" \
  -d '{"text":"Testing model cache.","voice_id":"cgSgspJ2msm6clMCkdW9"}' \
  -o /tmp/test1.mp4 && echo "Size: $(wc -c < /tmp/test1.mp4)"

echo "=== Request 2 ==="
time curl -s -X POST http://localhost:8200/generate \
  -H "Content-Type: application/json" \
  -d '{"text":"Second request should be fast.","voice_id":"cgSgspJ2msm6clMCkdW9"}' \
  -o /tmp/test2.mp4 && echo "Size: $(wc -c < /tmp/test2.mp4)"

# PASS: Request 2 under 3 seconds
# FAIL: Both requests ~13 seconds
```

### Test Part 2 (Pre-warm):
```bash
curl -s -X POST http://localhost:8200/warmup | python3 -m json.tool
# Should return {"status": "warm", "latency_ms": <number>}
```

### Test Part 3 (Vision — requires GEMINI_API_KEY):
```bash
# Check if key exists
curl -s http://localhost:8200/health | python3 -m json.tool
# Should show vision_enabled: true/false

# Test with a sample image (if key exists)
curl -s -X POST http://localhost:8200/vision/analyze \
  -F "image=@/tmp/test_hardware.jpg" | python3 -m json.tool

# If no test image, generate one:
# Download a Coldcard product image for testing
wget -q "https://coldcard.com/static/images/mk4-front.png" -O /tmp/test_hardware.jpg
```

## FILES TO MODIFY

1. `/home/ultron/protocol_pulse/oracle/avatar_server.py` — Main avatar server
   - Add ModelRegistry class
   - Add pre-warm pipeline
   - Add /warmup endpoint
   - Add /vision/analyze endpoint
   - Add /vision/guide endpoint
   - Add session management

2. Create `/home/ultron/protocol_pulse/oracle/model_registry.py` — Extracted model cache (cleaner)

3. Create `/home/ultron/protocol_pulse/oracle/vision_guide.py` — Vision analysis logic

4. Create `/home/ultron/protocol_pulse/oracle/gemini_client.py` — Gemini API wrapper

## IMPORTANT: RESTART AVATAR SERVER AFTER CHANGES

```bash
# Kill existing avatar server
tmux send-keys -t avatar C-c
sleep 3

# Start updated server
tmux send-keys -t avatar 'cd ~/protocol_pulse/oracle && python3 avatar_server.py' Enter

# Watch startup logs
sleep 5
tmux capture-pane -t avatar -p | tail -10
# Should see: "[ModelRegistry] All models loaded in X.Xs — VRAM locked"
```

## RULES

- Work on `main` branch
- GPU caching is #1 priority — do it FIRST, verify timing improvement
- If GEMINI_API_KEY is missing, log clearly but don't fail — vision features just stay disabled
- Keep Wav2Lip on GPU 0, leave GPUs 1-3 available
- FP16 inference where possible
- Git commit + push when done
- Report: before/after timing for avatar generation, VRAM usage, vision test results
- SEED PHRASE SECURITY: The vision system must NEVER read or repeat visible seed phrases/keys
