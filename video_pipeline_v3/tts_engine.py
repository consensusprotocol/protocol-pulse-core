#!/usr/bin/env python3
"""TTS Engine V5 — dual-host dialogue with ElevenLabs.
Host 1 (Eryn):  kdnRe2koJdOK4Ovxn2DI
Host 2 (Mark):  1SM7GgM6IMuvQlz2BwM3
Generates per-line audio with 0.3s silence gaps between speakers."""
import os, sys, json, subprocess, tempfile, time, struct
from pathlib import Path

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

from relay import get_key

VOICES = {
    1: {
        "voice_id": "kdnRe2koJdOK4Ovxn2DI",
        "name": "Eryn",
        "model_id": "eleven_turbo_v2_5",
        "speed": 1.12,
        "voice_settings": {
            "stability": 0.75,
            "similarity_boost": 0.75,
            "style": 0.10,
            "use_speaker_boost": True,
        },
    },
    2: {
        "voice_id": "1SM7GgM6IMuvQlz2BwM3",
        "name": "Mark",
        "model_id": "eleven_turbo_v2_5",
        "speed": 1.10,
        "voice_settings": {
            "stability": 0.40,
            "similarity_boost": 0.75,
            "style": 0.10,
            "use_speaker_boost": True,
        },
    },
}

# Hybrid voice settings per segment type (overrides for Matilda/Host 1 only)
# Cold open: whispery dramatic, classified briefing feel
# Narration (setup/react): clear, confident, authoritative
# Data callouts (wrap with price): slightly intense
# Social/transition: warm, inviting
VOICE_MODES = {
    "cold_open":       {"stability": 0.38, "similarity_boost": 0.78, "style": 0.15, "speed": 1.12},
    "setup":           {"stability": 0.75, "similarity_boost": 0.75, "style": 0.10, "speed": 1.12},
    "react":           {"stability": 0.75, "similarity_boost": 0.75, "style": 0.10, "speed": 1.12},
    "social_segment":  {"stability": 0.60, "similarity_boost": 0.75, "style": 0.12, "speed": 1.12},
    "wrap":            {"stability": 0.60, "similarity_boost": 0.72, "style": 0.20, "speed": 1.10},
    "data":            {"stability": 0.70, "similarity_boost": 0.78, "style": 0.10, "speed": 1.10},
}

SILENCE_GAP = 0.3  # seconds between speakers
MAX_CHUNK_CHARS = 4900

_KEY_CACHE: dict = {}


def _get_cached_key(name: str) -> str:
    if name not in _KEY_CACHE:
        k = get_key(name)
        if k:
            _KEY_CACHE[name] = k.strip()
    return _KEY_CACHE.get(name, "")


def ffprobe_duration(path: str) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path],
        capture_output=True, text=True,
    )
    try:
        return float(r.stdout.strip())
    except Exception:
        return 0.0


def _generate_silence(output_path: str, duration: float) -> bool:
    """Generate a silent audio file."""
    r = subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i",
         f"anullsrc=r=44100:cl=mono", "-t", str(duration),
         "-c:a", "aac", "-b:a", "192k", output_path],
        capture_output=True, text=True, timeout=30,
    )
    return r.returncode == 0 and os.path.exists(output_path)


def _mp3_to_m4a(mp3_path: str, m4a_path: str) -> bool:
    r = subprocess.run(
        ["ffmpeg", "-y", "-i", mp3_path,
         "-c:a", "aac", "-ar", "44100", "-ac", "1", "-b:a", "192k", m4a_path],
        capture_output=True, text=True, timeout=120,
    )
    return r.returncode == 0 and os.path.exists(m4a_path)


