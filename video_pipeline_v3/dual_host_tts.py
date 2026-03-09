#!/usr/bin/env python3
"""dual_host_tts.py — Single-host TTS engine for Pulse Check.

Generates audio using ElevenLabs TTS.
Host: Mark (1SM7GgM6IMuvQlz2BwM3) — PBX approved single narrator at 1.10x speed.
Both host=1 and host=2 entries route to Mark (single voice, no gender swap).

Usage:
    from dual_host_tts import generate_dialogue_audio

    dialogue = [
        {"host": 1, "text": "So Saylor just dropped another banger..."},
        {"host": 2, "text": "Let's roll the clip."},
        {"host": "CLIP", "duration": 30, "source": "@MicroStrategy"},
        {"host": 2, "text": "Ok here's what blows my mind about this..."},
        {"host": 1, "text": "Right, and if you think about it..."},
    ]

    result = generate_dialogue_audio(dialogue, output_dir="output/")
    # Returns: {
    #   "lines": [...],
    #   "full": "output/full_dialogue.m4a",
    #   "total_duration": 45.0,
    # }
"""
import os
import sys
import json
import subprocess
import time

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

from relay import get_key

# ── Voice configuration ──────────────────────────────────────────────────────
# PBX DIRECTIVE 2026-03-09: SINGLE HOST ONLY — Mark at 1.10x speed.
# Nicole (piTKgcLEGmPE4e6mEKli) and Chris (iP95p4xoKVk53GoZ742B) are BANNED.
# Both host=1 and host=2 map to Mark.

_MARK_VOICE = {
    "voice_id": "1SM7GgM6IMuvQlz2BwM3",
    "name": "Mark",
    "model_id": "eleven_turbo_v2_5",
    "voice_settings": {
        "stability": 0.55,
        "similarity_boost": 0.80,
        "style": 0.15,
        "use_speaker_boost": True,
        "speed": 1.10,
    },
}

VOICES = {
    1: _MARK_VOICE,
    2: _MARK_VOICE,  # both hosts → Mark (single narrator)
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


def _tts_generate_silence_fallback(text: str, output_path: str) -> bool:
    """BUG1 FIX A: Generate silence as last-resort TTS fallback (quota exhausted)."""
    dur = max(2.0, min(30.0, len(text) / 12.5)) if text else 3.0
    r = subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
        "-t", str(dur), "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
        output_path,
    ], capture_output=True, text=True, timeout=15)
    if r.returncode == 0 and os.path.exists(output_path):
        print(f"  [tts] FALLBACK: {dur:.1f}s silence generated (quota exhausted)")
        return True
    return False


def tts_elevenlabs(text: str, output_path: str, host: int = 1) -> bool:
    """Generate TTS audio for a single line using the specified host voice.

    Falls back to pyttsx3 system TTS, then silence, on ElevenLabs quota/auth failure.
    """
    if not HAS_REQUESTS:
        return _tts_generate_silence_fallback(text, output_path)

    key = _get_cached_key("ELEVENLABS_API_KEY")
    if not key:
        return _tts_generate_silence_fallback(text, output_path)

    voice = VOICES.get(host, VOICES[1])
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice['voice_id']}"
    headers = {"xi-api-key": key, "Content-Type": "application/json"}

    chunks = _chunk_text(text)
    chunk_files = []

    for ci, chunk in enumerate(chunks):
        # Extract speed (top-level ElevenLabs param) from voice_settings if present
        raw_settings = dict(voice["voice_settings"])
        speed_val = raw_settings.pop("speed", None)
        body = {
            "text": chunk,
            "model_id": voice["model_id"],
            "voice_settings": raw_settings,
        }
        if speed_val is not None:
            body["speed"] = speed_val
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
            # BUG1 FIX A: Fallback chain — pyttsx3 → silence (never return False)
            print(f"  [tts] ElevenLabs failed — trying pyttsx3 fallback")
            try:
                import pyttsx3
                _engine = pyttsx3.init()
                _engine.setProperty("rate", 150)
                wav_tmp = output_path + ".pyttsx3.wav"
                _engine.save_to_file(chunk, wav_tmp)
                _engine.runAndWait()
                if os.path.exists(wav_tmp) and os.path.getsize(wav_tmp) > 1000:
                    ok = _mp3_to_m4a(wav_tmp, output_path)
                    try:
                        os.remove(wav_tmp)
                    except Exception:
                        pass
                    if ok:
                        return ok
            except Exception as pyttsx_err:
                print(f"  [tts] pyttsx3 unavailable: {pyttsx_err}")
            return _tts_generate_silence_fallback(text, output_path)
        chunk_files.append(mp3_tmp)

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
        dialogue: List of dicts with keys:
            - host: 1 or 2 (both route to Mark), or "CLIP" (silence placeholder)
            - text: The line text (or clip description for CLIP)
            - duration: (CLIP only) silence duration in seconds
            - source: (CLIP only) source channel name

    Returns:
        {
            "lines": [
                {"path": str, "host": int|"CLIP", "duration": float,
                 "start": float, "text": str},
                ...
            ],
            "full": str,          # path to concatenated audio
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

        if host == "CLIP":
            clip_dur = float(entry.get("duration", 30.0))
            lines.append({
                "path": None,
                "host": "CLIP",
                "duration": clip_dur,
                "start": current_time,
                "source": entry.get("source", ""),
                "query": entry.get("query", ""),
                "text": text,
            })
            current_time += clip_dur  # advance timeline so subsequent lines sync correctly
            continue

        host_num = int(host) if host in (1, 2, "1", "2") else 1
        voice = VOICES.get(host_num, VOICES[1])
        line_path = os.path.join(output_dir, f"line_{i:03d}_{voice['name'].lower()}.m4a")

        print(f"  [tts] Line {i:02d} ({voice['name']}): {text[:60]}...")

        if tts_elevenlabs(text, line_path, host_num):
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


if __name__ == "__main__":
    from script_writer import generate_script
    style = sys.argv[1] if len(sys.argv) > 1 else "default"
    script = generate_script(style=style)
    audio_dir = os.path.join(BASE, "output", "audio_test")
    result = generate_dialogue_audio(script["dialogue"], audio_dir)
    print(json.dumps(
        {k: v for k, v in result.items() if k != "lines"},
        indent=2,
    ))
