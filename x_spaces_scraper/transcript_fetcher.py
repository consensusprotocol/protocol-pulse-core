"""
transcript_fetcher.py — Download Space audio and transcribe with Whisper.

Uses yt-dlp for audio download and faster-whisper for GPU-accelerated transcription.
Caches transcripts to avoid re-processing.
"""

import hashlib
import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)

# Whisper config — use "base" for speed, "large-v3" for accuracy
WHISPER_MODEL = "base"
WHISPER_DEVICE = "cuda"
WHISPER_COMPUTE_TYPE = "float16"


def _cache_path(space_id: str) -> Path:
    return CACHE_DIR / f"transcript_{space_id}.json"


def _audio_cache_path(space_id: str) -> Path:
    return CACHE_DIR / f"audio_{space_id}.mp3"


def get_cached_transcript(space_id: str) -> Optional[dict]:
    """Return cached transcript if available."""
    path = _cache_path(space_id)
    if path.exists():
        try:
            data = json.loads(path.read_text())
            if data.get("text"):
                logger.info(f"Cache hit for transcript {space_id}")
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return None


def download_audio(space_id: str, space_url: str) -> Optional[Path]:
    """
    Download Space audio using yt-dlp.
    Returns path to the downloaded audio file, or None on failure.
    """
    audio_path = _audio_cache_path(space_id)
    if audio_path.exists() and audio_path.stat().st_size > 1000:
        logger.info(f"Audio cache hit: {audio_path}")
        return audio_path

    logger.info(f"Downloading audio for Space {space_id}...")
    try:
        # yt-dlp handles X/Twitter Spaces natively
        cmd = [
            "yt-dlp",
            "--extract-audio",
            "--audio-format", "mp3",
            "--audio-quality", "0",
            "--output", str(audio_path.with_suffix("")),  # yt-dlp adds extension
            "--no-playlist",
            "--socket-timeout", "30",
            "--retries", "3",
            space_url,
        ]
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 min max
        )

        if proc.returncode != 0:
            logger.error(f"yt-dlp failed for {space_id}: {proc.stderr[:500]}")
            # Try alternate URL format
            alt_url = f"https://twitter.com/i/spaces/{space_id}"
            if alt_url != space_url:
                logger.info(f"Retrying with alternate URL: {alt_url}")
                cmd[-1] = alt_url
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                if proc.returncode != 0:
                    logger.error(f"yt-dlp retry failed: {proc.stderr[:500]}")
                    return None

        # yt-dlp may create the file with slightly different name
        if audio_path.exists():
            return audio_path
        # Check for file without double extension
        for candidate in audio_path.parent.glob(f"audio_{space_id}*"):
            if candidate.stat().st_size > 1000:
                if candidate != audio_path:
                    candidate.rename(audio_path)
                return audio_path

        logger.error(f"Audio file not found after download for {space_id}")
        return None

    except subprocess.TimeoutExpired:
        logger.error(f"yt-dlp timed out for {space_id}")
        return None
    except Exception as e:
        logger.error(f"download_audio({space_id}): {e}")
        return None


def transcribe_audio(audio_path: Path, space_id: str) -> Optional[dict]:
    """
    Transcribe audio using faster-whisper.
    Returns dict with: text, segments, language, duration.
    """
    logger.info(f"Transcribing {audio_path.name} with faster-whisper ({WHISPER_MODEL})...")
    try:
        from faster_whisper import WhisperModel

        model = WhisperModel(
            WHISPER_MODEL,
            device=WHISPER_DEVICE,
            compute_type=WHISPER_COMPUTE_TYPE,
        )

        segments_iter, info = model.transcribe(
            str(audio_path),
            language="en",
            beam_size=5,
            vad_filter=True,        # skip silence
            vad_parameters=dict(
                min_silence_duration_ms=500,
            ),
        )

        segments = []
        full_text_parts = []
        for seg in segments_iter:
            segments.append({
                "start": round(seg.start, 2),
                "end": round(seg.end, 2),
                "text": seg.text.strip(),
            })
            full_text_parts.append(seg.text.strip())

        full_text = " ".join(full_text_parts)
        result = {
            "space_id": space_id,
            "text": full_text,
            "segments": segments,
            "language": info.language,
            "duration_s": round(info.duration, 1),
            "word_count": len(full_text.split()),
        }

        # Cache result
        cache_path = _cache_path(space_id)
        cache_path.write_text(json.dumps(result, indent=2))
        logger.info(
            f"Transcription complete: {result['word_count']} words, "
            f"{result['duration_s']}s duration"
        )
        return result

    except Exception as e:
        logger.error(f"transcribe_audio({audio_path}): {e}")
        return None


def fetch_transcript(space_id: str, space_url: str) -> Optional[dict]:
    """
    Full pipeline: check cache → download audio → transcribe.
    Returns transcript dict or None on failure.
    """
    # Check cache first
    cached = get_cached_transcript(space_id)
    if cached:
        return cached

    # Download audio
    audio_path = download_audio(space_id, space_url)
    if not audio_path:
        logger.warning(f"Could not download audio for Space {space_id}")
        return None

    # Transcribe
    transcript = transcribe_audio(audio_path, space_id)

    # Clean up audio file to save disk (keep transcript cache)
    if transcript and audio_path.exists():
        try:
            audio_path.unlink()
            logger.debug(f"Cleaned up audio file: {audio_path}")
        except OSError:
            pass

    return transcript


# ─── CLI ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if len(sys.argv) < 2:
        print("Usage: python transcript_fetcher.py <space_url_or_id>")
        sys.exit(1)

    target = sys.argv[1]
    if target.startswith("http"):
        import re
        m = re.search(r"/spaces/(\w+)", target)
        sid = m.group(1) if m else target
        url = target
    else:
        sid = target
        url = f"https://twitter.com/i/spaces/{target}"

    result = fetch_transcript(sid, url)
    if result:
        print(f"\nTranscript ({result['word_count']} words, {result['duration_s']}s):")
        print(result["text"][:2000])
        if len(result["text"]) > 2000:
            print(f"\n... [{len(result['text']) - 2000} more chars]")
    else:
        print("Failed to fetch transcript.")
