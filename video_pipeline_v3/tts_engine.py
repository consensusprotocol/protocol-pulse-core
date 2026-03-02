#!/usr/bin/env python3
"""Step 5: TTS Engine — ElevenLabs with gTTS fallback."""
import os, sys, json, subprocess, tempfile
from pathlib import Path

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from gtts import gTTS
    HAS_GTTS = True
except ImportError:
    HAS_GTTS = False

from relay import get_key

VOICE_CONFIG = {
    "voice_id": "1m00Tcm4TlvDq8ikWAM",
    "model_id": "eleven_turbo_v2_5",
    "voice_settings": {
        "stability": 0.55,
        "similarity_boost": 0.85,
        "style": 0.50,
        "use_speaker_boost": True
    }
}


def ffprobe_duration(path: str) -> float:
    """Get audio duration via ffprobe."""
    r = subprocess.run(
        f"ffprobe -v error -show_entries format=duration -of csv=p=0 '{path}'",
        shell=True, capture_output=True, text=True
    )
    try:
        return float(r.stdout.strip())
    except:
        return 0.0


def tts_elevenlabs(text: str, output_path: str) -> bool:
    """Generate TTS via ElevenLabs API."""
    key = get_key("ELEVENLABS_API_KEY")
    if not key or not HAS_REQUESTS:
        return False
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_CONFIG['voice_id']}"
    headers = {"xi-api-key": key, "Content-Type": "application/json"}
    data = {
        "text": text,
        "model_id": VOICE_CONFIG["model_id"],
        "voice_settings": VOICE_CONFIG["voice_settings"]
    }
    try:
        r = requests.post(url, json=data, headers=headers, timeout=60)
        if r.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(r.content)
            return True
        print(f"  [elevenlabs] HTTP {r.status_code}: {r.text[:200]}")
    except Exception as e:
        print(f"  [elevenlabs] error: {e}")
    return False


def tts_gtts(text: str, output_path: str) -> bool:
    """Generate TTS via Google TTS (fallback)."""
    if not HAS_GTTS:
        return False
    try:
        tts = gTTS(text=text, lang='en', tld='com')
        tmp = output_path + ".tmp.mp3"
        tts.save(tmp)
        # Convert to consistent format and speed up slightly for broadcast energy
        subprocess.run(
            f"ffmpeg -y -i '{tmp}' -af 'atempo=1.15,loudnorm=I=-16:TP=-1.5:LRA=11' "
            f"-ar 44100 -ac 1 -c:a aac -b:a 192k '{output_path}'",
            shell=True, capture_output=True, text=True, timeout=60
        )
        os.remove(tmp)
        return os.path.exists(output_path)
    except Exception as e:
        print(f"  [gtts] error: {e}")
        return False


def generate_segment_audio(text: str, output_path: str, label: str = "") -> bool:
    """Generate TTS for a segment. Tries ElevenLabs, falls back to gTTS."""
    print(f"  [tts] Generating: {label}...")

    # Try ElevenLabs first
    if tts_elevenlabs(text, output_path):
        dur = ffprobe_duration(output_path)
        print(f"  [tts] ElevenLabs OK: {dur:.1f}s")
        return True

    # Fallback to gTTS
    if tts_gtts(text, output_path):
        dur = ffprobe_duration(output_path)
        print(f"  [tts] gTTS OK: {dur:.1f}s")
        return True

    print(f"  [tts] FAILED: {label}")
    return False


def generate_all_audio(script: dict, output_dir: str) -> dict:
    """Generate all TTS audio files from a script. Returns paths dict."""
    os.makedirs(output_dir, exist_ok=True)
    paths = {}

    # Cold open
    cold_path = os.path.join(output_dir, "cold_open.m4a")
    if generate_segment_audio(script["cold_open"], cold_path, "cold_open"):
        paths["cold_open"] = cold_path

    # Segments
    paths["segments"] = []
    for i, seg in enumerate(script["segments"]):
        seg_path = os.path.join(output_dir, f"seg_{i:02d}.m4a")
        if generate_segment_audio(seg["narration"], seg_path, f"seg_{i:02d} - {seg['headline']}"):
            paths["segments"].append(seg_path)
        else:
            paths["segments"].append(None)

        # Bridge
        if seg.get("bridge_to_next"):
            bridge_path = os.path.join(output_dir, f"bridge_{i:02d}.m4a")
            if generate_segment_audio(seg["bridge_to_next"], bridge_path, f"bridge_{i:02d}"):
                paths.setdefault("bridges", []).append(bridge_path)
            else:
                paths.setdefault("bridges", []).append(None)
        else:
            paths.setdefault("bridges", []).append(None)

        # Editorial drop
        if seg.get("editorial_drop"):
            ed_path = os.path.join(output_dir, f"editorial_{i:02d}.m4a")
            if generate_segment_audio(seg["editorial_drop"], ed_path, f"editorial_{i:02d}"):
                paths.setdefault("editorials", []).append(ed_path)
            else:
                paths.setdefault("editorials", []).append(None)
        else:
            paths.setdefault("editorials", []).append(None)

    # Outro
    outro_path = os.path.join(output_dir, "outro.m4a")
    if generate_segment_audio(script["outro"], outro_path, "outro"):
        paths["outro"] = outro_path

    # Full narration (concatenate all)
    all_parts = []
    if "cold_open" in paths:
        all_parts.append(paths["cold_open"])
    for i in range(len(script["segments"])):
        if paths["segments"][i]:
            all_parts.append(paths["segments"][i])
        if paths.get("bridges", [None]*99)[i]:
            all_parts.append(paths["bridges"][i])
        if paths.get("editorials", [None]*99)[i]:
            all_parts.append(paths["editorials"][i])
    if "outro" in paths:
        all_parts.append(paths["outro"])

    if all_parts:
        concat_file = os.path.join(output_dir, "concat_list.txt")
        with open(concat_file, "w") as f:
            for p in all_parts:
                f.write(f"file '{p}'\n")
        full_path = os.path.join(output_dir, "full_narration.m4a")
        subprocess.run(
            f"ffmpeg -y -f concat -safe 0 -i '{concat_file}' -c copy '{full_path}'",
            shell=True, capture_output=True, text=True
        )
        paths["full"] = full_path
        dur = ffprobe_duration(full_path)
        print(f"\n  [tts] Full narration: {dur:.1f}s")

    # Verify all
    print("\n  [tts] Verification:")
    for key, val in paths.items():
        if isinstance(val, str) and os.path.exists(val):
            dur = ffprobe_duration(val)
            sz = os.path.getsize(val)
            print(f"    {key}: {dur:.1f}s, {sz//1024}KB")

    return paths


if __name__ == "__main__":
    from script_writer import generate_script
    style = sys.argv[1] if len(sys.argv) > 1 else "default"
    script = generate_script(style=style)
    base = os.path.dirname(os.path.abspath(__file__))
    audio_dir = os.path.join(base, "output", "audio_test")
    paths = generate_all_audio(script, audio_dir)
    print(json.dumps({k: v for k, v in paths.items() if isinstance(v, str)}, indent=2))