def _chunk_text(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list:
    if len(text) <= max_chars:
        return [text]
    raw = text.replace("! ", "!\x00").replace(". ", ".\x00").replace("? ", "?\x00")
    sentences = raw.split("\x00")
    chunks, current = [], ""
    for sent in sentences:
        if len(current) + len(sent) + 1 <= max_chars:
            current = f"{current} {sent}".strip() if current else sent
        else:
            if current:
                chunks.append(current)
            current = sent
    if current:
        chunks.append(current)
    return [c for c in chunks if c.strip()]


def tts_elevenlabs(text: str, output_path: str, host: int = 1,
                   segment_type: str = "") -> bool:
    """Generate TTS for a single line using the specified host voice.

    Applies hybrid voice settings based on segment_type for Host 1 (Eryn):
    - cold_open: dramatic (stability 0.38, speed 1.12)
    - setup/react: clear, confident (stability 0.75, speed 1.12)
    - social_segment: warm (stability 0.60, speed 1.12)
    - wrap: warm, inviting (stability 0.60, speed 1.10)
    - data: authoritative (stability 0.70, speed 1.10)
    """
    if not HAS_REQUESTS:
        return False

    key = _get_cached_key("ELEVENLABS_API_KEY")
    if not key:
        return False

    voice = VOICES.get(host, VOICES[1])
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice['voice_id']}"
    headers = {"xi-api-key": key, "Content-Type": "application/json"}

    # Apply hybrid voice mode for Host 1 (Eryn) based on segment type
    voice_settings = dict(voice["voice_settings"])
    if host == 1 and segment_type in VOICE_MODES:
        mode = VOICE_MODES[segment_type]
        for k, v in mode.items():
            if k != "speed":
                voice_settings[k] = v

    chunks = _chunk_text(text)
    chunk_files = []

    for ci, chunk in enumerate(chunks):
        body = {
            "text": chunk,
            "model_id": voice["model_id"],
            "voice_settings": voice_settings,
        }
        # Add speed parameter — use mode-specific speed for Host 1
        speed = voice.get("speed", 1.0)
        if host == 1 and segment_type in VOICE_MODES:
            speed = VOICE_MODES[segment_type].get("speed", speed)
        if speed != 1.0:
            body["speed"] = speed
        mp3_tmp = output_path + f".chunk{ci}.mp3"
        success = False

        for attempt in range(3):
            try:
                r = requests.post(url, json=body, headers=headers, timeout=90)
                if r.status_code == 200:
                    with open(mp3_tmp, "wb") as f:
                        f.write(r.content)
                    success = True
                    break
                elif r.status_code == 429:
                    wait = 2 ** attempt
                    print(f"  [tts] Rate limited ({voice['name']}), waiting {wait}s...")
                    time.sleep(wait)
                else:
                    print(f"  [tts] HTTP {r.status_code} ({voice['name']}) attempt {attempt+1}: {r.text[:200]}")
                    if attempt < 2:
                        time.sleep(2 ** attempt)
            except Exception as e:
                print(f"  [tts] Error ({voice['name']}) attempt {attempt+1}: {e}")
                if attempt < 2:
                    time.sleep(2 ** attempt)

        if not success:
            for f in chunk_files:
                try:
                    os.remove(f)
                except Exception:
                    pass
            return False
        chunk_files.append(mp3_tmp)

    # Single chunk
    if len(chunk_files) == 1:
        ok = _mp3_to_m4a(chunk_files[0], output_path)
        try:
            os.remove(chunk_files[0])
        except Exception:
            pass
        return ok

    # Multi-chunk concat
    concat_list = output_path + ".concat.txt"
    mp3_combined = output_path + ".combined.mp3"
    with open(concat_list, "w") as f:
        for p in chunk_files:
            f.write(f"file '{os.path.abspath(p)}'\n")
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
         "-c", "copy", mp3_combined],
        capture_output=True, text=True,
    )
    ok = _mp3_to_m4a(mp3_combined, output_path)
    for f in chunk_files + [concat_list, mp3_combined]:
        try:
            if os.path.exists(f):
                os.remove(f)
        except Exception:
            pass
    return ok


