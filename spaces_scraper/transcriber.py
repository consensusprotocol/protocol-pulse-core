"""
transcriber.py — Real-time Whisper Transcription on RTX 4090
- Model loaded ONCE at startup; stays in GPU memory
- Processes AudioSegment objects from a queue
- Maintains a rolling transcript buffer (last N minutes)
- Thread-safe; can be called from async context
"""

import argparse
import asyncio
import logging
import os
import time
import tempfile
from collections import deque
from dataclasses import dataclass
from typing import Optional

import config

logger = logging.getLogger(__name__)

# Lazy import to avoid loading CUDA at import time
_whisper_model = None


def get_whisper_model():
    """Load Whisper model once and cache."""
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        logger.info(
            f"Loading Whisper {config.WHISPER_MODEL} on {config.WHISPER_DEVICE} "
            f"({config.WHISPER_COMPUTE_TYPE})..."
        )
        t0 = time.time()
        _whisper_model = WhisperModel(
            config.WHISPER_MODEL,
            device=config.WHISPER_DEVICE,
            compute_type=config.WHISPER_COMPUTE_TYPE,
            download_root=os.path.expanduser("~/.cache/whisper"),
        )
        logger.info(f"Whisper model loaded in {time.time()-t0:.1f}s")
    return _whisper_model


@dataclass
class TranscriptChunk:
    space_id: str
    text: str
    timestamp: float
    segment_index: int
    confidence: float
    transcription_latency_ms: float  # wall time taken to transcribe


class RollingTranscript:
    """
    Stores transcript chunks for a single Space; provides rolling window access.
    Thread-safe (uses deque, which has atomic append/pop).
    """

    def __init__(self, space_id: str, max_chunks: int = 500):
        self.space_id = space_id
        self._chunks: deque[TranscriptChunk] = deque(maxlen=max_chunks)

    def add(self, chunk: TranscriptChunk):
        self._chunks.append(chunk)

    def get_recent(self, minutes: float = 5.0) -> list[TranscriptChunk]:
        cutoff = time.time() - (minutes * 60)
        return [c for c in self._chunks if c.timestamp >= cutoff]

    def get_text(self, minutes: float = 5.0) -> str:
        return " ".join(c.text.strip() for c in self.get_recent(minutes) if c.text.strip())

    def get_all(self) -> list[TranscriptChunk]:
        return list(self._chunks)

    @property
    def total_chunks(self) -> int:
        return len(self._chunks)


class RealtimeTranscriber:
    """
    Consumes AudioSegment objects from an asyncio queue,
    transcribes each with faster-whisper, stores results in
    per-space RollingTranscript objects.
    """

    def __init__(self):
        self._transcripts: dict[str, RollingTranscript] = {}
        self._stats = {
            "segments_processed": 0,
            "total_transcription_ms": 0,
            "total_audio_seconds": 0,
            "errors": 0,
        }
        self._running = False
        # Load model at construction time to warm it up
        self._model = None  # lazy — loaded on first use

    def get_transcript(self, space_id: str) -> Optional[RollingTranscript]:
        return self._transcripts.get(space_id)

    def get_all_transcripts(self) -> dict[str, RollingTranscript]:
        return dict(self._transcripts)

    def get_stats(self) -> dict:
        stats = dict(self._stats)
        if stats["segments_processed"] > 0:
            stats["avg_latency_ms"] = stats["total_transcription_ms"] / stats["segments_processed"]
        else:
            stats["avg_latency_ms"] = 0
        if stats["total_transcription_ms"] > 0:
            stats["realtime_factor"] = (
                stats["total_audio_seconds"] * 1000 / stats["total_transcription_ms"]
            )
        else:
            stats["realtime_factor"] = 0
        return stats

    def transcribe_file(self, wav_path: str, space_id: str = "") -> Optional[TranscriptChunk]:
        """
        Synchronously transcribe a WAV file.
        Returns a TranscriptChunk, or None on failure.
        """
        if self._model is None:
            self._model = get_whisper_model()

        t0 = time.perf_counter()
        try:
            segments, info = self._model.transcribe(
                wav_path,
                beam_size=config.WHISPER_BEAM_SIZE,
                language=config.WHISPER_LANGUAGE,
                vad_filter=True,
                vad_parameters=dict(
                    min_silence_duration_ms=300,
                    speech_pad_ms=100,
                ),
            )
            text = " ".join(s.text for s in segments).strip()
            latency_ms = (time.perf_counter() - t0) * 1000

            # Estimate audio duration from file size (rough: 16kHz mono WAV ≈ 32 KB/s)
            try:
                file_size_kb = os.path.getsize(wav_path) / 1024
                audio_seconds = file_size_kb / 32.0
            except Exception:
                audio_seconds = config.SEGMENT_DURATION_S

            self._stats["segments_processed"] += 1
            self._stats["total_transcription_ms"] += latency_ms
            self._stats["total_audio_seconds"] += audio_seconds

            logger.debug(
                f"[{space_id}] Transcribed in {latency_ms:.0f}ms "
                f"(RTF={audio_seconds*1000/max(latency_ms,1):.1f}x): {text[:80]}"
            )

            return TranscriptChunk(
                space_id=space_id,
                text=text,
                timestamp=time.time(),
                segment_index=self._stats["segments_processed"],
                confidence=info.language_probability,
                transcription_latency_ms=latency_ms,
            )

        except Exception as e:
            self._stats["errors"] += 1
            logger.error(f"Transcription error for {wav_path}: {e}")
            return None
        finally:
            # Clean up WAV segment after transcription
            try:
                os.unlink(wav_path)
            except Exception:
                pass

    async def process_queue(self, queue: asyncio.Queue):
        """
        Async consumer: pulls AudioSegment items from the queue and transcribes them.
        Runs in an executor to avoid blocking the event loop during GPU inference.
        """
        self._running = True
        loop = asyncio.get_event_loop()
        logger.info("RealtimeTranscriber queue consumer started")

        # Pre-warm model
        loop.run_in_executor(None, get_whisper_model)

        while self._running:
            try:
                from capture import AudioSegment
                segment = await asyncio.wait_for(queue.get(), timeout=5.0)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Queue error: {e}")
                continue

            # Transcribe in thread pool (GPU, not blocking event loop)
            chunk = await loop.run_in_executor(
                None,
                self.transcribe_file,
                segment.path,
                segment.space_id,
            )

            if chunk:
                if segment.space_id not in self._transcripts:
                    self._transcripts[segment.space_id] = RollingTranscript(segment.space_id)
                self._transcripts[segment.space_id].add(chunk)

                # Log every 10th chunk
                if self._stats["segments_processed"] % 10 == 0:
                    stats = self.get_stats()
                    logger.info(
                        f"Transcriber stats: {stats['segments_processed']} segments, "
                        f"avg {stats['avg_latency_ms']:.0f}ms/seg, "
                        f"RTF {stats['realtime_factor']:.1f}x realtime"
                    )

            queue.task_done()

    def stop(self):
        self._running = False


