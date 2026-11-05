#!/usr/bin/env python3
"""Generate VO audio from edl.json using ElevenLabs.
Voice: PBX MAX (ELEVENLABS_VOICE_ID_PP2), eleven_v4 model.
Law 15: 1.0s pad before every line."""
import json
import os
import sys
import subprocess
import time
import requests
from dotenv import load_dotenv

load_dotenv("/home/ultron/protocol_pulse/.env")

BASE = "/home/ultron/protocol_pulse/segment_v2"
VO_DIR = f"{BASE}/vo_audio"
os.makedirs(VO_DIR, exist_ok=True)

VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID_PP2")
API_KEY = os.environ.get("ELEVENLABS_API_KEY")
if not VOICE_ID or not API_KEY:
    print("FATAL: ELEVENLABS_VOICE_ID_PP2 or ELEVENLABS_API_KEY missing")
    sys.exit(1)

MODEL_ID = "eleven_v4"
VOICE_SETTINGS = {
    "stability": 0.55,
    "similarity_boost": 0.75,
    "style": 0.15,
    "use_speaker_boost": True,
}


def generate_vo(text, output_mp3):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
    headers = {"xi-api-key": API_KEY.strip(), "Content-Type": "application/json"}
    body = {"text": text, "model_id": MODEL_ID, "voice_settings": VOICE_SETTINGS}

    print(f"  ElevenLabs ({len(text)} chars, {MODEL_ID})...", end=" ", flush=True)
    t0 = time.time()
    r = requests.post(url, json=body, headers=headers, timeout=60)
    if r.status_code != 200:
        print(f"ERROR: HTTP {r.status_code}: {r.text[:200]}")
        return False
    with open(output_mp3, "wb") as f:
        f.write(r.content)
    print(f"OK {len(r.content)} bytes, {time.time()-t0:.1f}s")
    return True


def transcode_to_wav(mp3_path, wav_path):
    subprocess.run([
        "ffmpeg", "-y", "-i", mp3_path,
        "-ac", "2", "-ar", "48000", "-c:a", "pcm_s16le", wav_path,
    ], capture_output=True, timeout=30)
    if os.path.exists(wav_path) and os.path.getsize(wav_path) > 100:
        dur = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", wav_path],
            capture_output=True, text=True, timeout=5).stdout.strip()
        print(f"  WAV: {dur}s")
        return True
    return False


with open(f"{BASE}/edl.json") as f:
    edl = json.load(f)

vo = edl.get("vo", {})
if not vo:
    print("ERROR: No VO in edl.json")
    sys.exit(1)

manifest = []

# Intro
intro = vo.get("intro", "")
if intro:
    print(f"Generating intro ({len(intro.split())} words)...")
    mp3 = f"{VO_DIR}/vo_intro_pp2.mp3"
    wav = f"{VO_DIR}/vo_intro_pp2.wav"
    if generate_vo(intro, mp3):
        transcode_to_wav(mp3, wav)
        manifest.append({"type": "intro", "mp3": mp3, "wav": wav})

# Bridges
for i, bridge in enumerate(vo.get("bridges", [])):
    text = bridge.get("text", "")
    if text:
        print(f"Generating bridge {i+1} ({len(text.split())} words)...")
        mp3 = f"{VO_DIR}/vo_bridge_{i+1:02d}_pp2.mp3"
        wav = f"{VO_DIR}/vo_bridge_{i+1:02d}_pp2.wav"
        if generate_vo(text, mp3):
            transcode_to_wav(mp3, wav)
            manifest.append({"type": f"bridge_{i+1}", "mp3": mp3, "wav": wav,
                             "after_clip": bridge.get("after_clip")})

# Signoff
signoff = vo.get("signoff", "")
if signoff:
    print(f"Generating signoff ({len(signoff.split())} words)...")
    mp3 = f"{VO_DIR}/vo_signoff_pp2.mp3"
    wav = f"{VO_DIR}/vo_signoff_pp2.wav"
    if generate_vo(signoff, mp3):
        transcode_to_wav(mp3, wav)
        manifest.append({"type": "signoff", "mp3": mp3, "wav": wav})

# Write manifest
with open(f"{VO_DIR}/VO_MANIFEST.json", "w") as f:
    json.dump(manifest, f, indent=2)
print(f"\nGenerated {len(manifest)} VO files. Manifest: {VO_DIR}/VO_MANIFEST.json")