def generate_dialogue_audio(dialogue: list, output_dir: str) -> dict:
    """Generate audio for the entire dual-host dialogue.

    Args:
        dialogue: List of {host: 1|2|"CLIP", text: "..."}
        output_dir: Directory for audio files

    Returns:
        {
            "lines": [{"path": str, "host": int, "duration": float, "start": float}, ...],
            "full": str,  # path to concatenated full audio
            "total_duration": float,
        }
    """
    os.makedirs(output_dir, exist_ok=True)

    key = _get_cached_key("ELEVENLABS_API_KEY")
    if not key:
        raise RuntimeError("ELEVENLABS_API_KEY not available. Cannot generate audio.")

    silence_path = os.path.join(output_dir, "silence.m4a")
    _generate_silence(silence_path, SILENCE_GAP)

    lines = []
    parts_for_concat = []
    current_time = 0.0

    for i, entry in enumerate(dialogue):
        host = entry.get("host")
        text = entry.get("text", "")

        # Skip CLIP markers — they don't have audio
        if host == "CLIP":
            lines.append({
                "path": None,
                "host": "CLIP",
                "duration": 0.0,
                "start": current_time,
                "source": entry.get("source", ""),
                "query": entry.get("query", ""),
                "text": text,
            })
            continue

        host_num = int(host) if host in (1, 2, "1", "2") else 1
        voice = VOICES.get(host_num, VOICES[1])
        segment_type = entry.get("type", "")
        line_path = os.path.join(output_dir, f"line_{i:03d}_{voice['name'].lower()}.m4a")

        mode_tag = f" [{segment_type}]" if segment_type and host_num == 1 else ""
        print(f"  [tts] Line {i:02d} ({voice['name']}{mode_tag}): {text[:60]}...")

        if tts_elevenlabs(text, line_path, host_num, segment_type=segment_type):
            dur = ffprobe_duration(line_path)
            lines.append({
                "path": line_path,
                "host": host_num,
                "duration": dur,
                "start": current_time,
                "text": text,
            })
            parts_for_concat.append(line_path)
            current_time += dur

            # Add silence gap between speakers (not after last line)
            if i < len(dialogue) - 1:
                parts_for_concat.append(silence_path)
                current_time += SILENCE_GAP
        else:
            print(f"  [tts] FAILED line {i} ({voice['name']})")
            lines.append({
                "path": None,
                "host": host_num,
                "duration": 0.0,
                "start": current_time,
                "text": text,
            })

    # Concatenate all lines into full audio
    full_path = os.path.join(output_dir, "full_dialogue.m4a")
    if parts_for_concat:
        concat_file = os.path.join(output_dir, "dialogue_concat.txt")
        with open(concat_file, "w") as f:
            for p in parts_for_concat:
                f.write(f"file '{os.path.abspath(p)}'\n")
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_file,
             "-c", "copy", full_path],
            capture_output=True, text=True,
        )
        if os.path.exists(concat_file):
            os.remove(concat_file)

    total_dur = ffprobe_duration(full_path) if os.path.exists(full_path) else current_time
    successful = sum(1 for l in lines if l["path"] and os.path.exists(l.get("path", "")))

    print(f"\n  [tts] Dialogue audio: {successful}/{len(dialogue)} lines, {total_dur:.1f}s total")

    return {
        "lines": lines,
        "full": full_path if os.path.exists(full_path) else None,
        "total_duration": total_dur,
    }


# Legacy compatibility — V3 pipeline used generate_all_audio
def generate_all_audio(script: dict, output_dir: str) -> dict:
    """Legacy wrapper: converts V4 dialogue script to audio paths dict."""
    if "dialogue" in script:
        return generate_dialogue_audio(script["dialogue"], output_dir)
    # V3 fallback
    raise RuntimeError("V4 pipeline requires dialogue-format script")


if __name__ == "__main__":
    from script_writer import generate_script
    style = sys.argv[1] if len(sys.argv) > 1 else "default"
    script = generate_script(style=style)
    base = os.path.dirname(os.path.abspath(__file__))
    audio_dir = os.path.join(base, "output", "audio_test")
    result = generate_dialogue_audio(script["dialogue"], audio_dir)
    print(json.dumps(
        {k: v for k, v in result.items() if k != "lines"},
        indent=2,
    ))
