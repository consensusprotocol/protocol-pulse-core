"""
Local Whisper Transcription
============================
Transcribe audio files locally using faster-whisper with GPU acceleration.
Returns word-level timestamps for precision clip cutting.
"""
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger("LocalWhisper")

# Lazy-load model to avoid GPU memory until needed
_model = None
_model_size = None


def _get_model(model_size: str = "base"):
    """Load whisper model (lazy, cached)."""
    global _model, _model_size
    if _model is not None and _model_size == model_size:
        return _model

    from faster_whisper import WhisperModel
    logger.info(f"  Loading Whisper model '{model_size}' on CUDA...")
    start = time.time()
    _model = WhisperModel(model_size, device="cuda", compute_type="float16")
    _model_size = model_size
    logger.info(f"  Whisper model loaded in {time.time() - start:.1f}s")
    return _model


def transcribe_audio(audio_path: str, model_size: str = "base",
                     language: str = "en") -> dict:
    """
    Transcribe an audio file with word-level timestamps.

    Args:
        audio_path: Path to audio file (wav, mp3, etc.)
        model_size: Whisper model size (base, small, medium, large-v3)
        language: Language code

    Returns:
        {
            "text": str,
            "segments": [{"start": float, "end": float, "text": str, "words": [...]}],
            "words": [{"word": str, "start": float, "end": float, "probability": float}],
            "timestamped_text": str,  # "[MM:SS] text" format
            "duration": float,
            "language": str,
        }
    """
    if not Path(audio_path).exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    model = _get_model(model_size)

    logger.info(f"  Transcribing: {Path(audio_path).name} (model={model_size})")
    start = time.time()

    segments_iter, info = model.transcribe(
        audio_path,
        language=language,
        word_timestamps=True,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
    )

    segments = []
    all_words = []
    full_text_parts = []
    timestamped_lines = []

    for seg in segments_iter:
        seg_words = []
        if seg.words:
            for w in seg.words:
                word_data = {
                    "word": w.word.strip(),
                    "start": round(w.start, 3),
                    "end": round(w.end, 3),
                    "probability": round(w.probability, 3),
                }
                seg_words.append(word_data)
                all_words.append(word_data)

        seg_text = seg.text.strip()
        segments.append({
            "start": round(seg.start, 3),
            "end": round(seg.end, 3),
            "text": seg_text,
            "words": seg_words,
        })

        full_text_parts.append(seg_text)
        mm = int(seg.start // 60)
        ss = int(seg.start % 60)
        timestamped_lines.append(f"[{mm:02d}:{ss:02d}] {seg_text}")

    elapsed = time.time() - start
    duration = info.duration if hasattr(info, "duration") else (segments[-1]["end"] if segments else 0)
    speed = duration / elapsed if elapsed > 0 else 0

    logger.info(f"  Transcribed in {elapsed:.1f}s ({speed:.0f}x realtime), "
                f"{len(segments)} segments, {len(all_words)} words")

    return {
        "text": " ".join(full_text_parts),
        "segments": segments,
        "words": all_words,
        "timestamped_text": "\n".join(timestamped_lines),
        "char_count": sum(len(t) for t in full_text_parts),
        "segment_count": len(segments),
        "word_count": len(all_words),
        "has_word_timestamps": len(all_words) > 0,
        "duration": round(duration, 2),
        "language": info.language if hasattr(info, "language") else language,
        "transcription_time": round(elapsed, 2),
    }


def download_audio(video_id: str, output_dir: str,
                   max_duration: int = 7200) -> Optional[str]:
    """
    Download audio from a YouTube video using yt-dlp.

    Returns path to the downloaded audio file, or None on failure.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    output_template = str(output_dir / f"{video_id}.%(ext)s")
    output_wav = output_dir / f"{video_id}.wav"

    # Check if already downloaded
    if output_wav.exists() and output_wav.stat().st_size > 1000:
        logger.info(f"  Audio already cached: {video_id}")
        return str(output_wav)

    url = f"https://www.youtube.com/watch?v={video_id}"

    cmd = [
        "yt-dlp",
        "-x", "--audio-format", "wav",
        "--audio-quality", "0",
        "--no-playlist",
        "-o", output_template,
        url,
    ]

    if max_duration:
        cmd.extend(["--match-filter", f"duration<={max_duration}"])

    logger.info(f"  Downloading audio: {video_id}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            logger.error(f"  yt-dlp failed: {result.stderr[:300]}")
            return None

        # Find the output file
        if output_wav.exists():
            size_mb = output_wav.stat().st_size / (1024 * 1024)
            logger.info(f"  Downloaded: {video_id}.wav ({size_mb:.1f} MB)")
            return str(output_wav)

        # Check for other audio formats that may have been downloaded
        for ext in ["wav", "m4a", "mp3", "opus", "webm"]:
            alt = output_dir / f"{video_id}.{ext}"
            if alt.exists():
                logger.info(f"  Downloaded as {ext}, converting to wav...")
                subprocess.run([
                    "ffmpeg", "-y", "-i", str(alt), "-ar", "16000",
                    "-ac", "1", str(output_wav)
                ], capture_output=True, timeout=120)
                if output_wav.exists():
                    return str(output_wav)

        logger.error(f"  No audio file found for {video_id}")
        return None

    except subprocess.TimeoutExpired:
        logger.error(f"  Audio download timed out for {video_id}")
        return None
    except Exception as e:
        logger.error(f"  Audio download error: {e}")
        return None
