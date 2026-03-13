#!/usr/bin/env python3
"""TTS Engine V7 — Dual-provider: ElevenLabs (default) + Inworld.
Host 1 (Eryn): kdnRe2koJdOK4Ovxn2DI at 1.12x — sharp female setup host.
Host 2 (Mark): 1SM7GgM6IMuvQlz2BwM3 at 1.10x — male contrarian react host.
Generates per-line audio with 0.3s silence gaps."""
import os, sys, json, subprocess, tempfile, time, struct
from pathlib import Path

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

from relay import get_key

# DUAL HOST RESTORED 2026-03-10: Eryn (HOST_1) + Mark (HOST_2)
# Nicole/Chris/Deborah/Brian are all BANNED.
_NATASHA_VOICE = {
    "voice_id": "kdnRe2koJdOK4Ovxn2DI",
    "name": "Eryn",
    "model_id": "eleven_turbo_v2_5",
    "speed": 1.12,
    "voice_settings": {
        "stability": 0.55,
        "similarity_boost": 0.80,
        "style": 0.15,
        "use_speaker_boost": True,
    },
}

_MARK_VOICE = {
    "voice_id": "1SM7GgM6IMuvQlz2BwM3",
    "name": "Mark",
    "model_id": "eleven_turbo_v2_5",
    "speed": 1.10,
    "voice_settings": {
        "stability": 0.55,
        "similarity_boost": 0.80,
        "style": 0.15,
        "use_speaker_boost": True,
    },
}

VOICES = {
    1: _NATASHA_VOICE,   # HOST_1 → Eryn (female)
    2: _MARK_VOICE,   # HOST_2 → Mark (male)
}

# ── INWORLD VOICE CONFIGS (set TTS_PROVIDER=inworld in .env to activate) ──
# Winners selected 2026-03-12: Lauren (sharp female) + Nate (authoritative male)
_LAUREN_INWORLD = {
    "voice_id": "Lauren",
    "name": "Lauren",
    "model_id": "inworld-tts-1.5-max",
    "speed": 1.0,
    "temperature": 0.5,
}
_NATE_INWORLD = {
    "voice_id": "Nate",
    "name": "Nate",
    "model_id": "inworld-tts-1.5-max",
    "speed": 1.0,
    "temperature": 0.5,
}
INWORLD_VOICES = {
    1: _LAUREN_INWORLD,
    2: _NATE_INWORLD,
}

def _get_tts_provider() -> str:
    """TTS provider locked to ElevenLabs per PIPELINE_LAWS."""
    val = os.environ.get("TTS_PROVIDER", "elevenlabs").lower().strip()
    if val != "elevenlabs":
        raise RuntimeError(
            f"[TTS] PIPELINE_LAWS violation: TTS_PROVIDER must be 'elevenlabs', got '{val}'. "
            "Inworld returns 0 bytes — never switch providers."
        )
    return "elevenlabs"


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
        logger.warning(f"[TTS] ffprobe_duration failed for {path}")
        return -1.0


def _generate_silence(output_path: str, duration: float) -> bool:
    """Generate a silent audio file."""
    r = subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i",
         f"anullsrc=r=48000:cl=stereo", "-t", str(duration),
         "-c:a", "aac", "-b:a", "192k", output_path],
        capture_output=True, text=True, timeout=30,
    )
    return r.returncode == 0 and os.path.exists(output_path)


def _mp3_to_m4a(mp3_path: str, m4a_path: str) -> bool:
    r = subprocess.run(
        ["ffmpeg", "-y", "-i", mp3_path,
         "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k", m4a_path],
        capture_output=True, text=True, timeout=120,
    )
    return r.returncode == 0 and os.path.exists(m4a_path)


MAX_CHUNK_CHARS = 500  # ElevenLabs safe chunk size
SILENCE_GAP = 0.3  # seconds between speakers


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


