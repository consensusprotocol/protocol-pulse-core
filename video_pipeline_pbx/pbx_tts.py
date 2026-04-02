#!/usr/bin/env python3
"""PBX TTS Engine — Single-voice ElevenLabs pipeline.

Voice: PBX (HmUVvDlHsEz0m3eUGLgu) via ElevenLabs eleven_turbo_v2_5 at 1.2x.
No dual-host. No Kokoro. Pure PBX narrator.

Usage:
    from pbx_tts import generate_pbx_audio
    results = generate_pbx_audio(dialogue, output_dir)
"""
import os, sys, json, subprocess, tempfile, time, shutil, logging, re, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Add parent paths for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "video_pipeline_v3"))

from relay import get_key

try:
    from video_pipeline_v3.tts_normalizer import normalize as tts_normalize
except ImportError:
    try:
        from tts_normalizer import normalize as tts_normalize
    except ImportError:
        def tts_normalize(text):
            return text

logger = logging.getLogger("pbx_tts")

# ── Rate limiter ─────────────────────────────────────────────────────────────
_el_rate_lock = threading.Lock()
_el_rate_calls = []
_EL_RATE_LIMIT = int(os.getenv("ELEVENLABS_RATE_LIMIT_PER_MINUTE", "30"))


def _elevenlabs_rate_limit():
    with _el_rate_lock:
        now = time.time()
        _el_rate_calls[:] = [t for t in _el_rate_calls if now - t < 60]
        if len(_el_rate_calls) >= _EL_RATE_LIMIT:
            wait = 60 - (now - _el_rate_calls[0])
            if wait > 0:
                logger.warning(f"ElevenLabs rate limit — waiting {wait:.1f}s")
                time.sleep(wait)
        _el_rate_calls.append(time.time())


# ── PBX Voice Config ─────────────────────────────────────────────────────────
PBX_VOICE_ID = "HmUVvDlHsEz0m3eUGLgu"
PBX_MODEL = "eleven_turbo_v2_5"
PBX_SPEED = 1.20

PBX_VOICE_SETTINGS = {
    "stability": 0.35,
    "similarity_boost": 0.90,
    "style": 0.30,
    "use_speaker_boost": True,
}

# Per-segment voice tuning (same base, but allows future differentiation)
VOICE_MODES = {
    "cold_open":      {"stability": 0.35, "similarity_boost": 0.90, "style": 0.35},
    "setup":          {"stability": 0.35, "similarity_boost": 0.90, "style": 0.30},
    "react":          {"stability": 0.35, "similarity_boost": 0.90, "style": 0.30},
    "social_segment": {"stability": 0.35, "similarity_boost": 0.90, "style": 0.25},
    "wrap":           {"stability": 0.40, "similarity_boost": 0.90, "style": 0.35},
    "data":           {"stability": 0.40, "similarity_boost": 0.90, "style": 0.20},
}

MAX_CHUNK_CHARS = 500
SILENCE_GAP = 0.08  # seconds between lines

_KEY_CACHE = {}


def _get_api_key() -> str:
    if "ELEVENLABS_API_KEY" not in _KEY_CACHE:
        k = get_key("ELEVENLABS_API_KEY")
        if k:
            _KEY_CACHE["ELEVENLABS_API_KEY"] = k.strip()
    return _KEY_CACHE.get("ELEVENLABS_API_KEY", "")


# ── Text Processing ──────────────────────────────────────────────────────────

