#!/usr/bin/env python3
"""Step 5: TTS Engine — ElevenLabs Jessica voice. No gTTS fallback.
Production mode: ElevenLabs or fail with clear error."""
import os, sys, json, subprocess, tempfile, time
from pathlib import Path

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

from relay import get_key

# Jessica voice — approved production voice
VOICE_CONFIG = {
    "voice_id": "cgSgspJ2msm6clMCkdW9",
    "model_id": "eleven_turbo_v2_5",
    "voice_settings": {
        "stability": 0.5,
        "similarity_boost": 0.75,
        "style": 0.0,
        "use_speaker_boost": True
    }
}

MAX_CHUNK_CHARS = 4900  # ElevenLabs hard limit is 5000

# Module-level API key cache (avoid repeated relay calls)
_KEY_CACHE: dict = {}


def _get_cached_key(name: str) -> str:
    """Get API key, caching after first fetch."""
    if name not in _KEY_CACHE:
        k = get_key(name)
        if k:
            _KEY_CACHE[name] = k.strip()
    return _KEY_CACHE.get(name, "")


def ffprobe_duration(path: str) -> float:
    """Get audio duration via ffprobe."""
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path],
        capture_output=True, text=True
    )
    try:
        return float(r.stdout.strip())
    except Exception:
        return 0.0


def _chunk_text(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list:
    """Split text into chunks at sentence boundaries."""
    if len(text) <= max_chars:
        return [text]

    # Split on sentence endings
    raw = text.replace("! ", "!\x00").replace(". ", ".\x00").replace("? ", "?\x00")
    sentences = raw.split("\x00")

    chunks = []
    current = ""
    for sent in sentences:
        if len(current) + len(sent) + 1 <= max_chars:
            current = f"{current} {sent}".strip() if current else sent
        else:
            if current:
                chunks.append(current)
            if len(sent) > max_chars:
                # Sentence too long — split on spaces
                words = sent.split()
                current = ""
                for word in words:
                    if len(current) + len(word) + 1 <= max_chars:
                        current = f"{current} {word}".strip() if current else word
                    else:
                        if current:
                            chunks.append(current)
                        current = word
            else:
                current = sent
    if current:
        chunks.append(current)
    return [c for c in chunks if c.strip()]


def _mp3_to_m4a(mp3_path: str, m4a_path: str) -> bool:
    """Convert MP3 to M4A/AAC for consistent downstream handling."""
    r = subprocess.run(
        ["ffmpeg", "-y", "-i", mp3_path,
         "-c:a", "aac", "-ar", "44100", "-ac", "1", "-b:a", "192k", m4a_path],
        capture_output=True, text=True, timeout=120
    )
    return r.returncode == 0 and os.path.exists(m4a_path)


def tts_elevenlabs(text: str, output_path: str) -> bool:
    """Generate TTS via ElevenLabs Jessica voice.
    Supports chunking (>4900 chars), 3-attempt retry, timing logs.
    Returns False on failure — caller should raise if ElevenLabs is required."""
    if not HAS_REQUESTS:
        print("  [elevenlabs] FAIL: requests library not installed")
        return False

    key = _get_cached_key("ELEVENLABS_API_KEY")
    if not key:
        print("  [elevenlabs] FAIL: ELEVENLABS_API_KEY not found")
        return False

    t_start = time.time()
    chunks = _chunk_text(text)
    if len(chunks) > 1:
        print(f"  [elevenlabs] Text split into {len(chunks)} chunks ({len(text)} chars total)")

    chunk_files = []
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_CONFIG['voice_id']}"
    headers = {"xi-api-key": key, "Content-Type": "application/json"}

    for ci, chunk in enumerate(chunks):
        body = {
            "text": chunk,
            "model_id": VOICE_CONFIG["model_id"],
            "voice_settings": VOICE_CONFIG["voice_settings"]
        }
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
                    print(f"  [elevenlabs] Rate limited, waiting {wait}s... (attempt {attempt+1}/3)")
                    time.sleep(wait)
                else:
                    print(f"  [elevenlabs] HTTP {r.status_code} on attempt {attempt+1}: {r.text[:200]}")
                    if attempt < 2:
                        time.sleep(2 ** attempt)
            except Exception as e:
                print(f"  [elevenlabs] Attempt {attempt+1}/3 error: {e}")
                if attempt < 2:
                    time.sleep(2 ** attempt)

        if not success:
            # Cleanup partial chunks
            for f in chunk_files:
                try:
                    os.remove(f)
                except Exception:
                    pass
            if os.path.exists(mp3_tmp):
                os.remove(mp3_tmp)
            print(f"  [elevenlabs] FAIL after 3 attempts on chunk {ci}")
            return False

        chunk_files.append(mp3_tmp)

    # Single chunk → convert directly
    if len(chunk_files) == 1:
        ok = _mp3_to_m4a(chunk_files[0], output_path)
        try:
            os.remove(chunk_files[0])
        except Exception:
            pass
        if ok:
            elapsed = time.time() - t_start
            dur = ffprobe_duration(output_path)
            print(f"  [elevenlabs] Narration: {dur:.1f}s of audio generated in {elapsed:.1f}s")
        return ok

    # Multiple chunks → concat MP3s then convert
    concat_list = output_path + ".concat_list.txt"
    mp3_combined = output_path + ".combined.mp3"
    with open(concat_list, "w") as f:
        for p in chunk_files:
            f.write(f"file '{os.path.abspath(p)}'\n")

    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
         "-c", "copy", mp3_combined],
        capture_output=True, text=True
    )
    ok = _mp3_to_m4a(mp3_combined, output_path)

    # Cleanup
    for f in chunk_files + [concat_list, mp3_combined]:
        try:
            if os.path.exists(f):
                os.remove(f)
        except Exception:
            pass

    if ok:
        elapsed = time.time() - t_start
        dur = ffprobe_duration(output_path)
        print(f"  [elevenlabs] Narration: {dur:.1f}s of audio generated in {elapsed:.1f}s ({len(chunks)} chunks)")
    return ok