def expand_numbers_for_tts(text: str) -> str:
    """Session 4 Fix 3: Expand numbers and abbreviations so ElevenLabs reads them naturally."""
    import re as _re

    # Dollar amounts: $83,420 → "83 thousand 420 dollars"
    def _dollar(m):
        val_str = m.group(1).replace(",", "")
        try:
            val = int(float(val_str))
        except ValueError:
            return m.group(0)
        if val >= 1_000_000_000:
            return f"{val/1_000_000_000:.1f} billion dollars".replace(".0 ", " ")
        if val >= 1_000_000:
            return f"{val/1_000_000:.1f} million dollars".replace(".0 ", " ")
        if val >= 1_000:
            b = val // 1000
            r = val % 1000
            if r == 0:
                return f"{b} thousand dollars"
            return f"{b} thousand {r} dollars"
        return f"{val} dollars"

    # Dollar + billion/million shorthand first: $1.2 billion → "1.2 billion dollars"
    text = _re.sub(r'\$(\d+(?:\.\d+)?)\s*[Bb]illion', lambda m: f"{m.group(1)} billion dollars", text)
    text = _re.sub(r'\$(\d+(?:\.\d+)?)\s*[Mm]illion', lambda m: f"{m.group(1)} million dollars", text)

    text = _re.sub(r'\$([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?)', _dollar, text)

    # Large plain numbers with commas: 70,015 → "70 thousand 15"
    def _plain_num(m):
        val_str = m.group(0).replace(",", "")
        try:
            val = int(val_str)
        except ValueError:
            return m.group(0)
        if val >= 1_000_000_000:
            return f"{val/1_000_000_000:.1f} billion".replace(".0 ", " ")
        if val >= 1_000_000:
            return f"{val/1_000_000:.1f} million".replace(".0 ", " ")
        if val >= 10_000:
            b = val // 1000
            r = val % 1000
            if r == 0:
                return f"{b} thousand"
            return f"{b} thousand {r}"
        return m.group(0)  # leave small numbers as-is
    text = _re.sub(r'\b\d{1,3}(?:,\d{3})+\b', _plain_num, text)

    # Percentages: 8.4% → "8 point 4 percent"
    def _pct(m):
        return m.group(1).replace(".", " point ") + " percent"
    text = _re.sub(r'([\d.]+)%', _pct, text)

    # Hashrate units
    text = _re.sub(r'(\d+(?:\.\d+)?)\s*EH/?s', lambda m: f"{m.group(1)} exahash per second", text)
    text = _re.sub(r'(\d+(?:\.\d+)?)\s*TH/?s', lambda m: f"{m.group(1)} terahash per second", text)
    text = _re.sub(r'(\d+(?:\.\d+)?)\s*PH/?s', lambda m: f"{m.group(1)} petahash per second", text)

    # Billion/million shorthand already in text (normalize)
    text = _re.sub(r'(\d+(?:\.\d+)?)\s*[Bb]illion', lambda m: f"{m.group(1)} billion", text)
    text = _re.sub(r'(\d+(?:\.\d+)?)\s*[Mm]illion', lambda m: f"{m.group(1)} million", text)

    # K shorthand: 74K → "74 thousand"
    def _k(m):
        val = float(m.group(1))
        if val == int(val):
            return f"{int(val)} thousand"
        return f"{val} thousand"
    text = _re.sub(r'(\d+(?:\.\d+)?)[Kk]\b', _k, text)

    return text


TTS_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tts_cache")


def _tts_cache_key(text: str, voice_id: str, segment_type: str) -> str:
    """SHA256 hash of text+voice+segment_type → stable cache key."""
    import hashlib
    payload = f"{voice_id}:{segment_type}:{text}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def _tts_cache_get(cache_key: str, output_path: str) -> bool:
    """Return True if valid cached file exists and passes validation."""
    cache_file = os.path.join(TTS_CACHE_DIR, f"{cache_key}.m4a")
    if os.path.exists(cache_file) and os.path.getsize(cache_file) > 10240:
        shutil.copy2(cache_file, output_path)
        try:
            validate_tts_output(output_path)
            return True
        except RuntimeError:
            logger.warning(f"[TTS] Corrupt cache deleted: {cache_file}")
            try:
                os.remove(cache_file)
                os.remove(output_path)
            except Exception:
                pass
    return False


def _tts_cache_put(cache_key: str, audio_path: str) -> None:
    """Save audio to TTS cache for future runs."""
    import shutil
    os.makedirs(TTS_CACHE_DIR, exist_ok=True)
    cache_file = os.path.join(TTS_CACHE_DIR, f"{cache_key}.m4a")
    if not os.path.exists(cache_file):
        shutil.copy2(audio_path, cache_file)