def expand_numbers_for_tts(text: str) -> str:
    """Convert numbers >999 to spoken words for natural TTS output."""
    try:
        from num2words import num2words as _n2w
    except ImportError:
        return text

    # Year detection: 1600-2099 not preceded by $
    def _year_to_words(y):
        if 2000 <= y <= 2009:
            return f"two thousand {_n2w(y - 2000) if y > 2000 else ''}".strip()
        if 2010 <= y <= 2099:
            return f"twenty {_n2w(y - 2000)}"
        hi, lo = y // 100, y % 100
        hi_word = _n2w(hi)
        if lo == 0:
            return f"{hi_word} hundred"
        elif lo < 10:
            return f"{hi_word} oh {_n2w(lo)}"
        return f"{hi_word} {_n2w(lo)}"

    def _year_sub(m):
        return _year_to_words(int(m.group(0)))

    text = re.sub(
        r'(?<!\$)(?<!\d)\b(1[6-9]\d{2}|20[0-9]\d)\b(?!\s*(?:EH|TH|PH|dollars|percent|%|K\b))',
        _year_sub, text
    )

    # Dollar abbreviations: $2B → "2 billion dollars"
    _scale = {"B": "billion", "M": "million", "T": "trillion", "K": "thousand"}
    def _dollar_abbr(m):
        num = float(m.group(1))
        sw = _scale.get(m.group(2).upper(), m.group(2))
        spoken = _n2w(int(num)) if num == int(num) else _n2w(num)
        return f"{spoken} {sw} dollars"

    text = re.sub(r'\$(\d+(?:\.\d+)?)\s*([BMTKbmtk])\b', _dollar_abbr, text)

    # Generic large numbers: 74,000 → "seventy-four thousand"
    def _big_num(m):
        raw = m.group(0).replace(",", "")
        try:
            val = int(raw)
            if val > 999:
                return _n2w(val)
        except ValueError:
            pass
        return m.group(0)

    text = re.sub(r'(?<!\$)\b\d{1,3}(?:,\d{3})+\b', _big_num, text)

    return text


def _clean_text(text: str) -> str:
    """Clean text for TTS: strip brackets, normalize, expand numbers."""
    text = re.sub(r'\[.*?\]', '', text).strip()
    text = tts_normalize(text)
    text = expand_numbers_for_tts(text)
    return text


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


# ── FFmpeg Helpers ────────────────────────────────────────────────────────────

def ffprobe_duration(path: str) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path],
        capture_output=True, text=True,
    )
    try:
        return float(r.stdout.strip())
    except Exception:
        return -1.0


def _generate_silence(output_path: str, duration: float) -> bool:
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


# ── ElevenLabs Synthesis ─────────────────────────────────────────────────────

def _synthesize_elevenlabs(text: str, output_path: str, segment_type: str = "setup") -> bool:
    """Synthesize a single line via ElevenLabs PBX voice."""
    import requests

    api_key = _get_api_key()
    if not api_key:
        logger.error("ELEVENLABS_API_KEY not found")
        return False

    _elevenlabs_rate_limit()

    mode = VOICE_MODES.get(segment_type, PBX_VOICE_SETTINGS)
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{PBX_VOICE_ID}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "text": text,
        "model_id": PBX_MODEL,
        "speed": PBX_SPEED,
        "voice_settings": mode,
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=60)
        if resp.status_code != 200:
            logger.error(f"ElevenLabs {resp.status_code}: {resp.text[:200]}")
            return False

        # Write MP3, convert to M4A for concat compatibility
        mp3_path = output_path.replace(".m4a", ".mp3")
        with open(mp3_path, "wb") as f:
            f.write(resp.content)

        if not _mp3_to_m4a(mp3_path, output_path):
            logger.error(f"MP3→M4A conversion failed: {mp3_path}")
            return False

        os.remove(mp3_path)
        dur = ffprobe_duration(output_path)
        logger.info(f"  TTS OK: {dur:.1f}s — {text[:60]}...")
        return True

    except Exception as e:
        logger.error(f"ElevenLabs error: {e}")
        return False


def _synthesize_line(index: int, text: str, segment_type: str, output_dir: str) -> dict:
    """Synthesize one dialogue line. Returns result dict."""
    text = _clean_text(text)
    if not text:
        return {"index": index, "ok": False, "reason": "empty text"}

    chunks = _chunk_text(text)
    chunk_paths = []

    for ci, chunk in enumerate(chunks):
        out_path = os.path.join(output_dir, f"line_{index:04d}_c{ci:02d}.m4a")
        ok = _synthesize_elevenlabs(chunk, out_path, segment_type)
        if ok:
            chunk_paths.append(out_path)
        else:
            return {"index": index, "ok": False, "reason": f"chunk {ci} failed"}

    # Concat chunks if multiple
    if len(chunk_paths) == 1:
        final_path = os.path.join(output_dir, f"line_{index:04d}.m4a")
        shutil.move(chunk_paths[0], final_path)
    else:
        final_path = os.path.join(output_dir, f"line_{index:04d}.m4a")
        concat_list = os.path.join(output_dir, f"line_{index:04d}_concat.txt")
        with open(concat_list, "w") as f:
            for p in chunk_paths:
                f.write(f"file '{p}'\n")
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
             "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k", final_path],
            capture_output=True, text=True, timeout=60,
        )
        for p in chunk_paths:
            os.remove(p)
        os.remove(concat_list)

    dur = ffprobe_duration(final_path) if os.path.exists(final_path) else -1
    return {
        "index": index,
        "ok": os.path.exists(final_path) and dur > 0,
        "path": final_path,
        "duration": dur,
        "text": text,
    }


