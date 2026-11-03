#!/usr/bin/env python3
"""Generate VO audio from edl.json using ElevenLabs.
Single API call per VO line. Transcode to PCM WAV for Resolve.
Voice: PBX (HmUVvDlHsEz0m3eUGLgu), eleven_multilingual_v2."""
import json, os, sys, subprocess, time

BASE = "/home/ultron/protocol_pulse/segment_v1"
VO_DIR = os.path.join(BASE, "vo_audio")
os.makedirs(VO_DIR, exist_ok=True)

# Reuse relay key getter from the main pipeline
sys.path.insert(0, "/home/ultron/protocol_pulse/video_pipeline_v3")
from relay import get_key

# PBX clone is the production voice; Connery is fallback
PBX_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID_PP", "e6gztcS9NPqChYKvXN6c")
MODEL_ID = "eleven_multilingual_v2"
VOICE_SETTINGS = {
    "stability": 0.60,
    "similarity_boost": 0.80,
    "style": 0.30,
    "use_speaker_boost": True,
}


def generate_vo(text, output_mp3, speed=1.15):
    """Call ElevenLabs TTS API and save as MP3."""
    import requests

    key = get_key("ELEVENLABS_API_KEY")
    if not key:
        print("ERROR: ELEVENLABS_API_KEY not available")
        return False

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{PBX_VOICE_ID}"
    headers = {"xi-api-key": key.strip(), "Content-Type": "application/json"}
    body = {
        "text": text,
        "model_id": MODEL_ID,
        "voice_settings": VOICE_SETTINGS,
    }

    print(f"  Calling ElevenLabs ({len(text)} chars)...", flush=True)
    t0 = time.time()
    r = requests.post(url, json=body, headers=headers, timeout=60)

    if r.status_code != 200:
        print(f"  ERROR: HTTP {r.status_code}: {r.text[:200]}")
        return False

    with open(output_mp3, "wb") as f:
        f.write(r.content)

    elapsed = time.time() - t0
    print(f"  OK: {len(r.content)} bytes, {elapsed:.1f}s", flush=True)
    return True


def transcode_to_pcm_wav(mp3_path, wav_path):
    """Transcode MP3 to 48kHz stereo PCM WAV for Resolve."""
    subprocess.run([
        "ffmpeg", "-y", "-i", mp3_path,
        "-ac", "2", "-ar", "48000", "-c:a", "pcm_s16le",
        wav_path,
    ], capture_output=True, timeout=30)
    if os.path.exists(wav_path) and os.path.getsize(wav_path) > 100:
        dur = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", wav_path],
            capture_output=True, text=True, timeout=5).stdout.strip()
        print(f"  PCM WAV: {wav_path} ({dur}s)")
        return True
    return False


if __name__ == "__main__":
    with open(os.path.join(BASE, "edl.json")) as f:
        edl = json.load(f)

    vo = edl.get("vo", {})
    if not vo:
        print("ERROR: No VO in edl.json")
        sys.exit(1)

    generated = []

    # Intro VO
    intro = vo.get("intro", "")
    if intro:
        print(f"Generating intro VO ({len(intro.split())} words)...")
        mp3 = os.path.join(VO_DIR, "vo_intro.mp3")
        wav = os.path.join(VO_DIR, "vo_intro.wav")
        if generate_vo(intro, mp3):
            transcode_to_pcm_wav(mp3, wav)
            generated.append({"type": "intro", "mp3": mp3, "wav": wav})

    # Bridge VOs
    for i, bridge in enumerate(vo.get("bridges", [])):
        text = bridge.get("text", "")
        if text:
            print(f"Generating bridge {i+1} VO ({len(text.split())} words)...")
            mp3 = os.path.join(VO_DIR, f"vo_bridge_{i+1:02d}.mp3")
            wav = os.path.join(VO_DIR, f"vo_bridge_{i+1:02d}.wav")
            if generate_vo(text, mp3):
                transcode_to_pcm_wav(mp3, wav)
                generated.append({"type": f"bridge_{i+1}", "mp3": mp3, "wav": wav,
                                   "after_clip": bridge.get("after_clip")})

    # Write manifest
    manifest = os.path.join(VO_DIR, "manifest.json")
    with open(manifest, "w") as f:
        json.dump(generated, f, indent=2)
    print(f"\nGenerated {len(generated)} VO files. Manifest: {manifest}")