def _tts_generate_silence_fallback(text: str, output_path: str) -> bool:
    """HARD FAIL: silence fallback is no longer allowed.

    Previously generated silent AAC as a last resort, masking total TTS failure.
    This caused downstream black frames and F-grade renders that QC scored 94/100.
    Now raises RuntimeError so the pipeline fails fast instead of rendering garbage.
    """
    snippet = (text[:80] + "...") if len(text) > 80 else text
    raise RuntimeError(
        f"TTS FATAL: ElevenLabs + pyttsx3 both failed. Refusing to render silence. "
        f"Text: \"{snippet}\". Fix the TTS provider before re-running."
    )


def validate_tts_output(path: str, min_size: int = 10240) -> None:
    """Validate TTS output file is real audio, not empty/corrupt.

    Raises RuntimeError if:
      - File doesn't exist
      - File < min_size bytes (10KB default)
      - ffprobe duration < 0.5s
    """
    if not os.path.exists(path):
        raise RuntimeError(f"TTS output missing: {path}")
    size = os.path.getsize(path)
    if size < min_size:
        raise RuntimeError(
            f"TTS output too small ({size} bytes < {min_size}): {path} — "
            f"ElevenLabs likely returned empty audio"
        )
    dur = ffprobe_duration(path)
    if dur < 0.5:
        raise RuntimeError(
            f"TTS output too short ({dur:.2f}s < 0.5s): {path} — "
            f"audio is effectively silent/corrupt"
        )


def tts_inworld(text: str, output_path: str, host: int = 1,
                segment_type: str = "narration") -> bool:
    """DISABLED: Inworld TTS banned per PIPELINE_LAWS (0-byte synthesis)."""
    raise RuntimeError(
        "Inworld TTS is disabled per PIPELINE_LAWS. TTS_PROVIDER must be 'elevenlabs'. "
        "Inworld synthesis returns 0 bytes — account not provisioned."
    )