# ── Main Entry Point ─────────────────────────────────────────────────────────

def generate_pbx_audio(dialogue: list, output_dir: str) -> dict:
    """Generate PBX narrator audio for an entire episode dialogue.

    Args:
        dialogue: List of dicts with keys: host, type, text, [rank, duration]
                  host="CLIP" entries are skipped (just timeline gaps).
        output_dir: Directory for audio files.

    Returns:
        dict with: full_dialogue_path, line_results, total_duration
    """
    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"[PBX-TTS] Generating audio for {len(dialogue)} dialogue entries")

    # Phase 1: Parallel synthesis of all spoken lines
    spoken = [(i, entry) for i, entry in enumerate(dialogue)
              if entry.get("host") != "CLIP" and entry.get("text", "").strip()]

    results = {}
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {}
        for idx, entry in spoken:
            f = executor.submit(
                _synthesize_line, idx, entry["text"],
                entry.get("type", "setup"), output_dir
            )
            futures[f] = idx

        for future in as_completed(futures):
            result = future.result()
            results[result["index"]] = result

    # Phase 2: Assemble timeline
    concat_entries = []
    total_duration = 0.0

    for i, entry in enumerate(dialogue):
        if entry.get("host") == "CLIP":
            # Clip gap — duration placeholder
            clip_dur = entry.get("duration", 30.0)
            total_duration += clip_dur
            continue

        if i in results and results[i]["ok"]:
            concat_entries.append(results[i]["path"])
            total_duration += results[i]["duration"]

            # Add silence gap between lines
            gap_path = os.path.join(output_dir, f"gap_{i:04d}.m4a")
            if _generate_silence(gap_path, SILENCE_GAP):
                concat_entries.append(gap_path)
                total_duration += SILENCE_GAP

    # Phase 3: Concatenate all audio into full_dialogue.m4a
    full_path = os.path.join(output_dir, "full_dialogue.m4a")
    if concat_entries:
        concat_list = os.path.join(output_dir, "full_concat.txt")
        with open(concat_list, "w") as f:
            for p in concat_entries:
                f.write(f"file '{p}'\n")
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
             "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k", full_path],
            capture_output=True, text=True, timeout=300,
        )
        os.remove(concat_list)

    ok_count = sum(1 for r in results.values() if r["ok"])
    fail_count = sum(1 for r in results.values() if not r["ok"])
    logger.info(f"[PBX-TTS] Done: {ok_count} OK, {fail_count} failed, {total_duration:.1f}s total")

    return {
        "full_dialogue_path": full_path if os.path.exists(full_path) else None,
        "line_results": results,
        "total_duration": total_duration,
        "ok_count": ok_count,
        "fail_count": fail_count,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
    # Quick test
    test_dialogue = [
        {"host": 2, "type": "cold_open", "text": "Bitcoin just printed a new local high. Let's break down what this means."},
        {"host": 2, "type": "setup", "text": "Simply Bitcoin had a fascinating segment on the mining difficulty adjustment."},
        {"host": "CLIP", "type": "clip", "rank": 1, "duration": 45.0},
        {"host": 2, "type": "react", "text": "That's a key insight. The hashrate is telling us something the price hasn't priced in yet."},
        {"host": 2, "type": "wrap", "text": "That's the pulse check. Stay free. Stay sovereign. This is PBX, Protocol Pulse."},
    ]
    out = "/tmp/pbx_tts_test"
    result = generate_pbx_audio(test_dialogue, out)
    print(json.dumps({k: v for k, v in result.items() if k != "line_results"}, indent=2))
