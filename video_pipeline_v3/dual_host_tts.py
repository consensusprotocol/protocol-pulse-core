#!/usr/bin/env python3
"""dual_host_tts.py — Dual-host TTS engine for Pulse Check.

Generates audio using ElevenLabs TTS.
Host 1 (Deborah): VeCVR24o7g2y1IxLJzZs — female newscaster, 1.0x speed.
Host 2 (PBX): HmUVvDlHsEz0m3eUGLgu — male contrarian, 1.2x speed.
NOTE: uxKr2vlA4hYgXZR1oPRT is PERMANENTLY BANNED (see PIPELINE_LAWS.md).
NOTE: kdnRe2koJdOK4Ovxn2DI (Eryn) is BANNED as of Render20.

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
import re
import sys
import json
import subprocess
import time
try:
    from tts_engine import expand_numbers_for_tts, apply_pronunciation_map
except ImportError:
    def expand_numbers_for_tts(t): return t

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

from relay import get_key

# ── Voice configuration ──────────────────────────────────────────────────────
# DUAL HOST RESTORED 2026-03-10: Deborah (HOST_1) + PBX (HOST_2)
# BANNED voices — ERROR if any appear:
#   Nicole (piTKgcLEGmPE4e6mEKli), Chris (iP95p4xoKVk53GoZ742B),
#   Eryn (kdnRe2koJdOK4Ovxn2DI), uxKr2vlA4hYgXZR1oPRT
_BANNED_VOICE_IDS = {"piTKgcLEGmPE4e6mEKli", "iP95p4xoKVk53GoZ742B", "kdnRe2koJdOK4Ovxn2DI", "uxKr2vlA4hYgXZR1oPRT"}

_NATASHA_VOICE = {
    "voice_id": "VeCVR24o7g2y1IxLJzZs",
    "name": "Deborah",
    "model_id": "eleven_turbo_v2_5",
    "voice_settings": {
        "stability": 0.55,
        "similarity_boost": 0.80,
        "style": 0.30,
        "use_speaker_boost": True,
        "speed": 1.0,
    },
}

_PBX_VOICE = {
    "voice_id": "HmUVvDlHsEz0m3eUGLgu",
    "name": "PBX",
    "model_id": "eleven_turbo_v2_5",
    "voice_settings": {
        "stability": 0.55,
        "similarity_boost": 0.80,
        "style": 0.15,
        "use_speaker_boost": True,
        "speed": 1.2,  # Render20: +10% from 1.10 → 1.21, capped at ElevenLabs max 1.2
    },
}

VOICES = {
    1: _NATASHA_VOICE,   # HOST_1 → Eryn (female)
    2: _PBX_VOICE,       # HOST_2 → PBX (male)
}

SILENCE_GAP = 0.03  # seconds between speakers (render18: 0.05→0.03 — tighter handoffs, eliminates dead air)
MAX_CHUNK_CHARS = 4900

# Render12 FIX 3: Key emphasis words for natural delivery
_EMPHASIS_WORDS = {"Bitcoin", "ETF", "billion", "trillion", "record", "halving", "hashrate", "sovereign"}


def _apply_prosody_substitutions(text: str) -> str:
    """Render12: Text-level prosody for natural AI voice delivery.

    ElevenLabs eleven_turbo_v2_5 does NOT support SSML — use text substitutions:
    1. Natural pauses after commas via ellipsis
    2. Slow down numbers by spacing digits in large numbers
    3. Emphasis on key words via CAPS (ElevenLabs reads caps with emphasis)
    """
    import re

    # 1. Natural pauses: replace ", " with " ... " for breath-like pauses
    # Only for mid-sentence commas (not inside numbers like "1,000")
    text = re.sub(r',\s+(?=[A-Za-z])', ' ... ', text)

    # 2. Numbers: add slight pauses around large numbers for clarity
    # "96482" → "96,482" (ElevenLabs handles formatted numbers better)
    def _format_number(m):
        num_str = m.group(0)
        if len(num_str) >= 4 and '.' not in num_str:
            try:
                return f"{int(num_str):,}"
            except ValueError:
                return num_str
        return num_str
    text = re.sub(r'\b\d{4,}\b', _format_number, text)

    # 3. Emphasis: capitalize key words (ElevenLabs adds natural stress to CAPS)
    for word in _EMPHASIS_WORDS:
        text = re.sub(r'\b' + re.escape(word) + r'\b', word.upper(), text, flags=re.IGNORECASE)

    return text

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


def trim_to_sentence(text: str, max_chars: int = 800) -> str:
    """Trim text at the last sentence boundary before max_chars.

    Render20: max_chars raised to 800. Only trim at natural sentence end —
    never mid-word, never mid-thought.
    """
    if len(text) <= max_chars:
        return text
    chunk = text[:max_chars]
    # Render18 FIX 3: Require min 20 chars before boundary and 15 chars after
    matches = [m for m in re.finditer(r'[.!?](?:\s|$)', chunk)
               if m.start() > 20 and (len(chunk) - m.end()) > 15]
    if matches:
        last = matches[-1]
        return text[:last.end()].strip()
    # Fallback: any sentence boundary (relaxed constraint)
    all_matches = list(re.finditer(r'[.!?](?:\s|$)', chunk))
    if all_matches:
        last = all_matches[-1]
        return text[:last.end()].strip()
    # No sentence boundary — trim at last word boundary
    last_space = chunk.rfind(' ')
    return (text[:last_space] if last_space > 0 else chunk).strip()


def _chunk_text(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list:
    if len(text) <= max_chars:
        return [text]
    raw = text.replace("! ", "!\x00").replace(". ", ".\x00").replace("? ", "?\x00")
    sentences = raw.split("\x00")
    chunks, current = [], ""
    for sent in sentences:
        # Safety: trim overly long sentences at sentence/word boundary
        if len(sent) > max_chars:
            sent = trim_to_sentence(sent, max_chars)
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
    """HARD FAIL: silence fallback is no longer allowed.

    Previously generated silent AAC masking total TTS failure.
    Now raises RuntimeError so the pipeline fails fast.
    """
    snippet = (text[:80] + "...") if len(text) > 80 else text
    raise RuntimeError(
        f"TTS FATAL: ElevenLabs + pyttsx3 both failed. Refusing to render silence. "
        f"Text: \"{snippet}\". Fix the TTS provider before re-running."
    )


def tts_elevenlabs(text: str, output_path: str, host: int = 1) -> bool:
    """Generate TTS audio for a single line using the specified host voice.

    Falls back to pyttsx3 system TTS, then silence, on ElevenLabs quota/auth failure.
    """
    # Render20: Banned voice guard
    voice = VOICES.get(host, VOICES[1])
    if voice["voice_id"] in _BANNED_VOICE_IDS:
        import logging as _lg
        _lg.getLogger("dual_host_tts").error(f"BANNED VOICE DETECTED: {voice['voice_id']} ({voice['name']})")
        raise RuntimeError(f"BANNED voice {voice['voice_id']} attempted — aborting")

    if not HAS_REQUESTS:
        return _tts_generate_silence_fallback(text, output_path)

    key = _get_cached_key("ELEVENLABS_API_KEY")
    if not key:
        return _tts_generate_silence_fallback(text, output_path)

    voice = VOICES.get(host, VOICES[1])
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice['voice_id']}"
    headers = {"xi-api-key": key, "Content-Type": "application/json"}

    text = expand_numbers_for_tts(text)
    text = apply_pronunciation_map(text)  # Fix 3: number babble prevention
    text = _apply_prosody_substitutions(text)  # Render12: natural delivery
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
            # P0.6 FIX: Fall back the ENTIRE text to pyttsx3 (not just this chunk).
            # Returning inside the chunk loop would abandon remaining chunks.
            print(f"  [tts] ElevenLabs failed — falling back entire text to pyttsx3")
            try:
                import pyttsx3
                _engine = pyttsx3.init()
                _engine.setProperty("rate", 150)
                wav_tmp = output_path + ".pyttsx3.wav"
                _engine.save_to_file(text, wav_tmp)  # full text, not just the failed chunk
                _engine.runAndWait()
                if os.path.exists(wav_tmp) and os.path.getsize(wav_tmp) > 1000:
                    ok = _mp3_to_m4a(wav_tmp, output_path)
                    try:
                        os.remove(wav_tmp)
                    except Exception:
                        pass
                    if ok:
                        print(f"  [tts] pyttsx3 fallback SUCCESS (full text)")
                        return True
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
        # P1.1 FIX: Route to pyttsx3 fallback instead of hard-failing.
        # tts_elevenlabs() below already handles missing key gracefully — this guard
        # was defeating that. Log a warning and continue so fallback is reachable.
        import logging as _logging
        _logging.warning("generate_dialogue_audio: ELEVENLABS_API_KEY missing — pyttsx3 fallback will be used")

    silence_path = os.path.join(output_dir, "silence.m4a")
    _generate_silence(silence_path, SILENCE_GAP)

    # IRON LAW: PBX (HOST_2) MUST always open the episode — unconditional
    for _idx, _entry in enumerate(dialogue):
        if _entry.get("host") != "CLIP" and _entry.get("host") != "SFX":
            _entry["host"] = 2  # Force PBX regardless of current value
            print(f"[TTS] IRON LAW: Forced PBX opener on line {_idx}")
            break

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

            # Don't insert silence before a CLIP — it has its own timing
            next_entry = dialogue[i + 1] if i < len(dialogue) - 1 else None
            if next_entry is not None and next_entry.get("host") != "CLIP":
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