def generate_segment_audio(text: str, output_path: str, label: str = "") -> bool:
    """Generate TTS for a segment via ElevenLabs (Jessica voice).
    No fallback — raises RuntimeError if ElevenLabs fails."""
    print(f"  [tts] Generating: {label}...")

    if tts_elevenlabs(text, output_path):
        return True

    raise RuntimeError(
        f"ElevenLabs TTS failed for segment '{label}'. "
        "Check ELEVENLABS_API_KEY and API quota. "
        "No fallback TTS is configured in production mode."
    )


def generate_all_audio(script: dict, output_dir: str) -> dict:
    """Generate all TTS audio files from a script. Returns paths dict."""
    os.makedirs(output_dir, exist_ok=True)
    paths = {}

    # Pre-fetch the key once (caches it)
    key = _get_cached_key("ELEVENLABS_API_KEY")
    if not key:
        raise RuntimeError("ELEVENLABS_API_KEY not available. Cannot generate audio.")

    # Cold open
    cold_path = os.path.join(output_dir, "cold_open.m4a")
    if generate_segment_audio(script["cold_open"], cold_path, "cold_open"):
        paths["cold_open"] = cold_path

    # Segments
    paths["segments"] = []
    for i, seg in enumerate(script["segments"]):
        seg_path = os.path.join(output_dir, f"seg_{i:02d}.m4a")
        if generate_segment_audio(seg["narration"], seg_path, f"seg_{i:02d} — {seg['headline']}"):
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

    # Concatenate all into full_narration
    all_parts = []
    if "cold_open" in paths:
        all_parts.append(paths["cold_open"])
    for i in range(len(script["segments"])):
        if paths["segments"][i]:
            all_parts.append(paths["segments"][i])
        bridges = paths.get("bridges", [])
        if i < len(bridges) and bridges[i]:
            all_parts.append(bridges[i])
        editorials = paths.get("editorials", [])
        if i < len(editorials) and editorials[i]:
            all_parts.append(editorials[i])
    if "outro" in paths:
        all_parts.append(paths["outro"])

    if all_parts:
        concat_file = os.path.join(output_dir, "concat_list.txt")
        with open(concat_file, "w") as f:
            for p in all_parts:
                f.write(f"file '{os.path.abspath(p)}'\n")
        full_path = os.path.join(output_dir, "full_narration.m4a")
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_file,
             "-c", "copy", full_path],
            capture_output=True, text=True
        )
        if os.path.exists(full_path):
            paths["full"] = full_path
            dur = ffprobe_duration(full_path)
            print(f"\n  [tts] Full narration: {dur:.1f}s total")

    # Verification summary
    print("\n  [tts] Audio verification:")
    for key_name, val in paths.items():
        if isinstance(val, str) and os.path.exists(val):
            dur = ffprobe_duration(val)
            sz = os.path.getsize(val)
            print(f"    {key_name}: {dur:.1f}s, {sz // 1024}KB")

    return paths


if __name__ == "__main__":
    from script_writer import generate_script
    style = sys.argv[1] if len(sys.argv) > 1 else "default"
    script = generate_script(style=style)
    base = os.path.dirname(os.path.abspath(__file__))
    audio_dir = os.path.join(base, "output", "audio_test")
    paths = generate_all_audio(script, audio_dir)
    print(json.dumps({k: v for k, v in paths.items() if isinstance(v, str)}, indent=2))