def tts_elevenlabs(text: str, output_path: str, host: int = 1,
                   segment_type: str = "") -> bool:
    """Generate TTS for a single line using the specified host voice.

    Checks TTS cache first (hash of text+voice+segment_type). On cache hit,
    copies cached audio — no ElevenLabs API call. On miss, generates and caches.
    Falls back to pyttsx3 system TTS, then silence, on ElevenLabs quota/auth failure.
    """
    if not HAS_REQUESTS:
        # No requests lib — try pyttsx3 or silence
        return _tts_generate_silence_fallback(text, output_path)

    key = _get_cached_key("ELEVENLABS_API_KEY")
    if not key:
        return _tts_generate_silence_fallback(text, output_path)

    # Session 4 Fix 3: Expand numbers before TTS to prevent babbling
    text = expand_numbers_for_tts(text)

    voice = VOICES.get(host, VOICES[1])
    # Check TTS cache first — avoid API call if same text+voice was generated before
    cache_key = _tts_cache_key(text, voice["voice_id"], segment_type)
    if _tts_cache_get(cache_key, output_path):
        print(f"  [tts] Cache HIT ({voice['name']}): {text[:50]}...")
        return True

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice['voice_id']}"
    headers = {"xi-api-key": key, "Content-Type": "application/json"}

    # Apply voice mode overrides based on segment type (both hosts)
    voice_settings = dict(voice["voice_settings"])
    if segment_type in VOICE_MODES:
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
        # Add speed parameter from voice config (host-specific)
        speed = voice.get("speed", 1.0)
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
                    # Pre-validate: ElevenLabs sometimes returns empty/tiny responses
                    if os.path.getsize(mp3_tmp) < 1000:
                        print(f"  [tts] WARNING: ElevenLabs returned tiny file ({os.path.getsize(mp3_tmp)}B) for chunk {ci}, retrying...")
                        if attempt < 2:
                            time.sleep(2 ** attempt)
                            continue
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
            print(f"  [tts] ElevenLabs failed for chunk {ci} — falling back entire text to pyttsx3")
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
            # Final fallback: generate silence so the segment still renders
            return _tts_generate_silence_fallback(text, output_path)
        chunk_files.append(mp3_tmp)

    # Single chunk
    if len(chunk_files) == 1:
        ok = _mp3_to_m4a(chunk_files[0], output_path)
        try:
            os.remove(chunk_files[0])
        except Exception:
            pass
        if ok and os.path.exists(output_path):
            validate_tts_output(output_path)
            _tts_cache_put(cache_key, output_path)
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
    if ok and os.path.exists(output_path):
        validate_tts_output(output_path)
        _tts_cache_put(cache_key, output_path)
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

    # Only require ElevenLabs key if actually using ElevenLabs
    _active_provider = _get_tts_provider()
    if _active_provider == "elevenlabs":
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

        # Skip CLIP markers — they don't have audio but DO advance the timeline
        if host == "CLIP":
            clip_duration = float(entry.get("duration", 30.0))  # use actual duration or default 30s
            lines.append({
                "path": None,
                "host": "CLIP",
                "duration": clip_duration,  # record actual duration, not hardcoded 0.0
                "start": current_time,
                "source": entry.get("source", ""),
                "query": entry.get("query", ""),
                "text": text,
            })
            current_time += clip_duration  # advance timeline so subsequent audio is correctly offset
            continue

        host_num = int(host) if host in (1, 2, "1", "2") else 1
        voice = VOICES.get(host_num, VOICES[1])
        segment_type = entry.get("type", "")
        line_path = os.path.join(output_dir, f"line_{i:03d}_{voice['name'].lower()}.m4a")

        mode_tag = f" [{segment_type}]" if segment_type and host_num == 1 else ""
        print(f"  [tts] Line {i:02d} ({voice['name']}{mode_tag}): {text[:60]}...")

        _provider = _get_tts_provider()
        # ElevenLabs only — Inworld disabled per PIPELINE_LAWS
        _tts_ok = tts_elevenlabs(text, line_path, host_num, segment_type=segment_type)
        if _tts_ok:
            dur = ffprobe_duration(line_path)
            lines.append({
                "path": line_path,
                "host": host_num,
                "duration": dur,
                "start": current_time,
                "text": text,
                "type": segment_type,
                "clip_rank": entry.get("clip_rank", 0),  # PiP FIX: preserve for assembler PiP lookup
            })
            parts_for_concat.append(line_path)
            current_time += dur

            # Add silence gap between speakers (not after last line, not before CLIP)
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
                "type": segment_type,
                "clip_rank": entry.get("clip_rank", 0),  # PiP FIX: preserve for assembler PiP lookup
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

    # Guard: full_dialogue.m4a must not be zero-byte or tiny
    if os.path.exists(full_path):
        full_size = os.path.getsize(full_path)
        if full_size < 10240:
            raise RuntimeError(
                f"full_dialogue.m4a is {full_size} bytes (<10KB) — "
                f"FFmpeg concat produced empty/corrupt audio. Aborting before render."
            )

    total_dur = ffprobe_duration(full_path) if os.path.exists(full_path) else current_time
    successful = sum(1 for l in lines if l["path"] and os.path.exists(l.get("path", "")))

    print(f"\n  [tts] Dialogue audio: {successful}/{len(dialogue)} lines, {total_dur:.1f}s total")

    # ── Per-host TTS validation: catch silent hosts BEFORE render starts ──
    host_stats = {}  # {host_num: {"total": N, "ok": N}}
    for l in lines:
        h = l.get("host")
        if h == "CLIP":
            continue
        if h not in host_stats:
            host_stats[h] = {"total": 0, "ok": 0}
        host_stats[h]["total"] += 1
        if l.get("path") and os.path.exists(l.get("path", "")):
            host_stats[h]["ok"] += 1

    for h, stats in host_stats.items():
        voice_name = VOICES.get(h, {}).get("name", f"Host{h}")
        if stats["ok"] == 0 and stats["total"] > 0:
            raise RuntimeError(
                f"TTS FATAL: {voice_name} (host {h}) has 0/{stats['total']} successful lines. "
                f"All audio is missing/silent. Aborting before render."
            )
        if stats["total"] > 0 and stats["ok"] / stats["total"] < 0.5:
            raise RuntimeError(
                f"TTS FATAL: {voice_name} (host {h}) has only {stats['ok']}/{stats['total']} "
                f"successful lines (<50%). Too many failures to produce a quality render."
            )

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
