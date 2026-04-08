#!/usr/bin/env python3
"""PBX Avatar Render — ElevenLabs audio → HeyGen avatar render."""
import os, sys, json, time, requests, base64

# Config
ELEVENLABS_KEY = os.environ.get("ELEVENLABS_API_KEY") or ""
HEYGEN_KEY = "sk_V2_hgu_kBwfPLbfWmt_CRSMrpqDsJwhVP6CiM1Pf6sl1ginEw4XR"
PBX_VOICE_ID = "HmUVvDlHsEz0m3eUGLgu"  # ElevenLabs PBX
PBX_AVATAR_ID = "3be8ed14b0954b898f4127836c21f6cc"  # HeyGen PBX

# Load ElevenLabs key from .env
if not ELEVENLABS_KEY:
    env_path = "/home/ultron/protocol_pulse/.env"
    if os.path.exists(env_path):
        for line in open(env_path):
            if line.startswith("ELEVENLABS_API_KEY="):
                ELEVENLABS_KEY = line.strip().split("=", 1)[1].strip("'\"")

# Get latest BTC data for script
try:
    ctx = json.load(open("/home/ultron/protocol_pulse/data/sovereign_context/latest.json"))
    price = ctx.get("btc", {}).get("price", 67000)
    change = ctx.get("btc", {}).get("change_24h", 0)
    fg = ctx.get("fear_greed", {}).get("value", 12)
    hashrate = ctx.get("network", {}).get("hashrate_eh", 1000)
except:
    price, change, fg, hashrate = 67000, -1.0, 12, 1000

# Build the script
narration = f"""Good evening. This is PBX with your Protocol Pulse check.

Bitcoin is trading at ${price:,.0f}, {('up' if change > 0 else 'down')} {abs(change):.1f}% over the last 24 hours. 

The Fear and Greed Index sits at {fg} — Extreme Fear territory. Historically, this is where smart money accumulates.

Network hashrate holds strong at {hashrate:.0f} exahashes per second. Miners aren't slowing down.

That's your pulse check. Stay sovereign. This is PBX, Protocol Pulse."""

print(f"[1] Script: {len(narration)} chars")
print(narration[:200])

# Step 1: Generate ElevenLabs audio
print("\n[2] Generating ElevenLabs TTS...")
tts_url = f"https://api.elevenlabs.io/v1/text-to-speech/{PBX_VOICE_ID}"
tts_resp = requests.post(tts_url, 
    headers={"xi-api-key": ELEVENLABS_KEY, "Content-Type": "application/json"},
    json={
        "text": narration,
        "model_id": "eleven_turbo_v2_5",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75, "speed": 1.2}
    },
    timeout=30
)

if tts_resp.status_code != 200:
    print(f"  ElevenLabs FAILED: {tts_resp.status_code} {tts_resp.text[:200]}")
    sys.exit(1)

audio_path = "/tmp/pbx_tts_audio.mp3"
with open(audio_path, "wb") as f:
    f.write(tts_resp.content)
audio_size = os.path.getsize(audio_path)
print(f"  Audio saved: {audio_size/1024:.0f}KB")

# Step 2: Upload audio to HeyGen
print("\n[3] Uploading audio to HeyGen...")
upload_resp = requests.post(
    "https://api.heygen.com/v1/asset",
    headers={"X-Api-Key": HEYGEN_KEY},
    files={"file": ("pbx_audio.mp3", open(audio_path, "rb"), "audio/mpeg")},
    timeout=30
)

if upload_resp.status_code != 200:
    print(f"  Upload FAILED: {upload_resp.status_code} {upload_resp.text[:200]}")
    sys.exit(1)

upload_data = upload_resp.json()
asset_url = upload_data.get("data", {}).get("url", "")
print(f"  Asset URL: {asset_url[:80]}...")

# Step 3: Generate HeyGen avatar video with uploaded audio
print("\n[4] Submitting HeyGen render (PBX avatar + ElevenLabs audio)...")
payload = {
    "video_inputs": [{
        "character": {
            "type": "avatar",
            "avatar_id": PBX_AVATAR_ID,
            "avatar_style": "normal",
        },
        "voice": {
            "type": "audio",
            "audio_url": asset_url,
        }
    }],
    "dimension": {"width": 1920, "height": 1080},
    "test": False,
}

gen_resp = requests.post(
    "https://api.heygen.com/v2/video/generate",
    headers={"X-Api-Key": HEYGEN_KEY, "Content-Type": "application/json"},
    json=payload,
    timeout=30
)

if gen_resp.status_code != 200:
    print(f"  HeyGen FAILED: {gen_resp.status_code} {gen_resp.text[:300]}")
    sys.exit(1)

gen_data = gen_resp.json()
video_id = gen_data.get("data", {}).get("video_id")
print(f"  Video ID: {video_id}")

# Step 4: Poll for completion
print("\n[5] Waiting for HeyGen render...")
for i in range(60):
    time.sleep(10)
    status_resp = requests.get(
        f"https://api.heygen.com/v1/video_status.get",
        headers={"X-Api-Key": HEYGEN_KEY},
        params={"video_id": video_id},
        timeout=15
    )
    if status_resp.status_code == 200:
        sdata = status_resp.json().get("data", {})
        status = sdata.get("status")
        print(f"  Poll {i+1}: {status}")
        if status == "completed":
            video_url = sdata.get("video_url")
            duration = sdata.get("duration")
            print(f"\n  DONE! Duration: {duration}s")
            print(f"  URL: {video_url}")
            
            # Download
            output = "/home/ultron/protocol_pulse/static/renders/pbx_heygen_latest.mp4"
            os.makedirs(os.path.dirname(output), exist_ok=True)
            dl = requests.get(video_url, stream=True, timeout=60)
            with open(output, "wb") as f:
                for chunk in dl.iter_content(8192):
                    f.write(chunk)
            print(f"  Saved: {output} ({os.path.getsize(output)/1024/1024:.1f}MB)")
            print(f"\n  DOWNLOAD: https://protocolpulse.io/static/renders/pbx_heygen_latest.mp4")
            sys.exit(0)
        elif status == "failed":
            print(f"  FAILED: {sdata}")
            sys.exit(1)

print("  TIMEOUT after 10 minutes")
