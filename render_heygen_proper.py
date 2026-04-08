#!/usr/bin/env python3
import requests, json, time, os, sys

key = [l.strip().split('=',1)[1].strip().strip("'\"") for l in open('/home/ultron/protocol_pulse/.env') if l.startswith('HEYGEN_API_KEY=')][0]
AVATAR_ID = "370e8197174344cf90abe5fed6c8886e"  # PBX -- 1
AUDIO_URL = "https://protocolpulse.io/static/renders/pbx_tts_audio.mp3"

print(f"HeyGen render: PBX--1 + ElevenLabs audio")

payload = {
    "video_inputs": [{
        "character": {
            "type": "avatar",
            "avatar_id": AVATAR_ID,
            "avatar_style": "normal",
        },
        "voice": {
            "type": "audio",
            "audio_url": AUDIO_URL,
        }
    }],
    "dimension": {"width": 1920, "height": 1080},
    "test": False,
}

resp = requests.post("https://api.heygen.com/v2/video/generate",
    headers={"X-Api-Key": key, "Content-Type": "application/json"},
    json=payload, timeout=30)

print(f"  HTTP {resp.status_code}: {resp.text[:300]}")
if resp.status_code != 200:
    sys.exit(1)

video_id = resp.json().get("data", {}).get("video_id")
print(f"  Video ID: {video_id}\n  Polling...")

for i in range(60):
    time.sleep(10)
    sr = requests.get("https://api.heygen.com/v1/video_status.get",
        headers={"X-Api-Key": key}, params={"video_id": video_id}, timeout=15)
    sd = sr.json().get("data", {})
    st = sd.get("status")
    print(f"  [{i+1}] {st}")
    if st == "completed":
        output = "/home/ultron/protocol_pulse/static/renders/pbx_heygen_latest.mp4"
        os.makedirs(os.path.dirname(output), exist_ok=True)
        dl = requests.get(sd["video_url"], stream=True, timeout=60)
        with open(output, "wb") as f:
            for chunk in dl.iter_content(8192):
                f.write(chunk)
        print(f"\n  DONE! {os.path.getsize(output)/1024/1024:.1f}MB")
        print(f"  https://protocolpulse.io/static/renders/pbx_heygen_latest.mp4")
        break
    elif st == "failed":
        print(f"  FAILED: {sd}")
        break