# ─── CLI Test ─────────────────────────────────────────────────────────────────

def _test_transcriber():
    """Transcribe a synthetic test audio file and report timing."""
    import subprocess
    import numpy as np

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    logger.info("=== Transcriber test ===")

    # Generate 10s of speech-like audio using a sample file or silence
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        test_wav = f.name

    # Try to use an existing audio file first, otherwise generate silence
    sample_sources = [
        "/usr/share/sounds/alsa/Front_Left.wav",
        "/usr/share/sounds/alsa/Noise.wav",
        os.path.expanduser("~/test_audio.wav"),
    ]
    existing_audio = next((s for s in sample_sources if os.path.exists(s)), None)

    if existing_audio:
        # Extend to 10 seconds
        subprocess.run([
            "ffmpeg", "-y", "-stream_loop", "-1",
            "-i", existing_audio,
            "-t", "10",
            "-ar", "16000", "-ac", "1",
            test_wav
        ], capture_output=True)
    else:
        # Generate 10s silent WAV at 16kHz (Whisper handles silence fine, just won't produce text)
        subprocess.run([
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "anoisesrc=r=16000:color=white:amplitude=0.001:duration=10",
            "-ar", "16000", "-ac", "1",
            test_wav
        ], capture_output=True)

    if not os.path.exists(test_wav) or os.path.getsize(test_wav) == 0:
        # Fallback: write raw silence directly
        import wave, struct
        with wave.open(test_wav, 'w') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(b'\x00\x00' * 16000 * 10)

    logger.info(f"Test audio: {test_wav} ({os.path.getsize(test_wav)} bytes)")

    transcriber = RealtimeTranscriber()
    logger.info("Starting transcription (model loading on first call)...")
    t0 = time.perf_counter()
    chunk = transcriber.transcribe_file(test_wav, space_id="test")
    elapsed = time.perf_counter() - t0

    if chunk:
        print(f"\n✓ Transcription complete!")
        print(f"  Audio duration: ~10s")
        print(f"  Transcription time: {elapsed:.2f}s")
        print(f"  Realtime factor: {10/elapsed:.1f}x faster than realtime")
        print(f"  Text: '{chunk.text or '(silence/no speech)'}'")
        print(f"  Confidence: {chunk.confidence:.3f}")
    else:
        print(f"\n✗ Transcription returned None (check GPU/model)")

    print(f"\nStats: {transcriber.get_stats()}")

    # Cleanup (file already deleted by transcribe_file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args()
    if args.test:
        _test_transcriber()
